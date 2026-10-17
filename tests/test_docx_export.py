"""DOCX 语义导出门禁（v0.8.0）。

三条纪律，对应 PLAN-v0.8.md 的验收判据：

1. **映射真实到达**：样例 HTML 里的每个语义块（标题层级/段落/列表/表格/
   内嵌图/引用/分隔/代码块）必须在 .docx 里逐项找到——用 python-docx 回读
   断言，不信任「导出成功」返回值。
2. **降级清单完整性**：报告声称保留的计数 == 源 HTML 的实际数量 ==
   docx 回读的计数；声称降级的（外链图/扁平化视觉/非语义容器文本）在
   docx 里必须真不存在。降级清单是承诺，不是免责声明。
3. **意图分工如实**：landing 强行导 docx 得到 400 引导（不是静默给出
   一个错误的 Word 文件）；deck 得到讲义；未装 python-docx 得到 pip 提示。

附带一条无依赖冒烟：.docx 是 zip，标准库直接读 document.xml 断言标题
文本在——不依赖 python-docx 的那条路径永不跳过（照 PPTX 的 zipfile 惯例）。
"""
from __future__ import annotations

import io
import json
import re
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from htmlninefox import docx_export, exporting  # noqa: E402
from htmlninefox.server.storage import StoreError  # noqa: E402

try:
    import docx  # noqa: F401
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

SAMPLE = """<!doctype html>
<html><head><title>季度交付报告</title></head>
<body><main>
<h1>季度交付报告</h1>
<h2>第一章 · 背景</h2>
<p>本季度完成了九尾狐交付链路的第一个闭环。</p>
<p>第二段说明背景细节。</p>
<h2>第二章 · 数据</h2>
<table><tr><th>指标</th><th>数值</th></tr><tr><td>命中率</td><td>92%</td></tr></table>
<ul><li>第一项</li><li>第二项</li></ul>
<ol><li>步骤一</li><li>步骤二</li></ol>
<blockquote>引用客户的原话评价。</blockquote>
<hr>
<pre><code>pip install htmlninefox[docx]</code></pre>
<p>内嵌图：<img alt="架构图" src="data:image/png;base64,{png_b64}"></p>
<p>外链图（离线不抓）：<img alt="远景" src="https://example.com/far.png"></p>
<svg width="10" height="10"></svg>
<div class="hero">游离在语义容器外的文字</div>
</main></body></html>"""


def _png_base64() -> str:
    # 1×1 PNG，最小合法载荷
    return ("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
            "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")


def _make_project(tmp_path: Path, html: str) -> Path:
    project = tmp_path / "proj"
    project.mkdir()
    (project / "output.html").write_text(
        html.replace("{png_b64}", _png_base64()), encoding="utf-8")
    return project


def _readback(path: Path):
    from docx import Document
    return Document(str(path))


def _paragraph_text(paragraph) -> str:
    return paragraph.text


