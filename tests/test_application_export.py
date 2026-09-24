"""Shared application seam for exporting an Artifact."""

import json
from pathlib import Path

from htmlninefox import pipeline
from htmlninefox.application import (
    ExportRequest,
    StudioApplication,
    StudioDependencies,
)


def make_export_project(root: Path, name: str = "export-app") -> Path:
    project = root / name
    project.mkdir()
    (project / "output.html").write_text(
        "<!doctype html><html><body><main>导出演示</main></body></html>",
        encoding="utf-8",
    )
    (project / pipeline.STATE_FILE).write_text(json.dumps({
        "prompt": "导出演示",
        "intent": "landing",
        "preset_id": "linear-light",
        "revision": 0,
    }, ensure_ascii=False), encoding="utf-8")
    return project


def test_export_normalizes_request_and_returns_typed_result(tmp_path: Path) -> None:
    project = make_export_project(tmp_path)
    captured = {}

    def fake_export(root, payload):
        captured["root"] = Path(root)
        captured["payload"] = payload
        return {
            "project_name": project.name,
            "export_id": "export-001",
            "format": "png",
            "files": [{
                "name": "page-01.png",
                "bytes": 1234,
                "download_url": "/output/export-app/exports/export-001/page-01.png?download=1",
                "preview_url": "/output/export-app/exports/export-001/page-01.png",
            }],
            "report": {
                "name": "export-report.json",
                "bytes": 456,
                "download_url": "/output/export-app/exports/export-001/export-report.json?download=1",
                "preview_url": "/output/export-app/exports/export-001/export-report.json",
            },
            "warnings": [],
            "compatibility_score": 96,
            "browser": {"name": "chromium", "page_count": 1},
        }

    studio = StudioApplication(StudioDependencies.for_workspace(
        tmp_path,
        run_export=fake_export,
    ))

    result = studio.export(ExportRequest(
        project_name=project.name,
        format="png",
        scope="pages",
        pages="1-2",
        width=960,
        height=540,
        scale=1,
    ))

    assert captured["root"] == tmp_path.resolve()
    assert captured["payload"]["pages"] == [1, 2]
    assert result.project_name == project.name
    assert result.export_id == "export-001"
    assert result.format == "png"
    assert result.compatibility_score == 96
    assert [item.name for item in result.files] == ["page-01.png"]
    assert result.report.name == "export-report.json"
    assert result.browser.to_mapping()["page_count"] == 1


def test_export_invalid_format_has_stable_error(tmp_path: Path) -> None:
    from htmlninefox.application import ExportError

    project = make_export_project(tmp_path, "invalid-format")
    studio = StudioApplication(StudioDependencies.for_workspace(tmp_path))

    try:
        studio.validate_export(ExportRequest(
            project_name=project.name,
            format="pptx",
        ))
    except ExportError as error:
        captured = error
    else:
        raise AssertionError("unsupported export format unexpectedly succeeded")

    assert captured.code == "export_format_unsupported"
    assert captured.message == "当前版本支持 PDF 和 PNG"
    assert captured.details == {"supported": ["pdf", "png"]}


def test_export_wraps_runtime_failure(tmp_path: Path) -> None:
    from htmlninefox.application import ExportError

    project = make_export_project(tmp_path, "runtime-failure")

    def fail_export(*args, **kwargs):
        raise RuntimeError("browser crashed")

    studio = StudioApplication(StudioDependencies.for_workspace(
        tmp_path,
        run_export=fail_export,
    ))

    try:
        studio.export(ExportRequest(project_name=project.name))
    except ExportError as error:
        captured = error
    else:
        raise AssertionError("failed export unexpectedly succeeded")

    assert captured.code == "export_failed"
    assert captured.message == "导出失败"
    assert captured.details == {"cause": "RuntimeError"}


def test_cli_export_uses_application_interface(tmp_path: Path) -> None:
    from click.testing import CliRunner

    from htmlninefox.cli import main

    project = make_export_project(tmp_path, "cli-export")
    result = CliRunner().invoke(main, [
        "export", str(project),
        "--format", "png",
        "--scope", "long",
        "--width", "800",
        "--height", "450",
        "--scale", "1",
    ])

    assert result.exit_code == 0, result.output
    assert "导出完成" in result.output
    exports = [path for path in (project / "exports").iterdir() if path.is_dir()]
    assert len(exports) == 1
    assert (exports[0] / "full-page.png").is_file()
    assert (exports[0] / "export-report.json").is_file()
