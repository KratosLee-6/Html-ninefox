"""Hand-maintained lists must still describe what is actually there.

Three incidents in this session had one shape: a list of names, maintained by
hand, with nothing checking it. Each failed differently and each failed quietly.

  * tests/test_action_registry.py kept a `SCANNED` list of front-end files.
    fox-core.js was extracted into static/ and not added, so the gate scanned
    one file fewer and stayed green. Nothing reported the narrowing.
  * packaging/verify_portable.py asserted markers against `/`, which stopped
    being true when the kernel moved to static/fox-core.js. It refused a correct
    Windows package at release time, naming a cause that had nothing to do with
    it.
  * tests/test_release_asset_metadata.py held a hard-coded tuple of tags, so
    every new release shipped unexamined until someone remembered to edit it.

The first attempt at catching these generically scanned every string literal in
tests/ and packaging/ for an asset suffix. It reported 13 false positives out of
161 — drive.js, chain.js, body.html, a glob — every one of them a filename a
test writes into a temp directory at runtime. A gate that cries wolf on thirty
findings teaches people to ignore it, which is worse than having none.

What survives contact with the tree is narrower and split in two:

  * module-level constants whose **majority** of entries look like static
    assets. Runtime temp paths are literals inside functions, never module
    constants, so they never enter the candidate set at all. Measured: two
    lists, zero false positives.
  * for each such list, both directions that are meaningful: no entry may
    dangle, and a route-shaped entry must actually be served.

Completeness is not inferred, it is declared. `EXHAUSTIVE` below names the lists
that claim to cover everything; only those get the "nothing may be missing"
check, because a sampled list and an exhaustive one fail in opposite ways and
guessing which is which would be the same mistake again.
"""
from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

STATIC = ROOT / "htmlninefox" / "server" / "static"
ASSET_SUFFIXES = (".js", ".css", ".html", ".svg", ".webmanifest")
SCANNED_DIRS = ("tests", "packaging")

# Lists that claim to cover every front-end asset of their kind. Completeness is
# declared here rather than guessed at, because a sampled list and an exhaustive
# one fail in opposite directions.
EXHAUSTIVE: dict[str, tuple[str, ...]] = {
    "test_action_registry.py": ("SCANNED",),
}

# Front-end files that are legitimately outside SCANNED's claim. sw.js is a
# service worker: it has no onclick and no action wiring, so a gate that scans
# for actions has nothing to look for in it, and listing it would be noise.
EXHAUSTIVE_EXCLUDE: dict[str, tuple[tuple[str, str], ...]] = {
    "test_action_registry.py": (("sw.js", "service worker，没有动作属性"),),
}


