"""MCP 服务（v0.9 · Agent 一等公民）：把工作台能力暴露为 MCP 工具。

设计决策（DESIGN-REVERSE-INTAKE §1 第 5 条）：MCP 内部**复用既有 HTTP API**，
不另起服务——先 `htmlninefox serve`，再让 agent 连接本 stdio 服务；
工作台未启动时工具返回带提示的错误，不静默失败。

安装：`pip install 'htmlninefox[mcp]'`（mcp 2.x）。
运行：`python -m htmlninefox.mcp_server`（stdio），或在各 agent 的 MCP 配置里
注册同一命令。基础地址可用环境变量 `HTMLNINEFOX_MCP_BASE` 覆盖。

工具一览：
  capabilities        健康与能力声明（先探这个）
  analyze             一句话 → 意图 / 置信度 / 推荐预设
  generate            一句话（或 blocks）→ 产物落盘
  intake_decompose    DOCX/PPTX/PDF 进料 → 可编辑提案（规划同名的核心工具）
  intake_adopt        改完的提案 → 采纳生成（可带 slot_images 挂真实图片）
  feedback            口语反馈 → 改写 → 新版本
  list_projects       项目清单
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

BASE = os.environ.get("HTMLNINEFOX_MCP_BASE", "http://127.0.0.1:8620").rstrip("/")
INTAKE_KINDS = ("docx", "pptx", "pdf")


class ApiError(RuntimeError):
    """工作台返回的错误（带 code），原样转给 agent。"""

    def __init__(self, status: int, code: str, message: str):
        super().__init__(f"[{code}] {message} (HTTP {status})")
        self.status, self.code = status, code


def _call(path: str, body: dict | None = None, timeout: int = 180) -> Any:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        BASE + path, data=data,
        headers={"Content-Type": "application/json"} if data else {},
        method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode("utf-8", "replace"))
            err = detail.get("error", {})
            raise ApiError(exc.code, err.get("code", "unknown"),
                           err.get("message", "")) from exc
        except json.JSONDecodeError:
            raise ApiError(exc.code, "unknown", exc.reason) from exc


def _wait_job(job_id: str, timeout_s: int = 180) -> dict:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        state = _call(f"/api/jobs/{job_id}")
        if state.get("status") in ("done", "failed"):
            return state
        time.sleep(1)
    return {"status": "timeout", "job_id": job_id}


# ── 工具实现（纯逻辑，便于脱离 MCP 协议单测）──

def tool_capabilities() -> dict:
    health = _call("/api/health")
    caps = _call("/api/capabilities")
    return {"version": health.get("version"),
            "features": caps.get("features", []),
            "base": BASE}


def tool_analyze(prompt: str) -> dict:
    return _call("/api/analyze", {"prompt": prompt})


def tool_generate(prompt: str, intent: str | None = None,
                  template: str | None = None) -> dict:
    body: dict[str, Any] = {"prompt": prompt, "quiet_llm": True}
    if intent:
        body["intent"] = intent
    if template:
        body["template"] = template
    return _call("/api/generate", body)


def tool_intake_decompose(kind: str, name: str, source_base64: str) -> dict:
    """规划同名的核心工具：文档 → 可编辑提案（带出处与边界）。"""
    if kind not in INTAKE_KINDS:
        raise ApiError(400, "kind_invalid", f"kind 只支持 {'/'.join(INTAKE_KINDS)}")
    return _call(f"/api/intake/{kind}",
                 {"name": name, f"{kind}_base64": source_base64})


def tool_intake_adopt(kind: str, name: str, source_base64: str,
                      proposal: dict | None = None,
                      slot_images: dict | None = None) -> dict:
    if kind not in INTAKE_KINDS:
        raise ApiError(400, "kind_invalid", f"kind 只支持 {'/'.join(INTAKE_KINDS)}")
    body: dict[str, Any] = {"name": name, f"{kind}_base64": source_base64}
    if proposal:
        body["proposal"] = proposal
    if slot_images:
        body["slot_images"] = slot_images
    return _call(f"/api/intake/{kind}/adopt", body)


def tool_feedback(project: str, note: str) -> dict:
    return _call("/api/feedback", {"project": project, "note": note})


def tool_list_projects() -> dict:
    return _call("/api/projects")


def tool_export(project_name: str, fmt: str = "pdf") -> dict:
    job = _call("/api/exports", {"project_name": project_name, "format": fmt},
                timeout=60)
    state = _wait_job(job["job"]["id"])
    return {"job": state, "exported": state.get("result", {})}


# ── MCP 协议层（[mcp] extra；mcp 2.x MCPServer）──

def build_server():
    try:
        from mcp.server.mcpserver import MCPServer
    except ImportError as exc:  # pragma: no cover - 可选 extra 守卫
        raise RuntimeError(
            "MCP 服务需要 mcp 包：pip install 'htmlninefox[mcp]'") from exc

    server = MCPServer(name="htmlninefox",
                       instructions=(
                           "Html九尾狐 · 本地优先的 HTML 生成与文档反拆服务。"
                           "先用 capabilities 探测，analyze/generate 出页，"
                           "intake_decompose 拆文档（返回带出处的块与边界清单），"
                           "intake_adopt 采纳生成，feedback 口语改稿。"
                           f"工作台地址：{BASE}（未启动时请先运行 htmlninefox serve）。"))

    @server.tool()
    def capabilities() -> dict:
        """工作台健康与能力声明（35 项 features）。先调这个。"""
        return tool_capabilities()

    @server.tool()
    def analyze(prompt: str) -> dict:
        """一句话 → 意图 / 置信度 / 推荐预设与模板（规则引擎，离线可用）。"""
        return tool_analyze(prompt)

    @server.tool()
    def generate(prompt: str, intent: str | None = None,
                 template: str | None = None) -> dict:
        """生成单文件 HTML 产物并落盘。intent/template 可选；返回 preview_url。"""
        return tool_generate(prompt, intent, template)

    @server.tool()
    def intake_decompose(kind: str, name: str, source_base64: str) -> dict:
        """文档反拆：DOCX/PPTX/PDF → 可编辑提案。返回 image_plan、limitations
        （如实说明拿不到什么）与带出处的块；改完用 intake_adopt 采纳。"""
        return tool_intake_decompose(kind, name, source_base64)

    @server.tool()
    def intake_adopt(kind: str, name: str, source_base64: str,
                     proposal: dict | None = None,
                     slot_images: dict | None = None) -> dict:
        """采纳提案并生成产物。proposal 是 intake_decompose 返回的可编辑提案；
        slot_images = {图片位名: base64} 可挂真实图片。"""
        return tool_intake_adopt(kind, name, source_base64, proposal, slot_images)

    @server.tool()
    def feedback(project: str, note: str) -> dict:
        """口语反馈改稿：「标题大一点」。返回新版本号，历史可回滚。"""
        return tool_feedback(project, note)

    @server.tool()
    def list_projects() -> list:
        """列出全部项目（名称/意图/版本/预览地址）。"""
        return tool_list_projects().get("items", [])

    @server.tool()
    def export(project_name: str, fmt: str = "pdf") -> dict:
        """导出交付物：pdf / png / pptx / docx。异步执行并等待完成。"""
        return tool_export(project_name, fmt)

    return server


def main() -> None:
    server = build_server()
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
