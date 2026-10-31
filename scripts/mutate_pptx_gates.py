"""变异验证：PPTX 反向拆解链（v0.8.3）。与 docx-intake 那套不是一回事——
一个守 Word 读进来，这个守 PPT 读进来；提案层两边共用，但兜底分支各有各的守。

四条性质都是**安静失败**：解析照样出结果、提案照样能采纳、没人抛错。

  P1 几何边界不再常驻   → 拆解结果假装「什么都拿到了」
  P2 locator 丢了 shape → 「第几页」还在，「第几个形状」没了，人审无法回指
  P3 图表被当成形状漏拆 → limitations 说「图表只计数」，实际上没人计数
  P4 pptx 意图兜底失效  → 三页小演示被判成 doc，产物形态静默走错

  .venv/Scripts/python.exe scripts/mutate_pptx_gates.py
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
PPTX = ROOT / "htmlninefox" / "pptx_import.py"
PROPOSAL = ROOT / "htmlninefox" / "intake_proposal.py"

# 基线只跑真链与合同门禁：纯单测跑得再多也照不出「界面照常、结果说谎」。
GATE = [
    "tests/test_pptx_import.py",
    "tests/test_pptx_intake_api.py",
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


def m_geometry_limitation_vanishes(pptx: str, proposal: str):
    """P1：几何边界不再常驻 limitations——拆解结果假装全拿到了。"""
    return _swap(pptx, "    limitations: list[str] = [GEOMETRY_LIMITATION]",
                 "    limitations: list[str] = []", "几何边界常驻"), proposal


def m_locator_loses_the_shape(pptx: str, proposal: str):
    """P2：evidence 只剩 slide 号，丢掉 shape——回指从「页＋形状」退化成「页」。"""
    return _swap(pptx, '        evidence = {"slide": number, "shape": shape_index}',
                 '        evidence = {"slide": number}', "evidence 的 shape 键"), proposal


def m_charts_stop_being_counted(pptx: str, proposal: str):
    """P3：图表早退失效——图表形状漏进「未拆解形状」桶，limitations 说谎。"""
    old = ('        if getattr(shape, "has_chart", False):\n'
           '            charts += 1\n'
           '            return')
    new = ('        if False:\n'
           '            charts += 1\n'
           '            return')
    return _swap(pptx, old, new, "图表早退"), proposal


def m_pptx_deck_fallback_goes_away(pptx: str, proposal: str):
    """P4：pptx 来源不再兜底 deck——小演示被判成 doc，产物形态静默走错。"""
    old = ('    if outline.source.kind == "pptx":\n'
           '        # 格式本身就是证据：一页一题的演示，页数少时上面的结构判定会漏判\n'
           '        # 成 doc——来源是 pptx 时按 deck 处理，除非更强的信号已经命中。\n'
           '        return "deck", "来源是演示文稿，页题即章节，按 deck 结构处理"\n')
    return pptx, _swap(proposal, old, "", "pptx 意图兜底")


# 参数顺序与 files 元组一致：(PPTX, PROPOSAL)。
MUTATIONS = [
    ("P1 几何边界不再常驻（结果假装全拿到）", m_geometry_limitation_vanishes,
     "test_geometry_boundary_is_always_stated"),
    ("P2 locator 丢了 shape（回指退化成只有页号）", m_locator_loses_the_shape,
     "test_locators_walk_back_to_the_source"),
    ("P3 图表被当成形状漏拆（limitations 说谎）", m_charts_stop_being_counted,
     "test_charts_are_counted_not_decomposed"),
    ("P4 pptx 意图兜底失效（小演示判成 doc）", m_pptx_deck_fallback_goes_away,
     "test_upload_returns_a_reviewable_deck_proposal"),
]


def main() -> int:
    files = (PPTX, PROPOSAL)
    original = {p: p.read_text(encoding="utf-8") for p in files}
    backup = Path(tempfile.mkdtemp(prefix="fox-pptx-intake-backup-"))
    for p in files:
        shutil.copy2(p, backup / p.name)

    def restore() -> None:
        for p in files:
            shutil.copy2(backup / p.name, p)

    rows: list[tuple[str, str]] = []
    print("=" * 74)
    print("PPTX 反向拆解链 · 变异验证（v0.8.3）")
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
