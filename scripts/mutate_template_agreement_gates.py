# -*- coding: utf-8 -*-
"""变异验证：预览/生成模板一致性门禁必须能拦住三类回归。

  M1 忠实集合裁掉 landing/infographic（登记被拆）
  M2 templates/landing.html 复活（死文件回包）
  M3 两者同时发生（完整回到缺陷现场：装了 jinja2 的机器预览与生成分叉）

  python scripts/mutate_template_agreement_gates.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
EXPERT = ROOT / "htmlninefox" / "experts" / "generate_expert.py"
LEGACY = ROOT / "htmlninefox" / "templates" / "landing.html"
# 端到端门禁一并跑：M3 的真实缺陷现场由它直接变红（本机装有可选 jinja2）。
GATES = ["tests/test_template_rendering_agreement.py",
         "tests/test_user_template_style_reaches_page.py"]

FULL_SET = ('_INTENT_TEMPLATE_ALIAS_NO_FALLBACK = frozenset({\n'
            '    "deck", "landing", "dashboard", "poster", "archdoc", "doc", "infographic",\n'
            '})')
TRIMMED_SET = ('_INTENT_TEMPLATE_ALIAS_NO_FALLBACK = frozenset({\n'
               '    "deck", "dashboard", "poster", "archdoc", "doc",\n'
               '})')
LEGACY_HTML = ("<!doctype html>\n<html><head><title>Linear · {{ intent }}</title>"
               "</head><body>{{ intent }}</body></html>\n")


def run_gates() -> int:
    r = subprocess.run([sys.executable, "-m", "pytest", *GATES,
                        "-q", "-p", "no:cacheprovider", "--tb=no"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return r.returncode


def main() -> int:
    expert_src = EXPERT.read_text(encoding="utf-8")
    legacy_had_file = LEGACY.exists()
    legacy_src = LEGACY.read_text(encoding="utf-8") if legacy_had_file else None
    bad: list[str] = []
    try:
        for name, apply_mutation in (
            ("M1 忠实集合裁掉 landing/infographic（登记被拆）",
             lambda: EXPERT.write_text(expert_src.replace(FULL_SET, TRIMMED_SET, 1),
                                       encoding="utf-8")),
            ("M2 templates/landing.html 复活（死文件回包）",
             lambda: LEGACY.write_text(LEGACY_HTML, encoding="utf-8")),
            ("M3 集合拆除 + 模板复活（完整回到缺陷现场）",
             lambda: (EXPERT.write_text(
                 expert_src.replace(FULL_SET, TRIMMED_SET, 1), encoding="utf-8"),
                 LEGACY.write_text(LEGACY_HTML, encoding="utf-8"))),
        ):
            apply_mutation()
            code = run_gates()
            verdict = "CAUGHT" if code != 0 else "MISSED"
            print(f"{verdict:8} {name}")
            if code == 0:
                bad.append(name)
            # 每轮结束都恢复原状，再进入下一轮
            EXPERT.write_text(expert_src, encoding="utf-8")
            if legacy_src is None:
                LEGACY.unlink(missing_ok=True)
            else:
                LEGACY.write_text(legacy_src, encoding="utf-8")
    finally:
        EXPERT.write_text(expert_src, encoding="utf-8")
        if legacy_src is None:
            LEGACY.unlink(missing_ok=True)
        else:
            LEGACY.write_text(legacy_src, encoding="utf-8")
    print(f"\n{3 - len(bad)}/3 CAUGHT" + (f"；未抓到：{bad}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
