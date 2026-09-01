"""llm.py · LiteLLM Router 封装（复用 PoC v0.1）"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .cache import DiskCache
from .config import get_default_config
from .cost import CostTracker

logger = logging.getLogger(__name__)

_LITELLM_ROUTER = None


def runtime_config_from_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    """Build a one-model LiteLLM config from local user settings."""
    model = str(settings.get("model") or "").strip()
    provider = str(settings.get("provider") or "openai-compatible").strip()
    if provider == "openai-compatible" and "/" not in model:
        litellm_model = f"openai/{model}"
    elif provider == "anthropic" and not model.startswith("anthropic/"):
        litellm_model = f"anthropic/{model}"
    elif provider == "ollama" and not model.startswith("ollama/"):
        litellm_model = f"ollama/{model}"
    else:
        litellm_model = model
    params: Dict[str, Any] = {"model": litellm_model}
    if settings.get("api_key"):
        params["api_key"] = settings["api_key"]
    if settings.get("base_url"):
        params["api_base"] = settings["base_url"]
    return {
        "_runtime_settings": dict(settings),
        "model_list": [{"model_name": "user-model", "litellm_params": params}],
        "router_settings": {"routing_strategy": "simple-shuffle", "num_retries": 1, "timeout": 45},
        "agent_routing": {
            "brief_expert": {"primary": "user-model"},
            "style_expert": {"primary": "user-model"},
            "feedback_expert": {"primary": "user-model"},
        },
        "cache_settings": {"enabled": True, "ttl_days": 7},
        "cost_rates": {"daily_budget_usd": 5.0},
    }


def _get_litellm_router(config: Dict[str, Any]):
    global _LITELLM_ROUTER
    if _LITELLM_ROUTER is not None:
        return _LITELLM_ROUTER
    try:
        from litellm import Router
    except ImportError as e:
        raise ImportError("请先安装 litellm: pip install litellm") from e
    rs = config.get("router_settings", {})
    _LITELLM_ROUTER = Router(
        model_list=config.get("model_list", []),
        routing_strategy=rs.get("routing_strategy", "simple-shuffle"),
        num_retries=rs.get("num_retries", 3),
        timeout=rs.get("timeout", 30),
        fallbacks=rs.get("fallbacks", []),
        context_window_fallbacks=rs.get("context_window_fallbacks", []),
        cooldown_time=rs.get("cooldown_time", 60),
    )
    return _LITELLM_ROUTER


@dataclass
class LLMResult:
    text: str
    model: str
    agent: str
    task: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    cached: bool = False
    fallback_used: bool = False
    raw: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.text


class HtmlNineFoxRouter:
    DEFAULT_AGENT = "brief_expert"
    DEFAULT_TASK = "general"

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        cache: Optional[DiskCache] = None,
        cost_tracker: Optional[CostTracker] = None,
    ):
        self.config = config or get_default_config()
        self.cache = cache or DiskCache(
            cache_dir=Path.home() / ".htmlninefox" / "cache" / "llm",
            ttl_seconds=self.config.get("cache_settings", {}).get("ttl_days", 7) * 24 * 3600,
            enabled=self.config.get("cache_settings", {}).get("enabled", True),
        )
        self.cost = cost_tracker or CostTracker(
            log_path=Path.home() / ".htmlninefox" / "logs" / "cost.jsonl",
            cost_rates=self.config.get("cost_rates", {}),
            daily_budget_usd=self.config.get("cost_rates", {}).get("daily_budget_usd", 5.0),
        )
        self._router = None

    def configure(self, config: Dict[str, Any]) -> None:
        global _LITELLM_ROUTER
        self.config = config
        self._router = None
        _LITELLM_ROUTER = None

    def _resolve_model(self, agent: str, task: str) -> str:
        ar = self.config.get("agent_routing", {})
        for key in (agent, task):
            cfg = ar.get(key, {})
            if isinstance(cfg, dict) and cfg.get("primary"):
                return cfg["primary"]
        ml = self.config.get("model_list", [])
        if ml:
            return ml[0].get("model_name", "minimax-cn")
        return "minimax-cn"

    def call(
        self,
        prompt: str,
        agent: str = DEFAULT_AGENT,
        task: str = DEFAULT_TASK,
        use_cache: bool = True,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMResult:
        if not prompt or not prompt.strip():
            raise ValueError("prompt 不能为空")
        model_name = self._resolve_model(agent, task)

        if use_cache:
            hit = self.cache.get(prompt, model_name, task)
            if hit is not None:
                logger.info(f"[cache HIT] agent={agent} model={model_name}")
                return LLMResult(
                    text=hit.get("text", ""),
                    model=hit.get("model", model_name),
                    agent=agent,
                    task=task,
                    input_tokens=hit.get("input_tokens", 0),
                    output_tokens=hit.get("output_tokens", 0),
                    cost_usd=0.0,
                    cached=True,
                )

        messages: List[Dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        runtime_settings = self.config.get("_runtime_settings")
        if runtime_settings:
            response = self._direct_completion(runtime_settings, messages, temperature, max_tokens)
        else:
            router = _get_litellm_router(self.config)
            try:
                response = router.completion(
                    model=model_name,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except Exception as e:
                raise RuntimeError(
                    f"LLM 调用失败（agent={agent}, model={model_name}）: {e}"
                ) from e

        text = ""
        if hasattr(response, "choices") and response.choices:
            text = response.choices[0].message.content or ""
        elif isinstance(response, dict):
            text = response.get("choices", [{}])[0].get("message", {}).get("content", "")

        usage = getattr(response, "usage", None) or {}
        in_tok = usage.get("prompt_tokens", 0) if isinstance(usage, dict) else 0
        out_tok = usage.get("completion_tokens", 0) if isinstance(usage, dict) else 0
        cost_usd = self.cost.estimate_cost(model_name, in_tok, out_tok)

        self.cost.record(agent, model_name, in_tok, out_tok, cost_usd, prompt, cached=False)

        if use_cache:
            self.cache.set(prompt, model_name, task, {
                "text": text, "model": model_name,
                "input_tokens": in_tok, "output_tokens": out_tok,
            })

        return LLMResult(
            text=text, model=model_name, agent=agent, task=task,
            input_tokens=in_tok, output_tokens=out_tok,
            cost_usd=cost_usd, cached=False,
        )

    @staticmethod
    def _direct_completion(settings: Dict[str, Any], messages: List[Dict[str, str]],
                           temperature: float, max_tokens: int) -> Dict[str, Any]:
        base_url = str(settings.get("base_url") or "").strip().rstrip("/")
        model = str(settings.get("model") or "").strip()
        if not base_url or not model:
            raise RuntimeError("AI 模型配置缺少 base_url 或 model")
        endpoint = base_url if base_url.endswith("/chat/completions") else base_url + "/chat/completions"
        body = json.dumps({
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        api_key = str(settings.get("api_key") or "").strip()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        request = urllib.request.Request(endpoint, data=body, method="POST", headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"模型接口返回 HTTP {error.code}：{detail}") from error
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            raise RuntimeError(f"模型接口连接失败：{error}") from error

    def stats(self) -> Dict[str, Any]:
        return {
            "cache": self.cache.stats(),
            "cost_today_usd": self.cost.today_total(),
            "over_budget": self.cost.over_budget(),
        }


router = HtmlNineFoxRouter()
