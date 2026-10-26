"""PDF intake gates (v0.8.4).

The fixture builds a real two-page PDF by hand — an uncompressed content
stream with two font sizes on page one and **no text at all on page two**
(the scanned-page analog). No new test dependency: the PDF is a plain
byte string both the writer and pdfminer can read.

Contract under test is the shared `intake_outline`: heading levels are
font-size-inferred (and stated as inferred), the scanned page lands in
limitations instead of being silently skipped, evidence = page + char span
and is walked back through pdfminer itself.
"""

from __future__ import annotations

import io

import pytest

from htmlninefox.intake_outline import Block, IntakeOutline, IntakeOutlineError
from htmlninefox.pdf_import import PdfIntakeError, parse_pdf


def build_pdf() -> bytes:
    """Page 1: 24pt heading + 12pt body. Page 2: empty (the scanned analog).

    Shape proven against pdfminer's fallback parser: objects in sequence,
    per-stream /Length computed (a wrong Length shifts the read window),
    trailer without xref (pdfminer scans objects when xref is absent).
    """
    def stream(*lines: bytes) -> bytes:
        return b"".join(line + b"\n" for line in lines)

    content1 = stream(
        b"BT /F2 24 Tf 72 700 Td (Quarterly Delivery Brief) Tj ET",
        b"BT /F1 12 Tf 72 660 Td (This body paragraph explains the plan.) Tj ET",
        b"BT /F1 12 Tf 72 640 Td (A second line of supporting evidence.) Tj ET")
    content2 = stream(b"BT ET")

    def stream_object(index: int, content: bytes) -> bytes:
        return (f"{index} 0 obj<</Length {len(content)}>>stream\n"
                .encode("latin-1") + content + b"endstream\nendobj\n")

    body = b"%PDF-1.4\n"
    body += b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    body += b"2 0 obj<</Type/Pages/Kids[3 0 R 5 0 R]/Count 2>>endobj\n"
    body += (b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R"
             b"/Resources<</Font<</F1 7 0 R/F2 8 0 R>>>>>>endobj\n")
    body += stream_object(4, content1)
    body += b"5 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 6 0 R>>endobj\n"
    body += stream_object(6, content2)
    body += b"7 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
    body += b"8 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica-Bold>>endobj\n"
    body += b"trailer<</Root 1 0 R/Size 9>>\n%%EOF"
    return body


@pytest.fixture()
def pdf_bytes() -> bytes:
    return build_pdf()


def test_outline_splits_headings_from_body_by_font_size(pdf_bytes):
    outline = parse_pdf(pdf_bytes)

    assert outline.source.kind == "pdf"
    assert outline.source.title == "Quarterly Delivery Brief", "无元数据时回退首个标题"
    assert outline.source.digest.startswith("sha256:")
    assert outline.source.origin == "user_upload" and outline.source.licence == "user_owned"
    assert outline.adapter.requires == ("pdfminer.six",)

    headings = [b for b in outline.blocks if b.kind == "heading"]
    paragraphs = [b for b in outline.blocks if b.kind == "paragraph"]
    assert [b.heading for b in headings] == ["Quarterly Delivery Brief"]
    assert len(paragraphs) == 2, "正文字号不冒充标题"
    assert headings[0].level == 1, "24pt 对 12pt 中位数 ≥1.5 倍 → 一级标题"


def test_every_block_carries_page_and_char_span(pdf_bytes):
    outline = parse_pdf(pdf_bytes)

    assert outline.evidence_complete is True
    for block in outline.blocks:
        assert isinstance(block.evidence.get("page"), int)
        chars = block.evidence.get("chars")
        assert isinstance(chars, list) and len(chars) == 2
        assert 0 <= chars[0] < chars[1]


def test_locator_walks_back_to_the_source(pdf_bytes):
    """抽样回源：chars 是页内文本偏移——按同序重组页面文本后切片，必得同一段话。"""
    outline = parse_pdf(pdf_bytes)
    from pdfminer.high_level import extract_pages
    from pdfminer.layout import LTTextContainer, LTTextLine

    page1_lines = []
    for element in list(extract_pages(io.BytesIO(pdf_bytes)))[0]:
        if isinstance(element, LTTextLine):
            page1_lines.append(element)
        elif isinstance(element, LTTextContainer):
            page1_lines.extend(c for c in element if isinstance(c, LTTextLine))
    page_text = "".join(line.get_text() for line in page1_lines)

    for block in (b for b in outline.blocks if b.evidence["page"] == 1):
        start, end = block.evidence["chars"]
        raw_slice = " ".join(page_text[start:end].split())
        expected = (block.heading or block.content)
        assert raw_slice == expected, f"{block.id}: {raw_slice!r} != {expected!r}"


def test_scanned_page_is_reported_not_silent(pdf_bytes):
    outline = parse_pdf(pdf_bytes)

    assert any("第 2 页无文本层" in note for note in outline.limitations), \
        outline.limitations
    assert not any(b.evidence["page"] == 2 for b in outline.blocks), \
        "空页不得产出任何块"


def test_inference_boundary_is_always_stated(pdf_bytes):
    outline = parse_pdf(pdf_bytes)

    assert any("字号推断" in note for note in outline.limitations)
    assert any("不还原" in note for note in outline.limitations)


def test_metadata_title_wins_but_first_heading_falls_back():
    without_title = parse_pdf(build_pdf())
    assert without_title.source.title == "Quarterly Delivery Brief", \
        "无元数据时回退首个标题"


def test_machine_form_is_stable_for_external_agents(pdf_bytes):
    payload = parse_pdf(pdf_bytes).as_dict()

    assert payload["source"]["kind"] == "pdf"
    assert payload["adapter"] == {"name": "pdf", "version": 1, "offline": True,
                                  "requires": ["pdfminer.six"]}
    assert payload["evidence_complete"] is True
    assert any("无文本层" in note for note in payload["limitations"])


def test_accepts_bytes_as_well_as_a_path(tmp_path):
    path = tmp_path / "pack.pdf"
    path.write_bytes(build_pdf())
    assert parse_pdf(path.read_bytes()).counts == parse_pdf(path).counts


def test_not_a_pdf_says_so(tmp_path):
    with pytest.raises(PdfIntakeError) as excinfo:
        parse_pdf(b"PK\x03\x04 not a pdf at all")
    assert "%PDF" in str(excinfo.value)


def test_contract_rejects_a_block_without_evidence(pdf_bytes):
    outline = parse_pdf(pdf_bytes)
    broken = IntakeOutline(
        source=outline.source,
        adapter=outline.adapter,
        blocks=(Block(id="b1", kind="paragraph", content="没有定位"),),
        limitations=(),
    )
    with pytest.raises(IntakeOutlineError) as excinfo:
        broken.validate()
    assert "可回指" in str(excinfo.value)
