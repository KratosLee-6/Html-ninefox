"""Application use cases shared by CLI, HTTP, and external adapters."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Mapping, TypeAlias

from . import llm, pipeline, recipe_run
from .project_memory import ProjectMemoryStore
from .server.inputs import InputStore
from .server.settings import AISettingsStore
from .user_gallery import UserGalleryError, UserGalleryStore

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]
GenerationRunner: TypeAlias = Callable[..., Mapping[str, object]]


def _json_object(value: object) -> JsonObject:
    return copy.deepcopy(value) if isinstance(value, dict) else {}


class GenerationError(Exception):
    """Stable generation failure independent of transport status codes."""

    def __init__(self, code: str, message: str, details: JsonObject | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


@dataclass(frozen=True)
class GenerationBlock:
    """One caller-selected composition block or block identifier."""

    _value: JsonValue = field(repr=False)

    @classmethod
    def from_value(cls, value: JsonValue) -> GenerationBlock:
        return cls(copy.deepcopy(value))

    def to_value(self) -> JsonValue:
        return copy.deepcopy(self._value)

@dataclass(frozen=True)
class VerificationResult:
    """HTML verification outcome returned by a generation use case."""

    _payload: JsonObject = field(repr=False)

    @classmethod
    def from_mapping(cls, value: object) -> VerificationResult:
        return cls(_json_object(value))

    @property
    def ok(self) -> bool:
        return self._payload.get("ok") is True

    def to_mapping(self) -> JsonObject:
        return copy.deepcopy(self._payload)


@dataclass(frozen=True)
class RecipeRunResult:
    """Observable Analyze → Deliver execution evidence."""

    _payload: JsonObject = field(repr=False)

    @classmethod
    def from_mapping(cls, value: object) -> RecipeRunResult:
        return cls(_json_object(value))

    @property
    def stage_ids(self) -> tuple[str, ...]:
        stages = self._payload.get("stages")
        if not isinstance(stages, list):
            return ()
        return tuple(
            str(stage.get("id"))
            for stage in stages
            if isinstance(stage, dict) and stage.get("id")
        )

    def to_mapping(self) -> JsonObject:
        return copy.deepcopy(self._payload)


@dataclass(frozen=True)
class MemoryApplicationResult:
    """Project Memory recommendations applied to one Generation Request."""

    _payload: JsonObject = field(repr=False)

    @classmethod
    def from_mapping(cls, value: object) -> MemoryApplicationResult:
        return cls(_json_object(value))

    @property
    def enabled(self) -> bool:
        return self._payload.get("enabled") is True

    def to_mapping(self) -> JsonObject:
        return copy.deepcopy(self._payload)


@dataclass(frozen=True)
class GenerationRequest:
    """Caller-owned requirements for one Artifact generation."""

    prompt: str
    input_ids: tuple[str, ...] = ()
    skill: str | None = None
    template: str | None = None
    intent: str | None = None
    quiet_llm: bool = False
    primary: str | None = None
    font: str | None = None
    gallery_id: str | None = None
    blocks: tuple[GenerationBlock, ...] = ()
    selection_mode: str = "custom"

    def _memory_context(self) -> JsonObject:
        """Expose only explicit requirements understood by Project Memory."""
        return {
            "intent": self.intent,
            "template": self.template,
            "primary": self.primary,
            "font": self.font,
            "gallery_id": self.gallery_id,
        }


@dataclass(frozen=True)
class GenerationResult:
    """Stable generation outcome consumed by adapters."""

    work: Path
    intent: str
    preset_id: str
    preset_name: str
    route_decision: str
    skill: str | None
    brief_confidence: float
    fallback_used: bool
    files: tuple[str, ...]
    verification: VerificationResult
    recipe_run: RecipeRunResult
    memory_applied: MemoryApplicationResult


@dataclass(frozen=True)
class StudioDependencies:
    """Explicit workspace dependencies shared by application use cases."""

    workspace_root: Path
    generation_root: Path
    inputs: InputStore
    ai_settings: AISettingsStore
    memory: ProjectMemoryStore
    gallery_root: Path
    allow_environment_ai: bool
    run_generation: GenerationRunner

    @classmethod
    def for_workspace(
        cls,
        workspace_root: str | Path,
        *,
        generation_root: str | Path | None = None,
        allow_environment_ai: bool = False,
        run_generation: GenerationRunner = pipeline.run_expert,
    ) -> StudioDependencies:
        workspace = Path(workspace_root).expanduser().resolve()
        output = Path(generation_root or workspace).expanduser().resolve()
        workspace.mkdir(parents=True, exist_ok=True)
        output.mkdir(parents=True, exist_ok=True)
        return cls(
            workspace_root=workspace,
            generation_root=output,
            inputs=InputStore(workspace),
            ai_settings=AISettingsStore(workspace),
            memory=ProjectMemoryStore(workspace),
            gallery_root=workspace / ".library" / "gallery",
            allow_environment_ai=allow_environment_ai,
            run_generation=run_generation,
        )


class StudioApplication:
    """Deep application module for creation workflows."""

    def __init__(self, dependencies: StudioDependencies) -> None:
        self.dependencies = dependencies

    def generate(
        self,
        request: GenerationRequest,
        progress_callback: recipe_run.ProgressCallback | None = None,
    ) -> GenerationResult:
        prompt, input_items = self._prepare_generation(request)

        ai_enabled = self.activate_ai()
        memory_applied = self.recommend_memory(prompt, request)
        memory_overrides = _json_object(memory_applied.get("overrides"))
        gallery_id = str(request.gallery_id or "")
        gallery_item = self._gallery_item(gallery_id)
        style_overrides: dict[str, str] = {}
        for key, explicit in (("primary", request.primary), ("font", request.font)):
            remembered = memory_overrides.get(key)
            value = explicit or (remembered if isinstance(remembered, str) else None)
            if value:
                style_overrides[key] = value
        if gallery_item:
            gallery_styles = gallery_item.get("style_overrides")
            if isinstance(gallery_styles, dict):
                for key, value in gallery_styles.items():
                    if isinstance(value, str):
                        style_overrides.setdefault(key, value)
        remembered_template = memory_overrides.get("template")
        template = request.template or (
            remembered_template if isinstance(remembered_template, str) else None
        )
        design_tokens = gallery_item.get("design_tokens") if gallery_item else {}
        try:
            result = self.dependencies.run_generation(
                prompt,
                skill=request.skill or None,
                template=template or None,
                output=str(self.dependencies.generation_root),
                intent_override=request.intent or None,
                quiet_llm=bool(request.quiet_llm) or not ai_enabled,
                style_overrides=style_overrides or None,
                composition={
                    "gallery_id": gallery_id or None,
                    "gallery_source": gallery_item.get("source") if gallery_item else "builtin",
                    "template_design_tokens": design_tokens if isinstance(design_tokens, dict) else {},
                    "blocks": [block.to_value() for block in request.blocks],
                    "inputs": input_items,
                    "selection_mode": request.selection_mode or "custom",
                },
                memory_context=memory_applied,
                progress_callback=progress_callback,
            )
        except GenerationError:
            raise
        except Exception as error:
            raise GenerationError(
                "generation_failed", "生成失败",
                {"cause": error.__class__.__name__},
            ) from error
        self.dependencies.memory.record_generation(memory_applied)
        if gallery_item:
            try:
                self._gallery_store().record_use(gallery_id)
            except (UserGalleryError, OSError, json.JSONDecodeError):
                pass
        return GenerationResult(
            work=Path(result["work"]),
            intent=str(result["intent"]),
            preset_id=str(result["preset_id"]),
            preset_name=str(result["preset_name"]),
            route_decision=str(result["route_decision"]),
            skill=str(result["skill"]) if result.get("skill") else None,
            brief_confidence=float(result["brief_confidence"]),
            fallback_used=bool(result["fallback_used"]),
            files=tuple(str(item) for item in result["files"]),
            verification=VerificationResult.from_mapping(result.get("verification")),
            recipe_run=RecipeRunResult.from_mapping(result.get("recipe_run")),
            memory_applied=MemoryApplicationResult.from_mapping(
                result.get("memory_applied", memory_applied)
            ),
        )

    def validate_generation(self, request: GenerationRequest) -> None:
        """Validate through the same rules used by generate()."""
        self._prepare_generation(request)

    def _prepare_generation(
        self,
        request: GenerationRequest,
    ) -> tuple[str, list[JsonObject]]:
        prompt = request.prompt.strip()
        input_items = [
            _json_object(item)
            for item in self.dependencies.inputs.describe(list(request.input_ids))
        ]
        if not prompt and input_items:
            prompt = "请根据用户上传的附件生成合适的 HTML 作品"
        prompt += InputStore.prompt_context(input_items)
        if not prompt:
            raise GenerationError("prompt_required", "prompt 或附件至少需要一个")
        return prompt, input_items

    def activate_ai(self) -> bool:
        settings = self.dependencies.ai_settings.activate()
        enabled = bool(settings.get("enabled") and settings.get("model") and settings.get("base_url"))
        if enabled:
            llm.router.configure(llm.runtime_config_from_settings(settings))
            return True
        if self.dependencies.allow_environment_ai:
            environment = llm.runtime_settings_from_env()
            if environment:
                llm.router.configure(llm.runtime_config_from_settings(environment))
                return True
        llm.router.configure(llm.get_default_config())
        return False

    def recommend_memory(
        self,
        prompt: str,
        request: GenerationRequest,
    ) -> JsonObject:
        recommendation = _json_object(
            self.dependencies.memory.recommend(prompt, request._memory_context())
        )
        overrides = _json_object(recommendation.get("overrides"))
        remembered_template = overrides.get("template")
        if isinstance(remembered_template, str) and remembered_template not in {
            item["id"] for item in pipeline.list_templates()
        }:
            overrides.pop("template", None)
            recommendation["overrides"] = overrides
            covered = recommendation.setdefault("covered", [])
            if isinstance(covered, list):
                covered.append({
                    "field": "template",
                    "reason": "记忆模板已不可用，已安全忽略",
                })
            applied = recommendation.get("applied")
            if isinstance(applied, list):
                recommendation["applied"] = [
                    item for item in applied
                    if not isinstance(item, dict) or item.get("field") != "template"
                ]
        return recommendation

    def _gallery_store(self) -> UserGalleryStore:
        return UserGalleryStore(self.dependencies.gallery_root)

    def _gallery_item(self, gallery_id: str) -> JsonObject | None:
        if not gallery_id:
            return None
        try:
            return _json_object(self._gallery_store().get(gallery_id))
        except UserGalleryError:
            return None
