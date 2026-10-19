"""变异验证：Word 审核台与采纳链（v0.8.1）。与 v0.8.0 的 `mutate_docx_gates.py`
（DOCX 导出）不是一回事，别合并——一个守"读进来"，一个守"导出去"。

六条性质都是**安静失败**：页面照渲染、JSON 照样解析、没人抛错。

  D1 目录模式从不触发      → 800 字目录重新变成首节巨型段落
  D2 空标题也进渲染        → 章节列表出现空壳
  D3 表格不再压平          → 表格文字从产物里消失
  D4 空品牌被兜底成占位符  → 客户方案顶着 "Your Product"
  D5 人审文案被规则覆盖    → 审核台改过的标题/摘要白改
  D6 意图白名单失效        → 非法形状被送进渲染器（400 变 500）

  .venv/Scripts/python.exe scripts/mutate_docx_intake_gates.py
  退出码：0 全 CAUGHT · 1 MISSED（真漏洞）· 2 基线红 · 3 STALE（锚点过期）
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mutation_support import finish, stale_report  # noqa: E402  (同目录共用诊断层)

ROOT = Path(__file__).resolve().parents[1]
DOCX = ROOT / "htmlninefox" / "docx_adopt.py"
PIPE = ROOT / "htmlninefox" / "pipeline.py"
SHARED = ROOT / "htmlninefox" / "generators" / "_shared.py"
PROPOSAL = ROOT / "htmlninefox" / "docx_proposal.py"

# 基线只跑这两条真链门禁：解析/提案的纯单测跑得再多也照不出下面这些洞。
GATE = [
    "tests/test_docx_adopt.py",
    "tests/test_docx_intake_api.py",
]

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # pragma: no cover - 老终端
    pass


class MutationFailure(RuntimeError):
    """变异没落到源码上 —— 测试体系问题，不是产品缺陷。"""


def _run(extra: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "pytest", *GATE, *extra,
         "-q", "-p", "no:cacheprovider", "--no-header"],
        cwd=ROOT, capture_output=True, text=True, timeout=900,
        encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"})


def _swap(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise MutationFailure(f"没找到锚点（{label}）——源码改形状了？\n{old}")
    return text.replace(old, new, 1)


def m_toc_mode_never_engages(docx: str, pipe: str, shared: str, proposal: str):
    """D1：目录提示句不再开启「目录模式」，后续 01/02 条目继续拼进正文。"""
    old = ('            toc_mode = True\n'
           '            notes.append("目录行已跳过：Word 的目录是域展开文本，不是正文")')
    new = ('            toc_mode = False\n'
           '            notes.append("目录行已跳过：Word 的目录是域展开文本，不是正文")')
    return _swap(docx, old, new, "目录模式"), pipe, shared, proposal


def m_emit_empty_sections(docx: str, pipe: str, shared: str, proposal: str):
    """D2：有标题就成节，不等正文 —— 空标题重新变成空壳章节。"""
    return _swap(docx, '        if current and current["content"].strip():',
                 '        if current:', "flush 的正文判断"), pipe, shared, proposal


def m_tables_vanish(docx: str, pipe: str, shared: str, proposal: str):
    """D3：表格不再压平，直接丢弃 —— 数据表从产物里静默消失。"""
    return _swap(docx, '            body = _rows_to_text(block.rows)',
                 '            body = ""', "表格压平"), pipe, shared, proposal


def m_placeholder_comes_back(docx: str, pipe: str, shared: str, proposal: str):
    """D4：显式空品牌重新被兜底成 "Your Product"。"""
    return docx, pipe, _swap(
        shared,
        '        return str(content.get("brand") or payload.get("brand") or "")',
        '        return str(content.get("brand") or payload.get("brand") or "Your Product")',
        "brand_of 的空值分支"), proposal


def m_reviewed_copy_is_overwritten(docx: str, pipe: str, shared: str, proposal: str):
    """D5：caller copy 被整段忽略，brief_expert 的规则文案盖回人审文案。"""
    return docx, _swap(pipe, '    if not isinstance(copy, dict):\n        return',
                       '    if True:\n        return', "_apply_caller_copy 的入口"), shared, proposal


def m_intent_whitelist_goes_away(docx: str, pipe: str, shared: str, proposal: str):
    """D6：意图白名单失效，非法形状被送进渲染器（400 变成 500）。"""
    return docx, pipe, shared, _swap(
        proposal, '        if self.intent not in INTENTS:', '        if False:',
        "Proposal.validate 的意图判定")


# 参数顺序与 files 元组一致：(DOCX, PIPE, SHARED, PROPOSAL)。
MUTATIONS = [
    ("D1 目录模式从不触发（目录变回巨型段落）", m_toc_mode_never_engages,
     "test_toc_run_is_skipped_not_rendered_as_a_giant_paragraph"),
    ("D2 空标题也进渲染（空壳章节）", m_emit_empty_sections,
     "test_empty_heading_is_skipped_and_table_text_lands_in_its_section"),
    ("D3 表格不再压平（数据表消失）", m_tables_vanish,
     "test_adopt_renders_the_word_prose_into_a_real_project"),
    ("D4 空品牌兜底成占位符", m_placeholder_comes_back,
     "test_no_brand_means_no_placeholder_on_the_page"),
    ("D5 人审文案被规则覆盖", m_reviewed_copy_is_overwritten,
     "test_adopt_renders_the_word_prose_into_a_real_project"),
    ("D6 意图白名单失效（非法形状进渲染器）", m_intent_whitelist_goes_away,
     "test_adopt_refuses_an_intent_the_desk_cannot_render"),
]


def main() -> int:
    files = (DOCX, PIPE, SHARED, PROPOSAL)
    original = {p: p.read_text(encoding="utf-8") for p in files}
    backup = Path(tempfile.mkdtemp(prefix="fox-docx-intake-backup-"))
    for p in files:
        shutil.copy2(p, backup / p.name)

    def restore() -> None:
        for p in files:
            shutil.copy2(backup / p.name, p)

    rows: list[tuple[str, str]] = []
    print("=" * 74)
    print("Word 审核台与采纳链 · 变异验证（v0.8.1）")
    print("=" * 74)
    try:
        clean = _run([])
        if clean.returncode != 0:
            print("基线就红：\n" + clean.stdout[-2500:])
            return 2
        print("基线：全过\n")

        for name, fn, gate in MUTATIONS:
            try:
                broken = fn(*(original[p] for p in files))
            except MutationFailure as exc:
                print(stale_report(
                    name, "htmlninefox/", str(exc),
                    reason="变异函数的锚点在当前源码里没命中",
                    hint="先确认功能还在，再更新锚点；不要删掉变异换绿。"))
                rows.append((name, "STALE"))
                restore()
                continue

            texts = dict(zip(files, broken))
            if all(texts[p] == original[p] for p in files):
                print(f"HARD FAIL  {name}\n          变异没有改变任何内容")
                rows.append((name, "HARD FAIL"))
                continue

            for path, text in texts.items():
                path.write_text(text, encoding="utf-8", newline="")
            try:
                proc = _run(["-k", gate])
            finally:
                restore()

            if proc.returncode == 0:
                verdict = "MISSED"
            elif "no tests ran" in proc.stdout:
                verdict = "BROKEN SELECTOR"
            else:
                verdict = "CAUGHT"
            rows.append((name, verdict))
            print(f"{verdict:17} {name}")
    finally:
        restore()
        shutil.rmtree(backup, ignore_errors=True)
        for p in files:
            same = p.read_text(encoding="utf-8") == original[p]
            print(f"  还原 {p.name}: {'一致' if same else '不一致！'}")

    print("=" * 74)
    return finish(rows)


if __name__ == "__main__":
    raise SystemExit(main())
