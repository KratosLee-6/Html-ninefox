"""pipeline.py · 编排流水线（CLI 与 Web 端共用的装配层）

run_expert()   —— 5 专家流水线：route → brief → style → asset → generate，写产物 + 状态
run_feedback() —— 反馈迭代：解析反馈 → 改 token → 重渲染（真实迭代，非重新生成）

状态文件 .foxstate.json 保存在项目目录，使 --revise 无需 LLM 即可确定性地重渲染。
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

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


def run_expert(prompt: str, skill: Optional[str] = None, template: Optional[str] = None,
               output: str = "./output", intent_override: Optional[str] = None,
               quiet_llm: bool = False,
               style_overrides: Optional[Dict[str, Any]] = None,
               composition: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """完整生成流水线。返回 {work, files, summary}。"""
    out_dir = Path(output).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d-%H%M%S")
    work = out_dir / f"html9n-{ts}"
    n = 1
    while work.exists():  # 同秒多次生成不互相覆盖
        n += 1
        work = out_dir / f"html9n-{ts}-{n}"
    work.mkdir(parents=True)

    router = AllianceRouter()

    # 1) Brief（LLM 优先 / 规则兜底）
    brief_result = brief_expert.BriefExpert().execute({"prompt": prompt, "allow_llm": not quiet_llm})
    intent = intent_override or brief_result.get("intent", "landing")

    # 2) 联盟路由
    route = router.route(brief_result, intent, skill_override=skill)

    # 3) Style（预设规则匹配 + LLM 微调）
    style_result = style_expert.StyleExpert().execute(
        {"brief": brief_result, "intent": intent, "allow_llm": not quiet_llm})
    preset = style_result["preset"]
    if template:  # 用户显式指定模板/预设
        preset = {**_tokens.get_preset(template), "_matched_by": f"user-template:{template}"}
        preset["tokens"] = dict(preset["tokens"])

    # 画布工作区的视觉素材覆盖（色卡 / 字体卡）
    if style_overrides:
        t = preset["tokens"]
        if style_overrides.get("primary") and re.fullmatch(r"#[0-9A-Fa-f]{6}", style_overrides["primary"]):
            t["primary"] = style_overrides["primary"].upper()
            preset["_matched_by"] += " +色卡覆盖"
        font_map = {
            "serif": "'Georgia','Noto Serif SC','Songti SC','SimSun',serif",
            "sans": "'Inter','PingFang SC','Microsoft YaHei',sans-serif",
            "mono": "'JetBrains Mono',Consolas,monospace",
        }
        fk = style_overrides.get("font")
        if fk in font_map:
            t["font_body"] = t["font_display"] = font_map[fk]
            preset["_matched_by"] += f" +字体({fk})"

    # 4) Asset 规划
    assets_result = asset_expert.AssetExpert().execute({"brief": brief_result, "intent": intent})
    composition = dict(composition or {})
    selected_blocks = [str(block).strip() for block in composition.get("blocks", []) if str(block).strip()]
    if selected_blocks:
        assets_result["blocks"] = list(dict.fromkeys(selected_blocks))
        assets_result["block_notes"] = "用户从模板作品或素材库中选择的页面配方"
    assets_result["composition"] = composition

    # 5) Generate
    gen_result = generate_expert.GenerateExpert().execute(
        {"brief": brief_result, "style": {"preset": preset}, "assets": assets_result,
         "route": route})

    html = gen_result["html"]
    (work / "output.html").write_text(html, encoding="utf-8")
    (work / "brief.json").write_text(
        json.dumps(brief_result, ensure_ascii=False, indent=2), encoding="utf-8")
    (work / "brief.md").write_text(_brief_to_md(brief_result.get("brief", {})), encoding="utf-8")
    (work / "style.md").write_text(style_result.get("style_md", ""), encoding="utf-8")
    (work / "assets.json").write_text(
        json.dumps(assets_result, ensure_ascii=False, indent=2), encoding="utf-8")

    # 状态（反馈迭代用）
    state = {
        "version": "v0.2",
        "prompt": prompt,
        "intent": intent,
        "preset_id": preset["id"],
        "preset": {k: v for k, v in preset.items() if not k.startswith("_")},
        "preset_matched_by": preset.get("_matched_by", ""),
        "brief": brief_result,
        "assets": assets_result,
        "route": {k: v for k, v in route.items() if k != "output_path"},
        "composition": composition,
        "revision": 0,
        "created_at": ts,
    }
    (work / STATE_FILE).write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    files = ["output.html", "brief.json", "brief.md", "style.md", "assets.json", STATE_FILE]
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
        "html_bytes": len(html),
    }


def run_feedback(project: str, note: str, revise: bool = True, allow_llm: bool = True) -> Dict[str, Any]:
    """反馈迭代：解析反馈 → 改 token → 重渲染 output.html。

    返回 {ok, project, revision, suggestion, applied_rules, ask_user?}
    """
    proj = Path(project).expanduser().resolve()
    state_path = proj / STATE_FILE
    output_path = proj / "output.html"
    if not state_path.exists():
        return {"ok": False, "error": f"项目缺少 {STATE_FILE}（请用 htmlninefox expert 生成）"}

    state = json.loads(state_path.read_text(encoding="utf-8"))
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

    rev_dir = proj / "revisions"
    rev_dir.mkdir(exist_ok=True)
    new_rev = state.get("revision", 0) + 1
    (rev_dir / f"rev{new_rev}.html").write_text(html, encoding="utf-8")
    output_path.write_text(html, encoding="utf-8")

    state["preset"] = {k: v for k, v in new_preset.items() if not k.startswith("_")}
    state["preset_id"] = new_preset.get("id", state.get("preset_id"))
    state["revision"] = new_rev
    state["last_feedback"] = {"note": note, "suggestion": fb.get("suggestion", ""),
                              "rules": fb.get("rules", []), "tokens": fb.get("tokens_extracted", {})}
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

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
