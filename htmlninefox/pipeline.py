"""pipeline.py · 编排流水线（CLI 与 Web 端共用的装配层）

run_expert()   —— 5 专家流水线：route → brief → style → asset → generate，写产物 + 状态
run_feedback() —— 反馈迭代：解析反馈 → 改 token → 重渲染（真实迭代，非重新生成）

状态文件 .foxstate.json 保存在项目目录，使 --revise 无需 LLM 即可确定性地重渲染。
"""

from __future__ import annotations

import json
import re
import shutil
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from . import recipe_run, revisions
from .alliance.router import AllianceRouter
from .experts import asset_expert, brief_expert, generate_expert, style_expert
from .experts import feedback_expert as feedback_expert_mod
from .generators import _tokens

STATE_FILE = ".foxstate.json"
PREVIEW_INTENTS = {"landing", "dashboard", "deck", "poster", "archdoc", "doc"}

_PREVIEW_BRIEF = {
    "brief": {
        "goal": {
            "type": "product-preview",
            "audience": "创作者与产品团队",
            "job_to_be_done": "快速判断页面骨架与视觉风格是否适合当前需求",
            "success_metric": "无需生成即可看懂版式与风格",
        },
        "content": {
            "brand": "Html九尾狐",
            "headline": "把想法变成可交付的页面",
            "subheadline": "从需求、版式到真实 HTML 预览，在一个工作台完成。",
            "core_message": "可视化编排 · 真实预览 · 持续迭代",
            "must_have": ["真实 HTML", "可视化工作流", "反馈迭代"],
            "cta": "开始创作",
        },
        "style": {"tone": "minimal", "reference": []},
        "constraints": {"forbidden": [], "technical": ["responsive", "single-file-html"]},
    }
}

_PREVIEW_BLOCKS = {
    "landing": ["nav", "hero", "features", "showcase", "pricing", "faq", "cta_footer"],
    "dashboard": ["topbar", "kpi_row", "charts", "table", "activity"],
    "deck": ["cover", "problem", "solution", "demo", "metrics", "roadmap", "ending"],
    "poster": ["headline", "key_info", "details", "action_bar"],
    "archdoc": ["title", "layer_diagram", "flow", "component_table", "decisions"],
    "doc": ["title", "summary", "sections", "key_points", "table", "conclusion"],
}



def _brief_to_md(brief_payload: dict) -> str:
    b = brief_payload
    lines = ["# Brief（标准 v0.1）", ""]
    g = b.get("goal", {})
    lines += [
        f"- **类型**: {g.get('type', '')}",
        f"- **受众**: {g.get('audience', '')}",
        f"- **核心任务**: {g.get('job_to_be_done', '')}",
        f"- **成功指标**: {g.get('success_metric', '')}",
        "",
        f"## 内容", "",
        f"- **品牌**: {b.get('content', {}).get('brand', '')}",
        f"- **核心信息**: {b.get('content', {}).get('core_message', '')}",
        f"- **必备要点**: {'、'.join(b.get('content', {}).get('must_have', [])[:6])}",
        "",
        f"## 风格", "",
        f"- **基调**: {b.get('style', {}).get('tone', '')}",
        f"- **参考**: {'、'.join(b.get('style', {}).get('reference', []))}",
        "",
        f"## 禁忌（不要做）", "",
    ]
    for f in b.get("constraints", {}).get("forbidden", []):
        lines.append(f"- ❌ {f}")
    for t in b.get("constraints", {}).get("technical", []):
        lines.append(f"- 🔧 {t}")
    return "\n".join(lines) + "\n"


def _apply_memory_context(brief_result: dict[str, Any], memory_context: dict[str, Any] | None) -> None:
    if not isinstance(memory_context, dict):
        return
    values = memory_context.get("values")
    if not isinstance(values, dict) or not values:
        return
    brief = brief_result.setdefault("brief", {})
    content = brief.setdefault("content", {})
    goal = brief.setdefault("goal", {})
    style = brief.setdefault("style", {})
    constraints = brief.setdefault("constraints", {})
    if values.get("brand"):
        content["brand"] = values["brand"]
    if values.get("audience"):
        goal["audience"] = values["audience"]
    if values.get("tone"):
        style["tone"] = values["tone"]
    if values.get("forbidden"):
        current = constraints.get("forbidden") if isinstance(constraints.get("forbidden"), list) else []
        constraints["forbidden"] = list(dict.fromkeys(current + list(values["forbidden"])))


