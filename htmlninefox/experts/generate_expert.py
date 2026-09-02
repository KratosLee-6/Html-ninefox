"""generate_expert.py · 生成专家（v0.2.1 真实联盟接入 + Jinja2 兜底）

输入：{"brief": ..., "style": preset, "assets": ..., "route": ...,
       "router": AllianceRouter, "output_path": str}
输出：{"html": str, "intent": ..., "generator": "...", "skill_used": ...}
策略：
  1. 调 router.invoke() 拉联盟 HTML → 写到 output_path 直接接管
  2. 联盟失败 → 用 Jinja2 模板（templates/<intent>.html）渲染本地 HTML
  3. 模板也失败 → 退回到 generators.render()（v0.2 原生生成器）
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import jinja2
except ImportError:  # 可选增强；缺失时继续使用原生生成器
    jinja2 = None

from .. import generators
from ..alliance.router import AllianceRouter
from ..rules import CONTENT_TYPES
from ._base import BaseExpert

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

# v0.3 意图→模板别名：把联盟 intent 映射到本地 Jinja2 模板文件名（兜底用）
# 优先级链：联盟 skill（installed） > 本地 Jinja2 模板 > 原生 generators
_INTENT_TEMPLATE_ALIAS: Dict[str, str] = {
    "ppt_image":     "baoyu-slide-deck",         # 飞书绝活大会·宝玉
    "ppt_html":      "frontend-slides",          # 飞书绝活大会·张咋啦 PPT
    "html_template": "beautiful-html-templates", # 飞书绝活大会·张咋啦 28 套
    # 已有映射保留
    "landing":   "landing",
    "deck":      "landing",     # deck 用 landing 模板兜底（保留原行为）
    "infographic": "landing",   # 信息图走 huashu 联盟，本地兜底到 landing
}


class GenerateExpert(BaseExpert):
    name = "generate_expert"

    def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        brief = input.get("brief") or {}
        style = input.get("style") or {}
        assets = input.get("assets") or {}
        route = input.get("route") or {}

        intent = (route.get("intent") or assets.get("intent")
                  or brief.get("intent") or "landing")
        if intent not in CONTENT_TYPES:
            intent = "landing"

        # 解析 style 兼容层
        preset = style.get("preset") if isinstance(style, dict) else style
        if not isinstance(preset, dict) or "tokens" not in preset:
            from ..generators import _tokens
            preset = _tokens.get_preset(_tokens.DEFAULT_PRESET)

        output_path: Optional[str] = input.get("output_path")
        router: Optional[AllianceRouter] = input.get("router")

        # 第 1 路径：联盟 skill 接管
        if router is not None and route.get("skill") and output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            inv = router.invoke(
                route["skill"],
                {"brief": brief, "style": style, "intent": intent,
                 "output": output_path},
                timeout_s=int(input.get("timeout_s", 60)),
            )
            if inv.get("success") and Path(output_path).exists():
                html = Path(output_path).read_text(encoding="utf-8")
                return {"html": html, "intent": intent,
                        "generator": f"alliance:{inv.get('skill')}",
                        "skill_used": inv.get("skill"),
                        "fallback_used": inv.get("fallback_used", False)}

        # 第 2 路径：Jinja2 本地模板（templates/<intent>.html 或别名模板）
        # v0.3：用别名映射把 ppt_image/ppt_html/html_template 路由到对应模板文件
        tmpl_name = _INTENT_TEMPLATE_ALIAS.get(intent, intent)
        tmpl_path = _TEMPLATES_DIR / f"{tmpl_name}.html"
        if tmpl_path.exists() and jinja2 is not None:
            try:
                env = jinja2.Environment(
                    loader=jinja2.FileSystemLoader(str(_TEMPLATES_DIR)),
                    autoescape=jinja2.select_autoescape(["html"]),
                    trim_blocks=True, lstrip_blocks=True,
                )
                html = env.get_template(f"{tmpl_name}.html").render(
                    brief=brief if isinstance(brief, dict) else {},
                    style=preset, assets=assets, intent=intent,
                )
                if output_path:
                    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                    Path(output_path).write_text(html, encoding="utf-8")
                return {"html": html, "intent": intent,
                        "generator": f"jinja2:{tmpl_name}", "skill_used": None,
                        "fallback_used": True}
            except Exception:
                pass  # 模板渲染失败 → 第 3 路径

        # 第 3 路径：v0.2 原生生成器（永远可用的兜底）
        if route.get("output_path") and Path(route["output_path"]).exists():
            # pipeline 旧路径：route 已写出文件
            html = Path(route["output_path"]).read_text(encoding="utf-8")
            return {"html": html, "intent": intent,
                    "generator": f"alliance:{route.get('skill')}",
                    "skill_used": route.get("skill")}

        html = generators.render(intent, brief, preset, assets)
        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_text(html, encoding="utf-8")
        return {"html": html, "intent": intent,
                "generator": f"local:{intent}-v0.2",
                "skill_used": route.get("skill_used_fallback") if route else None,
                "fallback_used": True}
