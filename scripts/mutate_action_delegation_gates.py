# -*- coding: utf-8 -*-
"""变异验证：C6 委托门禁必须拦住六类回归。

  M1 委托监听被拆（全部 data-action 点击静默失效）
  M2 number 类型转换被拆（data-id 字符串直进动作，=== 比较失效）
  M3 签名条目被删（参数静默丢成无参）
  M4 内联 onclick 回流（逃生口重开）
  M5 工作台键盘路径被拆（非原生控件 Enter/Space 失效）
  M6 classic 委托被拆（v0.8.3 复活的五个控件再次全灭）

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
CLASSIC = ROOT / "htmlninefox" / "server" / "static" / "classic.html"
GATES = ["tests/test_action_registry.py", "tests/test_action_delegation_runtime.py",
         "tests/test_keyboard_walk.py"]

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
# M5：fox-core 的 keydown 激活路径（v0.8.3 键盘可达）。
KEYDOWN_HEAD = """document.addEventListener('keydown', event => {
  if (event.key !== 'Enter' && event.key !== ' ') return;"""
KEYDOWN_DEAD = """document.addEventListener('keydown', event => {
  return; // MUTATED: 键盘路径被拆
  if (event.key !== 'Enter' && event.key !== ' ') return;"""
# M6：classic 自己的最小委托（v0.8.3 复活证书的守护对象）。
CLASSIC_CLICK_HEAD = """document.addEventListener('click', e => {
  const el = e.target.closest('[data-action]');
  if (el) dispatchAction(el, e);
});"""
CLASSIC_CLICK_DEAD = """document.addEventListener('click', e => {
  return; // MUTATED: classic 委托被拆
  const el = e.target.closest('[data-action]');
  if (el) dispatchAction(el, e);
});"""


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
        CLASSIC: CLASSIC.read_text(encoding="utf-8"),
    }
    bad: list[str] = []
    try:
        for name, path, old, new in (
            ("M1 委托监听被拆", CORE, LISTENER_HEAD, LISTENER_DEAD),
            ("M2 number 转换被拆", CORE, NUMBER_COERCE, NUMBER_RAW),
            ("M3 签名条目被删", CORE, SIGNATURE_ENTRY, ""),
            ("M4 内联 onclick 回流", INDEX, ZOOM_SITE, ONCLICK_BACK),
            ("M5 工作台键盘路径被拆", CORE, KEYDOWN_HEAD, KEYDOWN_DEAD),
            ("M6 classic 委托被拆", CLASSIC, CLASSIC_CLICK_HEAD, CLASSIC_CLICK_DEAD),
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
    print(f"\n{6 - len(bad)}/6 CAUGHT" + (f"；未抓到：{bad}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
