"""Reverse verification for the push-script gates.

Reverting each half of the fix must turn the gate red:

  * reading the working tree instead of the commit object
  * dropping the blob-sha assertion

The second is the dangerous one, because its absence is completely silent: the
tree is built from whatever sha the API returned, the ref moves, and the wrong
content is published behind a green CI run.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GATE = "tests/test_push_via_api.py"
TARGET = "scripts/push_via_api.py"


def make_skeleton(dest: Path) -> None:
    """Only the two files the gate imports — this repo holds ~178k files."""
    (dest / "tests").mkdir(parents=True)
    (dest / "scripts").mkdir(parents=True)
    shutil.copy2(REPO / GATE, dest / "tests" / Path(GATE).name)
    shutil.copy2(REPO / TARGET, dest / "scripts" / Path(TARGET).name)
    # The gate imports `scripts.push_via_api`; the test creates its own git
    # repos in tmp_path, so no other package file is needed.
    (dest / "scripts" / "__init__.py").write_text("", encoding="utf-8")


REGRESSIONS = [
    (
        "退回从工作区读内容",
        """    proc = subprocess.run(
        ["git", "cat-file", "blob", f"{commit}:{path}"],
        cwd=root or ROOT, capture_output=True,
    )
    if proc.returncode != 0:
        return b""
    return proc.stdout""",
        """    target = (root or ROOT) / path
    return target.read_bytes() if target.exists() else b\"\"""",
        "test_upload_blob_sends_the_committed_bytes",
    ),
    (
        "去掉 blob sha 断言",
        """    if blob["sha"] != local_blob:
        raise BlobMismatch(
            f"{path}: git says {local_blob[:7]}, the API says {blob['sha'][:7]}")
    return blob["sha"]""",
        """    return blob["sha"]""",
        "test_upload_blob_raises_when_the_api_sha_disagrees",
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
            # A revert that does not compile never exercised the gate; pytest
            # reports that as exit 2 during collection, which looks like
            # "nothing failed" to anything reading only the exit code.
            import ast
            try:
                ast.parse(unfixed)
            except SyntaxError as exc:
                print(f"HARD FAIL  {name}\n          revert does not compile: {exc}")
                results.append((name, False))
                continue
            (work / TARGET).write_text(unfixed, encoding="utf-8", newline="")
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