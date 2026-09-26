"""v0.6 Phase 1: intake review workbench API (fetch → candidates → approve)."""

from __future__ import annotations

import json
from pathlib import Path

from htmlninefox import intake
from tests.conftest import WorkbenchServer
from test_server_project_api import request as api_request

SAMPLE = (b"<!doctype html><html><head><title>Inspo Landing</title>"
          b"<style>h1{color:#173C8F;font-family:'Satoshi',sans-serif}</style></head>"
          b"<body><header><h1>Inspo Landing</h1></header><main><section>hero</section></main></body></html>")


def stub_fetch(monkeypatch, pages: dict[str, tuple[int, dict, bytes]]):
    """Patch intake.fetch_reference with an in-memory site; still validates URLs."""

    def fake_fetch(url, **kwargs):
        intake.validate_url(url)   # the safety gate always runs
        if url not in pages:
            raise intake.IntakeError("intake_fetch_failed", "远端返回 HTTP 404", 502)
        status, headers, body = pages[url]
        return {
            "url": url, "final_url": url, "followed": [url], "status": status,
            "content_type": headers.get("content-type", "text/html"), "body": body,
            "body_sha256": "0" * 64, "body_bytes": len(body),
            "fetched_at": "2026-09-26T12:00:00",
        }

    monkeypatch.setattr(intake, "fetch_reference", fake_fetch)


def test_intake_review_flow_end_to_end(tmp_path: Path, monkeypatch) -> None:
    stub_fetch(monkeypatch, {"https://example.com/inspo": (200, {"content-type": "text/html"}, SAMPLE)})
    with WorkbenchServer(tmp_path) as server:
        base = server.base_url

        sources = api_request(base, "/api/intake/sources")
        assert "land-book" in {item["id"] for item in sources[0]["sources"]}

        submitted, _ = api_request(base, "/api/intake/fetch", "POST",
                                   {"url": "https://example.com/inspo", "source_id": "land-book"})
        candidate = submitted["candidate"]
        assert candidate["status"] == "pending"
        assert candidate["source"] == "land-book"
        assert candidate["license_class"] == "reference"
        assert candidate["tokens"]["colors"] == ["#173C8F"]
        assert candidate["skeleton"]["semantic"]["header"] == 1

        pending, _ = api_request(base, "/api/intake/candidates?status=pending")
        assert [item["candidate_id"] for item in pending["candidates"]] == [candidate["candidate_id"]]

        approved, _ = api_request(base, f"/api/intake/candidates/{candidate['candidate_id']}/approve",
                                  "POST", {})
        assert approved["candidate"]["status"] == "approved"
        gallery_name = approved["gallery_item"]["name"]
        assert gallery_name == "Inspo Landing"

        gallery, _ = api_request(base, "/api/gallery")
        assert any(item["name"] == gallery_name for item in gallery["items"])

        empty, _ = api_request(base, "/api/intake/candidates?status=pending")
        assert empty["candidates"] == []


def test_intake_fetch_rejects_private_urls(tmp_path: Path, monkeypatch) -> None:
    def boom(url, **kwargs):
        raise AssertionError("transport must not be reached for private hosts")

    monkeypatch.setattr(intake, "fetch_reference", boom)
    with WorkbenchServer(tmp_path) as server:
        busy, _ = api_request(server.base_url, "/api/intake/fetch", "POST",
                              {"url": "http://127.0.0.1:8620/api/health"}, expected=403)
        assert busy["error"]["code"] == "intake_host_forbidden"


def test_intake_fetch_reports_unknown_source(tmp_path: Path) -> None:
    with WorkbenchServer(tmp_path) as server:
        missing, _ = api_request(server.base_url, "/api/intake/fetch", "POST",
                                 {"url": "https://example.com/", "source_id": "nope"}, expected=404)
        assert missing["error"]["code"] == "intake_source_missing"
