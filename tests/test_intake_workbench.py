"""v0.6 Phase 1: intake review workbench API (fetch → candidates → approve)."""

from __future__ import annotations

import json
import uuid
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

        # `reference` 的定义写在 data/sources/design-galleries.yaml 里：
        # 「可参考结构与风格，只提取令牌/骨架，产出必须原创重渲染」。
        # 所以批准它是对的——令牌与骨架已被上面的断言确认提取到了——
        # 但把它的整页 HTML 复制进模板库是违反这条声明的，那等于照搬。
        #
        # 这条断言过去写的是 gallery_item 非空，固化的正是那个错误行为：
        # 字段级的分块规则已经说 reference 只给结构不给正文，批准路径却
        # 整页放行，同一份许可在两条路径上得到相反结论。
        assert approved["gallery_item"] is None, \
            "reference 许可不得整页进入模板库"
        assert "reference" in (approved["gallery_skipped"] or ""), \
            f"跳过原因应说明是哪一档许可：{approved['gallery_skipped']!r}"

        gallery, _ = api_request(base, "/api/gallery")
        assert not any(item["name"] == "Inspo Landing" for item in gallery["items"]), \
            "reference 页面被写进了模板库"

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


# ---------------------------------------------------------------- S08 style presets


def test_approved_candidate_becomes_applicable_style_preset(tmp_path: Path, monkeypatch) -> None:
    stub_fetch(monkeypatch, {"https://example.com/inspo": (200, {"content-type": "text/html"}, SAMPLE)})
    with WorkbenchServer(tmp_path) as server:
        submitted, _ = api_request(server.base_url, "/api/intake/fetch", "POST",
                                   {"url": "https://example.com/inspo", "source_id": "land-book"})
        candidate_id = submitted["candidate"]["candidate_id"]

        # 未采纳的候选不能生成预设
        denied, _ = api_request(server.base_url, "/api/intake/style-presets/create", "POST",
                                {"candidate_id": candidate_id}, expected=409)
        assert denied["error"]["code"] == "intake_candidate_not_approved"

        api_request(server.base_url, f"/api/intake/candidates/{candidate_id}/approve", "POST", {})
        preset_result, _ = api_request(server.base_url, "/api/intake/style-presets/create", "POST",
                                       {"candidate_id": candidate_id})
        preset = preset_result["preset"]
        assert preset["colors"]["primary"] == "#173C8F"
        assert preset["license_class"] == "reference"

        # 应用 → 写入用户模板目录 → list_templates 可见
        # 注意：必须补丁基类 pathlib.Path.home。server/app.py 里 `Path.home()`
        # 解析到的是基类实现，打在 type(Path.home())（WindowsPath/PosixPath）
        # 上是空操作，会把产物写进真实的 ~/.htmlninefox。
        from htmlninefox import pipeline as pipeline_mod
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
        try:
            applied, _ = api_request(server.base_url,
                                     f"/api/intake/style-presets/{preset['preset_id']}/apply", "POST", {})
            applied_dir = Path(applied["applied"])
            assert applied_dir.is_dir(), f"apply 未产出模板目录：{applied['applied']!r}"
            style_json = applied_dir / "style.json"
            assert style_json.is_file(), f"apply 未产出 style.json：{style_json}"
            assert tmp_path in style_json.parents, f"产物泄漏到用户主目录之外：{style_json}"
            assert any(item["id"] == Path(style_json).parent.name
                       for item in pipeline_mod.list_templates()), "list_templates 看不到刚应用的预设"
        finally:
            monkeypatch.undo()


def test_style_preset_missing_reports_404(tmp_path: Path) -> None:
    with WorkbenchServer(tmp_path) as server:
        missing, _ = api_request(server.base_url,
                                 "/api/intake/style-presets/nope/apply", "POST", {}, expected=404)
        assert missing["error"]["code"] == "intake_preset_missing"


# ---------------------------------------------------------------- S09 component library

COMPONENT_PAGE = (b"<!doctype html><html><head><title>Comp Source</title></head><body>"
                  b'<nav class="topnav">links</nav>'
                  b'<section class="hero"><h1>Hero</h1><p>big</p></section></body></html>')


def test_components_import_requires_approved_components_kind(tmp_path: Path, monkeypatch) -> None:
    stub_fetch(monkeypatch, {"https://example.com/comp": (200, {"content-type": "text/html"}, COMPONENT_PAGE)})
    with WorkbenchServer(tmp_path) as server:
        submitted, _ = api_request(server.base_url, "/api/intake/fetch", "POST",
                                   {"url": "https://example.com/comp", "source_id": "codepen-picks"})
        candidate_id = submitted["candidate"]["candidate_id"]

        # 未采纳 → 409
        denied, _ = api_request(server.base_url, "/api/intake/components/import", "POST",
                                {"candidate_id": candidate_id}, expected=409)
        assert denied["error"]["code"] == "intake_candidate_not_approved"

        api_request(server.base_url, f"/api/intake/candidates/{candidate_id}/approve", "POST", {})
        result, _ = api_request(server.base_url, "/api/intake/components/import", "POST",
                                {"candidate_id": candidate_id})
        names = [item["name"] for item in result["registered"]]
        assert "topnav" in names and "hero" in names

        library, _ = api_request(server.base_url, "/api/intake/components")
        assert {item["name"] for item in library["components"]} >= {"topnav", "hero"}
        hero = next(item for item in library["components"] if item["name"] == "hero")
        assert hero["text"].startswith("Hero")
        assert "<h1>" in hero["snippet"]


