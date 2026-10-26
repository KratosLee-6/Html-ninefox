"""发版前把五套变异脚本一次跑完 —— 让红留在本地，而不是落在 tag 上。

背景：v0.7.7 / v0.7.8 / v0.8.0 三个 release commit 的 CI 都是红的，随后
补一条 fix commit 才绿。红落在发版提交上，等于每次发版都给自己发一封
「失败」通知，而且 tag 指向的提交是失败状态。

用法：

    .venv/Scripts/python.exe scripts/preflight_mutations.py      # Windows
    python scripts/preflight_mutations.py                        # CI / macOS / Linux

退出码沿用各脚本的语义：
    0 全绿 · 1 有 MISSED（门禁有洞）· 2 基线红 · 3 有 STALE（锚点过期）

任何一个非 0 都不要提交 release commit。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SCRIPTS = (
    ("smoke", "mutate_smoke_gates.py"),
    ("ui", "mutate_ui_gates.py"),
    ("page-blocks", "mutate_page_blocks_gates.py"),
    # v0.8.0 的导出链变异此前没接进 preflight——等于每次发版都没人验证它。
    ("docx-export", "mutate_docx_gates.py"),
    # v0.8.1 的 Word 审核台与采纳链（与上面那个不是一回事：一个读进来，一个导出去）。
    ("docx-intake", "mutate_docx_intake_gates.py"),
    # v0.8.3 的 PPTX 反向拆解链（边界常驻 / 回指完整 / 图表只计数 / 意图兜底）。
    ("pptx-intake", "mutate_pptx_gates.py"),
    # v0.8.4 的 PDF 反向拆解链（扫描页上报 / 回指含页号 / 字号推断 / 魔数守卫）。
    ("pdf-intake", "mutate_pdf_gates.py"),
)

MEANING = {
    0: "OK —— 全部 CAUGHT",
    1: "MISSED —— 门禁在真实破坏下仍然全绿，先修测试",
    2: "基线红 —— 干净树上就有失败，先修产品/测试",
    3: "STALE —— 变异锚点过期，更新锚点后重跑（不是产品坏了）",
}


def main() -> int:
    failures: list[tuple[str, int]] = []
    for name, script in SCRIPTS:
        path = ROOT / "scripts" / script
        print(f"\n{'=' * 74}\n[{name}] {script}\n{'=' * 74}", flush=True)
        proc = subprocess.run([sys.executable, str(path)], cwd=str(ROOT))
        meaning = MEANING.get(proc.returncode, f"未知退出码 {proc.returncode}")
        print(f"[{name}] → {meaning}", flush=True)
        if proc.returncode:
            failures.append((name, proc.returncode))

    print(f"\n{'=' * 74}")
    if not failures:
        print(f"preflight 通过：{len(SCRIPTS)} 套变异全绿，可以提交 release commit。")
        return 0
    print("preflight 未通过，不要在 red 状态下提交 release commit：")
    for name, code in failures:
        print(f"  {name}: 退出码 {code} —— {MEANING.get(code, '')}")
    print("  STALE 是测试体系过期（改锚点）；MISSED 是产品侧漏洞（补门禁）。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
