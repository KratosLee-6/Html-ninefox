"""PPTX intake (v0.8.3): read a .pptx back into an `intake_outline`.

Reading is the export side run backwards: python-pptx already ships in the
optional `[pptx]` extra, so importing a deck adds no new dependency — the
same discipline as `docx_export` (a missing extra is an honest pip hint,
never a silent install). The traversal is deliberately read-only and boring:
slides → shapes → text frames, plus tables, pictures and speaker notes.

What this adapter will NOT do is as much of the contract as what it does:
layout geometry (coordinates, masters, theme effects) is not reconstructed,
charts and SmartArt are counted rather than decomposed, and merged table
cells lose their span. Those boundaries live in `limitations` where the
review desk can see them — a claim without its limits is worse than a
smaller claim (the REA lesson, same as the DOCX adapter).

The output is the shared `intake_outline` artefact (see `intake_outline.py`),
so the proposal layer and the review desk consume a PPTX exactly the way
they consume a DOCX or a web page. Every block carries a locator — slide
number plus 1-based shape ordinal, `slide` being one of the contract's
locator keys — and shape-internal positions ride along as extra evidence
(`para` for paragraphs, `part` for group members and speaker notes).
"""

from __future__ import annotations

import hashlib
import io
import zipfile
from dataclasses import replace
from pathlib import Path

from .intake_outline import (
    AdapterInfo,
    Block,
    IntakeOutline,
    SourceInfo,
)

ADAPTER = AdapterInfo(name="pptx", version=1, offline=True, requires=("python-pptx",))

# 这条边界永远为真，所以永远在场——而不是等哪次拆解失败才想起来说。
GEOMETRY_LIMITATION = "布局几何不还原：坐标、母版与主题效果不读取"

PRESENTATION_PART = "ppt/presentation.xml"


class PptxIntakeError(ValueError):
    """The upload is not a .pptx we can read — say so, do not half-parse it."""

    code = "pptx_unreadable"


def _read(source: bytes | str | Path):
    raw = source if isinstance(source, bytes) else Path(source).read_bytes()
    try:
        from pptx import Presentation
    except ImportError as exc:  # pragma: no cover - 可选 extra 守卫
        raise PptxIntakeError(
            "读取 PPTX 需要 python-pptx：pip install 'htmlninefox[pptx]'") from exc
    # 先用 stdlib 验包，再交给 python-pptx：坏 zip 抛 BadZipFile（不是
    # ValueError），好 zip 但不是 ppt（如误传 docx）会在深处抛 AttributeError
    # ——都拦在门口，统一说「读不了」，绝不让半份解析流出去。
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            names = set(archive.namelist())
    except zipfile.BadZipFile as exc:
        raise PptxIntakeError(f"不是有效的 pptx（zip 读取失败）：{exc}") from exc
    if PRESENTATION_PART not in names:
        raise PptxIntakeError(
            f"不是有效的 pptx（找不到 {PRESENTATION_PART}，可能是其他 zip 文档）")
    try:
        return Presentation(io.BytesIO(raw)), raw
    except Exception as exc:
        raise PptxIntakeError(f"不是有效的 pptx（包读取失败）：{exc}") from exc


