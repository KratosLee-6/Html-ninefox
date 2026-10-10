# -*- coding: utf-8 -*-
"""变异验证：intake 编排回流 handler / 限速器双实例，结构门禁必须变红。

    python scripts/mutate_intake_service_gates.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "htmlninefox" / "server" / "app.py"
SERVICE = ROOT / "htmlninefox" / "server" / "intake_service.py"
GATES = ["tests/test_intake_service_structure.py"]

INLINE_FETCH = '''    def _api_intake_fetch(self, body: dict) -> dict:
        url = str(body.get("url") or "").strip()
        if not url:
            raise StoreError("intake_url_invalid", "url 不能为空", 400)
        intake.validate_url(url)
        _INTAKE_RATE_LIMITER.wait(url)
        evidence = intake.fetch_reference(url, headers={"Accept": "text/html"})
        candidate = intake.extract_candidate(
            evidence, source=self._intake_service()._resolve_source(
                str(body.get("source_id") or "")))
        self._intake_service().candidates().save(candidate, evidence)
        return {"ok": True, "candidate": candidate}'''

DUAL_LIMITER = "import intake as _intake_for_limiter\n_INTAKE_RATE_LIMITER2 = _intake_for_limiter.RateLimiter(default_interval=0.0)\n"

MUTATIONS = [
    ("M1 fetch 编排回流 handler（P1-7 回归）",
     APP,
     "    def _api_intake_fetch(self, body: dict) -> dict:\n"
     "        return self._intake_service().fetch(body)",
     INLINE_FETCH),
    ("M2 handler 造出第二个限速器实例（限速失效）",
     APP,
     "from .intake_service import INTAKE_RATE_LIMITER as _INTAKE_RATE_LIMITER  # noqa: E402",
     DUAL_LIMITER + "from .intake_service import INTAKE_RATE_LIMITER as _INTAKE_RATE_LIMITER  # noqa: E402"),
]


def run_gates() -> int:
    r = subprocess.run([sys.executable, "-m", "pytest", *GATES,
                        "-q", "-p", "no:cacheprovider", "--tb=no"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return r.returncode


def main() -> int:
    originals = {p: p.read_text(encoding="utf-8") for p in (APP, SERVICE)}
    bad: list[str] = []
    try:
        for name, path, old, new in MUTATIONS:
            src = originals[path]
            if old not in src:
                print(f"HARD FAIL 找不到变异目标：{name}")
                bad.append(name)
                continue
            path.write_text(src.replace(old, new, 1), encoding="utf-8")
            code = run_gates()
            verdict = "CAUGHT" if code != 0 else "MISSED"
            print(f"{verdict:8} {name}")
            if code == 0:
                bad.append(name)
            path.write_text(originals[path], encoding="utf-8")
    finally:
        for p, text in originals.items():
            p.write_text(text, encoding="utf-8")
    print(f"\n{len(MUTATIONS) - len(bad)}/{len(MUTATIONS)} CAUGHT"
          + (f"；未抓到：{bad}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
