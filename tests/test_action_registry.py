"""点击动作必须唯一登记且经统一委托：data-action 不可逃逸。

背景（S20 期间的真实缺陷）
----------------------------
`index.html` 曾用 44 个手写转发函数把 `onclick="foo(...)"` 接到 lifecycle
模块，动作名与实现之间没有任何编译期约束——引用一个漏登记的名字，只在
用户点击时抛 ReferenceError，而服务端、单元测试与 CI 全绿。`intakeFetchBatch`
就是这样成了死按钮。

v0.6 把动作名收进 `window.FoxActions`；v0.7.8（C6 收口）进一步把全部
内联 onclick 迁到 `data-action` + document 级事件委托：data-* 取值是
字符串而节点 id 是数字（=== 会失效），类型转换因此收敛到
fox-core.js 的 FOX_ACTION_SIGNATURES——声明即契约，本文件静态锁住：

  1. onclick 归零（注释除外）——回流即红；
  2. 每个 data-action 都能解析到派发表或裸全局函数；
  3. 带参数的 data-action 必须有签名，且站点的 data-* 键与签名完全一致
     （双向）——多站一个键、少声明一个类型都是失配；
  4. 派发表条目委托给真实的 Fox* Module（少数纯 UI 工具动作例外并说明理由）。
"""

from __future__ import annotations

import re
from pathlib import Path

STATIC = Path(__file__).resolve().parents[1] / "htmlninefox" / "server" / "static"

# 委托动作属性；ondblclick/onpointerdown/onkeydown 等仍内联（指针/键盘层，
# 见 ROADMAP C6 注记），但同样受「引用必须可解析」约束。
DATA_ACTION = re.compile(r'data-action="([a-zA-Z_$][\w$]*)"')
DATA_ATTR = re.compile(r'data-([a-zA-Z][\w-]*)=')
ACTION_ATTR = re.compile(r'\bon(?:click|onchange|ondblclick)="([a-zA-Z_$][\w$]*)\s*\(')
FUNCTION_DECL = re.compile(r"^\s*(?:async\s+)?function\s+([a-zA-Z_$][\w$]*)\s*\(", re.M)
TABLE_KEY = re.compile(
    r"^\s*([a-zA-Z_$][\w$]*)\s*:\s*(?:\([^)]*\)|[a-zA-Z_$][\w$]*)\s*=>", re.M)
SIGNATURE_KEY = re.compile(r"^\s*([a-zA-Z_$][\w$]*)\s*:\s*\{", re.M)
IGNORE = {"if", "for", "while", "switch", "catch", "function", "return"}

SCANNED = [
    "index.html", "classic.html", "motion-lab.html",
    "fox-core.js",
    "workbench-features.js", "canvas-productivity.js", "lifecycle-intake.js",
    "lifecycle-revisions.js", "lifecycle-generation.js", "lifecycle-exports.js",
    "lifecycle-slides.js", "lifecycle-projects.js", "workbench-ui.js",
    "interaction-system.js", "motion-system.js", "canvas-engine.js",
]

TABLE_MARKER = "window.FoxActions = {"
SIGNATURES_MARKER = "const FOX_ACTION_SIGNATURES = {"


def _read(name: str) -> str:
    path = STATIC / name
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _strip_js_comments(text: str) -> str:
    """剥掉 /* *​/ 块注释与行注释——门禁针对代码，不针对讲解文字。"""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return re.sub(r"^\s*//.*$", "", text, flags=re.M)


def _action_table() -> str:
    for name in SCANNED:
        text = _read(name)
        if TABLE_MARKER in text:
            return text.split(TABLE_MARKER, 1)[1].split("\n};", 1)[0]
    raise AssertionError(
        f"没有任何被扫描的文件定义 {TABLE_MARKER}——派发表被删掉或搬到了未登记的文件；"
        f"已扫描：{SCANNED}")


def _signatures() -> dict[str, list[str]]:
    """FOX_ACTION_SIGNATURES：动作 → 参数键列表（声明顺序）。"""
    for name in SCANNED:
        text = _read(name)
        if SIGNATURES_MARKER in text:
            body = text.split(SIGNATURES_MARKER, 1)[1].split("\n};", 1)[0]
            result: dict[str, list[str]] = {}
            for entry in re.findall(
                    r"([a-zA-Z_$][\w$]*)\s*:\s*\{(.*?)\}", body, re.S):
                keys = re.findall(r"([a-zA-Z_$][\w$]*)\s*:\s*'", entry[1])
                result[entry[0]] = keys
            return result
    raise AssertionError(
        f"找不到 {SIGNATURES_MARKER}——委托分派的类型契约被删除（C6 回归）")


def _registered_actions() -> set[str]:
    return set(TABLE_KEY.findall(_action_table()))


def _real_functions() -> set[str]:
    names: set[str] = set()
    for name in SCANNED:
        names.update(FUNCTION_DECL.findall(_read(name)))
    return names


def _camel(data_key: str) -> str:
    parts = data_key.split("-")
    return parts[0] + "".join(p.title() for p in parts[1:])


def test_action_registry_exists_and_is_not_empty() -> None:
    actions = _registered_actions()
    assert len(actions) >= 50, (
        f"派发表只登记了 {len(actions)} 个动作；实际：{sorted(actions)}")


