"""feedback_expert.py · 自研核心智能体（v0.2 · LLM + 离线规则双通道）

输入：用户口语化反馈 + project_id（+ 可选 html/brief 上下文）
输出：结构化反馈 JSON（target_element + suggestion + confidence + actionable
      + tokens_extracted + rules）—— rules 字段供 apply_feedback 重渲染。
策略：
  1. LLM 可用 → LLM 解析（置信度 <0.5 反问，绝不猜）
  2. LLM 不可用 → 离线规则解析（颜色深浅/字号/间距/圆角/明暗/hex/参考预设）
  3. 两路都失败 → ask_user
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .. import rules
from ..llm import router
from ._base import BaseExpert

logger = logging.getLogger(__name__)

FEEDBACK_SYSTEM_PROMPT = """你是「反馈分析」专家。用户会给你一句口语化反馈（如"颜色再深一点"），
你的任务：把它结构化成 JSON，便于代码层去改设计 token。

输出严格 JSON（不要 markdown 包裹），字段：
{
  "target_element": "global 或 CSS 选择器",
  "suggestion": "一句明确可执行的变更描述",
  "confidence": 0-1 浮点（模糊反馈必须 < 0.5）,
  "rules": ["theme_dark|theme_light|color_shift|color_lighten|radius_up|radius_down|font_up|font_down|spacing_up|spacing_down"],
  "tokens_extracted": {"primary_override": "#RRGGBB 可选", "reference_preset": "linear|vercel|stripe|notion|figma|shadcn|apple 可选"}
}
"""


class FeedbackExpert(BaseExpert):
    name = "feedback_expert"

    def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        user_note: str = (input.get("user_note") or input.get("note") or "").strip()
        project_id: Optional[str] = input.get("project_id")

        if not user_note:
            return _ask_user("请提供反馈内容（feedback.execute 需要 user_note）")

        project_id = project_id or "default"
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")

        # 通道 1：LLM 解析
        parsed = self._llm_parse(user_note, bool(input.get("allow_llm", True)))

        # 通道 2：离线规则解析（LLM 失败或低置信度时）
        offline = rules.parse_feedback(user_note)
        if parsed is None or (not parsed.get("actionable") and offline.get("actionable")):
            parsed = offline
            parsed["_model"] = "rules"
        elif parsed.get("actionable"):
            # 合并离线规则命中（双保险，LLM rules 可能更泛化）
            for r in offline.get("rules", []):
                if r not in parsed.setdefault("rules", []):
                    parsed["rules"].append(r)
            for k, v in offline.get("tokens_extracted", {}).items():
                parsed["tokens_extracted"].setdefault(k, v)

        if not parsed.get("actionable"):
            return _ask_user(parsed.get("ask_user") or "反馈太模糊，请具体说明：颜色？字号？布局？")

        # 持久化沉淀（三重沉淀之反馈库）
        _persist_feedback(project_id, ts, user_note, parsed)

        parsed["project_id"] = project_id
        parsed["timestamp"] = ts
        parsed["actionable"] = True
        parsed["ask_user"] = None

        # 三重沉淀之 Feedback 库（v0.2 · 自动入库；失败不阻塞主流程）
        try:
            from ..libraries.feedback_lib import FeedbackLib
            payload = dict(parsed)
            payload["raw_note"] = user_note
            FeedbackLib().append(project_id, payload)
        except Exception as e:
            logger.warning("[feedback_expert] 自动入库失败（非阻塞）: %s", e)

        return parsed

    def _llm_parse(self, user_note: str, allow_llm: bool = True) -> Optional[Dict[str, Any]]:
        try:
            if not allow_llm:
                raise RuntimeError("LLM disabled")
            result = router.call(
                prompt=f"用户反馈：{user_note}",
                agent="feedback_expert", task="feedback_analysis",
                system=FEEDBACK_SYSTEM_PROMPT, temperature=0.3, max_tokens=500,
            )
        except Exception as e:  # noqa: BLE001
            logger.info("[feedback_expert] LLM 不可用，走离线规则：%s", e.__class__.__name__)
            return None
        parsed = _parse_feedback(result.text or "")
        if parsed:
            parsed["_model"] = result.model
            # LLM 置信度阈值（< 0.5 不 actionable，交给离线规则/反问）
            parsed["actionable"] = parsed["confidence"] >= 0.5
        return parsed


def _parse_feedback(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    cleaned = text.strip()
    m = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    return {
        "target_element": data.get("target_element", "global"),
        "suggestion": data.get("suggestion", ""),
        "confidence": float(data.get("confidence", 0.5)),
        "actionable": bool(data.get("actionable", False)),
        "tokens_extracted": data.get("tokens_extracted", {}) or {},
        "rules": list(data.get("rules", []) or []),
    }


def _ask_user(reason: str) -> Dict[str, Any]:
    return {
        "actionable": False,
        "ask_user": reason,
        "confidence": 0.0,
        "target_element": "",
        "suggestion": "",
        "tokens_extracted": {},
        "rules": [],
        "_fallback": "ask_user",
    }


def _persist_feedback(project_id: str, ts: str, user_note: str, parsed: Dict[str, Any]) -> None:
    fb_dir = Path.home() / ".htmlninefox" / "feedback"
    fb_dir.mkdir(parents=True, exist_ok=True)
    md_path = fb_dir / f"{project_id}.md"
    entry = (
        f"\n---\n\n## {ts}\n\n"
        f"**用户反馈**: {user_note}\n\n"
        f"**目标元素**: `{parsed.get('target_element', 'global')}`\n\n"
        f"**建议**: {parsed.get('suggestion', '')}\n\n"
        f"**置信度**: {parsed.get('confidence', 0):.2f}\n\n"
        f"**规则**: `{', '.join(parsed.get('rules', []))}`\n\n"
        f"**模型**: `{parsed.get('_model', 'rules')}`\n"
    )
    if parsed.get("tokens_extracted"):
        entry += (f"\n**提取的 token**: ```json\n"
                  f"{json.dumps(parsed['tokens_extracted'], ensure_ascii=False, indent=2)}\n```\n")
    with md_path.open("a", encoding="utf-8") as f:
        f.write(entry)
    logger.info("[feedback_expert] appended → %s", md_path)
