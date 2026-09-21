from __future__ import annotations

import json
from pathlib import Path

from htmlninefox.project_memory import ProjectMemoryStore


def make_project(root: Path, name: str = "adopt-me") -> Path:
    project = root / name
    project.mkdir()
    state = {
        "prompt": "为 KratosLee 品牌制作设计师产品页，温暖专业，不要黑紫渐变",
        "intent": "landing", "preset_id": "fox-pixel-garden", "revision": 2,
        "brief": {"brief": {
            "content": {"brand": "KratosLee"}, "goal": {"audience": "设计师与开发者"},
            "style": {"tone": "温暖、专业"},
            "constraints": {"forbidden": ["黑紫渐变", "夸张 AI 光效"]},
        }},
        "preset": {"tokens": {"primary": "#3157D5", "font_body": "'Inter','PingFang SC',sans-serif"}},
        "last_feedback": {"note": "这里包含私人原文，不应被保存",
            "suggestion": "保持暖纸白并增加内容层级", "rules": ["减少装饰"],
            "tokens": {"primary": "#3157D5", "api_key": "secret"}},
    }
    (project / ".foxstate.json").write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    return project


def test_save_read_and_clear(tmp_path):
    store = ProjectMemoryStore(tmp_path)
    saved = store.save({"profile": {"brand": "KratosLee", "forbidden": "黑紫, 霓虹"}})
    assert saved["profile"]["brand"] == "KratosLee"
    forged = store.save({"stats": {"adopted_count": 99}, "evidence": [{"project": "fake"}]})
    assert forged["stats"]["adopted_count"] == 0
    assert forged["evidence"] == []
    assert store.read()["profile"]["forbidden"] == ["黑紫", "霓虹"]
    cleared = store.clear()
    assert cleared["profile"]["brand"] == ""
    assert cleared["stats"]["adopted_count"] == 0


def test_adoption_extracts_preferences_and_is_idempotent(tmp_path):
    store = ProjectMemoryStore(tmp_path)
    project = make_project(tmp_path)
    result = store.adopt(project)
    memory = result["memory"]
    assert result["adopted"] is True
    assert memory["profile"]["brand"] == "KratosLee"
    assert memory["profile"]["preferred_preset_by_intent"]["landing"] == "fox-pixel-garden"
    assert memory["profile"]["preferred_primary"] == "#3157D5"
    assert memory["profile"]["preferred_font"] == "sans"
    assert memory["stats"]["adopted_count"] == 1
    assert "私人原文" not in json.dumps(memory, ensure_ascii=False)
    assert "secret" not in json.dumps(memory, ensure_ascii=False)
    duplicate = store.adopt(project)
    assert duplicate["already_adopted"] is True
    assert duplicate["memory"]["stats"]["adopted_count"] == 1


def test_explicit_requirements_override_memory(tmp_path):
    store = ProjectMemoryStore(tmp_path)
    store.adopt(make_project(tmp_path))
    recommendation = store.recommend(
        "为 Acme 品牌制作面向管理者的严肃企业页面，不要像素风",
        {"template": "linear-light", "primary": "#FF0000"},
    )
    applied_fields = {item["field"] for item in recommendation["applied"]}
    covered_fields = {item["field"] for item in recommendation["covered"]}
    assert "brand" not in applied_fields
    assert {"brand", "audience", "tone", "forbidden", "template", "primary"} <= covered_fields
    assert recommendation["overrides"].get("font") == "sans"


def test_recommendation_is_empty_when_disabled(tmp_path):
    store = ProjectMemoryStore(tmp_path)
    store.save({"enabled": False, "profile": {"brand": "KratosLee"}})
    result = store.recommend("制作产品页", {})
    assert result["enabled"] is False
    assert result["applied"] == []


def test_browser_memory_dialog_generation_and_adoption(workbench_server):
    from playwright.sync_api import sync_playwright

    with workbench_server as server:
        base = server.base_url
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(base + "/")
            page.wait_for_timeout(900)

            page.click("#btn-memory")
            page.wait_for_selector("#memory-modal:not([hidden])")
            page.fill("#memory-brand", "KratosLee")
            page.fill("#memory-audience", "设计师与开发者")
            page.fill("#memory-tone", "温暖、专业")
            page.fill("#memory-template", "fox-pixel-garden")
            page.click("#memory-save")
            page.wait_for_function("document.querySelector('#memory-status').textContent.includes('已保存')")
            page.click("#memory-modal .preview-bar button")

            generated = page.evaluate("""async () => {
                const data = await api('/api/generate', 'POST', {
                    prompt:'制作一个落地页', intent:'landing', quiet_llm:true
                });
                const output = addNode('output', 900, 100, {
                    title:'落地页 · 产物', preview_url:data.preview_url, project:data.project,
                    project_name:data.project_name, intent:data.intent, preset_id:data.preset_id,
                    revision:0, feedback:[], recipe_run:data.recipe_run, verification:data.verification,
                    memory_applied:data.memory_applied
                });
                select(output.id);
                return data;
            }""")
            assert generated["memory_applied"]["applied"]
            page.wait_for_selector("text=本次项目记忆")
            page.get_by_role("button", name="采用此版本并学习").click()
            page.wait_for_selector("button:has-text('已采用并学习'):disabled")

            page.click("#btn-memory")
            page.wait_for_selector("#memory-modal:not([hidden])")
            assert page.locator("#memory-adopted-count").inner_text() == "1"
            assert not errors
            browser.close()


def test_concurrent_generation_counts_are_not_lost(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    store = ProjectMemoryStore(tmp_path)
    store.save({"profile": {"brand": "KratosLee"}})
    recommendation = store.recommend("制作一个页面", {})
    with ThreadPoolExecutor(max_workers=6) as executor:
        list(executor.map(lambda _: store.record_generation(recommendation), range(12)))
    assert store.read()["stats"]["generated_with_memory"] == 12