def test_inline_onclick_is_gone():
    """C6 终态：内联 onclick 全部迁到 data-action 委托。

    onclick 字符串靠全局名解析、无类型契约、无法静态校验参数——留一处
    就是一处逃生口。注释里的提法不算（先剥注释再查）。"""
    for name in SCANNED:
        text = _strip_js_comments(_read(name))
        hits = re.findall(r'onclick="', text)
        assert not hits, (
            f"{name} 仍有 {len(hits)} 处内联 onclick——点击动作必须走 "
            f"data-action 委托（C6）；{hits[:3]}")


def test_every_delegated_action_resolves() -> None:
    """任何 data-action 引用的动作名，都必须能解析到派发表或全局函数。"""
    registered = _registered_actions()
    defined = _real_functions() | registered
    missing: dict[str, list[str]] = {}
    for name in SCANNED:
        text = _strip_js_comments(_read(name))
        for action in DATA_ACTION.findall(text):
            if action in IGNORE or action in defined:
                continue
            missing.setdefault(action, []).append(name)
    assert not missing, (
        "以下 data-action 引用的动作名没有登记，点击时只会得到控制台报错"
        "（intakeFetchBatch 死按钮的形状）："
        + "; ".join(f"{k}（{', '.join(sorted(set(v)))}）" for k, v in sorted(missing.items())))


def test_action_argument_sites_match_signatures_exactly():
    """带参数的 data-action 必须有签名，且站点 data-* 键与签名键双向一致。

    站点多给一个 data-foo 而签名没有 → 静默丢参；签名声明了键而站点没给
    → undefined/NaN 进动作。两头都在 CI 拦住，而不是用户点击时。
    按元素开标签扫描（而非按行），同一行的兄弟元素互不串扰。data-icon /
    data-intake-filter / data-page-id 是**元素状态标记**（图标装饰、审核台
    筛选态高亮、预览页高亮，被 querySelector/样式逻辑读取），不是分派参数。"""
    signatures = _signatures()
    state_markers = {"action", "icon", "intakeFilter", "pageId"}
    sites: dict[str, set[str]] = {}
    for name in SCANNED:
        text = _strip_js_comments(_read(name))
        for tag in re.findall(r"<[^<>]*\bdata-action=\"[a-zA-Z_$][\w$]*\"[^<>]*>", text):
            for action in DATA_ACTION.findall(tag):
                keys = {_camel(k) for k in DATA_ATTR.findall(tag)} - state_markers
                sites.setdefault(action, set()).update(keys)
    problems: list[str] = []
    for action, keys in sorted(sites.items()):
        declared = set(signatures.get(action, []))
        if not keys and not declared:
            continue  # 无参动作，无需签名
        if keys - declared:
            problems.append(f"{action}: 站点用了 {sorted(keys - declared)}，签名未声明")
        if declared - keys:
            problems.append(f"{action}: 签名声明了 {sorted(declared - keys)}，站点从未使用")
    assert not problems, (
        "data-action 参数与 FOX_ACTION_SIGNATURES 失配（字符串→类型的唯一"
        f"转换点失效）：{problems}")


def test_every_signature_is_actually_delegated():
    declared = set(_signatures())
    used = set()
    for name in SCANNED:
        used.update(DATA_ACTION.findall(_strip_js_comments(_read(name))))
    dead = sorted(declared - used)
    assert not dead, (
        f"签名表里这些动作没有任何 data-action 站点使用：{dead}——"
        f"死声明让契约变成装饰")


def test_registry_entries_point_at_real_fox_modules() -> None:
    """派发表条目原则上应委托给某个真实的 window.Fox* Module。

    例外是少数纯 UI 工具动作（打开文件选择器、新窗口打开、内核相机工具）
    ——它们没有领域行为可委托，硬塞进某个 Module 反而是错误的耦合。
    例外写在这里，新增时要说明理由，避免它变成万能豁免口。"""
    non_module_ok = {
        "openZipPicker": "打开审核台的 ZIP 文件选择器，纯 DOM 触发，无领域行为",
        "openClassic": "新窗口打开 classic 静态页，纯导航，无领域行为",
        "zoomIn": "放大画布——内核相机工具 zoomBy 的语义别名，无领域模块可去",
        "zoomOut": "缩小画布——同上",
    }
    table = _action_table()
    module_globals = {
        "window.FoxProjects", "window.FoxGeneration", "window.FoxRevisions",
        "window.FoxExports", "window.FoxIntake", "window.FoxSlides",
        "window.FoxCanvasProductivity",
    }
    offenders: list[str] = []
    for name, target in re.findall(
        r"([a-zA-Z_$][\w$]*)\s*:\s*(?:\([^)]*\)|[a-zA-Z_$][\w$]*)\s*=>\s*([^\n]*)", table
    ):
        target = target.strip()
        if any(target.startswith(mod) for mod in module_globals):
            continue
        if name in non_module_ok:
            continue
        offenders.append(f"{name} -> {target}")
    assert not offenders, (
        f"派发表里这些条目既没委托给 Fox* Module，也没登记为有理由的例外：{offenders}；"
        f"如确实是纯 UI 工具，请加进 non_module_ok 并写明理由")


def test_no_inline_dom_pokes_in_action_attributes() -> None:
    """动作属性里不应再出现 document.querySelector(...).click() 这类内联 DOM 操作。"""
    pattern = re.compile(
        r'\b(?:data-action="[^"]*"|on(?:click|onchange|ondblclick)="[^"]*")'
        r"[^>]*document\.")
    for name in SCANNED:
        text = _strip_js_comments(_read(name))
        hits = pattern.findall(text)
        assert not hits, f"{name} 的动作属性里仍有内联 DOM 操作：{hits}"
