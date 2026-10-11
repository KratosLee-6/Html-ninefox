# -*- coding: utf-8 -*-
"""变异验证：撤掉动效层 / reduced-motion 块 / 导出定格，门禁必须变红。

    python scripts/mutate_ambient_motion_gates.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / "htmlninefox" / "generators" / "_shared.py"
EXPORTING = ROOT / "htmlninefox" / "exporting.py"
GATE = "tests/test_ambient_motion.py"

AMBIENT_CALL = "{ambient_motion_css(preset)}\n"
REDUCE_BLOCK_START = "@media (prefers-reduced-motion: reduce) {{"
SETTLE_CALL = "    _settle_ambient(page)\n"

MUTATIONS = [
    ("A1 六类渲染器不再挂动效层（升级被回退）",
     SHARED, AMBIENT_CALL, ""),
    ("A2 reduced-motion 块被删（动画不可关）",
     SHARED, REDUCE_BLOCK_START,
     "@media (prefers-reduced-motion: no-preference) {{ /* disabled gate */"),
    ("A3 导出不再定格（导出件出现空白区块）",
     EXPORTING, SETTLE_CALL, ""),
]


def run_gate() -> int:
    r = subprocess.run([sys.executable, "-m", "pytest", GATE,
                        "-q", "-p", "no:cacheprovider", "--tb=no"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return r.returncode


def main() -> int:
    originals = {p: p.read_text(encoding="utf-8") for p in (SHARED, EXPORTING)}
    bad: list[str] = []
    try:
        for name, path, old, new in MUTATIONS:
            src = originals[path]
            if old not in src:
                print(f"HARD FAIL 找不到变异目标：{name}")
                bad.append(name)
                continue
            path.write_text(src.replace(old, new, 1), encoding="utf-8")
            code = run_gate()
            verdict = "CAUGHT" if code != 0 else "MISSED"
            print(f"{verdict:8} {name}")
            if code == 0:
                bad.append(name)
            path.write_text(originals[path], encoding="utf-8")
    finally:
        for p, text in originals.items():
            p.write_text(text, encoding="utf-8")
    print(f"\n{len(MUTATIONS) - len(bad)}/{len(MUTATIONS)} CAUGHT"
          + (f"；未抓到：{bad}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
