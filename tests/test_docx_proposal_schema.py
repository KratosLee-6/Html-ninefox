"""提案 schema 锁定（v0.8.1 · step 5 的一半）。

审核台、外部 agent、采纳生成三方都读这份 JSON。字段一旦悄悄改名或消失，
界面不会报错——它会安静地显示空值。所以这里锁的是**键的集合**，不是值。
"""

from __future__ import annotations

from htmlninefox.intake_proposal import propose
from htmlninefox.intake_outline import AdapterInfo, Block, IntakeOutline, SourceInfo

TOP_KEYS = {"intent", "intent_reason", "style", "image_plan", "copy", "limitations", "refined_by"}
STYLE_KEYS = {"preset_id", "reason"}
PLAN_KEYS = {"slot", "purpose", "prompt"}
COPY_KEYS = {"headline", "summary", "sections", "key_points"}


def _outline() -> IntakeOutline:
    blocks = (
        Block(id="b1", kind="heading", heading="一、背景", level=1, evidence={"paragraph": 1},
              ordinal=0),
        Block(id="b2", kind="paragraph", content="正文第一段。", evidence={"paragraph": 2},
              ordinal=1),
        Block(id="b3", kind="heading", heading="二、方案", level=1, evidence={"paragraph": 3},
              ordinal=2),
        Block(id="b4", kind="paragraph", content="正文第二段。", evidence={"paragraph": 4},
              ordinal=3),
    )
    return IntakeOutline(
        source=SourceInfo(kind="docx", ref="upload://docx", title="季度交付说明",
                          digest="sha256:test"),
        adapter=AdapterInfo(name="docx"),
        blocks=blocks,
    ).validate()


def test_proposal_json_keeps_its_shape():
    payload = propose(_outline()).as_dict()

    assert set(payload) == TOP_KEYS
    assert set(payload["style"]) == STYLE_KEYS
    assert set(payload["copy"]) == COPY_KEYS
    assert payload["image_plan"], "提案必须至少有一个图片位"
    assert set(payload["image_plan"][0]) == PLAN_KEYS


def test_offline_fallback_is_explicit_not_silent():
    """没配模型时必须自称 rules —— 否则界面会把规则结果当成 AI 的判断。"""
    payload = propose(_outline()).as_dict()

    assert payload["refined_by"] == "rules"
    assert any("LLM" in item for item in payload["limitations"]), \
        "离线兜底要在 limitations 里说出来，不能只靠 refined_by 这个字段"


def test_a_slot_without_a_prompt_never_reaches_the_desk():
    payload = propose(_outline()).as_dict()

    assert payload["intent_reason"]
    assert payload["style"]["reason"]
    assert all(item["prompt"].strip() for item in payload["image_plan"]), \
        "图片位不能只有位置没有提示词"
