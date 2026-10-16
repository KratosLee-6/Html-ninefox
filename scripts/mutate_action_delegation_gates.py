# -*- coding: utf-8 -*-
"""变异验证：C6 委托门禁必须拦住四类回归。

  M1 委托监听被拆（全部 data-action 点击静默失效）
  M2 number 类型转换被拆（data-id 字符串直进动作，=== 比较失效）
  M3 签名条目被删（参数静默丢成无参）
  M4 内联 onclick 回流（逃生口重开）

  python scripts/mutate_action_delegation_gates.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "htmlninefox" / "server" / "static" / "fox-core.js"
INDEX = ROOT / "htmlninefox" / "server" / "static" / "index.html"
GATES = ["tests/test_action_registry.py", "tests/test_action_delegation_runtime.py"]

LISTENER_HEAD = """document.addEventListener('click', event => {
  const el = event.target.closest('[data-action]');"""
LISTENER_DEAD = """document.addEventListener('click', event => {
  return; // MUTATED: 委托被拆
  const el = event.target.closest('[data-action]');"""
NUMBER_COERCE = "    if (type === 'number') return Number(raw);"
NUMBER_RAW = "    if (type === 'number') return raw; // MUTATED"
SIGNATURE_ENTRY = "  focusWorkspace: { id: 'number' },\n"
ZOOM_SITE = 'data-action="zoomIn"'
ONCLICK_BACK = 'onclick="zoomBy(1.2)" data-action="zoomIn"'


def run_gates() -> int:
    r = subprocess.run([sys.executable, "-m", "pytest", *GATES,
                        "-q", "-p", "no:cacheprovider", "--tb=no"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return r.returncode


def main() -> int:
    originals = {
        CORE: CORE.read_text(encoding="utf-8"),
        INDEX: INDEX.read_text(encoding="utf-8"),
    }
    bad: list[str] = []
    try:
        for name, path, old, new in (
            ("M1 委托监听被拆", CORE, LISTENER_HEAD, LISTENER_DEAD),
            ("M2 number 转换被拆", CORE, NUMBER_COERCE, NUMBER_RAW),
            ("M3 签名条目被删", CORE, SIGNATURE_ENTRY, ""),
            ("M4 内联 onclick 回流", INDEX, ZOOM_SITE, ONCLICK_BACK),
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
    print(f"\n{4 - len(bad)}/4 CAUGHT" + (f"；未抓到：{bad}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
