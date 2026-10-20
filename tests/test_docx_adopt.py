"""docx adoption gates (v0.8.1 step 4).

Adoption must not grow a second rendering path: these gates render through the
same `generators.render` the product uses, in all six intents, and assert the
document's own prose survives.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from htmlninefox.docx_adopt import adopt, sections_from_outline
from htmlninefox.docx_proposal import propose
from htmlninefox.intake_outline import AdapterInfo, Block, IntakeOutline, SourceInfo

INTENTS = ["landing", "dashboard", "deck", "poster", "archdoc", "doc"]

# 只许用脱敏示例文档（tests/fixtures/demo_docx.py）。真实客户文档不进仓库、
# 不进测试、不进截图 —— 2026-10-20 的合规要求。
from tests.fixtures.demo_docx import build_plan_docx  # noqa: E402


def _block(index: int, kind: str, text: str = "", *, level: int = 0,
           rows: tuple[tuple[str, ...], ...] = (), asset: str = "") -> Block:
    return Block(
        id=f"b{index}",
        kind=kind,
        heading=text if kind == "heading" else "",
        content=text if kind in {"paragraph", "list"} else "",
        level=level,
        rows=rows,
        asset=asset,
        evidence={"paragraph": index},
        ordinal=index - 1,
    )


def sample_outline() -> IntakeOutline:
    blocks = [
        _block(1, "heading", "一、背景", level=1),
        _block(2, "paragraph", "这是背景的第一段正文。"),
        _block(3, "paragraph", "这是背景的第二段正文。"),
        _block(4, "heading", "二、方案", level=1),
        _block(5, "paragraph", "方案说明文字。"),
        _block(6, "table", rows=(("指标", "数值"), ("转化", "12%"))),
        _block(7, "heading", "三、空章节", level=1),
        _block(8, "image", asset="word/media/image1.png"),
    ]
    return IntakeOutline(
        source=SourceInfo(kind="docx", ref="upload://docx", title="季度交付说明",
                          digest="sha256:test", origin="user_upload", licence="user_owned"),
        adapter=AdapterInfo(name="docx"),
        blocks=tuple(blocks),
    ).validate()


def test_sections_follow_the_headings_and_keep_their_prose():
    sections, notes = sections_from_outline(sample_outline())

    assert [s["heading"] for s in sections] == ["一、背景", "二、方案"]
    assert "第一段" in sections[0]["content"] and "第二段" in sections[0]["content"]
    assert sections[0]["kind"] == "sections"
    assert sections[0]["source"].startswith("docx:paragraph-")
    assert any("表格已压成文本行" in note for note in notes)
    assert any("图片" in note for note in notes)


def test_empty_heading_is_skipped_and_table_text_lands_in_its_section():
    sections, _ = sections_from_outline(sample_outline())

    assert all(s["content"].strip() for s in sections), "不允有空章节进渲染"
    assert "12%" in sections[1]["content"]


@pytest.mark.parametrize("intent", INTENTS)
def test_every_intent_renders_the_document_prose(intent):
    outline = sample_outline()
    proposal = propose(outline)

    page = adopt(outline, proposal, intent=intent)

    assert page.intent == intent
    assert "这是背景的第一段正文。" in page.html
    assert "方案说明文字。" in page.html
    assert len(page.html) > 1000


def test_adoption_reports_what_the_channel_cannot_carry():
    page = adopt(sample_outline())

    joined = " ".join(page.limitations)
    assert "表格已压成文本行" in joined
    assert "未配置 LLM" in joined, "提案层的边界必须随页面一起交付"


def test_toc_run_is_skipped_not_rendered_as_a_giant_paragraph():
    """Word 的目录是「提示句 + 01/02 条目」，两段都要跳过。

    真实方案文档里这一串有 800+ 字，混进正文会变成首节一个巨型段落。
    """
    outline = IntakeOutline(
        source=SourceInfo(kind="docx", ref="upload://docx", title="方案",
                          digest="sha256:test"),
        adapter=AdapterInfo(name="docx"),
        blocks=(_block(1, "paragraph", "打开文档后可右键更新目录"),
                _block(2, "list", "01  一、执行摘要"),
                _block(3, "list", "02  二、方案"),
                _block(4, "heading", "一、执行摘要", level=1),
                _block(5, "paragraph", "真正的正文。")),
    ).validate()

    sections, notes = sections_from_outline(outline)
    text = " ".join(s["content"] for s in sections)

    assert "更新目录" not in text and "01  一、执行摘要" not in text
    assert "真正的正文。" in text
    assert any("目录行已跳过" in note for note in notes)


def test_no_brand_means_no_placeholder_on_the_page():
    page = adopt(sample_outline())

    assert "Your Product" not in page.html


def test_toc_heading_never_becomes_a_section():
    outline = IntakeOutline(
        source=SourceInfo(kind="docx", ref="upload://docx", title="方案",
                          digest="sha256:test"),
        adapter=AdapterInfo(name="docx"),
        blocks=(_block(1, "heading", "目录", level=1),
                _block(2, "paragraph", "01 执行摘要"),
                _block(3, "heading", "一、执行摘要", level=1),
                _block(4, "paragraph", "正文。")),
    ).validate()

    sections, _ = sections_from_outline(outline)
    headings = [s["heading"] for s in sections]

    assert "目录" not in headings, "目录不能变成章节"
    assert "一、执行摘要" in headings
    # 目录行落在首个真标题之前，按「文档标题下的前言」处理——宁可保留，
    # 也不猜哪一段是目录项（真实文档的封面语也长这样）。
    assert headings[0] == "方案"


@pytest.mark.parametrize("intent", ["doc", "archdoc"])
def test_real_business_doc_renders_end_to_end(tmp_path, intent):
    """用脱敏示例文档跑完整链路：三十来节、六张表，正文必须到达产物。"""
    from htmlninefox.docx_import import parse_docx

    sample = build_plan_docx(tmp_path / "demo-plan.docx")
    outline = parse_docx(sample)
    proposal = propose(outline)
    page = adopt(outline, proposal, intent=intent)

    assert page.section_count >= 8
    assert "执行摘要" in page.html
    assert len(page.html) > 8000