def run_expert(prompt: str, skill: Optional[str] = None, template: Optional[str] = None,
               output: str = "./output", intent_override: Optional[str] = None,
               quiet_llm: bool = False,
               style_overrides: Optional[Dict[str, Any]] = None,
               composition: Optional[Dict[str, Any]] = None,
               memory_context: Optional[Dict[str, Any]] = None,
               progress_callback: recipe_run.ProgressCallback | None = None) -> Dict[str, Any]:
    """Run the observable five-stage generation pipeline."""
    out_dir = Path(output).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    # Generate inside a dot-prefixed staging dir and publish by rename, so a
    # crash never leaves a half-written project visible in the workbench.
    project_name = _next_project_name(out_dir, ts)
    staging = out_dir / f".gen-{uuid.uuid4().hex}"
    staging.mkdir(parents=True)
    published = False
    try:
        result = _run_expert_into(staging, project_name, ts, prompt, skill, template, intent_override,
                                  quiet_llm, style_overrides, composition, memory_context,
                                  progress_callback,
                                  lambda final: _publish_project(out_dir, project_name, final))
        published = True
        return result
    finally:
        if not published:
            shutil.rmtree(staging, ignore_errors=True)


def _next_project_name(out_dir: Path, ts: str) -> str:
    name = f"html9n-{ts}"
    suffix = 1
    while (out_dir / name).exists():
        suffix += 1
        name = f"html9n-{ts}-{suffix}"
    return name


def _publish_project(out_dir: Path, name: str, staging: Path) -> Path:
    target = out_dir / name
    if target.exists():
        target = out_dir / _next_project_name(out_dir, name)
    staging.rename(target)
    return target


