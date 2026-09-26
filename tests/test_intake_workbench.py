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


# ---------------------------------------------------------------- S04 batch import

import base64 as _base64
import io
import zipfile


def _zip_base64(pages: dict[str, str]) -> str:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        for name, html in pages.items():
            archive.writestr(name, html)
    return _base64.b64encode(buf.getvalue()).decode("ascii")


def test_intake_zip_import_creates_pending_candidates(tmp_path: Path) -> None:
    pages = {
        "a/page-one.html": "<html><head><title>Zip Page One</title></head><body><main>x</main></body></html>",
        "b/page-two.html": "<html><head><title>Zip Page Two</title></head><body><main>y</main></body></html>",
        "c/readme.txt": "not html",
    }
    with WorkbenchServer(tmp_path) as server:
        created, _ = api_request(server.base_url, "/api/intake/zip", "POST",
                                 {"zip_base64": _zip_base64(pages), "name": "inspo-pack"})
        ids = [item["candidate_id"] for item in created["created"]]
        assert len(ids) == 2
        assert all(item["status"] == "pending" for item in created["created"])
        titles = {item["title"] for item in created["created"]}
        assert titles == {"Zip Page One", "Zip Page Two"}

        pending, _ = api_request(server.base_url, "/api/intake/candidates?status=pending")
        assert {item["candidate_id"] for item in pending["candidates"]} == set(ids)


def test_intake_zip_rejects_non_archive(tmp_path: Path) -> None:
    with WorkbenchServer(tmp_path) as server:
        bad, _ = api_request(server.base_url, "/api/intake/zip", "POST",
                             {"zip_base64": _base64.b64encode(b"not a zip").decode("ascii")},
                             expected=400)
        assert bad["error"]["code"] == "intake_zip_invalid"


def test_intake_zip_without_html_is_rejected(tmp_path: Path) -> None:
    with WorkbenchServer(tmp_path) as server:
        empty, _ = api_request(server.base_url, "/api/intake/zip", "POST",
                               {"zip_base64": _zip_base64({"only.txt": "nope"})}, expected=400)
        assert empty["error"]["code"] == "intake_zip_empty"


def test_intake_fetch_batch_creates_and_reports_failures(tmp_path: Path, monkeypatch) -> None:
    from htmlninefox.server import app as server_app
    monkeypatch.setattr(server_app._INTAKE_RATE_LIMITER, "default_interval", 0.0)
    stub_fetch(monkeypatch, {
        "https://example.com/one": (200, {"content-type": "text/html"}, SAMPLE),
        "https://example.com/two": (200, {"content-type": "text/html"},
                                    b"<html><head><title>Page Two</title></head><body><main>x</main></body></html>"),
    })
    with WorkbenchServer(tmp_path) as server:
        result, _ = api_request(server.base_url, "/api/intake/fetch-batch", "POST",
                                {"urls": ["https://example.com/one", "https://example.com/two",
                                          "https://example.com/missing", "http://127.0.0.1:1/x"]})
        assert len(result["created"]) == 2
        assert {item["title"] for item in result["created"]} >= {"Inspo Landing", "Page Two"}
        codes = {item["code"] for item in result["failed"]}
        assert "intake_fetch_failed" in codes
        assert "intake_host_forbidden" in codes


def test_intake_fetch_batch_requires_urls(tmp_path: Path) -> None:
    with WorkbenchServer(tmp_path) as server:
        bad, _ = api_request(server.base_url, "/api/intake/fetch-batch", "POST",
                             {"urls": []}, expected=400)
        assert bad["error"]["code"] == "intake_url_invalid"


# ---------------------------------------------------------------- S05 review workbench

import urllib.request as _urlrequest


def test_intake_preview_is_served_without_scripts(tmp_path: Path, monkeypatch) -> None:
    stub_fetch(monkeypatch, {"https://example.com/inspo": (200, {"content-type": "text/html"}, SAMPLE)})
    with WorkbenchServer(tmp_path) as server:
        submitted, _ = api_request(server.base_url, "/api/intake/fetch", "POST",
                                   {"url": "https://example.com/inspo"})
        candidate_id = submitted["candidate"]["candidate_id"]
        raw = _urlrequest.urlopen(
            f"{server.base_url}/api/intake/candidates/{candidate_id}/preview", timeout=10)
        content = raw.read().decode("utf-8")
        headers = raw.headers
        assert "Inspo Landing" in content
        assert headers["Content-Security-Policy"] == "default-src 'none'; style-src 'unsafe-inline'; img-src data:"
        assert headers["X-Content-Type-Options"] == "nosniff"


def test_intake_batch_operations(tmp_path: Path, monkeypatch) -> None:
    stub_fetch(monkeypatch, {
        "https://example.com/one": (200, {"content-type": "text/html"}, SAMPLE),
        "https://example.com/two": (200, {"content-type": "text/html"},
                                    b"<html><head><title>Page Two</title></head><body>x</body></html>"),
    })
    from htmlninefox.server import app as server_app
    monkeypatch.setattr(server_app._INTAKE_RATE_LIMITER, "default_interval", 0.0)
    with WorkbenchServer(tmp_path) as server:
        ids = []
        for url in ("https://example.com/one", "https://example.com/two"):
            result, _ = api_request(server.base_url, "/api/intake/fetch", "POST", {"url": url})
            ids.append(result["candidate"]["candidate_id"])

        bad, _ = api_request(server.base_url, "/api/intake/candidates/batch", "POST",
                             {"action": "maybe", "ids": ids}, expected=400)
        assert bad["error"]["code"] == "intake_status_invalid"

        batch, _ = api_request(server.base_url, "/api/intake/candidates/batch", "POST",
                               {"action": "approve", "ids": ids})
        assert all(item["ok"] for item in batch["results"])
        approved, _ = api_request(server.base_url, "/api/intake/candidates?status=approved")
        assert {item["candidate_id"] for item in approved["candidates"]} == set(ids)


def test_intake_candidates_filter_by_source(tmp_path: Path, monkeypatch) -> None:
    stub_fetch(monkeypatch, {
        "https://example.com/sourced": (200, {"content-type": "text/html"},
                                        b"<html><head><title>Sourced</title></head><body>x</body></html>"),
        "https://example.com/manual": (200, {"content-type": "text/html"},
                                       b"<html><head><title>Manual</title></head><body>y</body></html>"),
    })
    with WorkbenchServer(tmp_path) as server:
        api_request(server.base_url, "/api/intake/fetch", "POST",
                    {"url": "https://example.com/sourced", "source_id": "land-book"})
        api_request(server.base_url, "/api/intake/fetch", "POST",
                    {"url": "https://example.com/manual"})  # manual, no source

        by_source, _ = api_request(server.base_url, "/api/intake/candidates?status=pending&source=land-book")
        assert len(by_source["candidates"]) == 1
        assert by_source["candidates"][0]["source"] == "land-book"

        manual, _ = api_request(server.base_url, "/api/intake/candidates?status=pending&source=")
        assert len(manual["candidates"]) == 2
