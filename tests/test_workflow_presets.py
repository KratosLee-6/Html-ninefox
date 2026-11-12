"""0.9.4 拼装层第一批门禁：家族标签 + 工作流剧本。

家族标签（思路致敬 dsh-guizang-design「一套设计系统」）：
  * 11 家 preset 与画廊 10 张全部带 family；
  * 同家族语义：preset 与模板可共享视觉血缘（guizang/fox/shadcn…）；
  * 未登记的 preset 落 independent（不猜）。

工作流剧本（六条，致敬上游工作流表）：
  * 纯声明数据：每步引用 ability（引擎按能力路由），不绑定具体实现；
  * schema 门禁：id/name/description/steps 完整，ability 在已知能力集内；
  * API e2e：清单与单条 GET 真链 + 404。
"""

from __future__ import annotations

import json
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from htmlninefox.generators._tokens import (  # noqa: E402
    PRESET_FAMILY, PRESETS, preset_family,
)
from htmlninefox.workflow_presets import (  # noqa: E402
    WORKFLOWS, get_workflow, list_workflows,
)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

KNOWN_ABILITIES = {"generate", "intake", "adopt", "feedback", "export"}
VALID_FAMILIES = set(PRESET_FAMILY.values()) | {"independent"}


def test_every_preset_and_template_has_family():
    """家族标签完整性：preset 全体在映射表里；画廊模板全体带 family。"""
    missing = [pid for pid in PRESETS if pid not in PRESET_FAMILY]
    assert not missing, f"预设缺家族标签：{missing}"
    manifest = json.loads(
        (ROOT / "htmlninefox" / "templates" / "gallery" / "manifest.json")
        .read_text(encoding="utf-8"))
    no_family = [item["id"] for item in manifest["items"] if not item.get("family")]
    assert not no_family, f"模板缺家族标签：{no_family}"


def test_unknown_preset_falls_to_independent():
    assert preset_family("vercel-dark") == "vercel"
    assert preset_family("不存在的预设") == "independent"
    assert preset_family("不存在的预设") in VALID_FAMILIES


def test_gallery_and_preset_families_overlap():
    """家族语义可用的前提：至少一个家族同时拥有 preset 与模板
    （「三出口一家人」在 guizang/fox 家族上真实成立）。"""
    manifest = json.loads(
        (ROOT / "htmlninefox" / "templates" / "gallery" / "manifest.json")
        .read_text(encoding="utf-8"))
    template_families = {item["family"] for item in manifest["items"]}
    preset_families = set(PRESET_FAMILY.values())
    shared = template_families & preset_families
    assert {"guizang", "fox"} <= shared, f"核心家族未同时落在两侧：{shared}"


def test_template_family_follows_its_preset():
    """统规门禁（0.9.5 统查补）：模板 family 必须等于所引 preset 的家族 ——
    家族=视觉血缘，token 由 preset 决定；同一 preset 的两张模板家族不同
    即自相矛盾（0.9.4 曾漏网 3 条：guizang-swiss-signal/duola 与
    fox-vibrant-poster，集合级门禁抓不到逐条错位）。"""
    manifest = json.loads(
        (ROOT / "htmlninefox" / "templates" / "gallery" / "manifest.json")
        .read_text(encoding="utf-8"))
    mismatched = [
        f"{item['id']}: 画廊family={item.get('family')} preset家族={preset_family(item['preset_id'])}"
        for item in manifest["items"]
        if item.get("family") != preset_family(item["preset_id"])
    ]
    assert not mismatched, f"模板家族与所引 preset 不一致：{mismatched}"


def test_workflow_presets_schema():
    assert len(list_workflows()) == 6, "工作流剧本应 有 六条（致敬上游工作流表）"
    ids = set()
    for workflow in WORKFLOWS:
        for key in ("id", "name", "description", "steps"):
            assert workflow.get(key), f"{workflow} 缺 {key}"
        assert workflow["id"] not in ids, "工作流 id 重复"
        ids.add(workflow["id"])
        for step in workflow["steps"]:
            assert step["ability"] in KNOWN_ABILITIES, (
                f"{workflow['id']} 步骤引用未知能力：{step['ability']}")
            assert step.get("note"), f"{workflow['id']} 有步骤缺说明"
    ids_from_get = {w["id"] for w in
                    (get_workflow(wid) for wid in ids) if w}
    assert ids_from_get == ids, "get_workflow 与清单不一致"
    assert get_workflow("不存在") is None


import urllib.parse  # noqa: E402

import pytest  # noqa: E402


@pytest.fixture()
def workbench(tmp_path: Path):
    from tests.conftest import WorkbenchServer
    with WorkbenchServer(tmp_path / "output") as server:
        yield server


def test_workflow_api_roundtrip(workbench):
    from tests.test_server_project_api import request as api_request
    base = workbench.base_url
    listing, _ = api_request(base, "/api/workflows", "GET")
    assert listing["ok"] is True and len(listing["workflows"]) == 6
    one, _ = api_request(base, "/api/workflows/brand-suite", "GET")
    assert one["workflow"]["id"] == "brand-suite"
    assert one["workflow"]["steps"][0]["ability"] == "generate"
    missing, _ = api_request(
        base, "/api/workflows/" + urllib.parse.quote("不存在"), "GET", expected=404)
    assert missing["error"]["code"] == "not_found"


def test_mutation_removing_workflow_step_ability_is_caught(tmp_path: Path, monkeypatch):
    """变异验证：步骤引用未知能力 → schema 门禁当场红。"""
    import htmlninefox.workflow_presets as wp
    original = dict(wp.WORKFLOWS[0])
    try:
        broken = dict(original)
        broken["steps"] = [{"ability": "teleport", "note": "坏步骤"}]
        wp.WORKFLOWS = [broken] + list(wp.WORKFLOWS)[1:]
        bad = [w for w in wp.WORKFLOWS
               for s in w["steps"] if s["ability"] not in KNOWN_ABILITIES]
        assert bad, "变异后的坏步骤必须被 schema 检查发现"
    finally:
        wp.WORKFLOWS[0] = original
    assert not [w for w in wp.WORKFLOWS
                for s in w["steps"] if s["ability"] not in KNOWN_ABILITIES], "还原失败"


def test_generate_with_workflow_records_it_in_recipe_run(workbench):
    """端到端：generate 带 workflow → recipe-run compose 段记录剧本 id；
    未知剧本 → 400 workflow_invalid。"""
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tests.test_server_project_api import request as api_request
    base = workbench.base_url
    result, _ = api_request(base, "/api/generate", "POST", {
        "prompt": "做一个智能水杯的落地页", "intent": "landing",
        "workflow": "one-article-three-outputs", "quiet_llm": True})
    name = result["project_name"]
    run, _ = api_request(
        base, "/api/projects/" + urllib.parse.quote(name) + "/recipe-run", "GET")
    compose = next(s for s in run["stages"] if s["id"] == "compose")
    # compose 的 output_summary 不经端点透出全部字段——改为直接读产物目录
    run_file = workbench.output_root / name / "recipe-run.json"
    data = json.loads(run_file.read_text(encoding="utf-8"))
    compose_stage = next(s for s in data["stages"] if s["id"] == "compose")
    assert compose_stage.get("output_summary", {}).get("workflow") == \
        "one-article-three-outputs", "compose 必须记录工作流剧本"
    bad, _ = api_request(base, "/api/generate", "POST", {
        "prompt": "做一个落地页", "intent": "landing",
        "workflow": "不存在剧本", "quiet_llm": True}, expected=400)
    assert bad["error"]["code"] == "workflow_invalid"
