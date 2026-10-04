"""The front-end kernel is loadable outside the page — the C7 first step.

Before this extraction the 81k kernel lived in an inline <script> inside
index.html, so a test could only reach it by loading the whole document. That
is not a unit test. It now lives in static/fox-core.js, and this file proves
two things by execution rather than by reading source:

1. The whole front-end script chain, in the exact order index.html loads it,
   runs in a bare context and leaves every shared helper the external files
   depend on defined. fox-core.js is NOT standalone — it calls
   FoxCanvasEngine.create() at top level — so the gate loads the real chain.

2. Every <script src> the page asks for is actually served with HTTP 200.
   STATIC_FILES is an explicit whitelist, so a script that is written but not
   registered 404s and takes the whole workbench down while every other gate
   stays green. That is the same shape as the v0.6.0 portable crash.

Nothing here greps the source for a symbol name. A grep-shaped gate can be
satisfied by a comment and is satisfied by a harmless refactor, which is how
tests/test_gate_quality_gates.py was falsified and rejected. Every assertion
below runs code and inspects what the code produced.
"""
from __future__ import annotations

import re
import subprocess
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

STATIC = ROOT / "htmlninefox" / "server" / "static"
INDEX = STATIC / "index.html"
CORE = STATIC / "fox-core.js"

# The symbols the external .js files call as bare globals. If one goes missing
# the page breaks at load time, and this is the cheapest place to notice.
REQUIRED = ("api", "flash", "select", "timeline", "fitAll", "renderInspector",
            "renderPalette", "save", "loadSaved", "persistWorkspaceNow",
            "activeWorkspace")

# Namespaces the IIFE files reach the kernel through.
NAMESPACES = ("FoxCanvasGroups", "FoxActions")


def _script_srcs() -> list[str]:
    index = INDEX.read_text(encoding="utf-8")
    return re.findall(r'<script[^>]*\ssrc="([^"]+)"', index)


