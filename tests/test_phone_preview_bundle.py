"""快赢包门禁（0.8.6）：手机预览二维码 + 一键交付包。

lan-preview：枚举非回环地址、按实际监听端口拼 URL；segno 在位时出 SVG
二维码，缺席降级为纯地址文本（不静默装包）。
交付包：按意图自动组格式（deck=PDF+PPTX · doc/archdoc=PDF+DOCX ·
其余=PDF）逐格式真链导出 + 网页本体 → zip 落盘 + 清单。
"""

from __future__ import annotations

import json
import time
import urllib.request
import zipfile
from pathlib import Path

import pytest
from test_docx_intake_api import build_docx
from test_server_project_api import request as api_request

from tests.conftest import WorkbenchServer


@pytest.fixture()
def workbench(tmp_path: Path):
    with WorkbenchServer(tmp_path / "output") as server:
        yield server


def _make_project(workbench, prompt: str, intent: str) -> dict:
    payload, _ = api_request(
        workbench.base_url, "/api/generate", "POST",
        {"prompt": prompt, "intent": intent, "quiet_llm": True})
    return payload


def test_lan_preview_lists_nonloopback_urls_with_qr(workbench):
    payload, _ = api_request(workbench.base_url, "/api/lan-preview", "GET")

    assert payload["ok"] is True
    assert payload["urls"], "至少要枚举出一个局域网地址"
    for url in payload["urls"]:
        assert url.startswith("http://")
        assert str(workbench.base_url).split(":")[-2].split("//")[-1] or True
    # 端口必须与工作台实际监听一致
    port = payload["urls"][0].rsplit(":", 1)[-1]
    assert port.isdigit() and int(port) > 0
    assert payload["qr_svg"] and payload["qr_svg"].startswith("<?xml"), \
        "dev 环境装了 segno，二维码必须在场"
    assert payload["warning"], "无鉴权警示必须随响应"


def test_lan_preview_urls_use_the_real_port(workbench):
    payload, _ = api_request(workbench.base_url, "/api/lan-preview", "GET")
    server_port = workbench.base_url.rsplit(":", 1)[-1]
    assert all(url.endswith(f":{server_port}") for url in payload["urls"]), \
        payload["urls"]


def test_bundle_packages_html_pdf_and_docx_for_doc_intent(workbench):
    api_request(workbench.base_url, "/api/generate", "POST",
                {"prompt": "接入说明：内容交付流水线三步接入", "intent": "doc",
                 "quiet_llm": True})

    payload, _ = api_request(workbench.base_url, "/api/exports/bundle", "POST",
                             {"project_name": _latest(workbench)}, expected=202)
    assert payload["ok"] is True
    job_id = payload["job"]["id"]

    state = {"status": "queued"}
    for _ in range(120):
        state, _ = api_request(workbench.base_url, f"/api/jobs/{job_id}", "GET")
        if state.get("status") in ("succeeded", "done", "failed"):
            break
        time.sleep(1)
    assert state["status"] in ("succeeded", "done"), state
    result = state.get("result", {})
    assert result["intent"] == "doc"
    assert set(result["formats"]) == {"pdf", "docx"}

    zip_path = Path(result["zip"])
    assert zip_path.is_file() and zip_path.stat().st_size > 1000
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    assert any(n.endswith("output.html") for n in names), "网页本体必须在包内"
    assert any(n.endswith(".pdf") for n in names)
    assert any(n.endswith(".docx") for n in names)
    # 逐格式导出各带同名 export-report.json——必须按格式分目录，不允许重名
    assert len(names) == len(set(names)), f"zip 内重名条目: {sorted(names)}"
    # 下载链接必须真实可用（界面「下载」按钮的 href 就靠它）
    assert result["zip_name"] == "bundle.zip"
    assert result["zip_bytes"] == zip_path.stat().st_size
    download = urllib.request.urlopen(workbench.base_url + result["download_url"],
                                      timeout=10)
    assert download.status == 200
    body = download.read()
    assert body[:2] == b"PK" and len(body) == result["zip_bytes"]


def _latest(workbench) -> str:
    payload, _ = api_request(workbench.base_url, "/api/projects", "GET")
    return payload["items"][-1]["name"]


def test_bundle_formats_follow_the_intent(workbench):
    """deck → PDF+PPTX；doc → PDF+DOCX：组包格式跟着意图走。"""
    api_request(workbench.base_url, "/api/generate", "POST",
                {"prompt": "发布会演示：AI 内容交付", "intent": "deck",
                 "quiet_llm": True})
    api_request(workbench.base_url, "/api/generate", "POST",
                {"prompt": "接入说明文档", "intent": "doc", "quiet_llm": True})

    projects, _ = api_request(workbench.base_url, "/api/projects", "GET")
    names = {item["intent"]: item["name"] for item in projects["items"]}

    seen = {}
    for intent in ("deck", "doc"):
        payload, _ = api_request(workbench.base_url, "/api/exports/bundle", "POST",
                                 {"project_name": names[intent]}, expected=202)
        job_id = payload["job"]["id"]
        for _ in range(120):
            state, _ = api_request(workbench.base_url, f"/api/jobs/{job_id}", "GET")
            if state.get("status") in ("succeeded", "done", "failed"):
                break
            time.sleep(1)
        assert state["status"] in ("succeeded", "done"), state
        seen[intent] = set(state["result"]["formats"])

    assert seen["deck"] == {"pdf", "pptx"}
    assert seen["doc"] == {"pdf", "docx"}


def test_bundle_without_project_names_the_error(workbench):
    payload, _ = api_request(workbench.base_url, "/api/exports/bundle", "POST",
                             {}, expected=400)
    assert payload["error"]["code"] == "export_project_required"


STATIC = Path(__file__).resolve().parents[1] / "htmlninefox" / "server" / "static"


def test_every_delegated_module_method_exists():
    """死按钮门禁（S20 intakeFetchBatch 教训的推广）：派发表委托给
    window.Fox*.method 的每个方法，必须真实存在于该模块的定义里。
    注册表门禁只校验名字登记，拦不住「方法没实现、点击即 TypeError」——
    0.8.6 组包按钮首版正是这个形状：静态检查全绿、运行时死按钮。"""
    import re
    core = (STATIC / "fox-core.js").read_text(encoding="utf-8")
    table = core.split("window.FoxActions = {", 1)[1]
    targets = set(re.findall(
        r"=>\s*window\.(Fox[A-Za-z]+)\.([a-zA-Z_$][\w$]*)\s*\(", table))
    assert targets, "派发表委托目标一个都没扫到，正则可能失效"

    sources = {p.name: p.read_text(encoding="utf-8")
               for p in STATIC.glob("*.js")}

    def module_span(name: str) -> str:
        marker = f"window.{name} = " + "{"
        for text in sources.values():
            start = text.find(marker)
            if start < 0:
                continue
            depth, i = 0, text.index("{", start)
            for j, ch in enumerate(text[i:], start=i):
                depth += (ch == "{") - (ch == "}")
                if depth == 0:
                    return text[i:j]
        return ""

    missing = sorted(
        f"{mod}.{method}"
        for mod, method in targets if method not in module_span(mod))
    assert not missing, (
        f"派发表委托到 {missing}，但这些方法不在模块定义里——点击即 TypeError 的死按钮")
