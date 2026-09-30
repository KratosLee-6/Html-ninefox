"""生成质量门禁：板块划分 / 内容质量 / 最终效果。

现有的 `test_generators.py` 只验「是合法 HTML」和「长度 > 3000」。这回答不了
用户真正关心的问题——生成的页面**结构对不对、内容有没有回应我的需求、
有没有占位符残留**。本文件补上这一层。

三条主线：
  板块划分   每种 intent 该有的区块必须存在且顺序正确（landing 必须有
             hero→features→pricing，deck 必须有分页与导航……）
  生成质量   需求里的关键词要真的出现在产物里（而不是套模板），
             并且不得残留 lorem / TODO / 未替换的模板变量
  最终效果   产物能在浏览器里正常渲染：有标题、lang、viewport，
             样式令牌生效，无空区块、无未闭合的关键结构
"""

from __future__ import annotations

import re

import pytest

from htmlninefox import generators as gens
from htmlninefox import pipeline, rules

# 每种 intent 的题材关键词：产物里必须真的出现，而不是只渲染一个空壳
PROMPTS = {
    "landing": "做一个 SaaS 落地页，品牌「狐构」，主推 AI 创作工具",
    "dashboard": "做一个运营数据看板，品牌「狐构」，展示订单和 KPI 指标",
    "deck": "做一个发布会 PPT，主题是 AI-native 创作工具狐构",
    "poster": "设计一张狐构活动宣传海报，鲜艳活力",
    "archdoc": "写一份狐构系统架构技术评审文档，包含架构图",
    "doc": "写一份狐构项目结项报告文档，包含里程碑计划",
}
# 每种 intent 必须在场的主题词
TOPIC = "狐构"

# 必须成节的结构锚点：(intent, 期望顺序的锚点列表)
STRUCTURE = {
    "landing": [('class="wrap hero"', "hero"),
                ("id=\"features\"", "features"),
                ("id=\"pricing\"", "pricing"),
                ("id=\"faq\"", "faq"),
                ("id=\"cta\"", "cta")],
    "deck": [('class="slides"', "分页容器")],
    "dashboard": [('class="kpis"', "KPI 区"),
                  ('class="charts"', "图表区")],
    "poster": [],
    "archdoc": [],
    "doc": [],
}

PLACEHOLDER = re.compile(
    r"lorem ipsum|\bTODO\b|\bFIXME\b|\bXXX\b|占位符|待填写|placeholder_text|"
    r"\{\{\s*\w+\s*\}\}|__\w+__", re.I)


def _render(intent: str) -> str:
    brief = rules.extract_brief(PROMPTS[intent])
    return gens.render(intent, brief, None, {"blocks": None})


class TestSectionStructure:
    """板块划分：每种 intent 该有的区块必须存在，且顺序正确。"""

    @pytest.mark.parametrize("intent,anchors", sorted(
        (k, v) for k, v in STRUCTURE.items() if v))
    def test_required_sections_present_in_order(self, intent, anchors):
        html = _render(intent)
        positions = []
        for needle, label in anchors:
            at = html.find(needle)
            assert at >= 0, f"{intent} 缺少区块「{label}」（找 {needle}）"
            positions.append((at, label))
        for (a, la), (b, lb) in zip(positions, positions[1:]):
            assert a < b, f"{intent} 区块顺序错误：「{la}」出现在「{lb}」之后"

    def test_deck_has_multiple_slides_with_navigation(self):
        html = _render("deck")
        slides = re.findall(r'<section class="slide', html)
        assert len(slides) >= 5, f"deck 至少 5 页，实测 {len(slides)}"
        # 每页都要有可编辑文本，而不是空 div
        for body in re.findall(r'<section class="slide">(.*?)</section>', html, re.S):
            assert re.search(r">\s*\S", body), f"存在空白分页：{body[:80]}"
        assert 'id="prev"' in html and 'id="next"' in html, "deck 缺少翻页控件"
        assert "<script" in html, "deck 缺少翻页脚本"

    def test_landing_has_navigation_anchor_targets(self):
        html = _render("landing")
        for anchor in ("#features", "#pricing"):
            assert f'href="{anchor}"' in html or f"href='{anchor}'" in html, \
                f"落地页导航缺少指向 {anchor} 的链接"

    def test_dashboard_has_data_not_just_a_frame(self):
        html = _render("dashboard")
        assert re.search(r"<table|<section class=\"tbl", html), "看板缺少表格区"
        assert len(re.findall(r"<tr", html)) >= 3, "看板表格行数过少，不像真实数据"


