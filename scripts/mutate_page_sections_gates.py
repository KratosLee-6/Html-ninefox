"""Mutation check for the page-section channel.

The claim is that a page's sections now reach the generated page, and that the
change did not alter what existing projects render. Both directions need
proving: a mutation that puts the flattening back, and a mutation that makes
the new channel do nothing.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "htmlninefox" / "pipeline.py"
SHARED = ROOT / "htmlninefox" / "generators" / "_shared.py"
DOC = ROOT / "htmlninefox" / "generators" / "doc.py"
GATE = "tests/test_page_sections_reach_output.py"

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


def m_flatten_blocks_again(pipe: str, shared: str, doc: str):
    """The original defect: str() every block, so structure becomes a repr."""
    old = "        if isinstance(block, str):\n            value = block.strip()\n            key = value\n        elif isinstance(block, dict):"
    if old not in pipe:
        raise MutationFailure("没找到 _normalize_blocks 的分支")
    new = ("        if isinstance(block, str):\n            value = block.strip()\n"
           "            key = value\n        elif isinstance(block, dict):\n"
           "            value = str(block).strip()\n            key = value\n        if False:")
    return pipe.replace(old, new, 1), shared, doc


def m_blocks_of_drops_dict_ids(pipe: str, shared: str, doc: str):
    """blocks_of stops reducing a dict to its id, so every membership check in
    the six renderers misses it and a page-derived project renders nothing."""
    old = '        elif isinstance(block, dict) and block.get("id"):\n            out.append(str(block["id"]))'
    if old not in shared:
        raise MutationFailure("没找到 blocks_of 的 dict 分支")
    return pipe, shared.replace(old, "        else:\n            pass", 1), doc


def m_sections_of_returns_nothing(pipe: str, shared: str, doc: str):
    """The channel exists but carries nothing — the plumbing works and the user
    still sees the built-in copy."""
    old = "    return [b for b in (assets.get(\"blocks\") or [])\n            if isinstance(b, dict) and b.get(\"content\")]"
    if old not in shared:
        raise MutationFailure("没找到 sections_of 的实现")
    return pipe, shared.replace(old, "    return []", 1), doc


def m_doc_ignores_page_sections(pipe: str, shared: str, doc: str):
    """doc.py keeps its own copy regardless — the channel is plumbed end to end
    and nothing consumes it."""
    old = "        if page_sections:"
    if old not in doc:
        raise MutationFailure("没找到 doc.render 里的 page_sections 分支")
    return pipe, shared, doc.replace(old, "        if False:", 1)


def m_doc_empties_the_built_in_copy(pipe: str, shared: str, doc: str):
    """A project asks for key_points, the page supplies none, and the built-in
    copy comes out empty.

    Two earlier versions of this were no-ops and the gate correctly stayed
    green. Disabling the page branch changes nothing when there are no page
    sections, because the `else` runs either way. What actually distinguishes
    the cases is emptying the fallback itself.
    """
    old = '[("3 阶段", "实施路径"), ("8 周", "整体周期"), ("5 项", "关键交付物")]'
    if old not in doc:
        raise MutationFailure("没找到 doc.render 里 key_points 的内置文案")
    return pipe, shared, doc.replace(old, "[]", 1)


def m_drop_the_id_from_the_payload(pipe: str, shared: str, doc: str):
    """The id is kept out of the dict, so a renderer that wants both the id and
    the content has to reach back into the enclosing structure."""
    old = '            value = {"id": identifier, **value}'
    if old not in pipe:
        raise MutationFailure("没找到 _normalize_blocks 里写回 id 的那行")
    return pipe.replace(old, "            value = dict(value)", 1), shared, doc


MUTATIONS = [
    ("P1 又把 block 压成字符串（原缺陷）",
     m_flatten_blocks_again, "test_a_structured_block_survives_the_pipeline"),
    ("P2 blocks_of 不再从 dict 取 id",
     m_blocks_of_drops_dict_ids, "test_membership_checks_still_see_a_dict_block_s_id"),
    ("P3 sections_of 什么都不返回",
     m_sections_of_returns_nothing, "test_the_sections_reader_returns_only_the_structured_ones"),
    ("P4 doc.py 无视页面分块（通道通了但没人用）",
     m_doc_ignores_page_sections,
     "test_doc_renders_the_pages_own_sections_when_they_are_there"),
    ("P5 内置兜底文案被掏空（页面只给部分分块时）",
     m_doc_empties_the_built_in_copy,
     "test_a_page_section_does_not_suppress_the_built_in_copy_of_other_kinds"),
    ("P6 id 没写回 payload",
     m_drop_the_id_from_the_payload, "test_a_structured_block_survives_the_pipeline"),
]


def main() -> int:
    files = (PIPELINE, SHARED, DOC)
    original = {p: p.read_text(encoding="utf-8") for p in files}
    backup = Path(tempfile.mkdtemp(prefix="fox-sections-backup-"))
    for p in files:
        shutil.copy2(p, backup / p.name)

    def restore() -> None:
        for p in files:
            shutil.copy2(backup / p.name, p)

    rows: list[tuple[str, str]] = []
    print("=" * 74)
    print("页面分块通道门禁 · 变异验证")
    print("=" * 74)
    try:
        clean = _run([])
        if clean.returncode != 0:
            print("基线就红：\n" + clean.stdout[-2500:])
            return 2
        print("基线：全过\n")

        for name, fn, gate in MUTATIONS:
            try:
                p2, s2, d2 = fn(original[PIPELINE], original[SHARED], original[DOC])
            except MutationFailure as exc:
                print(f"HARD FAIL  {name}\n          {exc}")
                rows.append((name, "HARD FAIL"))
                restore()
                continue

            if (p2, s2, d2) == tuple(original[p] for p in files):
                print(f"HARD FAIL  {name}\n          变异没有改变任何内容")
                rows.append((name, "HARD FAIL"))
                continue

            PIPELINE.write_text(p2, encoding="utf-8", newline="")
            SHARED.write_text(s2, encoding="utf-8", newline="")
            DOC.write_text(d2, encoding="utf-8", newline="")
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
