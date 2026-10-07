"""Mutation check: the fetcher must work in the shape production calls it.

`_api_intake_fetch` passes only `headers`; every test in test_design_intake.py
except one injects an explicit resolver. Under that regime the suite stays
green while `fetch_reference` crashes with `TypeError: 'NoneType' object is not
callable` on every successful fetch — the post-fetch rebinding check called
`_resolve(host, resolver)` with the raw parameter. That defect shipped in
v0.6.2–v0.6.4 and no gate saw it, because no gate exercised the production
shape. The gate is `test_fetch_succeeds_in_the_production_shape`; the mutation
removes the default and the gate must go red.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTAKE = ROOT / "htmlninefox" / "intake.py"
GATE = ["tests/test_design_intake.py"]

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


class MutationFailure(RuntimeError):
    """The mutation did not change the file — hard failure."""


def _run(extra: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "pytest", *GATE, *extra,
         "-q", "-p", "no:cacheprovider", "--no-header"],
        cwd=ROOT, capture_output=True, text=True, timeout=900,
        encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"})


def m_resolver_stays_none(intake: str):
    """The default never happens: production's resolver=None reaches
    `_resolve` raw and every successful fetch dies at the rebinding check."""
    # 同样的默认值在 validate_url 里也有一份；锚定注释，删的必须是
    # fetch_reference 自己的那一份——删错一份门禁照样绿，那不是门禁
    # 放水，是变异打偏。打偏的变异必须报 HARD FAIL，不能记成 CAUGHT。
    old = ("    # 就是 TypeError —— 传输成功的那一刻必崩。与 validate_url 同一默认。\n"
           "    resolver = resolver or socket.getaddrinfo\n")
    if old not in intake:
        raise MutationFailure("没找到 fetch_reference 的 resolver 默认值（改形状了？）")
    return intake.replace(old, "", 1)


MUTATIONS = [
    ("F1 生产形态的 resolver 默认值被移除（成功抓取瞬间 TypeError）",
     m_resolver_stays_none,
     "test_fetch_succeeds_in_the_production_shape"),
]


def main() -> int:
    files = (INTAKE,)
    original = {p: p.read_text(encoding="utf-8") for p in files}
    backup = Path(tempfile.mkdtemp(prefix="fox-fetch-backup-"))
    for p in files:
        shutil.copy2(p, backup / p.name)

    def restore() -> None:
        for p in files:
            shutil.copy2(backup / p.name, p)

    rows: list[tuple[str, str]] = []
    print("=" * 74)
    print("抓取生产形态门禁 · 变异验证")
    print("=" * 74)
    try:
        clean = _run([])
        if clean.returncode != 0:
            print("基线就红：\n" + clean.stdout[-2500:])
            return 2
        print("基线：全过\n")

        for name, fn, gate in MUTATIONS:
            try:
                broken = fn(original[INTAKE])
            except MutationFailure as exc:
                print(f"HARD FAIL  {name}\n          {exc}")
                rows.append((name, "HARD FAIL"))
                restore()
                continue
            if broken == original[INTAKE]:
                print(f"HARD FAIL  {name}\n          变异没有改变任何内容")
                rows.append((name, "HARD FAIL"))
                continue
            INTAKE.write_text(broken, encoding="utf-8", newline="")
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