def _slide_blocks(number: int, slide, assets: dict[str, bytes],
                  limitations: list[str]) -> list[Block]:
    """一页 → 块。

    形状序号 1 起，与审核台里「第 N 页第 M 个形状」对得上。组内形状沿用
    组的形状号，成员身份记在 `part`（如 group.1）；图表与读不懂的形状只
    计数并写进 limitations——拆不出来时如实说，比硬拆出错的块强。
    """
    from pptx.enum.shapes import MSO_SHAPE_TYPE, PP_PLACEHOLDER

    blocks: list[Block] = []
    title_types = {PP_PLACEHOLDER.TITLE, PP_PLACEHOLDER.CENTER_TITLE}
    body_types = {PP_PLACEHOLDER.BODY, PP_PLACEHOLDER.OBJECT,
                  PP_PLACEHOLDER.VERTICAL_BODY, PP_PLACEHOLDER.VERTICAL_OBJECT}
    charts = opaque = 0

    def ph_type(shape):
        """占位符类型；枚举里没有的自造类型降级为 None，不当普通文本崩掉整份解析。"""
        try:
            return shape.placeholder_format.type
        except ValueError:
            return None

    def base_id(shape_index: int, suffix: str) -> str:
        return f"s{number}-sh{shape_index}" + (f"-{suffix}" if suffix else "")

    def locator(shape_index: int, suffix: str, **extra) -> dict:
        evidence = {"slide": number, "shape": shape_index}
        if suffix:
            evidence["part"] = suffix
        evidence.update(extra)
        return evidence

    def text_frame_blocks(shape, shape_index: int, suffix: str) -> None:
        """标题占位符 → 标题；正文占位符 → 列表；其余文本 → 段落。

        一段一块（与 DOCX 逐段成块同一纪律），段落号进 evidence。
        """
        if shape.is_placeholder and ph_type(shape) in title_types:
            heading = " ".join((shape.text_frame.text or "").split())
            if heading:
                blocks.append(Block(
                    id=base_id(shape_index, suffix), kind="heading",
                    heading=heading, level=1,
                    evidence=locator(shape_index, suffix),
                    provenance="verbatim"))
            return
        kind = ("list" if shape.is_placeholder
                and ph_type(shape) in body_types else "paragraph")
        for para_index, para in enumerate(shape.text_frame.paragraphs, start=1):
            text = " ".join((para.text or "").split())
            if not text:
                continue
            blocks.append(Block(
                id=f"{base_id(shape_index, suffix)}-p{para_index}",
                kind=kind, content=text,
                level=(para.level + 1) if kind == "list" else 0,
                evidence=locator(shape_index, suffix, para=para_index),
                provenance="verbatim"))

    def table_block(shape, shape_index: int, suffix: str) -> None:
        table = shape.table
        rows = tuple(
            tuple(" ".join((cell.text or "").split()) for cell in row.cells)
            for row in table.rows)
        rows = tuple(row for row in rows if any(row))
        if rows:
            blocks.append(Block(
                id=base_id(shape_index, suffix), kind="table", rows=rows,
                evidence=locator(shape_index, suffix), provenance="verbatim"))
        if any(getattr(cell, "is_spanned", False)
               for row in table.rows for cell in row.cells):
            limitations.append(
                f"第 {number} 页表格含合并单元格，已压成普通行列，跨格结构丢失")

    def picture_block(shape, shape_index: int, suffix: str) -> None:
        try:
            image = shape.image
        except ValueError:  # 外链图片没有内嵌部件，拿不到字节
            limitations.append(f"第 {number} 页有图片无法提取（可能外链未内嵌）")
            return
        name = f"pptx/slide-{number}-sh{shape_index}.{image.ext}"
        assets[name] = image.blob
        blocks.append(Block(
            id=base_id(shape_index, suffix), kind="image", asset=name,
            evidence=locator(shape_index, suffix), provenance="verbatim"))

    def handle(shape, shape_index: int, suffix: str = "") -> None:
        nonlocal charts, opaque
        if getattr(shape, "has_chart", False):
            charts += 1
            return
        if getattr(shape, "has_table", False):
            table_block(shape, shape_index, suffix)
            return
        shape_type = getattr(shape, "shape_type", None)
        if shape_type == MSO_SHAPE_TYPE.PICTURE:
            picture_block(shape, shape_index, suffix)
            return
        if shape_type == MSO_SHAPE_TYPE.GROUP:
            for inner_index, inner in enumerate(shape.shapes, start=1):
                inner_suffix = f"{suffix}group.{inner_index}." if suffix else f"group.{inner_index}."
                handle(inner, shape_index, inner_suffix)
            return
        if getattr(shape, "has_text_frame", False):
            text_frame_blocks(shape, shape_index, suffix)
            return
        opaque += 1  # SmartArt、媒体等——只计数，不猜内容

    for shape_index, shape in enumerate(slide.shapes, start=1):
        handle(shape, shape_index)

    if charts:
        limitations.append(f"第 {number} 页有 {charts} 个图表，只计数未拆解")
    if opaque:
        limitations.append(f"第 {number} 页有 {opaque} 个未拆解形状（SmartArt/媒体等），只计数")

    # 讲稿备注是逐页文本，归段落块；`part=notes` 让它能被回指核对。
    if slide.has_notes_slide:
        notes = " ".join((slide.notes_slide.notes_text_frame.text or "").split())
        if notes:
            blocks.append(Block(
                id=f"s{number}-notes", kind="paragraph", content=notes,
                evidence={"slide": number, "part": "notes"},
                provenance="verbatim"))
    return blocks


def parse_pptx(source: bytes | str | Path) -> IntakeOutline:
    """Parse a .pptx into an `intake_outline`.

    `source` may be a path, a Path, or the uploaded bytes. Raises
    PptxIntakeError when the file cannot be read at all; anything readable
    but undecodable lands in `limitations` instead.
    """
    presentation, raw = _read(source)

    blocks: list[Block] = []
    assets: dict[str, bytes] = {}
    limitations: list[str] = [GEOMETRY_LIMITATION]

    for number, slide in enumerate(presentation.slides, start=1):
        for block in _slide_blocks(number, slide, assets, limitations):
            blocks.append(replace(block, ordinal=len(blocks)))

    title = (presentation.core_properties.title or "").strip()
    if not title:
        first_heading = next(
            (b for b in blocks if b.kind == "heading" and b.heading), None)
        title = first_heading.heading if first_heading else ""
    if not blocks:
        limitations.append("演示没有可读的文本内容")
    if not title:
        limitations.append("演示没有标题：核心属性与首页标题都没有")

    ref = (source if isinstance(source, str)
           else str(source) if isinstance(source, Path) else "upload://pptx")
    return IntakeOutline(
        source=SourceInfo(kind="pptx", ref=ref, title=title,
                          digest="sha256:" + hashlib.sha256(raw).hexdigest(),
                          origin="user_upload", licence="user_owned"),
        adapter=ADAPTER,
        blocks=tuple(blocks),
        assets=assets,
        limitations=tuple(dict.fromkeys(limitations)),
    ).validate()
