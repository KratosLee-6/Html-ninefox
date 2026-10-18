"""变异验证的共用诊断层 —— 把「红」分成两类。

为什么需要这个文件
------------------
v0.7.7 / v0.7.8 / v0.8.0 三个发版提交的 CI 都是红的，根因不是产品坏了，
而是**变异脚本的字面锚点被源码改动打飞**：脚本打印一句 `NOT APPLIED`，
job 退出码 1，GitHub 就发一封「Test workflow run failed」。看通知的人
以为是功能坏了，实际是测试体系自己过期。

两类失败必须分开报，而且给不同退出码：

    0  OK        全部 CAUGHT
    1  MISSED    门禁在真实破坏下仍然全绿 —— 这是**真漏洞**，要修测试
    3  STALE     变异锚点找不到 —— 这是**测试体系过期**，要修锚点
    2  基线红    （各脚本自己返回，表示连干净树都不过）

3 仍然让 CI 红（否则覆盖率会在无人察觉时下降），但 GH 的注解会写明
「锚点过期」而不是笼统的失败，人一眼就知道该改哪儿。

用法
----
    from mutation_support import STALE_EXIT, MISSED_EXIT, stale_report, finish

    except MutationFailure as exc:            # 或 old not in text
        print(stale_report(name, target, needle, text, str(exc)))
        rows.append((name, "STALE"))
"""

from __future__ import annotations

import difflib
from pathlib import Path
from typing import Iterable, Sequence

STALE_EXIT = 3
MISSED_EXIT = 1

# 这些 verdict 都表示「变异没落上去」，属于测试体系问题，不是产品缺陷。
STALE_VERDICTS = frozenset({"STALE", "HARD FAIL", "NOT APPLIED", "BROKEN SELECTOR"})
MISSED_VERDICTS = frozenset({"MISSED"})


def nearest_line(text: str, needle: str) -> tuple[int, str]:
    """在 text 里找与 needle 最像的一行，返回 (行号, 内容)。

    锚点过期时最有用的信息是「你以为的那一行现在长什么样」，而不是
    「PATTERN NOT FOUND」。用第一行做相似度锚点，够用且便宜。
    """
    probe = (needle.splitlines() or [""])[0].strip()
    lines = text.splitlines()
    if not lines:
        return 0, ""
    best_i, best_ratio = 0, 0.0
    for i, line in enumerate(lines):
        ratio = difflib.SequenceMatcher(None, probe, line.strip()).ratio()
        if ratio > best_ratio:
            best_i, best_ratio = i, ratio
    if best_ratio < 0.4:
        return 0, ""
    return best_i + 1, lines[best_i].strip()


def stale_report(
    label: str,
    target: str | Path,
    needle: str,
    text: str,
    reason: str = "",
    hint: str = "",
) -> str:
    """锚点过期时的完整诊断块：文件、行号、期望、现实、下一步。"""
    line_no, actual = nearest_line(text, needle)
    where = f"{target}:{line_no}" if line_no else str(target)
    expected = "\n".join(needle.splitlines()[:3])
    out = [
        "",
        f"STALE  {label}",
        f"  这不是产品缺陷，是变异锚点过期了：源码改过，脚本仍按旧文本找它。",
        f"  目标   {where}",
    ]
    if reason:
        out.append(f"  原因   {reason}")
    out.append("  期望   " + expected.replace("\n", "\n         "))
    if actual:
        out.append(f"  实际   {actual[:160]}")
    else:
        out.append("  实际   附近没有相似行（整段可能被删掉或改名了）")
    out.append(
        "  下一步 把该变异的锚点改成能容忍同类改动的正则/结构定位，"
        "再跑一遍；不要为了变绿把变异删掉。")
    if hint:
        out.append(f"  提示   {hint}")
    return "\n".join(out)


def finish(rows: Sequence[Sequence[str]], total_expected: int | None = None) -> int:
    """按 verdict 给出退出码，并打印「结论一句话」。

    行可以是 (name, verdict) 或 (name, verdict, evidence) —— 三个脚本的历史
    结构不同，这里只取前两项，避免让调用方为了对齐格式而改动记录逻辑。
    """
    pairs = [(row[0], row[1]) for row in rows]
    caught = sum(1 for _, v in pairs if v == "CAUGHT")
    missed = [n for n, v in pairs if v in MISSED_VERDICTS]
    stale = [n for n, v in pairs if v in STALE_VERDICTS]
    other = [(n, v) for n, v in pairs
             if v not in MISSED_VERDICTS | STALE_VERDICTS and v != "CAUGHT"]

    print("=" * 74)
    print(f"{caught}/{len(pairs)} CAUGHT")
    if missed:
        print("MISSED —— 门禁在真实破坏下仍然全绿，这是产品侧漏洞：")
        for name in missed:
            print(f"  {name}")
    if stale:
        print("STALE —— 变异锚点过期，覆盖率没有被验证（不是产品坏了）：")
        for name in stale:
            print(f"  {name}")
    for name, verdict in other:
        print(f"  {verdict}  {name}")
    print("=" * 74)

    if missed:
        print(f"CI 结论：MISSED（退出码 {MISSED_EXIT}）—— 修门禁。")
        return MISSED_EXIT
    if stale or other:
        print(f"CI 结论：STALE（退出码 {STALE_EXIT}）—— 更新变异锚点后重跑。")
        return STALE_EXIT
    if total_expected is not None and caught != total_expected:
        print(f"CI 结论：只捕获 {caught}/{total_expected} —— 当作 STALE 处理。")
        return STALE_EXIT
    return 0


def check_anchor(target: str | Path, needle: str) -> bool:
    """一条命令检查锚点还在不在（给发版前的 preflight 用）。"""
    path = Path(target)
    if not path.exists():
        return False
    return needle in path.read_text(encoding="utf-8")
