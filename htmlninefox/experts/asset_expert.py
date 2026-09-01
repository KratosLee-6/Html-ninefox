"""asset_expert.py · 资产规划专家（v0.2.1 真实联盟接入）

输入：{"brief": ..., "intent": ..., "router": AllianceRouter（可选）}
输出：{"asset_list": [...], "chart_data": {...}, "tokens": {...},
       "intent": ..., "fallback_used": bool, "skill_used": str|None}
策略：
  1. 调 router.route() 识别意图 + 选 skill（与 pipeline 同层）
  2. 调 router.invoke() 拉真实素材（失败自动 fallback 链）
  3. 输出供 generate_expert / Web 工作台共用的结构化资产清单
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from ..alliance.router import AllianceRouter
from ..rules import CONTENT_TYPES, _INTENT_BLOCKS, classify_intent
from ._base import BaseExpert

# 区块说明（可读性 + 供 Web 工作台展示）
_BLOCK_NOTES = {
    "landing": "导航 / Hero / 特性 / 场景展示 / 定价 / FAQ / CTA+页脚",
    "dashboard": "顶栏 / KPI 行 / 图表区 / 订单表 / 动态流",
    "deck": "封面 / 问题 / 解法 / 演示 / 数据 / 路线图 / 结尾",
    "poster": "主标题 / 关键信息 / 详情 / 行动栏",
    "archdoc": "标题头 / 分层图 / 流水线 / 组件表 / 决策",
    "doc": "标题头 / 摘要 / 章节 / 代码块 / 表格 / 页脚",
}


class AssetExpert(BaseExpert):
    name = "asset_expert"

    def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        brief = input.get("brief") or {}
        intent = input.get("intent") or brief.get("intent")
        if not intent or intent not in CONTENT_TYPES:
            intent, _, _ = classify_intent(str(brief)[:400])

        # 接入联盟路由（pipeline 已建过 router 时复用）
        router: Optional[AllianceRouter] = input.get("router")
        if router is None:
            router = AllianceRouter()

        route = router.route(brief, intent, skill_override=input.get("skill_override"))
        skill_used = route.get("skill")
        fallback_used = route.get("decision") == "fallback"

        # 调联盟 skill 拉真实素材；assets_path 是约定 manifest 中 {output} 占位
        out_assets = str(Path(input.get("output_dir") or ".") / "assets.json")
        Path(out_assets).parent.mkdir(parents=True, exist_ok=True)
        invocation: Dict[str, Any] = {"success": True, "skill": None,
                                       "fallback_used": False, "error": None}
        if skill_used and route.get("decision") != "local":
            invocation = router.invoke(
                skill_used, {"brief": brief, "intent": intent, "output": out_assets},
                timeout_s=int(input.get("timeout_s", 30)),
            )
            fallback_used = fallback_used or invocation.get("fallback_used", False)

        blocks: List[str] = list(_INTENT_BLOCKS.get(intent, _INTENT_BLOCKS["landing"]))
        asset_list = _extract_asset_list(invocation, blocks, intent)

        return {
            "intent": intent,
            "blocks": blocks,
            "block_notes": _BLOCK_NOTES.get(intent, ""),
            "asset_list": asset_list,
            "chart_data": invocation.get("chart_data") or {},
            "tokens": invocation.get("tokens") or {},
            "alliance_skill": skill_used,
            "skill_used": invocation.get("skill") or skill_used,
            "fallback_used": fallback_used,
            "invocation": {k: v for k, v in invocation.items()
                           if k in ("success", "fallback_used", "error")},
        }


def _extract_asset_list(invocation: Dict[str, Any], blocks: List[str],
                        intent: str) -> List[Dict[str, Any]]:
    """把联盟 invocation 输出（manifest entry 写出的 assets.json）合并到 blocks。"""
    out_path = invocation.get("output_path")
    if not out_path or not Path(out_path).exists():
        return [{"block": b, "source": "rules", "items": []} for b in blocks]
    try:
        import json
        data = json.loads(Path(out_path).read_text(encoding="utf-8"))
        items = data.get("items") or data.get("assets") or []
    except Exception:
        items = []
    return [{"block": b, "source": "alliance", "items": items} for b in blocks]
