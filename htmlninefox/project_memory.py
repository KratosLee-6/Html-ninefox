"""Local, explainable project memory built from explicit adoption signals."""

from __future__ import annotations

import copy
import json
import re
import threading
from functools import wraps
from datetime import datetime
from pathlib import Path
from typing import Any

from . import revisions, rules

MEMORY_VERSION = 1
MEMORY_FILE = "project-memory.json"
MAX_MEMORY_BYTES = 128 * 1024
MAX_TEXT = 500
MAX_NOTES = 2000
MAX_LIST_ITEMS = 24
MAX_EVIDENCE = 30
MAX_DECISIONS = 30


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _default_memory() -> dict[str, Any]:
    return {
        "version": MEMORY_VERSION,
        "enabled": True,
        "profile": {
            "brand": "", "audience": "", "tone": "", "forbidden": [],
            "preferred_preset_by_intent": {}, "preferred_primary": "",
            "preferred_font": "", "notes": "",
        },
        "stats": {"adopted_count": 0, "generated_with_memory": 0, "last_adopted_project": ""},
        "evidence": [], "decisions": [], "updated_at": "",
    }


def _text(value: Any, limit: int = MAX_TEXT) -> str:
    return "" if value is None else str(value).strip()[:limit]


def _string_list(value: Any) -> list[str]:
    values = value if isinstance(value, list) else re.split(r"[，,；;\n]+", str(value or ""))
    cleaned = [_text(item, 160) for item in values]
    return list(dict.fromkeys(item for item in cleaned if item))[:MAX_LIST_ITEMS]


def _safe_mapping(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, str] = {}
    for key, item in list(value.items())[:16]:
        safe_key, safe_value = _text(key, 40), _text(item, 80)
        if safe_key and safe_value:
            result[safe_key] = safe_value
    return result


_MEMORY_LOCK = threading.RLock()


def _locked(method):
    @wraps(method)
    def wrapper(*args, **kwargs):
        with _MEMORY_LOCK:
            return method(*args, **kwargs)
    return wrapper


