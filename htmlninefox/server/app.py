"""Local HTTP interface for the Html九尾狐 Web and PWA clients."""

from __future__ import annotations

import json
import mimetypes
import os
import shutil
import sys
import traceback
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, unquote, urlparse

from .. import __version__, exporting, llm, pipeline, project_memory, revisions, template_gallery
from ..application import (
    ExportError, ExportRequest, ExportResult,
    FeedbackError, FeedbackRequest, FeedbackResult,
    GenerationBlock, GenerationError, GenerationRequest, GenerationResult,
    RestoreError, RestoreRequest, StudioApplication, StudioDependencies,
)
from ..user_gallery import UserGalleryError, UserGalleryStore
from .diagnostics import create_diagnostic_bundle
from .inputs import InputError, InputStore
from .jobs import get_job_manager
from .settings import AISettingsStore
from .storage import ProjectStore, StoreError

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_FILES = {
    "/manifest.webmanifest": ("manifest.webmanifest", "application/manifest+json; charset=utf-8", "no-cache"),
    "/sw.js": ("sw.js", "application/javascript; charset=utf-8", "no-cache"),
    "/icon.svg": ("icon.svg", "image/svg+xml; charset=utf-8", "public, max-age=86400"),
    "/logo-mark.svg": ("logo-mark.svg", "image/svg+xml; charset=utf-8", "public, max-age=86400"),
    "/logo-horizontal.svg": ("logo-horizontal.svg", "image/svg+xml; charset=utf-8", "public, max-age=86400"),
    "/canvas-engine.js": ("canvas-engine.js", "application/javascript; charset=utf-8", "no-cache"),
    "/interaction-system.js": ("interaction-system.js", "application/javascript; charset=utf-8", "no-cache"),
    "/lifecycle-projects.js": ("lifecycle-projects.js", "application/javascript; charset=utf-8", "no-cache"),
    "/lifecycle-generation.js": ("lifecycle-generation.js", "application/javascript; charset=utf-8", "no-cache"),
    "/lifecycle-revisions.js": ("lifecycle-revisions.js", "application/javascript; charset=utf-8", "no-cache"),
    "/lifecycle-exports.js": ("lifecycle-exports.js", "application/javascript; charset=utf-8", "no-cache"),
    "/motion-system.js": ("motion-system.js", "application/javascript; charset=utf-8", "no-cache"),
    "/motion-lab": ("motion-lab.html", "text/html; charset=utf-8", "no-cache"),
    "/canvas-productivity.js": ("canvas-productivity.js", "application/javascript; charset=utf-8", "no-cache"),
    "/workbench-features.js": ("workbench-features.js", "application/javascript; charset=utf-8", "no-cache"),
    "/workbench-ui.js": ("workbench-ui.js", "application/javascript; charset=utf-8", "no-cache"),
    "/workbench-system.css": ("workbench-system.css", "text/css; charset=utf-8", "no-cache"),
}
APP_CAPABILITIES = {
    "api_version": "v1",
    "clients": {
        "web": "ready",
        "pwa": "ready",
        "windows": "beta",
        "linux": "beta",
        "macos": "planned",
        "ios": "planned",
        "android": "later",
        "wechat_mini_program": "later",
    },
    "features": [
        "generate", "analyze", "feedback", "projects", "project_crud",
        "workspace_recovery", "jobs", "diagnostics", "templates", "template_preview", "template_gallery",
        "page_extraction", "private_template_import", "template_usage_learning",
        "canvas_history", "canvas_multiselect", "canvas_grouping", "canvas_locking",
        "canvas_minimap", "canvas_command_palette", "interaction_system",
        "input_attachments", "ai_settings", "alliance",
        "export_center", "export_pdf", "export_png",
        "recipe_run", "recipe_partial_rerun", "project_memory", "adoption_signal",
        "revision_diff", "revision_history", "revision_labels", "revision_restore",
    ],
    "schemas": {"canvas": 1},
    "offline": {"workspace": True, "generation": False},
}

_OUTPUT_ROOT = Path.home() / "htmlninefox-output"
MAX_REQUEST_BYTES = 36 * 1024 * 1024

