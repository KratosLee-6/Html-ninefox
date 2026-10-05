"""Mutation check for the C7 step-two gates.

The point of this refactor was that workbench-features.js stopped executing
anything at load time, which is what makes it loadable on its own and stops the
script order in index.html from mattering. Both of those are claims, and a claim
that has never been seen to fail is not evidence.

Every mutation below restores a defect the refactor removed. A gate that stays
green on any of them is not a gate.

Rules this script holds itself to, both learned the hard way:
  * a mutation whose replacement string did not match is a HARD FAILURE, never
    a MISSED. MISSED means "the gate stayed green on broken code"; a mutation
    that never applied is simply untested, and recording it as MISSED would
    manufacture a fake finding.
  * a non-zero pytest exit is not proof the gate went red. "no tests ran" and a
    collection error both exit non-zero while nothing was verified.
"""
from __future__ import annotations

import json
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

FEATURES = ROOT / "htmlninefox" / "server" / "static" / "workbench-features.js"
CORE = ROOT / "htmlninefox" / "server" / "static" / "fox-core.js"
INDEX = ROOT / "htmlninefox" / "server" / "static" / "index.html"
GATE = "tests/test_workbench_features_pure.py"


class MutationFailure(RuntimeError):
    """The mutation did not actually change the file — hard failure."""


