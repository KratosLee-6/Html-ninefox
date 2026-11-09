"""voice_profile.py · 语气档案（v0.9.3 · 融合 dsh-guizang-design 的语气档案思路）。

记录用户自己的写作习惯，给 copy_expert 的润色/去 AI 味当「保留什么」的依据：

  * 结构化条目：preferred_terms（常用词）/ forbidden_terms（禁词）/
    sentence_style（句长与节奏）/ openers（开头方式）/ closers（结尾方式）/
    salutation（称呼习惯）；
  * **证据纪律（上游 ≥2 处样本规则）**：每条特征必须带 evidence——出现过的
    源文本摘录列表；learn() 自动统计，证据 <2 条的特征**不入档**（宁缺勿错，
    一条样本很可能是偶然）；
  * 每条可人工改/删（handle_edit/handle_remove），人工编辑带 edited=True
    且不再被 learn 覆盖；
  * 存储独立于 project-memory.json（.settings/voice-profile.json），互不污染。

消费端：copy_expert.polish_slots 的禁词来自 forbidden_terms（在 memory.forbidden
之外叠加），summary_for_prompt() 给 LLM 一段紧凑的语气说明。
"""

from __future__ import annotations

import copy
import json
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from .project_memory import _now

PROFILE_FILE = "voice-profile.json"
PROFILE_VERSION = 1

MIN_EVIDENCE = 2          # 每条特征的最低样本证据数（上游纪律）
MAX_ENTRIES_PER_KIND = 12
MAX_TERM_LEN = 24
MAX_EXAMPLE_LEN = 60
MAX_EVIDENCE_PER_ENTRY = 4
MAX_SAMPLE = 4000         # 单次学习素材上限（字符）

_KINDS = ("preferred_terms", "forbidden_terms", "sentence_style",
          "openers", "closers", "salutation")

_SENTENCE_SPLIT = re.compile(r"[。！？!?;\n]+")


def _default_profile() -> dict[str, Any]:
    return {"version": PROFILE_VERSION, "entries": {}, "updated_at": ""}


def _clip(value: Any, limit: int) -> str:
    return "" if value is None else str(value).strip()[:limit]


def _locked(method):
    """实例级互斥（与 ProjectMemoryStore._locked 同语义，独立实现避免跨模块私用）。"""
    def wrapper(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)
    return wrapper