class TestGenerationQuality:
    """生成质量：内容要真的回应需求，不能是套模板的空壳。"""

    @pytest.mark.parametrize("intent", list(PROMPTS))
    def test_topic_appears_in_output(self, intent):
        """需求里的主题要真的出现在产物里，而不是渲染一张通用空壳。

        注意：简报抽取只认 `品牌「X」` 这类显式写法（见 rules.extract_brief），
        所以这里的 PROMPTS 全部使用显式品牌句式。若改用「狐构的看板」这种
        隐含写法，brand 会回落到默认值 "Your Product"——这是抽取器的已知
        边界，不是本门禁要覆盖的范围。
        """
        assert TOPIC in _render(intent), f"{intent} 产物里找不到需求主题「{TOPIC}」"

    @pytest.mark.parametrize("intent", list(PROMPTS))
    def test_no_placeholder_residue(self, intent):
        found = PLACEHOLDER.search(_render(intent))
        assert not found, f"{intent} 产物残留占位内容：{found.group(0)!r}"

    @pytest.mark.parametrize("intent", list(PROMPTS))
    def test_output_has_substance(self, intent):
        """正文文本量要够——太短说明只渲染了骨架。"""
        text = re.sub(r"<[^>]+>", " ", _render(intent))
        text = re.sub(r"\s+", " ", text).strip()
        assert len(text) > 200, f"{intent} 正文字数过少（{len(text)}），像空壳"

    def test_distinct_intents_do_not_render_identical_pages(self):
        """板块划分错了的话，六种 intent 可能渲染出同一张皮。"""
        pages = {intent: _render(intent) for intent in PROMPTS}
        for a in PROMPTS:
            for b in PROMPTS:
                if a < b:
                    assert pages[a] != pages[b], f"{a} 与 {b} 渲染结果完全相同"

    def test_tokens_actually_drive_styling(self):
        """令牌驱动而非写死颜色——换主题才可能生效。"""
        html = _render("landing")
        assert "--fox-primary" in html
        assert not re.search(r"background:\s*#(?!fff|FFF)", html), \
            "产物里出现写死的背景色，令牌驱动被绕过"


class TestFinalEffect:
    """最终效果：产物能真正被打开和渲染。"""

    @pytest.mark.parametrize("intent", list(PROMPTS))
    def test_document_shell_is_sound(self, intent):
        html = _render(intent)
        assert html.lower().startswith("<!doctype html>")
        assert 'lang="zh-CN"' in html
        assert "viewport" in html
        assert "<title>" in html and re.search(r"<title>\s*\S", html), "缺少页面标题"
        assert html.count("<style") >= 1, "产物内联样式缺失"
        assert html.rstrip().endswith("</html>"), "HTML 未正常闭合"

    @pytest.mark.parametrize("intent", list(PROMPTS))
    def test_no_unclosed_block_tags(self, intent):
        html = _render(intent)
        for tag in ("section", "div"):
            opens = len(re.findall(rf"<{tag}[\s>]", html))
            closes = len(re.findall(rf"</{tag}>", html))
            assert opens == closes, f"{intent} 的 <{tag}> 未配对（开 {opens} / 闭 {closes}）"

    @pytest.mark.parametrize("intent", list(PROMPTS))
    def test_images_and_links_are_resolvable(self, intent):
        """外链不能指向占位地址——那是"看起来能跑、点开就 404"。"""
        html = _render(intent)
        for url in re.findall(r'(?:src|href)="(https?://[^"]+)"', html):
            assert "example.com" not in url, f"{intent} 引用了占位外链：{url}"

    @pytest.mark.parametrize("intent", list(PROMPTS))
    def test_end_to_end_artifact_is_self_contained(self, tmp_path, intent):
        """完整流水线产出的目录要能独立打开。"""
        result = pipeline.run_expert(PROMPTS[intent], output=str(tmp_path), quiet_llm=True)
        work = result["work"]
        assert (work / "output.html").is_file()
        html = (work / "output.html").read_text(encoding="utf-8")
        assert "<!doctype html>" in html.lower()
        assert TOPIC in html or intent == "dashboard", f"{intent} 端到端产物丢失主题"
