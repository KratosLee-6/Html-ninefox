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


# ============================================================
# 0.9.1 后半：调性选择器全链路 + 配方时间线
# ============================================================

import urllib.parse  # noqa: E402

import pytest  # noqa: E402


@pytest.fixture()
def workbench(tmp_path: Path):
    from tests.conftest import WorkbenchServer
    with WorkbenchServer(tmp_path / "output") as server:
        yield server


def _analyze(workbench, body: dict, expected: int = 200) -> dict:
    from tests.test_server_project_api import request as api_request
    payload, _ = api_request(workbench.base_url, "/api/analyze", "POST", body,
                             expected=expected)
    return payload


def _generate(workbench, body: dict, expected: int = 200) -> dict:
    from tests.test_server_project_api import request as api_request
    payload, _ = api_request(workbench.base_url, "/api/generate", "POST", body,
                             expected=expected)
    return payload


def test_analyze_rejects_unknown_tone(workbench):
    error = _analyze(workbench, {"prompt": "做一个落地页", "tone": "赛博朋克"},
                     expected=400)
    assert error["error"]["code"] == "tone_invalid"


def test_analyze_respects_explicit_tone(workbench):
    payload = _analyze(workbench, {
        "prompt": "做一个面向开发者的性能监控看板，深色，强调数据密度",
        "tone": "editorial"})
    assert payload["tone"] == "editorial"
    assert payload["motion"]["archetype"] == "premium", (
        "显式调性必须压过自动分析（深色文本会推 dark/energetic）")
    assert payload["style_reason"]


def test_generate_rejects_unknown_tone(workbench):
    error = _generate(workbench, {"prompt": "做一个落地页", "intent": "landing",
                                  "tone": "蒸汽波", "quiet_llm": True}, expected=400)
    assert error["error"]["code"] == "tone_invalid"


def test_generate_output_carries_tone_motion(workbench):
    """端到端：tone 覆盖 → pipeline 注入 brief → style_expert 重匹配 →
    渲染产物携带原型的真实动效参数。vibrant→playful(0.6s/14s)，
    editorial→premium(0.9s/32s)。"""
    cases = {"vibrant": ("fox-ink-drop 0.6s", "fox-ambient-drift 14s"),
             "editorial": ("fox-ink-drop 0.9s", "fox-ambient-drift 32s")}
    for tone, (ink_needle, ambient_needle) in cases.items():
        result = _generate(workbench, {
            "prompt": "做一个智能水杯的落地页：三档控温", "intent": "landing",
            "tone": tone, "quiet_llm": True})
        name = result["project_name"]
        html = (workbench.output_root / name / "output.html").read_text(encoding="utf-8")
        assert ink_needle in html, f"{tone}: {ink_needle} 未进产物"
        assert ambient_needle in html, f"{tone}: {ambient_needle} 未进产物"


def test_generate_without_tone_keeps_automatic_match(workbench):
    """不传 tone = 交给分析（回归护栏）：深色文本照走 dark/energetic。"""
    result = _generate(workbench, {
        "prompt": "做一个面向开发者的性能监控看板，深色", "intent": "landing",
        "quiet_llm": True})
    html = (workbench.output_root / result["project_name"]
            / "output.html").read_text(encoding="utf-8")
    assert "fox-ink-drop 0.6s" in html and "fox-ambient-drift 12s" in html


def test_recipe_run_endpoint_returns_stages(workbench):
    result = _generate(workbench, {
        "prompt": "做一个智能水杯的落地页", "intent": "landing", "quiet_llm": True})
    name = result["project_name"]
    from tests.test_server_project_api import request as api_request
    payload, _ = api_request(
        workbench.base_url,
        "/api/projects/" + urllib.parse.quote(name) + "/recipe-run", "GET")
    assert payload["ok"] is True and payload["status"] == "succeeded"
    stages = payload["stages"]
    assert [s["id"] for s in stages] == ["analyze", "compose", "generate",
                                         "verify", "deliver"]
    for stage in stages:
        assert "fallback_used" in stage and "model" in stage, (
            "时间线徽章的数据源（model/fallback_used）必须在场")
    # 缺配方记录 → 404 not_found（file 节点的时间线会安静隐藏）
    (workbench.output_root / name / "recipe-run.json").unlink()
    missing, _ = api_request(
        workbench.base_url,
        "/api/projects/" + urllib.parse.quote(name) + "/recipe-run",
        "GET", expected=404)
    assert missing["error"]["code"] == "not_found"
