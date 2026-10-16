# -*- coding: utf-8 -*-
"""变异验证：首启种子门禁必须拦住真实回归。

  M1 save() 的初始化守卫被拆（过早持久化复活，空快照毒死种子）。

  曾经还编码了「M2 boot 尾部落盘被拆」，验证时 MISSED——因为 fitAll 的
  相机提交（applyCamera(commit=true) → save()）在 +120ms 时也会落盘，
  拆掉 boot 尾部的显式 save 并不破坏「服务端最终有完整快照」这一属性。
  一个不构成回归的变异不配留在验证脚本里，故删除；boot 尾部的显式 save
  保留在代码里作为显式优于副作用的防御。

  python scripts/mutate_first_boot_gates.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "htmlninefox" / "server" / "static" / "fox-core.js"
GATES = ["tests/test_first_boot_seed.py"]

GUARD = """function save() {
  /* 初始化未完成（首启种子完成前）不持久化。此刻画布还是空的，任何一次
   * 过早保存都会把「空工作区」写进本地快照，其 650ms 防抖还会 PUT 到服务端；
   * 随后 loadSaved/loadRemoteWorkspace 把这个空快照当成「已恢复」，
   * 首启种子在本次与后续每一次启动都被杀掉——test_v061_mobile_library
   * 的 READY 超时正是它（alliance 响应慢时几乎必现）。种子/恢复完成后的
   * boot 尾部会显式 save() 一次，把完整状态落盘。 */
  if (!allowNodeEnter) return;
"""
GUARD_LESS = """function save() {
"""


def run_gates() -> int:
    r = subprocess.run([sys.executable, "-m", "pytest", *GATES,
                        "-q", "-p", "no:cacheprovider", "--tb=no"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return r.returncode


def main() -> int:
    original = CORE.read_text(encoding="utf-8")
    bad: list[str] = []
    try:
        for name, old, new in (
            ("M1 save() 初始化守卫被拆", GUARD, GUARD_LESS),
        ):
            assert old in original, f"变异目标找不到：{name}"
            CORE.write_text(original.replace(old, new, 1), encoding="utf-8")
            code = run_gates()
            verdict = "CAUGHT" if code != 0 else "MISSED"
            print(f"{verdict:8} {name}")
            if code == 0:
                bad.append(name)
            CORE.write_text(original, encoding="utf-8")
    finally:
        CORE.write_text(original, encoding="utf-8")
    print(f"\n{1 - len(bad)}/1 CAUGHT" + (f"；未抓到：{bad}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
