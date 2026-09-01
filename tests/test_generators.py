"""测试生成器与流水线：5 类内容产物 + 端到端 + 反馈迭代"""

import json
from pathlib import Path

import pytest

from htmlninefox import pipeline, rules
from htmlninefox import generators as gens

PROMPTS = {
    "landing": "做一个 SaaS 落地页，品牌「狐构」，主推 AI 创作工具",
    "dashboard": "做一个运营数据看板，深色，展示订单和KPI",
    "deck": "做一个发布会 PPT，主题是 AI-native 创作工具狐构",
    "poster": "设计一张活动宣传海报，鲜艳活力",
    "archdoc": "写一份狐构系统架构技术评审文档，包含架构图",
    "doc": "写一份狐构项目结项报告文档，包含里程碑计划",
}


class TestGenerators:
    @pytest.mark.parametrize("intent", list(PROMPTS))
    def test_render_produces_publishable_html(self, intent):
        brief = rules.extract_brief(PROMPTS[intent])
        preset = {"tokens": dict(
            __import__("htmlninefox.generators._tokens", fromlist=["PRESETS"]).PRESETS["linear-light"]["tokens"]),
            "id": "linear-light", "name": "test", "dark": False, "_matched_by": "test"}
        html = gens.render(intent, brief, preset, {"blocks": None})
        assert html.startswith("<!doctype html>")
        assert 'lang="zh-CN"' in html and "viewport" in html
        assert "--fox-primary" in html  # token 驱动
        assert len(html) > 3000

    def test_deck_has_navigation_js(self):
        html = gens.render("deck", rules.extract_brief(PROMPTS["deck"]), None, {})
        assert "ArrowRight" in html and 'class="slide' in html

    def test_unknown_intent_falls_back_landing(self):
        html = gens.render("nope", {}, None, {})
        assert "hero" in html


class TestRunExpert:
    @pytest.mark.parametrize("intent,prompt", list(PROMPTS.items()))
    def test_offline_end_to_end(self, tmp_path, intent, prompt):
        result = pipeline.run_expert(prompt, output=str(tmp_path), quiet_llm=True)
        work = result["work"]
        assert result["intent"] == intent
        for f in result["files"]:
            assert (work / f).exists(), f
        html = (work / "output.html").read_text(encoding="utf-8")
        assert html.startswith("<!doctype html>")
        state = json.loads((work / pipeline.STATE_FILE).read_text(encoding="utf-8"))
        assert state["intent"] == intent and state["revision"] == 0

    def test_explicit_type_override(self, tmp_path):
        result = pipeline.run_expert("随便说点什么", output=str(tmp_path),
                                     intent_override="poster", quiet_llm=True)
        assert result["intent"] == "poster"

    def test_template_override(self, tmp_path):
        result = pipeline.run_expert(PROMPTS["landing"], output=str(tmp_path),
                                     template="vibrant-poster", quiet_llm=True)
        assert result["preset_id"] == "vibrant-poster"


class TestRunFeedback:
    def test_revise_changes_output(self, tmp_path):
        result = pipeline.run_expert(PROMPTS["landing"], output=str(tmp_path), quiet_llm=True)
        work = result["work"]
        before = (work / "output.html").read_text(encoding="utf-8")

        fb = pipeline.run_feedback(str(work), "颜色再深一点，标题大一点", revise=True)
        assert fb["ok"] and fb["revision"] == 1
        after = (work / "output.html").read_text(encoding="utf-8")
        assert before != after
        assert (work / "revisions" / "rev1.html").exists()
        assert "颜色" in (work / "feedback.md").read_text(encoding="utf-8")

        # 第二轮迭代
        fb2 = pipeline.run_feedback(str(work), "参考 vercel", revise=True)
        assert fb2["ok"] and fb2["revision"] == 2
        assert (work / "revisions" / "rev2.html").exists()

    def test_vague_feedback_asks_user(self, tmp_path):
        result = pipeline.run_expert(PROMPTS["landing"], output=str(tmp_path), quiet_llm=True)
        fb = pipeline.run_feedback(str(result["work"]), "就是感觉不好看", revise=True)
        assert not fb["ok"] and fb.get("ask_user")

    def test_missing_state_errors(self, tmp_path):
        fb = pipeline.run_feedback(str(tmp_path), "深色", revise=True)
        assert not fb["ok"] and "error" in fb


class TestListTemplates:
    def test_builtin_six(self):
        items = pipeline.list_templates()
        ids = {i["id"] for i in items}
        assert {"linear-light", "vercel-dark", "guizang-magazine",
                "shadcn-dashboard", "vibrant-poster", "doc-clean",
                "fox-pixel-garden", "fox-duotone-studio", "fox-editorial-ink",
                "fox-swiss-signal", "fox-soft-silver"} <= ids

    def test_user_template_loaded(self, tmp_path, monkeypatch):
        home = tmp_path / "home"
        tdir = home / ".htmlninefox" / "templates" / "my-brand"
        tdir.mkdir(parents=True)
        (tdir / "style.json").write_text(json.dumps({
            "name": "我的品牌风", "dark": True, "tokens": {"bg": "#101010"}}),
            encoding="utf-8")
        monkeypatch.setattr(Path, "home", lambda: home)
        items = pipeline.list_templates()
        mine = [i for i in items if i["id"] == "my-brand"]
        assert mine and mine[0]["source"] == "user" and mine[0]["dark"] is True


def test_render_template_preview_is_real_html():
    html = pipeline.render_template_preview("landing", "vercel-dark")
    assert "<!doctype html>" in html.lower()
    assert "Html九尾狐" in html
    assert "--fox-bg" in html

    deck = pipeline.render_template_preview("deck", "fox-pixel-garden")
    assert 'class="slide"' in deck
    assert '>1</b> / 7<' in deck


@pytest.mark.parametrize("preset", [
    "fox-pixel-garden", "fox-duotone-studio", "fox-editorial-ink",
    "fox-swiss-signal", "fox-soft-silver",
])
@pytest.mark.parametrize("intent", ["landing", "dashboard", "deck", "poster", "archdoc", "doc"])
def test_new_visual_systems_render_rich_preview(preset, intent):
    html = pipeline.render_template_preview(intent, preset)
    assert "<!doctype html>" in html.lower()
    assert len(html) > 3000
    assert "visual_system" not in html


def test_render_template_preview_rejects_unknown_values():
    with pytest.raises(ValueError):
        pipeline.render_template_preview("unknown", "vercel-dark")
    with pytest.raises(ValueError):
        pipeline.render_template_preview("landing", "missing-template")
