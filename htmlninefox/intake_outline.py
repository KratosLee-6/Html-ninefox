"""The intake handover artefact (v0.8.1): one shape for every input format.

Why one shape
-------------
The page-block channel, the DOCX parser and (next) PPTX/PDF all answer the same
question — "what does this source actually contain, and where did that come
from?" — so they must produce the same artefact. Format-specific models would
force the review desk, the proposal layer and the six generators to grow a
branch per format.

Two things are mandatory here, and they are the lessons worth stealing from
REA (morluto/rea): **every block carries evidence** (a locator you can follow
back to the source) and **every outline carries its limitations** (what was not
read, rather than silence). A block without a locator is not allowed into the
review desk — an unverifiable claim is worse than no claim.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# 允许的块类型。新增类型要同时更新审核台渲染与生成器消费。
BLOCK_KINDS = frozenset({"heading", "paragraph", "list", "table", "image", "section"})

# 版权三档，与 intake.py 的 provenance 同名同义。
PROVENANCES = frozenset({"verbatim", "paraphrased", "structure_only"})

# 至少命中一个，才算「可以回指」。
LOCATOR_KEYS = ("path", "paragraph", "slide", "page", "chars")


class IntakeOutlineError(ValueError):
    """The outline breaks the contract — fail here, not in the review desk."""

    code = "intake_outline_invalid"


@dataclass(frozen=True)
class SourceInfo:
    kind: str                       # html | docx | pptx | pdf | image
    ref: str                        # path, URL, or upload://…
    digest: str = ""                # sha256:…
    origin: str = "user_upload"     # user_upload | public_url
    licence: str = "user_owned"     # open | reference | inspiration-only | user_owned
    title: str = ""                 # 文档自带标题（core.xml / <title> / 文件名）


@dataclass(frozen=True)
class AdapterInfo:
    name: str
    version: int = 1
    offline: bool = True
    requires: tuple[str, ...] = ()


@dataclass(frozen=True)
class Block:
    id: str
    kind: str
    heading: str = ""
    content: str = ""
    level: int = 0
    rows: tuple[tuple[str, ...], ...] = ()
    asset: str = ""
    provenance: str = "verbatim"
    evidence: dict[str, Any] = field(default_factory=dict)
    ordinal: int = 0

    def as_dict(self) -> dict:
        data: dict[str, Any] = {
            "id": self.id,
            "kind": self.kind,
            "provenance": self.provenance,
            "evidence": dict(self.evidence),
            "ordinal": self.ordinal,
        }
        if self.heading:
            data["heading"] = self.heading
        if self.content:
            data["content"] = self.content
        if self.level:
            data["level"] = self.level
        if self.rows:
            data["rows"] = [list(row) for row in self.rows]
        if self.asset:
            data["asset"] = self.asset
        return data

    def locator(self) -> dict:
        """Only the keys that make this block traceable."""
        return {k: v for k, v in self.evidence.items() if k in LOCATOR_KEYS}


@dataclass(frozen=True)
class IntakeOutline:
    source: SourceInfo
    adapter: AdapterInfo
    blocks: tuple[Block, ...]
    assets: dict[str, bytes] = field(default_factory=dict)
    limitations: tuple[str, ...] = ()

    @property
    def counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for block in self.blocks:
            counts[block.kind] = counts.get(block.kind, 0) + 1
        return counts

    @property
    def evidence_complete(self) -> bool:
        return all(block.locator() for block in self.blocks)

    def validate(self) -> "IntakeOutline":
        """Contract checks. Raises instead of letting a half-formed outline through."""
        if self.source.kind not in {"html", "docx", "pptx", "pdf", "image"}:
            raise IntakeOutlineError(f"未知来源类型：{self.source.kind}")
        if self.source.origin not in {"user_upload", "public_url"}:
            raise IntakeOutlineError(f"未知来源：{self.source.origin}")
        if self.source.licence not in {"open", "reference", "inspiration-only", "user_owned"}:
            raise IntakeOutlineError(f"未知许可档位：{self.source.licence}")
        for block in self.blocks:
            if block.kind not in BLOCK_KINDS:
                raise IntakeOutlineError(f"块 {block.id} 的类型不受支持：{block.kind}")
            if block.provenance not in PROVENANCES:
                raise IntakeOutlineError(f"块 {block.id} 的 provenance 非法：{block.provenance}")
            if not block.locator():
                raise IntakeOutlineError(
                    f"块 {block.id} 没有可回指的位置（{LOCATOR_KEYS}），不允许进审核台")
        return self

    def as_dict(self) -> dict:
        """Machine-readable handover. External agents drive this."""
        return {
            "source": {
                "kind": self.source.kind,
                "ref": self.source.ref,
                "digest": self.source.digest,
                "origin": self.source.origin,
                "licence": self.source.licence,
                "title": self.source.title,
            },
            "adapter": {
                "name": self.adapter.name,
                "version": self.adapter.version,
                "offline": self.adapter.offline,
                "requires": list(self.adapter.requires),
            },
            "blocks": [block.as_dict() for block in self.blocks],
            "assets": [{"part": name, "bytes": len(payload)}
                       for name, payload in sorted(self.assets.items())],
            "counts": self.counts,
            "evidence_complete": self.evidence_complete,
            "limitations": list(self.limitations),
        }


def paragraph_evidence(index: int, **extra: Any) -> dict[str, Any]:
    """A 1-based locator into a document body — the DOCX adapter's evidence shape."""
    return {"paragraph": index, **extra}
