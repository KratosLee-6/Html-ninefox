"""导出中心 · 格式联动门禁（v0.8.2 B3-1）。

两个断言，都是截图评审发现的真问题：
  1. 选 Word / PPTX 时不许再让人填「画布宽高」——那两个字段对页面结构导出无意义
  2. 选 Word 时必须先讲清楚会丢什么（与后端 warnings、报告、回读同口径）
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "htmlninefox" / "server" / "static" / "index.html"
JS = ROOT / "htmlninefox" / "server" / "static" / "lifecycle-exports.js"


def test_canvas_size_fields_are_wrapped_so_they_can_hide():
    html = HTML.read_text(encoding="utf-8")

    assert 'id="export-width-field"' in html
    assert 'id="export-height-field"' in html


def test_file_bridge_formats_hide_canvas_size_and_show_degradation():
    js = JS.read_text(encoding="utf-8")

    assert "fileBridge" in js
    assert "widthField.hidden = fileBridge" in js
    assert "heightField.hidden = fileBridge" in js
    assert "DEGRADATION[format]" in js


def test_word_degradation_list_matches_the_backend_warnings():
    js = JS.read_text(encoding="utf-8")

    for fact in ("配色", "外链图片", "非语义"):
        assert fact in js, f"Word 降级清单缺少「{fact}」这一条"


def test_export_result_renders_server_warnings():
    js = JS.read_text(encoding="utf-8")

    assert "result.warnings" in js, "导出结果必须把后端 warnings 贴出来，不能只在报告里"
