"""DOCX intake (v0.8.1 · step 1): read a .docx with the standard library only.

A .docx is an OOXML zip: `word/document.xml` carries the body,
`word/_rels/document.xml.rels` maps relationship ids to parts, and
`word/media/*` holds the embedded pictures. Parsing it with `zipfile` +
`ElementTree` keeps the offline promise intact and means the upload path works
on a machine with no `[docx]` extra installed — the same discipline the export
side uses for its zip smoke path.

The output is the shared `intake_outline` artefact (see `intake_outline.py`),
not a DOCX-specific model: the review desk, the proposal layer and the six
generators consume one shape whatever the input format. Every block carries a
locator (its 1-based body position) and every outline carries its limitations —
what was not read, rather than silence.
"""

from __future__ import annotations

import hashlib
import io
import posixpath
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from .intake_outline import (
    AdapterInfo,
    Block,
    IntakeOutline,
    SourceInfo,
    paragraph_evidence,
)

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"

DOCUMENT_PART = "word/document.xml"
RELS_PART = "word/_rels/document.xml.rels"
CORE_PART = "docProps/core.xml"

DC = "{http://purl.org/dc/elements/1.1/}"
TOC_TITLES = {"目录", "目 录", "contents", "table of contents"}

ADAPTER = AdapterInfo(name="docx", version=1, offline=True, requires=())

_HEADING_STYLE = re.compile(r"^heading\s*([1-6])$", re.I)
_TITLE_STYLES = {"title", "subtitle"}


class DocxIntakeError(ValueError):
    """The upload is not a .docx we can read — say so, do not half-parse it."""

    code = "docx_unreadable"


def _read(source: bytes | str | Path) -> tuple[dict[str, bytes], list[str], bytes]:
    raw = source if isinstance(source, bytes) else Path(source).read_bytes()
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            parts = {name: archive.read(name) for name in archive.namelist()}
    except zipfile.BadZipFile as exc:
        raise DocxIntakeError(f"不是有效的 docx（zip 读取失败）：{exc}") from exc
    if DOCUMENT_PART not in parts:
        raise DocxIntakeError("docx 里找不到 word/document.xml")
    return parts, sorted(parts), raw


def _relationships(parts: dict[str, bytes]) -> dict[str, str]:
    """rId → package part name. Internal targets are relative to `word/`."""
    raw = parts.get(RELS_PART)
    if not raw:
        return {}
    base = DOCUMENT_PART.rsplit("/", 1)[0]
    rels: dict[str, str] = {}
    for rel in ET.fromstring(raw):
        target = rel.get("Target") or ""
        if not target or rel.get("TargetMode") == "External":
            continue
        if target.startswith("/"):
            resolved = target.lstrip("/")          # package-absolute
        else:
            resolved = posixpath.normpath(posixpath.join(base, target))
        rels[rel.get("Id", "")] = resolved
    return rels


def _core_title(parts: dict[str, bytes]) -> str:
    """docProps/core.xml 的 dc:title —— 真实文档里比第一个标题更可信。"""
    raw = parts.get(CORE_PART)
    if not raw:
        return ""
    try:
        core = ET.fromstring(raw)
    except ET.ParseError:
        return ""
    node = core.find(DC + "title")
    return (node.text or "").strip() if node is not None else ""


def _paragraph_text(node: ET.Element) -> str:
    """Collect w:t, honour tabs and explicit line breaks, ignore field codes."""
    pieces: list[str] = []
    for child in node.iter():
        tag = child.tag
        if tag == W + "t":
            pieces.append(child.text or "")
        elif tag == W + "tab":
            pieces.append("\t")
        elif tag in (W + "br", W + "cr"):
            pieces.append("\n")
    return "".join(pieces).strip()


def _paragraph_style(node: ET.Element) -> str:
    style = node.find(f"{W}pPr/{W}pStyle")
    return (style.get(W + "val") or "") if style is not None else ""


def _list_info(node: ET.Element) -> tuple[bool, int]:
    """(is_list, depth) from w:numPr — depth is ilvl + 1, 0 when absent."""
    num_pr = node.find(f"{W}pPr/{W}numPr")
    if num_pr is None:
        return False, 0
    ilvl = num_pr.find(W + "ilvl")
    depth = 0
    if ilvl is not None:
        try:
            depth = int(ilvl.get(W + "val") or 0) + 1
        except ValueError:
            depth = 1
    return True, max(depth, 1)


def _image_parts(node: ET.Element, rels: dict[str, str]) -> list[str]:
    found: list[str] = []
    for blip in node.iter(A + "blip"):
        rid = blip.get(R + "embed") or blip.get(R + "link")
        part = rels.get(rid or "")
        if part:
            found.append(part)
    return found


