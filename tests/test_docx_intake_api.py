"""Word 导入审核台 API 门禁（v0.8.1 · step 3 的服务器半边）。

上传 → 提案 → 采纳，走真实 HTTP 与真实生成用例：断言目录落地、产物里是
Word 自己的正文，而不是演示文案。
"""

from __future__ import annotations

import base64
import io
import zipfile
from pathlib import Path

import pytest
from test_server_project_api import request as api_request

from tests.conftest import WorkbenchServer

DOCX_CT = ("<?xml version='1.0' encoding='UTF-8'?>"
           "<Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'>"
           "<Default Extension='xml' ContentType='application/xml'/>"
           "<Override PartName='/word/document.xml' ContentType='application/vnd.openxmlformats-"
           "officedocument.wordprocessingml.document.main+xml'/></Types>")
DOCX_RELS = ("<?xml version='1.0' encoding='UTF-8'?>"
             "<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'>"
             "<Relationship Id='rId1' Type='http://schemas.openxmlformats.org/officeDocument/2006/"
             "relationships/officeDocument' Target='word/document.xml'/></Relationships>")


def _p(text: str, style: str = "") -> str:
    ppr = f"<w:pPr><w:pStyle w:val='{style}'/></w:pPr>" if style else ""
    return f"<w:p>{ppr}<w:r><w:t>{text}</w:t></w:r></w:p>"


def _table(rows: list[list[str]]) -> str:
    body = ""
    for row in rows:
        cells = "".join(
            f"<w:tc><w:p><w:r><w:t>{cell}</w:t></w:r></w:p></w:tc>" for cell in row)
        body += f"<w:tr>{cells}</w:tr>"
    return f"<w:tbl>{body}</w:tbl>"


def build_docx(*, title: str = "季度交付说明") -> bytes:
    document = (
        "<?xml version='1.0' encoding='UTF-8'?>"
        "<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'>"
        "<w:body>"
        + _p(title, "Title")
        + _p("一、背景", "Heading1")
        + _p("这是 Word 里的背景正文。")
        + _p("二、方案", "Heading1")
        + _p("方案说明文字。")
        + _table([["指标", "数值"], ["转化", "12%"]])
        + _p("三、空章节", "Heading1")
        + "</w:body></w:document>")
    core = ("<?xml version='1.0' encoding='UTF-8'?>"
            "<cp:coreProperties xmlns:cp='http://schemas.openxmlformats.org/package/2006/"
            "metadata/core-properties' xmlns:dc='http://purl.org/dc/elements/1.1/'>"
            f"<dc:title>{title}</dc:title></cp:coreProperties>")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as pack:
        pack.writestr("[Content_Types].xml", DOCX_CT)
        pack.writestr("_rels/.rels", DOCX_RELS)
        pack.writestr("word/document.xml", document)
        pack.writestr("docProps/core.xml", core)
    return buffer.getvalue()


def upload_payload(data: bytes | None = None, **extra) -> dict:
    body = {"name": "季度交付说明.docx"}
    if data is not None:
        body["docx_base64"] = base64.b64encode(data).decode("ascii")
    body.update(extra)
    return body


@pytest.fixture()
def workbench(tmp_path: Path):
    with WorkbenchServer(tmp_path / "output") as server:
        yield server


def test_upload_returns_a_reviewable_proposal(workbench):
    payload, _ = api_request(workbench.base_url, "/api/intake/docx", "POST",
                             upload_payload(build_docx()))

    assert payload["source"]["title"] == "季度交付说明"
    assert payload["counts"]["heading"] >= 3
    assert payload["counts"]["table"] == 1
    proposal = payload["proposal"]
    assert proposal["intent"] in {"doc", "landing", "dashboard", "deck", "poster", "archdoc"}
    assert proposal["style"]["preset_id"]
    assert proposal["style"]["reason"]
    assert proposal["image_plan"], "提案必须带图片位"
    assert payload["limitations"], "解析边界必须随提案一起返回"


@pytest.mark.parametrize("data,code", [
    (None, "docx_upload_required"),
    (b"not a docx at all", "docx_unreadable"),
])
def test_upload_errors_name_the_reason(workbench, data, code):
    payload, _ = api_request(workbench.base_url, "/api/intake/docx", "POST",
                             upload_payload(data), expected=400)

    assert payload["error"]["code"] == code


def test_upload_rejects_broken_base64(workbench):
    payload, _ = api_request(workbench.base_url, "/api/intake/docx", "POST",
                             {"docx_base64": "%%%not-base64%%%"}, expected=400)

    assert payload["error"]["code"] == "docx_upload_invalid"


def test_adopt_renders_the_word_prose_into_a_real_project(workbench):
    payload, _ = api_request(workbench.base_url, "/api/intake/docx/adopt", "POST",
                             upload_payload(build_docx()))

    assert payload["ok"] is True
    assert payload["docx"]["sections"] >= 2
    html = (Path(payload["project"]) / "output.html").read_text(encoding="utf-8")

    assert "这是 Word 里的背景正文。" in html
    assert "方案说明文字。" in html
    assert "12%" in html, "表格压平后的文字也要到产物里"
    assert "Your Product" not in html, "品牌为空时不能印占位符"
    assert any("表格已压成文本行" in item for item in payload["limitations"])


def test_review_desk_can_change_intent_and_preset_before_adopting(workbench):
    payload, _ = api_request(
        workbench.base_url, "/api/intake/docx/adopt", "POST",
        upload_payload(build_docx(),
                       proposal={"intent": "poster", "style": {"preset_id": "vercel-dark"}}))

    assert payload["intent"] == "poster"
    assert payload["preset_id"] == "vercel-dark"
    html = (Path(payload["project"]) / "output.html").read_text(encoding="utf-8")
    assert "这是 Word 里的背景正文。" in html


def test_adopt_refuses_an_intent_the_desk_cannot_render(workbench):
    payload, _ = api_request(
        workbench.base_url, "/api/intake/docx/adopt", "POST",
        upload_payload(build_docx(), proposal={"intent": "hologram"}), expected=400)

    assert payload["error"]["code"] == "docx_proposal_invalid"


def test_adopt_can_drop_an_image_slot(workbench):
    one_slot = [{"slot": "cover", "purpose": "封面主视觉", "prompt": "深蓝像素花园"}]
    payload, _ = api_request(
        workbench.base_url, "/api/intake/docx/adopt", "POST",
        upload_payload(build_docx(), proposal={"image_plan": one_slot}))

    assert payload["ok"] is True


@pytest.mark.parametrize("intent", ["landing", "dashboard", "deck", "poster", "archdoc", "doc"])
def test_every_intent_survives_the_real_generation_chain(workbench, intent):
    """真链：HTTP → 解析 → 提案 → 生成用例 → 磁盘产物，六个意图逐个走一遍。"""
    payload, _ = api_request(
        workbench.base_url, "/api/intake/docx/adopt", "POST",
        upload_payload(build_docx(), proposal={"intent": intent}))

    assert payload["intent"] == intent
    html = (Path(payload["project"]) / "output.html").read_text(encoding="utf-8")
    assert "这是 Word 里的背景正文。" in html, f"{intent} 丢了正文"
    assert payload["verification"]["ok"] is not False