class ProjectMemoryStore:
    """Owns validation, persistence, recommendation and adoption behavior."""

    def __init__(self, output_root: str | Path):
        self.output_root = Path(output_root).expanduser().resolve()
        self.path = self.output_root / ".settings" / MEMORY_FILE

    @_locked
    def read(self) -> dict[str, Any]:
        if not self.path.is_file():
            return _default_memory()
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            return self._normalize(payload)
        except (OSError, json.JSONDecodeError, ValueError, TypeError):
            return _default_memory()

    @_locked
    def save(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("项目记忆必须是对象")
        candidate = copy.deepcopy(self.read())
        if "enabled" in payload:
            candidate["enabled"] = bool(payload["enabled"])
        if "profile" in payload:
            if not isinstance(payload["profile"], dict):
                raise ValueError("profile 必须是对象")
            candidate["profile"].update(payload["profile"])
        candidate["updated_at"] = _now()
        memory = self._normalize(candidate)
        self._write(memory)
        return memory

    @_locked
    def clear(self) -> dict[str, Any]:
        memory = _default_memory()
        memory["updated_at"] = _now()
        self._write(memory)
        return memory

    @_locked
    def recommend(self, prompt: str, request: dict[str, Any] | None = None) -> dict[str, Any]:
        memory = self.read()
        request = request if isinstance(request, dict) else {}
        profile = memory["profile"]
        if not memory["enabled"]:
            return {"enabled": False, "applied": [], "covered": [], "values": {}, "overrides": {}}
        explicit = self._explicit_requirements(prompt, request)
        candidates = {
            "brand": profile["brand"], "audience": profile["audience"],
            "tone": profile["tone"], "forbidden": profile["forbidden"],
        }
        applied: list[dict[str, Any]] = []
        covered: list[dict[str, Any]] = []
        values: dict[str, Any] = {}
        for field, value in candidates.items():
            if not value:
                continue
            if explicit.get(field):
                covered.append({"field": field, "reason": "本次明确要求优先"})
            else:
                values[field] = copy.deepcopy(value)
                applied.append({"field": field, "value": copy.deepcopy(value)})
        intent = _text(request.get("intent"), 40) or rules.classify_intent(prompt)[0]
        preset = profile["preferred_preset_by_intent"].get(intent, "")
        overrides: dict[str, str] = {}
        for field, request_key, value in (
            ("template", "template", preset),
            ("primary", "primary", profile["preferred_primary"]),
            ("font", "font", profile["preferred_font"]),
        ):
            if not value:
                continue
            if request.get(request_key) or (field == "template" and request.get("gallery_id")):
                covered.append({"field": field, "reason": "本次明确选择优先"})
            else:
                overrides[request_key] = value
                applied.append({"field": field, "value": value})
        return {"enabled": True, "intent": intent, "applied": applied, "covered": covered,
                "values": values, "overrides": overrides}

    @_locked
    def adopt(self, project_path: str | Path) -> dict[str, Any]:
        project = Path(project_path).expanduser().resolve()
        try:
            project.relative_to(self.output_root)
        except ValueError as exc:
            raise ValueError("项目不在当前输出目录") from exc
        state_path = project / ".foxstate.json"
        if not state_path.is_file():
            raise ValueError("项目缺少 .foxstate.json")
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("项目状态无法读取") from exc
        memory = self.read()
        if any(item.get("project") == project.name for item in memory["evidence"]):
            return {"adopted": False, "already_adopted": True, "learned": [], "memory": memory}
        brief_result = state.get("brief") if isinstance(state.get("brief"), dict) else {}
        brief = brief_result.get("brief") if isinstance(brief_result.get("brief"), dict) else {}
        content = brief.get("content") if isinstance(brief.get("content"), dict) else {}
        goal = brief.get("goal") if isinstance(brief.get("goal"), dict) else {}
        style = brief.get("style") if isinstance(brief.get("style"), dict) else {}
        constraints = brief.get("constraints") if isinstance(brief.get("constraints"), dict) else {}
        preset = state.get("preset") if isinstance(state.get("preset"), dict) else {}
        tokens = preset.get("tokens") if isinstance(preset.get("tokens"), dict) else {}
        intent = _text(state.get("intent"), 40)
        learned: list[dict[str, Any]] = []
        def learn(field: str, value: Any) -> None:
            if value in (None, "", []):
                return
            memory["profile"][field] = copy.deepcopy(value)
            learned.append({"field": field, "value": copy.deepcopy(value)})
        learn("brand", _text(content.get("brand")))
        learn("audience", _text(goal.get("audience")))
        learn("tone", _text(style.get("tone"), 160))
        forbidden = _string_list(constraints.get("forbidden"))
        if forbidden:
            learn("forbidden", list(dict.fromkeys(memory["profile"]["forbidden"] + forbidden))[:MAX_LIST_ITEMS])
        preset_id = _text(state.get("preset_id"), 80)
        if intent and preset_id:
            memory["profile"]["preferred_preset_by_intent"][intent] = preset_id
            learned.append({"field": "template", "value": preset_id})
        primary = _text(tokens.get("primary"), 20)
        if re.fullmatch(r"#[0-9A-Fa-f]{6}", primary):
            learn("preferred_primary", primary.upper())
        font = self._font_key(tokens.get("font_body") or tokens.get("font_display"))
        if font:
            learn("preferred_font", font)
        feedback = state.get("last_feedback") if isinstance(state.get("last_feedback"), dict) else {}
        decision = {"project": project.name, "suggestion": _text(feedback.get("suggestion"), 300),
                    "rules": _string_list(feedback.get("rules")),
                    "tokens": self._safe_tokens(feedback.get("tokens")), "adopted_at": _now()}
        if decision["suggestion"] or decision["rules"] or decision["tokens"]:
            memory["decisions"].insert(0, decision)
            memory["decisions"] = memory["decisions"][:MAX_DECISIONS]
        memory["evidence"].insert(0, {"project": project.name, "intent": intent,
            "preset_id": preset_id, "revision": max(0, int(state.get("revision") or 0)), "adopted_at": _now()})
        memory["evidence"] = memory["evidence"][:MAX_EVIDENCE]
        memory["stats"]["adopted_count"] += 1
        memory["stats"]["last_adopted_project"] = project.name
        memory["updated_at"] = _now()
        memory = self._normalize(memory)
        self._write(memory)
        return {"adopted": True, "already_adopted": False, "learned": learned, "memory": memory}

    @_locked
    def record_generation(self, recommendation: dict[str, Any]) -> dict[str, Any]:
        if not recommendation.get("applied"):
            return self.read()
        memory = self.read()
        memory["stats"]["generated_with_memory"] += 1
        memory["updated_at"] = _now()
        self._write(memory)
        return memory

    def _normalize(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("项目记忆格式无效")
        memory = _default_memory()
        memory["enabled"] = bool(payload.get("enabled", True))
        profile = payload.get("profile") if isinstance(payload.get("profile"), dict) else {}
        memory["profile"] = {
            "brand": _text(profile.get("brand")), "audience": _text(profile.get("audience")),
            "tone": _text(profile.get("tone"), 160), "forbidden": _string_list(profile.get("forbidden")),
            "preferred_preset_by_intent": _safe_mapping(profile.get("preferred_preset_by_intent")),
            "preferred_primary": _text(profile.get("preferred_primary"), 20),
            "preferred_font": _text(profile.get("preferred_font"), 20),
            "notes": _text(profile.get("notes"), MAX_NOTES),
        }
        stats = payload.get("stats") if isinstance(payload.get("stats"), dict) else {}
        memory["stats"] = {"adopted_count": max(0, int(stats.get("adopted_count") or 0)),
            "generated_with_memory": max(0, int(stats.get("generated_with_memory") or 0)),
            "last_adopted_project": _text(stats.get("last_adopted_project"), 80)}
        evidence = payload.get("evidence") if isinstance(payload.get("evidence"), list) else []
        memory["evidence"] = [self._safe_evidence(item) for item in evidence if isinstance(item, dict)][:MAX_EVIDENCE]
        decisions = payload.get("decisions") if isinstance(payload.get("decisions"), list) else []
        memory["decisions"] = [self._safe_decision(item) for item in decisions if isinstance(item, dict)][:MAX_DECISIONS]
        memory["updated_at"] = _text(payload.get("updated_at"), 40)
        if len(json.dumps(memory, ensure_ascii=False).encode("utf-8")) > MAX_MEMORY_BYTES:
            raise ValueError("项目记忆超过 128KB")
        return memory

    def _write(self, memory: dict[str, Any]) -> None:
        revisions.atomic_write(
            self.path, json.dumps(memory, ensure_ascii=False, indent=2))

    @staticmethod
    def _explicit_requirements(prompt: str, request: dict[str, Any]) -> dict[str, bool]:
        text = str(prompt or "")
        _, audience_matches = rules.detect_audience(text)
        _, tone_matches = rules.detect_tone(text)
        return {"brand": bool(rules.detect_brand(text) or request.get("brand")),
                "audience": bool(audience_matches or request.get("audience")),
                "tone": bool(tone_matches or request.get("tone")),
                "forbidden": bool(re.search(r"(?:不要|避免|禁止|禁用|不能|不可|排除)", text))}

    @staticmethod
    def _font_key(value: Any) -> str:
        font = str(value or "").lower()
        if "mono" in font or "consolas" in font:
            return "mono"
        if "sans-serif" in font or "pingfang" in font or "yahei" in font or "inter" in font:
            return "sans"
        if "serif" in font or "songti" in font or "simsun" in font:
            return "serif"
        return "sans" if font else ""

    @staticmethod
    def _safe_tokens(value: Any) -> dict[str, str]:
        if not isinstance(value, dict):
            return {}
        allowed = {"primary", "background", "surface", "text", "font_body", "font_display"}
        return {key: _text(item, 160) for key, item in value.items() if key in allowed and _text(item, 160)}

    @staticmethod
    def _safe_evidence(item: dict[str, Any]) -> dict[str, Any]:
        return {"project": _text(item.get("project"), 80), "intent": _text(item.get("intent"), 40),
                "preset_id": _text(item.get("preset_id"), 80),
                "revision": max(0, int(item.get("revision") or 0)),
                "adopted_at": _text(item.get("adopted_at"), 40)}

    @classmethod
    def _safe_decision(cls, item: dict[str, Any]) -> dict[str, Any]:
        return {"project": _text(item.get("project"), 80), "suggestion": _text(item.get("suggestion"), 300),
                "rules": _string_list(item.get("rules")), "tokens": cls._safe_tokens(item.get("tokens")),
                "adopted_at": _text(item.get("adopted_at"), 40)}
