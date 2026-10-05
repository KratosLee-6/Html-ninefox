"""Mutation check for the node-removal observer gates.

The gates claim that deleting nodes leaves `nodes`, `edges` and the persisted
snapshot agreeing. Every mutation below breaks one of those three in a way the
in-place rewrite could plausibly introduce, and each must turn a test red.

The interesting one is N1: it removes the reassignment while keeping the filter
call. That is not a typo — it is exactly the "I made it in place but forgot the
binding still points at the new array" shape, and the classic inverse, where
the code builds a correct new array and then forgets to publish it. Nothing
throws in either case.

Rules this script holds itself to:
  * a mutation whose replacement string did not match is a HARD FAILURE, never a
    MISSED — MISSED means "the gate stayed green on broken code", while a
    mutation that never applied is simply untested
  * a non-zero pytest exit with "no tests ran" is not a red gate
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "htmlninefox" / "server" / "static" / "fox-core.js"
PROJECTS = ROOT / "htmlninefox" / "server" / "static" / "lifecycle-projects.js"
GATE = "tests/test_nodes_removal_observers.py"

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


class MutationFailure(RuntimeError):
    """The mutation did not change the file — hard failure."""


def _run(extra: list[str]) -> subprocess.CompletedProcess:
    import os
    return subprocess.run(
        [sys.executable, "-m", "pytest", GATE, *extra,
         "-q", "-p", "no:cacheprovider", "--no-header", "-x"],
        cwd=ROOT, capture_output=True, text=True, timeout=1200,
        encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"})


# --- each mutation takes (core, projects) and returns the broken pair

def m_publish_nothing(core: str, projects: str):
    """The filter runs, the assignment does not. Nothing throws; nothing happens."""
    old = "    nodes = nodes.filter(x => !removed.has(x.id));"
    if old not in projects:
        raise MutationFailure("没找到 removeNodes 里的 nodes 重新赋值")
    return core, projects.replace(old, "    nodes.filter(x => !removed.has(x.id));")


def m_forget_edges(core: str, projects: str):
    """Nodes are cleaned, the edges that pointed at them are not."""
    old = "    edges = edges.filter(e => !removed.has(e.from) && !removed.has(e.to));"
    if old not in projects:
        raise MutationFailure("没找到 removeNodes 里的 edges 过滤")
    return core, projects.replace(old, "", 1)


def m_filter_too_wide(core: str, projects: str):
    """The kind survives but the project's file nodes survive too — a predicate
    that quietly stopped matching one of the two kinds."""
    old = "['file', 'output'].includes(x.kind)"
    if old not in projects:
        raise MutationFailure("没找到 removeNodes 的 kind 过滤")
    return core, projects.replace(old, "x.kind === 'output'", 1)


def m_kernel_stops_publishing(core: str, projects: str):
    """The kernel's own site, same shape as N1."""
    old = "  nodes = nodes.filter(node => !removing.has(node.id));"
    if old not in core:
        raise MutationFailure("没找到 deleteNodeIds 里的 nodes 重新赋值")
    return core.replace(old, "  nodes.filter(node => !removing.has(node.id));"), projects


def m_kernel_forget_edges(core: str, projects: str):
    old = "  edges = edges.filter(edge => !removing.has(edge.from) && !removing.has(edge.to));"
    if old not in core:
        raise MutationFailure("没找到 deleteNodeIds 里的 edges 过滤")
    return core.replace(old, "", 1), projects


def m_kernel_leaves_active_workspace_id(core: str, projects: str):
    """The workspace is gone but the kernel still points at it.

    The first attempt removed only the `activeWorkspaceId = null` inside the
    loop and the gate stayed green — correctly. There is a second line just
    below it that recomputes the id and nulls it anyway, so the code has two
    paths to the same end state and one of them can go without anyone noticing.
    Removing only one is not a defect; removing both is.
    """
    first = "    if (activeWorkspaceId === workspace.id) activeWorkspaceId = null;"
    second = ("  if (!nodes.some(node => node.kind === 'ws'"
              " && node.id === activeWorkspaceId)) activeWorkspaceId = nodes.find")
    if first not in core:
        raise MutationFailure("没找到 deleteNodeIds 循环里清 activeWorkspaceId 的那行")
    if second not in core:
        raise MutationFailure("没找到 deleteNodeIds 末尾重算 activeWorkspaceId 的那行")
    broken = core.replace(first, "", 1)
    cut = broken.index(second)
    end = broken.index("\n", cut)
    return broken[:cut] + broken[end + 1:], projects