def _run_expert_into(work: Path, project_name: str, ts: str, prompt: str, skill: Optional[str] = None,
                     template: Optional[str] = None,
                     intent_override: Optional[str] = None,
                     quiet_llm: bool = False,
                     style_overrides: Optional[Dict[str, Any]] = None,
                     composition: Optional[Dict[str, Any]] = None,
                     memory_context: Optional[Dict[str, Any]] = None,
                     progress_callback: recipe_run.ProgressCallback | None = None,
                     publish: Optional[Callable[[Path], Path]] = None) -> Dict[str, Any]:
    """Run the observable five-stage generation pipeline."""
    tracker = recipe_run.RecipeRunTracker(prompt, progress_callback)
    active_stage = "analyze"
    router = AllianceRouter()
    verification: dict[str, Any] = {}
    state: dict[str, Any] = {}

    try:
        tracker.start("analyze", {
            "prompt_chars": len(prompt),
            "llm_enabled": not quiet_llm,
            "intent_override": intent_override,
            "project_memory": bool((memory_context or {}).get("applied")),
        })
        brief_result = brief_expert.BriefExpert().execute({"prompt": prompt, "allow_llm": not quiet_llm})
        _apply_memory_context(brief_result, memory_context)
        intent = intent_override or brief_result.get("intent", "landing")
        tracker.complete("analyze", {
            "intent": intent,
            "confidence": brief_result.get("confidence"),
            "missing_fields": brief_result.get("missing_fields", []),
            "memory_applied": (memory_context or {}).get("applied", []),
            "memory_covered": (memory_context or {}).get("covered", []),
        }, model=brief_result.get("_model"), fallback_used=brief_result.get("fallback_used", False))

        active_stage = "compose"
        tracker.start("compose", {
            "requested_skill": skill,
            "requested_template": template,
            "selected_blocks": len((composition or {}).get("blocks", [])),
            "memory_overrides": (memory_context or {}).get("overrides", {}),
        })
        route = router.route(brief_result, intent, skill_override=skill)
        style_result = style_expert.StyleExpert().execute(
            {"brief": brief_result, "intent": intent, "allow_llm": not quiet_llm})
        preset = style_result["preset"]
        if template:
            preset = {**_tokens.get_preset(template), "_matched_by": f"user-template:{template}"}
            preset["tokens"] = dict(preset["tokens"])

        if style_overrides:
            tokens = preset["tokens"]
            if style_overrides.get("primary") and re.fullmatch(
                    r"#[0-9A-Fa-f]{6}", style_overrides["primary"]):
                tokens["primary"] = style_overrides["primary"].upper()
                preset["_matched_by"] += " +色卡覆盖"
            font_map = {
                "serif": "'Georgia','Noto Serif SC','Songti SC','SimSun',serif",
                "sans": "'Inter','PingFang SC','Microsoft YaHei',sans-serif",
                "mono": "'JetBrains Mono',Consolas,monospace",
            }
            font_key = style_overrides.get("font")
            if font_key in font_map:
                tokens["font_body"] = tokens["font_display"] = font_map[font_key]
                preset["_matched_by"] += f" +字体({font_key})"

        assets_result = asset_expert.AssetExpert().execute({"brief": brief_result, "intent": intent})
        composition = dict(composition or {})
        selected_blocks = [
            str(block).strip() for block in composition.get("blocks", []) if str(block).strip()
        ]
        if selected_blocks:
            assets_result["blocks"] = list(dict.fromkeys(selected_blocks))
            assets_result["block_notes"] = "用户从模板作品或素材库中选择的页面配方"
        assets_result["composition"] = composition
        tracker.complete("compose", {
            "intent": intent,
            "route_decision": route.get("decision"),
            "skill": route.get("skill"),
            "preset_id": preset.get("id"),
            "blocks": assets_result.get("blocks", []),
            "selection_mode": composition.get("selection_mode"),
            "memory_applied": (memory_context or {}).get("applied", []),
        }, model=style_result.get("model"), fallback_used=style_result.get("fallback_used", False))

        active_stage = "generate"
        tracker.start("generate", {
            "intent": intent,
            "preset_id": preset.get("id"),
            "route_decision": route.get("decision"),
        })
        gen_result = generate_expert.GenerateExpert().execute(
            {"brief": brief_result, "style": {"preset": preset}, "assets": assets_result,
             "route": route})
        html = gen_result["html"]
        tracker.complete("generate", {
            "generator": gen_result.get("generator"),
            "skill_used": gen_result.get("skill_used"),
            "html_bytes": len(html.encode("utf-8")),
        }, model=gen_result.get("generator"), fallback_used=gen_result.get("fallback_used", False))

        active_stage = "verify"
        tracker.start("verify", {"html_bytes": len(html.encode("utf-8"))})
        verification = recipe_run.verify_html(html)
        if not verification["ok"]:
            raise ValueError("生成结果未通过 HTML 基础质量验证")
        tracker.complete("verify", verification, model="html-quality-gate", fallback_used=False)

        active_stage = "deliver"
        tracker.start("deliver", {"output_root": str(work.parent), "project_name": project_name})
        revisions.atomic_write(work / "output.html", html)
        revisions.atomic_write(work / "brief.json",
                               json.dumps(brief_result, ensure_ascii=False, indent=2))
        revisions.atomic_write(work / "brief.md", _brief_to_md(brief_result.get("brief", {})))
        revisions.atomic_write(work / "style.md", style_result.get("style_md", ""))
        revisions.atomic_write(work / "assets.json",
                               json.dumps(assets_result, ensure_ascii=False, indent=2))

        state = {
            "version": "v0.3",
            "prompt": prompt,
            "intent": intent,
            "preset_id": preset["id"],
            "preset": {key: value for key, value in preset.items() if not key.startswith("_")},
            "preset_matched_by": preset.get("_matched_by", ""),
            "brief": brief_result,
            "assets": assets_result,
            "route": {key: value for key, value in route.items() if key != "output_path"},
            "composition": composition,
            "revision": 0,
            "created_at": ts,
            "verification": verification,
            "recipe_run": tracker.snapshot(),
            "memory_applied": memory_context or {"enabled": False, "applied": [], "covered": []},
        }
        revisions.atomic_write(work / STATE_FILE, json.dumps(state, ensure_ascii=False, indent=2))
        tracker.complete("deliver", {
            "project_name": project_name,
            "files": 9,
            "preview": "output.html",
        }, model="local-filesystem", fallback_used=False)
        run = tracker.succeed()
        state["recipe_run"] = run
        revisions.atomic_write(work / STATE_FILE, json.dumps(state, ensure_ascii=False, indent=2))
        revisions.snapshot(work, state, html)
        recipe_run.write_recipe_run(work, run)
        if publish is not None:
            work = publish(work)
    except Exception as error:
        if tracker.run.get("status") != "failed":
            tracker.fail(active_stage, error)
        recipe_run.write_recipe_run(work, tracker.snapshot())
        raise

    files = [
        "output.html", "revisions/rev0.html", "revisions/rev0.json", "brief.json", "brief.md", "style.md", "assets.json",
        STATE_FILE, recipe_run.RECIPE_RUN_FILE,
    ]
    return {
        "work": work,
        "files": files,
        "intent": intent,
        "preset_id": preset["id"],
        "preset_name": preset["name"],
        "route_decision": route.get("decision"),
        "skill": route.get("skill"),
        "brief_confidence": brief_result.get("confidence"),
        "fallback_used": brief_result.get("fallback_used", False),
        "html_bytes": len(html.encode("utf-8")),
        "verification": verification,
        "recipe_run": run,
        "memory_applied": memory_context or {"enabled": False, "applied": [], "covered": []},
    }


