"""变异验证：证明 UI 行为级门禁在坏代码上会红。

`tests/test_ui_e2e_smoke.py` 的 7 条门禁全过，本身不是证据——它完全可能像
`docs/REJECTED-test_gate_quality_gates.py.txt` 里那份被证伪的门禁一样，扫的是源码、
断言的是巧合。本脚本按真实故障形态逐个破坏产品，然后要求对应门禁变红。

覆盖的故障形态（对应两次事故的真实形状）：

* **死按钮**：某个动作从 `window.FoxActions` 派发表里被删（HTML 还在引用它）
* **onclick 指向不存在的函数**：引用了没人实现的名字
* **派发表条目不再委托给模块**：名字在、函数在，点下去什么都不干
* **请求 payload 被改成空**：请求发出去了、服务端回 200，只是没有内容
* **生成完成后产物不落盘**：界面报成功、磁盘上什么都没有
* **交互中抛未捕获 JS 错误**：HTTP 全 200、节点照样渲染，只有页面里炸了（v0.6.1）

本脚本对自己的两条纪律（都是从这个仓库的两次事故里学来的）：

1. **替换串没匹配上是硬失败，不是 MISSED。** MISSED 的含义是「门禁在真实破坏下
   仍然全绿 = 门禁无效」；而没匹配上的变异只是**根本没测到**，记成 MISSED 会凭空
   造出一条假结论。两者必须分开，且硬失败时脚本以非零码退出。
2. **用事先读到的字节还原，绝不用 `git checkout --`。** 仓库里有用户未提交的改动
   （SKILL.md 的删除状态、assets/marketing/、skill/、一份 research 文档），
   git checkout 会连它们一起丢掉。写入时统一 `newline=""`，避免 Windows 的 CRLF
   转换把只改了逻辑的文件变成"字节不同"的假变异。
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # pragma: no cover
    pass

STATIC = ROOT / "htmlninefox" / "server" / "static"
INDEX = STATIC / "index.html"
CORE = STATIC / "fox-core.js"
EXPORTS = STATIC / "lifecycle-exports.js"
APP = ROOT / "htmlninefox" / "server" / "app.py"

TARGETS = (INDEX, CORE, EXPORTS, APP)
GATE = "tests/test_ui_e2e_smoke.py"


class MutationFailure(RuntimeError):
    """变异没有真的改变文件——硬失败，不是 MISSED。"""


def _run(extra: list[str]) -> subprocess.CompletedProcess:
    import os
    return subprocess.run(
        [sys.executable, "-m", "pytest", GATE, *extra,
         "-q", "-p", "no:cacheprovider", "--no-header", "-x"],
        cwd=ROOT, capture_output=True, text=True, timeout=1800,
        # 门禁输出中文，Windows 控制台是 GBK；不给显式编码会让 proc.stdout 变成
        # None，看起来像"静默通过"。
        encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"})


# --- 变异体：每个接收原文，返回被破坏的原文 ---

def m_dead_advance_button(texts: dict[str, str]) -> dict[str, str]:
    """死按钮（主生成按钮）：派发表里删掉 advanceActive，HTML 的 onclick 照旧。"""
    out = dict(texts)
    for line in out[str(CORE)].splitlines(keepends=True):
        if line.lstrip().startswith("advanceActive:"):
            out[str(CORE)] = out[str(CORE)].replace(line, "")
            return out
    raise MutationFailure("fox-core.js 的派发表里找不到 advanceActive 条目")


def m_dead_batch_button(texts: dict[str, str]) -> dict[str, str]:
    """死按钮（S20 原型）：派发表里删掉 intakeFetchBatch。"""
    out = dict(texts)
    for line in out[str(CORE)].splitlines(keepends=True):
        if line.lstrip().startswith("intakeFetchBatch:"):
            out[str(CORE)] = out[str(CORE)].replace(line, "")
            return out
    raise MutationFailure("fox-core.js 的派发表里找不到 intakeFetchBatch 条目")


def m_onclick_points_at_nothing(texts: dict[str, str]) -> dict[str, str]:
    """onclick 指向一个不存在的函数名。"""
    out = dict(texts)
    if 'onclick="advanceActive()"' not in out[str(INDEX)]:
        raise MutationFailure('index.html 里找不到 onclick="advanceActive()"')
    out[str(INDEX)] = out[str(INDEX)].replace(
        'onclick="advanceActive()"', 'onclick="advanceActiveRenamed()"', 1)
    return out


def m_onclick_batch_points_at_nothing(texts: dict[str, str]) -> dict[str, str]:
    """onclick 指向不存在的函数名（批量抓取那一颗）。"""
    out = dict(texts)
    if 'onclick="intakeFetchBatch()"' not in out[str(INDEX)]:
        raise MutationFailure('index.html 里找不到 onclick="intakeFetchBatch()"')
    out[str(INDEX)] = out[str(INDEX)].replace(
        'onclick="intakeFetchBatch()"', 'onclick="intakeFetchBatchRenamed()"', 1)
    return out


def m_dispatch_entry_becomes_a_noop(texts: dict[str, str]) -> dict[str, str]:
    """派发表条目还在、名字也还挂在 window 上，但不再委托给任何模块。"""
    out = dict(texts)
    for line in out[str(CORE)].splitlines(keepends=True):
        if line.lstrip().startswith("openExportCenter:"):
            broken = line.replace("=> window.FoxExports.open(nodeId)", "=> undefined")
            if broken == line:
                raise MutationFailure("openExportCenter 条目没有委托给 FoxExports.open")
            out[str(CORE)] = out[str(CORE)].replace(line, broken)
            return out
    raise MutationFailure("fox-core.js 的派发表里找不到 openExportCenter 条目")


def m_export_payload_emptied(texts: dict[str, str]) -> dict[str, str]:
    """导出请求发出去了、服务端也回了响应，只是格式字段被清空。"""
    out = dict(texts)
    needle = "format: $('#export-format').value,"
    if needle not in out[str(EXPORTS)]:
        raise MutationFailure("lifecycle-exports.js 里找不到导出 payload 的 format 字段")
    out[str(EXPORTS)] = out[str(EXPORTS)].replace(needle, "format: '',", 1)
    return out


def m_artifact_never_lands(texts: dict[str, str]) -> dict[str, str]:
    """生成完成、界面报成功、产物节点也画出来了——但产物留在 staging 目录里被删掉。

    这是最阴险的一种：所有状态字段都正常，只有磁盘上什么都没有。
    """
    out = dict(texts)
    needle = "            source.rename(target)\n"
    if needle not in out[str(APP)]:
        raise MutationFailure("app.py 里找不到把生成结果搬进产物目录的 source.rename(target)")
    out[str(APP)] = out[str(APP)].replace(
        needle, "            pass  # mutation: 生成完成但不落盘\n", 1)
    return out


def m_uncaught_error_during_interaction(texts: dict[str, str]) -> dict[str, str]:
    """交互中抛未捕获 JS 错误：HTTP 全 200、节点照样渲染，只有页面里炸了。"""
    out = dict(texts)
    needle = "  async function open(nodeId) {\n"
    if needle not in out[str(EXPORTS)]:
        raise MutationFailure("lifecycle-exports.js 里找不到导出中心的 open()")
    out[str(EXPORTS)] = out[str(EXPORTS)].replace(
        needle, needle + "    throw new Error('mutation: 导出中心在交互中崩溃');\n", 1)
    return out


MUTATIONS = [
    ("U1 死按钮：派发表删掉 advanceActive",
     m_dead_advance_button, "advance_button_really_drives"),
    ("U2 死按钮：派发表删掉 intakeFetchBatch（S20 原型）",
     m_dead_batch_button, "batch_intake_button_really_reaches"),
    ("U3 onclick 指向不存在的函数（推进按钮）",
     m_onclick_points_at_nothing, "advance_button_really_drives"),
    ("U4 onclick 指向不存在的函数（批量抓取）",
     m_onclick_batch_points_at_nothing, "batch_intake_button_really_reaches"),
    ("U5 派发表条目不再委托给 FoxExports",
     m_dispatch_entry_becomes_a_noop, "deck_export_writes_a_real_pptx"),
    ("U6 导出请求的 payload 被改成空",
     m_export_payload_emptied, "deck_export_writes_a_real_pptx"),
    ("U7 生成完成后产物不落盘",
     m_artifact_never_lands, "generate_click_lands_a_real_artifact"),
    ("U8 交互中抛未捕获的页面 JS 错误",
     m_uncaught_error_during_interaction, "no_uncaught_page_errors"),
]


def main() -> int:
    originals = {str(path): path.read_text(encoding="utf-8") for path in TARGETS}
    backup = Path(tempfile.mkdtemp(prefix="fox-mutate-ui-backup-"))
    for path in TARGETS:
        shutil.copy2(path, backup / path.name)

    def restore() -> None:
        for path in TARGETS:
            shutil.copy2(backup / path.name, path)

    def apply(texts: dict[str, str]) -> None:
        for path in TARGETS:
            # newline="" 关掉 CRLF 转换：否则只改了一行的文件会变成"整文件字节都不同"，
            # 变异就退化成"随便破坏点什么"，而不是上面写明的那个故障形态。
            path.write_text(texts[str(path)], encoding="utf-8", newline="")

    rows: list[tuple[str, str]] = []
    print("=" * 74)
    print("UI 行为级门禁 · 变异验证")
    print("=" * 74)
    try:
        clean = _run([])
        if clean.returncode != 0:
            print("基线就红，无法做变异验证：")
            print(clean.stdout[-3000:])
            return 2
        print(f"基线：{GATE} 全过\n")

        for name, fn, gate in MUTATIONS:
            try:
                broken = fn(originals)
            except MutationFailure as exc:
                print(f"HARD FAIL  {name}\n          {exc}")
                rows.append((name, "HARD FAIL"))
                continue

            if broken == originals:
                print(f"HARD FAIL  {name}\n          变异没有改变任何内容")
                rows.append((name, "HARD FAIL"))
                continue

            apply(broken)
            try:
                proc = _run(["-k", gate])
            finally:
                restore()

            verdict = "MISSED" if proc.returncode == 0 else "CAUGHT"
            rows.append((name, verdict))
            print(f"{verdict:9} {name}  → {gate}")
            if verdict == "CAUGHT":
                # 只打断言/异常那几行。进度点（"F"）不是证据——它只说明"红了"，
                # 不说明"是因为哪条断言红的"。
                evidence = [line.strip() for line in proc.stdout.splitlines()
                            if line.strip().startswith("E ")
                            and ("assert" in line or "Error" in line)]
                for line in evidence[:2]:
                    print(f"          {line[:118]}")
    finally:
        restore()
        shutil.rmtree(backup, ignore_errors=True)

    print("=" * 74)
    caught = sum(1 for _, verdict in rows if verdict == "CAUGHT")
    missed = [name for name, verdict in rows if verdict == "MISSED"]
    hard = [name for name, verdict in rows if verdict == "HARD FAIL"]
    print(f"{caught}/{len(rows)} CAUGHT")
    if missed:
        print("门禁在真实破坏下仍然全绿——视为无效门禁：")
        for name in missed:
            print(f"  MISSED   {name}")
    if hard:
        print("变异没有生效，本轮结论无效：")
        for name in hard:
            print(f"  HARD     {name}")
    print("=" * 74)
    return 1 if (missed or hard) else 0


if __name__ == "__main__":
    raise SystemExit(main())
