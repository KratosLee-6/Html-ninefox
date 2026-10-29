"""E8：网上资源进料 → 人审采纳 → 拆块全链实录（v0.8.4 Agent帖补证）。

产线补全最后一段：URL 抓取（许可三档）→ 人审采纳 → 拆成带出处的块。
证据进帖内 配图/assets/。
"""
from __future__ import annotations

import json
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from tests.conftest import WorkbenchServer  # noqa: E402

DST = ROOT / "scripts" / "assets"   # 证据落仓库 scripts/assets，发布物另行拷贝
LOG: list[str] = []


def say(line: str) -> None:
    print(line)
    LOG.append(line)


def main() -> int:
    DST.mkdir(parents=True, exist_ok=True)
    with WorkbenchServer(Path(tempfile.mkdtemp())) as server:
        def call(path: str, body=None):
            data = json.dumps(body).encode() if body is not None else None
            req = urllib.request.Request(
                server.base_url + path, data=data,
                headers={"Content-Type": "application/json"},
                method="POST" if body is not None else "GET")
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.load(r)

        t0 = time.time()
        c = call("/api/intake/fetch", {"url": "https://docs.python.org/3/tutorial/index.html"})
        cid = c["candidate"]["candidate_id"]
        say(f"E8a fetch  {time.time() - t0:.1f}s → {cid} · 许可 {c['candidate']['license_class']}"
            f" · 状态 {c['candidate']['status']} · body 哈希 {c["candidate"]["body_sha256"][:16]}…")

        t1 = time.time()
        approved = call(f"/api/intake/candidates/{cid}/approve", {})
        say(f"E8b approve  {time.time() - t1:.1f}s → ok={approved.get('ok')}")

        t2 = time.time()
        b = call("/api/intake/page-blocks", {"candidate_id": cid})
        blocks = b.get("blocks") or []
        say(f"E8c page-blocks  {time.time() - t2:.1f}s → {len(blocks)} 块")
        for blk in blocks[:4]:
            say(f"    {blk.get('kind')} | {str(blk.get('heading') or blk.get('content'))[:44]} "
                f"| {blk.get('provenance')}")
        say(f"    limitations: {(b.get('limitations') or ['-'])[:2]}")

        (DST / "evidence-intake.json").write_text(
            json.dumps({"candidate_id": cid,
                        "license_class": c["candidate"]["license_class"],
                        "body_sha256": c["candidate"]["body_sha256"],
                        "blocks_count": len(blocks),
                        "sample_blocks": blocks[:4],
                        "limitations": b.get("limitations")},
                       ensure_ascii=False, indent=1)[:2500], encoding="utf-8")

    (DST / "会话实录.txt").open("a", encoding="utf-8").write("\n" + "\n".join(LOG))
    print("\nE8 证据已入帖内 assets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
