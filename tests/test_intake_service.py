"""IntakeService 直属单测：编排逻辑不再借 HTTP handler 测试。

P1-7 把候选编排从 `_Handler` 提取出来，编排逻辑的测试随之独立——
不启动服务、不走 HTTP，直接驱动 service 方法（抓取用 monkeypatch
替换传输层，与 tests/test_intake_workbench.py 的 stub_fetch 同缝）。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from htmlninefox import intake  # noqa: E402
from htmlninefox.server.intake_service import (  # noqa: E402
    INTAKE_RATE_LIMITER,
    IntakeService,
)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PAGE = ("<html><body><main><section><h2>标题</h2><p>正文</p></section>"
        "</main></body></html>").encode("utf-8")


class _GallerySpy:
    def __init__(self) -> None:
        self.imported: list[dict] = []

    def import_files(self, files, *, name="", tags=None):
        self.imported.append({"files": files, "name": name, "tags": tags})
        return {"name": name}


class _RefuseGallery:
    def import_files(self, *_a, **_k):
        raise AssertionError("reference 许可不得整页导入模板库")


@pytest.fixture()
def service(tmp_path, monkeypatch):
    monkeypatch.setattr(INTAKE_RATE_LIMITER, "default_interval", 0.0)
    svc = IntakeService(output_root=tmp_path, gallery=_GallerySpy())
    yield svc


def _stub_fetch(monkeypatch, pages: dict[str, tuple[int, bytes]], licence: str = "open"):
    def fake_fetch(url, **kwargs):
        status, body = pages[url]
        evidence = {
            "url": url, "final_url": url, "followed": [url], "status": status,
            "content_type": "text/html; charset=utf-8", "body": body,
            "body_sha256": "0" * 64, "body_bytes": len(body),
            "fetched_at": "2026-10-08T09:00:00",
        }
        source = {"id": "stub", "name": "stub", "kind": "gallery",
                  "license_class": licence, "entry_url": url}
        return intake.extract_candidate(evidence, source=source) or {}

    def fake_fetch_reference(url, **kwargs):
        status, body = pages[url]
        return {"url": url, "final_url": url, "followed": [url], "status": status,
                "content_type": "text/html; charset=utf-8", "body": body,
                "body_sha256": "0" * 64, "body_bytes": len(body),
                "fetched_at": "2026-10-08T09:00:00"}

    monkeypatch.setattr(intake, "fetch_reference", fake_fetch_reference)
    real_extract = intake.extract_candidate

    def extract_with_source(evidence, *, source=None, notes=""):
        evidence = dict(evidence)
        return real_extract(evidence, source=source, notes=notes)

    monkeypatch.setattr(intake, "extract_candidate", extract_with_source)


def test_fetch_creates_pending_candidate(service, monkeypatch):
    pages = {"https://example.com/a": (200, PAGE)}
    _stub_fetch(monkeypatch, pages)
    out = service.fetch({"url": "https://example.com/a", "source_id": None})
    candidate = out["candidate"]
    assert out["ok"] is True
    assert candidate[intake.CandidateKeys.STATUS] == "pending"
    stored = service.candidates().list()
    assert len(stored) == 1


def test_decide_reference_never_imports_whole_page(service, monkeypatch):
    pages = {"https://example.com/b": (200, PAGE)}
    _stub_fetch(monkeypatch, pages, licence="reference")
    out = service.fetch({"url": "https://example.com/b", "source_id": None})
    cid = out["candidate"][intake.CandidateKeys.CANDIDATE_ID]
    service.gallery = _RefuseGallery()
    decided = service.decide(cid, "approve")
    assert decided["gallery_item"] is None
    assert "reference" in (decided["gallery_skipped"] or "")


def test_page_blocks_read_only(service, monkeypatch):
    pages = {"https://example.com/c": (200, PAGE)}
    _stub_fetch(monkeypatch, pages, licence="open")
    out = service.fetch({"url": "https://example.com/c", "source_id": None})
    cid = out["candidate"][intake.CandidateKeys.CANDIDATE_ID]
    service.candidates().set_status(cid, "approved")
    result = service.page_blocks({"candidate_id": cid})
    assert result["ok"] is True and result["blocks"]
    # 只读：再次读取不产生新文件、候选不变
    before = sorted(p.name for p in (service.candidates().root / "candidates" / cid).iterdir())
    service.page_blocks({"candidate_id": cid})
    after = sorted(p.name for p in (service.candidates().root / "candidates" / cid).iterdir())
    assert before == after


def test_stats_aggregates_by_licence(service, monkeypatch):
    pages = {"https://example.com/d": (200, PAGE)}
    _stub_fetch(monkeypatch, pages, licence="reference")
    service.fetch({"url": "https://example.com/d", "source_id": None})
    stats = service.stats()
    assert stats["by_license"].get("reference") == 1


def test_rate_limiter_is_shared_instance():
    """app.py 的 `_INTAKE_RATE_LIMITER` 别名必须指向同一实例，
    既有测试按别名打补丁（default_interval=0）才仍然生效。"""
    import htmlninefox.server.app as server_app
    assert server_app._INTAKE_RATE_LIMITER is INTAKE_RATE_LIMITER
