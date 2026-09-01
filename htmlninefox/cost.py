"""cost.py · 成本统计（复用 PoC v0.1）"""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_LOG_PATH = Path.home() / ".htmlninefox" / "logs" / "cost.jsonl"
_write_lock = threading.Lock()


class CostTracker:
    def __init__(
        self,
        log_path: str | Path | None = None,
        cost_rates: Optional[Dict[str, Dict[str, float]]] = None,
        daily_budget_usd: float = 5.0,
        monthly_budget_usd: float = 50.0,
    ):
        self.log_path = Path(log_path) if log_path else DEFAULT_LOG_PATH
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.cost_rates = cost_rates or {}
        self.daily_budget_usd = daily_budget_usd
        self.monthly_budget_usd = monthly_budget_usd

    def estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        rate = self.cost_rates.get(model, {})
        in_rate = rate.get("input_per_1m", 0.0)
        out_rate = rate.get("output_per_1m", 0.0)
        cost = (input_tokens / 1_000_000) * in_rate + (output_tokens / 1_000_000) * out_rate
        return round(cost, 6)

    def record(
        self,
        agent: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        prompt_preview: str = "",
        cached: bool = False,
    ) -> Dict[str, Any]:
        entry = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "epoch": int(time.time()),
            "agent": agent,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost_usd": cost_usd,
            "cached": cached,
            "prompt_preview": prompt_preview[:120],
        }
        with _write_lock:
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry

    def today_total(self) -> float:
        today = datetime.now().date().isoformat()
        total = 0.0
        if not self.log_path.exists():
            return total
        with _write_lock:
            with self.log_path.open("r", encoding="utf-8") as f:
                for line in f:
                    try:
                        e = json.loads(line)
                        if e.get("ts", "").startswith(today):
                            total += e.get("cost_usd", 0.0)
                    except json.JSONDecodeError:
                        continue
        return round(total, 4)

    def over_budget(self) -> bool:
        return self.today_total() > self.daily_budget_usd
