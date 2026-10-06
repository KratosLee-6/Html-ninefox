"""Mutation check: can this gate actually see the three incidents it exists for?

A gate written to catch drift is worth nothing until each historical incident
is replayed against it. The three:

  C1 a static file exists but is missing from a hand-maintained list — the
     test_action_registry SCANNED case, which shrank its own coverage and stayed
     green
  C2 a hand-maintained list names a file that no longer exists — the
     verify_portable CONTENT_EXPECTATIONS case, which failed a correct package
     at release time
  C3 a list names a route the server does not serve

Each is applied by editing the real file, and the gate has to go red.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "tests" / "test_action_registry.py"
PORTABLE = ROOT / "packaging" / "verify_portable.py"
APP = ROOT / "htmlninefox" / "server" / "app.py"
CORE = ROOT / "htmlninefox" / "server" / "static" / "fox-core.js"
GATE = "tests/test_hand_maintained_lists.py"

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


# --- each mutation takes the four files' current text and returns broken text

def m_list_missing_a_file_that_exists(reg, port, app, core):
    """C1, replayed. Drop fox-core.js from SCANNED — the exact shape of the
    original incident, where the gate scanned one file fewer and stayed green."""
    old = '    "workbench-features.js", "canvas-productivity.js",'
    if old not in reg:
        raise MutationFailure("没找到 SCANNED 里的相邻两行")
    return reg.replace(old, '    "workbench-features.js",', 1), port, app, core


def m_list_names_a_file_that_is_gone(reg, port, app, core):
    """C2, replayed. Assert a static file that does not exist."""
    old = 'STATIC_ROUTES = ("/workbench-system.css",'
    if old not in port:
        raise MutationFailure("没找到 verify_portable 的 STATIC_ROUTES")
    return reg, port.replace(old, 'STATIC_ROUTES = ("/gone-since-refactor.js",', 1), app, core


def m_route_is_not_served(reg, port, app, core):
    """C3. A route alias that the server does not serve — fetching it yields a
    404 and the failure reads as "stale artefact".

    Deliberately written without an asset suffix. The first attempt used
    "/not-a-route.js", which is a *file* by this gate's classification, so it
    was tested by the dangling check and the route check never saw it.
    """
    old = 'STATIC_ROUTES = ("/workbench-system.css",'
    new = 'STATIC_ROUTES = ("/not-a-real-route",'
    if old not in port:
        raise MutationFailure("没找到 verify_portable 的 STATIC_ROUTES")
    return reg, port.replace(old, new, 1), app, core


def m_new_static_file_is_never_registered(reg, port, app, core):
    """The v0.6.0 shape: a file lands in static/ and nothing serves it.

    This one has to actually create a file. Appending CSS to fox-core.js — which
    is what the first attempt did — leaves the set of filenames untouched, so
    an orphan check has nothing to notice.
    """
    return reg, port, app, core, "brand-new-file.css"


def m_exhaustive_list_shrinks(reg, port, app, core):
    """And the coverage direction, using the real current text.

    Drop canvas-productivity.js from SCANNED without touching static/ — which is
    what actually happened, and what nothing noticed.
    """
    old = '    "workbench-features.js", "canvas-productivity.js", "lifecycle-intake.js",'
    if old not in reg:
        raise MutationFailure("没找到 SCANNED 里那三个文件同行的那一行")
    new = '    "workbench-features.js", "lifecycle-intake.js",'
    return reg.replace(old, new, 1), port, app, core


MUTATIONS = [
    ("L1 清单漏收一个存在的文件（原事故形状：扫描范围静默缩小）",
     m_list_missing_a_file_that_exists,
     "test_declared_exhaustive_lists_have_not_fallen_behind"),
    ("L2 清单指向一个已不存在的文件（原事故形状：发布时挡住好产物）",
     m_list_names_a_file_that_is_gone,
     "test_no_entry_in_a_hand_maintained_list_dangles"),
    ("L3 清单引用了服务端不伺服的路由",
     m_route_is_not_served,
     "test_route_shaped_entries_are_actually_served"),
    ("L4 新增的静态文件没人伺服（v0.6.0 形状）",
     m_new_static_file_is_never_registered,
     "test_every_static_file_is_either_served_or_declared"),
    ("L5 完备清单少了一项（fox-core 之外的那条）",
     m_exhaustive_list_shrinks,
     "test_declared_exhaustive_lists_have_not_fallen_behind"),
]


def main() -> int:
    files = (REGISTRY, PORTABLE, APP, CORE)
    original = {p: p.read_text(encoding="utf-8") for p in files}
    backup = Path(tempfile.mkdtemp(prefix="fox-lists-backup-"))
    for p in files:
        shutil.copy2(p, backup / p.name)

    def restore() -> None:
        for p in files:
            shutil.copy2(backup / p.name, p)

    rows: list[tuple[str, str]] = []
    created: list[Path] = []
    print("=" * 74)
    print("手工清单门禁 · 变异验证（三次历史事故逐一重放）")
    print("=" * 74)
    try:
        clean = _run([])
        if clean.returncode != 0:
            print("基线就红：\n" + clean.stdout[-2500:])
            return 2
        print("基线：全过\n")

        for name, fn, gate in MUTATIONS:
            try:
                result = fn(*(original[p] for p in files))
            except MutationFailure as exc:
                print(f"HARD FAIL  {name}\n          {exc}")
                rows.append((name, "HARD FAIL"))
                restore()
                continue

            if len(result) == 5:
                r2, p2, a2, c2, new_file = result
            else:
                r2, p2, a2, c2 = result
                new_file = None

            unchanged = (r2, p2, a2, c2) == tuple(original[p] for p in files) and not new_file
            if unchanged:
                print(f"HARD FAIL  {name}\n          变异没有改变任何内容")
                rows.append((name, "HARD FAIL"))
                continue

            REGISTRY.write_text(r2, encoding="utf-8", newline="")
            PORTABLE.write_text(p2, encoding="utf-8", newline="")
            APP.write_text(a2, encoding="utf-8", newline="")
            CORE.write_text(c2, encoding="utf-8", newline="")
            if new_file:
                target = CORE.parent / new_file
                target.write_text("/* added, never registered */\n", encoding="utf-8")
                created.append(target)
            try:
                proc = _run(["-k", gate])
            finally:
                restore()
                for path in created:
                    if path.exists():
                        path.unlink()
                created.clear()

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
        for path in created:
            if path.exists():
                path.unlink()
        shutil.rmtree(backup, ignore_errors=True)
        for p in files:
            same = p.read_text(encoding="utf-8") == original[p]
            print(f"  还原 {p.name}: {'一致' if same else '不一致！'}")
        stray = sorted(q.name for q in (CORE.parent).glob("brand-new-file.css"))
        if stray:
            print(f"  ⚠ 变异文件残留：{stray}")

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