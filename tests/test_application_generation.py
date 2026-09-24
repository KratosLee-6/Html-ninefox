"""Shared application seam for HTML generation."""

import json
from pathlib import Path

import pytest

from htmlninefox import pipeline
from htmlninefox.application import (
    GenerationError,
    GenerationRequest,
    StudioApplication,
    StudioDependencies,
)


def test_generation_requires_prompt_or_attachment(tmp_path: Path) -> None:
    studio = StudioApplication(StudioDependencies.for_workspace(tmp_path))

    with pytest.raises(GenerationError) as captured:
        studio.generate(GenerationRequest(prompt="", quiet_llm=True))

    assert captured.value.code == "prompt_required"
    assert captured.value.message == "prompt 或附件至少需要一个"
    assert captured.value.details == {}


def test_generation_returns_project_revision_and_recipe_run(tmp_path: Path) -> None:
    studio = StudioApplication(StudioDependencies.for_workspace(tmp_path))

    result = studio.generate(GenerationRequest(
        prompt="为独立咖啡店做一张秋季新品海报",
        intent="poster",
        quiet_llm=True,
    ))

    assert result.work.parent == tmp_path.resolve()
    assert result.intent == "poster"
    assert result.preset_id
    assert result.route_decision
    assert result.verification.ok is True
    assert set(result.recipe_run.stage_ids) == {
        "analyze", "compose", "generate", "verify", "deliver",
    }
    assert result.recipe_run.to_mapping()["status"] == "succeeded"
    assert (result.work / "output.html").is_file()
    assert (result.work / "revisions" / "rev0.html").is_file()
    state = json.loads((result.work / pipeline.STATE_FILE).read_text(encoding="utf-8"))
    assert state["revision"] == 0
    assert state["intent"] == result.intent


def test_cli_and_http_share_generation_contract(tmp_path: Path, workbench_server) -> None:
    from click.testing import CliRunner
    from urllib import request as urllib_request

    from htmlninefox.cli import main
    from htmlninefox.project_memory import ProjectMemoryStore

    cli_root = tmp_path / "cli"
    cli_root.mkdir()
    memory_payload = {
        "enabled": True,
        "profile": {
            "brand": "九尾咖啡研究所",
            "preferred_primary": "#173C8F",
        },
    }
    ProjectMemoryStore(cli_root).save(memory_payload)
    ProjectMemoryStore(workbench_server.output_root).save(memory_payload)

    prompt = "制作一张秋季新品海报"
    cli = CliRunner().invoke(main, [
        "expert", prompt, "--type", "poster", "--quiet-llm", "-o", str(cli_root),
    ])
    assert cli.exit_code == 0, cli.output
    cli_project = sorted(cli_root.glob("html9n-*"))[-1]
    cli_state = json.loads((cli_project / pipeline.STATE_FILE).read_text(encoding="utf-8"))

    with workbench_server as server:
        payload = json.dumps({
            "prompt": prompt,
            "intent": "poster",
            "quiet_llm": True,
        }).encode("utf-8")
        response = urllib_request.urlopen(urllib_request.Request(
            server.base_url + "/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        ), timeout=30)
        http_result = json.loads(response.read().decode("utf-8"))
    http_state = json.loads(
        (Path(http_result["project"]) / pipeline.STATE_FILE).read_text(encoding="utf-8")
    )

    for key in ("intent", "preset_id"):
        assert cli_state[key] == http_state[key]
    assert cli_state["route"]["decision"] == http_state["route"]["decision"]
    assert cli_state["verification"]["ok"] == http_state["verification"]["ok"] is True
    assert cli_state["memory_applied"] == http_state["memory_applied"]
    assert cli_state["memory_applied"]["applied"] == [
        {"field": "brand", "value": "九尾咖啡研究所"},
        {"field": "primary", "value": "#173C8F"},
    ]
    assert [stage["id"] for stage in cli_state["recipe_run"]["stages"]] == [
        stage["id"] for stage in http_state["recipe_run"]["stages"]
    ]


def test_generation_wraps_runtime_failure_in_stable_error(tmp_path: Path) -> None:
    def fail_generation(*args, **kwargs):
        raise RuntimeError("provider exploded")

    studio = StudioApplication(StudioDependencies.for_workspace(
        tmp_path,
        run_generation=fail_generation,
    ))

    with pytest.raises(GenerationError) as captured:
        studio.generate(GenerationRequest(prompt="生成一张产品海报", quiet_llm=True))

    assert captured.value.code == "generation_failed"
    assert captured.value.message == "生成失败"
    assert captured.value.details == {"cause": "RuntimeError"}


def test_cli_workspace_can_activate_environment_ai(tmp_path: Path, monkeypatch) -> None:
    from htmlninefox import llm

    for name in ("MINIMAX_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-key")
    studio = StudioApplication(StudioDependencies.for_workspace(
        tmp_path,
        allow_environment_ai=True,
    ))
    try:
        assert studio.activate_ai() is True
        assert llm.router.config["_runtime_settings"]["model"] == "gpt-4o"
    finally:
        llm.router.configure(llm.get_default_config())


def test_async_job_accepts_attachment_without_prompt(tmp_path: Path, workbench_server) -> None:
    import base64
    import time
    from urllib import request as urllib_request

    from htmlninefox.server.inputs import InputStore

    attachment = InputStore(workbench_server.output_root).save({
        "name": "brief.md",
        "mime": "text/markdown",
        "data_base64": base64.b64encode("秋季新品：桂花拿铁".encode("utf-8")).decode("ascii"),
    })

    def post(url: str, payload: dict) -> dict:
        response = urllib_request.urlopen(urllib_request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        ), timeout=30)
        return json.loads(response.read().decode("utf-8"))

    with workbench_server as server:
        submitted = post(server.base_url + "/api/jobs", {
            "prompt": "",
            "inputs": [attachment["id"]],
            "intent": "poster",
            "quiet_llm": True,
        })
        job_id = submitted["job"]["id"]
        deadline = time.time() + 30
        while time.time() < deadline:
            response = urllib_request.urlopen(
                server.base_url + "/api/jobs/" + job_id,
                timeout=30,
            )
            job = json.loads(response.read().decode("utf-8"))
            if job["status"] not in {"queued", "running"}:
                break
            time.sleep(0.05)

    assert job["status"] == "succeeded", job
    assert Path(job["result"]["project"]).is_dir()
    assert job["result"]["intent"] == "poster"


def test_dsh_cli_flags_map_to_generation_request(tmp_path: Path) -> None:
    from click.testing import CliRunner

    from htmlninefox.cli import main

    result = CliRunner().invoke(main, [
        "expert",
        "为九尾咖啡制作秋季新品海报",
        "--type", "poster",
        "--skill", "huashu-design",
        "--template", "linear-light",
        "--quiet-llm",
        "--output", str(tmp_path),
    ])

    assert result.exit_code == 0, result.output
    project = next(tmp_path.glob("html9n-*"))
    state = json.loads((project / pipeline.STATE_FILE).read_text(encoding="utf-8"))
    assert state["intent"] == "poster"
    assert state["preset_id"] == "linear-light"
    assert state["route"]["skill"] == "huashu-design"
    analyze = next(stage for stage in state["recipe_run"]["stages"] if stage["id"] == "analyze")
    assert analyze["input_summary"]["llm_enabled"] is False
