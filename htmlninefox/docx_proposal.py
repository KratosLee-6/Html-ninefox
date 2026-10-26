"""docx proposal (v0.8.1 · step 2): an `intake_outline` → a reviewable proposal.

The proposal is the handover artefact between "we read the document" and "we
render it": intent, a style choice with its reason, an image plan (slots with
prompts, not images), and copy a human can edit. AI proposes, the person
approves — so every field here is explainable and editable, and the offline
rule engine must produce a usable proposal on its own. A configured LLM is an
upgrade: it may refine the fields, it may never be required.

The rule engine is deliberately boring. Guessing wrong is cheap for a person to
fix in the review desk; guessing silently is not. Every choice therefore
carries a `reason` string, and the proposal says out loud when it was made
without a model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .generators._tokens import INTENT_TONE_PRESET, PRESETS
from .intake_outline import IntakeOutline

INTENTS = ("doc", "archdoc", "deck", "dashboard", "poster", "landing")

# 意图判定的关键词（中文为主，英文兜底）。命中标题或任一级标题即算。
_ARCHDOC_WORDS = ("架构", "拓扑", "部署", "系统设计", "architecture", "deployment")
_POSTER_WORDS = ("海报", "poster", "宣传单", "banner")
_DECK_WORDS = ("发布会", "分享会", "演讲", "路演", "keynote", "slides")

# 每种意图的默认语气（决定落到哪个既有预设）。
_INTENT_TONE = {"deck": "editorial", "poster": "vibrant",
                "dashboard": "techy", "doc": "professional",
                "archdoc": "professional", "landing": "minimal"}


@dataclass(frozen=True)
class ImagePlanItem:
    slot: str
    purpose: str
    prompt: str

    def as_dict(self) -> dict:
        return {"slot": self.slot, "purpose": self.purpose, "prompt": self.prompt}


@dataclass(frozen=True)
class Proposal:
    intent: str
    intent_reason: str
    preset_id: str
    style_reason: str
    image_plan: tuple[ImagePlanItem, ...]
    copy: dict[str, Any]
    limitations: tuple[str, ...] = ()
    refined_by: str = "rules"

    def validate(self) -> "Proposal":
        if self.intent not in INTENTS:
            raise ValueError(f"未知意图：{self.intent}")
        if self.preset_id not in PRESETS:
            raise ValueError(f"未知预设：{self.preset_id}")
        if not self.copy.get("headline"):
            raise ValueError("提案缺少 headline")
        for item in self.image_plan:
            if not item.prompt.strip():
                raise ValueError(f"图片位 {item.slot} 没有提示词")
        return self

    def as_dict(self) -> dict:
        """Machine-readable handover: external agents edit this, humans approve it."""
        return {
            "intent": self.intent,
            "intent_reason": self.intent_reason,
            "style": {"preset_id": self.preset_id, "reason": self.style_reason},
            "image_plan": [item.as_dict() for item in self.image_plan],
            "copy": dict(self.copy),
            "limitations": list(self.limitations),
            "refined_by": self.refined_by,
        }


# 目录类标题不能当章节，也不能给它配图位——真实商务文档的第一个
# Heading1 常常就是「目录」，把它当章节会得到一张「目录」配图。
_TOC_HEADS = {"目录", "目 录", "contents", "table of contents"}


def _is_toc(heading: str) -> bool:
    return heading.strip().lower() in _TOC_HEADS


def _one_line(text: str) -> str:
    """压掉换行与多余空白：摘要要能直接放版式里。"""
    return " ".join(text.split())


def _text_of(outline: IntakeOutline) -> str:
    parts = [outline.source.title]
    for block in outline.blocks:
        if block.kind == "heading":
            parts.append(block.heading)
        elif block.kind in {"paragraph", "list"}:
            parts.append(block.content)
    return " ".join(parts)


def _has(text: str, words: tuple[str, ...]) -> bool:
    low = text.lower()
    return any(word.lower() in low for word in words)


def _judge_intent(outline: IntakeOutline) -> tuple[str, str]:
    counts = outline.counts
    headings = counts.get("heading", 0)
    paragraphs = counts.get("paragraph", 0)
    tables = counts.get("table", 0)
    title = outline.source.title
    text = f"{title} " + " ".join(b.heading for b in outline.blocks if b.kind == "heading")

    if _has(text, _POSTER_WORDS) and len(outline.blocks) <= 12:
        return "poster", "标题或章节出现海报类词，且正文块不超过 12 个"
    if _has(text, _ARCHDOC_WORDS) and tables <= 8:
        return "archdoc", "标题或章节出现架构/部署类词，且没有大量表格"
    if tables >= 4 and headings <= 8 and paragraphs <= tables:
        return "dashboard", (f"{tables} 张表、{headings} 个标题、仅 {paragraphs} 段正文："
                             f"结构更像数据看板")
    if tables <= 2 and headings >= 6 and paragraphs <= headings * 2.5:
        return "deck", (f"{headings} 个标题、仅 {paragraphs} 段正文："
                        f"章节多而正文短，更像逐页讲稿")
    if _has(text, _DECK_WORDS):
        return "deck", "标题出现发布会/分享类词，按演示结构处理"
    if outline.source.kind == "pptx":
        # 格式本身就是证据：一页一题的演示，页数少时上面的结构判定会漏判
        # 成 doc——来源是 pptx 时按 deck 处理，除非更强的信号已经命中。
        return "deck", "来源是演示文稿，页题即章节，按 deck 结构处理"
    return "doc", f"{headings} 个标题、{paragraphs} 段正文、{tables} 张表：按文档结构处理"


def _style_for(intent: str) -> tuple[str, str]:
    tone = _INTENT_TONE.get(intent, "professional")
    preset_id = INTENT_TONE_PRESET.get(intent, {}).get(tone, "doc-clean")
    return preset_id, (f"意图 {intent} × 语气 {tone}：沿用既有预设 "
                       f"{preset_id}（未新建风格，可在上方直接换）")


def _image_plan(outline: IntakeOutline) -> tuple[ImagePlanItem, ...]:
    title = outline.source.title or "未命名文档"
    plan: list[ImagePlanItem] = [ImagePlanItem(
        slot="cover",
        purpose="封面主视觉",
        prompt=(f"为《{title}》做一张封面图：暖纸白底、深钴蓝主色、薄荷绿点缀，"
                "编辑感排版，留出标题安全区，无文字，横向 16:9"),
    )]
    sections = [b.heading for b in outline.blocks
                if b.kind == "heading" and b.heading and not _is_toc(b.heading)][:4]
    for index, heading in enumerate(sections, start=1):
        if index > 3:
            break
        plan.append(ImagePlanItem(
            slot=f"section-{index}",
            purpose=f"「{heading}」章节分隔",
            prompt=(f"章节配图，主题「{heading}」：抽象的纸张与网格质感，"
                    "钴蓝结构线、薄荷绿高光，不要文字与人脸，横幅 21:9"),
        ))
    if len(plan) == 1:
        plan.append(ImagePlanItem(
            slot="section-1",
            purpose="内页配图",
            prompt=(f"《{title}》的内页配图：结构化的信息图底纹，钴蓝与薄荷绿，"
                    "留白充足，无文字，横幅 21:9"),
        ))
    return tuple(plan)


def _copy(outline: IntakeOutline) -> dict[str, Any]:
    title = outline.source.title or next(
        (b.heading for b in outline.blocks if b.kind == "heading" and b.heading), "未命名文档")
    paragraphs = [b for b in outline.blocks if b.kind in {"paragraph", "list"} and b.content]
    summary = _one_line(paragraphs[0].content)[:120] if paragraphs else ""
    outline_sections = []
    for block in outline.blocks:
        if block.kind != "heading" or not block.heading or _is_toc(block.heading):
            continue
        outline_sections.append({"heading": block.heading[:80], "level": block.level})
        if len(outline_sections) >= 12:
            break
    return {
        "headline": _one_line(title)[:60],
        "summary": summary,
        "sections": outline_sections,
        "key_points": [_one_line(b.content)[:80] for b in paragraphs
                       if b.kind == "list"][:6],
    }


def propose(outline: IntakeOutline,
            refiner: Callable[[IntakeOutline, "Proposal"], dict | None] | None = None
            ) -> Proposal:
    """Produce a proposal from an outline. Offline rules first; LLM may refine.

    `refiner` is optional and must return a dict of overrides. Whatever it
    returns still goes through `validate()`, so a bad refiner fails loudly
    instead of shipping a half-filled proposal.
    """
    intent, intent_reason = _judge_intent(outline)
    preset_id, style_reason = _style_for(intent)
    limitations = list(outline.limitations)
    limitations.append("未配置 LLM：意图 / 风格 / 图片位由规则引擎给出，可在审核台直接改")

    proposal = Proposal(
        intent=intent,
        intent_reason=intent_reason,
        preset_id=preset_id,
        style_reason=style_reason,
        image_plan=_image_plan(outline),
        copy=_copy(outline),
        limitations=tuple(limitations),
    )

    if refiner is not None:
        overrides = refiner(outline, proposal) or {}
        if overrides:
            data = proposal.as_dict()
            # 只允许覆盖提案字段，不允许改契约形状
            for key in ("intent", "intent_reason", "copy", "limitations"):
                if key in overrides:
                    data[key] = overrides[key]
            style = dict(data["style"])
            style.update(overrides.get("style") or {})
            if "image_plan" in overrides:
                data["image_plan"] = overrides["image_plan"]
            proposal = Proposal(
                intent=data["intent"],
                intent_reason=data["intent_reason"],
                preset_id=style.get("preset_id", proposal.preset_id),
                style_reason=style.get("reason", proposal.style_reason),
                image_plan=tuple(
                    item if isinstance(item, ImagePlanItem) else ImagePlanItem(**item)
                    for item in data["image_plan"]),
                copy=data["copy"],
                limitations=tuple(data["limitations"]),
                refined_by="llm",
            )

    return proposal.validate()
