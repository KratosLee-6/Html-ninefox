# -*- coding: utf-8 -*-
"""变异验证：撤掉两条响应式 CSS 修复，test_responsive_chrome.py 必须变红。

  * index.html ≤1100 的紧凑时间线规则删除 → 768 溢出门禁红；
  * workbench-system.css ≤420 的 .ver 恢复为 display:none → 徽标门禁红。

    python scripts/mutate_responsive_gates.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "htmlninefox" / "server" / "static" / "index.html"
WCSS = ROOT / "htmlninefox" / "server" / "static" / "workbench-system.css"
GATE = "tests/test_responsive_chrome.py"

INDEX_BLOCK = """  .timeline { padding:0 12px; }
  .tl-title, .tl-status { display:none; }
  .tl-stage { min-width:0; flex:0 0 auto; }
  .tl-stage .tl-label { display:none; }
  .tl-stage.active .tl-label, .tl-stage.failed .tl-label { display:inline; font-size:var(--fs-md); }
  .tl-line { margin:0 5px; min-width:8px; }
"""
WCSS_FIX = "  .ver { display:inline-block; font-size:10px; letter-spacing:0; padding:0 2px; }"
WCSS_REVERT = "  .ver { display:none; }"

MUTATIONS = [
    ("R1 删除 ≤1100 紧凑时间线规则（768 溢出复发）",
     INDEX, INDEX_BLOCK, ""),
    ("R2 ≤420 徽标改回 display:none（移动端无法自证版本）",
     WCSS, WCSS_FIX, WCSS_REVERT),
]


def run_gate() -> int:
    r = subprocess.run([sys.executable, "-m", "pytest", GATE,
                        "-q", "-p", "no:cacheprovider", "--tb=no"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return r.returncode


def main() -> int:
    originals = {p: p.read_text(encoding="utf-8") for p in (INDEX, WCSS)}
    bad = []
    try:
        for name, path, old, new in [(m[0], m[1], m[2], m[3]) for m in
                                     [(x[0], x[1], x[2], x[3]) for x in MUTATIONS]]:
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
