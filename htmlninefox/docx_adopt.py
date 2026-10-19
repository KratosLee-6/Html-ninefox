"""DOCX adoption (v0.8.1 · step 4): outline + proposal → the existing block channel.

Adoption adds no rendering path. The six generators already consume
`assets["blocks"]` (v0.7's channel), so this module's whole job is to turn a
`docx_outline` into the section dicts those renderers understand — and to say,
in `limitations`, what the channel cannot carry (tables are flattened into
text, images stay assets rather than being inlined).

Keeping the seam this thin is deliberate: a second rendering path is how the
preview and the shipped page drift apart, which is exactly what v0.7.4 cost.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from .docx_proposal import Proposal, propose
from .generators import _tokens, render
from .intake_outline import IntakeOutline

_TOC_HEADS = {"目录", "目 录", "contents", "table of contents"}


@dataclass(frozen=True)
class AdoptedPage:
    html: str
    intent: str
    preset_id: str
    section_count: int
    limitations: tuple[str, ...]


def _rows_to_text(rows: tuple[tuple[str, ...], ...]) -> str:
    """Tables become one readable line each — a loss we state, not hide."""
    return "\n".join(" ｜ ".join(cell for cell in row) for row in rows if any(row))


def sections_from_outline(outline: IntakeOutline) -> tuple[list[dict], list[str]]:
    """Outline blocks → the `kind: sections` dicts the renderers consume.

    A heading opens a section; paragraphs and lists fill it; a table is
    flattened into its section and reported; an image stays an asset and is
    reported. Headings with no body are skipped rather than emitted empty —
    a document full of empty headings is worse than a shorter document.
    """
    sections: list[dict] = []
    notes: list[str] = []
    current: dict | None = None

    def flush() -> None:
        nonlocal current
        if current and current["content"].strip():
            current["content"] = current["content"].strip()
            sections.append(current)
        current = None

    for block in outline.blocks:
        if block.kind == "heading":
            if block.heading.strip().lower() in _TOC_HEADS:
                continue
            flush()
            current = {
                "id": f"doc-section-{len(sections) + 1}",
                "kind": "sections",
                "heading": block.heading.strip(),
                "content": "",
                "provenance": block.provenance,
                "source": f"docx:paragraph-{block.evidence.get('paragraph', '')}",
            }
            continue

        body = block.content or (block.heading if block.kind == "section" else "")
        if block.kind == "table" and block.rows:
            body = _rows_to_text(block.rows)
            notes.append("表格已压成文本行；列宽、合并单元格与边框不随行")
        elif block.kind == "image":
            notes.append(f"图片 {block.asset} 保留为资产，未内联进页面")

        if not body:
            continue
        if current is None:
            current = {
                "id": f"doc-section-{len(sections) + 1}",
                "kind": "sections",
                "heading": outline.source.title or "概述",
                "content": "",
                "provenance": block.provenance,
                "source": f"docx:paragraph-{block.evidence.get('paragraph', '')}",
            }
        current["content"] += ("\n\n" if current["content"] else "") + body

    flush()
    if not sections:
        fallback = outline.source.title or "文档"
        notes.append("文档没有可用的章节正文，已用标题生成一个概述节")
        sections = [{"id": "doc-section-1", "kind": "sections",
                     "heading": fallback, "content": fallback,
                     "provenance": "structure_only", "source": "docx:fallback"}]
    return sections, notes


def adopt(outline: IntakeOutline, proposal: Proposal | None = None, *,
          intent: str | None = None) -> AdoptedPage:
    """Render the adopted page through the existing generators.

    `intent` lets the review desk try another shape without re-proposing.
    """
    proposal = proposal or propose(outline)
    if intent and intent != proposal.intent:
        proposal = replace(proposal, intent=intent)

    sections, notes = sections_from_outline(outline)
    assets = {"blocks": sections}
    brief = {
        "brief": {
            "headline": proposal.copy.get("headline", ""),
            "brand": "",
            "content": {
                "summary": proposal.copy.get("summary", ""),
                "sections": proposal.copy.get("sections", []),
                "key_points": proposal.copy.get("key_points", []),
            },
        }
    }
    preset = dict(_tokens.get_preset(proposal.preset_id))
    html = render(proposal.intent, brief, preset, assets)

    limitations = tuple(dict.fromkeys((*outline.limitations, *proposal.limitations, *notes)))
    return AdoptedPage(html=html, intent=proposal.intent,
                       preset_id=proposal.preset_id,
                       section_count=len(sections), limitations=limitations)
