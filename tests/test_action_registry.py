"""动作名必须唯一登记：HTML 引用的动作必须存在于派发表或真实实现里。

背景（S20 期间的真实缺陷）
----------------------------
`index.html` 此前用 44 个手写的 `function foo(){ return window.FoxBar.foo(); }`
转发函数，把 HTML/模板字符串里的 `onclick="foo(...)"` 接到 lifecycle 模块。
HTML 里的动作名与那份清单之间**没有任何编译期约束**：引用一个漏登记的名字，
只会在用户点击时抛 `ReferenceError`，而服务端、单元测试与 CI 全绿。
`intakeFetchBatch` 就是这样成了死按钮——「多 URL 批量」这条 v0.6.0 主线
能力在界面上完全不可达。

现在动作名集中在 `window.FoxActions`，本门禁在测试期静态校验每一个被引用的
动作名都能解析。漏登记会在 CI 上失败，而不是在用户点击时失败。
"""

from __future__ import annotations

import re
from pathlib import Path

STATIC = Path(__file__).resolve().parents[1] / "htmlninefox" / "server" / "static"

# 会触发用户动作的属性。其余属性（onchange / oninput / onpointerdown 等）
# 走各自的监听器或由模块自己处理，不走动作派发表。
ACTION_ATTR = re.compile(r'\bon(?:click|onchange|ondblclick)="([a-zA-Z_$][\w$]*)\s*\(')
# 真实的全局函数实现（不是转发 shim）
FUNCTION_DECL = re.compile(r"^\s*(?:async\s+)?function\s+([a-zA-Z_$][\w$]*)\s*\(", re.M)
# 派发表里的 key。箭头函数的参数可以带括号（`() =>`）也可以不带（`arg =>`），
# 两种都得认出来。
TABLE_KEY = re.compile(
    r"^\s*([a-zA-Z_$][\w$]*)\s*:\s*(?:\([^)]*\)|[a-zA-Z_$][\w$]*)\s*=>", re.M)
# 明确不是动作的调用
IGNORE = {"if", "for", "while", "switch", "catch", "function", "return"}

SCANNED = [
    "index.html", "classic.html", "motion-lab.html",
    "workbench-features.js", "canvas-productivity.js", "lifecycle-intake.js",
    "lifecycle-revisions.js", "lifecycle-generation.js", "lifecycle-exports.js",
    "lifecycle-slides.js", "lifecycle-projects.js", "workbench-ui.js",
    "interaction-system.js", "motion-system.js", "canvas-engine.js",
]


def _read(name: str) -> str:
    path = STATIC / name
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _registered_actions() -> set[str]:
    index = _read("index.html")
    table = index.split("window.FoxActions = {", 1)[1].split("\n};", 1)[0]
    return set(TABLE_KEY.findall(table))


def _real_functions() -> set[str]:
    names: set[str] = set()
    for name in SCANNED:
        names.update(FUNCTION_DECL.findall(_read(name)))
    return names


def test_action_registry_exists_and_is_not_empty() -> None:
    actions = _registered_actions()
    assert len(actions) >= 40, (
        f"派发表只登记了 {len(actions)} 个动作，预期覆盖原有 44 个转发函数；"
        f"实际：{sorted(actions)}")


def test_every_referenced_action_resolves() -> None:
    """任何被 HTML / 模板字符串引用的动作名，都必须能解析。"""
    registered = _registered_actions()
    defined = _real_functions() | registered
    missing: dict[str, list[str]] = {}
    for name in SCANNED:
        text = _read(name)
        for action in ACTION_ATTR.findall(text):
            if action in IGNORE or action in defined:
                continue
            missing.setdefault(action, []).append(name)
    assert not missing, (
        "以下动作名被 HTML/JS 引用但没有登记，点击时只会抛 ReferenceError"
        "（这正是 intakeFetchBatch 死按钮的形状）："
        + "; ".join(f"{k}（{', '.join(sorted(set(v)))}）" for k, v in sorted(missing.items())))


def test_registry_entries_point_at_real_fox_modules() -> None:
    """派发表条目原则上应委托给某个真实的 window.Fox* Module。

    例外是少数纯 UI 工具动作（打开文件选择器、新窗口打开）——它们没有
    领域行为可委托，硬塞进某个 Module 反而是错误的耦合。例外写在这里，
    新增时要说明理由，避免它变成万能豁免口。
    """
    non_module_ok = {
        "openZipPicker": "打开审核台的 ZIP 文件选择器，纯 DOM 触发，无领域行为",
        "openClassic": "新窗口打开 classic 静态页，纯导航，无领域行为",
    }
    index = _read("index.html")
    table = index.split("window.FoxActions = {", 1)[1].split("\n};", 1)[0]
    module_globals = {
        "window.FoxProjects", "window.FoxGeneration", "window.FoxRevisions",
        "window.FoxExports", "window.FoxIntake", "window.FoxSlides",
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
    pattern = re.compile(r'\bon(?:click|onchange|ondblclick)="[^"]*document\.[^"]*"')
    for name in SCANNED:
        text = _read(name)
        hits = pattern.findall(text)
        assert not hits, f"{name} 的动作属性里仍有内联 DOM 操作：{hits}"
