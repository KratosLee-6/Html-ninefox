"""Reverse verification for the publish-name-collision gates.

Each revert removes one part of the fix and must turn the gate red. The
splice-the-timestamp revert is included because it is the subtlest of the
three: it produces a plausible-looking directory name, so nothing fails loudly.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GATE = "tests/test_publish_name_collision.py"
TARGET = "htmlninefox/pipeline.py"


def make_skeleton(dest: Path) -> None:
    (dest / "tests").mkdir(parents=True)
    shutil.copy2(REPO / GATE, dest / "tests" / Path(GATE).name)
    shutil.copytree(REPO / "htmlninefox", dest / "htmlninefox",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for extra in ("pyproject.toml", "pytest.ini", "setup.cfg"):
        src = REPO / extra
        if src.exists():
            shutil.copy2(src, dest / extra)


REGRESSIONS = [
    (
        "退回把完整名字当时间戳传",
        """    if not (out_dir / name).exists():
        return name
    counter = 2
    candidate = f"{name}-{counter}\"""",
        """    if not (out_dir / name).exists():
        return name
    return _next_project_name(out_dir, name)""",
        "test_no_doubled_prefix_appears_in_any_published_name",
    ),
    (
        "退回按最后一段拆分时间戳",
        """    if not (out_dir / name).exists():
        return name
    counter = 2
    candidate = f"{name}-{counter}"
    while (out_dir / candidate).exists():
        counter += 1
        candidate = f"{name}-{counter}"
    return candidate""",
        """    if not (out_dir / name).exists():
        return name
    stem, _, suffix = name.rpartition("-")
    base = stem if stem and suffix.isdigit() else name
    counter = int(suffix) + 1 if (stem and suffix.isdigit()) else 2
    candidate = f"{base}-{counter}"
    while (out_dir / candidate).exists():
        counter += 1
        candidate = f"{base}-{counter}"
    return candidate""",
        "test_the_timestamp_survives_a_collision",
    ),
    (
        "发布时只试一次（撤掉重试）",
        "    for _ in range(_PUBLISH_ATTEMPTS):",
        # Keeping the `for` and shrinking it to one pass is a real revert of the
        # retry. Removing the loop outright was tried first and left a dangling
        # `continue` — a SyntaxError that made pytest exit 2 during collection,
        # which looks exactly like "the gate caught nothing" if you only read
        # the exit code.
        "    for _ in range(1):",
        "test_publish_gives_up_with_a_message_that_names_the_problem",
    ),
]


def run_gate(work: Path) -> tuple[int, list[str]]:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", GATE, "-q", "-p", "no:cacheprovider",
         "--no-header", "-rf"],
        cwd=work, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    out = proc.stdout + proc.stderr
    failed = [l.strip()[len("FAILED "):] for l in out.splitlines()
              if l.strip().startswith("FAILED ")]
    return proc.returncode, failed


def main() -> int:
    src = REPO / TARGET
    original = src.read_text(encoding="utf-8")
    results = []

    for name, old, new, target in REGRESSIONS:
        if old not in original:
            print(f"SKIP  {name}: revert fragment not found (shape changed?)")
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
            broken_file = work / TARGET
            broken_file.write_text(unfixed, encoding="utf-8", newline="")
            # A revert that does not compile never exercised the gate. pytest
            # reports that as exit 2 during collection, which reads as "nothing
            # failed" if only the exit code is looked at.
            import ast
            try:
                ast.parse(unfixed)
            except SyntaxError as exc:
                print(f"HARD FAIL  {name}\n          revert does not compile: {exc}")
                results.append((name, False))
                continue
            code, failed = run_gate(work)
            caught = code != 0 and any(target in f for f in failed)
            print(f"{'CAUGHT' if caught else 'MISSED':>7}  {name}  "
                  f"(exit={code}, {len(failed)} failed)")
            if not caught:
                print(f"        failed: {failed}")
            results.append((name, caught))

    missed = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(missed)}/{len(results)} reverts caught by the gate")
    return 1 if missed else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())