@revisions.locked_project
def rerun_project(project: str | Path, stage: str = "generate",
                  progress_callback: recipe_run.ProgressCallback | None = None) -> Dict[str, Any]:
    """Rerun the render or verification stage using persisted project state."""
    if stage not in {"generate", "verify"}:
        raise ValueError("局部重跑仅支持 generate 或 verify")
    project_path = Path(project).expanduser().resolve()
    state_path = project_path / STATE_FILE
    if not state_path.is_file():
        raise ValueError(f"项目缺少 {STATE_FILE}")
    state = revisions.load_state(project_path)
    before = dict(state)
    previous_run = state.get("recipe_run") if isinstance(state.get("recipe_run"), dict) else {}
    tracker = recipe_run.RecipeRunTracker(
        state.get("prompt", ""), progress_callback,
        parent_run_id=previous_run.get("id"), rerun_from=stage,
    )
    for reused_stage in ("analyze", "compose"):
        tracker.reuse(reused_stage)
    html_path = project_path / "output.html"
    active_stage = stage
    try:
        if stage == "generate":
            tracker.start("generate", {
                "preset_id": state.get("preset_id"),
                "revision": state.get("revision", 0),
                "source": "persisted_project_state",
            })
            html = _render_state(state, state.get("preset", {}))
            tracker.complete("generate", {
                "generator": "local:state-rerender",
                "html_bytes": len(html.encode("utf-8")),
            }, model="local:state-rerender", fallback_used=False)
        else:
            tracker.reuse("generate", {"source": "existing_output.html"})
            if not html_path.is_file():
                raise ValueError("项目缺少 output.html")
            html = html_path.read_text(encoding="utf-8")

        active_stage = "verify"
        tracker.start("verify", {"html_bytes": len(html.encode("utf-8"))})
        verification = recipe_run.verify_html(html)
        if not verification["ok"]:
            raise ValueError("产物未通过 HTML 基础质量验证")
        tracker.complete("verify", verification, model="html-quality-gate", fallback_used=False)

        active_stage = "deliver"
        tracker.start("deliver", {"project_name": project_path.name})
        tracker.complete("deliver", {
            "project_name": project_path.name,
            "files_updated": ["output.html", STATE_FILE, recipe_run.RECIPE_RUN_FILE],
        }, model="local-filesystem", fallback_used=False)
        run = tracker.succeed()
        state["verification"] = verification
        state["recipe_run"] = run
        state["updated_at"] = datetime.now().isoformat(timespec="seconds")
        if stage == "generate":
            state = revisions.commit(project_path, before, state, html, kind="rerun")
        else:
            revisions.atomic_write(state_path, json.dumps(state, ensure_ascii=False, indent=2))
        recipe_run.write_recipe_run(project_path, run)
    except Exception as error:
        if tracker.run.get("status") != "failed":
            tracker.fail(active_stage, error)
        recipe_run.write_recipe_run(project_path, tracker.snapshot())
        raise

    return {
        "ok": True,
        "project": str(project_path),
        "project_name": project_path.name,
        "preview_url": f"/output/{project_path.name}/output.html",
        "intent": state.get("intent"),
        "preset_id": state.get("preset_id"),
        "revision": state.get("revision", 0),
        "verification": verification,
        "recipe_run": run,
        "rerun_from": stage,
    }
