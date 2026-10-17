# -*- coding: utf-8 -*-
"""变异验证：DOCX 导出门禁必须拦住三类回归。

  M1 表格映射被拆（读回断言变红——映射必须真实到达）
  M2 降级清单说谎（unmapped 计数恒 0——完整性门禁变红）
  M3 意图守卫被拆（landing 强行导出 docx 不再被引导）

  python scripts/mutate_docx_gates.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "htmlninefox" / "docx_export.py"
EXPORTING = ROOT / "htmlninefox" / "exporting.py"
GATES = ["tests/test_docx_export.py"]

TABLE_RENDER = ('        elif kind == "table":\n'
                '            rows = block["rows"]')
TABLE_DEAD = ('        elif kind == "table" and False:  # MUTATED: 表格映射被拆\n'
              '            rows = block["rows"]')
UNMAPPED_LINE = '        "unmapped_text_chars": parsed["unmapped_chars"],'
UNMAPPED_ZERO = '        "unmapped_text_chars": 0,  # MUTATED: 降级清单说谎'
INTENT_GUARD = '    if intent not in DOCX_SUITED_INTENTS:'
INTENT_PASS = '    if False and intent not in DOCX_SUITED_INTENTS:  # MUTATED: 守卫被拆'


def run_gates() -> int:
    r = subprocess.run([sys.executable, "-m", "pytest", *GATES,
                        "-q", "-p", "no:cacheprovider", "--tb=no"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return r.returncode


def main() -> int:
    originals = {
        BRIDGE: BRIDGE.read_text(encoding="utf-8"),
        EXPORTING: EXPORTING.read_text(encoding="utf-8"),
    }
    bad: list[str] = []
    try:
        for name, path, old, new in (
            ("M1 表格映射被拆", BRIDGE, TABLE_RENDER, TABLE_DEAD),
            ("M2 降级清单说谎", BRIDGE, UNMAPPED_LINE, UNMAPPED_ZERO),
            ("M3 意图守卫被拆", EXPORTING, INTENT_GUARD, INTENT_PASS),
        ):
            src = originals[path]
            if old not in src:
                print(f"HARD FAIL 找不到变异目标：{name}")
                bad.append(name)
                continue
            path.write_text(src.replace(old, new, 1), encoding="utf-8")
            code = run_gates()
            verdict = "CAUGHT" if code != 0 else "MISSED"
            print(f"{verdict:8} {name}")
            if code == 0:
                bad.append(name)
            path.write_text(originals[path], encoding="utf-8")
    finally:
        for path, text in originals.items():
            path.write_text(text, encoding="utf-8")
    print(f"\n{3 - len(bad)}/3 CAUGHT" + (f"；未抓到：{bad}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
