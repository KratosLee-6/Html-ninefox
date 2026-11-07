"""copy_expert 门禁（0.9.2 · AI 生成深化）。

纪律：LLM 只是建议——
  * preset 推荐：preset_id 必须在库，不在 = 回退规则（fallback_used=True）；
  * 槽位润色：数字串双向一致（不许丢也不许发明）、禁词剔除、超长丢弃；
  * 无 AI 照实说：available=false + 「润色需要 LLM」，规则引擎不代写文案；
  * 测试接缝：HTMLNINEFOX_LLM_STUB=1（env 门控，见 llm.py），API e2e 不打真网。
"""

from __future__ import annotations

import os
import sys
import urllib.parse
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

STUB_ENV = {"HTMLNINEFOX_LLM_STUB": "1"}

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


# -------------------------------------------------- 单元层（进程内 + 假 router）

class _FakeResult:
    def __init__(self, text: str):
        self.text = text
        self.model = "fake-model"


def _with_fake_router(monkeypatch, responses: dict[str, str]):
    """把 llm.router.call 替换成按 task 返回固定文本的假模型。"""
    from htmlninefox.experts import copy_expert

    def fake_call(*, prompt, agent="copy_expert", task="general", **kwargs):
        if task not in responses:
            raise RuntimeError(f"fake router: no response for {task}")
        return _FakeResult(responses[task])

    monkeypatch.setattr(copy_expert.router, "call", fake_call)


def test_recommend_preset_accepts_valid_id(monkeypatch):
    _with_fake_router(monkeypatch, {
        "preset_recommend": '{"preset_id": "shadcn-dashboard", "reason": "数据密度优先"}',
    })
    from htmlninefox.experts.copy_expert import CopyExpert
    result = CopyExpert().recommend_preset(
        {"brief": {"style": {"tone": "dark"}}}, "dashboard", allow_llm=True)
    assert result["preset_id"] == "shadcn-dashboard"
    assert result["fallback_used"] is False
    assert "数据密度" in result["reason"]


def test_recommend_preset_rejects_unknown_id(monkeypatch):
    """LLM 推荐了不存在的预设 = 回退规则（返回 fallback_used，preset_id=None）。"""
    _with_fake_router(monkeypatch, {
        "preset_recommend": '{"preset_id": "not-a-preset", "reason": "幻觉"}',
    })
    from htmlninefox.experts.copy_expert import CopyExpert
    result = CopyExpert().recommend_preset({"brief": {}}, "landing", allow_llm=True)
    assert result["fallback_used"] is True and result["preset_id"] is None


def test_recommend_preset_survives_broken_json(monkeypatch):
    _with_fake_router(monkeypatch, {"preset_recommend": "这不是 JSON"})
    from htmlninefox.experts.copy_expert import CopyExpert
    result = CopyExpert().recommend_preset({"brief": {}}, "landing", allow_llm=True)
    assert result["fallback_used"] is True


def test_polish_slots_drops_invented_numbers(monkeypatch):
    """原文没有 86.9%，建议发明了 —— 该槽丢弃（LLM 无权编造指标）。"""
    _with_fake_router(monkeypatch, {
        "copy_polish": '{"headline": "看板", "summary": "转化率高达 86.9%"}',
    })
    from htmlninefox.experts.copy_expert import CopyExpert
    result = CopyExpert().polish_slots(
        {"headline": "看板", "summary": "交付看板"},
        {"intent": "dashboard"}, allow_llm=True)
    assert result["suggestions"] == {"headline": "看板"}
    assert any("数字" in item for item in result["dropped"])


def test_polish_slots_drops_lost_numbers_and_forbidden(monkeypatch):
    """原文的 1,284 被弄丢 + 禁词出现 —— 分别丢弃。"""
    _with_fake_router(monkeypatch, {
        "copy_polish": json_dumps_two(),
    })
    from htmlninefox.experts.copy_expert import CopyExpert
    result = CopyExpert().polish_slots(
        {"summary": "日交付 1,284 页", "cta": "放心交付"},
        {"intent": "doc", "memory": {"forbidden": ["放心"]}}, allow_llm=True)
    assert result["suggestions"] == {}
    assert len(result["dropped"]) == 2


