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
GATE = "tests/test_page_blocks_from_candidate.py"

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
        cwd=ROOT, capture_output=True, text=True, timeout=900,
        encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"})


def m_back_to_a_flat_regex(intake: str, core: str, feat: str, doc: str):
    """The first version: a flat finditer, where <main> swallows every <section>
    inside it. The feature still "works" — it returns blocks — and delivers one
    useless summary instead of a decomposition."""
    old = "        nested = _innermost_sections(match.group(3), depth + 1)\n        records.extend(nested or [_section_record(match)])"
    if old not in intake:
        raise MutationFailure("没找到 _innermost_sections 里的递归那一行")
    new = "        records.append(_section_record(match))"
    return intake.replace(old, new, 1), core, feat, doc


def m_carry_text_regardless_of_licence(intake: str, core: str, feat: str, doc: str):
    """The copyright rule undone: every page hands over its prose."""
    old = '    may_carry_text = licence == "open"'
    if old not in intake:
        raise MutationFailure("没找到 may_carry_text 的判定")
    return intake.replace(old, "    may_carry_text = True", 1), core, feat, doc


def m_mislabel_the_provenance(intake: str, core: str, feat: str, doc: str):
    """The text is still carried, but the block claims to be structure only —
    the renderer and any future filter both trust the label."""
    old = '            "provenance": "verbatim" if may_carry_text else "structure_only",'
    if old not in intake:
        raise MutationFailure("没找到 provenance 的赋值")
    return intake.replace(old, '            "provenance": "structure_only",', 1), core, feat, doc


def m_break_the_section_regex(intake: str, core: str, feat: str, doc: str):
    """The backreference written as a raw string — two backslashes, matches
    nothing, and the extractor returns zero sections with no error at all."""
    old = 'chr(60) + "/" + "\\\\1" + chr(62)'
    if old not in intake:
        raise MutationFailure("没找到反向引用那一段")
    return intake.replace(old, 'chr(60) + "/" + r"\\\\1" + chr(62)', 1), core, feat, doc


def m_drop_the_ordinal(intake: str, core: str, feat: str, doc: str):
    """Sections come back but in the wrong order: the page's own sequence is
    the one piece of structure that survives re-rendering."""
    old = '            "ordinal": ordinal,'
    if old not in intake:
        raise MutationFailure("没找到 ordinal 的赋值")
    return intake.replace(old, "            \"ordinal\": 0,", 1), core, feat, doc


def m_renderer_goes_back_to_matching_the_id_only(intake: str, core: str,
                                                 feat: str, doc: str):
    """doc.py matches only the vocabulary id again. A page contributes
    page-section-3, not an entry called "sections", so the document comes out
    empty — which is exactly what happened the first time.

    Parameters are in the same order as the harness's file tuple; the first
    version of this took `doc` first and so edited intake.py while believing it
    was editing the renderer.
    """
    old = '    if "sections" in blocks or page_sections:'
    if old not in doc:
        raise MutationFailure("没找到 doc.render 里的 sections 闸门")
    return intake, core, feat, doc.replace(
        old, '    if "sections" in blocks:', 1)


def m_pipeline_flattens_blocks_again(pipeline_like: str = "", core: str = "",
                                     feat: str = "", doc: str = ""):
    raise MutationFailure("unused")


MUTATIONS = [
    ("P1 退回平面正则（<main> 把内部 section 全吞掉）",
     m_back_to_a_flat_regex, "test_slices_can_be_re_derived_from_the_stored_body"),
    ("P2 不论许可都带正文（版权规则失效）",
     m_carry_text_regardless_of_licence,
     "test_text_is_carried_verbatim_only_for_an_open_licensed_page"),
    ("P3 正文照带但谎称 structure_only",
     m_mislabel_the_provenance,
     "test_text_is_carried_verbatim_only_for_an_open_licensed_page"),
    ("P4 反向引用写成 raw 字符串（静默切不出任何分区）",
     m_break_the_section_regex,
     "test_slices_can_be_re_derived_from_the_stored_body"),
    ("P5 序号全置 0（顺序丢失）",
     m_drop_the_ordinal, "test_blocks_carry_what_a_renderer_needs_and_where_they_came_from"),
    ("P6 渲染器只认词汇表 id（产物为空）",
     m_renderer_goes_back_to_matching_the_id_only,
     "test_blocks_survive_the_pipeline_and_reach_the_page"),
]


def main() -> int:
    files = (INTAKE, CORE, FEATURES, DOC)
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

            texts = dict(zip((INTAKE, CORE, FEATURES, DOC), broken))
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