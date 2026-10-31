"""MCP 服务门禁（v0.9 · Agent 一等公民）。

两层验证：
1. 工具函数层——对真实 WorkbenchServer 逐个调用（analyze/generate/
   decompose/adopt/feedback/capabilities），断言返回规整数据；
2. 协议层——stdio 子进程走真 MCP 握手：initialize → list_tools →
   call_tool(capabilities)。mcp 是 dev 依赖，不因 ImportError 跳过
   （与 cryptography 纪律一致）。
"""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import htmlninefox.mcp_server as mcp_server  # noqa: E402
from tests.conftest import WorkbenchServer  # noqa: E402
from tests.test_docx_intake_api import build_docx  # noqa: E402


@pytest.fixture()
def mcp_base(tmp_path: Path):
    with WorkbenchServer(tmp_path / "output") as server:
        old = mcp_server.BASE
        mcp_server.BASE = server.base_url
        try:
            yield server
        finally:
            mcp_server.BASE = old


def test_capabilities_reports_version_and_features(mcp_base):
    caps = mcp_server.tool_capabilities()
    assert caps["version"]
    assert len(caps["features"]) >= 30
    assert caps["base"] == mcp_server.BASE


def test_analyze_returns_regular_data(mcp_base):
    result = mcp_server.tool_analyze("做一个 AI 产品发布会页面")
    assert result["intent"] in ("landing", "deck", "poster", "dashboard",
                                "doc", "archdoc")
    assert result["engine"] == "rules", "未配密钥时走规则引擎"
    assert isinstance(result["preset_id"], str) and result["preset_id"]


def test_full_chain_decompose_adopt_feedback(mcp_base):
    source = base64.b64encode(build_docx()).decode()

    proposal = mcp_server.tool_intake_decompose("docx", "方案.docx", source)
    assert proposal["evidence_complete"] is True, "块必须带出处"
    assert proposal["limitations"], "边界清单是交付物"
    assert proposal["proposal"]["intent"] in ("doc", "deck", "landing")

    adopted = mcp_server.tool_intake_adopt(
        "docx", "方案.docx", source,
        proposal={"intent": "deck"})
    assert adopted["verification"]["ok"] is True

    fb = mcp_server.tool_feedback(adopted["project"], "标题大一点")
    assert fb["revision"] >= 1


def test_generate_lands_project(mcp_base):
    result = mcp_server.tool_generate("做一个落地页，主题本地优先", intent="landing")
    assert result["verification"]["ok"] is True
    assert result["preview_url"].startswith("/output/")


def test_errors_surface_as_typed_exceptions(mcp_base):
    import urllib.error

    # HTTP 错误在 _call 内被映射为带 code 的 ApiError——工具层不再漏裸异常
    with pytest.raises(mcp_server.ApiError) as excinfo:
        mcp_server.tool_intake_decompose("docx", "x.docx", base64.b64encode(b"junk").decode())
    assert excinfo.value.code == "docx_unreadable"

    with pytest.raises(mcp_server.ApiError) as excinfo:
        mcp_server.tool_intake_decompose("exe", "x.exe", base64.b64encode(b"junk").decode())
    assert excinfo.value.code == "kind_invalid"


def test_stdio_server_speaks_mcp(mcp_base, tmp_path: Path):
    """协议冒烟：stdio 子进程 initialize → list_tools → call_tool。"""
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    params = StdioServerParameters(
        command=sys.executable,
        args=["-c",
              "import sys; sys.path.insert(0, r'%s'); sys.path.insert(0, r'%s');"
              "import os; os.environ['HTMLNINEFOX_MCP_BASE'] = r'%s';"
              "from htmlninefox.mcp_server import main; main()"
              % (str(ROOT), str(ROOT / "tests"), mcp_server.BASE)],
    )
    import anyio

    async def run():
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                names = {tool.name for tool in tools.tools}
                assert "intake_decompose" in names, names
                assert {"analyze", "generate", "feedback", "capabilities"} <= names
                result = await session.call_tool("capabilities", {})
                text = result.content[0].text
                assert json.loads(text)["version"]

    anyio.run(run)
