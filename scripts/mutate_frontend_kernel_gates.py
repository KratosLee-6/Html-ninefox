"""Mutation check for the C7 front-end kernel gates.

A gate that has never been seen to fail is not evidence. Every mutation below
breaks one way the front-end can break and the matching gate MUST go red.

Two rules this script holds itself to, both learned the hard way:

* A mutation whose replacement string did not match is a **hard failure**, not
  a MISSED. MISSED means "the gate stayed green on broken code"; a mutation
  that never applied is simply untested, and recording it as MISSED would
  manufacture a fake finding.
* Mutations run in-process against a restored copy of the real files, and the
  originals are restored from the bytes read up front — not via git — so the
  script cannot lose work that was never committed.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

INDEX = ROOT / "htmlninefox" / "server" / "static" / "index.html"
CORE = ROOT / "htmlninefox" / "server" / "static" / "fox-core.js"
APP = ROOT / "htmlninefox" / "server" / "app.py"

# The kernel file is read by two gates: the new front-end ones, and the older
# action-registry gate, which used to find window.FoxActions inside index.html
# and had to be taught where the table moved to. Both are run together so a
# relocation cannot quietly weaken either.
GATES = ("tests/test_frontend_kernel_loadable.py", "tests/test_action_registry.py")


class MutationFailure(RuntimeError):
    """The mutation did not actually change the file — hard failure."""


def _run(gate_args: list[str]) -> subprocess.CompletedProcess:
    import os
    return subprocess.run(
        [sys.executable, "-m", "pytest", *GATES, *gate_args,
         "-q", "-p", "no:cacheprovider", "--no-header", "-x"],
        cwd=ROOT, capture_output=True, text=True, timeout=900,
        # The gate speaks Chinese; the Windows console codepage is GBK and
        # raises UnicodeDecodeError on pytest output, which surfaces as
        # proc.stdout being None and looks like a silent pass.
        encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"})


# --- mutation bodies: each takes the original text and returns broken text ---

def m_drop_whitelist_entry(index: str, core: str, app: str) -> tuple:
    """The exact v0.6.0-shaped trap: the file ships, the whitelist forgets it."""
    for line in app.splitlines(keepends=True):
        if '"/fox-core.js"' in line:
            return index, core, app.replace(line, "")
    raise MutationFailure("app.py 里找不到 /fox-core.js 白名单条目")


def m_drop_script_tag(index: str, core: str, app: str) -> tuple:
    line = '  <script src="/fox-core.js"></script>\n'
    if line not in index:
        line = '<script src="/fox-core.js"></script>\n'
    if line not in index:
        raise MutationFailure("index.html 里找不到 fox-core.js 的 script 标签")
    return index.replace(line, "", 1), core, app


def m_inline_the_kernel(index: str, core: str, app: str) -> tuple:
    """Put the kernel back inside the page while keeping the script tag, so
    only the inline-size assertion can catch it."""
    tag = '<script src="/fox-core.js"></script>'
    if tag not in index:
        raise MutationFailure("index.html 里找不到 fox-core.js 的 script 标签")
    body = core.split("\n", 1)[1] if "\n" in core else core
    return index.replace(tag, "<script>\n" + body + "\n</script>", 1), core, app


def m_rename_shared_helper(index: str, core: str, app: str) -> tuple:
    if "function flash(" not in core:
        raise MutationFailure("fox-core.js 里找不到 function flash(")
    return index, core.replace("function flash(", "function flash_RENAMED(", 1), app


def m_throw_on_load(index: str, core: str, app: str) -> tuple:
    """The kernel parses but dies while running — a blank workbench."""
    cut = core.find("*/")
    if cut < 10:
        raise MutationFailure("fox-core.js 开头没有以 */ 结束的横幅注释")
    at = core.find("\n", cut)
    if at < 0:
        raise MutationFailure("横幅注释结尾没有换行")
    at += 1
    return index, core[:at] + "throw new Error('mutation: kernel dies on load');\n" + core[at:], app


def m_syntax_error(index: str, core: str, app: str) -> tuple:
    if not core.rstrip().endswith(";"):
        raise MutationFailure("无法确定注入位置")
    return index, core.rstrip()[:-1] + "\nfunction (\n", app


def m_whitelist_points_at_wrong_file(index: str, core: str, app: str) -> tuple:
    for line in app.splitlines(keepends=True):
        if '"/fox-core.js"' in line:
            broken = line.replace('("fox-core.js"', '("canvas-engine.js"')
            return index, core, app.replace(line, broken)
    raise MutationFailure("app.py 里找不到 /fox-core.js 白名单条目")


def m_break_namespace(index: str, core: str, app: str) -> tuple:
    if "window.FoxActions" not in core:
        raise MutationFailure("fox-core.js 里找不到 window.FoxActions")
    return index, core.replace("window.FoxActions", "window.__FoxActions_MUTATED", 1), app


def m_unregister_a_referenced_action(index: str, core: str, app: str) -> tuple:
    """The S20 dead-button shape: the HTML calls the name, nothing implements it.

    intakeFetchBatch is referenced by index.html and is implemented *only* as a
    dispatch-table entry, so deleting the entry is exactly the defect this gate
    was written for.
    """
    if "onclick=\"intakeFetchBatch()\"" not in index:
        raise MutationFailure("index.html 里找不到 onclick=\"intakeFetchBatch()\"")
    for line in core.splitlines(keepends=True):
        if line.lstrip().startswith("intakeFetchBatch:"):
            return index, core.replace(line, ""), app
    raise MutationFailure("fox-core.js 的派发表里找不到 intakeFetchBatch 条目")


def m_entry_stops_delegating_to_a_module(index: str, core: str, app: str) -> tuple:
    for line in core.splitlines(keepends=True):
        if "loadProjects:" in line and "window.FoxProjects.load()" in line:
            broken = line.replace("window.FoxProjects.load()", "legacyLoadProjects()")
            return index, core.replace(line, broken), app
    raise MutationFailure("fox-core.js 的派发表里找不到 loadProjects 条目")


MUTATIONS = [
    ("K1 白名单漏登记 /fox-core.js",
     m_drop_whitelist_entry, "test_every_script_the_page_asks_for_is_actually_served"),
    ("K2 页面不再加载 fox-core.js",
     m_drop_script_tag, "test_fox_core_exists_and_is_not_inline"),
    ("K3 内核被搬回 inline",
     m_inline_the_kernel, "test_fox_core_exists_and_is_not_inline"),
    ("K4 共享助手 flash 消失",
     m_rename_shared_helper, "test_front_end_chain_loads_and_every_shared_helper_is_really_defined"),
    ("K5 内核加载即抛错",
     m_throw_on_load, "test_front_end_chain_loads_and_every_shared_helper_is_really_defined"),
    ("K6 内核语法错误",
     m_syntax_error, "test_fox_core_passes_the_node_syntax_check"),
    ("K7 白名单指向了别的文件",
     m_whitelist_points_at_wrong_file, "test_every_script_the_page_asks_for_is_actually_served"),
    ("K8 命名空间不再暴露",
     m_break_namespace, "test_front_end_chain_loads_and_every_shared_helper_is_really_defined"),
    ("K9 派发表漏登记被引用的动作（S20 死按钮形状）",
     m_unregister_a_referenced_action, "test_every_referenced_action_resolves"),
    ("K10 派发表条目不再委托给 Fox* Module",
     m_entry_stops_delegating_to_a_module, "test_registry_entries_point_at_real_fox_modules"),
]


def main() -> int:
    original = {p: p.read_text(encoding="utf-8") for p in (INDEX, CORE, APP)}
    backup = Path(tempfile.mkdtemp(prefix="fox-mutate-backup-"))
    for p in original:
        shutil.copy2(p, backup / p.name)

    def restore() -> None:
        for p in original:
            shutil.copy2(backup / p.name, p)

    rows: list[tuple[str, str]] = []
    print("=" * 74)
    print("C7 前端内核门禁 · 变异验证")
    print("=" * 74)
    try:
        clean = _run([])
        if clean.returncode != 0:
            print("基线就红，无法做变异验证：")
            print(clean.stdout[-3000:])
            return 2
        print(f"基线：{len(GATES)} 个门禁文件全过\n")

        for name, fn, gate in MUTATIONS:
            try:
                i2, c2, a2 = fn(original[INDEX], original[CORE], original[APP])
            except MutationFailure as exc:
                print(f"HARD FAIL  {name}\n          {exc}")
                rows.append((name, "HARD FAIL"))
                restore()
                continue

            if (i2, c2, a2) == tuple(original[p] for p in (INDEX, CORE, APP)):
                print(f"HARD FAIL  {name}\n          变异没有改变任何内容")
                rows.append((name, "HARD FAIL"))
                continue

            INDEX.write_text(i2, encoding="utf-8")
            CORE.write_text(c2, encoding="utf-8")
            APP.write_text(a2, encoding="utf-8")
            try:
                proc = _run([f"-k", gate])
            finally:
                restore()

            if proc.returncode == 0:
                verdict = "MISSED"
            else:
                verdict = "CAUGHT"
            rows.append((name, verdict))
            print(f"{verdict:9} {name}  → {gate}")
            if verdict == "CAUGHT":
                tail = [l for l in proc.stdout.splitlines() if l.strip()][:1]
                if tail:
                    print(f"          {tail[0][:110]}")
    finally:
        restore()
        shutil.rmtree(backup, ignore_errors=True)

    print("=" * 74)
    caught = sum(1 for _, v in rows if v == "CAUGHT")
    missed = [n for n, v in rows if v == "MISSED"]
    hard = [n for n, v in rows if v == "HARD FAIL"]
    print(f"{caught}/{len(rows)} CAUGHT")
    if missed:
        print("门禁在真实破坏下仍然全绿——视为无效门禁：")
        for n in missed:
            print(f"  MISSED   {n}")
    if hard:
        print("变异没有生效，本轮结论无效：")
        for n in hard:
            print(f"  HARD     {n}")
    print("=" * 74)
    return 1 if (missed or hard) else 0


if __name__ == "__main__":
    raise SystemExit(main())
