"""style_expert.py · 自研核心智能体（v0.2 · token 预设 + LLM 增强）

输入：brief_expert 输出（含 intent）
输出：{"preset": 风格预设（生成器直接消费）, "style_decision": 决策说明, "style_md": 可读 markdown}
策略：规则匹配 6 风格预设保证「离线可用且结果稳定」；LLM 可用时仅做
      微调（在 preset token 上覆盖主色/字体），不推翻整体预设。
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional

from ..generators import _tokens
from ..llm import router
from ._base import BaseExpert

logger = logging.getLogger(__name__)

STYLE_SYSTEM_PROMPT = """你是「视觉风格微调」专家。输入是 Brief JSON 与已匹配的风格预设 token。
你只能微调，不能推翻预设：最多修改 primary/accent 两个颜色（必须给 #RRGGBB hex）。
输出严格 JSON：{"primary": "#...", "accent": "#...", "reason": "一句话"}，不要 markdown 包裹。
颜色要与预设明暗基调协调（深色预设给高亮度色，浅色预设给中低亮度色）。
"""


class StyleExpert(BaseExpert):
    name = "style_expert"

    def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        brief = input.get("brief") or {}
        payload = brief.get("brief", brief) if isinstance(brief, dict) else {}
        intent = input.get("intent") or brief.get("intent", "landing")
        if isinstance(intent, dict):
            intent = intent.get("intent", "landing")

        preset = _tokens.match_preset(brief, intent)

        # LLM 微调（可选增强，失败不影响主流程）
        adjusted, model_used = False, "rules"
        if input.get("allow_llm", True):
            decision = self._llm_refine(payload, preset)
            if decision:
                t = preset["tokens"]
                t["primary"] = decision.get("primary", t["primary"])
                t["accent"] = decision.get("accent", t["accent"])
                adjusted, model_used = True, decision.get("_model", "llm")

        decision_payload = {
            "preset_id": preset["id"],
            "preset_name": preset["name"],
            "matched_by": preset.get("_matched_by", "rules"),
            "llm_adjusted": adjusted,
            "model": model_used,
        }
        return {
            "preset": preset,
            "style_decision": decision_payload,
            "style_md": _tokens.tokens_to_style_md(preset, intent),
            "fallback_used": not adjusted,
        }

    def _llm_refine(self, payload: dict, preset: dict) -> Optional[Dict[str, Any]]:
        try:
            user_msg = (
                "[Brief]\n" + json.dumps(payload.get("goal", {}), ensure_ascii=False) + "\n"
                "[预设]\n" + json.dumps(preset["tokens"], ensure_ascii=False)
            )
            result = router.call(
                prompt=user_msg, agent="style_expert", task="style_refine",
                system=STYLE_SYSTEM_PROMPT, temperature=0.4, max_tokens=300,
            )
        except Exception as e:  # noqa: BLE001
            logger.info("[style_expert] LLM 不可用，使用纯规则预设：%s", e.__class__.__name__)
            return None
        text = result.text or ""
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            return None
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
        hex_re = re.compile(r"^#[0-9A-Fa-f]{6}$")
        out: Dict[str, Any] = {}
        for k in ("primary", "accent"):
            v = data.get(k, "")
            if hex_re.match(v or ""):
                out[k] = v.upper()
        if out:
            out["_model"] = result.model
            return out
        return None


def _persist_style(decision: Dict[str, Any], brief: Dict[str, Any]) -> None:
    style_dir = Path.home() / ".htmlninefox" / "styles"
    style_dir.mkdir(parents=True, exist_ok=True)
    pid = brief.get("project_id", "unknown") if isinstance(brief, dict) else "unknown"
    path = style_dir / f"{pid}.md"
    md = decision.get("style_md", "")
    if md:
        path.write_text(md, encoding="utf-8")
        logger.info("[style_expert] persisted → %s", path)
