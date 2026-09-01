"""Create a privacy-conscious diagnostic bundle for support."""

from __future__ import annotations

import json
import os
import platform
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from .. import __version__
from .jobs import get_job_manager
from .storage import ProjectStore, StoreError

_ENV_NAMES = [
    "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY",
    "DEEPSEEK_API_KEY", "MINIMAX_API_KEY",
]


def create_diagnostic_bundle(root: str | Path, capabilities: dict[str, Any]) -> dict[str, Any]:
    output_root = Path(root).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    diagnostic_dir = output_root / ".diagnostics"
    diagnostic_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = diagnostic_dir / f"htmlninefox-diagnostic-{stamp}.zip"

    store = ProjectStore(output_root)
    manager = get_job_manager(output_root)
    try:
        workspace = store.load_workspace()
    except StoreError as error:
        workspace = {"exists": True, "error": {"code": error.code, "message": error.message}}

    projects = store.list_projects(limit=100)
    jobs = manager.list(limit=30)
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "app": {"name": "htmlninefox", "version": __version__, "capabilities": capabilities},
        "runtime": {
            "python": sys.version,
            "platform": platform.platform(),
            "executable": Path(sys.executable).name,
        },
        "configuration": {
            "user_config_exists": (Path.home() / ".htmlninefox" / "config.yaml").is_file(),
            "environment_keys_present": {name: bool(os.environ.get(name)) for name in _ENV_NAMES},
        },
        "storage": {
            "output_root_name": output_root.name,
            "project_count": len(projects),
            "projects": [{key: project.get(key) for key in (
                "name", "intent", "preset_id", "revision", "created_at", "updated_at", "files"
            )} for project in projects],
            "workspace": _workspace_summary(workspace),
        },
        "jobs": [_job_summary(job) for job in jobs],
        "privacy": {
            "included": ["runtime versions", "feature flags", "project metadata", "job status"],
            "excluded": ["API key values", "HTML output", "full prompts", "brief content", "feedback content"],
        },
    }

    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("diagnostic.json", json.dumps(report, ensure_ascii=False, indent=2))
        readme = (
            "Html九尾狐 diagnostic bundle\n"
            "This archive excludes API key values, generated HTML, prompts, briefs, and feedback text.\n"
        )
        archive.writestr("README.txt", readme)

    return {
        "name": target.name,
        "path": str(target),
        "download_url": f"/output/.diagnostics/{target.name}",
        "size": target.stat().st_size,
    }


def _workspace_summary(workspace: dict[str, Any]) -> dict[str, Any]:
    if not workspace.get("exists") or workspace.get("error"):
        return workspace
    state = workspace.get("state", {})
    canvas = state.get("canvas", {})
    return {
        "exists": True,
        "recovered": workspace.get("recovered", False),
        "schema_version": state.get("schema_version"),
        "saved_at": state.get("saved_at"),
        "node_count": len(canvas.get("nodes", [])),
        "edge_count": len(canvas.get("edges", [])),
    }


def _job_summary(job: dict[str, Any]) -> dict[str, Any]:
    error = job.get("error") or {}
    result = job.get("result") or {}
    return {
        "id": job.get("id"),
        "kind": job.get("kind"),
        "status": job.get("status"),
        "stage": job.get("stage"),
        "progress": job.get("progress"),
        "created_at": job.get("created_at"),
        "updated_at": job.get("updated_at"),
        "error_code": error.get("code"),
        "project_name": result.get("project_name"),
    }
