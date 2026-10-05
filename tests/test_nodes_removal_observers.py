"""Deleting nodes must leave every holder of the array agreeing.

What this is for
----------------
C7's next step is to stop reassigning `nodes` and delete in place instead. There
are two such sites today:

    fox-core.js:1081             deleteNodeIds
    lifecycle-projects.js:58     removeNodes   (via window.FoxProjects.removeNodes)

Reassigning a shared array is the kind of change that looks obviously safe and
is not: any holder that captured the array keeps the old one, and the two views
silently diverge — deleted nodes still counted by the canvas, still persisted,
still drawn. Nothing throws. That is the v0.6.0 shape again, in a data
structure instead of a release.

So this pins the *current, correct* behaviour, and does it by comparing the
holders against each other rather than against a literal list:

    nodes                       the kernel's binding
    workspaceSnapshot()         what gets persisted
    edges                       must not keep dangling references

If a refactor makes one of them disagree with the others, this goes red. That is
the property the in-place rewrite has to preserve, and until it exists there is
nothing to fail against.

What is *not* claimed
--------------------
Checked first, because the question is easy to get wrong in the other
direction: the current code does not have a stale reference. Every place that
appears to snapshot `nodes` is a function-local `nodes.filter(...)` that does not
outlive the call, and the holders that do outlive it are `() => nodes` closures,
which re-read the variable. So this file is not pinning a bug fix — it is
putting a net under a refactor that has not happened yet.

The DOM re-render is deliberately not asserted here: `nodesEl.innerHTML = ''` and
`renderNode` need a real document, and a stubbed one would let a missing re-render
pass. The e2e suite covers the visible result.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "htmlninefox" / "server" / "static"

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Reuse the loader that the extension-layer gates already proved works: it
# loads the real thirteen-file chain from index.html's real script order with a
# DOM stub and shaped fetch responses.
sys.path.insert(0, str(Path(__file__).parent))
from test_workbench_features_pure import (  # noqa: E402
    _CHAIN_LOADER, _RESPONSES, _chain_from_index)

_ARM = r"""
(() => {
  window.__log = [];
  window.__ready = [];
  window.addEventListener = (ev, fn) => {
    if (ev === 'DOMContentLoaded') window.__ready.push(fn);
  };
  window.confirm = () => true;
  return 'armed';
})()
"""

# The node shape is addNode's, not a convenient one: `data` is its own field and
# everything read as `node.data.project_name` lives inside it. A first attempt
# put project_name at the top level, the removal filter matched nothing, and
# removeNodes returned success having deleted nothing — a fixture that reads as
# a passing test and is not one.
_SEED = r"""
(() => {
  const mk = (id, kind, data) => ({
    id: String(id), kind, x: 0, y: 0,
    w: kind === 'ws' ? 880 : (kind === 'output' || kind === 'file') ? 430 : 226,
    h: kind === 'ws' ? 540 : undefined,
    workspaceId: data.workspaceId ?? null,
    title: data.title || '', data,
  });
  nodes = [
    mk(1, 'ws', { title: '工作区 1' }),
    mk(2, 'output', { project_name: 'P1', title: 'P1 产物' }),
    mk(3, 'file', { project_name: 'P1', title: 'P1 文件' }),
    mk(4, 'requirement', { title: '保留的需求', text: 'x' }),
    mk(5, 'output', { project_name: 'P2', title: 'P2 产物' }),
  ];
  edges = [{ from: '2', to: '4' }, { from: '3', to: '4' }];
  // The active workspace has to be set, or the "deleting the active workspace
  // clears the id" test passes without ever entering the scenario: the id
  // starts null, so both guards that null it are no-ops and the assertion sees
  // null either way. A gate that passes because the setup never happened is
  // worse than no gate.
  activeWorkspaceId = '1';
  return 'seeded';
})()
"""

_REPORT = r"""
(() => {
  const snap = (() => {
    try { return workspaceSnapshot(); } catch (e) { return { error: e.message }; }
  })();
  const canvas = (snap && snap.canvas) ? snap.canvas : {};
  return JSON.stringify({
    nodeIds: nodes.map(n => n.id),
    edges: edges.map(e => e.from + '->' + e.to).sort(),
    snapNodeIds: (canvas.nodes || []).map(n => n.id),
    snapEdges: (canvas.edges || []).map(e => e.from + '->' + e.to).sort(),
    activeWorkspaceId: activeWorkspaceId === null ? null : String(activeWorkspaceId),
    snapActiveWorkspaceId: canvas.activeWorkspaceId === null
      ? null : String(canvas.activeWorkspaceId),
  });
})()
"""


def _node_available() -> bool:
    try:
        subprocess.run(["node", "--version"], capture_output=True, check=True)
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


needs_node = pytest.mark.skipif(not _node_available(), reason="node 不可用")


def _drive(actions: list[str]) -> dict:
    """Load the chain, seed, run each action, return the final report."""
    driver = (
        _CHAIN_LOADER
        .replace("  fetch: () => __stub('fetch()'),",
                 "  fetch: (u) => Promise.resolve({ ok: true, status: 200,"
                 " json: () => Promise.resolve(RESPONSES[String(u).split('?')[0]] ?? {}),"
                 " text: () => Promise.resolve('') }),")
        .replace("vm.createContext(sandbox);",
                 _RESPONSES + "\nvm.createContext(sandbox);\n"
                 "  vm.runInContext(" + json.dumps(_ARM) + ", sandbox);")
        + "\nconst run = (src) => vm.runInContext(src, sandbox);\n"
        + f"run({json.dumps(_SEED)});\n"
        + "\n".join(f"run({json.dumps(a)});" for a in actions)
        + "\nconsole.log('REPORT:' + run(" + json.dumps(_REPORT) + "));\n"
    )
    d = Path(tempfile.mkdtemp())
    js = d / "drive.js"
    js.write_text(driver, encoding="utf-8")
    proc = subprocess.run(
        ["node", str(js), str(STATIC), json.dumps(_chain_from_index())],
        capture_output=True, text=True, timeout=180,
        encoding="utf-8", errors="replace")
    if "LOAD_ERROR" in proc.stdout:
        pytest.fail(f"前端链装不上：{proc.stdout.strip()[:500]}")
    line = next((l for l in proc.stdout.splitlines() if l.startswith("REPORT:")), None)
    assert line, f"没有拿到报告：\n{proc.stdout[-800:]}\n{proc.stderr[-400:]}"
    return json.loads(line[7:])


# ------------------------------------------------------------------ removeNodes

@needs_node
def test_removing_a_project_leaves_every_holder_agreeing():
    """删除项目之后，`nodes`、`edges`、持久化快照三者必须说同一件事。"""
    r = _drive(["window.FoxProjects.removeNodes('P1')"])
    assert r["nodeIds"] == ["1", "4", "5"], f"删错节点了：{r['nodeIds']}"
    assert r["edges"] == [], f"留下了悬空的边：{r['edges']}"
    assert r["snapNodeIds"] == r["nodeIds"], (
        f"持久化快照与 nodes 不一致：快照 {r['snapNodeIds']} vs nodes {r['nodeIds']}——"
        f"这正是整体替换会造成的陈旧引用")
    assert r["snapEdges"] == r["edges"], (
        f"快照的边与 edges 不一致：{r['snapEdges']} vs {r['edges']}")


@needs_node
def test_removing_one_project_does_not_take_the_other_one_with_it():
    """P1 被删时 P2 必须完好——过滤条件写宽一点点就会静默连带删除。"""
    r = _drive(["window.FoxProjects.removeNodes('P1')"])
    assert "5" in r["nodeIds"], f"P2 的产物节点被连带删了：{r['nodeIds']}"
    assert "4" in r["nodeIds"], f"无关的需求节点被连带删了：{r['nodeIds']}"
    assert "1" in r["nodeIds"], f"工作区节点被连带删了：{r['nodeIds']}"


@needs_node
def test_removing_a_project_that_is_not_there_changes_nothing():
    """删一个不存在的项目名必须是空操作，而不是把 `removed` 之外的都清掉。"""
    r = _drive(["window.FoxProjects.removeNodes('NOPE')"])
    assert r["nodeIds"] == ["1", "2", "3", "4", "5"], \
        f"删不存在的项目却改了节点集：{r['nodeIds']}"


# ---------------------------------------------------------------- deleteNodeIds

@needs_node
def test_delete_node_ids_leaves_every_holder_agreeing():
    """内核那条删除路径（delNode → deleteNodeIds）也要满足同一个不变量。"""
    r = _drive(["deleteNodeIds(['2', '3'])"])
    assert r["nodeIds"] == ["1", "4", "5"], f"删错节点了：{r['nodeIds']}"
    assert r["edges"] == [], f"留下了悬空的边：{r['edges']}"
    assert r["snapNodeIds"] == r["nodeIds"], (
        f"快照与 nodes 不一致：{r['snapNodeIds']} vs {r['nodeIds']}")
    assert r["snapEdges"] == r["edges"], \
        f"快照的边与 edges 不一致：{r['snapEdges']} vs {r['edges']}"


@needs_node
def test_deleting_the_active_workspace_clears_the_active_id_everywhere():
    """工作区被删时 `activeWorkspaceId` 与快照里的那份必须同时清掉。"""
    r = _drive(["deleteNodeIds(['1'])"])
    assert "1" not in r["nodeIds"], f"工作区没被删掉：{r['nodeIds']}"
    assert r["activeWorkspaceId"] is None, \
        f"内核还指着已删的工作区：{r['activeWorkspaceId']}"
    assert r["snapActiveWorkspaceId"] == r["activeWorkspaceId"], (
        f"快照里的 activeWorkspaceId 与内核不一致："
        f"{r['snapActiveWorkspaceId']} vs {r['activeWorkspaceId']}")


@needs_node
def test_both_removal_paths_agree_with_each_other():
    """同一批节点，走两条删除路径，结果必须一致。

    两条路径是各自独立写的（一个在核心里、一个在 lifecycle 里）。它们今天碰巧
    一致，但没有任何东西要求它们一致——把 `nodes` 改成原地删除时，这正是最容易
    只改一条的地方。
    """
    via_lifecycle = _drive(["window.FoxProjects.removeNodes('P1')"])
    via_kernel = _drive(["deleteNodeIds(['2', '3'])"])
    assert via_lifecycle["nodeIds"] == via_kernel["nodeIds"], (
        f"两条删除路径结果不同：lifecycle {via_lifecycle['nodeIds']} "
        f"vs kernel {via_kernel['nodeIds']}")
    assert via_lifecycle["edges"] == via_kernel["edges"], (
        f"两条删除路径留下的边不同：{via_lifecycle['edges']} vs {via_kernel['edges']}")