class VoiceProfileStore:
    """语气档案存储 + 学习器（线程安全，接口与 ProjectMemoryStore 同风格）。"""

    def __init__(self, output_root: str | Path):
        self.output_root = Path(output_root)
        self.path = self.output_root / ".settings" / PROFILE_FILE
        self._lock = threading.RLock()

    # ---------- 存取 ----------
    def _read_raw(self) -> dict[str, Any]:
        if not self.path.is_file():
            return _default_profile()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8", errors="replace"))
        except (json.JSONDecodeError, OSError):
            return _default_profile()
        return data if isinstance(data, dict) and data.get("version") else _default_profile()

    def _write(self, profile: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        profile["updated_at"] = _now()
        self.path.write_text(
            json.dumps(profile, ensure_ascii=False, indent=1), encoding="utf-8")

    def read(self) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._read_raw())

    # ---------- 学习 ----------
    @_locked
    def learn(self, samples: list[str]) -> dict[str, Any]:
        """从用户亲手写的文本里提取特征；证据 <MIN_EVIDENCE 的不入档。

        规则引擎提取（确定性、可门禁）——LLM 建档是后续可选增强，不在此处。"""
        texts = [t for t in (str(s or "") for s in samples) if t.strip()]
        if not texts:
            return self.read()
        corpus = "\n".join(texts)[: MAX_SAMPLE * len(texts)]
        evidence: dict[tuple[str, str], list[str]] = {}

        def add(kind: str, term: str, example: str) -> None:
            term, example = _clip(term, MAX_TERM_LEN), _clip(example, MAX_EXAMPLE_LEN)
            if not term or not example:
                return
            key = (kind, term)
            bucket = evidence.setdefault(key, [])
            if example not in bucket and len(bucket) < MAX_EVIDENCE_PER_ENTRY:
                bucket.append(example)

        # 常用词：滑窗 n-gram（2-6 字），跨样本合并计数——重复出现的字符串
        # 才是特征（裸正则按位置切词形不稳，证据永远凑不齐）。
        gram_counts: dict[str, int] = {}
        for text in texts:
            sample = text[:MAX_SAMPLE]
            sentences = [x.strip() for x in _SENTENCE_SPLIT.split(sample) if x.strip()]
            for sentence in sentences:
                for width in range(2, 7):
                    for start in range(0, max(0, len(sentence) - width + 1)):
                        gram = sentence[start:start + width]
                        gram_counts[gram] = gram_counts.get(gram, 0) + 1
                # 句长：以句为单位记录长度档
                length = len(sentence)
                bucket = "短句" if length <= 20 else "中句" if length <= 45 else "长句"
                add("sentence_style", bucket, sentence[:MAX_EXAMPLE_LEN])
            # 开头/结尾方式：每段文本的首句与末句
            if sentences:
                add("openers", sentences[0][:MAX_TERM_LEN], sentences[0])
                add("closers", sentences[-1][:MAX_TERM_LEN], sentences[-1])
        # 达到证据阈值的片段，长优先去重叠（保留的片段不再被子串占名额）
        frequent = sorted(
            (g for g, c in gram_counts.items() if c >= MIN_EVIDENCE and len(g) >= 2),
            key=len, reverse=True)
        kept: list[str] = []
        for gram in frequent:
            if not any(gram in kept_gram for kept_gram in kept):
                kept.append(gram)
            if len(kept) >= 8:
                break
        for gram in kept:
            # 证据按**句子**取（同一文本里出现 N 次=N 个不同句子证据；
            # 按文本取会三撞一，被证据纪律误杀——首跑实锤）
            hosts = [sen for sen in sentences if gram in sen] or [gram]
            for host in hosts[:MAX_EVIDENCE_PER_ENTRY]:
                add("preferred_terms", gram, host[:MAX_EXAMPLE_LEN])

        with self._lock:
            profile = self._read_raw()
            entries = profile.setdefault("entries", {})
            for (kind, term), examples in evidence.items():
                if len(examples) < MIN_EVIDENCE:
                    continue   # 证据纪律：<2 处样本不入档
                bucket = entries.setdefault(kind, [])
                existing = next((e for e in bucket if e["term"] == term), None)
                if existing:
                    for example in examples:
                        if example not in existing["evidence"] and len(existing["evidence"]) < MAX_EVIDENCE_PER_ENTRY:
                            existing["evidence"].append(example)
                elif len(bucket) < MAX_ENTRIES_PER_KIND:
                    bucket.append({"term": term, "evidence": examples,
                                   "edited": False, "added_at": _now()})
            # 各类按证据数降序裁剪到上限
            for kind in _KINDS:
                bucket = entries.get(kind)
                if bucket and len(bucket) > MAX_ENTRIES_PER_KIND:
                    entries[kind] = sorted(
                        bucket, key=lambda e: -len(e.get("evidence", [])))[:MAX_ENTRIES_PER_KIND]
            self._write(profile)
            return copy.deepcopy(profile)

    # ---------- 人工编辑 ----------
    @_locked
    def edit(self, kind: str, term: str, update: dict[str, Any]) -> dict[str, Any]:
        """人工修改一条（edited=True 后 learn 不再覆盖证据列表）。"""
        if kind not in _KINDS:
            raise ValueError(f"未知档案类别：{kind}")
        with self._lock:
            profile = self._read_raw()
            bucket = profile.setdefault("entries", {}).setdefault(kind, [])
            entry = next((e for e in bucket if e.get("term") == term), None)
            if entry is None:
                if isinstance(update.get("evidence"), list) and len(update["evidence"]) >= 1:
                    entry = {"term": _clip(term, MAX_TERM_LEN),
                             "evidence": [_clip(x, MAX_EXAMPLE_LEN)
                                          for x in update["evidence"][:MAX_EVIDENCE_PER_ENTRY]],
                             "edited": True, "added_at": _now()}
                    bucket.append(entry)
                else:
                    raise ValueError(f"档案中不存在该条目：{kind}/{term}")
            if isinstance(update.get("term"), str) and update["term"].strip():
                entry["term"] = _clip(update["term"], MAX_TERM_LEN)
            if isinstance(update.get("evidence"), list):
                entry["evidence"] = [_clip(x, MAX_EXAMPLE_LEN)
                                     for x in update["evidence"][:MAX_EVIDENCE_PER_ENTRY]]
            entry["edited"] = True
            self._write(profile)
            return copy.deepcopy(profile)

    @_locked
    def remove(self, kind: str, term: str) -> dict[str, Any]:
        if kind not in _KINDS:
            raise ValueError(f"未知档案类别：{kind}")
        with self._lock:
            profile = self._read_raw()
            bucket = profile.setdefault("entries", {}).setdefault(kind, [])
            profile["entries"][kind] = [e for e in bucket if e.get("term") != term]
            self._write(profile)
            return copy.deepcopy(profile)

    @_locked
    def clear(self) -> dict[str, Any]:
        with self._lock:
            profile = _default_profile()
            self._write(profile)
            return copy.deepcopy(profile)

    # ---------- 消费 ----------
    def forbidden_terms(self) -> list[str]:
        """禁词 = 档案 forbidden_terms + 各条目里用户明确标记过「不用」的词。

        与 project-memory.profile.forbidden 叠加由调用方完成。"""
        entries = self.read().get("entries", {}).get("forbidden_terms", [])
        return [e["term"] for e in entries if e.get("term")]

    def summary_for_prompt(self) -> str:
        """给 LLM 的紧凑语气说明（prompt 一段话，非结构化倒灌）。"""
        profile = self.read()
        entries = profile.get("entries", {})
        lines: list[str] = []
        terms = [e["term"] for e in entries.get("preferred_terms", [])[:6]]
        if terms:
            lines.append(f"偏好用词：{'、'.join(terms)}")
        forbidden = [e["term"] for e in entries.get("forbidden_terms", [])[:6]]
        if forbidden:
            lines.append(f"从不使用的词：{'、'.join(forbidden)}")
        style = [e["term"] for e in entries.get("sentence_style", [])[:3]]
        if style:
            lines.append(f"句子节奏：{'、'.join(style)}（以证据多数为准）")
        openers = [e["term"] for e in entries.get("openers", [])[:2]]
        if openers:
            lines.append(f"惯用开头：{' / '.join(openers)}")
        closers = [e["term"] for e in entries.get("closers", [])[:2]]
        if closers:
            lines.append(f"惯用结尾：{' / '.join(closers)}")
        salutation = entries.get("salutation", [])
        if salutation:
            lines.append(f"称呼习惯：{salutation[0].get('term', '')}")
        return "\n".join(lines)
