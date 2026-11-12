"""0.9.5-B 交付包字体子集化门禁

纪律：①子集按产物实际用字（宁小勿全）；②无 fonttools / 无缓存字体时
交付包照旧、报告照实说（与联盟 fallback: skip 同一纪律）；③工作区
output.html 永不被改动 —— 内嵌只发生在交付包副本上。
"""

import sys

import pytest

from htmlninefox.fontsubset import (EMBED_SANS, _cache_dir, embed_fonts_into_html,
                                    extract_used_chars, font_capabilities,
                                    subset_font_woff)

_SAMPLE_HTML = """<!DOCTYPE html>
<html><head><title>狐构科技 · 季度简报</title>
<style>:root{--fox-font_body: 'Inter','PingFang SC','Microsoft YaHei',sans-serif;}</style></head>
<body><h1>狐构科技</h1><p>开发者平台一屏尽览 1+2=3</p>
<script>var x = "script 里的字不算";</script>
<style>.x{content: "style 里的字也不算"}</style>
</body></html>"""


@pytest.fixture()
def tiny_font(tmp_path):
    """fontTools 现造微 TTF（含测试字形），写进缓存目录的 catalog 名下。"""
    from fontTools.fontBuilder import FontBuilder
    from fontTools.pens.ttGlyphPen import TTGlyphPen

    text = ("狐构科技开发者平台一屏尽览季度简报"
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    glyphs = [".notdef"] + [f"g{i}" for i in range(len(text))]
    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder(glyphs)
    fb.setupCharacterMap({ord(ch): f"g{i}" for i, ch in enumerate(text)})
    glyf = {}
    for name in glyphs:
        pen = TTGlyphPen(None)
        pen.moveTo((0, 0)); pen.lineTo((500, 0)); pen.lineTo((250, 700)); pen.closePath()
        glyf[name] = pen.glyph()
    fb.setupGlyf(glyf)
    fb.setupHorizontalMetrics({n: (600, 50) for n in glyphs})
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200)
    fb.setupNameTable({"familyName": "FoxTestFont", "styleName": "Regular"})
    path = tmp_path / ".settings" / "fonts" / "NotoSansSC-Regular.woff2"
    path.parent.mkdir(parents=True)
    fb.save(str(path))
    return tmp_path


class TestExtract:
    def test_visible_text_only(self):
        chars = extract_used_chars(_SAMPLE_HTML)
        assert "狐" in chars and "构" in chars and "览" in chars
        assert "A" in chars, "ASCII 基础盘必须包含"
        for leaked in ("算", "容"):  # script/style 的字绝不能进子集
            assert leaked not in chars


class TestSubset:
    def test_subset_roundtrip_glyph_set(self, tiny_font):
        font_path = _cache_dir(tiny_font) / "NotoSansSC-Regular.woff2"
        used = extract_used_chars(_SAMPLE_HTML)
        data = subset_font_woff(font_path, used)
        assert len(data) < 64 * 1024, "微字体子集必须很小"
        import io

        from fontTools.ttLib import TTFont
        buf_font = TTFont(io.BytesIO(data))
        cmap = buf_font.getBestCmap()
        assert ord("狐") in cmap and ord("览") in cmap
        assert all(ord(c) in cmap for c in "Fox9"), "基础盘字形必须在"


class TestEmbed:
    def test_full_chain_with_cache(self, tiny_font):
        new_html, report = embed_fonts_into_html(_SAMPLE_HTML, tiny_font)
        assert report["embedded"], "有缓存字体必须内嵌"
        assert report["embedded"][0]["family"] == EMBED_SANS
        assert report["chars"] == len(extract_used_chars(_SAMPLE_HTML))
        assert "@font-face" in new_html and "data:font/woff;base64," in new_html
        assert f"'{EMBED_SANS}'," in new_html, "font 栈必须前插内嵌 family"
        assert new_html.endswith("</body></html>"), "正文收尾不受损"
        assert "<h1>狐构科技</h1>" in new_html, "正文内容不受损"
        assert new_html.index("@font-face") < new_html.index("<h1>"), "样式必须注入在 head 内"

    def test_no_cache_is_honest(self, tmp_path):
        tmp_path.mkdir(exist_ok=True)
        new_html, report = embed_fonts_into_html(_SAMPLE_HTML, tmp_path)
        assert new_html == _SAMPLE_HTML, "无缓存字体必须原样返回"
        assert report["embedded"] == [] and report["skipped"], "报告必须照实说"

    def test_no_fonttools_is_honest(self, tmp_path, monkeypatch):
        monkeypatch.setitem(sys.modules, "fontTools.subset", None)
        new_html, report = embed_fonts_into_html(_SAMPLE_HTML, tmp_path)
        assert new_html == _SAMPLE_HTML
        assert any("fonttools" in s for s in report["skipped"])


class TestCapabilities:
    def test_capabilities_report(self, tiny_font):
        caps = font_capabilities(tiny_font)
        assert caps["fonttools"] is True
        assert len(caps["cached_fonts"]) == 1
        assert caps["cached_fonts"][0]["bytes"] > 1024
