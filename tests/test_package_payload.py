"""打包载荷门禁：static/ 的每一个文件都必须真的出现在构建产物的文件清单里。

要堵的洞
--------
`htmlninefox/server/static/` 靠 `pyproject.toml` 里手写的
`[tool.setuptools.package-data]` 正则白名单进包。v0.6.3 刚往 `static/` 加了
`fox-core.js`（从 index.html 抽离出来的前端内核），`.js` 恰好在白名单里所以没出事。
但「恰好」不是保证：下一个新文件格式或子目录随时可能匹配不上，而匹配不上的后果
是用户下载到的包前端全废、**所有门禁全绿**。

第二条独立的失效：白名单匹配到了文件，但 `app.py` 的 `STATIC_FILES` 没登记，
路由 404，工作台同样全废。这两件事互不相干，所以下面各有各的门禁。

纪律
----
门禁真的把 wheel 打出来（`scripts/verify_package_payload.py` 调 PEP 517 后端）、
真的打开 zip、逐个文件比对**清单与字节**。不扫描 `pyproject.toml` 文本再 grep
pattern——那验证的是文本形状，一行注释就能满足它。

这里刻意**不**采信验证脚本的结论：脚本与本文件各自独立比对一遍同一个 zip。
单点的判断被破坏时，两边不会一起变绿。代价是十来行重复比对，换的是门禁不会因为
报告工具被改弱而失效。
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "htmlninefox" / "server" / "static"
INDEX_HTML = STATIC_DIR / "index.html"
VERIFIER = ROOT / "scripts" / "verify_package_payload.py"
GATE_REL = "tests/test_package_payload.py"
WORKFLOWS = ROOT / ".github" / "workflows"
WHEEL_STATIC_PREFIX = "htmlninefox/server/static/"

SCRIPT_SRC = re.compile(r"""<script[^>]*\ssrc\s*=\s*["']([^"']+)["']""", re.I)

# 刻意不进包也不发出去的静态文件，附带理由。新增条目必须写理由。
#
# 为什么需要这张表而不是「全都发出去」：`pixel-garden-tokens.css` 的文件头
# 明确声明它是品牌色值参考表、**没有任何消费者**，生成器从不 @import 它。
# 把它登记进 STATIC_FILES 反而是把一个刻意不参与产品的文件暴露出去。
#
# 为什么不能放任不管：它在 `static/` 里、跟着 `*.css` 进了包，于是看起来一切
# 正常——直到有人把文件头那句「没有接入生成链路」改成「已接入」，那天它就会
# 404，而没有任何门禁会说一个字。这张表把「不发」变成一个需要理由的决定，
# 于是新增一个漏登记的文件仍然会红。
DELIBERATELY_UNSERVED = {
    "pixel-garden-tokens.css":
        "文件头声明为品牌色参考表，生成器从不 @import；见该文件第 5-14 行",
}

# 路由表是穷尽的：app.py 的 _get 里，除下面的字面路由外只认 STATIC_FILES。
LITERAL_ROUTES = {"/": "index.html", "/classic": "classic.html"}


def _build_wheel(out_dir: Path) -> Path:
    """真的构建一个 wheel。走 subprocess 隔离，报告脚本不污染 pytest 进程。

    helper 脚本落地成文件而不是 `python -c`：本机 PowerShell 5.1 会把 `-c` 里的
    引号剥掉，内联代码到 Windows 上就会被拆碎。
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [sys.executable, str(VERIFIER), "--build-wheel", str(out_dir)],
        cwd=ROOT, capture_output=True, text=True, timeout=600,
        # 控制台是 GBK，不显式给 encoding 会让 proc.stdout 变 None，
        # 看起来像静默通过。
        encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    assert proc.returncode == 0, (
        f"构建 wheel 失败（rc={proc.returncode}）：\n{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}")
    lines = [l for l in proc.stdout.splitlines() if l.startswith("WHEEL=")]
    assert lines, f"构建脚本没有回报 wheel 文件名：\n{proc.stdout[-2000:]}"
    return out_dir / lines[-1].split("=", 1)[1]


