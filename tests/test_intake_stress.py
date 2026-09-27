"""V0.6-S16: absorption stress — 100 candidates incl. malformed bodies."""

from __future__ import annotations

import time
from pathlib import Path

from htmlninefox import intake
from htmlninefox.intake import CandidateStore, IntakeError


def _evidence(index: int, body: bytes) -> dict:
    return {
        "url": f"https://example.com/page-{index}",
        "final_url": f"https://example.com/page-{index}",
        "followed": [], "status": 200, "content_type": "text/html",
        "body": body, "body_sha256": f"{index:064d}",
        "body_bytes": len(body), "fetched_at": "2026-09-28T00:00:00",
    }


MALFORMED_BODIES = [
    b"<html><head><title>unclosed",
    b"<<<<>>>",
    b"\x00\x01\x02 binary junk",
    b"<html><body>" + b"<div>" * 5000,
    b"",
]


def test_hundred_candidates_stress(tmp_path: Path) -> None:
    store = CandidateStore(tmp_path)
    source = {"id": "land-book", "kind": "gallery", "license_class": "reference"}
    started = time.perf_counter()
    created = 0
    for index in range(100):
        body = SAMPLE_HTML if index % 5 else MALFORMED_BODIES[index % len(MALFORMED_BODIES)]
        evidence = _evidence(index, body)
        candidate = intake.extract_candidate(evidence, source=source)
        store.save(candidate, evidence)
        created += 1
    elapsed_create = time.perf_counter() - started
    assert created == 100

    started = time.perf_counter()
    pending = store.list("pending")
    elapsed_list = time.perf_counter() - started
    assert len(pending) == 100
    # 列表/筛选在 100 候选规模下必须亚秒级（工作台交互底线）
    assert elapsed_list < 1.0, f"list too slow: {elapsed_list:.2f}s"

    # 畸形页面也不影响候选可用性（title 兜底为 URL）
    sample_ids = {item["candidate_id"] for item in pending}
    assert sum(1 for cid in sample_ids if cid.startswith("example.com")) == 100
    print(f"stress: create {elapsed_create:.2f}s, list {elapsed_list * 1000:.0f}ms for 100 candidates")


SAMPLE_HTML = (b"<!doctype html><html><head><title>Stress Page</title></head>"
               b"<body><main><h1>s</h1></main></body></html>")


def test_candidate_ids_reject_path_traversal(tmp_path: Path) -> None:
    store = CandidateStore(tmp_path)
    for attack in ("../escape", "..%2Fescape", "a/../b", ".hidden", "", "a" * 200):
        try:
            store.body(attack)
        except IntakeError as error:
            assert error.code in {"intake_candidate_invalid", "intake_candidate_missing"}
        else:
            raise AssertionError(f"path traversal accepted: {attack!r}")
    # 目录树中不存在任何逃逸产物
    assert list(tmp_path.rglob("escape")) == []
