"""DOCX intake (v0.8.1 · step 1): read a .docx with the standard library only.

A .docx is an OOXML zip: `word/document.xml` carries the body,
`word/_rels/document.xml.rels` maps relationship ids to parts, and
`word/media/*` holds the embedded pictures. Parsing it with `zipfile` +
`ElementTree` keeps the offline promise intact and means the upload path works
on a machine with no `[docx]` extra installed — the same discipline the export
side uses for its zip smoke path.

The output is a *handover artefact* (`docx_outline`): blocks the review desk can
render, assets an image plan can reference, and a warning list that says what
did not survive instead of dropping it quietly (VISION: AI proposes, humans
review; nothing is lost silently).
"""

from __future__ import annotations

import io
import posixpath
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"

DOCUMENT_PART = "word/document.xml"
RELS_PART = "word/_rels/document.xml.rels"
CORE_PART = "docProps/core.xml"

DC = "{http://purl.org/dc/elements/1.1/}"
TOC_TITLES = {"目录", "目 录", "contents", "table of contents"}

_HEADING_STYLE = re.compile(r"^heading\s*([1-6])$", re.I)
_TITLE_STYLES = {"title", "subtitle"}


@dataclass(frozen=True)
class DocxBlock:
    """One semantic block. `kind` is the block vocabulary used by the pipeline."""

    kind: str                      # heading | paragraph | list | table | image
    text: str = ""
    level: int = 0                 # heading level 1–6, or list depth
    rows: tuple[tuple[str, ...], ...] = ()
    asset: str = ""                # part name, e.g. word/media/image1.png
    style: str = ""                # w:pStyle value, kept for debugging

    def as_dict(self) -> dict:
        data: dict = {"kind": self.kind}
        if self.text:
            data["text"] = self.text
        if self.level:
            data["level"] = self.level
        if self.rows:
            data["rows"] = [list(row) for row in self.rows]
        if self.asset:
            data["asset"] = self.asset
        if self.style:
            data["style"] = self.style
        return data


@dataclass(frozen=True)
class DocxOutline:
    """The `docx_outline` handover artefact."""

    title: str
    blocks: tuple[DocxBlock, ...]
    assets: dict[str, bytes] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    @property
    def counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for block in self.blocks:
            counts[block.kind] = counts.get(block.kind, 0) + 1
        return counts

    @property
    def headings(self) -> tuple[DocxBlock, ...]:
        return tuple(b for b in self.blocks if b.kind == "heading")

    def as_dict(self) -> dict:
        """Machine-readable form (external agents drive this)."""
        return {
            "title": self.title,
            "blocks": [b.as_dict() for b in self.blocks],
            "assets": sorted(self.assets),
            "counts": self.counts,
            "warnings": list(self.warnings),
        }


class DocxIntakeError(ValueError):
    """The upload is not a .docx we can read — say so, do not half-parse it."""

    code = "docx_unreadable"

    def __init__(self, message: str):
        super().__init__(message)


def _read(source: bytes | str | Path) -> tuple[dict[str, bytes], list[str]]:
    raw = source if isinstance(source, bytes) else Path(source).read_bytes()
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            parts = {name: archive.read(name) for name in archive.namelist()}
    except zipfile.BadZipFile as exc:
        raise DocxIntakeError(f"不是有效的 docx（zip 读取失败）：{exc}") from exc
    if DOCUMENT_PART not in parts:
        raise DocxIntakeError("docx 里找不到 word/document.xml")
    return parts, sorted(parts)


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


def parse_docx(source: bytes | str | Path) -> DocxOutline:
    """Parse a .docx into a `docx_outline`. Raises DocxIntakeError when unreadable."""
    parts, names = _read(source)
    rels = _relationships(parts)
    document = ET.fromstring(parts[DOCUMENT_PART])

    blocks: list[DocxBlock] = []
    assets: dict[str, bytes] = {}
    warnings: list[str] = []
    title = ""

    for node in _body_children(document):
        if node.tag == W + "tbl":
            rows = _table_rows(node)
            if rows:
                blocks.append(DocxBlock(kind="table", rows=rows))
            continue
        if node.tag != W + "p":
            warnings.append(f"忽略未知块级元素 {node.tag.split('}')[-1]}")
            continue

        text = _paragraph_text(node)
        style = _paragraph_style(node)

        for part in _image_parts(node, rels):
            if part in parts:
                assets[part] = parts[part]
                blocks.append(DocxBlock(kind="image", asset=part, text=text))
            else:
                warnings.append(f"图片引用指向缺失的部件：{part}")

        if not text:
            continue

        match = _HEADING_STYLE.match(style)
        if match:
            level = int(match.group(1))
            blocks.append(DocxBlock(kind="heading", text=text, level=level, style=style))
            continue
        if style.lower() in _TITLE_STYLES:
            title = title or text
            blocks.append(DocxBlock(kind="heading", text=text, level=1, style=style))
            continue

        is_list, depth = _list_info(node)
        if is_list:
            blocks.append(DocxBlock(kind="list", text=text, level=depth, style=style))
        else:
            blocks.append(DocxBlock(kind="paragraph", text=text, style=style))

    if not title:
        # 真实文档里第一个 Heading1 常常是「目录」。核心属性里的 dc:title
        # 更可信；没有再退回第一个非目录标题。
        title = _core_title(parts)
    if not title:
        first_heading = next(
            (b for b in blocks
             if b.kind == "heading" and b.text.strip().lower() not in TOC_TITLES),
            None)
        title = first_heading.text if first_heading else ""

    # 说出丢了什么，而不是静默吞掉——降级清单是交付物的一部分。
    unsupported = [n for n in names if n.startswith("word/")
                   and n not in (DOCUMENT_PART, RELS_PART)
                   and not n.startswith("word/media/")
                   and not n.startswith("word/theme/")
                   and not n.startswith("word/fontTable")]
    if unsupported:
        warnings.append(f"未读取的部件 {len(unsupported)} 个：" + "、".join(sorted(unsupported)[:6]))
    if not blocks:
        warnings.append("文档没有可读的正文块")

    return DocxOutline(title=title, blocks=tuple(blocks), assets=assets, warnings=tuple(warnings))
