"""素材脱敏门禁（2026-10-20 KX 明确要求）。

规则：仓库里不得出现真实客户名、真实客户文件路径、指向私人工作区的绝对路径。
真实文档只在本机 `E:\\工作\\...` 下流转，进仓库的一律是
`tests/fixtures/demo_docx.py` 生成的虚构方案（星野智造／栖木云）。

黑名单放在仓库外的 `~/.htmlninefox/private-terms.txt`（一行一个词），
这样门禁文件本身不会把敏感词写进仓库。
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TERMS_FILE = Path.home() / ".htmlninefox" / "private-terms.txt"

SCANNED_SUFFIXES = {".md", ".py", ".txt", ".json", ".html", ".css", ".js", ".yml", ".yaml"}
# 二进制与发布资产不在这里扫（图片需要 OCR，另有人工清单）。
SKIP_DIRS = {".git", ".venv", "output", "dist", "build", "node_modules", "assets"}


def _tracked_files() -> list[Path]:
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True)
    if out.returncode != 0:
        return []
    files = []
    for line in out.stdout.splitlines():
        path = ROOT / line.strip()
        if path.suffix.lower() in SCANNED_SUFFIXES and not any(
                part in SKIP_DIRS for part in path.parts):
            files.append(path)
    return files


def _private_terms() -> list[str]:
    if not TERMS_FILE.is_file():
        return []
    return [line.strip() for line in TERMS_FILE.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")]


def test_no_private_terms_in_tracked_text():
    terms = _private_terms()
    if not terms:
        pytest.skip(f"没有黑名单文件：{TERMS_FILE}（本机才需要）")

    hits = []
    for path in _tracked_files():
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for term in terms:
            if term in text:
                hits.append(f"{path.relative_to(ROOT)}: {term}")

    assert not hits, "仓库里出现未脱敏素材：\n" + "\n".join(hits)


def test_no_absolute_private_paths():
    """脚本与测试只许相对仓库定位；绝对路径会把本地目录结构带进公开仓库。"""
    pattern = re.compile(r"[A-Za-z]:[\\/](?:工作|Users)[\\/]")
    hits = []
    for path in _tracked_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        if pattern.search(text):
            hits.append(str(path.relative_to(ROOT)))

    assert not hits, "这些文件里有绝对路径，改成 Path(__file__).parents 相对定位：\n" + "\n".join(hits)


def test_screenshots_come_from_the_demo_document():
    """截图脚本必须用虚构示例文档，不能指向任何真实文件或私人目录。"""
    for script in ("capture_v081_desk.py", "capture_v081_desk_mobile.py",
                   "capture_v082_word_flow.py"):
        text = (ROOT / "scripts" / script).read_text(encoding="utf-8")
        assert "build_plan_docx" in text, f"{script} 必须用脱敏示例文档"
        assert "GEO/" not in text, f"{script} 仍指向真实客户目录"
        assert not re.search(r"[A-Za-z]:[\\/](?:工作|Users)[\\/]", text), \
            f"{script} 里有私人绝对路径"
