"""测试规则引擎：意图分类 / 离线 Brief / 反馈解析"""

from htmlninefox import rules


class TestClassifyIntent:
    def test_landing(self):
        intent, conf, ev = rules.classify_intent("做一个 SaaS 落地页，主推 AI 创作工具")
        assert intent == "landing"
        assert conf > 0.5
        assert "落地页" in ev

    def test_dashboard(self):
        intent, _, _ = rules.classify_intent("做一个运营数据看板，展示订单和KPI")
        assert intent == "dashboard"

    def test_deck(self):
        intent, _, _ = rules.classify_intent("做一个发布会 PPT，5 页")
        assert intent == "deck"

    def test_poster(self):
        intent, _, _ = rules.classify_intent("设计一张活动宣传海报")
        assert intent == "poster"

    def test_archdoc(self):
        intent, _, _ = rules.classify_intent("写一份技术方案文档，包含架构图")
        assert intent in ("archdoc", "doc")

    def test_doc_report(self):
        intent, _, ev = rules.classify_intent("写一份项目结项报告文档，包含里程碑计划")
        assert intent == "doc", ev
        assert "报告" in ev or "文档" in ev

    def test_no_hit_defaults_landing_low_confidence(self):
        intent, conf, ev = rules.classify_intent("随便来一个东西")
        assert intent == "landing"
        assert conf == 0.35
        assert ev == []


class TestExtractBrief:
    def test_structure_complete(self):
        out = rules.extract_brief("做一个 SaaS 落地页，品牌「狐构」，目标用户是设计师")
        b = out["brief"]
        assert set(b) >= {"goal", "context", "content", "style", "constraints"}
        assert b["content"]["brand"] == "狐构"
        assert out["confidence"] > 0.4
        assert isinstance(b["constraints"]["forbidden"], list) and b["constraints"]["forbidden"]

    def test_tone_dark_detected(self):
        out = rules.extract_brief("做一个深色数据看板")
        assert out["brief"]["style"]["tone"] == "dark"

    def test_audience_detected(self):
        out = rules.extract_brief("给设计师做一个作品集落地页")
        assert "设计师" in out["brief"]["goal"]["audience"]

    def test_blocks_match_intent(self):
        out = rules.extract_brief("做一个发布会 PPT")
        assert out["brief"]["content"]["blocks"] == rules._INTENT_BLOCKS["deck"]

    def test_missing_fields_marked(self):
        out = rules.extract_brief("做一个页面")
        assert isinstance(out["missing_fields"], list)


class TestParseFeedback:
    def test_darker(self):
        r = rules.parse_feedback("颜色再深一点")
        assert r["actionable"] and "color_shift" in r["rules"]

    def test_lighter(self):
        r = rules.parse_feedback("颜色浅一点")
        assert "color_lighten" in r["rules"]

    def test_hex_override(self):
        r = rules.parse_feedback("主色用 #FF5A00")
        assert r["tokens_extracted"]["primary_override"] == "#FF5A00"

    def test_reference_preset(self):
        r = rules.parse_feedback("参考 vercel 风格")
        assert r["tokens_extracted"]["reference_preset"] == "vercel"

    def test_theme_dark(self):
        r = rules.parse_feedback("换成深色主题")
        assert "theme_dark" in r["rules"]

    def test_vague_asks_user(self):
        r = rules.parse_feedback("不好看")
        assert not r["actionable"] and r.get("ask_user")

    def test_empty(self):
        assert not rules.parse_feedback("")["actionable"]

    def test_font_and_spacing(self):
        assert "font_up" in rules.parse_feedback("标题字大一点")["rules"]
        assert "spacing_down" in rules.parse_feedback("排版紧凑一点")["rules"]
