"""Local HTTP interface for the Html九尾狐 Web and PWA clients."""

from __future__ import annotations

import json
import mimetypes
import os
import shutil
import traceback
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, unquote, urlparse

from .. import __version__, llm, pipeline, template_gallery
from ..user_gallery import UserGalleryError, UserGalleryStore
from .diagnostics import create_diagnostic_bundle
from .inputs import InputError, InputStore
from .jobs import get_job_manager
from .settings import AISettingsStore
from .storage import ProjectStore, StoreError

STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_FILES = {
    "/manifest.webmanifest": ("manifest.webmanifest", "application/manifest+json; charset=utf-8", "no-cache"),
    "/sw.js": ("sw.js", "application/javascript; charset=utf-8", "no-cache"),
    "/icon.svg": ("icon.svg", "image/svg+xml; charset=utf-8", "public, max-age=86400"),
    "/logo-mark.svg": ("logo-mark.svg", "image/svg+xml; charset=utf-8", "public, max-age=86400"),
    "/logo-horizontal.svg": ("logo-horizontal.svg", "image/svg+xml; charset=utf-8", "public, max-age=86400"),
    "/canvas-engine.js": ("canvas-engine.js", "application/javascript; charset=utf-8", "no-cache"),
    "/canvas-productivity.js": ("canvas-productivity.js", "application/javascript; charset=utf-8", "no-cache"),
    "/workbench-features.js": ("workbench-features.js", "application/javascript; charset=utf-8", "no-cache"),
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
        "canvas_minimap", "canvas_command_palette",
        "input_attachments", "ai_settings", "alliance",
    ],
    "schemas": {"canvas": 1},
    "offline": {"workspace": True, "generation": False},
}

