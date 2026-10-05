"""workbench-features.js 的纯函数可以在 Node 里单独测了。

这是 C7 第二步要兑现的那句话。以前这个文件在**解析时**就执行十三行顶层语句：
七处 DOM 绑定、一处 DOM 调用、三处对内核 PALETTE 的赋值。于是它既不能被单独
加载（没有 DOM、没有 PALETTE 就抛），也只能靠 Playwright 从外面戳。

现在顶层只剩声明，纯函数只看 `state`，所以下面这个门禁用一个假 state 把文件
load 起来，逐个函数断言**真实返回值**。

关于「纯」的诚实说法
--------------------
这一批里真正只依赖 `state` 的只有六个：
    galleryItem / galleryTemplateData / galleryPageData
    memoryValueText / memorySummaryMarkup / isProjectAdopted
`applyRecommendedRecipe` 与 `ensureCreationRequirement` 改的是工作区内容，依赖
`membersOf` / `addMaterialToWorkspace` / DOM，本轮**没有**变成可单测的纯函数。
早先的规划文档把它们一并算成「八个纯函数」，那是高估。

为什么用 node 的 vm 而不是 jsdom
-------------------------------
这里要证明的是「这个文件不依赖加载顺序、也不在加载时碰外部对象」。jsdom 会
给出一个真实的 DOM，反而把「文件自己声明了哪些顶层副作用」这件事盖住。用一个
只有假 state 的空沙箱，装得上就是装得上，装不上会立刻报出是哪一行碰了外部。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "htmlninefox" / "server" / "static"
FEATURES = STATIC / "workbench-features.js"
CORE = STATIC / "fox-core.js"
INDEX = STATIC / "index.html"

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# 加载器：只提供 state 与 esc。少给一个，报错就会指名道姓说是哪个名字找不到，
# 而不是含糊地失败——这正是「装得上就是装得上」要能被看见的地方。
LOADER = r"""
const fs = require('fs'), vm = require('vm');
const sandbox = {
  state: JSON.parse(process.argv[3]),
  esc: s => (s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
            .replace(/"/g,'&quot;').replace(/'/g,'&#39;'),
  console,
};
sandbox.globalThis = sandbox; sandbox.self = sandbox; sandbox.window = sandbox;
vm.createContext(sandbox);
try {
  vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), sandbox,
                  { filename: 'workbench-features.js' });
} catch (e) {
  console.log('LOAD_ERROR:' + e.name + ': ' + e.message);
  console.log((e.stack || '').split('\n').slice(1, 4).join('\n'));
  process.exit(3);
}
console.log('LOADED');
const out = {};
for (const expr of JSON.parse(process.argv[4])) {
  try { out[expr] = { ok: true, value: vm.runInContext(expr, sandbox) }; }
  catch (e) { out[expr] = { ok: false, error: e.name + ': ' + e.message }; }
}
console.log('RESULTS:' + JSON.stringify(out));
"""


def _node_available() -> bool:
    try:
        subprocess.run(["node", "--version"], capture_output=True, check=True)
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


needs_node = pytest.mark.skipif(not _node_available(), reason="node 不可用")


# 整条链用的加载器。DOM 是一个无限深的 stub：这里要回答的是「装得上吗」，
# 不是「渲染对吗」，后者归 e2e。
_CHAIN_LOADER = r"""
const fs = require('fs'), vm = require('vm'), path = require('path');
const STATIC_DIR = process.argv[2];
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
      if (k === 'style' || k === 'dataset' || k === 'classList') return __stub(String(k));
      if (k === 'setAttribute' || k === 'addEventListener' || k === 'appendChild') return () => undefined;
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
  console, setTimeout, clearTimeout, setInterval, clearInterval,
  fetch: () => __stub('fetch()'),
  location: { protocol:'http:', host:'x', href:'http://x/', origin:'http://x' },
  URL, URLSearchParams, FormData, Headers, Request, Response,
  Blob, TextEncoder, TextDecoder,
  AbortController, Event, EventTarget: class { addEventListener(){} },
  CustomEvent: class { constructor(t,o){ this.type=t; Object.assign(this,o); } },
  MessageChannel: class { port1={}; port2={}; },
  Worker: class { postMessage(){} terminate(){} addEventListener(){} },
  crypto: { getRandomValues: a => a, subtle: {} },
  customElements: { define(){}, get(){ return null; } },
  matchMedia: () => ({ matches:false, addEventListener(){}, addListener(){} }),
  navigator: { clipboard:{ writeText(){} }, userAgent:'node', language:'zh' },
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
sandbox.globalThis = sandbox; sandbox.self = sandbox; sandbox.window = sandbox;
vm.createContext(sandbox);
for (const f of JSON.parse(process.argv[3])) {
  try {
    vm.runInContext(fs.readFileSync(path.join(STATIC_DIR, f), 'utf8'), sandbox, { filename: f });
  } catch (e) {
    console.log('LOAD_ERROR:' + f + ' :: ' + e.message);
    process.exit(3);
  }
}
console.log('LOADED');
"""


def _chain_from_index() -> list[str]:
    """The script chain index.html actually loads, read from index.html.

    Deliberately not a hard-coded list: with a hard-coded one, "somebody moved
    the extension file to the front" is invisible to every gate here, and that
    is precisely the change this refactor is supposed to have made harmless.
    """
    index = INDEX.read_text(encoding="utf-8")
    names = [s.rsplit("/", 1)[-1] for s in
             re.findall(r'<script[^>]*\ssrc\s*=\s*["\'](/[^"\']+)["\']', index)]
    assert len(names) >= 10, f"从 index.html 只读到 {len(names)} 个脚本，规则不对"
    return names


def _load_chain(order: list[str]) -> str | None:
    """Load a whole chain; return None if it loaded, else the failure text."""
    d = Path(tempfile.mkdtemp())
    js = d / "chain.js"
    js.write_text(_CHAIN_LOADER, encoding="utf-8")
    proc = subprocess.run(
        ["node", str(js), str(STATIC), json.dumps(order)],
        capture_output=True, text=True, timeout=120,
        encoding="utf-8", errors="replace")
    if proc.returncode == 0 and "LOADED" in proc.stdout:
        return None
    return (proc.stdout.strip() or proc.stderr.strip())[:600]


def _load(state: dict, expressions: list[str]) -> dict:
    d = Path(tempfile.mkdtemp())
    js = d / "loader.js"
    js.write_text(LOADER, encoding="utf-8")
    proc = subprocess.run(
        ["node", str(js), str(FEATURES), json.dumps(state), json.dumps(expressions)],
        capture_output=True, text=True, timeout=60,
        encoding="utf-8", errors="replace")
    if proc.returncode == 3 or "LOAD_ERROR" in proc.stdout:
        pytest.fail(
            "workbench-features.js 装不进一个只有 state 的空上下文——"
            "说明它加载时还在碰 DOM 或内核对象：\n" + proc.stdout.strip()[:900])
    assert proc.returncode == 0, f"node 失败：{proc.stderr[-600:]}"
    line = next(l for l in proc.stdout.splitlines() if l.startswith("RESULTS:"))
    return json.loads(line[8:])


GALLERY = [
    {"id": "g1", "name": "发布会", "source": "user", "description": "用户导入",
     "intent": "deck", "preset_id": "fox-pixel-garden", "origin": "本地",
     "preview_url": "/p/1", "pages": [{"id": "p1", "name": "封面",
                                      "headline": "开场", "preview_url": "/p/1a"}]},
    {"id": "g2", "name": "报告", "source": "builtin", "description": "内置",
     "intent": "deck", "preset_id": "fox-ink", "origin": "官方",
     "preview_url": "/p/2", "pages": [{"id": "p2", "name": "摘要",
                                      "headline": "结论", "preview_url": "/p/2a"}]},
]

MEMORY = {"enabled": True, "stats": {"adopted_count": 2},
          "evidence": [{"project": "P1"}],
          "profile": {"preferred_preset_by_intent": {"deck": "fox-ink"}}}


# --------------------------------------------------------------- 加载本身

@needs_node
def test_features_file_loads_with_nothing_but_a_state():
    """这条是整份门禁的地基：它只证明「装得上」。

    它不检查任何业务行为，业务行为在下面几条。它失败时最有用的信息是
    load 时报出的那个名字——那直接指名了还在顶层执行的语句。
    """
    _load({"gallery": [], "memory": None}, ["typeof galleryItem"])


@needs_node
def test_the_pure_helpers_all_exist_as_functions():
    got = _load({"gallery": GALLERY, "memory": MEMORY},
                [f"typeof {name}" for name in (
                    "galleryItem", "galleryTemplateData", "galleryPageData",
                    "memoryValueText", "memorySummaryMarkup", "isProjectAdopted")])
    missing = [k for k, v in got.items() if v.get("value") != "function"]
    assert not missing, f"这些名字在本文件里不再是函数：{missing}"


# --------------------------------------------------------- 真实行为断言

@needs_node
def test_gallery_item_reads_the_injected_state():
    got = _load({"gallery": GALLERY}, [
        "galleryItem('g1').name",
        "galleryItem('nope') === undefined",
    ])
    assert got["galleryItem('g1').name"]["value"] == "发布会"
    assert got["galleryItem('nope') === undefined"]["value"] is True


@needs_node
def test_gallery_template_data_carries_the_drag_payload():
    """拖拽数据是这个函数的全部用途：它必须把 gallery_id / preview 一起带上，
    否则拖到画布上的模板节点就找不到自己的来源。

    字段名照抄 galleryTemplateData 的真实返回结构（preset 而不是 preset_id），
    不靠记忆。第一版这里写成 preset_id，断言直接 KeyError——测试自己写错了字段，
    报出来的却像是产品坏了。
    """
    got = _load({"gallery": GALLERY}, ["JSON.stringify(galleryTemplateData(galleryItem('g1')))"])
    data = json.loads(got["JSON.stringify(galleryTemplateData(galleryItem('g1')))"]["value"])
    assert data["gallery_id"] == "g1"
    assert data["preset"] == "fox-pixel-garden"
    assert data["intent"] == "deck"
    assert data["preview_url"] == "/p/1"
    assert data["title"] == "发布会"
    assert data["pages"] == GALLERY[0]["pages"]


@needs_node
def test_gallery_page_data_keeps_both_the_item_and_the_page():
    got = _load({"gallery": GALLERY},
                ["JSON.stringify(galleryPageData(galleryItem('g2'), galleryItem('g2').pages[0]))"])
    data = json.loads(
        got["JSON.stringify(galleryPageData(galleryItem('g2'), galleryItem('g2').pages[0]))"]["value"])
    assert data["gallery_id"] == "g2"
    assert data["page_id"] == "p2"
    assert data["template"] == "fox-ink"
    assert data["text"] == "结论"


@needs_node
def test_memory_value_text_flattens_arrays_and_survives_nothing():
    got = _load({"memory": None}, [
        "memoryValueText(['品牌', '受众'])",
        "memoryValueText('品牌')",
        "memoryValueText(undefined)",
    ])
    assert got["memoryValueText(['品牌', '受众'])"]["value"] == "品牌、受众"
    assert got["memoryValueText('品牌')"]["value"] == "品牌"
    assert got["memoryValueText(undefined)"]["value"] == ""


@needs_node
def test_is_project_adopted_answers_from_the_evidence_list():
    got = _load({"memory": MEMORY}, [
        "isProjectAdopted('P1')", "isProjectAdopted('P2')", "isProjectAdopted('')",
    ])
    assert got["isProjectAdopted('P1')"]["value"] is True
    assert got["isProjectAdopted('P2')"]["value"] is False
    assert got["isProjectAdopted('')"]["value"] is False


@needs_node
def test_is_project_adopted_is_false_when_memory_never_loaded():
    """记忆面板没加载成功时 state.memory 是空对象而不是 undefined 之外的什么，
    这里钉住「没有证据就不算采用过」，免得把空值当成真。"""
    got = _load({"memory": None}, ["isProjectAdopted('P1')"])
    assert got["isProjectAdopted('P1')"]["value"] is False


@needs_node
def test_memory_summary_markup_escapes_the_value_it_echoes():
    """这个函数把 memory 里的值拼进 HTML。漏掉 esc 就是一条注入路径，
    所以门禁要验的是「恶意值被转义」，不是「有输出」。"""
    got = _load({"memory": MEMORY}, [
        "memorySummaryMarkup({ applied: [{ field: 'brand', value: '<img src=x>' }], covered: [] })",
        "memorySummaryMarkup(null)",
        "memorySummaryMarkup({ applied: [], covered: [] })",
    ])
    html = got["memorySummaryMarkup({ applied: [{ field: 'brand', value: '<img src=x>' }], covered: [] })"]["value"]
    assert "&lt;img src=x&gt;" in html, f"记忆摘要没有转义用户值：{html!r}"
    assert "<img" not in html, f"记忆摘要里有未转义的标签：{html!r}"
    assert got["memorySummaryMarkup(null)"]["value"] == ""
    assert got["memorySummaryMarkup({ applied: [], covered: [] })"]["value"] == ""


# --------------------------------------------------- 顺序不再是硬约束

@needs_node
def test_features_declares_no_top_level_side_effects():
    """顶层只允许声明。

    这是「顺序无关」这件事的结构性保证。检查方式是数：把文件逐行的花括号深度
    累计一遍，深度为 0 的行如果既不是声明、也不是空行或注释，就说明加载时还有
    语句要执行。改动本文件的人会立刻看到自己多加了一行。
    """
    depth = 0
    in_comment = False
    offenders: list[tuple[int, str]] = []
    decl = re.compile(r"^(?:async\s+)?(?:function\s|const\s|let\s|var\s|class\s|/\*|\*|//|\})")
    for i, raw in enumerate(FEATURES.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if in_comment:
            if "*/" in line:
                in_comment = False
            continue
        if line.startswith("/*"):
            in_comment = "*/" not in line
            continue
        if line and not line.startswith("//") and depth == 0 and not decl.match(line):
            offenders.append((i, line))
        stripped = re.sub(r"//.*$", "", raw)
        depth += stripped.count("{") - stripped.count("}")
    assert depth == 0, f"花括号不配平（结束时深度 {depth}），文件可能被改坏"
    assert not offenders, (
        "顶层还有会在加载时执行的语句，加载顺序因此又是硬约束：\n  "
        + "\n  ".join(f"{i}: {t[:80]}" for i, t in offenders))


@needs_node
def test_the_kernel_actually_calls_into_the_extension_layer():
    """内核**真的调用了**注册函数，而不只是源码里出现过这几个字。

    第一版这里写的是 `assert "registerWorkbenchPalette?.(PALETTE)" in core`，
    变异一跑就现原形：把内核里那一行删掉，门禁照样绿——因为同一串字符也出现在
    我自己写的那段注释里。文本断言就是这样：它验证字符串出现过，不验证代码跑过。

    所以改成装探针：先在沙箱里放一个假的 registerWorkbenchPalette / bindWorkbenchDom
    记录自己被调用过，再把整条链装上、触发 init()，最后看探针有没有被叫到。
    init() 后面会抛（沙箱不是浏览器），但注册是它的第一件事，抛之前已经记下了。
    """
    expr = ("(() => {"
            " window.__called = []; window.__ready = [];"
            " window.addEventListener = (ev, fn) => {"
            "   if (ev === 'DOMContentLoaded') window.__ready.push(fn); };"
            " return 'armed';"
            " })()")
    d = Path(tempfile.mkdtemp())
    js = d / "probe.js"
    js.write_text(
        _CHAIN_LOADER.replace(
            "vm.createContext(sandbox);",
            "vm.createContext(sandbox);\n"
            "  vm.runInContext(" + json.dumps(expr) + ", sandbox);")
        + """
