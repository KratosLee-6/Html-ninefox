"""风格轴门禁（v0.9.1 · 风格轴第一批）。

调性四原型（Playful/Premium/Corporate/Energetic）成为动效参数与组合
语义的权威轴，原则源自 LottieFiles/motion-design-skill（MIT），参数全部
落在 0.8.7 动效门禁内：

  * 覆盖矩阵：6 意图 × 4 原型 ≥ 1 个可产出组合（tone→preset 查表驱动）
    ——空洞不可发版；
  * 画廊 manifest 全体带 tone ∈ 词表，且每个 tone 都映射到原型；
  * match_preset 附带中文推荐理由（规则引擎版照给——「AI 增强可见」
    的兜底半场）；
  * 原型参数只随 ink/stagger/ambient 三轴变化，reveal 基础 .6s 固定
    （0.8.7 门禁锚点不动）。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from htmlninefox.generators._tokens import (  # noqa: E402
    INTENT_TONE_PRESET, MOTION_ARCHETYPES, PRESETS, match_preset,
    motion_params_for,
)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

TONE_VOCABULARY = {"dark", "minimal", "editorial", "vibrant", "professional", "techy"}
INTENTS = ("landing", "dashboard", "deck", "poster", "archdoc", "doc")


def _matrix_holes() -> list[str]:
    holes = []
    for intent in INTENTS:
        intent_tones = set(INTENT_TONE_PRESET.get(intent, {}))
        for archetype, spec in MOTION_ARCHETYPES.items():
            if not (intent_tones & set(spec["tones"])):
                holes.append(f"{intent}×{archetype}")
    return holes


def test_coverage_matrix_intent_x_archetype():
    """6 意图 × 4 原型：每个组合必须至少有一个 tone 能产出（空洞不可发版）。"""
    holes = _matrix_holes()
    assert not holes, (
        f"覆盖矩阵空洞（无法产出的组合）：{holes}——补 preset 映射或补模板")


def test_motion_archetype_params_stay_inside_motion_gates():
    """原型参数三轴全部落在 0.8.7 门禁内（只随 ink/stagger/ambient 变，
    reveal 基础 .6s 固定）。"""
    for name, spec in MOTION_ARCHETYPES.items():
        assert 600 <= spec["ink_ms"] <= 1200, f"{name} ink 越戏剧档"
        assert 120 <= spec["reveal_cap_ms"] < 500, f"{name} stagger cap 越预算"
        assert 20 <= spec["reveal_step_ms"] <= 90, f"{name} stagger 步长异常"
        assert 8 <= spec["ambient_s"] <= 40, f"{name} ambient 周期异常"
        assert spec["reveal_cap_ms"] >= spec["reveal_step_ms"] * 3, (
            f"{name} cap 承载不了三步 stagger")


def test_tone_maps_to_archetype_including_unknown_fallback():
    for tone in TONE_VOCABULARY:
        params = motion_params_for(tone)
        assert params["archetype"] in MOTION_ARCHETYPES
        assert params["ink_ms"] == MOTION_ARCHETYPES[params["archetype"]]["ink_ms"]
    # 词表外输入落兜底（风格轴不因生造词失效）
    fallback = motion_params_for("赛博朋克蒸汽波")
    assert fallback["archetype"] == "corporate"


def test_match_preset_carries_motion_and_reason():
    result = match_preset({"brief": {"style": {"tone": "dark"}}}, "landing")
    assert result["_motion"]["archetype"] == "energetic"
    reason = result["_reason"]
    assert result["name"] in reason and reason.endswith(
        MOTION_ARCHETYPES["energetic"]["copy"]), reason
    assert match_preset({"brief": {"style": {"tone": "editorial"}}},
                        "deck")["_motion"]["archetype"] == "premium"


def test_gallery_manifest_tone_labels_complete():
    manifest = json.loads(
        (ROOT / "htmlninefox" / "templates" / "gallery" / "manifest.json")
        .read_text(encoding="utf-8"))
    items = manifest["items"]
    assert len(items) >= 10, "画廊缩水"
    missing = [item["id"] for item in items if item.get("tone") not in TONE_VOCABULARY]
    assert not missing, f"tone 标签缺失或越表：{missing}"
    # 每张模板的 tone 都能落到一个原型（组合语义可用）
    for item in items:
        assert motion_params_for(item["tone"])["archetype"] in MOTION_ARCHETYPES


def test_archetype_params_reach_generated_product():
    """端到端：energetic 原型的 ink/ambient 真出现在渲染产物里。"""
    from htmlninefox.generators import _tokens, render as _  # noqa: F401
    from htmlninefox.generators.landing import render as render_landing
    preset = dict(match_preset(
        {"brief": {"style": {"tone": "dark"},
                   "content": {"core_message": "开发者平台"}}}, "landing"))
    assert preset["_motion"]["archetype"] == "energetic"
    html = render_landing(
        {"brief": {"brand": "狐构", "headline": "开发者平台",
                   "style": {"tone": "dark"}}},
        preset, {})
    assert "fox-ink-drop 0.6s" in html, "energetic ink 0.6s 未进产物"
    assert "fox-ambient-drift 12s" in html, "energetic ambient 12s 未进产物"
    assert "Math.min(200," in html and "* 24)" in html, "energetic stagger 未进产物"
    # 默认（无 _motion 的旧式 preset）保持 0.8.7 现值——向后兼容
    legacy = render_landing(
        {"brief": {"brand": "狐构", "headline": "开发者平台"}},
        dict(_tokens.PRESETS["linear-light"]), {})
    assert "fox-ink-drop 0.7s" in legacy and "fox-ambient-drift 26s" in legacy


def test_mutation_dropping_a_matrix_mapping_is_caught():
    """变异验证：砍掉 dashboard 的 dark/techy（energetic 仅有的 tone）→
    覆盖矩阵门禁 CAUGHT（同进程函数式变异）。"""
    import htmlninefox.generators._tokens as tokens
    original = dict(tokens.INTENT_TONE_PRESET["dashboard"])
    try:
        tokens.INTENT_TONE_PRESET["dashboard"] = {
            k: v for k, v in original.items() if k not in ("dark", "techy")}
        holes = _matrix_holes()
        assert "dashboard×energetic" in holes, (
            "砍掉映射后矩阵必须报出 dashboard×energetic 空洞")
    finally:
        tokens.INTENT_TONE_PRESET["dashboard"] = original
    assert not _matrix_holes(), "还原后矩阵必须闭合"