@revisions.locked_project
def run_feedback(project: str, note: str, revise: bool = True, allow_llm: bool = True) -> Dict[str, Any]:
    """反馈迭代：解析反馈 → 改 token → 重渲染 output.html。

    返回 {ok, project, revision, suggestion, applied_rules, ask_user?}
    """
    proj = Path(project).expanduser().resolve()
    state_path = proj / STATE_FILE
    output_path = proj / "output.html"
    if not state_path.exists():
        return {"ok": False, "error": f"项目缺少 {STATE_FILE}（请用 htmlninefox expert 生成）"}

    state = revisions.load_state(proj)
    before = dict(state)
    preset = state.get("preset") or {}
    if "tokens" not in preset:
        preset = _tokens.get_preset(state.get("preset_id", _tokens.DEFAULT_PRESET))

    # 反馈解析（LLM 优先 / 离线规则兜底）
    fb = feedback_expert_mod.FeedbackExpert().execute(
        {"user_note": note, "project_id": proj.name, "allow_llm": allow_llm})
    if not fb.get("actionable"):
        return {"ok": False, "ask_user": fb.get("ask_user", "反馈太模糊"), "project": str(proj)}

    if not revise:
        return {"ok": True, "dry_run": True, "suggestion": fb.get("suggestion", ""),
                "applied_rules": fb.get("rules", []), "project": str(proj)}

    # 真实迭代：改 token → 重渲染
    new_preset = _tokens.apply_feedback(preset, fb.get("tokens_extracted", {}),
                                        fb.get("rules", []))
    new_preset["_matched_by"] = f"feedback:rev{state.get('revision', 0) + 1}"
    html = _render_state(state, new_preset)

    state["preset"] = {k: v for k, v in new_preset.items() if not k.startswith("_")}
    state["preset_id"] = new_preset.get("id", state.get("preset_id"))
    state["last_feedback"] = {"note": note, "suggestion": fb.get("suggestion", ""),
                              "rules": fb.get("rules", []), "tokens": fb.get("tokens_extracted", {})}
    state["verification"] = recipe_run.verify_html(html)
    if not state["verification"]["ok"]:
        raise ValueError("产物未通过 HTML 基础质量验证")
    state["recipe_run"] = None
    state = revisions.commit(proj, before, state, html, kind="feedback")
    new_rev = state["revision"]

    # 项目内反馈沉淀
    fb_md = proj / "feedback.md"
    with fb_md.open("a", encoding="utf-8") as f:
        f.write(f"\n## {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · rev{new_rev}\n\n"
                f"> {note}\n\n"
                f"- **执行**: {fb.get('suggestion', '')}\n"
                f"- **规则**: `{', '.join(fb.get('rules', []))}`\n"
                f"- **模型**: `{fb.get('_model', 'rules')}`\n")

    return {"ok": True, "project": str(proj), "revision": new_rev,
            "suggestion": fb.get("suggestion", ""), "applied_rules": fb.get("rules", []),
            "tokens": fb.get("tokens_extracted", {}),
            "model": fb.get("_model", "rules"),
            "output": str(output_path)}


def _render_state(state: dict, preset: dict) -> str:
    """用状态 + 新 token 重渲染（不重跑 Brief/Style，保证确定性）。"""
    from . import generators
    return generators.render(state.get("intent", "landing"), state.get("brief", {}),
                             preset, state.get("assets", {}))


def list_templates() -> list:
    """内置 6 风格预设 + 用户模板（~/.htmlninefox/templates/）。"""
    items = []
    for pid, p in _tokens.PRESETS.items():
        items.append({"id": pid, "name": p["name"], "dark": p["dark"],
                      "source": "builtin", "visual_system": p.get("visual_system", "token-default"),
                      "origin": p.get("origin", "Html九尾狐内置"), "tokens": p["tokens"]})
    user_dir = Path.home() / ".htmlninefox" / "templates"
    if user_dir.is_dir():
        for d in sorted(user_dir.iterdir()):
            style_json = d / "style.json"
            if d.is_dir() and style_json.exists():
                try:
                    data = json.loads(style_json.read_text(encoding="utf-8"))
                    items.append({"id": d.name, "name": data.get("name", d.name),
                                  "dark": data.get("dark", False), "source": "user",
                                  "visual_system": data.get("visual_system", "user"),
                                  "origin": data.get("origin", "用户模板"),
                                  "tokens": data.get("tokens", {})})
                except (json.JSONDecodeError, OSError):
                    continue
    return items


def render_template_preview(intent: str, template_id: str | None = None) -> str:
    """Render an in-memory HTML preview without creating a project directory."""
    from . import generators

    if intent not in PREVIEW_INTENTS:
        raise ValueError(f"不支持的预览类型：{intent}")
    preset_id = template_id or _tokens.DEFAULT_PRESET
    if preset_id not in _tokens.PRESETS:
        user_template = next((item for item in list_templates() if item["id"] == preset_id), None)
        if not user_template:
            raise ValueError(f"模板不存在：{preset_id}")
        default = _tokens.get_preset(_tokens.DEFAULT_PRESET)
        preset = {
            "id": user_template["id"],
            "name": user_template["name"],
            "dark": user_template["dark"],
            "tokens": {**default["tokens"], **user_template["tokens"]},
        }
    else:
        base = _tokens.get_preset(preset_id)
        preset = {**base, "tokens": dict(base["tokens"])}
    assets = {"blocks": _PREVIEW_BLOCKS[intent]}
    return generators.render(intent, _PREVIEW_BRIEF, preset, assets)
