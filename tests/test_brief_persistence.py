from pathlib import Path

from htmlninefox.experts import brief_expert


def test_brief_cache_failure_does_not_block_generation(monkeypatch):
    def denied(*args, **kwargs):
        raise PermissionError("read-only home")

    monkeypatch.setattr(Path, "write_text", denied)
    brief_expert._persist_brief("demo", {"brief": {}}, True)


def test_feedback_and_cost_logs_are_non_blocking(monkeypatch, tmp_path):
    from htmlninefox.cost import CostTracker
    from htmlninefox.experts import feedback_expert

    tracker = CostTracker(log_path=tmp_path / "cost.jsonl")
    original_open = Path.open

    def denied(path, *args, **kwargs):
        if path.name in {"cost.jsonl", "demo.md"}:
            raise PermissionError("read-only log directory")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", denied)
    entry = tracker.record("brief", "demo", 1, 1, 0.0)
    assert entry["log_persisted"] is False
    feedback_expert._persist_feedback("demo", "2026-09-14T20:00:00", "调整颜色", {})
