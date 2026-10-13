"""C7 收口：工作台全局共享状态的声明约束（state.* 不再是无主之地）。

架构审计 C7 的最后一块：六个 lifecycle-*.js 与内核共享一个 `state` 对象，
字面量只声明了一半——`intakeComponents` 在字面量里根本不存在，lifecycle-intake
直接往里塞，palette 的读取方只能写 `(state.intakeComponents || [])` 猜形状。
读取方与写入方之间没有任何编译期约束，写错键名要等用户打开界面才会发现。

现在 fox-core.js 集中声明全部键（声明即默认值），并以只读的 `window.FoxState`
暴露声明的可执行形态。本文件三面夹击：

1. 静态双向：源码里每一次 `state.<key>` 引用都必须对着声明；每一个声明都必须
   真的被引用（防死声明）。
2. 作用域：六个 lifecycle 文件各自必须仍是单个顶层 IIFE——审计里「共享顶层
   作用域」的回归通道直接焊死。
3. 执行：在裸上下文里加载真实脚本链，问活着的对象——运行时键 == 声明键、
   形状正确、FoxState 冻结（核查面不得变成第二条写通道）。

只有执行级断言在跑代码；静态断言明确存在的原因是它能在「键名拼错但恰好
不抛错」的场景下于 CI 拦截，执行级拦不到没被触发的分支。
"""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

STATIC = ROOT / "htmlninefox" / "server" / "static"
CORE = STATIC / "fox-core.js"

# 与 test_action_registry.py 同一份清单：经典脚本链 + 页面本体。
SCANNED = [
    "index.html", "classic.html", "motion-lab.html",
    "fox-core.js",
    "workbench-features.js", "canvas-productivity.js", "lifecycle-intake.js",
    "lifecycle-revisions.js", "lifecycle-generation.js", "lifecycle-exports.js",
    "lifecycle-slides.js", "lifecycle-projects.js", "workbench-ui.js",
    "interaction-system.js", "motion-system.js", "canvas-engine.js",
]

LIFECYCLE = [
    "lifecycle-projects.js", "lifecycle-generation.js", "lifecycle-revisions.js",
    "lifecycle-exports.js", "lifecycle-intake.js", "lifecycle-slides.js",
]

# 在函数体内声明了局部 `state`（影子绑定）的文件。这类文件里的 state.<key>
# 指向局部对象，不参与全局 schema 的静态扫描；允许清单必须双向一致——
# 出现在清单里的文件必须真的有影子，有影子的文件必须出现在清单里，
# 否则一次静默的改名就能把全局引用扫漏。约定：内核的全局声明写在 fox-core.js
# 顶层第 0 列，局部影子一律带缩进——检测只认缩进声明。
# lifecycle-generation.js：每节点的生成状态（generatingNodes.get(n.id)）。
# workbench-ui.js：移动端任务卡的状态徽标字符串。
SHADOWED = {"lifecycle-generation.js", "workbench-ui.js"}

STATE_REF = re.compile(r"\bstate\.([A-Za-z_$][\w$]*)")
LOCAL_STATE_DECL = re.compile(r"^\s+(?:const|let|var)\s+state\s*=", re.M)


