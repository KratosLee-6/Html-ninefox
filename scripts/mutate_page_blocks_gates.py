"""Mutation check for the page-block wiring.

Three properties, each of which can be undone in a way that fails quietly:

  * the slices are actually cut, including the inner sections a flat regex
    swallows
  * the copyright rule holds — a non-open page contributes structure and no
    prose
  * the blocks reach the document, in the page's own order
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTAKE = ROOT / "htmlninefox" / "intake.py"
CORE = ROOT / "htmlninefox" / "server" / "static" / "fox-core.js"
FEATURES = ROOT / "htmlninefox" / "server" / "static" / "workbench-features.js"
DOC = ROOT / "htmlninefox" / "generators" / "doc.py"
SHARED = ROOT / "htmlninefox" / "generators" / "_shared.py"
GATE = [
    "tests/test_page_blocks_from_candidate.py",
    # P6 lives at the renderer layer, and the pipeline gate above only checked
    # section headings. This one counts the page's prose in the output.
    "tests/test_page_sections_reach_every_intent.py",
]

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


class MutationFailure(RuntimeError):
    """The mutation did not change the file — hard failure."""


def _run(extra: list[str]) -> subprocess.CompletedProcess:
    import os
    return subprocess.run(
        [sys.executable, "-m", "pytest", *GATE, *extra,
         "-q", "-p", "no:cacheprovider", "--no-header"],
        cwd=ROOT, capture_output=True, text=True, timeout=900,
        encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"})


def m_back_to_a_flat_regex(intake: str, core: str, feat: str, doc: str, shared: str):
    """The first version: a flat finditer, where <main> swallows every <section>
    inside it. The feature still "works" — it returns blocks — and delivers one
    useless summary instead of a decomposition.

    The implementation is now span-based (`_section_spans` + a leaf test), so
    the old revert of the recursion line no longer exists. The equivalent
    regression is dropping the leaf test: every span becomes a "section",
    containers swallow their contents, and a section directly inside a section
    is one summary again.
    """
    old = ('        if any(o["start"] > start and o["start"] + len(o["snippet"]) <= end\n'
           '               for j, o in enumerate(spans) if j != i):\n'
           '            continue\n')
    if old not in intake:
        raise MutationFailure(
            "没找到 _innermost_sections 的叶子过滤（切分器改形状了？）\n" + old)
    return intake.replace(old, "", 1), core, feat, doc, shared


def m_carry_text_regardless_of_licence(intake: str, core: str, feat: str, doc: str,
                                        shared: str):
    """The copyright rule undone: every page hands over its prose.

    This used to rewrite `may_carry_text = licence == "open"` in
    page_blocks_from_candidate. That line is gone — the rule moved into the
    shared `may_carry_verbatim_text`, so both paths now ask one function and
    cannot drift apart. Reverting the old line silently matched nothing and
    the case reported HARD FAIL, which is what it should have said: a mutation
    that never applied is not evidence that a gate let something through.

    It attacks the shared rule instead, which is where the decision lives now.
    """
    old = '    return str(license_class or "") == "open"'
    if old not in intake:
        raise MutationFailure(
            "没找到 intake.may_carry_verbatim_text 的判定"
            f"（许可规则改形状了？）\n{old}")
    return (intake.replace(old, '    return str(license_class or "") != ""', 1),
            core, feat, doc, shared)


def m_mislabel_the_provenance(intake: str, core: str, feat: str, doc: str,
                               shared: str):
    """The text is still carried, but the block claims to be structure only —
    the renderer and any future filter both trust the label."""
    old = '            "provenance": "verbatim" if may_carry_text else "structure_only",'
    if old not in intake:
        raise MutationFailure("没找到 provenance 的赋值")
    return intake.replace(old, '            "provenance": "structure_only",', 1), core, feat, doc, shared


def m_break_the_section_pairing(intake: str, core: str, feat: str, doc: str,
                               shared: str):
    """Section tags never close: pairing is gone, so every span runs to EOF and
    the only leaf left is the last tag on the page.

    This used to break the regex backreference — the extractor returned zero
    sections, and the failure was at least total. The pairing now lives in
    `_section_spans`'s stack, and the silent shape is worse: records still come
    back, just one whole-page summary instead of the page's sections.
    """
    old = "        if match.group(1):  # 闭标签"
    if old not in intake:
        raise MutationFailure("没找到 _section_spans 的闭标签分支（配对改形状了？）")
    return intake.replace(old, "        if False:  # 闭标签", 1), core, feat, doc, shared


def m_heading_becomes_the_whole_text_again(intake: str, core: str, feat: str,
                                           doc: str, shared: str):
    """heading = content = the section's text head — the endpoint's own shape
    that made every renderer print each page's prose twice.

    The hand-made fixtures cannot see this: their heading differs from their
    content. Only the gates fed by `page_blocks_from_candidate` itself go red.
    """
    old = ('        heading, content_text = _split_heading(\n'
           '            str(section.get("snippet") or ""), str(section.get("text_head") or ""))\n')
    if old not in intake:
        raise MutationFailure("没找到 _split_heading 的调用（标题拆分改形状了？）")
    new = ('        heading = " ".join(str(section.get("text_head") or "").split())\n'
           '        content_text = heading\n')
    return intake.replace(old, new, 1), core, feat, doc, shared


def m_drop_the_ordinal(intake: str, core: str, feat: str, doc: str, shared: str):
    """Sections come back but in the wrong order: the page's own sequence is
    the one piece of structure that survives re-rendering."""
    old = '            "ordinal": ordinal,'
    if old not in intake:
        raise MutationFailure("没找到 ordinal 的赋值")
    return intake.replace(old, "            \"ordinal\": 0,", 1), core, feat, doc, shared


def m_renderer_goes_back_to_matching_the_id_only(intake: str, core: str,
                                                 feat: str, doc: str,
                                                 shared: str):
    """doc.py stops honouring the vocabulary fallback and matches ids only.

    The document comes out empty — which is exactly what happened the first
    time: a page contributes `page-section-3`, not an entry called "sections",
    so matching the vocabulary id alone rendered nothing.

    This used to revert the `if "sections" in blocks or page_sections:` gate in
    doc.render. That line no longer exists: `block_ids_of` moved the fallback
    into the shared layer, so the old revert silently matched nothing and the
    case was reported MISSED — a mutation that never applied, which must never
    be recorded as "the gate let it through".

    The mutation now targets the shared helper instead, which is where that
    decision lives now.

    Parameters are in the same order as the harness's file tuple
    (INTAKE, CORE, FEATURES, DOC, SHARED). Naming them all explicitly is
    deliberate: `shared: str` first turned this into a HARD FAIL that looked
    like a missing pattern, when the real problem was the order.
    """
    old = "    return [v for v in vocabulary if v in present] or vocabulary"
    if old not in shared:
        raise MutationFailure(
            f"没找到 _shared.block_ids_of 里的回落（回落已改形状？）\n{old}")
    return intake, core, feat, doc, shared.replace(
        old, "    return [v for v in vocabulary if v in present]", 1)


def m_pipeline_flattens_blocks_again(pipeline_like: str = "", core: str = "",
                                     feat: str = "", doc: str = ""):
    raise MutationFailure("unused")


MUTATIONS = [
    ("P1 退回平面正则（<main> 把内部 section 全吞掉）",
     m_back_to_a_flat_regex, "test_sections_directly_nested_are_yielded_as_leaves"),
    ("P2 不论许可都带正文（版权规则失效）",
     m_carry_text_regardless_of_licence,
     "test_text_is_carried_verbatim_only_for_an_open_licensed_page"),
    ("P3 正文照带但谎称 structure_only",
     m_mislabel_the_provenance,
     "test_text_is_carried_verbatim_only_for_an_open_licensed_page"),
    ("P4 配对失效（闭标签被无视，整页只剩一条摘要）",
     m_break_the_section_pairing,
     "test_slices_can_be_re_derived_from_the_stored_body"),
    ("P5 序号全置 0（顺序丢失）",
     m_drop_the_ordinal, "test_blocks_carry_what_a_renderer_needs_and_where_they_came_from"),
    ("P6 渲染器只认词汇表 id（产物为空）",
     m_renderer_goes_back_to_matching_the_id_only,
     # This used to point at test_blocks_survive_the_pipeline_and_reach_the_page.
     # That gate only asserted the section HEADINGS appeared, so dropping the
     # vocabulary fallback left doc's own `or page_sections` branch still
     # emitting them — the gate stayed green while the behaviour it was
     # written for had gone. The every-intent gate counts the page's PROSE and
     # asserts it appears exactly once, which is the property P6 removes.
     "test_structure_only_page_falls_back_to_the_built_in_copy"),
    ("P7 heading 重新等于整段正文（每个 intent 渲染两遍）",
     m_heading_becomes_the_whole_text_again,
     "test_blocks_from_the_real_endpoint_render_each_prose_once"),
]


def main() -> int:
    # _shared.py joins the tuple because P6 mutates it directly. Leaving it out
    # of the backup would strand a mutation in production source after the run.
    files = (INTAKE, CORE, FEATURES, DOC, SHARED)
    original = {p: p.read_text(encoding="utf-8") for p in files}
    backup = Path(tempfile.mkdtemp(prefix="fox-pageblocks-backup-"))
    for p in files:
        shutil.copy2(p, backup / p.name)

    def restore() -> None:
        for p in files:
            shutil.copy2(backup / p.name, p)

    rows: list[tuple[str, str]] = []
    print("=" * 74)
    print("页面分块接线门禁 · 变异验证")
    print("=" * 74)
    try:
        clean = _run([])
        if clean.returncode != 0:
            print("基线就红：\n" + clean.stdout[-2500:])
            return 2
        print("基线：全过\n")

        for name, fn, gate in MUTATIONS:
            try:
                broken = fn(*(original[p] for p in files))
            except MutationFailure as exc:
                print(f"HARD FAIL  {name}\n          {exc}")
                rows.append((name, "HARD FAIL"))
                restore()
                continue

            # Zip against `files`, not a hand-written tuple: when _shared.py
            # joined the tuple, the hard-coded four-path version raised KeyError
            # on it — a harness crash that reads like a broken mutation.
            texts = dict(zip(files, broken))
            if all(texts[p] == original[p] for p in files):
                print(f"HARD FAIL  {name}\n          变异没有改变任何内容")
                rows.append((name, "HARD FAIL"))
                continue

            for path, text in texts.items():
                path.write_text(text, encoding="utf-8", newline="")
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