@pytest.mark.skipif(not HAS_DOCX, reason="python-docx 未安装（pip install 'htmlninefox[docx]'）")
class TestDeepReadback:
    """需要 python-docx 的深度回读。dev extra 已含 python-docx，CI 必跑。"""

    def test_every_semantic_block_reaches_the_document(self, tmp_path):
        project = _make_project(tmp_path, SAMPLE)
        report = docx_export.export_document_docx(project)
        doc = _readback(Path(report["file"]))

        headings = [p.text for p in doc.paragraphs if p.style.name.startswith("Heading")]
        assert "季度交付报告" in headings and "第一章 · 背景" in headings, \
            f"标题层级未到达：{headings}"
        level_of = {p.text: p.style.name for p in doc.paragraphs if p.style.name.startswith("Heading")}
        assert level_of.get("第一章 · 背景") == "Heading 2", f"层级映射错误：{level_of}"

        bullets = [p.text for p in doc.paragraphs if p.style.name == "List Bullet"]
        numbers = [p.text for p in doc.paragraphs if p.style.name == "List Number"]
        assert {"第一项", "第二项"} <= set(bullets), f"无序列表未到达：{bullets}"
        assert {"步骤一", "步骤二"} <= set(numbers), f"有序列表未到达：{numbers}"

        quote = [p.text for p in doc.paragraphs if p.style.name == "Intense Quote"]
        assert quote == ["引用客户的原话评价。"], f"引用未到达：{quote}"

        code_text = "\n".join(p.text for p in doc.paragraphs)
        assert "pip install htmlninefox[docx]" in code_text, "代码块未到达"

        assert len(doc.tables) == 1 and doc.tables[0].rows[0].cells[0].text == "指标", \
            "表格未到达"
        assert len(doc.inline_shapes) == 1, "内嵌图片未到达"

    def test_degradation_report_is_complete_and_honest(self, tmp_path):
        """声称保留的计数 == 源数量 == docx 回读；声称丢弃的真不在文档里。"""
        project = _make_project(tmp_path, SAMPLE)
        report = docx_export.export_document_docx(project)
        doc = _readback(Path(report["file"]))
        source = (project / "output.html").read_text(encoding="utf-8")

        mapped = report["mapped"]
        assert mapped["headings"] == len(re.findall(r"<h[1-6]", source, re.I)), \
            f"标题计数与源不符：{mapped['headings']}"
        assert mapped["tables"] == 1 and len(doc.tables) == mapped["tables"]
        assert mapped["images_embedded"] == 1 and len(doc.inline_shapes) == 1

        degraded = report["degraded"]
        assert len(degraded["external_images"]) == 1, "外链图未如实上报"
        assert "example.com/far.png" in degraded["external_images"][0]
        # 声称丢弃的：外链图不能以图片形式出现在文档里
        assert len(doc.inline_shapes) == mapped["images_embedded"], \
            "报告称只内嵌 1 图，文档里却有更多——降级清单在撒谎"
        assert degraded["flattened"].get("svg") == len(re.findall(r"<svg", source, re.I)), \
            "扁平化计数与源不符"
        assert degraded["unmapped_text_chars"] >= len("游离在语义容器外的文字"), \
            "非语义容器文本未如实上报"
        # chrome（nav/footer 等）不是内容降级——单独计数，不在正文里
        full_text = "\n".join(p.text for p in doc.paragraphs)
        assert "游离在语义容器外的文字" not in full_text, \
            "被上报为 unmapped 的文字却出现在了文档里——降级清单在撒谎"

    def test_deck_becomes_a_handout_outline(self, tmp_path):
        html = ("<!doctype html><html><head><title>发布会</title></head><body>"
                + "".join(
                    f'<section class="slide"><h1>第{i}页标题</h1><p>要点{i}-甲</p>'
                    f'<p>要点{i}-乙</p></section>' for i in range(1, 4))
                + "</body></html>")
        project = _make_project(tmp_path, html)
        report = docx_export.export_deck_handout_docx(project)
        assert report["mode"] == "deck-handout" and report["slides"] == 3
        doc = _readback(Path(report["file"]))
        h2 = [p.text for p in doc.paragraphs if p.style.name == "Heading 2"]
        assert h2 == ["第 1 页 · 第1页标题", "第 2 页 · 第2页标题", "第 3 页 · 第3页标题"], \
            f"讲义大纲未按页到达：{h2}"
        bullets = [p.text for p in doc.paragraphs if p.style.name == "List Bullet"]
        assert "要点2-甲" in bullets, "页内要点未到达"

    def test_empty_document_gets_pdf_guidance(self, tmp_path):
        project = _make_project(tmp_path, "<html><body><main></main></body></html>")
        with pytest.raises(RuntimeError, match="PDF / PNG"):
            docx_export.export_document_docx(project)


class TestHonestBoundaries:
    """不依赖 python-docx 的路径——永不跳过。"""

    def test_visual_intents_get_guidance_not_a_wrong_file(self, tmp_path):
        project = _make_project(tmp_path, "<html><body>landing</body></html>")
        manifest = {"project_path": str(project), "project_name": "proj",
                    "intent": "landing", "source_file": "output.html",
                    "warnings": [], "compatibility_score": 90}
        with pytest.raises(StoreError) as exc_info:
            exporting._export_docx(project, {"format": "docx"}, manifest)
        assert exc_info.value.code == "docx_intent_unsuited"
        assert exc_info.value.status == 400
        assert "PDF" in exc_info.value.message, "引导信息应指向 PDF/PNG"
        for intent in ("poster", "dashboard", "landing"):
            with pytest.raises(StoreError):
                exporting._export_docx(project, {"format": "docx"},
                                       {**manifest, "intent": intent})

    def test_missing_python_docx_gets_a_pip_hint(self, tmp_path, monkeypatch):
        """未装 [docx] extra：RuntimeError 给出 pip 安装提示（照 PPTX 惯例），
        由 Studio 层如实转成 500 + 原因，而不是静默产出坏文件。"""
        monkeypatch.setitem(sys.modules, "docx", None)  # from docx import … 视为缺失
        project = _make_project(tmp_path, "<html><body><p>x</p></body></html>")
        with pytest.raises(RuntimeError, match=r"htmlninefox\[docx\]"):
            docx_export.export_document_docx(project)

    def test_docx_is_a_zip_with_the_heading_inside(self, tmp_path):
        """标准库冒烟：不依赖 python-docx 的那条路径永不跳过。"""
        pytest.importorskip("docx")
        project = _make_project(tmp_path, SAMPLE.replace("{png_b64}", _png_base64()))
        report = docx_export.export_document_docx(project)
        with zipfile.ZipFile(report["file"]) as bundle:
            document_xml = bundle.read("word/document.xml").decode("utf-8")
        assert "季度交付报告" in document_xml
        assert "第一章 · 背景" in document_xml
        assert report["file"].endswith(".docx")

    def test_capabilities_and_served_page_carry_the_docx_option(self):
        assert "docx" in exporting.SUPPORTED_FORMATS
        assert exporting.runtime_capabilities()["docx_ready"] is True
        page = (ROOT / "htmlninefox" / "server" / "static" / "index.html").read_text(encoding="utf-8")
        assert 'value="docx"' in page, "导出中心选项未登记——陈旧产物在发布回读时会被抓住"
        assert "Word 文档" in page

    def test_export_format_error_message_names_docx(self):
        with pytest.raises(StoreError) as exc_info:
            exporting.normalize_export_request({"project_name": "p", "format": "wav"})
        assert "DOCX" in exc_info.value.message, "不支持格式的报错应列全 DOCX"
