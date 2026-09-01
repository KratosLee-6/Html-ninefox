"""_base.py · BaseExpert 抽象类"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseExpert(ABC):
    """所有智能体的基类。"""

    name: str = "base"

    @abstractmethod
    def execute(self, input: Dict[str, Any]) -> Dict[str, Any]:
        """输入 dict → 输出 dict。v0.1 返回 mock 数据。"""

    def _placeholder(self, hint: str = "") -> Dict[str, Any]:
        return {
            "_v0_1_placeholder": True,
            "_hint": hint,
            "_note": "Day 7-9 真实实现",
        }
