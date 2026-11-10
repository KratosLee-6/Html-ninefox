"""Workflow presets (0.9.4 · 拼装层第一批).

六条跨意图工作流剧本（思路致敬 dsh-guizang-design 的工作流表）：
每条是「步骤列表」，步骤引用能力而非具体 skill——引擎按能力路由到
本地管线（analyze/generate/feedback/export），联盟成员装了则可接管。

数据是纯声明：步骤由工作台/agent 按顺序推进，每步产出喂下一步。
"""

from __future__ import annotations

from typing import Any

WORKFLOWS: tuple[dict[str, Any], ...] = (
    {
        "id": "one-article-three-outputs",
        "name": "一篇文章，三种出口",
        "description": "同一篇文章排成落地页，再做海报与文档版——三个出口同一套主题",
        "steps": [
            {"ability": "generate", "intent": "landing",
             "note": "文章正文 → 落地页（主出口）"},
            {"ability": "generate", "intent": "poster",
             "note": "同素材提炼 → 活动海报（分享出口）"},
            {"ability": "generate", "intent": "doc",
             "note": "全文 → 文档版（阅读出口）"},
        ],
        "family_hint": True,   # 三步建议同家族 preset（主题一家人）
    },
    {
        "id": "decompose-then-adopt",
        "name": "旧文档翻新",
        "description": "Word/PPT/PDF 拆成带出处的提案，审核采纳后生成全新产物",
        "steps": [
            {"ability": "intake", "note": "上传旧文档 → 拆分提案（逐块带出处）"},
            {"ability": "adopt", "note": "审核采纳（可改文案/换图）→ 生成"},
        ],
    },
    {
        "id": "speech-recycle",
        "name": "演讲回收",
        "description": "讲完的 PPT 连讲稿备注一起整理成文章，再排成网页",
        "steps": [
            {"ability": "intake", "note": "贴入 PPT（含讲稿备注）→ 提案"},
            {"ability": "adopt", "note": "整理成文章结构 → 生成 doc 网页"},
        ],
    },
    {
        "id": "brand-suite",
        "name": "品牌套件",
        "description": "品牌色生成受约束主题，落地页与海报统一用它",
        "steps": [
            {"ability": "generate", "intent": "landing",
             "note": "品牌主色 + 项目记忆 → 落地页"},
            {"ability": "generate", "intent": "poster",
             "note": "同一品牌色 → 海报（同家族 preset）"},
        ],
        "family_hint": True,
    },
    {
        "id": "iterate-with-voice",
        "name": "口语迭代",
        "description": "生成后用口语反馈连续改稿，每轮都是可回滚的新修订",
        "steps": [
            {"ability": "generate", "intent": "landing", "note": "先出一版"},
            {"ability": "feedback", "note": "口语反馈（标题大一点…）→ rev+1"},
            {"ability": "export", "note": "满意后导出交付"},
        ],
    },
    {
        "id": "bundle-delivery",
        "name": "一键交付",
        "description": "按意图自动组包：产物 + 全格式导出打 zip，交付出厂即走",
        "steps": [
            {"ability": "export", "note": "桌面壳 📦 / 导出中心一键交付包"},
        ],
    },
)


def list_workflows() -> list[dict[str, Any]]:
    return [dict(w) for w in WORKFLOWS]


def get_workflow(workflow_id: str) -> dict[str, Any] | None:
    for workflow in WORKFLOWS:
        if workflow["id"] == workflow_id:
            return dict(workflow)
    return None