def _run(extra: list[str]) -> subprocess.CompletedProcess:
    import os
    return subprocess.run(
        [sys.executable, "-m", "pytest", GATE, *extra,
         "-q", "-p", "no:cacheprovider", "--no-header", "-x"],
        cwd=ROOT, capture_output=True, text=True, timeout=900,
        encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"})


# --- each mutation takes (features, core, index) and returns the broken triple

def m_restore_top_level_palette_patch(feat: str, core: str, index: str):
    """Put one palette assignment back at the file's top level.

    This is the exact shape the refactor removed: a top-level statement that
    touches a kernel object, so the file can no longer be loaded on its own.
    It has to land at column 0 near the top of the file — merely dedenting the
    line inside registerWorkbenchPalette leaves it at brace depth 1, which is
    not a top-level statement at all, and the gate correctly stays green.
    """
    for line in feat.splitlines(keepends=True):
        if "PALETTE.layouts = workbenchPaletteLayouts;" in line:
            return feat.replace(line, "", 1) + "\nPALETTE.layouts = workbenchPaletteLayouts;\n", core, index
    raise MutationFailure("没找到 PALETTE.layouts = workbenchPaletteLayouts;")


def m_restore_top_level_dom_binding(feat: str, core: str, index: str):
    for line in feat.splitlines(keepends=True):
        if "$('#create-modal').addEventListener" in line:
            return feat.replace(line, "", 1) + "\n" + line.strip() + "\n", core, index
    raise MutationFailure("没找到 #create-modal 的 pointerdown 绑定")


def m_drop_the_palette_registration(feat: str, core: str, index: str):
    """The kernel stops wiring the extension in: the palette never gets the
    gallery providers, so the layouts tab silently falls back to built-ins.

    The target is the *indented code line*. The same string also appears inside
    the explanatory comment right above it, and removing that copy changes
    nothing — which is exactly how the first version of this mutation slipped
    through and left a text-shaped gate looking green.
    """
    for line in core.splitlines(keepends=True):
        if line.strip() == "registerWorkbenchPalette?.(PALETTE);":
            return feat, core.replace(line, "", 1), index
    raise MutationFailure("没找到独立成行的 registerWorkbenchPalette?.(PALETTE);")


def m_drop_the_dom_binding_call(feat: str, core: str, index: str):
    for line in core.splitlines(keepends=True):
        if line.strip() == "bindWorkbenchDom?.();":
            return feat, core.replace(line, "", 1), index
    raise MutationFailure("没找到独立成行的 bindWorkbenchDom?.();")


def m_unregister_only_some_palette_slots(feat: str, core: str, index: str):
    """Two of the three providers registered. The layouts tab looks fine and
    the styles tab quietly loses the real gallery — the kind of partial break
    that a boolean flag test would miss."""
    old = "  PALETTE.blocks = workbenchPaletteBlocks;\n"
    if old not in feat:
        raise MutationFailure("没找到 PALETTE.blocks 的注册行")
    return feat.replace(old, ""), core, index


def m_leak_the_gallery_id_out_of_drag_payload(feat: str, core: str, index: str):
    """gallery_id is what ties a dropped template node back to its source.
    Without it the node renders but can never be re-identified."""
    old = "    gallery_id: item.id,"
    if old not in feat:
        raise MutationFailure("没找到 gallery_id: item.id,")
    return feat.replace(old, "    gallery_id: undefined,", 1), core, index


def m_drop_escaping_from_the_memory_summary(feat: str, core: str, index: str):
    """A memory value is user data going into innerHTML. Losing esc() here is
    an injection path, and it is invisible to every other gate in the repo."""
    old = "esc(memoryValueText(item.value))"
    if old not in feat:
        raise MutationFailure("没找到 memorySummaryMarkup 里的 esc(...)")
    return feat.replace(old, "memoryValueText(item.value)", 1), core, index


def m_invert_the_adopted_check(feat: str, core: str, index: str):
    old = "return Boolean(projectName && (state.memory?.evidence || []).some("
    if old not in feat:
        raise MutationFailure("没找到 isProjectAdopted 的实现")
    return feat.replace(old, "return Boolean(projectName && !(state.memory?.evidence || []).some(", 1), core, index


def m_rename_a_pure_helper(feat: str, core: str, index: str):
    old = "function galleryItem(id) {"
    if old not in feat:
        raise MutationFailure("没找到 function galleryItem(id) {")
    return feat.replace(old, "function galleryItemRenamed(id) {", 1), core, index


def m_break_the_load_order_again(feat: str, core: str, index: str):
    """Move the extension file to the front of index.html's script list.

    This is a behaviour *change*, not a defect: after the refactor the page is
    supposed to work in that order too. It lives here because it is the sharpest
    check that the refactor did what it claims — and it is expected to leave
    every gate green. If this ever goes red, the honest reading is "the
    extension file depends on load order again", not "the gate is wrong".

    Note the gate it exercises derives the chain from index.html rather than a
    hard-coded list, so this mutation is actually seen.
    """
    old = '<script src="/workbench-features.js"></script>'
    if old not in index:
        raise MutationFailure("index.html 里找不到 workbench-features.js 的 script 标签")
    return feat, core, index.replace(old + "\n", "").replace(
        '<script src="/canvas-engine.js"></script>',
        old + '\n<script src="/canvas-engine.js"></script>', 1)


def m_register_too_late(feat: str, core: str, index: str):
    """Move the palette registration to after the data load.

    This is the ordering property the gate
    test_the_palette_is_registered_before_the_first_render exists for. The
    registration is still called, so the "did the kernel call it" gate stays
    green; what changes is that loadGallery has already rendered the layouts tab
    with the built-in templates by then.
    """
    call = "  registerWorkbenchPalette?.(PALETTE);\n"
    if call not in core:
        raise MutationFailure("没找到独立成行的 registerWorkbenchPalette?.(PALETTE);")
    stripped = core.replace(call, "", 1)
    anchor = ("  await Promise.all([loadTemplates(), loadGallery(), loadProjects(),"
              " loadAlliance(), loadAISettings(), loadProjectMemory()]);\n")
    if anchor not in stripped:
        raise MutationFailure("没找到 init() 里的 Promise.all 那一行")
    return feat, stripped.replace(anchor, anchor + call, 1), index


MUTATIONS = [
    ("C1 顶层又去改 PALETTE（顺序重新变硬约束）",
     m_restore_top_level_palette_patch,
     "test_features_declares_no_top_level_side_effects"),
    ("C2 顶层又去绑 DOM",
     m_restore_top_level_dom_binding,
     "test_features_declares_no_top_level_side_effects"),
    ("C3 内核不再注册调色板贡献者",
     m_drop_the_palette_registration,
     "test_the_kernel_actually_calls_into_the_extension_layer"),
    ("C4 内核不再调用 DOM 绑定",
     m_drop_the_dom_binding_call,
     "test_the_kernel_actually_calls_into_the_extension_layer"),
    ("C5 三个调色板槽只注册两个（半坏的形状）",
     m_unregister_only_some_palette_slots,
     "test_all_three_palette_slots_are_registered"),
    ("C6 拖拽数据丢掉 gallery_id",
     m_leak_the_gallery_id_out_of_drag_payload,
     "test_gallery_template_data_carries_the_drag_payload"),
    ("C7 记忆摘要忘了转义（注入路径）",
     m_drop_escaping_from_the_memory_summary,
     "test_memory_summary_markup_escapes_the_value_it_echoes"),
    ("C8 isProjectAdopted 判断取反",
     m_invert_the_adopted_check,
     "test_is_project_adopted_answers_from_the_evidence_list"),
    ("C9 纯函数被改名",
     m_rename_a_pure_helper,
     "test_the_pure_helpers_all_exist_as_functions"),
    ("C10 调色板注册被挪到第一次渲染之后",
     m_register_too_late,
     "test_the_palette_is_registered_before_the_first_render"),
]


def main() -> int:
    files = (FEATURES, CORE, INDEX)
    original = {p: p.read_text(encoding="utf-8") for p in files}
    backup = Path(tempfile.mkdtemp(prefix="fox-c7-backup-"))
    for p in files:
        shutil.copy2(p, backup / p.name)

    def restore() -> None:
        for p in files:
            shutil.copy2(backup / p.name, p)

    rows: list[tuple[str, str]] = []
    print("=" * 74)
    print("C7 第二步门禁 · 变异验证")
    print("=" * 74)
    try:
        clean = _run([])
        if clean.returncode != 0:
            print("基线就红，无法做变异验证：")
            print(clean.stdout[-3000:])
            return 2
        print("基线：全过\n")

        for name, fn, gate in MUTATIONS:
            try:
                f2, c2, i2 = fn(original[FEATURES], original[CORE], original[INDEX])
            except MutationFailure as exc:
                print(f"HARD FAIL  {name}\n          {exc}")
                rows.append((name, "HARD FAIL"))
                restore()
                continue

            if (f2, c2, i2) == tuple(original[p] for p in files):
                print(f"HARD FAIL  {name}\n          变异没有改变任何内容")
                rows.append((name, "HARD FAIL"))
                continue

            FEATURES.write_text(f2, encoding="utf-8", newline="")
            CORE.write_text(c2, encoding="utf-8", newline="")
            INDEX.write_text(i2, encoding="utf-8", newline="")
            try:
                proc = _run(["-k", gate])
            finally:
                restore()

            if proc.returncode == 0:
                verdict = "MISSED"
            elif "no tests ran" in proc.stdout or "no tests collected" in proc.stdout:
                # A non-zero exit with nothing collected is not a red gate. It
                # is a broken selector wearing a green gate's clothes.
                verdict = "BROKEN SELECTOR"
            else:
                verdict = "CAUGHT"
            rows.append((name, verdict))
            print(f"{verdict:17} {name}  → {gate}")
    finally:
        restore()
        shutil.rmtree(backup, ignore_errors=True)
        for p in files:
            now = p.read_text(encoding="utf-8")
            was = original[p]
            print(f"  还原 {p.name}: {'一致' if now == was else '不一致！'}")

    print("=" * 74)
    caught = sum(1 for _, v in rows if v == "CAUGHT")
    bad = [(n, v) for n, v in rows if v != "CAUGHT"]
    print(f"{caught}/{len(rows)} CAUGHT")
    if bad:
        print("以下变异没有被有效抓住：")
        for n, v in bad:
            print(f"  {v}  {n}")
    print("=" * 74)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
