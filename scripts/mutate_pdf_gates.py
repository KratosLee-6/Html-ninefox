"""变异验证：PDF 反向拆解链（v0.8.4）。与 pptx-intake 那套同构——一个守
PPT 读进来，这个守 PDF 读进来。四条性质都是**安静失败**。

  P1 扫描页不再上报    → 空页静默跳过，结果假装「全拿到了」
  P2 locator 丢了页号  → 只剩 chars 区间，「第几页」没了，人审无法回指
  P3 字号推断守卫被拆  → 正文行全部冒充标题，层级静默走错
  P4 魔数校验被拆      → 非 PDF 文件溜进 pdfminer 炸出裸异常

  .venv/Scripts/python.exe scripts/mutate_pdf_gates.py
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
PDF = ROOT / "htmlninefox" / "pdf_import.py"

GATE = [
    "tests/test_pdf_import.py",
    "tests/test_pdf_intake_api.py",
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


def m_scanned_pages_stop_being_reported(pdf: str):
    """P1：无文本层的页不再写 limitations——静默跳过。"""
    old = ('            limitations.append(f"第 {number} 页无文本层，'
           '未提取文字（可能为扫描件或纯图页）")')
    return _swap(pdf, old, "            pass  # MUTATED: 扫描页静默跳过", "扫描页上报")


def m_locator_loses_the_page(pdf: str):
    """P2：evidence 只剩 chars，丢掉 page——回指退化成「页内某段」。"""
    return _swap(pdf, '            evidence = {"page": number, "chars": [offset, offset + span]}',
                 '            evidence = {"chars": [offset, offset + span]}', "evidence 的 page 键")


def m_font_inference_guard_goes_away(pdf: str):
    """P3：标题判定恒真——正文行全部冒充标题。"""
    old = """            is_heading = (
                median_size > 0 and size >= median_size * 1.15
                and len(text) <= 120
            )"""
    return _swap(pdf, old, "            is_heading = True  # MUTATED", "字号推断守卫")


def m_magic_check_goes_away(pdf: str):
    """P4：%PDF- 魔数校验拆除——任意字节溜进 pdfminer。"""
    return _swap(pdf, '    if not raw.startswith(PDF_MAGIC):',
                 '    if False:', "魔数校验")


MUTATIONS = [
    ("P1 扫描页不再上报（静默跳过）", m_scanned_pages_stop_being_reported,
     "test_scanned_page_is_reported_not_silent"),
    ("P2 locator 丢了页号（回指退化）", m_locator_loses_the_page,
     "test_every_block_carries_page_and_char_span"),
    ("P3 字号推断守卫被拆（正文冒充标题）", m_font_inference_guard_goes_away,
     "test_outline_splits_headings_from_body_by_font_size"),
    ("P4 魔数校验被拆（任意字节进解析器）", m_magic_check_goes_away,
     "test_not_a_pdf_says_so"),
]


def main() -> int:
    original = PDF.read_text(encoding="utf-8")
    backup = Path(tempfile.mkdtemp(prefix="fox-pdf-intake-backup-"))
    shutil.copy2(PDF, backup / PDF.name)

    def restore() -> None:
        shutil.copy2(backup / PDF.name, PDF)

    rows: list[tuple[str, str]] = []
    print("=" * 74)
    print("PDF 反向拆解链 · 变异验证（v0.8.4）")
    print("=" * 74)
    try:
        clean = _run([])
        if clean.returncode != 0:
            print("基线就红：\n" + clean.stdout[-2500:])
            return 2
        print("基线：全过\n")

        for name, fn, gate in MUTATIONS:
            try:
                broken = fn(original)
            except MutationFailure as exc:
                print(stale_report(
                    name, "htmlninefox/", str(exc),
                    reason="变异函数的锚点在当前源码里没命中",
                    hint="先确认功能还在，再更新锚点；不要删掉变异换绿。"))
                rows.append((name, "STALE"))
                restore()
                continue

            if broken == original:
                print(f"HARD FAIL  {name}\n          变异没有改变任何内容")
                rows.append((name, "HARD FAIL"))
                continue

            PDF.write_text(broken, encoding="utf-8", newline="")
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
        same = PDF.read_text(encoding="utf-8") == original
        print(f"  还原 {PDF.name}: {'一致' if same else '不一致！'}")

    print("=" * 74)
    return finish(rows)


if __name__ == "__main__":
    raise SystemExit(main())