def json_dumps_two() -> str:
    import json
    return json.dumps({
        "summary": "日交付上千页",
        "cta": "放心交付，立即开始",
    }, ensure_ascii=False)


def test_polish_slots_disabled_is_honest(monkeypatch):
    from htmlninefox.experts.copy_expert import CopyExpert
    result = CopyExpert().polish_slots({"headline": "标题"}, {}, allow_llm=False)
    assert result["fallback_used"] is True and result["suggestions"] == {}


# -------------------------------------------------- API 层（真 HTTP + stub）

@pytest.fixture()
def stubbed_workbench(tmp_path: Path, monkeypatch):
    """服务端进程开 stub：真 HTTP 打 /api/polish-slots，不打真网。
    WorkbenchServer 是进程内线程——setenv 即对服务端生效。"""
    from tests.conftest import WorkbenchServer

    monkeypatch.setenv("HTMLNINEFOX_LLM_STUB", "1")
    with WorkbenchServer(tmp_path / "output") as server:
        yield server


def _post(workbench, path: str, body: dict, expected: int = 200) -> dict:
    from tests.test_server_project_api import request as api_request
    payload, _ = api_request(workbench.base_url, path, "POST", body,
                             expected=expected)
    return payload


def test_polish_slots_api_with_stub(stubbed_workbench):
    payload = _post(stubbed_workbench, "/api/polish-slots", {
        "prompt": "做一个开发者看板", "intent": "dashboard",
        "slots": {"headline": "内容交付看板"}})
    assert payload["ok"] is True and payload["available"] is True
    assert payload["suggestions"]["headline"] == "性能监控 · 一屏尽览"
    assert payload["model"] == "test-stub"


def test_polish_slots_api_without_slots(stubbed_workbench):
    error = _post(stubbed_workbench, "/api/polish-slots",
                  {"prompt": "x", "slots": {}}, expected=400)
    assert error["error"]["code"] == "polish_slots_required"


def test_polish_slots_api_without_ai_is_honest(tmp_path: Path):
    """未配 AI：available=false + 照实说（不走 stub 也不打真网）。"""
    from tests.conftest import WorkbenchServer
    from tests.test_server_project_api import request as api_request

    with WorkbenchServer(tmp_path / "out") as server:
        payload, _ = api_request(server.base_url, "/api/polish-slots", "POST",
                                 {"prompt": "做一个落地页",
                                  "slots": {"headline": "标题"}})
    assert payload["ok"] is True and payload["available"] is False
    assert "润色需要 LLM" in payload["reason"]


def test_analyze_uses_llm_preset_recommendation(stubbed_workbench):
    """compose 推荐 LLM 化：stub 推荐 vercel-dark + 理由 → analyze 采用并在
    理由里注明（AI 推荐）；matched_by 带 +AI 推荐。"""
    payload = _post(stubbed_workbench, "/api/analyze",
                    {"prompt": "做一个开发者性能看板，深色"})
    assert payload["preset_id"] == "vercel-dark"
    assert "AI 推荐" in payload["style_reason"]
    assert payload["motion"]["archetype"] == "energetic"


def test_adopted_polish_reaches_generated_product(stubbed_workbench, tmp_path: Path):
    """端到端闭环：润色建议 → generate content 通道 → 产物印人采纳的文案。"""
    from tests.test_server_project_api import request as api_request

    suggestion = _post(stubbed_workbench, "/api/polish-slots", {
        "prompt": "做一个智能水杯的落地页", "intent": "landing",
        "slots": {"headline": "智能水杯 · 三档控温"}})["suggestions"]["headline"]
    result = _post(stubbed_workbench, "/api/generate", {
        "prompt": "做一个智能水杯的落地页", "intent": "landing", "quiet_llm": True,
        "content": {"headline": suggestion}})
    html = (Path(str(result["project"])) / "output.html").read_text(encoding="utf-8")
    assert suggestion in html, "人采纳的润色文案必须出现在产物里"