_REVISION_ERROR_STATUSES = {
    "revision_forbidden": 403,
    "revision_invalid": 400,
    "revision_not_found": 404,
    "revision_too_large": 413,
    "revision_encoding_invalid": 422,
    "project_state_invalid": 409,
    "revision_conflict": 409,
    "revision_already_current": 409,
    "revision_state_missing": 409,
    "project_busy": 409,
}


def serve(host: str = "127.0.0.1", port: int = 8620, output: str | None = None) -> None:
    global _OUTPUT_ROOT
    if output:
        _OUTPUT_ROOT = Path(output).expanduser().resolve()
    _OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    console = _console()
    server = ThreadingHTTPServer((host, port), _Handler)
    console.print(f"[bold cyan]🦊 Html九尾狐 工作台[/bold cyan] v{__version__}")
    console.print(f"  地址: [cyan underline]http://{host}:{port}[/cyan underline]")
    console.print(f"  产物: [dim]{_OUTPUT_ROOT}[/dim]   Ctrl+C 退出")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        console.print("\n[yellow]已停止[/yellow]")
    finally:
        server.server_close()


def _console():
    try:
        from rich.console import Console
        return Console()
    except ImportError:  # pragma: no cover
        class _P:
            def print(self, msg):
                import re
                print(re.sub(r"\[/?[a-z _]+\]", "", msg))
        return _P()


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        pass

    @property
    def request_id(self) -> str:
        if not hasattr(self, "_request_id"):
            self._request_id = uuid.uuid4().hex[:12]
        return self._request_id

    def _store(self) -> ProjectStore:
        return ProjectStore(_OUTPUT_ROOT)

    def _inputs(self) -> InputStore:
        return InputStore(_OUTPUT_ROOT)

    def _user_gallery(self) -> UserGalleryStore:
        return UserGalleryStore(_OUTPUT_ROOT / ".library" / "gallery")

    def _ai_settings(self) -> AISettingsStore:
        return AISettingsStore(_OUTPUT_ROOT)

    def _memory(self) -> project_memory.ProjectMemoryStore:
        return project_memory.ProjectMemoryStore(_OUTPUT_ROOT)

    def _memory_recommendation(self, prompt: str, body: dict) -> dict:
        return self._studio().recommend_memory(prompt, self._generation_request(body))

    def _activate_ai(self) -> bool:
        return self._studio().activate_ai()


    def _prompt_and_inputs(self, body: dict) -> tuple[str, list[dict]]:
        prompt = (body.get("prompt") or "").strip()
        input_ids = body.get("inputs") if isinstance(body.get("inputs"), list) else []
        items = self._inputs().describe([str(item) for item in input_ids])
        if not prompt and items:
            prompt = "请根据用户上传的附件生成合适的 HTML 作品"
        return prompt + InputStore.prompt_context(items), items

    def _jobs(self):
        return get_job_manager(_OUTPUT_ROOT)

    def _json(self, data: dict, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Request-ID", self.request_id)
        self.end_headers()
        self.wfile.write(body)

    def _error(self, error: StoreError):
        return self._json({
            "ok": False,
            "error": {
                "code": error.code,
                "message": error.message,
                "details": error.details,
            },
            "request_id": self.request_id,
        }, error.status)

    def _file(self, path: Path, mime: str, cache_control: str = "no-store",
              headers: dict[str, str] | None = None):
        if not path.is_file():
            raise StoreError("not_found", "资源不存在", 404)
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache_control)
        self.send_header("X-Request-ID", self.request_id)
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def _html(self, html: str, cache_control: str = "no-store",
              headers: dict[str, str] | None = None):
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache_control)
        self.send_header("X-Request-ID", self.request_id)
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        if length > MAX_REQUEST_BYTES:
            raise StoreError("request_too_large", "请求体不能超过 36MB", 413)
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise StoreError("invalid_json", "请求体不是合法 JSON", 400) from exc
        if not isinstance(payload, dict):
            raise StoreError("invalid_json", "请求体必须是 JSON object", 400)
        return payload

    def _run(self, action: Callable[[], None]):
        try:
            return action()
        except StoreError as error:
            return self._error(error)
        except revisions.RevisionError as error:
            return self._error(StoreError(error.code, str(error), error.status))
        except Exception:  # noqa: BLE001
            traceback.print_exc()
            return self._error(StoreError("internal_error", "服务内部错误", 500,
                                          {"request_id": self.request_id}))

    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        query = parse_qs(parsed.query)
        return self._run(lambda: self._get(path, query))

    def do_POST(self):
        path = unquote(urlparse(self.path).path)
        return self._run(lambda: self._post(path, self._body()))

    def do_PUT(self):
        path = unquote(urlparse(self.path).path)
        return self._run(lambda: self._put(path, self._body()))

    def do_PATCH(self):
        path = unquote(urlparse(self.path).path)
        return self._run(lambda: self._patch(path, self._body()))

    def do_DELETE(self):
        path = unquote(urlparse(self.path).path)
        return self._run(lambda: self._delete(path))

    def _get(self, path: str, query: dict[str, list[str]] | None = None):
        query = query or {}
        if path == "/":
            return self._file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
        if path == "/classic":
            return self._file(STATIC_DIR / "classic.html", "text/html; charset=utf-8")
        if path in STATIC_FILES:
            filename, mime, cache_control = STATIC_FILES[path]
            headers = {"Service-Worker-Allowed": "/"} if path == "/sw.js" else None
            return self._file(STATIC_DIR / filename, mime, cache_control, headers)
        if path == "/api/health":
            return self._json({"ok": True, "version": __version__, "api_version": "v1",
                               "output_root": str(_OUTPUT_ROOT),
                               "distribution": os.getenv("HTMLNINEFOX_DISTRIBUTION", "python")})
        if path == "/api/capabilities":
            return self._json(APP_CAPABILITIES)
        if path == "/api/exports/capabilities":
            return self._json({"ok": True, **exporting.runtime_capabilities()})
        if path == "/api/templates":
            return self._json({"items": pipeline.list_templates()})
        if path == "/api/gallery":
            return self._json({"items": template_gallery.list_gallery(self._user_gallery().root)})
        if path == "/api/gallery-preview":
            item_id = (query.get("id") or [""])[0]
            page_id = (query.get("page") or [None])[0]
            try:
                item = template_gallery.get_gallery_item(item_id, self._user_gallery().root)
                html = template_gallery.render_gallery_preview(
                    item_id, page_id, self._user_gallery().root)
            except ValueError as exc:
                raise StoreError("gallery_preview_invalid", str(exc), 400) from exc
            headers = None
            if item.get("source") == "user":
                headers = {
                    "Content-Security-Policy": (
                        "default-src 'self' data: blob: https: http:; "
                        "script-src 'self' 'unsafe-inline' data: blob: https: http:; "
                        "style-src 'self' 'unsafe-inline' data: blob: https: http:; "
                        "connect-src 'none'; object-src 'none'; form-action 'none'; "
                        "frame-ancestors 'self'; sandbox allow-scripts"
                    ),
                    "X-Content-Type-Options": "nosniff",
                }
            return self._html(html, "private, max-age=300", headers)
        if path.startswith("/api/gallery-assets/"):
            relative = path[len("/api/gallery-assets/"):]
            item_id, separator, asset_path = relative.partition("/")
            if not separator:
                raise StoreError("gallery_asset_invalid", "模板资源路径无效", 400)
            try:
                target = self._user_gallery().resolve_file(item_id, asset_path)
            except UserGalleryError as exc:
                raise StoreError("gallery_asset_invalid", str(exc), 404) from exc
            mime = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            return self._file(target, mime, "private, max-age=300")
        if path == "/api/settings/ai":
            return self._json({"ok": True, "settings": self._ai_settings().public()})
        if path == "/api/memory":
            return self._json({"ok": True, "memory": self._memory().read()})
        if path == "/api/template-preview":
            intent = (query.get("intent") or ["landing"])[0]
            template_id = (query.get("template") or [None])[0]
            try:
                html = pipeline.render_template_preview(intent, template_id)
            except ValueError as exc:
                raise StoreError("template_preview_invalid", str(exc), 400) from exc
            return self._html(html, "private, max-age=300")
        if path == "/api/alliance":
            from ..alliance.router import AllianceRouter
            return self._json({"items": AllianceRouter().list_available_skills()})
        if path == "/api/projects":
            return self._json({"items": self._store().list_projects()})
        if path == "/api/jobs":
            return self._json({"items": self._jobs().list()})
        if path.startswith("/api/jobs/"):
            return self._json(self._jobs().get(path[len("/api/jobs/"):]))
        if path == "/api/workspace":
            return self._json(self._store().load_workspace())
        if path.startswith("/api/projects/") and path.endswith("/revisions"):
            name = path[len("/api/projects/"):-len("/revisions")]
            return self._json(self._store().revision_history(name))
        if path.startswith("/api/projects/") and path.endswith("/diff"):
            name = path[len("/api/projects/"):-len("/diff")]
            def revision_param(key: str) -> int | None:
                raw = (query.get(key) or [None])[0]
                if raw in {None, ""}:
                    return None
                try:
                    value = int(raw)
                except ValueError as exc:
                    raise StoreError("revision_invalid", f"{key} 版本必须是整数", 400) from exc
                if value < 0:
                    raise StoreError("revision_invalid", f"{key} 版本不能小于 0", 400)
                return value
            return self._json(self._store().compare_revisions(
                name, revision_param("from"), revision_param("to")))
        if path.startswith("/api/projects/"):
            return self._json(self._store().get_project(path[len("/api/projects/"):]))
        if path.startswith("/output/"):
            relative = Path(path[len("/output/"):])
            target = (_OUTPUT_ROOT / relative).resolve()
            try:
                target.relative_to(_OUTPUT_ROOT.resolve())
            except ValueError as exc:
                raise StoreError("output_forbidden", "禁止访问工作目录外文件", 403) from exc
            mime = (
                "text/html; charset=utf-8" if target.suffix == ".html" else
                "application/json; charset=utf-8" if target.suffix == ".json" else
                "application/zip" if target.suffix == ".zip" else
                mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            )
            headers = None
            if (query.get("download") or [""])[0] == "1":
                safe_filename = target.name.replace('"', "")
                headers = {"Content-Disposition": f'attachment; filename="{safe_filename}"'}
            return self._file(target, mime, headers=headers)
        raise StoreError("not_found", "接口不存在", 404)

    def _post(self, path: str, body: dict):
        if path == "/api/generate":
            return self._api_generate(body)
        if path == "/api/analyze":
            return self._api_analyze(body)
        if path == "/api/feedback":
            return self._api_feedback(body)
        if path == "/api/inputs":
            try:
                item = self._inputs().save(body)
            except InputError as exc:
                raise StoreError("input_invalid", str(exc), 400) from exc
            return self._json({"ok": True, "input": item}, 201)
        if path == "/api/gallery/import":
            try:
                item = self._user_gallery().import_files(
                    body.get("files") if isinstance(body.get("files"), list) else [],
                    name=str(body.get("name") or ""), entry=str(body.get("entry") or ""),
                    tags=body.get("tags") if isinstance(body.get("tags"), list) else [],
                )
            except UserGalleryError as exc:
                raise StoreError("gallery_import_invalid", str(exc), 400) from exc
            return self._json({"ok": True, "item": item}, 201)
        if path == "/api/settings/ai/test":
            if not self._activate_ai():
                raise StoreError("ai_not_configured", "请先启用并保存 AI 模型配置", 400)
            try:
                result = llm.router.call("只回复 OK", agent="brief_expert", task="settings_test",
                                         use_cache=False, temperature=0, max_tokens=16)
            except Exception as exc:  # noqa: BLE001
                raise StoreError("ai_connection_failed", str(exc), 502) from exc
            return self._json({"ok": True, "model": result.model, "reply": result.text[:120]})
        if path == "/api/jobs":
            return self._api_submit_job(body)
        if path == "/api/exports/analyze":
            project_name = str(body.get("project_name") or "").strip()
            if not project_name:
                raise StoreError("export_project_required", "请选择需要导出的项目", 400)
            return self._json({"ok": True, "manifest": exporting.analyze_project(_OUTPUT_ROOT, project_name)})
        if path == "/api/exports":
            request = self._export_request(body)
            try:
                self._studio().validate_export(request)
            except ExportError as error:
                raise self._export_store_error(error) from error
            job = self._jobs().submit(
                "export", lambda: self._export_payload(self._studio().export(request))
            )
            return self._json({"ok": True, "job": job}, 202)
        if path == "/api/diagnostics":
            bundle = create_diagnostic_bundle(_OUTPUT_ROOT, APP_CAPABILITIES)
            return self._json({"ok": True, "bundle": bundle}, 201)
        if path.startswith("/api/projects/") and path.endswith("/restore-revision"):
            name = path[len("/api/projects/"):-len("/restore-revision")]
            store = self._store()
            project = store.resolve_project(name)
            try:
                result = self._studio().restore(RestoreRequest(
                    project=project,
                    revision=body.get("revision"),
                    expected_revision=body.get("expected_revision"),
                ))
            except RestoreError as error:
                raise self._restore_store_error(error) from error
            return self._json({
                "ok": True,
                "project": store.get_project(result.project.name),
            })
        if path.startswith("/api/projects/") and path.endswith("/recipe-rerun"):
            name = path[len("/api/projects/"):-len("/recipe-rerun")]
            stage = str(body.get("stage") or "generate")
            if stage not in {"generate", "verify"}:
                raise StoreError("recipe_stage_invalid", "局部重跑仅支持 generate 或 verify", 400)
            project = self._store().get_project(name)
            job = self._jobs().submit(
                "recipe-rerun",
                lambda report: pipeline.rerun_project(project["project"], stage, report),
                with_reporter=True,
            )
            return self._json({"ok": True, "job": job}, 202)
        if path.startswith("/api/projects/") and path.endswith("/adopt"):
            name = path[len("/api/projects/"):-len("/adopt")]
            project = self._store().get_project(name)
            try:
                result = self._memory().adopt(project["project"])
            except ValueError as exc:
                raise StoreError("project_memory_adopt_invalid", str(exc), 400) from exc
            return self._json({"ok": True, **result})
        if path.startswith("/api/projects/") and path.endswith("/duplicate"):
            name = path[len("/api/projects/"):-len("/duplicate")]
            project = self._store().duplicate_project(name, body.get("new_name"))
            return self._json({"ok": True, "project": project}, 201)
        raise StoreError("not_found", "接口不存在", 404)

    def _put(self, path: str, body: dict):
        if path == "/api/workspace":
            return self._json({"ok": True, **self._store().save_workspace(body)})
        if path == "/api/memory":
            try:
                memory = self._memory().save(body)
            except ValueError as exc:
                raise StoreError("project_memory_invalid", str(exc), 400) from exc
            return self._json({"ok": True, "memory": memory})
        if path == "/api/settings/ai":
            try:
                settings = self._ai_settings().save(body)
            except ValueError as exc:
                raise StoreError("ai_settings_invalid", str(exc), 400) from exc
            self._activate_ai()
            return self._json({"ok": True, "settings": settings})
        raise StoreError("not_found", "接口不存在", 404)

    def _patch(self, path: str, body: dict):
        if path.startswith("/api/projects/") and path.endswith("/revision-label"):
            name = path[len("/api/projects/"):-len("/revision-label")]
            return self._json(self._store().name_revision(name, body.get("revision"), body.get("label")))
        if path.startswith("/api/projects/"):
            name = path[len("/api/projects/"):]
            project = self._store().rename_project(name, body.get("new_name", ""))
            return self._json({"ok": True, "project": project})
        raise StoreError("not_found", "接口不存在", 404)

    def _delete(self, path: str):
        if path == "/api/memory":
            return self._json({"ok": True, "memory": self._memory().clear()})
        if path.startswith("/api/jobs/"):
            return self._json({"ok": True, "job": self._jobs().cancel(path[len("/api/jobs/"):])})
        if path.startswith("/api/projects/"):
            name = path[len("/api/projects/"):]
            return self._json({"ok": True, **self._store().delete_project(name)})
        if path.startswith("/api/gallery/"):
            item_id = path[len("/api/gallery/"):]
            if not self._user_gallery().delete(item_id):
                raise StoreError("gallery_not_found", "私人模板不存在", 404)
            return self._json({"ok": True, "deleted": item_id})
        raise StoreError("not_found", "接口不存在", 404)

    def _api_generate(self, body: dict):
        return self._json(self._generation_result(body))

    def _api_submit_job(self, body: dict):
        request = self._generation_request(body)
        try:
            self._studio().validate_generation(request)
        except GenerationError as error:
            raise self._generation_store_error(error) from error
        staging_root = _OUTPUT_ROOT / ".jobs-work" / uuid.uuid4().hex
        job = self._jobs().submit(
            "generate",
            lambda report: self._staged_generation(request, staging_root, report),
            with_reporter=True,
        )
        return self._json({"ok": True, "job": job}, 202)

    def _staged_generation(self, request: GenerationRequest, staging_root: Path,
                           progress_callback=None) -> dict:
        staging_root.mkdir(parents=True, exist_ok=True)
        try:
            try:
                generated = self._studio(staging_root).generate(request, progress_callback)
            except GenerationError as error:
                raise self._generation_store_error(error) from error
            result = self._generation_payload(generated)
            source = Path(result["project"])
            target = _OUTPUT_ROOT / source.name
            suffix = 2
            while target.exists():
                target = _OUTPUT_ROOT / f"{source.name}-{suffix}"
                suffix += 1
            source.rename(target)
            result["project"] = str(target)
            result["project_name"] = target.name
            result["preview_url"] = f"/output/{target.name}/output.html"
            return result
        finally:
            shutil.rmtree(staging_root, ignore_errors=True)

    def _studio(self, generation_root: Path | None = None) -> StudioApplication:
        return StudioApplication(StudioDependencies.for_workspace(
            _OUTPUT_ROOT, generation_root=generation_root or _OUTPUT_ROOT,
        ))

    @staticmethod
    def _generation_request(body: dict) -> GenerationRequest:
        input_ids = body.get("inputs") if isinstance(body.get("inputs"), list) else []
        blocks = body.get("blocks") if isinstance(body.get("blocks"), list) else []
        return GenerationRequest(
            prompt=str(body.get("prompt") or ""),
            input_ids=tuple(str(item) for item in input_ids),
            skill=body.get("skill") or None,
            template=body.get("template") or None,
            intent=body.get("intent") or None,
            quiet_llm=bool(body.get("quiet_llm", False)),
            primary=body.get("primary") or None,
            font=body.get("font") or None,
            gallery_id=body.get("gallery_id") or None,
            blocks=tuple(
                GenerationBlock.from_value(item)
                for item in blocks
            ),
            selection_mode=body.get("selection_mode") or "custom",
        )

    @staticmethod
    def _generation_payload(result: GenerationResult) -> dict:
        return {
            "ok": True,
            "project": str(result.work),
            "project_name": result.work.name,
            "preview_url": f"/output/{result.work.name}/output.html",
            "intent": result.intent,
            "preset_id": result.preset_id,
            "preset_name": result.preset_name,
            "route_decision": result.route_decision,
            "skill": result.skill,
            "brief_confidence": result.brief_confidence,
            "verification": result.verification.to_mapping(),
            "recipe_run": result.recipe_run.to_mapping(),
            "memory_applied": result.memory_applied.to_mapping(),
        }

    @staticmethod
    def _generation_store_error(error: GenerationError) -> StoreError:
        status = 400 if error.code == "prompt_required" else 500
        return StoreError(error.code, error.message, status, error.details)

    def _generation_result(self, body: dict, output_root: Path | None = None,
                           progress_callback=None) -> dict:
        try:
            result = self._studio(output_root).generate(
                self._generation_request(body), progress_callback,
            )
        except GenerationError as error:
            raise self._generation_store_error(error) from error
        return self._generation_payload(result)

    def _api_analyze(self, body: dict):
        prompt, input_items = self._prompt_and_inputs(body)
        if not prompt:
            raise StoreError("prompt_required", "prompt 或附件至少需要一个", 400)
        from ..experts import brief_expert
        from ..generators import _tokens
        ai_enabled = self._activate_ai()
        memory_applied = self._memory_recommendation(prompt, body)
        memory_values = memory_applied.get("values", {})
        memory_overrides = memory_applied.get("overrides", {})
        result = brief_expert.BriefExpert().execute({"prompt": prompt, "allow_llm": ai_enabled})
        payload = result.get("brief", {})
        goal = payload.get("goal", {})
        content = payload.get("content", {})
        style = payload.get("style", {})
        preset_id = memory_overrides.get("template") or _tokens.match_preset(
            result, result.get("intent", "landing"))["id"]
        recommended = template_gallery.recommend_gallery(
            result.get("intent", "landing"), preset_id, self._user_gallery().root)
        return self._json({
            "ok": True,
            "intent": result.get("intent", "landing"),
            "intent_confidence": result.get("intent_confidence", 0),
            "confidence": result.get("confidence", 0),
            "brand": memory_values.get("brand") or content.get("brand", ""),
            "audience": memory_values.get("audience") or goal.get("audience", ""),
            "tone": memory_values.get("tone") or style.get("tone", ""),
            "headline": content.get("headline", ""),
            "must_have": (content.get("must_have") or [])[:4],
            "blocks": content.get("blocks") or [],
            "preset_id": preset_id,
            "engine": "rules" if result.get("fallback_used") else "llm",
            "inputs": input_items,
            "recommended_template": recommended,
            "recommended_blocks": [page["block_id"] for page in recommended.get("pages", [])],
            "memory_applied": memory_applied,
        })

    @staticmethod
    def _export_request(body: dict) -> ExportRequest:
        pages_value = body.get("pages")
        if pages_value is None:
            pages = ""
        elif isinstance(pages_value, str):
            pages = pages_value
        elif isinstance(pages_value, list):
            pages = tuple(pages_value)
        else:
            raise StoreError("export_pages_invalid", "pages 必须是数组或页码字符串", 400)
        return ExportRequest(
            project_name=str(body.get("project_name") or ""),
            format=str(body.get("format") or "pdf"),
            scope=str(body.get("scope") or "auto"),
            pages=pages,
            width=body.get("width"),
            height=body.get("height"),
            scale=body.get("scale"),
            paper=str(body.get("paper") or "A4"),
            landscape=bool(body.get("landscape", False)),
        )

    @staticmethod
    def _export_payload(result: ExportResult) -> dict:
        return result.to_mapping()

    @staticmethod
    def _export_store_error(error: ExportError) -> StoreError:
        statuses = {
            "export_project_required": 400,
            "export_format_unsupported": 400,
            "export_scope_invalid": 400,
            "export_paper_invalid": 400,
            "export_pages_invalid": 400,
            "export_width_invalid": 400,
            "export_height_invalid": 400,
            "export_scale_invalid": 400,
            "export_page_out_of_range": 400,
            "export_page_limit": 413,
            "export_analysis_failed": 409,
            "export_source_missing": 409,
            "export_source_invalid": 409,
            "export_runtime_missing": 503,
            "export_browser_unavailable": 503,
            "project_name_invalid": 400,
            "project_not_found": 404,
            "project_state_invalid": 409,
        }
        return StoreError(
            error.code,
            error.message,
            statuses.get(error.code, 500),
            error.details,
        )

    def _api_feedback(self, body: dict):
        try:
            result = self._studio().feedback(self._feedback_request(body))
        except FeedbackError as error:
            raise self._feedback_store_error(error) from error
        return self._json(self._feedback_payload(result))

    @staticmethod
    def _feedback_request(body: dict) -> FeedbackRequest:
        project = str(body.get("project") or "").strip()
        return FeedbackRequest(
            project=Path(project) if project else None,
            note=str(body.get("note") or ""),
            dry_run=False,
            quiet_llm=False,
        )

    @staticmethod
    def _feedback_payload(result: FeedbackResult) -> dict:
        payload = {
            "ok": True,
            "project": str(result.project),
            "suggestion": result.suggestion,
            "applied_rules": list(result.applied_rules),
            "tokens": result.tokens.to_mapping(),
            "model": result.model,
            "preview_url": f"/output/{result.project.name}/output.html",
        }
        if result.revision is not None:
            payload["revision"] = result.revision
        if result.output is not None:
            payload["output"] = str(result.output)
        if result.dry_run:
            payload["dry_run"] = True
        return payload

    @staticmethod
    def _restore_store_error(error: RestoreError) -> StoreError:
        statuses = {"project_required": 400, **_REVISION_ERROR_STATUSES}
        return StoreError(
            error.code,
            error.message,
            statuses.get(error.code, 500),
            error.details,
        )

    @staticmethod
    def _feedback_store_error(error: FeedbackError) -> StoreError:
        statuses = {
            "feedback_fields_required": 400,
            "feedback_not_actionable": 422,
            **_REVISION_ERROR_STATUSES,
        }
        return StoreError(
            error.code,
            error.message,
            statuses.get(error.code, 500),
            error.details,
        )
