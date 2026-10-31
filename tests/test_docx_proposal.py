"""docx proposal gates (v0.8.1 step 2).

Outlines are built directly: the proposal layer must work on the shared
contract, not on a DOCX-specific object. No LLM is configured in these tests —
the offline rule engine has to carry the whole path on its own, with a reason
attached to every choice it makes.
"""

from __future__ import annotations

import pytest

from htmlninefox.intake_proposal import (ImagePlanItem, Proposal, _judge_intent,
                                       propose)
from htmlninefox.intake_outline import (AdapterInfo, Block, IntakeOutline,
                                        SourceInfo)


def _block(index: int, kind: str, text: str, *, level: int = 0,
           rows: tuple[tuple[str, ...], ...] = ()) -> Block:
    """Every block carries a locator — the contract refuses those that don't."""
    values = {"heading": text, "paragraph": text, "list": text}
    if kind == "table":
        return Block(id=f"b{index}", kind="table", rows=rows,
                     evidence={"paragraph": index, "table": True}, ordinal=index - 1)
    return Block(id=f"b{index}", kind=kind, level=level,
                 heading=values.get(kind, ""),
                 content=values.get(kind, ""),
                 evidence={"paragraph": index}, ordinal=index - 1)


def outline(title: str, blocks: list[Block],
            limitations: tuple[str, ...] = ()) -> IntakeOutline:
    return IntakeOutline(
        source=SourceInfo(kind="docx", ref="upload://docx", title=title,
                          digest="sha256:test", origin="user_upload",
                          licence="user_owned"),
        adapter=AdapterInfo(name="docx"),
        blocks=tuple(blocks),
        limitations=limitations,
    ).validate()


def doc_like() -> IntakeOutline:
    blocks: list[Block] = []
    for section in range(10):
        blocks.append(_block(len(blocks) + 1, "heading", f"第{section + 1}章 说明", level=1))
        blocks.append(_block(len(blocks) + 1, "paragraph", f"这是第 {section + 1} 章的正文。"))
        blocks.append(_block(len(blocks) + 1, "paragraph", "第二段解释细节。"))
    for table in range(4):
        blocks.append(_block(len(blocks) + 1, "table", "",
                             rows=(("指标", "数值"), (f"项{table}", str(table)))))
    return outline("季度交付说明", blocks)


def deck_like() -> IntakeOutline:
    blocks = [_block(1, "heading", "把复杂创作折叠成一条路径", level=1)]
    for section in range(7):
        blocks.append(_block(len(blocks) + 1, "heading", f"章节{section + 1}", level=1))
        blocks.append(_block(len(blocks) + 1, "paragraph", "一句要点。"))
    return outline("发布会讲稿", blocks)


def archdoc_like() -> IntakeOutline:
    blocks = [_block(1, "heading", "系统架构说明", level=1)]
    for section in range(4):
        blocks.append(_block(len(blocks) + 1, "heading", f"模块{section + 1}", level=2))
        blocks.append(_block(len(blocks) + 1, "paragraph", "职责说明。"))
    return outline("平台部署架构", blocks)


def poster_like() -> IntakeOutline:
    blocks = [
        _block(1, "heading", "新品发布", level=1),
        _block(2, "paragraph", "一句话卖点。"),
        _block(3, "paragraph", "时间与地点。"),
    ]
    return outline("秋季新品海报", blocks)


def dashboard_like() -> IntakeOutline:
    blocks = [_block(1, "heading", "经营看板", level=1)]
    for table in range(6):
        blocks.append(_block(len(blocks) + 1, "table", "",
                             rows=(("指标", "数值"), (f"项{table}", str(table)))))
    for line in range(3):
        blocks.append(_block(len(blocks) + 1, "paragraph", "一句结论。"))
    return outline("月度经营看板", blocks)


@pytest.mark.parametrize("factory, expected", [
    (doc_like, "doc"),
    (deck_like, "deck"),
    (archdoc_like, "archdoc"),
    (poster_like, "poster"),
    (dashboard_like, "dashboard"),
])
def test_intent_rules_pick_the_document_shape(factory, expected):
    source = factory()
    intent, reason = _judge_intent(source)
    assert intent == expected, f"{expected} 判成了 {intent}：{reason}"
    assert reason and isinstance(reason, str)


