"""tests/test_integration.py · 端到端集成测试（Day 13-14）

覆盖范围：
  1. expert CLI 端到端（5 智能体联盟 + Jinja2 fallback → 真实 HTML）
  2. BriefLib / TemplateLib / FeedbackLib 三重沉淀 CRUD
  3. FeedbackLib.get_tokens_extracted 深 merge 语义
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJ_ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable


def test_expert_full_pipeline(tmp_path):
    """完整 expert 流程：CLI → 5 智能体联盟 + Jinja2 fallback → 6 文件产物"""
    out = tmp_path / "expert-test"
    result = subprocess.run(
        [PYTHON, "-m", "htmlninefox", "expert", "做一个 SaaS 落地页", "-o", str(out)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
        env={**os.environ, "PYTHONPATH": str(PROJ_ROOT)},
    )
    assert result.returncode == 0, f"expert 失败: stderr={result.stderr[-500:]}"

    # 验证产物目录 + 6 文件
    project_dirs = [d for d in out.iterdir() if d.is_dir()]
    assert len(project_dirs) >= 1, f"无产物目录: {list(out.iterdir())}"
    project = project_dirs[0]

    for fname in ["brief.json", "brief.md", "style.md", "output.html", "assets.json"]:
        assert (project / fname).exists(), f"missing: {fname}"

    # 真实 HTML（不是占位 fallback）
    html_size = (project / "output.html").stat().st_size
    assert html_size > 5000, f"output.html 太小 ({html_size}B)，疑似占位"


def test_brief_lib_crud():
    """BriefLib 真实持久化文件可列出"""
    from htmlninefox.libraries.brief_lib import BriefLib

    lib = BriefLib()
    briefs = lib.list()
    # 至少 1 条（KX 之前跑过 142 次 CLI 必有沉淀）
    assert len(briefs) >= 1, f"BriefLib 没找到任何 brief（base_dir={lib.base_dir}）"


def test_feedback_token_extraction(tmp_path):
    """FeedbackLib.get_tokens_extracted 深 merge（最新值覆盖 + 同 key 不丢）"""
    from htmlninefox.libraries.feedback_lib import FeedbackLib

    lib = FeedbackLib(base_dir=tmp_path)
    proj = "test-token-merge"

    # 第 1 条：colors.primary = #5B5FCF
    lib.append(proj, {
        "target_element": "button.primary", "suggestion": "v1",
        "confidence": 0.8, "actionable": True,
        "tokens_extracted": {"colors": {"primary": "#5B5FCF"}},
    })
    # 第 2 条：radius = 12（独立 category）
    lib.append(proj, {
        "target_element": "global.radius", "suggestion": "v2",
        "confidence": 0.9, "actionable": True,
        "tokens_extracted": {"radius": 12},
    })
    # 第 3 条：colors.primary 覆盖为 #7C3AED（最新值）
    lib.append(proj, {
        "target_element": "button.primary", "suggestion": "v3",
        "confidence": 0.7, "actionable": True,
        "tokens_extracted": {"colors": {"primary": "#7C3AED"}},
    })

    tokens = lib.get_tokens_extracted(proj)
    assert tokens["colors"]["primary"] == "#7C3AED", "最新值未覆盖"
    assert tokens["radius"] == 12, "独立 category 丢失"
    assert len(lib.list(proj)) == 3, "list(project_id) 数量不对"


def test_template_lib_crud(tmp_path):
    """TemplateLib.add → list → get → search_by_tag 完整链路"""
    from htmlninefox.libraries.template_lib import TemplateLib

    lib = TemplateLib(base_dir=tmp_path)

    test_html = tmp_path / "test.html"
    test_html.write_text(
        "<style>body{color:#5B5FCF;background:#0A0A0F;border-radius:12px}</style>",
        encoding="utf-8",
    )

    result = lib.add(str(test_html), name="integration-test", tags=["demo", "purple"])
    tpl_id = result["id"]
    assert tpl_id, "add 返回的 id 为空"

    items = lib.list()
    assert any(t["id"] == tpl_id for t in items), "list 找不到刚 add 的模板"

    found = lib.get(tpl_id)
    assert found is not None, "get 返回 None"
    assert found["name"] == "integration-test", "name 不一致"

    hits = lib.search_by_tag("purple")
    assert any(h["id"] == tpl_id for h in hits), "search_by_tag 没命中"
