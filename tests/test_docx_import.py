"""docx intake gates (v0.8.1 step 1).

The fixture builds a real .docx with `zipfile`, so these tests exercise the
same path an upload takes: no python-docx, no network, no binary fixture in
the repo that nobody can inspect.
"""

from __future__ import annotations

import zipfile

import pytest

from htmlninefox.docx_import import DocxIntakeError, parse_docx

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"

DOCUMENT = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="{W_NS}" xmlns:r="{R_NS}" xmlns:a="{A_NS}">
  <w:body>
    <w:p><w:pPr><w:pStyle w:val="Title"/></w:pPr><w:r><w:t>交付说明文档</w:t></w:r></w:p>
    <w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>一、背景</w:t></w:r></w:p>
    <w:p><w:r><w:t>这是一段正文。</w:t></w:r></w:p>
    <w:p><w:pPr><w:pStyle w:val="Heading2"/></w:pPr><w:r><w:t>1.1 目标</w:t></w:r></w:p>
    <w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr></w:pPr>
      <w:r><w:t>第一条要点</w:t></w:r></w:p>
    <w:p><w:pPr><w:numPr><w:ilvl w:val="1"/><w:numId w:val="1"/></w:numPr></w:pPr>
      <w:r><w:t>缩进要点</w:t></w:r></w:p>
    <w:tbl>
      <w:tr><w:tc><w:p><w:r><w:t>指标</w:t></w:r></w:p></w:tc>
            <w:tc><w:p><w:r><w:t>数值</w:t></w:r></w:p></w:tc></w:tr>
      <w:tr><w:tc><w:p><w:r><w:t>转化</w:t></w:r></w:p></w:tc>
            <w:tc><w:p><w:r><w:t>12%</w:t></w:r></w:p></w:tc></w:tr>
    </w:tbl>
    <w:p><w:r><w:drawing><a:blip r:embed="rId5"/></w:drawing></w:r></w:p>
    <w:sectPr/>
  </w:body>
</w:document>
"""

RELS = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId5" Type="{R_NS}/image" Target="media/image1.png"/>
</Relationships>
"""


def build_docx(tmp_path, *, extra_parts: dict[str, bytes] | None = None,
               document: str | None = None):
    path = tmp_path / "brief.docx"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", document or DOCUMENT)
        archive.writestr("word/_rels/document.xml.rels", RELS)
        archive.writestr("word/media/image1.png", b"\x89PNG\r\n\x1a\nfake")
        for name, payload in (extra_parts or {}).items():
            archive.writestr(name, payload)
    return path


def test_outline_carries_headings_paragraphs_lists_and_tables(tmp_path):
    outline = parse_docx(build_docx(tmp_path))

    assert outline.title == "交付说明文档"
    kinds = [b.kind for b in outline.blocks]
    assert kinds.count("heading") == 3, kinds
    assert kinds.count("paragraph") == 1
    assert kinds.count("list") == 2
    assert kinds.count("table") == 1

    headings = [(b.text, b.level) for b in outline.headings]
    assert headings == [("交付说明文档", 1), ("一、背景", 1), ("1.1 目标", 2)]

    lists = [b for b in outline.blocks if b.kind == "list"]
    assert [b.level for b in lists] == [1, 2], "ilvl 0 → 深度 1，ilvl 1 → 深度 2"

    table = next(b for b in outline.blocks if b.kind == "table")
    assert table.rows == (("指标", "数值"), ("转化", "12%"))


def test_embedded_image_becomes_an_asset_candidate(tmp_path):
    outline = parse_docx(build_docx(tmp_path))

    assert "word/media/image1.png" in outline.assets
    assert outline.assets["word/media/image1.png"].startswith(b"\x89PNG")
    image = next(b for b in outline.blocks if b.kind == "image")
    assert image.asset == "word/media/image1.png"


def test_accepts_bytes_as_well_as_a_path(tmp_path):
    path = build_docx(tmp_path)
    assert parse_docx(path.read_bytes()).counts == parse_docx(path).counts


def test_unreadable_upload_says_so_instead_of_half_parsing(tmp_path):
    bad = tmp_path / "bad.docx"
    bad.write_bytes(b"not a zip at all")

    with pytest.raises(DocxIntakeError) as excinfo:
        parse_docx(bad)
    assert "zip" in str(excinfo.value)


def test_missing_document_part_is_reported(tmp_path):
    path = tmp_path / "empty.docx"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")

    with pytest.raises(DocxIntakeError) as excinfo:
        parse_docx(path)
    assert "word/document.xml" in str(excinfo.value)


def test_degradation_list_names_what_was_not_read(tmp_path):
    """丢掉的东西必须写出来——与导出侧的降级清单同一纪律。"""
    path = build_docx(tmp_path, extra_parts={"word/comments.xml": b"<comments/>"})
    outline = parse_docx(path)

    assert any("word/comments.xml" in warning for warning in outline.warnings), outline.warnings


def test_machine_form_is_stable_for_external_agents(tmp_path):
    payload = parse_docx(build_docx(tmp_path)).as_dict()

    assert payload["title"] == "交付说明文档"
    assert payload["counts"] == {"heading": 3, "paragraph": 1, "list": 2,
                                 "table": 1, "image": 1}
    assert payload["assets"] == ["word/media/image1.png"]
    assert payload["blocks"][0] == {"kind": "heading", "text": "交付说明文档",
                                    "level": 1, "style": "Title"}


# 真实商务文档的第一个 Heading1 常常就是「目录」——用它当标题会让整份
# 提案在审核台上显示成「目录」。
TOC_DOCUMENT = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="{W_NS}" xmlns:r="{R_NS}" xmlns:a="{A_NS}">
  <w:body>
    <w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>目录</w:t></w:r></w:p>
    <w:p><w:r><w:t>01 一、执行摘要</w:t></w:r></w:p>
    <w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>一、执行摘要</w:t></w:r></w:p>
  </w:body>
</w:document>
"""

CORE = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
  xmlns:dc="http://purl.org/dc/elements/1.1/">
  <dc:title>全域数字营销方案</dc:title>
</cp:coreProperties>"""


def test_core_properties_title_wins_over_the_toc_heading(tmp_path):
    path = build_docx(tmp_path, document=TOC_DOCUMENT,
                      extra_parts={"docProps/core.xml": CORE.encode("utf-8")})

    assert parse_docx(path).title == "全域数字营销方案"


def test_toc_heading_is_skipped_when_no_core_title(tmp_path):
    outline = parse_docx(build_docx(tmp_path, document=TOC_DOCUMENT))

    assert outline.title == "一、执行摘要", "「目录」不能当文档标题"