_OUTPUT_ROOT = Path.home() / "htmlninefox-output"
MAX_REQUEST_BYTES = 36 * 1024 * 1024


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

    def _activate_ai(self) -> bool:
        settings = self._ai_settings().activate()
        enabled = bool(settings.get("enabled") and settings.get("model") and settings.get("base_url"))
        if enabled:
            llm.router.configure(llm.runtime_config_from_settings(settings))
        else:
            llm.router.configure(llm.get_default_config())
        return enabled

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
                "text/plain; charset=utf-8"
            )
            return self._file(target, mime)
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
        if path == "/api/diagnostics":
            bundle = create_diagnostic_bundle(_OUTPUT_ROOT, APP_CAPABILITIES)
            return self._json({"ok": True, "bundle": bundle}, 201)
        if path.startswith("/api/projects/") and path.endswith("/duplicate"):
            name = path[len("/api/projects/"):-len("/duplicate")]
            project = self._store().duplicate_project(name, body.get("new_name"))
            return self._json({"ok": True, "project": project}, 201)
        raise StoreError("not_found", "接口不存在", 404)

    def _put(self, path: str, body: dict):
        if path == "/api/workspace":
            return self._json({"ok": True, **self._store().save_workspace(body)})
        if path == "/api/settings/ai":
            try:
                settings = self._ai_settings().save(body)
            except ValueError as exc:
                raise StoreError("ai_settings_invalid", str(exc), 400) from exc
            self._activate_ai()
            return self._json({"ok": True, "settings": settings})
        raise StoreError("not_found", "接口不存在", 404)

    def _patch(self, path: str, body: dict):
        if path.startswith("/api/projects/"):
            name = path[len("/api/projects/"):]
            project = self._store().rename_project(name, body.get("new_name", ""))
            return self._json({"ok": True, "project": project})
        raise StoreError("not_found", "接口不存在", 404)

    def _delete(self, path: str):
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
        prompt = (body.get("prompt") or "").strip()
        if not prompt:
            raise StoreError("prompt_required", "prompt 不能为空", 400)
        staging_root = _OUTPUT_ROOT / ".jobs-work" / uuid.uuid4().hex
        job = self._jobs().submit("generate", lambda: self._staged_generation(dict(body), staging_root))
        return self._json({"ok": True, "job": job}, 202)

    def _staged_generation(self, body: dict, staging_root: Path) -> dict:
        staging_root.mkdir(parents=True, exist_ok=True)
        try:
            result = self._generation_result(body, staging_root)
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

    def _generation_result(self, body: dict, output_root: Path | None = None) -> dict:
        prompt, input_items = self._prompt_and_inputs(body)
        if not prompt:
            raise StoreError("prompt_required", "prompt 或附件至少需要一个", 400)
        ai_enabled = self._activate_ai()
        blocks = body.get("blocks") if isinstance(body.get("blocks"), list) else []
        gallery_id = str(body.get("gallery_id") or "")
        gallery_item = None
        style_overrides = {key: body[key] for key in ("primary", "font") if body.get(key)}
        if gallery_id:
            try:
                gallery_item = self._user_gallery().get(gallery_id)
            except UserGalleryError:
                gallery_item = None
        if gallery_item:
            for key, value in gallery_item.get("style_overrides", {}).items():
                style_overrides.setdefault(key, value)
        result = pipeline.run_expert(
            prompt,
            skill=body.get("skill") or None,
            template=body.get("template") or None,
            output=str(output_root or _OUTPUT_ROOT),
            intent_override=body.get("intent") or None,
            quiet_llm=bool(body.get("quiet_llm", False)) or not ai_enabled,
            style_overrides=style_overrides or None,
            composition={
                "gallery_id": gallery_id or None,
                "gallery_source": gallery_item.get("source") if gallery_item else "builtin",
                "template_design_tokens": gallery_item.get("design_tokens", {}) if gallery_item else {},
                "blocks": blocks,
                "inputs": input_items,
                "selection_mode": body.get("selection_mode") or "custom",
            },
        )
        work = result["work"]
        if gallery_item:
            try:
                self._user_gallery().record_use(gallery_id)
            except (UserGalleryError, OSError, json.JSONDecodeError):
                pass
        return {
            "ok": True,
            "project": str(work),
            "project_name": work.name,
            "preview_url": f"/output/{work.name}/output.html",
            "intent": result["intent"],
            "preset_id": result["preset_id"],
            "preset_name": result["preset_name"],
            "route_decision": result["route_decision"],
            "skill": result["skill"],
            "brief_confidence": result["brief_confidence"],
        }

    def _api_analyze(self, body: dict):
        prompt, input_items = self._prompt_and_inputs(body)
        if not prompt:
            raise StoreError("prompt_required", "prompt 或附件至少需要一个", 400)
        from ..experts import brief_expert
        from ..generators import _tokens
        ai_enabled = self._activate_ai()
        result = brief_expert.BriefExpert().execute({"prompt": prompt, "allow_llm": ai_enabled})
        payload = result.get("brief", {})
        goal = payload.get("goal", {})
        content = payload.get("content", {})
        style = payload.get("style", {})
        preset_id = _tokens.match_preset(result, result.get("intent", "landing"))["id"]
        recommended = template_gallery.recommend_gallery(
            result.get("intent", "landing"), preset_id, self._user_gallery().root)
        return self._json({
            "ok": True,
            "intent": result.get("intent", "landing"),
            "intent_confidence": result.get("intent_confidence", 0),
            "confidence": result.get("confidence", 0),
            "brand": content.get("brand", ""),
            "audience": goal.get("audience", ""),
            "tone": style.get("tone", ""),
            "headline": content.get("headline", ""),
            "must_have": (content.get("must_have") or [])[:4],
            "blocks": content.get("blocks") or [],
            "preset_id": preset_id,
            "engine": "rules" if result.get("fallback_used") else "llm",
            "inputs": input_items,
            "recommended_template": recommended,
            "recommended_blocks": [page["block_id"] for page in recommended.get("pages", [])],
        })

    def _api_feedback(self, body: dict):
        project = (body.get("project") or "").strip()
        note = (body.get("note") or "").strip()
        if not project or not note:
            raise StoreError("feedback_fields_required", "project 与 note 必填", 400)
        result = pipeline.run_feedback(project, note, revise=True, allow_llm=self._activate_ai())
        if not result.get("ok"):
            message = result.get("ask_user") or result.get("error") or "反馈无法执行"
            raise StoreError("feedback_not_actionable", message, 422, result)
        result["preview_url"] = f"/output/{Path(project).name}/output.html"
        return self._json(result)
