"""verify_portable 的内容断言必须指向**定义**所在的地方，不是提到它的地方。

它刚刚抓错了一次，而且是在最不该错的地方：v0.6.4 的 Windows 构建里，那
81,375 字符的内核已经被 C7 抽离到 static/fox-core.js，而断言还在 index.html
（`/`）上找 `window.FoxActions`。于是它拒绝认证一个完全正确的产物——而且理由是
「产物很可能是用陈旧源码打出来的」，这句话指向的完全是另一个方向。

同一份断言里还有一个更弱的写法：`intakeFetchBatch` 断言在 `/` 上，而那里只有
按钮的 onclick 属性写着这个名字，**函数本身在 workbench-features.js 里**。
这条断言证明了按钮写了名字，没证明函数存在——而那正是 v0.6 挖出的「死按钮」
形状：引用一个不存在的名字，所有测试全绿，只有用户点下去才发现。

所以这个文件守两件事：
  * 每条内容断言的标记，真的能在它断言的那个路由里找到
  * 每条标记，都断言在**定义**所在的地方——如果一个名字在 index.html 里只剩
    引用而定义在别处，断言必须跟着搬，否则它会在下一次搬动时给出错误结论
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

STATIC = ROOT / "htmlninefox" / "server" / "static"
INDEX = STATIC / "index.html"

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def _load_verify_portable():
    spec = importlib.util.spec_from_file_location(
        "fox_verify_portable", ROOT / "packaging" / "verify_portable.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_every_content_marker_actually_exists_where_it_is_asserted() -> None:
    """每条断言的标记，必须真的在它断言的那个路由对应的源文件里。

    这是那个 Windows 构建失败的直接教训：断言指向了一个标记已经不在的地方，
    于是它对一份好产物报错。断言本身必须先被验证它还成立。
    """
    module = _load_verify_portable()
    checked = 0
    broken: list[str] = []
    for route, markers in module.CONTENT_EXPECTATIONS:
        name = "/" if route == "/" else route.lstrip("/")
        path = INDEX if name == "/" else STATIC / name
        if not path.is_file():
            broken.append(f"{route} 对应的源文件不存在：{path}")
            continue
        body = path.read_text(encoding="utf-8", errors="replace")
        for marker in markers:
            checked += 1
            if marker not in body:
                broken.append(
                    f"{route} 断言含 {marker!r}，但 {path.name} 里没有它——"
                    f"这条断言会对着一个正确的产物报错")
    assert checked, "没有解析到任何内容断言，检查器本身可能失效了"
    assert not broken, "这些内容断言已经失效：\n  " + "\n  ".join(broken)


def test_a_name_is_asserted_where_it_is_defined_not_where_it_is_referenced() -> None:
    """「死按钮」形状的正面防守。

    如果 index.html 里只剩某个动作名的**引用**，而定义在别处，那么针对
    `/` 的断言就只能证明「按钮写了名字」——名字存在、函数不存在，按钮照旧是死的。
    """
    module = _load_verify_portable()
    index = INDEX.read_text(encoding="utf-8", errors="replace")
    other = {p.name: p.read_text(encoding="utf-8", errors="replace")
             for p in STATIC.glob("*.js") if p.name != "index.html"}

    referenced_only: list[str] = []
    for route, markers in module.CONTENT_EXPECTATIONS:
        if route != "/":
            continue
        for marker in markers:
            if marker not in index:
                continue          # 已经被上一条门禁报过了，不重复
            if re.search(rf"function\s+{re.escape(marker)}\b", index):
                continue          # 定义就在页面上，没问题
            # 这个名字在别处被定义了吗？
            for name, body in other.items():
                if re.search(rf"function\s+{re.escape(marker)}\b", body) \
                        or re.search(rf"\b{re.escape(marker)}\s*[:=]\s*(?:async\s*)?(?:\(|function)",
                                     body):
                    referenced_only.append(
                        f"{marker!r} 断言在 `/` 上，但它的定义在 {name} 里——"
                        f"这条断言只能证明按钮写了名字，证明不了函数存在")
                    break

    assert not referenced_only, "\n".join(referenced_only)


def test_the_extracted_kernel_is_a_served_route() -> None:
    """内核被抽成了独立文件，所以它必须是**被伺服出去的**路由。

    这一条在 C7 第一步就该加：抽离文件而不把它登记进 STATIC_FILES，页面会
    白屏而所有门禁全绿——那正是 v0.6.0 的形状。
    """
    module = _load_verify_portable()
    from htmlninefox.server import app as server_app

    assert "/fox-core.js" in server_app.STATIC_FILES, (
        "fox-core.js 没有登记进 STATIC_FILES——页面会 404 并白屏，"
        "而构建仍然是绿的")
    assert (STATIC / "fox-core.js").is_file(), "static/fox-core.js 不存在"
    assert '<script src="/fox-core.js">' in INDEX.read_text(encoding="utf-8"), \
        "index.html 没有引用 /fox-core.js"
    # and the marker this file asserts on is really in it
    assert "window.FoxActions" in (STATIC / "fox-core.js").read_text(encoding="utf-8")


def test_stale_routes_are_not_asserted() -> None:
    """断言里的路由必须都在 STATIC_ROUTES 或期望表里被真正取到过。

    verify_content 按 CONTENT_EXPECTATIONS 的路由去 fetch，路由写错会 404，
    而 fetch 到 404 的响应体里当然没有那些标记——报错信息会指向「产物陈旧」，
    而真正的原因是断言写错了路由。
    """
    module = _load_verify_portable()
    from htmlninefox.server import app as server_app

    for route, _ in module.CONTENT_EXPECTATIONS:
        if route == "/":
            continue
        assert route.lstrip("/") or True
        name = route.lstrip("/")
        assert (STATIC / name).is_file(), \
            f"内容断言引用了不存在的静态文件：{route}"
        assert route in server_app.STATIC_FILES, (
            f"内容断言引用了 {route}，但它没有登记进 STATIC_FILES——"
            f"运行时取到的是 404")
