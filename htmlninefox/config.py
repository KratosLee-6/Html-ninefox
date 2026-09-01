"""config.py · 配置加载（复用 PoC v0.1）"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict

import yaml

DEFAULT_CONFIG_PATH = Path.home() / ".htmlninefox" / "config.yaml"
PACKAGE_ROOT = Path(__file__).resolve().parent
DEFAULT_ROUTER_CONFIG = PACKAGE_ROOT / "example" / "litellm-router-config.yaml"

_ENV_PATTERN = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)\}")


def _expand_env(value: Any) -> Any:
    if isinstance(value, str):
        def repl(m: re.Match) -> str:
            return os.environ.get(m.group(1), m.group(0))
        return _ENV_PATTERN.sub(repl, value)
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(v) for v in value]
    return value


def load_config(config_path: str | Path | None = None) -> Dict[str, Any]:
    path = Path(config_path) if config_path else None
    if path is None and DEFAULT_CONFIG_PATH.exists():
        path = DEFAULT_CONFIG_PATH
    if path is None or not path.exists():
        path = DEFAULT_ROUTER_CONFIG
    if not path.exists():
        raise FileNotFoundError(
            f"找不到配置。\n  尝试过: {path}\n"
            f"  请创建 {DEFAULT_CONFIG_PATH} 或放一份到 example/litellm-router-config.yaml。"
        )
    with path.open("r", encoding="utf-8") as f:
        return _expand_env(yaml.safe_load(f))


def get_default_config() -> Dict[str, Any]:
    return load_config(DEFAULT_ROUTER_CONFIG)
