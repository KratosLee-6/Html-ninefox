"""Reverse verification for the every-intent page-sections fix.

Each regression removes one part of the fix in a throwaway copy of the tree and
requires the gate to go red. A green gate against a broken renderer is worse
than no gate, so every case is checked, not assumed.

The tree is copied, not the whole repository: this repo holds ~178k files /
6.5 GB of workspace output, and copying it per case turns a seconds-long check
into minutes that look like a hang.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GATE = "tests/test_page_sections_reach_every_intent.py"
SKIP = shutil.ignore_patterns(
    ".git", "e2e-shots", "e2e-output", "__pycache__", ".pytest_cache",
    "*.png", "*.gif", "*.jpg",
)


# (name, generator file, revert old, revert new, intent whose tests must go red)
#
# The intent — not a specific test function name — is the contract here. A
# revert legitimately turns several gates red at once (removing the vocabulary
# fallback breaks the structure-only AND the no-blocks cases together), and
# pinning one function name reported those as MISSED when the gate had in fact
# caught the regression. That is a false negative in the measuring instrument,
# which is the more expensive kind.
REGRESSIONS = [
    (
        "landing 不再清空 blocks",
        "landing.py",
        "    if page_sections:\n        blocks = []\n",
        "",
        "landing",
    ),
    (
        "deck 不再为页面分块建幻灯片",
        "deck.py",
        "    for i, sec in enumerate(page_sections, start=1):\n"
        "        slides.append(slide(f\"{i:02d}\", page_sections_html(\n"
        "            [sec], section_cls=\"\", item_cls=\"card\")))\n",
        "",
        "deck",
    ),
    (
        "archdoc 不再渲染页面分块",
        "archdoc.py",
        "    if page_sections:\n"
        "        parts.append(page_sections_html(page_sections, section_cls=\"\",\n"
        "                                        item_cls=\"card\"))\n",
        "",
        "archdoc",
    ),
    (
        "block_ids_of 不再丢弃未知 id",
        "_shared.py",
        "    return [v for v in vocabulary if v in present] or vocabulary",
        "    return [v for v in vocabulary if v in present] or []",
        "landing",
    ),
    (
        "block_ids_of 不再回落默认词汇表",
        "_shared.py",
        "    return [v for v in vocabulary if v in present] or vocabulary",
        "    return present",
        "dashboard",
    ),
]


def make_skeleton(dest: Path) -> None:
    """Lay down only what the gate imports.

    Copying the repository per case pulled in 607 MB / 57k files of workspace
    output and took minutes — which reads as a hang, not as a slow test. The
    gate imports `htmlninefox.generators`, so the package and the test file
    are the whole requirement.
    """
    (dest / "tests").mkdir(parents=True)
    shutil.copytree(
        REPO / "htmlninefox", dest / "htmlninefox",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    shutil.copy2(REPO / GATE, dest / "tests" / Path(GATE).name)
    for extra in ("pyproject.toml", "pytest.ini", "setup.cfg"):
        src = REPO / extra
        if src.exists():
            shutil.copy2(src, dest / extra)


def run_gate(work: Path) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", GATE, "-q", "-p", "no:cacheprovider",
         "--no-header", "-rf"],
        cwd=work, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    return proc.returncode, proc.stdout + proc.stderr


def _failed_ids(out: str) -> list[str]:
    """The pytest node ids of the failures, from the short summary."""
    ids = []
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("FAILED "):
            ids.append(line[len("FAILED "):].strip())
    return ids


def main() -> int:
    results = []
    for name, rel, old, new, intent in REGRESSIONS:
        src = REPO / "htmlninefox" / "generators" / rel
        original = src.read_text(encoding="utf-8")
        if old not in original:
            print(f"SKIP  {name}: revert fragment not found in {rel}")
            results.append((name, False))
            continue
        unfixed = original.replace(old, new, 1)
        if unfixed == original:
            print(f"SKIP  {name}: revert did not change the source")
            results.append((name, False))
            continue

        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "repo"
            make_skeleton(work)
            (work / "htmlninefox" / "generators" / rel).write_text(
                unfixed, encoding="utf-8", newline="")
            code, out = run_gate(work)
            failed = _failed_ids(out)
            caught = code != 0 and any(intent in f for f in failed)
            print(f"{'CAUGHT' if caught else 'MISSED':>7}  {name}  "
                  f"(exit={code}, {len(failed)} failed, intent={intent})")
            if not caught:
                print(f"        failed ids: {failed[:8]}")
            results.append((name, caught))

    missed = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(missed)}/{len(results)} reverts caught by the gate")
    return 1 if missed else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())