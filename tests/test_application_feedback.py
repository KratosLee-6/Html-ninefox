"""Shared application seam for Artifact feedback iteration."""

from pathlib import Path

from htmlninefox import pipeline
from htmlninefox.application import (
    FeedbackError,
    FeedbackRequest,
    StudioApplication,
    StudioDependencies,
)


def test_feedback_creates_revision_through_application_interface(tmp_path: Path) -> None:
    generated = pipeline.run_expert(
        "做一个产品介绍落地页",
        output=str(tmp_path),
        quiet_llm=True,
    )
    project = generated["work"]
    studio = StudioApplication(StudioDependencies.for_workspace(tmp_path))

    result = studio.feedback(FeedbackRequest(
        project=project,
        note="颜色再深一点，标题大一点",
        quiet_llm=True,
    ))

    assert result.project == project.resolve()
    assert result.revision == 1
    assert set(result.applied_rules) == {"color_shift", "font_up"}
    assert result.dry_run is False
    assert result.output == project.resolve() / "output.html"
    assert (project / "revisions" / "rev1.html").is_file()


def test_cli_reports_stable_feedback_failure_for_corrupt_project(tmp_path: Path) -> None:
    from click.testing import CliRunner

    from htmlninefox.cli import main

    project = tmp_path / "broken-project"
    project.mkdir()
    (project / pipeline.STATE_FILE).write_text("{", encoding="utf-8")

    result = CliRunner().invoke(main, [
        "feedback",
        "--project", str(project),
        "--note", "颜色再深一点",
    ])

    assert result.exit_code == 2
    assert "项目或版本状态损坏" in result.output


def test_http_reports_stable_feedback_failure_for_corrupt_project(
    workbench_server,
) -> None:
    import json
    from urllib import error as urllib_error
    from urllib import request as urllib_request

    project = workbench_server.output_root / "broken-project"
    project.mkdir()
    (project / pipeline.STATE_FILE).write_text("{", encoding="utf-8")

    with workbench_server as server:
        request = urllib_request.Request(
            server.base_url + "/api/feedback",
            data=json.dumps({
                "project": str(project),
                "note": "颜色再深一点",
            }).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib_request.urlopen(request, timeout=30)
        except urllib_error.HTTPError as error:
            payload = json.loads(error.read().decode("utf-8"))
            status = error.code
        else:
            raise AssertionError("corrupt Project feedback unexpectedly succeeded")

    assert status == 409
    assert payload["error"]["code"] == "project_state_invalid"
    assert payload["error"]["message"] == "项目或版本状态损坏"


def test_feedback_preserves_revision_error_contract(tmp_path: Path) -> None:
    project = tmp_path / "broken-project-direct"
    project.mkdir()
    (project / pipeline.STATE_FILE).write_text("{", encoding="utf-8")
    studio = StudioApplication(StudioDependencies.for_workspace(tmp_path))

    try:
        studio.feedback(FeedbackRequest(
            project=project,
            note="颜色再深一点",
            quiet_llm=True,
        ))
    except FeedbackError as error:
        captured = error
    else:
        raise AssertionError("corrupt Project feedback unexpectedly succeeded")

    assert captured.code == "project_state_invalid"
    assert captured.message == "项目或版本状态损坏"
    assert captured.details == {}


def test_feedback_non_actionable_error_is_stable(tmp_path: Path) -> None:
    generated = pipeline.run_expert(
        "做一个产品介绍落地页",
        output=str(tmp_path),
        quiet_llm=True,
    )
    studio = StudioApplication(StudioDependencies.for_workspace(tmp_path))

    try:
        studio.feedback(FeedbackRequest(
            project=generated["work"],
            note="不好看",
            quiet_llm=True,
        ))
    except FeedbackError as error:
        captured = error
    else:
        raise AssertionError("vague feedback unexpectedly succeeded")

    assert captured.code == "feedback_not_actionable"
    assert captured.requires_clarification is True
    assert captured.details["ok"] is False
    assert captured.details["ask_user"]


def test_cli_and_http_share_feedback_contract(tmp_path: Path, workbench_server) -> None:
    import json
    from urllib import request as urllib_request

    from click.testing import CliRunner

    from htmlninefox.cli import main

    cli_root = tmp_path / "cli"
    cli_root.mkdir()
    cli_project = pipeline.run_expert(
        "做一个产品介绍落地页",
        output=str(cli_root),
        quiet_llm=True,
    )["work"]
    http_project = pipeline.run_expert(
        "做一个产品介绍落地页",
        output=str(workbench_server.output_root),
        quiet_llm=True,
    )["work"]

    cli = CliRunner().invoke(main, [
        "feedback",
        "--project", str(cli_project),
        "--note", "颜色再深一点，标题大一点",
    ])
    assert cli.exit_code == 0, cli.output

    with workbench_server as server:
        response = urllib_request.urlopen(urllib_request.Request(
            server.base_url + "/api/feedback",
            data=json.dumps({
                "project": str(http_project),
                "note": "颜色再深一点，标题大一点",
            }).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        ), timeout=30)
        http_result = json.loads(response.read().decode("utf-8"))

    cli_state = json.loads((cli_project / pipeline.STATE_FILE).read_text(encoding="utf-8"))
    http_state = json.loads((http_project / pipeline.STATE_FILE).read_text(encoding="utf-8"))
    assert cli_state["revision"] == http_result["revision"] == http_state["revision"] == 1
    assert cli_state["last_feedback"]["rules"] == http_result["applied_rules"]
    assert cli_state["last_feedback"] == http_state["last_feedback"]
    assert cli_state["preset"]["tokens"] == http_state["preset"]["tokens"]