def test_proposal_carries_intent_style_and_reason():
    proposal = propose(doc_like())

    assert proposal.intent == "doc"
    assert proposal.preset_id in {"doc-clean", "vercel-dark", "guizang-magazine"}
    assert proposal.style_reason
    assert "未配置 LLM" in " ".join(proposal.limitations)


def test_image_plan_has_a_cover_and_prompts_but_no_images():
    proposal = propose(doc_like())

    slots = [item.slot for item in proposal.image_plan]
    assert slots[0] == "cover" and len(slots) == len(set(slots))
    assert 2 <= len(proposal.image_plan) <= 4
    for item in proposal.image_plan:
        assert item.prompt.strip(), f"{item.slot} 缺提示词"
        assert "cover" in item.slot or item.slot.startswith("section-")


def test_copy_is_editable_text_not_a_render_decision():
    proposal = propose(doc_like())

    assert proposal.copy["headline"] == "季度交付说明"
    assert proposal.copy["summary"]
    assert proposal.copy["sections"][0]["heading"].startswith("第1章")
    assert len(proposal.copy["sections"]) <= 12


def test_outline_limitations_survive_into_the_proposal():
    source = outline("带限制的文档",
                     [_block(1, "heading", "标题", level=1),
                      _block(2, "paragraph", "正文。")],
                     limitations=("第 3–5 页是扫描图，未提取文本",))

    proposal = propose(source)

    assert "第 3–5 页是扫描图，未提取文本" in proposal.limitations


def test_machine_form_is_stable_for_external_agents():
    payload = propose(deck_like()).as_dict()

    assert payload["intent"] == "deck"
    assert payload["refined_by"] == "rules"
    assert set(payload) == {"intent", "intent_reason", "style", "image_plan",
                            "copy", "limitations", "refined_by"}
    assert payload["style"]["preset_id"] in {"guizang-magazine", "vercel-dark",
                                             "doc-clean", "vibrant-poster"}
    assert payload["image_plan"][0]["slot"] == "cover"


def test_invalid_preset_fails_loudly_instead_of_shipping():
    proposal = Proposal(intent="doc", intent_reason="x", preset_id="not-a-preset",
                        style_reason="x", image_plan=(), copy={"headline": "标题"})
    with pytest.raises(ValueError, match="未知预设"):
        proposal.validate()


def test_refiner_can_override_but_cannot_break_the_contract():
    def refiner(source, base):
        return {"intent": "archdoc",
                "style": {"preset_id": "vercel-dark", "reason": "LLM：技术读者偏好深色"},
                "copy": {**base.copy, "headline": "AI 改过的标题"}}

    refined = propose(doc_like(), refiner=refiner)
    assert refined.refined_by == "llm"
    assert refined.intent == "archdoc" and refined.preset_id == "vercel-dark"
    assert refined.copy["headline"] == "AI 改过的标题"

    def bad_refiner(source, base):
        return {"intent": "not-an-intent"}

    with pytest.raises(ValueError, match="未知意图"):
        propose(doc_like(), refiner=bad_refiner)


def test_toc_heading_is_not_a_section_and_gets_no_image_slot():
    """真实商务文档：第一个 Heading1 是「目录」，它不该变成章节或配图位。"""
    source = outline("方案", [
        _block(1, "heading", "目录", level=1),
        _block(2, "paragraph", "01 一、执行摘要"),
        _block(3, "heading", "一、执行摘要", level=1),
        _block(4, "paragraph", "正文。"),
    ])

    proposal = propose(source)

    assert [item.slot for item in proposal.image_plan] == ["cover", "section-1"]
    assert all("目录" not in item.purpose for item in proposal.image_plan)
    assert [s["heading"] for s in proposal.copy["sections"]] == ["一、执行摘要"]


def test_summary_is_collapsed_to_one_line():
    source = outline("方案", [
        _block(1, "heading", "标题", level=1),
        _block(2, "paragraph", "第一行\n第二行   第三行"),
    ])

    summary = propose(source).copy["summary"]

    assert "\n" not in summary and "  " not in summary
    assert summary.startswith("第一行 第二行 第三行")
