"""环境动效门禁：「墨水落纸」层必须在、必须可关、必须不吞内容。

v0.7.x 设计升级（方法论：impeccable 的 animate/audit + shaders 的材质
语言）给六类渲染器加了共享动效层（generators/_shared.py）：

  * fox-ambient 光带呼吸（focal moment 的环境部分，只动 background-position）；
  * fox-ink-in 墨水标题（700ms focal entrance）；
  * fox-reveal 卡片滚动显形（stagger cap 360ms）；
  * fox-cursor-glow 光标辉光（仅 pointer:fine）；
  * prefers-reduced-motion / print / 导出 settle 三条「终态」通路。

门禁分两层：

  结构层（渲染产物内容）：六类输出都必须携带完整动效资产，
  reduced-motion 块必须把所有动画元素归为静态终态。

  行为层（真实浏览器）：reduced-motion 仿真下所有卡片立即可见；
  正常模式下滚动触发显形；导出 settle 后整页无隐藏元素。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from htmlninefox.generators import _tokens, render  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

INTENTS = ["landing", "dashboard", "deck", "poster", "archdoc", "doc"]
BRIEF = {"brief": {"brand": "狐构", "headline": "把想法变成可交付的成果"}}
PRESET = dict(_tokens.get_preset(_tokens.DEFAULT_PRESET))


@pytest.mark.parametrize("intent", INTENTS)
def test_ambient_assets_present(intent):
    """六类输出都必须携带完整动效资产。"""
    html = render(intent, BRIEF, PRESET, {})
    for needle, label in (
        ('class="fox-ambient"', "光带环境层"),
        ("fox-ambient-drift", "光带呼吸 keyframes"),
        ("fox-ink-drop", "墨水标题 keyframes"),
        ("fox-reveal", "滚动显形"),
        ("fox-cursor-glow", "光标辉光"),
        (":focus-visible", "键盘焦点环"),
        ("IntersectionObserver", "显形观察器"),
        ("fox-glow-on", "辉光开关"),
    ):
        assert needle in html, f"{intent} 缺少动效资产「{label}」（{needle}）"


@pytest.mark.parametrize("intent", INTENTS)
def test_reduced_motion_collapses_to_final_state(intent):
    """reduced-motion 不是 0.01ms 全杀：所有动画元素显式归为静态终态，
    且 reveal 元素不留在 opacity:0。"""
    html = render(intent, BRIEF, PRESET, {})
    assert "@media (prefers-reduced-motion: reduce)" in html, \
        f"{intent} 缺少 reduced-motion 块"
    block = html.split("@media (prefers-reduced-motion: reduce)")[1]
    block = block.split("@media print")[0]
    for needle in ("animation: none", "opacity: 1", "transform: none",
                   "display: none"):
        assert needle in block, f"{intent} 的 reduced-motion 块缺少「{needle}」"


def test_export_settles_ambient_motion():
    """导出必须先定格动效：导出件是终态文档，不是录屏。"""
    import re as _re
    source = (ROOT / "htmlninefox" / "exporting.py").read_text(encoding="utf-8")
    assert "_settle_ambient" in source, "exporting.py 缺少动效定格步骤"
    calls = _re.findall(r"^    _settle_ambient\(page\)$", source, _re.M)
    assert len(calls) >= 2, \
        f"PNG 与 PDF 两条导出路径都必须定格，实测调用 {len(calls)} 处"
    assert ".fox-reveal" in source and "fox-in" in source, \
        "定格必须把 reveal 元素置为可见终态"


def test_acceptance_script_settles_before_screenshots():
    """e2e_verify 的验收截图同样要先定格（截图是终态文档）。"""
    source = (ROOT / "e2e_verify.py").read_text(encoding="utf-8")
    assert "fox-reveal" in source and "fox-in" in source, \
        "e2e_verify.py 截图前必须定格环境动效"


def test_reveal_has_content_safety_backstop():
    """显形必须有内容安全兜底：IO 不可用或超时后元素以终态呈现。"""
    from htmlninefox.generators._shared import ambient_motion_js
    js = ambient_motion_js()
    assert "1800" in js, "缺少超时兜底（内容不可见比少一段编排更严重）"
    assert "fox-in" in js
