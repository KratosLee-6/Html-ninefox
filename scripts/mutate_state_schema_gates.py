# -*- coding: utf-8 -*-
"""变异验证：C7 状态声明门禁必须拦住三类回归。

  M1 未声明的全局状态键被引用（审计 C7 原始缺陷形态）
  M2 声明里的键被删掉（声明与对象脱钩）
  M3 lifecycle 文件顶层泄漏语句（作用域重新共享）

  python scripts/mutate_state_schema_gates.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "htmlninefox" / "server" / "static" / "fox-core.js"
INTAKE = ROOT / "htmlninefox" / "server" / "static" / "lifecycle-intake.js"
PROJECTS = ROOT / "htmlninefox" / "server" / "static" / "lifecycle-projects.js"
GATES = ["tests/test_frontend_state_schema.py"]

STRICT = "(function () {\n  'use strict';"
PROBE = "(function () {\n  'use strict';\n  void state.c7ProbeUndeclared;"
DECLARED = "  intakeComponents: [],\n};"


def run_gates() -> int:
    r = subprocess.run([sys.executable, "-m", "pytest", *GATES,
                        "-q", "-p", "no:cacheprovider", "--tb=no"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return r.returncode


def main() -> int:
    originals = {
        CORE: CORE.read_text(encoding="utf-8"),
        INTAKE: INTAKE.read_text(encoding="utf-8"),
        PROJECTS: PROJECTS.read_text(encoding="utf-8"),
    }
    bad: list[str] = []
    try:
        for name, mutate, restore in (
            ("M1 未声明键被引用（intakeComponents 式回归）",
             lambda: INTAKE.write_text(
                 originals[INTAKE].replace(STRICT, PROBE, 1), encoding="utf-8"),
             lambda: INTAKE.write_text(originals[INTAKE], encoding="utf-8")),
            ("M2 声明删掉 intakeComponents（声明与对象脱钩）",
             lambda: CORE.write_text(
                 originals[CORE].replace(DECLARED, "};", 1), encoding="utf-8"),
             lambda: CORE.write_text(originals[CORE], encoding="utf-8")),
            ("M3 顶层泄漏 var（作用域重新共享）",
             lambda: PROJECTS.write_text(
                 "var c7Leaked = 1;\n" + originals[PROJECTS], encoding="utf-8"),
             lambda: PROJECTS.write_text(originals[PROJECTS], encoding="utf-8")),
        ):
            mutate()
            code = run_gates()
            verdict = "CAUGHT" if code != 0 else "MISSED"
            print(f"{verdict:8} {name}")
            if code == 0:
                bad.append(name)
            restore()
    finally:
        for path, text in originals.items():
            path.write_text(text, encoding="utf-8")
    print(f"\n{3 - len(bad)}/3 CAUGHT" + (f"；未抓到：{bad}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
