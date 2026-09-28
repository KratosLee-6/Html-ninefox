"""V0.6-S13: PPTX file bridge — controlled mapping from deck artifacts."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from htmlninefox import pipeline

pytest.importorskip("pptx", reason="python-pptx optional extra")


def _make_deck(tmp_path: Path) -> Path:
    return pipeline.run_expert(
        "做一个 AI 产品发布会 PPT，像素花园风格", intent_override="deck",
        output=str(tmp_path), quiet_llm=True)["work"]


def test_deck_artifact_exports_to_editable_pptx(tmp_path: Path) -> None:
    from htmlninefox import pptx_export

    work = _make_deck(tmp_path)
    report = pptx_export.export_deck_pptx(work)

    target = Path(report["file"])
    assert target.is_file() and target.suffix == ".pptx"
    assert report["slides"] >= 5, "生成的 deck 应有多个分页"
    assert isinstance(report["editable_elements"], int) and report["editable_elements"] > 0

    # 可编辑验证：用 python-pptx 重新打开，逐页存在文本框且标题非空
    from pptx import Presentation
    presentation = Presentation(str(target))
    assert len(presentation.slides) == report["slides"]
    first = presentation.slides[0]
    texts = [shape.text_frame.text for shape in first.shapes
             if shape.has_text_frame and shape.text_frame.text.strip()]
    assert texts, "首页应有可编辑文本"
    assert any(len(text) > 3 for text in texts)


def test_non_deck_artifact_is_rejected_with_clear_error(tmp_path: Path) -> None:
    from htmlninefox import pptx_export

    work = pipeline.run_expert(
        "做一个极简落地页", output=str(tmp_path), quiet_llm=True)["work"]
    with pytest.raises(RuntimeError, match="slide"):
        pptx_export.export_deck_pptx(work)


def test_parse_deck_slides_reports_flattened_visuals() -> None:
    from htmlninefox.pptx_export import parse_deck_slides
    html = (b"<html><body>"
            b'<section class="slide"><h1>One</h1><svg width="10"></svg></section>'
            b'<section class="slide"><h1>Two</h1></section></body></html>')
    slides = parse_deck_slides(html.decode("utf-8"))
    assert len(slides) == 2
    assert slides[0]["flattened"] == ["svg×1"]
    assert slides[1]["flattened"] == []


# ---------------------------------------------------------------- S13U-a slide editing API


def test_slides_edit_api_creates_revision_and_conflict_protects(tmp_path: Path) -> None:
    import json
    import time
    import urllib.error
    import urllib.request

    from htmlninefox import revisions
    from htmlninefox.server import app as server_app
    from tests.conftest import WorkbenchServer

    work = pipeline.run_expert("做一个发布会 PPT", intent_override="deck",
                               output=str(tmp_path), quiet_llm=True)["work"]
    with WorkbenchServer(tmp_path) as server:
        base = server.base_url

        def call(path, method="GET", payload=None, expected=200):
            data = json.dumps(payload).encode() if payload is not None else None
            request = urllib.request.Request(base + path, data=data, method=method,
                                             headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(request, timeout=15) as response:
                    assert response.status == expected
                    return json.loads(response.read().decode())
            except urllib.error.HTTPError as error:
                assert error.code == expected, error.read().decode()
                return json.loads(error.read().decode())

        slides_payload = call(f"/api/projects/{work.name}/slides")
        slides = slides_payload["slides"]
        current_revision = slides_payload["revision"]
        assert len(slides) >= 5
        assert slides[0]["texts"], "每个分页都应有可编辑文本节点"

        target = slides[1]["texts"][0]
        edits = [{"slide": target["slide"], "node": target["node"], "text": "编辑后的章节标题"}]

        conflict = call(f"/api/projects/{work.name}/slides", "PUT",
                        {"edits": edits, "expected_revision": current_revision + 99},
                        expected=409)
        assert conflict["error"]["code"] == "revision_conflict"

        empty = call(f"/api/projects/{work.name}/slides", "PUT",
                     {"edits": [], "expected_revision": current_revision}, expected=400)
        assert empty["error"]["code"] == "slides_edit_empty"

        result = call(f"/api/projects/{work.name}/slides", "PUT",
                      {"edits": edits, "expected_revision": current_revision})
        assert result["revision"] == current_revision + 1
        assert "编辑后的章节标题" in (work / "output.html").read_text(encoding="utf-8")
        # 生成新 Revision，历史保留
        history = [item["revision"] for item in revisions.history(work)]
        assert history == list(range(result["revision"] + 1))
