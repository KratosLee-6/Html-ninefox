"""paraphrase.py · reference 正文的改写吸收（provenance 第三档 `paraphrased`）。

设计决策（ROADMAP 定案，v0.7.7 落地）：

  1. **改写由谁做**：配置了的 LLM（`llm.router`）。未配置或调用失败一律
     返回 None，块回落 `structure_only`——「离线可用」不被破坏，LLM 是
     能力升级而不是能力依赖。
  2. **改写发生在哪一步**：page_blocks（审核台预览拆块时）。用户看到并
     选择的文本就是改写后的文本——预览即所得。v0.7.4 的教训（预览与生成
     两种页面）不允许改写发生在生成时。
  3. **忠实度门禁**：`is_faithful`——改写与原文的字符三元组包含度不超过
     `OVERLAP_CEILING`、长度比例有界、非空且非原文。不过关按改写失败处理，
     `paraphrased` 不允许退化成带假标签的 `verbatim`。

职责边界：本模块的 `make_llm_rewriter` 只是**运输层**（调用 LLM，失败
返回 None）；忠实度判定属于许可规则层，由 `intake.page_blocks_from_candidate`
在标注 provenance 时执行——规则只有一个 owner，测试只盯一处。
"""
from __future__ import annotations

import re

from typing import Callable, Optional

# 改写与原文的字符三元组包含度上限（|tri(改写) ∩ tri(原文)| / |tri(改写)|）。
# 超过即视为照抄：中文连续 6 字大致对应 4 个三元组，0.5 的上限允许必要的
# 术语与专名重合，拒绝句式级别的搬运。
OVERLAP_CEILING = 0.5

# 改写文本长度必须有界：低于原文 40% 多半丢了事实，高于 180% 多半在注水。
MIN_REWRITE_RATIO = 0.4
MAX_REWRITE_RATIO = 1.8

_WHITESPACE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    return _WHITESPACE.sub("", str(text or "")).lower()


def _trigrams(text: str) -> set[str]:
    text = _normalize(text)
    return {text[i:i + 3] for i in range(len(text) - 2)} if len(text) >= 3 else set()


def overlap(source: str, rewrite: str) -> float:
    """改写文本的三元组有多少出现在原文里（包含度，0..1）。"""
    rewrite_tri = _trigrams(rewrite)
    if not rewrite_tri:
        return 0.0
    source_tri = _trigrams(source)
    return len(rewrite_tri & source_tri) / len(rewrite_tri)


def is_faithful(source: str, rewrite: str) -> bool:
    """改写是否配得上 `paraphrased`：真改写、长度有界、不照抄。

    这条是 `paraphrased` 的承重墙——没有它，改写通道就是一个带假标签的
    verbatim 通道，许可三档在字段级名存实亡。
    """
    rewrite_norm = _normalize(rewrite)
    source_norm = _normalize(source)
    if not rewrite_norm or not source_norm:
        return False
    if rewrite_norm == source_norm:
        return False
    ratio = len(rewrite_norm) / len(source_norm)
    if not (MIN_REWRITE_RATIO <= ratio <= MAX_REWRITE_RATIO):
        return False
    return overlap(source, rewrite) <= OVERLAP_CEILING


def rewrite_prompt(source: str, heading: str = "") -> str:
    head = f"小节标题：{heading}\n" if heading else ""
    return (head + "请把下面这段网页正文改写成原创表述：保留全部事实与信息，"
            "但必须更换句式与用词，禁止照抄任何连续 6 个字以上的原文片段，"
            "也不要添加原文没有的承诺、数字或联系方式。只输出改写后的正文，"
            "不要解释。\n\n原文：\n" + str(source or "").strip()[:2000])


def make_llm_rewriter(router) -> Callable[[str, str], Optional[str]]:
    """返回 `(source, heading) -> 改写文本 | None` 的运输层闭包。

    任何失败（未配置、网络、超时、空响应）都归一为 None，由许可规则层
    回落 structure_only。这里**不做**忠实度判定——那是 intake 的职责。
    """
    def rewriter(source: str, heading: str = "") -> Optional[str]:
        if not source or not source.strip():
            return None
        try:
            result = router.call(
                rewrite_prompt(source, heading),
                agent="brief_expert", task="paraphrase",
                temperature=0.4, max_tokens=2048, use_cache=True)
        except Exception:  # noqa: BLE001 - 未配置/网络/限额一律静默回落
            return None
        text = str(result).strip() if result is not None else ""
        return text or None
    return rewriter