// 换掉 callee，而不是预埋 spy：workbench-features.js 里的函数**声明**会在链加载时
// 覆盖任何事先塞进去的同名值，预埋的探针根本活不到 init() 被调用。换掉之后，
// 记到的就是「init() 到底有没有去调它」。
(async () => {
  const called = [];
  vm.runInContext(
    "registerWorkbenchPalette = function () { __called.push('palette'); };"
    + "bindWorkbenchDom = function () { __called.push('dom'); };", sandbox);
  for (const fn of (sandbox.__ready || [])) { try { await fn(); } catch (e) { /* 沙箱不是浏览器，后面的错误与本门禁无关 */ } }
  called.push(...sandbox.__called);
  console.log('CALLED:' + JSON.stringify(called));
})();
""",
        encoding="utf-8")
    proc = subprocess.run(
        ["node", str(js), str(STATIC),
         json.dumps(_chain_from_index())],
        capture_output=True, text=True, timeout=120,
        encoding="utf-8", errors="replace")
    line = next((l for l in proc.stdout.splitlines() if l.startswith("CALLED:")), None)
    assert line, (
        "没能观测到内核是否调用了扩展层，探针没有回报：\n"
        + (proc.stdout[-800:] or proc.stderr[-800:]))
    called = json.loads(line[7:])
    assert "palette" in called, (
        "init() 没有调用 registerWorkbenchPalette——调色板永远装不上，"
        "版式页会悄悄退回内置模板（内核源码里可能还留着这几个字，但代码没跑）")
    assert "dom" in called, (
        "init() 没有调用 bindWorkbenchDom——本文件的 DOM 绑定全部装不上")


def test_index_still_loads_the_extension_file():
    """兜底：抽离或改名之后页面必须还在引用它。"""
    index = INDEX.read_text(encoding="utf-8")
    assert '<script src="/workbench-features.js">' in index


@needs_node
def test_all_three_palette_slots_are_registered():
    """三个槽位必须**全部**被替换，少一个就是半坏的形状。

    这条是被变异逼出来的。之前的门禁只检查「顶层没有副作用」，于是把
    `PALETTE.blocks = workbenchPaletteBlocks;` 单独删掉时，没有任何一条会红：
    版式页看起来完全正常，只有内容区和风格区悄悄退回内置实现。

    所以这里用一个探针 PALETTE 调一次注册函数，逐个槽位看有没有被换成新实现。
    探针的三个槽位都返回 'orig'，注册之后三者都必须不再返回它。

    比的是**身份**而不是返回值：这些 provider 依赖 fox-core 的 BLOCKS /
    miniOf，调用它们需要整个内核，而这条门禁要证明的恰恰是「不需要内核」。
    """
    expr = ("(() => {"
            " const o = { blocks: () => 'orig', layouts: () => 'orig', styles: () => 'orig' };"
            " const P = Object.assign({}, o);"
            " registerWorkbenchPalette(P);"
            " return JSON.stringify({"
            " blocks: P.blocks === o.blocks,"
            " layouts: P.layouts === o.layouts,"
            " styles: P.styles === o.styles });"
            " })()")
    result = json.loads(_load({"gallery": GALLERY, "memory": MEMORY}, [expr])[expr]["value"])

    assert not result["blocks"], "PALETTE.blocks 没被替换，内容区会退回内置积木"
    assert not result["layouts"], "PALETTE.layouts 没被替换，版式页会丢掉真实模板"
    assert not result["styles"], "PALETTE.styles 没被替换，风格页会丢掉真实案例"


@needs_node
def test_the_file_loads_before_the_kernel():
    """顺序无关的直接证明：把整条链换成「扩展层在前」照样装得上。

    改造之前这会立刻 ReferenceError——PALETTE 是 fox-core 的 const，值在
    workbench-features.js 被解析时还不存在。所以这条门禁自己造一个反过来的
    顺序，装的是 index.html 的那 13 个真脚本，不另造一套。

    链从 index.html 现读而不是写死：写死一份的话，「把扩展层提到最前」这个
    变异对门禁是不可见的，而它恰恰是最该被看见的那个。

    它只断言「装得上」。页面在那个顺序下是不是照样能用，由 e2e 覆盖；这里守的是
    更早的那道失效点——解析期就炸。
    """
    chain = _chain_from_index()
    assert "workbench-features.js" in chain
    swapped = ["workbench-features.js"] + [n for n in chain
                                           if n != "workbench-features.js"]

    for order, label in ((chain, "index.html 的真实顺序"),
                         (swapped, "扩展层被提到最前的顺序")):
        loaded = _load_chain(order)
        assert loaded is None, (
            f"{label}下整条前端链装不上，加载顺序仍是硬约束：\n{loaded}")