@pytest.fixture(scope="session")
def wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """session 级：一次构建，六条断言共用同一个产物。"""
    out = tmp_path_factory.mktemp("payload-wheel")
    return _build_wheel(out)


@pytest.fixture(scope="session")
def shipped(wheel: Path) -> dict[str, bytes]:
    """wheel 里 server/static/ 下的内容：{相对 static 的路径: 字节}。"""
    with zipfile.ZipFile(wheel) as archive:
        out: dict[str, bytes] = {}
        for name in archive.namelist():
            if name.startswith(WHEEL_STATIC_PREFIX) and not name.endswith("/"):
                out[name[len(WHEEL_STATIC_PREFIX):]] = archive.read(name)
        return out


def _source_static_files() -> list[str]:
    """static/ 下真实存在的文件，递归。

    递归是有意的：白名单是 `server/static/*.js` 这类平铺 pattern，一旦有人加了
    子目录（字体、图标集），平铺 pattern 不会递归覆盖，而那正是要抓的形状。
    """
    files = []
    for path in STATIC_DIR.rglob("*"):
        if path.is_dir() or "__pycache__" in path.parts:
            continue
        files.append(path.relative_to(STATIC_DIR).as_posix())
    return sorted(files)


def test_every_static_file_ships_in_the_built_wheel(shipped: dict[str, bytes]) -> None:
    """static/ 下每一个真实存在的文件都在 wheel 的清单里，且内容逐字节一致。

    为什么必须是产物而不是源码：服务器测试跑的是仓库里的源码树，它对
    package-data 完全无感。`fox-core.js` 可以写好、放好、被十几个测试引用，
    同时**进不了 wheel**——而这条门禁是唯一会在发布前发现这件事的地方。
    """
    wanted = _source_static_files()
    assert wanted, f"{STATIC_DIR} 下一个文件都没有，门禁失去意义"

    missing = [name for name in wanted if name not in shipped]
    assert not missing, (
        f"{len(missing)}/{len(wanted)} 个静态文件存在于仓库却没进 wheel，"
        f"用户下载到的包前端会缺件（检查 pyproject.toml 的 package-data 白名单）：\n  "
        + "\n  ".join(missing))

    changed = []
    for name in wanted:
        expect = (STATIC_DIR / name).read_bytes()
        got = shipped[name]
        if got != expect:
            head = got[:60].decode("utf-8", "replace").replace("\n", " ")
            changed.append(f"{name}：wheel {len(got)} 字节 / 仓库 {len(expect)} 字节，"
                           f"开头 {head!r}")
    assert not changed, (
        "以下静态文件在 wheel 里的字节与仓库不一致——产物很可能是用陈旧源码打出来的：\n  "
        + "\n  ".join(changed))


def test_every_script_the_page_asks_for_is_packaged_and_registered(
        shipped: dict[str, bytes]) -> None:
    """index.html 的每一个 <script src>：文件在 static/、在 STATIC_FILES、进得了包。

    三处缺任何一处都是同一个用户可见后果（白页或 404），而三者的失效原因互不
    相关：package-data 是手写正则，STATIC_FILES 是手写字典，页面是手写 HTML。
    只查其中一处，另外两处照样能把工作台打废。

    STATIC_FILES 作为**运行时对象**读，不是把 app.py 当文本 grep。
    """
    from htmlninefox.server import app as server_app

    page = INDEX_HTML.read_text(encoding="utf-8")
    srcs = sorted({s for s in SCRIPT_SRC.findall(page)
                   if s.startswith("/") and not s.startswith("//")})
    assert srcs, "index.html 没有引用任何外部脚本，门禁失去意义"

    absent, unregistered, misdirected, unpackaged, corrupt = [], [], [], [], []
    for src in srcs:
        filename = src.rsplit("/", 1)[-1]
        if not (STATIC_DIR / filename).is_file():
            absent.append(f"{src} -> static/{filename} 不存在")
            continue
        entry = server_app.STATIC_FILES.get(src)
        if entry is None:
            unregistered.append(src)
        elif entry[0] != filename:
            misdirected.append(f"{src} -> STATIC_FILES 指向 {entry[0]}")
        if filename not in shipped:
            unpackaged.append(f"{src} -> static/{filename} 没进 wheel")
        elif shipped[filename] != (STATIC_DIR / filename).read_bytes():
            corrupt.append(src)

    problems = ([f"文件不存在：{x}" for x in absent]
                + [f"未登记进 app.py 的 STATIC_FILES（线上必然 404）：{x}"
                   for x in unregistered]
                + [f"白名单指错文件：{x}" for x in misdirected]
                + [f"没进 wheel：{x}" for x in unpackaged]
                + [f"wheel 里的字节与仓库不一致：{x}" for x in corrupt])
    assert not problems, (
        f"index.html 请求的 {len(srcs)} 个脚本有三处对不上：\n  " + "\n  ".join(problems))