def _excluded(file_name: str) -> set[str]:
    return {name for name, _ in EXHAUSTIVE_EXCLUDE.get(file_name, ())}

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def _module_constants(path: Path) -> dict[str, list[str]]:
    """Module-level names bound to a list/tuple whose items are all strings."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, OSError):
        return {}
    out: dict[str, list[str]] = {}
    for node in tree.body:
        name = value = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name):
            name, value = node.targets[0].id, node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) \
                and node.value is not None:
            name, value = node.target.id, node.value
        if not name or not isinstance(value, (ast.List, ast.Tuple)):
            continue
        items = [e.value for e in value.elts
                 if isinstance(e, ast.Constant) and isinstance(e.value, str)]
        if items and len(items) == len(value.elts):
            out[name] = items
    return out


def _asset_lists() -> list[tuple[str, str, list[str]]]:
    """(file, constant, entries) for every module-level asset-looking list.

    Entries are returned **verbatim**, leading slash and all. An earlier version
    stripped the basename here, which quietly emptied the route-shaped half of
    every list and left `test_route_shaped_entries_are_actually_served`
    skipping forever. A gate that always skips is the exact quiet pass this
    file exists to prevent, and it looked fine in the output — "2 skipped" sat
    there unexamined.

    A bare suffix such as ".js" and a glob such as "*.js" are not file names and
    must not be treated as entries — the first version of this file listed its
    own ASSET_SUFFIXES constant as a dangling reference.
    """
    found = []
    for directory in SCANNED_DIRS:
        for path in sorted((ROOT / directory).glob("*.py")):
            for name, items in _module_constants(path).items():
                entries = [i for i in items
                           if not i.startswith(".") and "*" not in i]
                looks = [i.split("/")[-1] for i in entries
                         if i.split("/")[-1].endswith(ASSET_SUFFIXES)]
                if looks and len(looks) * 2 >= len(entries):
                    found.append((path.name, name, entries))
    return found


def _static_names() -> set[str]:
    return {p.name for p in STATIC.iterdir() if p.is_file()}


def _served_routes() -> set[str]:
    """The URL paths the product actually serves.

    The route names are the **keys** of STATIC_FILES, not its values. "/motion-lab"
    is a route that serves motion-lab.html, and the first version of this
    function collected the filenames, so every alias route looked unserved.
    The three page routes handled directly in `_get` are added by hand.
    """
    from htmlninefox.server import app as server_app
    served = {f"/{name}" for name in server_app.STATIC_FILES}
    served |= {"/", "/classic", "/motion-lab"}
    return served


def test_the_discovery_finds_the_lists_it_is_meant_to_find() -> None:
    """A discovery rule that quietly stops discovering protects nothing.

    Pinning the count and the names makes "the scan found nothing" an explicit
    failure rather than a pass — which is the exact failure mode this file is
    about. If someone legitimately restructures a list, this fails and says so.
    """
    found = {(f, n) for f, n, _ in _asset_lists()}
    expected = {("test_action_registry.py", "SCANNED"),
                ("verify_portable.py", "STATIC_ROUTES")}
    missing = expected - found
    assert not missing, (
        f"发现规则没有找到这些已知清单：{sorted(missing)}。"
        f"实际找到：{sorted(found)}\n"
        f"规则本身退化了，它现在保护不了任何东西。")


@pytest.mark.parametrize("file_name, const_name, entries", _asset_lists(),
                         ids=[f"{f}::{n}" for f, n, _ in _asset_lists()])
def test_no_entry_in_a_hand_maintained_list_dangles(
        file_name: str, const_name: str, entries: list[str]) -> None:
    """清单里写着的**文件**必须真的在 static/ 里。

    这一条挡住「断言指向了一个标记已经不在的位置」——v0.6.4 的 Windows 构建
    就是被这种断言挡住的，而产物完全正确。

    只查带资源后缀的条目。`/motion-lab` 这类没有后缀的条目是路由而不是文件，
    它们归下一条门禁管；把它们也当文件名去比，会得到一堆假警报。
    """
    present = _static_names()
    files = [e for e in entries if e.endswith(ASSET_SUFFIXES)]
    if not files:
        pytest.skip(f"{const_name} 里没有文件形态的条目")
    dangling = sorted({e for e in files if e.split("/")[-1] not in present})
    assert not dangling, (
        f"{file_name} 的 {const_name} 列了这些文件，但 static/ 里没有：{dangling}。"
        f"要么它已被移走或改名，要么这个清单该删掉这一条。")


@pytest.mark.parametrize("file_name, const_name, entries", _asset_lists(),
                         ids=[f"{f}::{n}" for f, n, _ in _asset_lists()])
def test_route_shaped_entries_are_actually_served(
        file_name: str, const_name: str, entries: list[str]) -> None:
    """形如 `/x.js` 的条目，必须是产品真的伺服得出来的路由。

    否则清单会去取一个 404 路由的内容，然后发现里面没有那些标记——报错会指向
    「产物陈旧」，而真正的原因是这条路由写错了。
    """
    served = _served_routes()
    # A route-shaped entry is one written with a leading slash and no asset
    # suffix: "/workbench-system.css" names both a route and a file, while
    # "/motion-lab" is a route serving motion-lab.html under a different name.
    routes = [e for e in entries
              if e.startswith("/") and not e.endswith(ASSET_SUFFIXES)]
    if not routes:
        pytest.skip(f"{const_name} 里没有路由别名的条目")
    unknown = [r for r in routes if r not in served]
    assert not unknown, (
        f"{file_name} 的 {const_name} 引用了这些路由，但服务端没有伺服它们："
        f"{unknown}。取它们只会拿到 404，"
        f"而报错会误导成「产物是用陈旧源码打出来的」。")


def test_declared_exhaustive_lists_have_not_fallen_behind() -> None:
    """声明为「覆盖全部」的清单，不许漏掉任何前端资产。

    这一条是三次事故里最安静的那次的解药：test_action_registry.SCANNED 在
    fox-core.js 被抽出来时没有跟着加，于是那条门禁**扫描范围缩小了一格**，
    依然是绿的——没有任何东西说得出它漏了。

    与「不悬空」正好相反：一个只查不悬空的门禁永远抓不到这一种。
    """
    present = _static_names()
    skip = _excluded("test_action_registry.py")
    # SCANNED claims every page and every feature script the product serves
    covered = {"index.html", "classic.html", "motion-lab.html"}
    covered |= {n for n in present if n.endswith(".js")} - skip
    gone = sorted(n for n in covered if n not in present)
    assert not gone, f"static/ 里这些前端脚本/页面不见了：{gone}"

    constants = {n: items for n, items in
                 _module_constants(ROOT / "tests" / "test_action_registry.py").items()}
    scanned = {i.split("/")[-1] for i in constants.get("SCANNED", [])}
    missing = sorted(covered - scanned)
    assert not missing, (
        f"static/ 里有这些前端脚本/页面，但 test_action_registry.SCANNED 没有收录："
        f"{missing}\n"
        f"后果不是它会报错，而是它**扫得更少却依然全绿**——"
        f"漏掉的那个文件从此不受任何门禁检查。")


def test_every_static_file_is_either_served_or_declared() -> None:
    """反向不变量：static/ 里的每个文件都要么被伺服，要么被显式声明为不发。

    这是 v0.6.0 的形状：文件写好了、提交了，页面也引用了，而服务端没有登记
    路由——白屏，而构建全绿。往前加一个文件而不登记，就是这个形状。
    """
    from htmlninefox.server import app as server_app
    served_files = {e[0] for e in server_app.STATIC_FILES.values()}
    served_files |= {"index.html", "classic.html", "motion-lab.html"}
    declared_unserved = set(_declared_unserved())
    orphans = sorted({p.name for p in STATIC.iterdir()
                      if p.is_file()} - served_files - declared_unserved)
    assert not orphans, (
        f"static/ 里这些文件既没有路由伺服，也不在 DELIBERATELY_UNSERVED 里"
        f"声明为刻意不发：{orphans}\n"
        f"要么把它们登记进 app.py 的 STATIC_FILES，要么显式声明不发。")


def _declared_unserved() -> list[str]:
    """Read the declaration from the payload gate rather than restating it."""
    from tests.test_package_payload import DELIBERATELY_UNSERVED
    return list(DELIBERATELY_UNSERVED)