def _kernel_mod():
    """Load the sibling kernel test module for its node harness (the 80-line
    DOM stub is not duplicated here; duplicating it would let the two copies
    drift)."""
    spec = importlib.util.spec_from_file_location(
        "kernel_loadable", ROOT / "tests" / "test_frontend_kernel_loadable.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _strip_comments(source: str) -> str:
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
    return re.sub(r"^\s*//.*$", "", source, flags=re.M)


def _state_literal() -> str:
    core = CORE.read_text(encoding="utf-8")
    match = re.search(r"const state = \{(.*?)\n\};", core, re.S)
    assert match, "fox-core.js 里找不到 const state = {...} 声明——全局状态失去声明"
    return match.group(1)


def _declared_keys() -> list[str]:
    """Flat keys of the state literal, at brace depth 1.

    The captured group sits *inside* the literal's opening brace, so the
    parser starts at depth 1. `ai: { enabled: false }` nests to depth 2;
    `enabled` is a shape of the ai value, not a state key. Values at depth 1
    are bare literals (`[]`, `{...}`, `null`, `false`) — no strings to trip
    the scanner.
    """
    keys, depth, token = [], 1, ""
    for ch in _state_literal():
        if ch == "{":
            depth += 1
            token = ""
        elif ch == "}":
            depth -= 1
            token = ""
        elif ch == ":" and depth == 1:
            name = token.strip()
            if re.fullmatch(r"[A-Za-z_$][\w$]*", name):
                keys.append(name)
            token = ""
        elif ch == "," and depth == 1:
            token = ""
        else:
            token += ch
    return sorted(set(keys))


def _used_keys() -> dict[str, list[str]]:
    """Every state.<key> reference in the scanned chain, global state only.

    Files with a local `state` shadow are excluded (their references point at
    the local object); the shadow allowlist itself is gated in both directions.
    """
    used: dict[str, list[str]] = {}
    for name in SCANNED:
        path = STATIC / name
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if name in SHADOWED:
            continue
        for key in STATE_REF.findall(text):
            used.setdefault(key, []).append(name)
    return used


def test_every_state_reference_has_a_declaration():
    used = _used_keys()
    declared = _declared_keys()
    unknown = sorted(set(used) - set(declared))
    assert not unknown, (
        f"源码引用了未声明的全局状态键 {unknown}——写入方与读取方之间没有契约，"
        f"这正是审计 C7 的原始缺陷形态（intakeComponents 曾经就是这样）。"
        f"先在 fox-core.js 的 const state 声明，再使用。"
        f"已声明：{declared}")


def test_every_declaration_is_actually_used():
    declared = _declared_keys()
    used = _used_keys()
    dead = [key for key in declared if key not in used]
    assert not dead, (
        f"声明的全局状态键 {dead} 没有任何引用——死声明让 schema 变成装饰，"
        f"下一次有人读它时不再能相信它描述真实使用面")


def test_the_shadow_allowlist_is_honest():
    for name in SCANNED:
        path = STATIC / name
        if not path.exists():
            continue
        shadows = bool(LOCAL_STATE_DECL.search(path.read_text(encoding="utf-8")))
        if name in SHADOWED:
            assert shadows, (
                f"{name} 在影子允许清单里但已没有局部 state 声明——请把它从"
                f"清单移除，让全局扫描重新覆盖它")
        else:
            assert not shadows, (
                f"{name} 新出现了局部 state 声明——它对全局 schema 的静态扫描"
                f"从此失明。要么改掉局部命名，要么把它显式加入 SHADOWED 并"
                f"说明理由")


def test_lifecycle_files_are_single_top_level_iifes():
    """审计 C7 的原始表述就是「以经典脚本加载、共享顶层作用域」。IIFE 化是
    v0.6.4 之前就完成的事实，这里把它变成不可回退的约束：六个文件剥掉注释后
    必须各自恰好是一个顶层 IIFE，任何顶层 var/let/const/function 泄漏都会
    重新制造跨文件的名字污染。"""
    body_re = re.compile(
        r"^\s*\(?\s*(?:function\s*\(\s*\)\s*\{|\(\s*\)\s*=>\s*\{).*\}\)?\s*\)\s*\(\s*\)\s*;?\s*$",
        re.S)
    for name in LIFECYCLE:
        text = _strip_comments((STATIC / name).read_text(encoding="utf-8")).strip()
        assert text.startswith("("), f"{name} 顶层在 IIFE 之前还有别的语句"
        assert body_re.fullmatch(text), (
            f"{name} 的顶层不再是一个 IIFE——经典脚本共享顶层作用域，"
            f"顶层声明会泄漏给之后加载的所有文件（审计 C7）")


def _node_available():
    try:
        subprocess.run(["node", "--version"], capture_output=True, check=True)
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


@pytest.mark.skipif(not _node_available(), reason="node 不可用")
def test_runtime_state_matches_the_declaration():
    """执行级核查：加载真实脚本链，问活着的 state 对象。

    只 grep 源码拦不住「声明被改成注释」「state 被换成另一个对象」这类
    静态形态不变、运行时已变心的回归；答案从执行后的上下文里读。"""
    kernel = _kernel_mod()
    srcs = kernel._script_srcs()
    names = [s.rsplit("/", 1)[-1] for s in srcs]
    assert "fox-core.js" in names

    driver_tail = r"""
for (const f of JSON.parse(process.argv[3])) {
  if (typeof sandbox[f] === 'undefined') {
    console.log('MISSING:' + f);
    process.exit(4);
  }
}
const fsState = sandbox.FoxState;
console.log('KEYS:' + JSON.stringify(fsState.keys()));
console.log('FROZEN:' + (() => {
  const before = fsState.keys;
  try { fsState.keys = () => ['x']; } catch (e) { /* 严格态抛错，宽松态静默失效 */ }
  return fsState.keys === before ? 'frozen' : 'mutated';
})());
console.log('PROBE:' + JSON.stringify({
  intakeIsArray: Array.isArray(fsState.value('intakeComponents')),
  templatesIsArray: Array.isArray(fsState.value('templates')),
  aiShape: typeof fsState.value('ai'),
  memoryDefault: fsState.value('memory'),
}));
"""
    d = Path(tempfile.mkdtemp())
    js = d / "driver.js"
    js.write_text(
        "const fs = require('fs');\n"
        "const vm = require('vm');\n"
        "const path = require('path');\n"
        f"const STATIC_DIR = {str(STATIC)!r};\n"
        + kernel._STUB_JS + driver_tail,
        encoding="utf-8")

    proc = subprocess.run(
        ["node", str(js), json.dumps(names), json.dumps(["FoxState"])],
        capture_output=True, text=True, timeout=120,
        encoding="utf-8", errors="replace")
    if proc.returncode in (3, 4) or "LOAD_ERROR" in proc.stdout or "MISSING:" in proc.stdout:
        pytest.fail(f"脚本链加载失败：{proc.stdout.strip()[:600]}")
    assert proc.returncode == 0, f"node 失败：{proc.stderr[-600:]}"

    def line(prefix):
        found = next((l for l in proc.stdout.splitlines() if l.startswith(prefix)), None)
        assert found, f"driver 没有回报 {prefix}：{proc.stdout[:400]}"
        return json.loads(found[len(prefix):])

    keys = line("KEYS:")
    assert keys == _declared_keys(), (
        f"运行时 state 键 {keys} != 声明键 {_declared_keys()}——"
        f"声明与对象脱钩，schema 成为装饰")

    frozen = next((l[7:] for l in proc.stdout.splitlines()
                   if l.startswith("FROZEN:")), None)
    assert frozen == "frozen", (
        "FoxState 可被改写——核查面变成了第二条写通道，声明的只读性失效")

    probe = line("PROBE:")
    assert probe["intakeIsArray"] and probe["templatesIsArray"], (
        f"声明键的默认值形状不对：{probe}——声明即默认值的前提是默认值可用")
    assert probe["aiShape"] == "object", f"ai 的默认形状不对：{probe}"
    assert probe["memoryDefault"] is None, f"memory 的默认形状不对：{probe}"
