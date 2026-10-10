# -*- coding: utf-8 -*-
"""IntakeService · 设计吸收的编排层（ROADMAP #11 P1-7 + #16 C8）。

历史：`app.py` 的 `_Handler` 同时承担 HTTP 解析与 intake 编排——抓取、
限速、来源解析、候选存取、许可治理、模板库导入、分块全部内联在请求
方法里。提取成具体类（审计注：今日只有 HTTP 一个 adapter，不要造
Protocol），handler 退回解析 + 错误映射。

依赖只走构造参数：output_root 与来源注册目录；gallery 由 output_root
派生。错误沿用 storage.StoreError（handler 已按 code→status 映射），
不另造错误类型。
"""
from __future__ import annotations

import base64
import hashlib
import re
from datetime import datetime
from pathlib import Path

from .. import intake
from ..user_gallery import UserGalleryError
from .storage import StoreError

# 限速器唯一实例；app.py 保留同名别名供既有测试打补丁（同对象生效）。
INTAKE_RATE_LIMITER = intake.RateLimiter(default_interval=6.0)


class IntakeService:
    """候选从抓取到采纳到拆分的全部编排；无 HTTP 概念。"""

    def __init__(self, output_root, gallery, sources_extra_dir=None) -> None:
        self.output_root = Path(output_root)
        self.gallery = gallery
        self.sources_extra_dir = (Path(sources_extra_dir) if sources_extra_dir
                                  else Path.home() / ".htmlninefox" / "sources")
        self.rate_limiter = INTAKE_RATE_LIMITER

    # ---- stores ------------------------------------------------------------
    def candidates(self) -> intake.CandidateStore:
        return intake.CandidateStore(self.output_root)

    def components(self) -> intake.ComponentStore:
        return intake.ComponentStore(self.output_root)

    def motion(self) -> intake.MotionStore:
        return intake.MotionStore(self.output_root)

    def style_presets(self) -> intake.StylePresetStore:
        return intake.StylePresetStore(self.output_root)

    # ---- 抓取 ----------------------------------------------------------------
    def _resolve_source(self, source_id: str) -> dict | None:
        if not source_id:
            return None
        source = intake.find_source(source_id, extra_dir=self.sources_extra_dir)
        if source is None:
            raise StoreError("intake_source_missing", f"来源不存在：{source_id}", 404)
        return source

    def fetch(self, body: dict) -> dict:
        url = str(body.get("url") or "").strip()
        if not url:
            raise StoreError("intake_url_invalid", "url 不能为空", 400)
        intake.validate_url(url)   # defense in depth: gate before any transport work
        source_id = str(body.get("source_id") or "").strip()
        source = self._resolve_source(source_id)
        self.rate_limiter.wait(source_id or intake.url_host(url) or "adhoc")
        evidence = intake.fetch_reference(url, headers={"Accept": "text/html"})
        candidate = intake.extract_candidate(evidence, source=source)
        candidate = self.candidates().save(candidate, evidence)
        return {"ok": True, "candidate": candidate}

    def fetch_batch(self, body: dict) -> dict:
        urls = intake.batch_urls(body.get("urls") if isinstance(body.get("urls"), list) else [])
        source_id = str(body.get("source_id") or "").strip()
        source = self._resolve_source(source_id)
        created: list[dict] = []
        failed: list[dict] = []
        for url in urls:
            key = source_id or intake.url_host(url) or "adhoc"
            try:
                intake.validate_url(url)
                self.rate_limiter.wait(key)
                evidence = intake.fetch_reference(url, headers={"Accept": "text/html"})
                candidate = intake.extract_candidate(evidence, source=source)
                created.append(self.candidates().save(candidate, evidence))
            except intake.IntakeError as error:
                failed.append({"url": url, "code": error.code, "message": error.message})
        return {"ok": True, "created": created, "failed": failed}

    def import_zip(self, body: dict) -> dict:
        import base64 as _base64
        try:
            data = _base64.b64decode(str(body.get("zip_base64") or ""), validate=True)
        except (ValueError, TypeError) as exc:
            raise StoreError("intake_zip_invalid", "ZIP 数据不是合法 Base64", 400) from exc
        members = intake.zip_html_entries(data)
        created: list[dict] = []
        for member in members:
            evidence = {
                "url": f"zip://{body.get('name') or 'upload'}/{member['name']}",
                "final_url": f"zip://{body.get('name') or 'upload'}/{member['name']}",
                "followed": [], "status": 200,
                "content_type": "text/html", "body": member["body"],
                "body_sha256": hashlib.sha256(member["body"]).hexdigest(),
                "body_bytes": len(member["body"]),
                "fetched_at": datetime.now().isoformat(timespec="seconds"),
            }
            candidate = intake.extract_candidate(
                evidence, source=None,
                notes=f"ZIP 手动导入：{body.get('name') or 'upload'}")
            created.append(self.candidates().save(candidate, evidence))
        return {"ok": True, "created": created}

    # ---- 审核 ----------------------------------------------------------------
    def decide(self, candidate_id: str, action: str) -> dict:
        store = self.candidates()
        candidate = store.set_status(candidate_id, "approved" if action == "approve" else "rejected")
        gallery_item = None
        gallery_skipped = None
        if action == "approve":
            # 许可治理：只有 open 许可允许整页代码进入模板库。分块通道问的
            # 是同一个问题（licence_of / may_carry_verbatim_text），答案只有
            # 一处——reference 不再出现「一边只给结构、一边整页复制」的矛盾。
            licence = intake.licence_of(candidate)
            if not intake.may_carry_verbatim_text(licence):
                return {"ok": True, "candidate": candidate, "gallery_item": None,
                        "gallery_skipped": f"{licence}：仅作灵感板，不做代码导入"}
            safe_name = re.sub(r"[^\w.-]+", "-", candidate[intake.CandidateKeys.TITLE]).strip("-")[:60] or "intake-candidate"
            tags = ["intake"]
            if candidate.get(intake.CandidateKeys.SOURCE):
                tags.append(candidate[intake.CandidateKeys.SOURCE])
            try:
                gallery_item = self.gallery.import_files(
                    [{"name": f"{safe_name}.html",
                      "data_base64": base64.b64encode(store.body(candidate_id)).decode("ascii")}],
                    name=candidate[intake.CandidateKeys.TITLE], tags=tags)
            except UserGalleryError as exc:
                raise StoreError("intake_import_failed", str(exc), 409) from exc
        return {"ok": True, "candidate": candidate, "gallery_item": gallery_item,
                "gallery_skipped": gallery_skipped}

    # ---- 拆解与再利用 ----------------------------------------------------------
    def motion_import(self, body: dict) -> dict:
        candidate_id = str(body.get("candidate_id") or "")
        candidate = self.candidates().get(candidate_id)
        entry = self.motion().import_from_candidate(candidate)
        return {"ok": True, "motion": entry}

    def components_import(self, body: dict) -> dict:
        candidate_id = str(body.get("candidate_id") or "")
        candidate = self.candidates().get(candidate_id)
        registered = self.components().import_from_candidate(candidate)
        return {"ok": True, "registered": registered}

    def style_preset_create(self, body: dict) -> dict:
        candidate_id = str(body.get("candidate_id") or "")
        store = self.candidates()
        candidate = store.get(candidate_id)
        if candidate.get(intake.CandidateKeys.STATUS) != "approved":
            raise StoreError("intake_candidate_not_approved",
                             "只有已采纳的候选才能生成风格预设", 409)
        preset = intake.build_style_preset(candidate)
        return {"ok": True, "preset": self.style_presets().save(preset)}

    def page_blocks(self, body: dict) -> dict:
        """把已采纳候选的分区切成生成通道认识的 block。只读不写回。"""
        candidate_id = str(body.get("candidate_id") or "")
        store = self.candidates()
        candidate = store.get(candidate_id)
        if candidate.get(intake.CandidateKeys.STATUS) != "approved":
            raise StoreError("intake_candidate_not_approved",
                             "只有已采纳的候选才能拆成分区", 409)
        raw = store.body(candidate_id)
        blocks = intake.page_blocks_from_candidate(
            candidate, raw.decode("utf-8", "replace"))
        return {
            "ok": True,
            "candidate": candidate,
            "blocks": blocks,
            "license_class": intake.licence_of(candidate),
            "carries_text": any(b.get("provenance") == "verbatim" for b in blocks),
            "block_notes": "从页面拆出的分区；结构与顺序可用，正文仅在开放许可时随行",
        }

    # ---- 统计 ----------------------------------------------------------------
    def stats(self) -> dict:
        candidates = self.candidates().list()
        by_status: dict[str, int] = {}
        by_source: dict[str, int] = {}
        by_license: dict[str, int] = {}
        for item in candidates:
            status = item.get(intake.CandidateKeys.STATUS, "pending")
            by_status[status] = by_status.get(status, 0) + 1
            source = item.get(intake.CandidateKeys.SOURCE) or "手动导入"
            by_source[source] = by_source.get(source, 0) + 1
            lic = intake.licence_of(item)
            by_license[lic] = by_license.get(lic, 0) + 1
        return {
            "total": len(candidates),
            "by_status": by_status,
            "by_source": by_source,
            "by_license": by_license,
            "components": len(self.components().list()),
            "motion_styles": len(self.motion().list()),
            "style_presets": len(self.style_presets().list()),
        }
