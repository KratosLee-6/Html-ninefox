# -*- coding: utf-8 -*-
"""变异验证：paraphrased 门禁必须拦住四类回归。

  M1 忠实度门禁放水（paraphrased 退化成带假标签的 verbatim）
  M2 改写块被标成 verbatim（许可语义被污染）
  M3 open 路径开始调用改写器（verbatim 语义与开销被破坏）
  M4 service 掉线改写器（接线断路）
  M5 重改包装被拆（retry 不绕缓存）

  python scripts/mutate_paraphrase_gates.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
PARA = ROOT / "htmlninefox" / "paraphrase.py"
INTAKE = ROOT / "htmlninefox" / "intake.py"
SERVICE = ROOT / "htmlninefox" / "server" / "intake_service.py"
GATES = ["tests/test_paraphrase_provenance.py"]

FAITHFUL_TAIL = "    return overlap(source, rewrite) <= OVERLAP_CEILING"
PARA_LABEL = '                provenance, carried = "paraphrased", attempt.strip()'
VERA_LABEL = '                provenance, carried = "verbatim", attempt.strip()'
ELIGIBLE = "        elif rewriter is not None and content_text.strip():"
ALWAYS = "        if rewriter is not None and content_text.strip():"
SERVICE_WIRE = "            candidate, raw.decode(\"utf-8\", \"replace\"), rewriter=rewriter)"
RETRY_WIRE = ("        if retry and rewriter is not None:\n"
              "            rewriter = paraphrase.retrying(rewriter)")
RETRY_DEAD = ("        if retry and rewriter is not None:\n"
              "            pass  # MUTATED: 重试包装被拆")
SERVICE_CUT = "            candidate, raw.decode(\"utf-8\", \"replace\"), rewriter=None)"


def run_gates() -> int:
    r = subprocess.run([sys.executable, "-m", "pytest", *GATES,
                        "-q", "-p", "no:cacheprovider", "--tb=no"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return r.returncode


def main() -> int:
    originals = {
        PARA: PARA.read_text(encoding="utf-8"),
        INTAKE: INTAKE.read_text(encoding="utf-8"),
        SERVICE: SERVICE.read_text(encoding="utf-8"),
    }
    bad: list[str] = []
    try:
        for name, mutate in (
            ("M1 忠实度门禁放水",
             lambda: PARA.write_text(
                 originals[PARA].replace(FAITHFUL_TAIL, "    return True", 1),
                 encoding="utf-8")),
            ("M2 改写块被标成 verbatim",
             lambda: INTAKE.write_text(
                 originals[INTAKE].replace(PARA_LABEL, VERA_LABEL, 1),
                 encoding="utf-8")),
            ("M3 open 路径开始调用改写器（elif → if）",
             lambda: INTAKE.write_text(
                 originals[INTAKE].replace(ELIGIBLE, ALWAYS, 1),
                 encoding="utf-8")),
            ("M4 service 掉线改写器",
             lambda: SERVICE.write_text(
                 originals[SERVICE].replace(SERVICE_WIRE, SERVICE_CUT, 1),
                 encoding="utf-8")),
            ("M5 重改包装被拆（retry 不绕缓存）",
             lambda: SERVICE.write_text(
                 originals[SERVICE].replace(RETRY_WIRE, RETRY_DEAD, 1),
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
    print(f"\n{5 - len(bad)}/5 CAUGHT" + (f"；未抓到：{bad}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
