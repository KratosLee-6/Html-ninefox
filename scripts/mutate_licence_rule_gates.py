"""Reverse verification for the licence-rule gates.

Two reverts, and the second one is the interesting case:

  1. restoring the old whole-page rule in the approve path
  2. making `may_carry_verbatim_text` say yes to `reference`

Revert 2 does not touch app.py at all, and a gate that only watched app.py would
stay green. That is the whole point of asserting the two answers match.
"""

from __future__ import annotations

import ast
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
GATE = "tests/test_licence_rule_is_one_rule.py"
APP = "htmlninefox/server/app.py"
INTAKE = "htmlninefox/intake.py"


def make_skeleton(dest: Path) -> None:
    # copytree creates the package directory itself; creating it first here
    # makes it raise FileExistsError on Windows.
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
        "退回整页级的旧规则",
        APP,
        "if not intake.may_carry_verbatim_text(candidate.get(\"license_class\")):",
        "if candidate.get(\"license_class\") == \"inspiration-only\":",
        "test_the_two_paths_never_disagree",
    ),
    (
        "让 may_carry_verbatim_text 对 reference 也放行",
        INTAKE,
        'return str(license_class or "") == "open"',
        'return str(license_class or "") in ("open", "reference")',
        "test_only_open_licence_carries_verbatim_text",
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
    results = []
    for name, rel, old, new, target in REGRESSIONS:
        src = REPO / rel
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
        try:
            ast.parse(unfixed)
        except SyntaxError as exc:
            print(f"HARD FAIL  {name}\n          revert does not compile: {exc}")
            results.append((name, False))
            continue

        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "repo"
            make_skeleton(work)
            (work / rel).write_text(unfixed, encoding="utf-8", newline="")
            code, failed = run_gate(work)
            caught = code != 0 and any(target in f for f in failed)
            print(f"{'CAUGHT' if caught else 'MISSED':>7}  {name}  "
                  f"(exit={code}, {len(failed)} failed)")
            if not caught:
                print(f"        failed: {failed[:5]}")
            results.append((name, caught))

    missed = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(missed)}/{len(results)} reverts caught by the gate")
    return 1 if missed else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())