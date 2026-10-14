# -*- coding: utf-8 -*-
"""变异验证：打包矩阵门禁必须拦住三类回归。

  M1 .deb 退出字节级回读清单（坏包可在验证眼皮下溜进发布）
  M2 .deb 依赖声明丢失 python3-venv（装出点不亮的包）
  M3 verify_unix_portable 的内容断言放水（陈旧产物畅通无阻）

  python scripts/mutate_packaging_gates.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "build-release-packages.yml"
DEB = ROOT / "packaging" / "linux" / "build_deb.py"
VERIFIER = ROOT / "packaging" / "verify_unix_portable.py"
GATES = ["tests/test_packaging_matrix.py"]

DEB_ASSET = ' --asset "*.run" --asset "*.whl" --asset "*.deb" --keep'
DEB_ASSET_LESS = ' --asset "*.run" --asset "*.whl" --keep'
VENV_DECL = "Depends: python3 (>= 3.10), python3-venv"
VENV_LESS = "Depends: python3 (>= 3.10)"


def run_gates() -> int:
    r = subprocess.run([sys.executable, "-m", "pytest", *GATES,
                        "-q", "-p", "no:cacheprovider", "--tb=no"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return r.returncode


def main() -> int:
    originals = {
        WORKFLOW: WORKFLOW.read_text(encoding="utf-8"),
        DEB: DEB.read_text(encoding="utf-8"),
        VERIFIER: VERIFIER.read_text(encoding="utf-8"),
    }
    bad: list[str] = []
    try:
        for name, mutate in (
            ("M1 .deb 退出回读清单",
             lambda: WORKFLOW.write_text(
                 originals[WORKFLOW].replace(DEB_ASSET, DEB_ASSET_LESS, 1),
                 encoding="utf-8")),
            ("M2 Depends 丢 python3-venv",
             lambda: DEB.write_text(
                 originals[DEB].replace(VENV_DECL, VENV_LESS, 1),
                 encoding="utf-8")),
            ("M3 内容断言放水（verify_content 恒 0）",
             lambda: VERIFIER.write_text(
                 originals[VERIFIER].replace(
                     "    return 1 if bad else 0",
                     "    return 0  # MUTATED: 内容断言放水", 1),
                 encoding="utf-8")),
        ):
            mutate()
            code = run_gates()
            verdict = "CAUGHT" if code != 0 else "MISSED"
            print(f"{verdict:8} {name}")
            if code == 0:
                bad.append(name)
            for path, text in originals.items():
                path.write_text(text, encoding="utf-8")
    finally:
        for path, text in originals.items():
            path.write_text(text, encoding="utf-8")
    print(f"\n{3 - len(bad)}/3 CAUGHT" + (f"；未抓到：{bad}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
