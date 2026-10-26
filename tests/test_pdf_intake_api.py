"""PDF 导入审核台 API 门禁（v0.8.4）。

镜像 test_pptx_intake_api 的纪律：真实 HTTP → 解析 → 提案 → 采纳 → 真实
生成用例 → 磁盘产物，断言产物里是这份 PDF 自己的正文；解析边界（扫描页、
字号推断）必须随响应到达客户端。
"""

from __future__ import annotations

import base64
from pathlib import Path

import pytest
from test_pdf_import import build_pdf
from test_server_project_api import request as api_request

from tests.conftest import WorkbenchServer


def upload_payload(data: bytes | None = None, **extra) -> dict:
    body = {"name": "brief.pdf"}
    if data is not None:
        body["pdf_base64"] = base64.b64encode(data).decode("ascii")
    body.update(extra)
    return body


@pytest.fixture()
def workbench(tmp_path: Path):
    with WorkbenchServer(tmp_path / "output") as server:
        yield server


def test_upload_returns_a_reviewable_proposal(workbench):
    payload, _ = api_request(workbench.base_url, "/api/intake/pdf", "POST",
                             upload_payload(build_pdf()))

    assert payload["source"]["kind"] == "pdf"
    assert payload["source"]["title"] == "Quarterly Delivery Brief"
    assert payload["counts"]["heading"] == 1
    assert payload["counts"]["paragraph"] == 2
    proposal = payload["proposal"]
    assert proposal["intent"] in {"doc", "archdoc", "landing", "dashboard", "deck", "poster"}
    assert proposal["style"]["preset_id"]
    assert any("无文本层" in note for note in payload["limitations"]), \
        "扫描页边界必须随响应到达客户端"
    assert any("字号推断" in note for note in payload["limitations"])
    assert payload["evidence_complete"] is True


@pytest.mark.parametrize("data,code", [
    (None, "pdf_upload_required"),
    (b"PK\x03\x04 definitely not a pdf", "pdf_unreadable"),
])
def test_upload_errors_name_the_reason(workbench, data, code):
    payload, _ = api_request(workbench.base_url, "/api/intake/pdf", "POST",
                             upload_payload(data), expected=400)

    assert payload["error"]["code"] == code


def test_upload_rejects_broken_base64(workbench):
    payload, _ = api_request(workbench.base_url, "/api/intake/pdf", "POST",
                             {"pdf_base64": "%%%not-base64%%%"}, expected=400)

    assert payload["error"]["code"] == "pdf_upload_invalid"


def test_adopt_renders_the_pdf_prose_into_a_real_project(workbench):
    payload, _ = api_request(workbench.base_url, "/api/intake/pdf/adopt", "POST",
                             upload_payload(build_pdf()))

    assert payload["ok"] is True
    assert payload["pdf"]["sections"] >= 1
    html = (Path(payload["project"]) / "output.html").read_text(encoding="utf-8")

    assert "This body paragraph explains the plan." in html, "PDF 正文要进产物"
    assert "Your Product" not in html, "品牌为空时不能印占位符"
    assert any("无文本层" in item for item in payload["limitations"])


def test_review_desk_can_change_intent_and_preset_before_adopting(workbench):
    payload, _ = api_request(
        workbench.base_url, "/api/intake/pdf/adopt", "POST",
        upload_payload(build_pdf(),
                       proposal={"intent": "deck", "style": {"preset_id": "vercel-dark"}}))

    assert payload["intent"] == "deck"
    assert payload["preset_id"] == "vercel-dark"
    html = (Path(payload["project"]) / "output.html").read_text(encoding="utf-8")
    assert "This body paragraph explains the plan." in html


def test_adopt_refuses_an_intent_the_desk_cannot_render(workbench):
    payload, _ = api_request(
        workbench.base_url, "/api/intake/pdf/adopt", "POST",
        upload_payload(build_pdf(), proposal={"intent": "hologram"}), expected=400)

    assert payload["error"]["code"] == "pdf_proposal_invalid"


@pytest.mark.parametrize("intent", ["landing", "dashboard", "deck", "poster", "archdoc", "doc"])
def test_every_intent_survives_the_real_generation_chain(workbench, intent):
    """真链：HTTP → 解析 → 提案 → 生成用例 → 磁盘产物，六个意图逐个走一遍。"""
    payload, _ = api_request(
        workbench.base_url, "/api/intake/pdf/adopt", "POST",
        upload_payload(build_pdf(), proposal={"intent": intent}))

    assert payload["intent"] == intent
    html = (Path(payload["project"]) / "output.html").read_text(encoding="utf-8")
    assert "This body paragraph explains the plan." in html, f"{intent} 丢了 PDF 正文"
    assert payload["verification"]["ok"] is not False


def test_image_inspection_endpoint_reports_the_asset(workbench):
    """图片资产环节：上传 → 检查（尺寸 + 主色），不做任何结构假装。"""
    from PIL import Image
    import io as _io
    buffer = _io.BytesIO()
    Image.new("RGB", (30, 10), (98, 60, 234)).save(buffer, format="PNG")

    payload, _ = api_request(workbench.base_url, "/api/intake/image", "POST",
                             {"image_base64": base64.b64encode(buffer.getvalue()).decode()})
    assert payload["ok"] is True
    assert payload["asset"]["format"] == "png"
    assert (payload["asset"]["width"], payload["asset"]["height"]) == (30, 10)
    assert payload["asset"]["color_source"] == "pillow"


def test_image_inspection_endpoint_rejects_garbage(workbench):
    payload, _ = api_request(workbench.base_url, "/api/intake/image", "POST",
                             {"image_base64": base64.b64encode(b"not an image").decode()},
                             expected=400)
    assert payload["error"]["code"] == "image_asset_invalid"

    payload, _ = api_request(workbench.base_url, "/api/intake/image", "POST", {},
                             expected=400)
    assert payload["error"]["code"] == "image_upload_required"