def test_components_import_rejects_non_components_kind(tmp_path: Path, monkeypatch) -> None:
    stub_fetch(monkeypatch, {"https://example.com/inspo": (200, {"content-type": "text/html"}, SAMPLE)})
    with WorkbenchServer(tmp_path) as server:
        submitted, _ = api_request(server.base_url, "/api/intake/fetch", "POST",
                                   {"url": "https://example.com/inspo", "source_id": "land-book"})
        candidate_id = submitted["candidate"]["candidate_id"]
        api_request(server.base_url, f"/api/intake/candidates/{candidate_id}/approve", "POST", {})
        wrong, _ = api_request(server.base_url, "/api/intake/components/import", "POST",
                               {"candidate_id": candidate_id}, expected=409)
        assert wrong["error"]["code"] == "intake_kind_invalid"


def test_intake_motion_import_endpoint(tmp_path: Path, monkeypatch) -> None:
    motion_page = (b"<html><head><title>Motion API Inspo</title><style>"
                   b"h1{animation:fade 9s ease-in}</style></head>"
                   b"<body><main><h1>T</h1></main></body></html>")
    stub_fetch(monkeypatch, {"https://example.com/motion": (200, {"content-type": "text/html"}, motion_page)})
    with WorkbenchServer(tmp_path) as server:
        submitted, _ = api_request(server.base_url, "/api/intake/fetch", "POST",
                                   {"url": "https://example.com/motion", "source_id": "codrops"})
        candidate_id = submitted["candidate"]["candidate_id"]

        denied, _ = api_request(server.base_url, "/api/intake/motion/import", "POST",
                                {"candidate_id": candidate_id}, expected=409)
        assert denied["error"]["code"] == "intake_candidate_not_approved"

        api_request(server.base_url, f"/api/intake/candidates/{candidate_id}/approve", "POST", {})
        result, _ = api_request(server.base_url, "/api/intake/motion/import", "POST",
                                {"candidate_id": candidate_id})
        assert "prefers-reduced-motion" in result["motion"]["css"]

        listed, _ = api_request(server.base_url, "/api/intake/motion")
        assert len(listed["motions"]) == 1


# ---------------------------------------------------------------- S11 AI analysis


def _enable_ai(server_base: str, monkeypatch=None) -> None:
    import os
    previous = os.environ.get("HTMLNINEFOX_AI_SETTINGS")
    api_request(server_base, "/api/settings/ai", "PUT", {
        "enabled": True, "provider": "openai-compatible",
        "model": "test-model", "base_url": "https://llm.example/v1",
        "api_key": "fake-" + uuid.uuid4().hex[:12],   # 运行时生成的假凭据
    })
    if monkeypatch is not None:
        # PUT 会设置全局 env 指向本测试的临时目录；用 monkeypatch 在 teardown 恢复，
        # 避免污染后续测试（否则它们可能读到别的 AI 配置发起真实网络调用）。
        if previous:
            monkeypatch.setenv("HTMLNINEFOX_AI_SETTINGS", previous)
        else:
            monkeypatch.delenv("HTMLNINEFOX_AI_SETTINGS", raising=False)


def test_intake_ai_analyze_enriches_candidate(tmp_path: Path, monkeypatch, request) -> None:
    stub_fetch(monkeypatch, {"https://example.com/inspo": (200, {"content-type": "text/html"}, SAMPLE)})
    from htmlninefox.server import app as server_app

    canned = json.dumps({
        "description": "定价页采用三栏卡片与对比表",
        "tags": ["定价", "三栏", "SaaS"],
        "layout_notes": "顶部 hero + 三栏价格卡 + FAQ",
        "content_recipe": "封面/功能对比/常见问题",
    }, ensure_ascii=False)

    class FakeResult:
        text = canned
        model = "test-model"

    monkeypatch.setattr(server_app.llm.router, "call",
                        lambda **kwargs: FakeResult(), raising=True)
    with WorkbenchServer(tmp_path) as server:
        _enable_ai(server.base_url, monkeypatch)
        # llm.router 是模块级单例：分析后复位默认配置，避免污染后续测试
        request.addfinalizer(lambda: server_app.llm.router.configure(
            server_app.llm.get_default_config()))
        submitted, _ = api_request(server.base_url, "/api/intake/fetch", "POST",
                                   {"url": "https://example.com/inspo", "source_id": "land-book"})
        candidate_id = submitted["candidate"]["candidate_id"]

        analyzed, _ = api_request(server.base_url, "/api/intake/analyze", "POST",
                                  {"candidate_id": candidate_id})
        analysis = analyzed["candidate"]["ai_analysis"]
        assert "三栏" in analysis["description"]
        assert "定价" in analyzed["candidate"]["ai_tags"]

        stored, _ = api_request(server.base_url, "/api/intake/candidates?status=pending")
        assert stored["candidates"][0].get("ai_tags") == ["定价", "三栏", "SaaS"]


