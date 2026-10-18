"""Mutation-check the success-path smoke suite.

A smoke suite that cannot be shown to fail on broken code is decoration. The
question is not "do the tests pass" but "if the implementation were wrong,
would they notice".

Each mutation breaks a real production path in a throwaway copy; every one of
them must turn a smoke test red. A mutation whose pattern does not match is
reported as NOT APPLIED, never as MISSED — conflating the two is how you end
up declaring a gate invalid when nothing was actually tested.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mutation_support import finish, stale_report  # noqa: E402  (同目录共用诊断层)

sys.stdout.reconfigure(encoding="utf-8")

# This script lives in .codex_tmp/, so the repository root is one level up.
# An earlier version set ROOT = REPO.parent on top of that, which shifted
# every path a further level up and silently copied the previous run's
# leftovers instead of this tree.
REPO = Path(__file__).resolve().parent.parent
ROOT = REPO
GATE = "tests/test_smoke_success_paths.py"

# Scratch trees go to the system temp dir, not into the repo: .codex_tmp/ and
# .tmp/ are both gitignored, so evidence of a failed mutation run could never
# be uploaded from there.
SCRATCH = Path(tempfile.gettempdir()) / "htmlninefox-mutation"

MUTATIONS = [
    # 1. Generator stops closing the document — the v0.6.0 shape, a shell that
    #    "runs" and produces nothing usable.
    ("M1 landing page missing </html>",
     "htmlninefox/generators/_shared.py",
     "</body>\n</html>", "</body>"),
    # 2. Token-driven CSS silently dropped from every artefact.
    ("M2 generator drops the token CSS block",
     "htmlninefox/generators/_shared.py",
     "<style>{base_css(preset, extra_css)}</style>",
     "<style></style>"),
    # 3. A generator returns a stub instead of rendering.
    ("M3 landing generator returns a stub",
     "htmlninefox/generators/landing.py",
     "def render(brief: dict, style: dict, assets: dict) -> str:",
     "def render(brief: dict, style: dict, assets: dict) -> str:\n"
     "    return '<!doctype html><html lang=\"zh-CN\"><head>"
     "<meta charset=\"utf-8\"></head><body></body></html>'"),
    # 4. The analyser reports a size it did not measure.
    ("M4 analyser reports a wrong source_size",
     "htmlninefox/exporting.py",
     '"source_size": html_path.stat().st_size,',
     '"source_size": 0,'),
    # 5. The compatibility score is fabricated.
    ("M5 analyser hard-codes the score",
     "htmlninefox/exporting.py",
     '"compatibility_score":', '"compatibility_score_ignored":'),
    # 6. The intake parser stops collecting headings.
    ("M6 skeleton parser drops headings",
     "htmlninefox/intake.py",
     "elif tag in {\"h1\", \"h2\", \"h3\", \"h4\", \"h5\", \"h6\"}:",
     "elif tag in {\"h1\", \"h2\", \"h3\", \"h4\", \"h5\", \"h6\"} and False:"),
    # 7. The private-address guard is disabled — the v0.6.2-shaped mistake.
    ("M7 SSRF guard disabled",
     "htmlninefox/intake.py",
     "return (not addr.is_global) or addr.is_multicast or addr.is_unspecified",
     "return False"),
    # 8. export stops reporting what it can produce.
    ("M8 runtime stops reporting pdf",
     "htmlninefox/exporting.py",
     'SUPPORTED_FORMATS = ("pdf", "png", "pptx", "docx")',
     'SUPPORTED_FORMATS = ()'),
    # 9. The v0.6.2 shape proper: the whole fetch raises, so the feature is
    #    100% dead while a rejection-only suite stays green. If the smoke
    #    suite cannot catch THIS, it does not solve the problem it was
    #    written for.
    ("M9 outbound fetch always fails (the v0.6.2 shape)",
     "htmlninefox/intake.py",
     "def _default_transport(url: str, headers: dict[str, str], timeout: float,",
     "def _default_transport(url: str, headers: dict[str, str], timeout: float,\n"
     "                       _boom: bool = True):\n"
     "    raise IntakeError(\"intake_fetch_failed\", \"boom\")\n"
     "def _unused_transport(url: str, headers: dict[str, str], timeout: float,"),
]

RESOURCES = ("htmlninefox/example", "htmlninefox/data",
             "htmlninefox/templates", "examples")

# 结构锚点：文字锚点会随源码「同类改动」失效（M8 就死在格式元组从
# ("pdf","png","pptx") 扩到带 docx 的那一次）。这里给它一个能容忍同类
# 改动的正则版本；命中就以它为准，命中不了才报 STALE。
REGEX_ANCHORS: dict[str, tuple[str, str]] = {
    "M8 runtime stops reporting pdf": (
        r'SUPPORTED_FORMATS\s*=\s*\([^)]*\)',
        "SUPPORTED_FORMATS = ()",
    ),
    "M4 analyser reports a wrong source_size": (
        r'"source_size"\s*:\s*[^,\n]+',
        '"source_size": 0',
    ),
}


def prepare(tag: str) -> Path:
    work = SCRATCH / f"smoke-{tag}"
    shutil.rmtree(work, ignore_errors=True)
    (work / "tests").mkdir(parents=True)
    for extra in RESOURCES:
        src = ROOT / extra
        if src.exists():
            shutil.copytree(src, work / extra, dirs_exist_ok=True)
    shutil.copytree(ROOT / "htmlninefox", work / "htmlninefox",
                    dirs_exist_ok=True, ignore=shutil.ignore_patterns(
                        "__pycache__", "*.pyc", ".codex_tmp"))
    shutil.copytree(ROOT / "packaging", work / "packaging",
                    dirs_exist_ok=True, ignore=shutil.ignore_patterns(
                        "__pycache__", "*.pyc"))
    shutil.copytree(ROOT / ".github", work / ".github", dirs_exist_ok=True)
    shutil.copy(ROOT / GATE, work / GATE)
    (work / "conftest.py").write_text(
        "import sys\nfrom pathlib import Path\n"
        "sys.path.insert(0, str(Path(__file__).parent))\n", encoding="utf-8")
    return work


def cleanup(keep: Path) -> None:
    """Remove every scratch tree this run created, except the last one kept
    for inspection when something failed."""
    for path in SCRATCH.glob("smoke-*"):
        if path.is_dir() and path != keep:
            shutil.rmtree(path, ignore_errors=True)


def run(work: Path) -> tuple[int, str]:
    # encoding must be explicit. Without it Python decodes the child's output
    # with the console codepage, which on this machine is GBK, and any Chinese
    # in a test's failure message raises UnicodeDecodeError — after which
    # proc.stdout is None and the next line dies on None.splitlines(). That is
    # not a subtle degradation: the harness crashes instead of reporting, and a
    # crashed harness that previously printed "9/9 caught" is worse than a red
    # one, because it looks like it ran.
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", str(work / GATE), "-q",
         "-p", "no:cacheprovider"],
        capture_output=True, text=True, cwd=str(work), timeout=1200,
        encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    out = proc.stdout or ""
    tail = [l for l in out.splitlines()
            if "passed" in l or "failed" in l or "error" in l]
    return proc.returncode, (tail[-1] if tail else "?")


def main() -> int:
    base = prepare(f"base-{int(time.time())}")
    rc, out = run(base)
    print(f"baseline: {out}  (rc={rc})")
    if rc != 0:
        print("BASELINE RED — the smoke suite does not pass on the real tree")
        print(f"kept for inspection: {base}")
        return 2

    results = []
    last = base
    for i, (label, rel, old, new) in enumerate(MUTATIONS):
        work = prepare(f"{i}-{int(time.time())}")
        last = work
        target = work / rel
        text = target.read_text(encoding="utf-8")

        # 先走结构锚点（正则），再退回文字锚点。两条都不中才算 STALE ——
        # 只有这时才说明「源码里没有这个形态了」，不是「门禁漏了」。
        mutated = None
        regex = REGEX_ANCHORS.get(label)
        if regex:
            candidate, hits = re.subn(regex[0], regex[1], text, count=1)
            if hits:
                mutated = candidate
        if mutated is None and old in text:
            mutated = text.replace(old, new, 1)
        if mutated is None or mutated == text:
            print(stale_report(
                label, rel, regex[0] if regex else old, text,
                reason="文字锚点与结构锚点都没有命中",
                hint="先确认这条功能还在，再把锚点改成结构定位；不要删掉变异换绿。"))
            results.append((label, "STALE", ""))
            shutil.rmtree(work, ignore_errors=True)
            continue

        target.write_text(mutated, encoding="utf-8")
        rc, out = run(work)
        verdict = "CAUGHT" if rc != 0 else "MISSED"
        results.append((label, verdict, out))
        print(f"\n{label}: {verdict}  {out}")
        shutil.rmtree(work, ignore_errors=True)

    cleanup(base)
    return finish(results, total_expected=len(MUTATIONS))


if __name__ == "__main__":
    raise SystemExit(main())
