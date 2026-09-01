"""brief_expert.py · 自研核心智能体（v0.2 真实 LLM 实现）

输入：user prompt（一句话需求）
输出：符合 Brief 标准 v0.1 的 5 字段 JSON（含 goal/context/content/style/constraints + confidence + missing_fields）
副作用：写到 ~/.htmlninefox/briefs/<project_id>.json
Fallback：3 层 — LiteLLM 重试 1 次 → 上次缓存 → "基础 Brief"（只填 goal）
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .. import rules
from ..llm import router
from ._base import BaseExpert

logger = logging.getLogger(__name__)

BRIEF_SYSTEM_PROMPT = """你是「Brief 标准 v0.1」专家。用户会给你一句话需求，你的任务是把它拆解成 Brief 标准的 5 个必填字段：
goal（目标）、context（场景）、content（内容）、style（风格）、constraints（约束）。

行为规则：
1. 用户没说清的字段 → 给出"最合理的推断" + 标记到 missing_fields
2. 每个字段必须具体（受众要有人群画像，颜色要有 hex 值）
3. constraints.forbidden 至少 2 条（禁忌往往比期望更重要）
4. 输出必须是合法 JSON，不要任何 markdown 代码块标记
5. 不要复述用户原话，要做"翻译"和"补全"
"""


class BriefExpert(BaseExpert):
    name = "brief_expert"

    def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        prompt: str = (input.get("prompt") or "").strip()
        context_hints: Optional[Dict[str, Any]] = input.get("context_hints")
        existing_brief: Optional[Dict[str, Any]] = input.get("existing_brief")

        if not prompt:
            return {
                "error": {"code": "EMPTY_PROMPT", "message": "prompt 不能为空"},
                "fallback_used": True,
            }

        user_msg = f"用户需求：\n{prompt}\n"
        if context_hints:
            user_msg += f"\n用户补充上下文：\n{json.dumps(context_hints, ensure_ascii=False)}\n"
        if existing_brief:
            user_msg += f"\n上一次 Brief（用于迭代）：\n{json.dumps(existing_brief, ensure_ascii=False)}\n"
        user_msg += (
            "\n请按 Brief 标准 v0.1 输出结构化 JSON："
            "\n- 字段名严格用：goal / context / content / style / constraints"
            "\n- 不要 markdown 包裹，直接输出 JSON"
            "\n- 在 JSON 末尾加 confidence（0-1）和 missing_fields（数组）"
        )

        # 第 1 层：真实 LLM 调用（含内部重试由 litellm router 负责）
        try:
            if not input.get("allow_llm", True):
                raise RuntimeError("LLM disabled")
            result = router.call(
                prompt=user_msg,
                agent="brief_expert",
                task="brief_generation",
                system=BRIEF_SYSTEM_PROMPT,
                temperature=0.5,
                max_tokens=1500,
            )
            parsed = _parse_brief(result.text)
        except Exception as e:  # noqa: BLE001 —— LLM 不可用是常态（离线模式）
            logger.info("[brief_expert] LLM 不可用，走离线规则引擎：%s", e.__class__.__name__)
            parsed = None

        fallback_used = parsed is None

        # 第 2 层：离线规则引擎兜底（v0.2：真实结构化，非占位）
        if parsed is None:
            parsed = rules.extract_brief(prompt)
            fallback_used = True

        # 意图分类（联盟路由需要；LLM Brief 同样补充）
        intent, intent_conf, intent_evidence = rules.classify_intent(prompt)
        parsed["intent"] = intent
        parsed["intent_confidence"] = intent_conf

        # 持久化到 ~/.htmlninefox/briefs/
        project_id = input.get("project_id") or _derive_project_id(prompt)
        _persist_brief(project_id, parsed, fallback_used)

        parsed["fallback_used"] = fallback_used
        parsed["project_id"] = project_id
        parsed["_model"] = getattr(result, "model", "unknown") if not fallback_used else "fallback"

        # 三重沉淀之 Brief 库（v0.2 · 自动入库；失败不阻塞主流程）
        try:
            from ..libraries.brief_lib import BriefLib
            # 将 parsed 序列化成 Markdown 假文件喂给 BriefLib.add（复用了它的 schema 校验逻辑）
            import tempfile
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".md", encoding="utf-8", delete=False
            ) as _tmp:
                _tmp.write(f"# {parsed.get('brief', {}).get('goal', {}).get('job_to_be_done', prompt)}\n\n")
                tmp_path = _tmp.name
            try:
                BriefLib().add(tmp_path)
            finally:
                Path(tmp_path).unlink(missing_ok=True)
        except Exception as e:
            logger.warning("[brief_expert] 自动入库失败（非阻塞）: %s", e)

        return parsed


def _parse_brief(text: str) -> Optional[Dict[str, Any]]:
    """从 LLM 返回里抽 JSON。容忍 markdown 包裹 + 前后杂文本。"""
    if not text:
        return None
    cleaned = text.strip()
    # 去掉 ```json ... ``` 包裹
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
    if m:
        cleaned = m.group(1)
    # 截取第一个 { 到最后一个 }
    if "{" in cleaned and "}" in cleaned:
        cleaned = cleaned[cleaned.index("{"): cleaned.rindex("}") + 1]
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    # 校验 5 必填字段
    brief = data.get("brief", data)
    required = ("goal", "context", "content", "style", "constraints")
    if not all(k in brief for k in required):
        return None
    return {
        "brief": brief,
        "confidence": float(data.get("confidence", 0.6)),
        "missing_fields": list(data.get("missing_fields", [])),
        "reasoning": data.get("reasoning", ""),
    }


def _fallback_brief(prompt: str) -> Dict[str, Any]:
    """已由 rules.extract_brief 取代（保留函数名兼容旧调用）。"""
    return rules.extract_brief(prompt)


def _derive_project_id(prompt: str) -> str:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    slug = re.sub(r"[^\w\u4e00-\u9fff]+", "-", prompt[:30]).strip("-") or "project"
    return f"{ts}-{slug[:20]}"


def _persist_brief(project_id: str, payload: Dict[str, Any], fallback_used: bool) -> None:
    brief_dir = Path.home() / ".htmlninefox" / "briefs"
    brief_dir.mkdir(parents=True, exist_ok=True)
    path = brief_dir / f"{project_id}.json"
    enriched = dict(payload)
    enriched["_persisted_at"] = datetime.now().isoformat(timespec="seconds")
    enriched["_fallback_used"] = fallback_used
    path.write_text(json.dumps(enriched, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("[brief_expert] persisted → %s", path)


def _load_latest_brief_cache(prompt: str) -> Optional[Dict[str, Any]]:
    """已废弃（v0.2）：旧实现按 mtime 盲取最新 brief，会把 A 项目的 Brief
    错配给 B 需求；离线兜底已由 rules.extract_brief 接管，不再使用缓存层。"""
    return None