def test_intake_ai_analyze_requires_configured_ai(tmp_path: Path, monkeypatch) -> None:
    stub_fetch(monkeypatch, {"https://example.com/inspo": (200, {"content-type": "text/html"}, SAMPLE)})
    with WorkbenchServer(tmp_path) as server:
        submitted, _ = api_request(server.base_url, "/api/intake/fetch", "POST",
                                   {"url": "https://example.com/inspo"})
        candidate_id = submitted["candidate"]["candidate_id"]
        denied, _ = api_request(server.base_url, "/api/intake/analyze", "POST",
                                {"candidate_id": candidate_id}, expected=400)
        assert denied["error"]["code"] == "ai_not_configured"


# ---------------------------------------------------------------- S12 stats


def test_intake_stats_aggregate_across_assets(tmp_path: Path, monkeypatch) -> None:
    stub_fetch(monkeypatch, {
        "https://example.com/sourced": (200, {"content-type": "text/html"}, SAMPLE),
        "https://example.com/manual": (200, {"content-type": "text/html"},
                                       b"<html><head><title>Manual</title></head><body>y</body></html>"),
    })
    from htmlninefox.server import app as server_app
    monkeypatch.setattr(server_app._INTAKE_RATE_LIMITER, "default_interval", 0.0)
    with WorkbenchServer(tmp_path) as server:
        api_request(server.base_url, "/api/intake/fetch", "POST",
                    {"url": "https://example.com/sourced", "source_id": "land-book"})
        api_request(server.base_url, "/api/intake/fetch", "POST",
                    {"url": "https://example.com/manual"})
        approved, _ = api_request(server.base_url, "/api/intake/candidates?status=pending")
        ids = [item["candidate_id"] for item in approved["candidates"]]
        api_request(server.base_url, f"/api/intake/candidates/{ids[0]}/approve", "POST", {})

        stats, _ = api_request(server.base_url, "/api/intake/stats")
        data = stats["stats"]
        assert data["total"] == 2
        assert data["by_status"]["pending"] == 1 and data["by_status"]["approved"] == 1
        assert data["by_source"]["land-book"] == 1 and data["by_source"]["手动导入"] == 1
        assert data["by_license"]["reference"] == 2


# ---------------------------------------------------------------- S14 pptx export center


def test_export_center_pptx_end_to_end(tmp_path: Path) -> None:
    from htmlninefox import pipeline
    from tests.conftest import WorkbenchServer
    work = pipeline.run_expert("做一个产品发布会 PPT", intent_override="deck",
                               output=str(tmp_path), quiet_llm=True)["work"]
    with WorkbenchServer(tmp_path) as server:
        submitted, _ = api_request(server.base_url, "/api/exports", "POST",
                                   {"project_name": work.name, "format": "pptx"}, expected=202)
        job_id = submitted["job"]["id"]
        import time
        deadline = time.time() + 60
        job = {}
        while time.time() < deadline:
            job, _ = api_request(server.base_url, f"/api/jobs/{job_id}")
            if job["status"] not in {"queued", "running"}:
                break
            time.sleep(0.2)
        assert job["status"] == "succeeded", f"export 任务失败：{job.get('error', job)}"
        result = job["result"]
        assert result["format"] == "pptx"
        names = [f["name"] for f in result["files"]]
        assert any(name.endswith(".pptx") for name in names)
        assert any(name == "export-report.json" for name in names)
        # 降级与可编辑数在报告里
        assert "pptx" in json.dumps(result)


def test_inspiration_only_approve_skips_gallery_import(tmp_path: Path, monkeypatch) -> None:
    stub_fetch(monkeypatch, {"https://example.com/godly": (200, {"content-type": "text/html"}, SAMPLE)})
    with WorkbenchServer(tmp_path) as server:
        submitted, _ = api_request(server.base_url, "/api/intake/fetch", "POST",
                                   {"url": "https://example.com/godly", "source_id": "godly"})
        candidate_id = submitted["candidate"]["candidate_id"]
        assert submitted["candidate"]["license_class"] == "inspiration-only"

        result, _ = api_request(server.base_url, f"/api/intake/candidates/{candidate_id}/approve",
                                "POST", {})
        assert result["candidate"]["status"] == "approved"
        assert result["gallery_item"] is None
        assert "inspiration-only" in (result.get("gallery_skipped") or "")
        gallery, _ = api_request(server.base_url, "/api/gallery")
        assert not any(item.get("source") == "user" for item in gallery["items"])