def test_every_static_file_is_either_served_or_declared_unserved() -> None:
    """static/ 里不存在「既发不出去、也没人声明过」的文件。

    前两条门禁只覆盖 index.html 请求的脚本。剩下的文件——图标、CSS、
    webmanifest——没有任何测试问过服务端到底给不给得出。缺了这条，一个
    放进 static/、跟着白名单进了包、却没人登记的文件会一直安静地 404。

    同时反过来检查声明表：如果某个「刻意不发」的文件其实已经被登记了，
    说明当初的理由已经不成立，门禁要逼人来更新这张表，而不是让两套说法并存。
    """
    from htmlninefox.server import app as server_app

    served = dict(LITERAL_ROUTES)
    for path, entry in server_app.STATIC_FILES.items():
        served[path] = entry[0]
    served_filenames = set(served.values())

    on_disk = {p.name for p in STATIC_DIR.iterdir() if p.is_file()}

    unreachable = sorted(on_disk - served_filenames - set(DELIBERATELY_UNSERVED))
    assert not unreachable, (
        "这些静态文件在仓库里、也跟着进了包，但服务端没有任何路由会发它们，"
        "任何引用都是 404：\n  " + "\n  ".join(unreachable)
        + "\n如果这是刻意的（例如没有消费者的参考表），把它加进 "
          "DELIBERATELY_UNSERVED 并写明理由；否则登记进 app.py 的 STATIC_FILES。")

    stale = sorted(f for f in DELIBERATELY_UNSERVED if f in served_filenames)
    assert not stale, (
        f"这些文件在 DELIBERATELY_UNSERVED 里声明「不发」，但服务端其实有路由："
        f"{stale}。当初的理由已经不成立，请更新声明表。")

    missing = sorted(set(DELIBERATELY_UNSERVED) - on_disk)
    assert not missing, (
        f"DELIBERATELY_UNSERVED 里的文件已经不在 static/ 了：{missing}；"
        f"删掉这些条目，否则这张表会逐渐变成一份没人核对的清单")

    for name, reason in DELIBERATELY_UNSERVED.items():
        assert reason.strip(), f"{name} 的「刻意不发」理由是空的"
    """门禁只有跑在发布流水线里才算数。

    与 tests/test_smoke_success_paths.py 里 verify_portable.py 那条同形：v0.6.0 的
    产物通过了全部构建 job 与全部测试，一启动就崩，正是因为「能验证」的那道检查
    从来没被接进流水线。
    """
    assert VERIFIER.exists(), "缺少 scripts/verify_package_payload.py"
    assert (ROOT / GATE_REL).exists(), f"缺少 {GATE_REL}"
    wired = [p.name for p in WORKFLOWS.glob("*.yml")
             if "verify_package_payload.py" in p.read_text(encoding="utf-8")]
    assert wired, ("verify_package_payload.py 没有接进任何 workflow——"
                   "这道门禁在发布前不会运行")