def m_removal_nukes_everything(core: str, projects: str):
    """A filter so wide that deleting a project that is not there wipes the
    canvas anyway. This is the mutation the "nothing to delete" gate exists
    for; the first attempt reused N1's mutation, which produces exactly the
    unchanged node set that gate wants to see, so it proved nothing.
    """
    old = "nodes = nodes.filter(x => !removed.has(x.id));"
    if old not in projects:
        raise MutationFailure("没找到 removeNodes 里的 nodes 重新赋值")
    return core, projects.replace(
        old, "nodes = nodes.filter(x => x.kind !== 'ws');", 1)


def m_the_two_paths_disagree(core: str, projects: str):
    """Make removeNodes drop one node fewer than deleteNodeIds does, so the two
    independently written removal paths stop matching."""
    old = "  function removeNodes(name) {"
    if old not in projects:
        raise MutationFailure("没找到 removeNodes 的定义")
    broken = projects.replace(
        old, "  function removeNodes(name) {\n    name = 'P1' === name ? 'P2' : name;", 1)
    return core, broken


MUTATIONS = [
    ("N1 removeNodes 算出了新数组但没赋回去",
     m_publish_nothing, "test_removing_a_project_leaves_every_holder_agreeing"),
    ("N2 removeNodes 忘了清边",
     m_forget_edges, "test_removing_a_project_leaves_every_holder_agreeing"),
    ("N3 removeNodes 的 kind 过滤被改窄（只删 output）",
     m_filter_too_wide, "test_removing_a_project_leaves_every_holder_agreeing"),
    ("N4 deleteNodeIds 算出了新数组但没赋回去",
     m_kernel_stops_publishing, "test_delete_node_ids_leaves_every_holder_agreeing"),
    ("N5 deleteNodeIds 忘了清边",
     m_kernel_forget_edges, "test_delete_node_ids_leaves_every_holder_agreeing"),
    ("N6 删了工作区却不清 activeWorkspaceId（两条路径都断）",
     m_kernel_leaves_active_workspace_id,
     "test_deleting_the_active_workspace_clears_the_active_id_everywhere"),
    ("N7 两条删除路径结果不一致",
     m_the_two_paths_disagree, "test_both_removal_paths_agree_with_each_other"),
    ("N8 删除不存在的项目却把画布清空了",
     m_removal_nukes_everything,
     "test_removing_a_project_that_is_not_there_changes_nothing"),
]


def main() -> int:
    files = (CORE, PROJECTS)
    original = {p: p.read_text(encoding="utf-8") for p in files}
    backup = Path(tempfile.mkdtemp(prefix="fox-nodes-backup-"))
    for p in files:
        shutil.copy2(p, backup / p.name)

    def restore() -> None:
        for p in files:
            shutil.copy2(backup / p.name, p)

    rows: list[tuple[str, str]] = []
    print("=" * 74)
    print("节点删除观察者门禁 · 变异验证")
    print("=" * 74)
    try:
        clean = _run([])
        if clean.returncode != 0:
            print("基线就红：\n" + clean.stdout[-3000:])
            return 2
        print("基线：全过\n")

        for name, fn, gate in MUTATIONS:
            try:
                c2, p2 = fn(original[CORE], original[PROJECTS])
            except MutationFailure as exc:
                print(f"HARD FAIL  {name}\n          {exc}")
                rows.append((name, "HARD FAIL"))
                restore()
                continue

            if (c2, p2) == (original[CORE], original[PROJECTS]):
                print(f"HARD FAIL  {name}\n          变异没有改变任何内容")
                rows.append((name, "HARD FAIL"))
                continue

            CORE.write_text(c2, encoding="utf-8", newline="")
            PROJECTS.write_text(p2, encoding="utf-8", newline="")
            try:
                proc = _run(["-k", gate])
            finally:
                restore()

            if proc.returncode == 0:
                verdict = "MISSED"
            elif "no tests ran" in proc.stdout:
                verdict = "BROKEN SELECTOR"
            else:
                verdict = "CAUGHT"
            rows.append((name, verdict))
            print(f"{verdict:17} {name}")
    finally:
        restore()
        shutil.rmtree(backup, ignore_errors=True)
        for p in files:
            same = p.read_text(encoding="utf-8") == original[p]
            print(f"  还原 {p.name}: {'一致' if same else '不一致！'}")

    print("=" * 74)
    caught = sum(1 for _, v in rows if v == "CAUGHT")
    bad = [(n, v) for n, v in rows if v != "CAUGHT"]
    print(f"{caught}/{len(rows)} CAUGHT")
    for n, v in bad:
        print(f"  {v}  {n}")
    print("=" * 74)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