def _table_rows(node: ET.Element) -> tuple[tuple[str, ...], ...]:
    rows: list[tuple[str, ...]] = []
    for row in node.iter(W + "tr"):
        cells = []
        for cell in row.findall(W + "tc"):
            text = " ".join(filter(None, (_paragraph_text(p) for p in cell.findall(W + "p"))))
            cells.append(text.strip())
        if cells:
            rows.append(tuple(cells))
    return tuple(rows)


def _body_children(document: ET.Element) -> list[ET.Element]:
    body = document.find(W + "body")
    if body is None:
        raise DocxIntakeError("docx 的 document.xml 里没有 w:body")
    return [child for child in list(body) if child.tag != W + "sectPr"]


def parse_docx(source: bytes | str | Path) -> IntakeOutline:
    """Parse a .docx into an `intake_outline`.

    `source` may be a path, a Path, or the uploaded bytes. Raises
    DocxIntakeError when the file cannot be read at all; anything readable but
    incomplete lands in `limitations` instead.
    """
    parts, names, raw = _read(source)
    rels = _relationships(parts)
    document = ET.fromstring(parts[DOCUMENT_PART])

    blocks: list[Block] = []
    assets: dict[str, bytes] = {}
    limitations: list[str] = []
    title = ""

    for position, node in enumerate(_body_children(document), start=1):
        if node.tag == W + "tbl":
            rows = _table_rows(node)
            if rows:
                blocks.append(Block(
                    id=f"b{position}", kind="table", rows=rows,
                    evidence=paragraph_evidence(position, table=True),
                    ordinal=len(blocks), provenance="verbatim"))
            continue
        if node.tag != W + "p":
            limitations.append(f"忽略未知块级元素 {node.tag.split('}')[-1]}")
            continue

        text = _paragraph_text(node)
        style = _paragraph_style(node)
        locator = paragraph_evidence(position)

        for part in _image_parts(node, rels):
            if part in parts:
                assets[part] = parts[part]
                blocks.append(Block(
                    id=f"b{position}-img{len(blocks)}", kind="image",
                    asset=part, content=text,
                    evidence=paragraph_evidence(position, part=part),
                    ordinal=len(blocks), provenance="verbatim"))
            else:
                limitations.append(f"图片引用指向缺失的部件：{part}")

        if not text:
            continue

        match = _HEADING_STYLE.match(style)
        if match:
            blocks.append(Block(
                id=f"b{position}", kind="heading", heading=text,
                level=int(match.group(1)), evidence=locator,
                ordinal=len(blocks), provenance="verbatim"))
            continue
        if style.lower() in _TITLE_STYLES:
            title = title or text
            blocks.append(Block(
                id=f"b{position}", kind="heading", heading=text, level=1,
                evidence=locator, ordinal=len(blocks), provenance="verbatim"))
            continue

        is_list, depth = _list_info(node)
        blocks.append(Block(
            id=f"b{position}", kind="list" if is_list else "paragraph",
            content=text, level=depth, evidence=locator,
            ordinal=len(blocks), provenance="verbatim"))

    if not title:
        # 真实文档里第一个 Heading1 常常是「目录」。核心属性里的 dc:title
        # 更可信；没有再退回第一个非目录标题。
        title = _core_title(parts)
    if not title:
        first_heading = next(
            (b for b in blocks
             if b.kind == "heading" and b.heading.strip().lower() not in TOC_TITLES),
            None)
        title = first_heading.heading if first_heading else ""

    # 说出丢了什么，而不是静默吞掉——降级清单是交付物的一部分。
    unsupported = [n for n in names if n.startswith("word/")
                   and n not in (DOCUMENT_PART, RELS_PART)
                   and not n.startswith("word/media/")
                   and not n.startswith("word/theme/")
                   and not n.startswith("word/fontTable")]
    if unsupported:
        limitations.append(f"未读取的部件 {len(unsupported)} 个："
                           + "、".join(sorted(unsupported)[:6]))
    if not blocks:
        limitations.append("文档没有可读的正文块")
    if not title:
        limitations.append("文档没有标题：核心属性与标题样式都没有")

    ref = (source if isinstance(source, str)
           else str(source) if isinstance(source, Path) else "upload://docx")
    return IntakeOutline(
        source=SourceInfo(kind="docx", ref=ref, title=title,
                          digest="sha256:" + hashlib.sha256(raw).hexdigest(),
                          origin="user_upload", licence="user_owned"),
        adapter=ADAPTER,
        blocks=tuple(blocks),
        assets=assets,
        limitations=tuple(limitations),
    ).validate()
