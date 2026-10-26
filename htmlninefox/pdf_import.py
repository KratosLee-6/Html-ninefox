"""PDF intake (v0.8.4): read a .pdf into an `intake_outline`.

`pdfminer.six` (pure Python) ships in the optional `[pdf]` extra — the same
discipline as `[docx]`/`[pptx]`: a missing extra is an honest pip hint, never
a silent install, and the offline promise stays intact.

Three honesty rules shape everything below (DESIGN-REVERSE-INTAKE §4):
1. **Only the text layer is trusted.** A page with no extractable text is
   reported ("第 N 页无文本层"), never OCR-guessed — OCR is a provider
   decision, not this adapter's business.
2. **Heading levels are inferred from font size**, so they are stated as
   inferred: a line whose largest glyph is ≥1.15× the document's median size
   (and short enough to be a title) becomes a heading. The inference rule
   rides in `limitations` where the review desk can see it.
3. **Tables are not reconstructed.** PDF tables are coordinate-collaged;
   rebuilding them yields "looks right, structurally wrong" blocks. We say
   so instead of guessing (宁小勿假).

The output is the shared `intake_outline` artefact: every block carries
`page` plus a per-page character span (`chars`), both contract locator keys,
and `validate()` refuses any block without a locator.
"""

from __future__ import annotations

import hashlib
import io
import statistics
from dataclasses import replace
from pathlib import Path

from .intake_outline import (
    AdapterInfo,
    Block,
    IntakeOutline,
    SourceInfo,
)

ADAPTER = AdapterInfo(name="pdf", version=1, offline=True, requires=("pdfminer.six",))

PDF_MAGIC = b"%PDF-"


class PdfIntakeError(ValueError):
    """The upload is not a .pdf we can read — say so, do not half-parse it."""

    code = "pdf_unreadable"


def _read(source: bytes | str | Path):
    raw = source if isinstance(source, bytes) else Path(source).read_bytes()
    try:
        from pdfminer.high_level import extract_pages
    except ImportError as exc:  # pragma: no cover - 可选 extra 守卫
        raise PdfIntakeError(
            "读取 PDF 需要 pdfminer.six：pip install 'htmlninefox[pdf]'") from exc
    if not raw.startswith(PDF_MAGIC):
        raise PdfIntakeError("不是有效的 PDF（缺少 %PDF- 文件头）")
    try:
        return list(extract_pages(io.BytesIO(raw))), raw
    except Exception as exc:
        raise PdfIntakeError(f"不是有效的 PDF（解析失败）：{exc}") from exc


def _metadata_title(raw: bytes) -> str:
    """The document Info dict's title, when the producer bothered to set one."""
    try:
        from pdfminer.pdfparser import PDFParser
        from pdfminer.pdfdocument import PDFDocument
        document = PDFDocument(PDFParser(io.BytesIO(raw)))
        return (document.info or [{}])[0].get("Title", "").strip()
    except Exception:
        return ""


def _line_text(line) -> str:
    return " ".join(line.get_text().split())


def _char_size(line) -> float:
    sizes = [char.size for char in line
             if hasattr(char, "size") and isinstance(char.size, (int, float))]
    return max(sizes) if sizes else 0.0


def parse_pdf(source: bytes | str | Path) -> IntakeOutline:
    """Parse a .pdf into an `intake_outline`.

    `source` may be a path, a Path, or the uploaded bytes. Raises
    PdfIntakeError when the file cannot be read at all; anything readable
    but weak (no text layer, no title) lands in `limitations` instead.
    """
    pages, raw = _read(source)

    blocks: list[Block] = []
    limitations: list[str] = [
        "版面不还原：坐标拼版与表格结构不还原，产出「结构对、样式朴素」的块",
        "标题层级由字号推断（≥正文中位数的 1.15 倍视为标题），可能与作者意图有出入",
    ]

    # 全文档字号中位数：推断标题的基准（先扫一遍再产块）。
    # pdfminer 的常见布局：页顶层是 LTTextBox（容器），文本行在其子级
    # （LTTextLineHorizontal）；个别 PDF 也会把行直接放在页顶层。两层都收。
    from pdfminer.layout import LTTextContainer, LTTextLine
    all_sizes: list[float] = []
    page_lines: list[tuple[int, list]] = []
    for number, page in enumerate(pages, start=1):
        lines: list = []
        for element in page:
            if isinstance(element, LTTextLine):
                lines.append(element)
            elif isinstance(element, LTTextContainer):
                lines.extend(child for child in element
                             if isinstance(child, LTTextLine))
        page_lines.append((number, lines))
        for line in lines:
            size = _char_size(line)
            if size:
                all_sizes.append(size)
    median_size = statistics.median(all_sizes) if all_sizes else 0.0

    images_total = 0
    for number, lines in page_lines:
        if not lines:
            limitations.append(f"第 {number} 页无文本层，未提取文字（可能为扫描件或纯图页）")
            continue
        images_total += sum(
            1 for element in pages[number - 1]
            if type(element).__name__ == "LTImage")
        # 同页拼接文本的字符区间：先按版面顺序串起来，块定位用 [start, end]
        offset = 0
        for line in lines:
            text = _line_text(line)
            span = sum(len(line.get_text()) for line in [line])
            if not text:
                offset += span
                continue
            evidence = {"page": number, "chars": [offset, offset + span]}
            size = _char_size(line)
            is_heading = (
                median_size > 0 and size >= median_size * 1.15
                and len(text) <= 120
            )
            if is_heading:
                level = 1 if size >= median_size * 1.5 else 2
                blocks.append(Block(
                    id=f"p{number}-c{offset}", kind="heading", heading=text,
                    level=level, evidence=evidence, provenance="verbatim"))
            else:
                blocks.append(Block(
                    id=f"p{number}-c{offset}", kind="paragraph", content=text,
                    evidence=evidence, provenance="verbatim"))
            offset += span

    if images_total:
        limitations.append(f"检测到 {images_total} 张内嵌图片，未提取（图片资产环节见 v0.8.4 次项）")

    title = _metadata_title(raw)
    if not title:
        first_heading = next(
            (b for b in blocks if b.kind == "heading" and b.heading), None)
        title = first_heading.heading if first_heading else ""
    if not blocks:
        limitations.append("PDF 没有可读的文本内容（全文扫描件？）")
    if not title:
        limitations.append("PDF 没有标题：元数据与首行标题都没有")

    ref = (source if isinstance(source, str)
           else str(source) if isinstance(source, Path) else "upload://pdf")
    return IntakeOutline(
        source=SourceInfo(kind="pdf", ref=ref, title=title,
                          digest="sha256:" + hashlib.sha256(raw).hexdigest(),
                          origin="user_upload", licence="user_owned"),
        adapter=ADAPTER,
        blocks=tuple(replace(block, ordinal=i) for i, block in enumerate(blocks)),
        limitations=tuple(dict.fromkeys(limitations)),
    ).validate()
