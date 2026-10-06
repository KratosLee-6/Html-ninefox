"""Mutation check for the block-vocabulary gates.

These gates exist because three copies of the block vocabulary can drift apart
with no failure anywhere. Each mutation below introduces a specific drift and
the matching gate has to go red.

The one that matters most is the last: adding an intent to `_intent` without
adding it to `BLOCKS_BY_INTENT` is a latent KeyError on the next gallery
import, and today nothing in the repository would notice.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "htmlninefox" / "rules.py"
PIPELINE = ROOT / "htmlninefox" / "pipeline.py"
GALLERY = ROOT / "htmlninefox" / "user_gallery.py"
GATE = "tests/test_block_vocabulary_copies.py"

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
        cwd=ROOT, capture_output=True, text=True, timeout=600,
        encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"})


def m_preview_drift(rules_s: str, pipeline_s: str, gallery_s: str):
    """pipeline 的预览词表多一个 section——渲染器不认它，那一段静默消失。"""
    old = '    "doc": ["title", "summary", "sections", "key_points", "table", "conclusion"],\n}\n'
    if old not in pipeline_s:
        raise MutationFailure("没找到 pipeline._PREVIEW_BLOCKS 的 doc 行")
    new = old.replace('"conclusion"]', '"conclusion", "appendix"]')
    return rules_s, pipeline_s.replace(old, new, 1), gallery_s


def m_gallery_drift(rules_s: str, pipeline_s: str, gallery_s: str):
    """user_gallery 覆盖的 intent 词表与权威表不一致。"""
    old = '    "landing": ["nav", "hero", "features", "showcase", "pricing", "faq", "cta_footer"],\n}\n'
    if old not in gallery_s:
        raise MutationFailure("没找到 user_gallery.BLOCKS_BY_INTENT 的 landing 行")
    new = old.replace('"faq"', '"faq", "testimonials"')
    return rules_s, pipeline_s, gallery_s.replace(old, new, 1)


def m_intent_returns_something_unmapped(rules_s: str, pipeline_s: str, gallery_s: str):
    """The real one: _intent starts returning poster, BLOCKS_BY_INTENT has no key.

    `_block_id` would raise KeyError on the next gallery import. This is the
    latent crash that nothing in the repository could see.
    """
    old = "    return \"landing\""
    if old not in gallery_s:
        raise MutationFailure("没找到 user_gallery._intent 的兜底 return \"landing\"")
    return rules_s, pipeline_s, gallery_s.replace(
        old, "    if html_count > 0 and \"poster\" in text:\n        return \"poster\"\n" + old,
        1)


def m_authority_gains_an_intent_the_gallery_does_not_know(rules_s: str,
                                                         pipeline_s: str, gallery_s: str):
    """The authority adds an intent; nobody notices that the other two copies
    never learned about it."""
    old = '    "doc": ["title", "summary", "sections", "key_points", "table", "conclusion"],\n}\n'
    if old not in rules_s:
        raise MutationFailure("没找到 rules._INTENT_BLOCKS 的 doc 行")
    new = old.replace('"conclusion"]', '"conclusion", "faq"]')
    return rules_s.replace(old, new, 1), pipeline_s, gallery_s


MUTATIONS = [
    ("V1 pipeline 的预览词表与权威表漂移",
     m_preview_drift, "test_the_preview_copy_is_identical_to_the_authority"),
    ("V2 user_gallery 覆盖的词表漂移",
     m_gallery_drift, "test_the_gallery_copy_agrees_wherever_it_claims_to_cover"),
    ("V3 _intent 返回一个 BLOCKS_BY_INTENT 里没有的 intent（潜伏 KeyError）",
     m_intent_returns_something_unmapped,
     "test_every_intent_the_gallery_can_infer_is_a_key_it_can_look_up"),
    ("V4 权威表新增 intent 而另两份没跟上",
     m_authority_gains_an_intent_the_gallery_does_not_know,
     "test_the_preview_copy_is_identical_to_the_authority"),
]


def main() -> int:
    files = (RULES, PIPELINE, GALLERY)
    original = {p: p.read_text(encoding="utf-8") for p in files}
    backup = Path(tempfile.mkdtemp(prefix="fox-vocab-backup-"))
    for p in files:
        shutil.copy2(p, backup / p.name)

    def restore() -> None:
        for p in files:
            shutil.copy2(backup / p.name, p)

    rows: list[tuple[str, str]] = []
    print("=" * 74)
    print("blocks 词表副本门禁 · 变异验证")
    print("=" * 74)
    try:
        clean = _run([])
        if clean.returncode != 0:
            print("基线就红：\n" + clean.stdout[-2500:])
            return 2
        print("基线：全过\n")

        for name, fn, gate in MUTATIONS:
            try:
                r2, p2, g2 = fn(original[RULES], original[PIPELINE], original[GALLERY])
            except MutationFailure as exc:
                print(f"HARD FAIL  {name}\n          {exc}")
                rows.append((name, "HARD FAIL"))
                restore()
                continue

            if (r2, p2, g2) == (original[RULES], original[PIPELINE], original[GALLERY]):
                print(f"HARD FAIL  {name}\n          变异没有改变任何内容")
                rows.append((name, "HARD FAIL"))
                continue

            RULES.write_text(r2, encoding="utf-8", newline="")
            PIPELINE.write_text(p2, encoding="utf-8", newline="")
            GALLERY.write_text(g2, encoding="utf-8", newline="")
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
