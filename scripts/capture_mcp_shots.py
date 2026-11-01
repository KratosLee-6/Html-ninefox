"""MCP 会话可视化取证：真实 stdio 会话 + 真实产物页截图。

  evidence-mcp-tools.json   真实 list_tools 协议回显（8 工具全录）
  evidence-mcp-call.json    真实 generate 调用回显（项目名/verification）
  evidence-mcp-artifact.png MCP 生成产物的浏览器实拍
  evidence-classic.png      classic 历史页实拍（MCP 生成的项目在列）
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import anyio  # noqa: E402
from mcp import ClientSession  # noqa: E402
from mcp.client.stdio import StdioServerParameters, stdio_client  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

from tests.conftest import WorkbenchServer  # noqa: E402

SHOTS = Path(__file__).resolve().parent / "assets"
PROMPT = "做一个城市交通数据看板，深色，展示早高峰流量、地铁满载率和事故热线"


def main() -> int:
    SHOTS.mkdir(parents=True, exist_ok=True)
    with WorkbenchServer(Path(tempfile.mkdtemp())) as server:
        params = StdioServerParameters(
            command=sys.executable,
            args=["-c",
                  f"import sys; sys.path.insert(0, r'{ROOT}'); "
                  f"import os; os.environ['HTMLNINEFOX_MCP_BASE'] = r'{server.base_url}'; "
                  f"from htmlninefox.mcp_server import main; main()"])

        async def mcp_run():
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    tools_dump = [{"name": t.name, "description": t.description}
                                  for t in tools.tools]
                    caps = await session.call_tool("capabilities", {})
                    gen = await session.call_tool("generate",
                                                  {"prompt": PROMPT, "intent": "dashboard"})
                    out = json.loads(gen.content[0].text)
                    fb = await session.call_tool(
                        "feedback", {"project": out["project"], "note": "标题大一点"})
                    return tools_dump, json.loads(caps.content[0].text), out, \
                        json.loads(fb.content[0].text)

        tools_dump, caps, gen, fb = anyio.run(mcp_run)
        (SHOTS / "evidence-mcp-tools.json").write_text(
            json.dumps(tools_dump, ensure_ascii=False, indent=1), encoding="utf-8")
        (SHOTS / "evidence-mcp-call.json").write_text(
            json.dumps({"capabilities": caps, "generate": {
                "project_name": gen["project_name"], "intent": gen["intent"],
                "verification": gen["verification"]}, "feedback_rev": fb["revision"]},
                       ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"MCP 会话: {len(tools_dump)} 工具 · 生成 {gen['project_name']} · rev{fb['revision']}")

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.goto(server.base_url + gen["preview_url"])
            page.wait_for_timeout(1800)
            page.screenshot(path=SHOTS / "evidence-mcp-artifact.png")
            print("shot: evidence-mcp-artifact.png")

            page.goto(server.base_url + "/classic")
            page.wait_for_function("typeof generate === 'function'")
            page.wait_for_selector("#projects .hist-item, #projects .tagline",
                                   timeout=15000)
            page.wait_for_timeout(500)
            page.locator("#projects").screenshot(path=SHOTS / "evidence-mcp-classic.png")
            print("shot: evidence-mcp-classic.png")
            browser.close()

    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