def _inline_block_sizes() -> list[int]:
    index = INDEX.read_text(encoding="utf-8")
    return [len(b) for b in
            re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", index, re.S)]


def _node_available() -> bool:
    try:
        subprocess.run(["node", "--version"], capture_output=True, check=True)
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


# A callable, constructible, infinitely-deep stub. Top-level front-end code does
# things like document.querySelector(...).classList.add(...); this answers all
# of it without pretending to be a DOM. It is deliberately a *loader* context:
# the gate below asserts what gets defined, not that rendering works.
_STUB_JS = r"""
function __stub(name) {
  const fn = function () { return __stub(name + '()'); };
  return new Proxy(fn, {
    get(t, k) {
      if (k === Symbol.toPrimitive) return () => 0;
      if (k === 'toString') return () => '';
      if (k === Symbol.iterator) return function* () {};
      if (k === 'then') return undefined;
      if (k === Symbol.hasInstance) return () => false;
      if (k === 'prototype') return t.prototype;
      if (k === 'nodeType' || k === 'length' || k === 'clientWidth') return 0;
      if (k === 'style' || k === 'dataset' || k === 'classList') {
        return __stub(name + '.' + String(k));
      }
      if (k === 'setAttribute' || k === 'addEventListener' || k === 'appendChild') {
        return () => undefined;
      }
      return __stub(name + '.' + String(k));
    },
    apply() { return __stub(name + '()'); },
    construct() { return __stub('new ' + name); },
  });
}

const document = __stub('document');
document.documentElement = __stub('html');
document.body = __stub('body');
document.head = __stub('head');

const sandbox = {
  document,
  localStorage: { getItem: () => null, setItem(){}, removeItem(){}, clear(){} },
  sessionStorage: { getItem: () => null, setItem(){}, removeItem(){}, clear(){} },
  console,
  setTimeout, clearTimeout, setInterval, clearInterval,
  fetch: () => __stub('fetch()'),
  location: { protocol: 'http:', host: 'x', href: 'http://x/', origin: 'http://x' },
  URL, URLSearchParams, FormData, Headers, Request, Response,
  Blob, TextEncoder, TextDecoder,
  AbortController, Event, EventTarget: class { addEventListener(){} },
  CustomEvent: class { constructor(t, o){ this.type = t; Object.assign(this, o); } },
  MessageChannel: class { port1 = {}; port2 = {}; },
  Worker: class { postMessage(){} terminate(){} addEventListener(){} },
  crypto: { getRandomValues: (a) => a, subtle: {} },
  customElements: { define(){}, get(){ return null; } },
  matchMedia: () => ({ matches: false, addEventListener(){}, addListener(){} }),
  navigator: { clipboard: { writeText: () => {} }, userAgent: 'node', language: 'zh' },
  getComputedStyle: () => __stub('css'),
  requestAnimationFrame: () => 0, cancelAnimationFrame(){},
  ResizeObserver: class { observe(){} unobserve(){} disconnect(){} },
  MutationObserver: class { observe(){} disconnect(){} takeRecords(){ return []; } },
  IntersectionObserver: class { observe(){} disconnect(){} },
  performance: { now: () => 0 },
  alert(){}, confirm: () => true, prompt: () => null,
  history: { pushState(){}, replaceState(){} },
  addEventListener(){}, removeEventListener(){}, dispatchEvent(){ return true; },
  innerWidth: 1280, innerHeight: 800, devicePixelRatio: 1,
  screen: { width: 1280, height: 800 },
};
sandbox.globalThis = sandbox;
sandbox.self = sandbox;
// In a browser window === globalThis. Mirror that, otherwise top-level function
// declarations land on the context global and never become window properties.
sandbox.window = sandbox;

vm.createContext(sandbox);
for (const f of JSON.parse(process.argv[2])) {
  const src = fs.readFileSync(path.join(STATIC_DIR, f), 'utf8');
  try {
    vm.runInContext(src, sandbox, { filename: f });
  } catch (e) {
    console.log('LOAD_ERROR:' + f + ' :: ' + e.message);
    process.exit(3);
  }
}
const want = JSON.parse(process.argv[3]);
const out = {};
for (const n of want) out[n] = typeof sandbox[n];
console.log('TYPES:' + JSON.stringify(out));
"""


def test_fox_core_exists_and_is_not_inline():
    """The kernel must be a real served file, not a blob back in the page."""
    assert CORE.exists(), (
        "static/fox-core.js 不存在——内核仍困在 index.html 的 inline script 里")
    index = INDEX.read_text(encoding="utf-8")
    assert '<script src="/fox-core.js">' in index, "index.html 没有引用 fox-core.js"
    sizes = _inline_block_sizes()
    assert all(s < 2000 for s in sizes), (
        f"index.html 里仍有大型 inline script（{sizes} 字符）——内核被搬回去了")


def test_fox_core_passes_the_node_syntax_check():
    proc = subprocess.run(["node", "--check", str(CORE)],
                          capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    assert proc.returncode == 0, f"语法错误：{proc.stderr[-500:]}"


@pytest.mark.skipif(not _node_available(), reason="node 不可用")
def test_front_end_chain_loads_and_every_shared_helper_is_really_defined():
    """Load index.html's real script chain in a bare context and ask the
    finished context what it defined.

    A syntax check alone cannot catch a file that parses and then throws on
    load — which is the difference between "the file is fine" and "the page is
    blank". Equally, grepping for `function flash(` would pass on a comment and
    would keep passing if the definition were moved into a dead branch, so the
    answer is read back off a live context object instead.
    """
    import json
    import tempfile

    srcs = _script_srcs()
    names = [s.rsplit("/", 1)[-1] for s in srcs]
    assert "fox-core.js" in names, "index.html 没有加载 fox-core.js"
    for name in names:
        assert (STATIC / name).exists(), f"index.html 引用了不存在的脚本：{name}"

    d = Path(tempfile.mkdtemp())
    js = d / "driver.js"
    js.write_text(
        "const fs = require('fs');\n"
        "const vm = require('vm');\n"
        "const path = require('path');\n"
        f"const STATIC_DIR = {str(STATIC)!r};\n"
        + _STUB_JS,
        encoding="utf-8")

    proc = subprocess.run(
        ["node", str(js), json.dumps(names), json.dumps(list(REQUIRED) + list(NAMESPACES))],
        capture_output=True, text=True, timeout=120,
        encoding="utf-8", errors="replace")

    if proc.returncode == 3 or "LOAD_ERROR" in proc.stdout:
        pytest.fail(
            f"前端脚本链在裸上下文中加载即抛错：{proc.stdout.strip()[:600]}")
    assert proc.returncode == 0, f"node 失败：{proc.stderr[-600:]}"

    line = next((l for l in proc.stdout.splitlines() if l.startswith("TYPES:")), None)
    assert line, f"driver 没有回报类型：{proc.stdout[:400]}"
    types = json.loads(line[6:])

    missing = [n for n in REQUIRED if types.get(n) != "function"]
    assert not missing, (
        f"加载完成后仍未定义的共享助手：{missing}——外部脚本会在运行时报错")
    bad_ns = [n for n in NAMESPACES if types.get(n) != "object"]
    assert not bad_ns, f"内核未暴露命名空间：{bad_ns}"


def test_every_script_the_page_asks_for_is_actually_served():
    """STATIC_FILES is an explicit whitelist; a script written but not
    registered returns 404 and the entire workbench stops booting while every
    other gate stays green. Boot the real handler and fetch each one.
    """
    from htmlninefox.server import app as server_app

    srcs = _script_srcs()
    assert srcs, "index.html 没有引用任何外部脚本"

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server_app._Handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        bad = []
        for src in srcs:
            name = src.rsplit("/", 1)[-1]
            try:
                with urlopen(f"http://127.0.0.1:{port}{src}", timeout=10) as r:
                    status, body = r.status, r.read()
                    ctype = r.headers.get("Content-Type", "")
            except Exception as exc:  # noqa: BLE001 - report the real reason
                bad.append(f"{src} -> {type(exc).__name__}: {exc}")
                continue
            if status != 200:
                bad.append(f"{src} -> HTTP {status}")
            elif body != (STATIC / name).read_bytes():
                # Catches a whitelist entry that points at the wrong file as
                # well as a truncated body. Comparing bytes beats asserting a
                # length, which a wrong-but-plausible file would survive.
                bad.append(f"{src} -> 返回内容与 {name} 不一致（{len(body)} 字节）")
            elif "javascript" not in ctype:
                bad.append(f"{src} -> Content-Type 不是 JavaScript：{ctype!r}")
        assert not bad, (
            "页面请求的脚本在真实服务端上不可达或内容不符"
            "（检查 app.py 的 STATIC_FILES 白名单）：\n" + "\n".join(bad))
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=10)
