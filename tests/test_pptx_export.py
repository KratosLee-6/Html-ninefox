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
