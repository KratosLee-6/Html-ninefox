"""copy_expert · 0.9.2 AI 生成深化的文案侧智能体。

两个职责，同一个纪律——LLM 只是建议，校验不过就老实回退：

1. recommend_preset：结合 brief + 项目记忆，从 11 家设计预设里挑一个并
   给出中文理由；preset_id 不在库 = 回退规则匹配（match_preset）。
2. polish_slots：槽位文案润色（headline/summary/cta/bullets…）。硬校验：
   原文里的数字必须原样保留（价格/日期不许 LLM 改）、禁词表一律剔除、
   超长截断——违反者该槽位直接丢弃，宁缺勿错。

LLM 不可用是常态：两个职责都返回 fallback_used=True 由调用方走规则路径，
功能不缺失（无密钥 = 「润色需要 LLM」照实说，规则引擎不代写文案）。
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict

from ..llm import router

logger = logging.getLogger(__name__)

PRESET_SYSTEM_PROMPT = (
    "你是资深网页设计顾问。根据需求摘要、意图与项目记忆，从给定的设计预设清单里"
    "选出最合适的一个。只输出 JSON：{\"preset_id\": \"...\", \"reason\": \"一句中文理由，"
    "说清为什么这个预设适合这份需求（40 字以内）\"}。不要 markdown 包裹。"
)

POLISH_SYSTEM_PROMPT = (
    "你是资深中文文案编辑，为网页槽位润色。保持原意与所有数字（价格、日期、"
    "型号）完全不变，只让表达更有力、更贴合语气。输出 JSON：键与输入槽位一致，"
    "值为润色后的文案。不要 markdown 包裹，不要新增键。"
)

# 槽位长度上限（超出即丢弃该建议——宁缺勿错）
SLOT_LENGTH_LIMITS = {"headline": 30, "cta": 16, "summary": 120, "hero_sub": 60}
DEFAULT_SLOT_LIMIT = 80
_DIGITS_RE = re.compile(r"\d+(?:\.\d+)?")


def _extract_json(text: str) -> Dict[str, Any] | None:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text).rstrip("`").strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, ValueError):
        return None


def _numbers_preserved(original: str, suggestion: str) -> bool:
    """数字串双向一致：原文的数字不许丢，建议里也不许发明新数字
    （价格/日期/指标是事实，LLM 无权增删）。"""
    return (sorted(_DIGITS_RE.findall(original or ""))
            == sorted(_DIGITS_RE.findall(suggestion or "")))


def _passes_gates(original: str, suggestion: str, forbidden: list[str]) -> bool:
    text = str(suggestion or "").strip()
    if not text:
        return False
    if not _numbers_preserved(original, text):
        return False
    lowered = text.lower()
    if any(word and word.lower() in lowered for word in forbidden or []):
        return False
    return True


class CopyExpert:
    name = "copy_expert"

    # -------------------------------------------------- preset 推荐
    def recommend_preset(self, brief: dict, intent: str,
                         memory: dict | None = None,
                         allow_llm: bool = True) -> Dict[str, Any]:
        from htmlninefox.generators._tokens import PRESETS

        payload = brief.get("brief", brief) if isinstance(brief, dict) else {}
        catalog = "\n".join(
            f"- {pid}：{spec.get('name', '')}（关键词：{'、'.join(spec.get('match_keywords', [])[:4])}）"
            for pid, spec in PRESETS.items())
        memory = memory or {}
        user_msg = (
            f"意图：{intent}\n"
            f"headline：{payload.get('content', {}).get('headline', '')}\n"
            f"核心诉求：{payload.get('content', {}).get('core_message', '')}\n"
            f"调性：{payload.get('style', {}).get('tone', '')}\n"
            f"项目记忆：品牌={memory.get('brand', '')} 受众={memory.get('audience', '')} "
            f"语气={memory.get('tone', '')}\n"
            f"设计预设清单：\n{catalog}\n\n请输出 JSON。"
        )
        fallback: Dict[str, Any] = {"preset_id": None, "reason": None,
                                    "fallback_used": True, "model": "fallback"}
        try:
            if not allow_llm:
                raise RuntimeError("LLM disabled")
            result = router.call(prompt=user_msg, agent="copy_expert",
                                 task="preset_recommend",
                                 system=PRESET_SYSTEM_PROMPT,
                                 temperature=0.3, max_tokens=200)
            data = _extract_json(result.text) or {}
            preset_id = str(data.get("preset_id") or "").strip()
            reason = str(data.get("reason") or "").strip()[:80]
            if preset_id not in PRESETS:
                logger.info("[copy_expert] LLM 推荐了不存在的预设 %r，回退规则", preset_id)
                return fallback
            return {"preset_id": preset_id, "reason": reason or None,
                    "fallback_used": False, "model": result.model}
        except Exception as e:  # noqa: BLE001 —— LLM 不可用是常态
            logger.info("[copy_expert] 预设推荐走规则引擎：%s", e.__class__.__name__)
            return fallback

    # -------------------------------------------------- 槽位润色
    def polish_slots(self, slots: Dict[str, str], context: Dict[str, Any],
                     allow_llm: bool = True) -> Dict[str, Any]:
        """slots = {槽位: 现文}；返回可用建议（逐槽过门禁）与元信息。"""
        if not isinstance(slots, dict) or not slots:
            return {"suggestions": {}, "fallback_used": True, "model": "fallback",
                    "dropped": []}
        memory = context.get("memory") or {}
        forbidden = list(memory.get("forbidden") or [])
        slot_lines = "\n".join(f"- {key}：{value}" for key, value in slots.items())
        user_msg = (
            f"意图：{context.get('intent', '')}\n"
            f"语气：{memory.get('tone') or context.get('tone', '')}\n"
            f"受众：{memory.get('audience', '')}\n"
            f"禁用词（出现即弃）：{'、'.join(forbidden) if forbidden else '无'}\n"
            f"槽位现文：\n{slot_lines}\n\n请输出润色后的 JSON（键保持一致）。"
        )
        empty: Dict[str, Any] = {"suggestions": {}, "fallback_used": True,
                                 "model": "fallback", "dropped": []}
        try:
            if not allow_llm:
                raise RuntimeError("LLM disabled")
            result = router.call(prompt=user_msg, agent="copy_expert",
                                 task="copy_polish",
                                 system=POLISH_SYSTEM_PROMPT,
                                 temperature=0.6, max_tokens=800)
            data = _extract_json(result.text)
            if not data:
                return empty
            suggestions: Dict[str, str] = {}
            dropped: list[str] = []
            for key, original in slots.items():
                if key not in data:
                    continue
                suggestion = str(data[key] or "").strip()
                limit = SLOT_LENGTH_LIMITS.get(key, DEFAULT_SLOT_LIMIT)
                if not _passes_gates(str(original), suggestion, forbidden):
                    dropped.append(f"{key}(数字改动/禁词/为空)")
                    continue
                if len(suggestion) > limit:
                    dropped.append(f"{key}(超长 {len(suggestion)}>{limit})")
                    continue
                suggestions[key] = suggestion
            return {"suggestions": suggestions, "fallback_used": False,
                    "model": result.model, "dropped": dropped}
        except Exception as e:  # noqa: BLE001
            logger.info("[copy_expert] 润色不可用：%s", e.__class__.__name__)
            return empty
