"""Application use cases shared by CLI, HTTP, and external adapters."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Mapping, TypeAlias

from . import llm, pipeline, recipe_run, revisions
from .project_memory import ProjectMemoryStore
from .user_gallery import UserGalleryError, UserGalleryStore

if TYPE_CHECKING:
    from .server.inputs import InputStore
    from .server.settings import AISettingsStore

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]
GenerationRunner: TypeAlias = Callable[..., Mapping[str, object]]
FeedbackRunner: TypeAlias = Callable[..., Mapping[str, object]]
RestoreRunner: TypeAlias = Callable[..., Mapping[str, object]]
ExportRunner: TypeAlias = Callable[..., Mapping[str, object]]


def _json_object(value: object) -> JsonObject:
    return copy.deepcopy(value) if isinstance(value, dict) else {}


class ApplicationError(Exception):
    """Stable application failure independent of Adapter transport details."""

    def __init__(self, code: str, message: str, details: JsonObject | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


class GenerationError(ApplicationError):
    """Stable generation failure independent of transport status codes."""


class FeedbackError(ApplicationError):
    """Stable feedback failure independent of transport status codes."""

    @property
    def requires_clarification(self) -> bool:
        return self.code == "feedback_not_actionable" and bool(self.details.get("ask_user"))


class RestoreError(ApplicationError):
    """Stable Restore failure independent of transport status codes."""


class ExportError(ApplicationError):
    """Stable Export failure independent of transport status codes."""


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
class FeedbackTokenChanges:
    """Design-token changes extracted from one Feedback Iteration."""

    _payload: JsonObject = field(repr=False)

    @classmethod
    def from_mapping(cls, value: object) -> FeedbackTokenChanges:
        return cls(_json_object(value))

    def to_mapping(self) -> JsonObject:
        return copy.deepcopy(self._payload)


@dataclass(frozen=True)
class FeedbackRequest:
    """Caller-owned requirements for one Feedback Iteration."""

    project: Path | None
    note: str
    dry_run: bool = False
    quiet_llm: bool = False


@dataclass(frozen=True)
class FeedbackResult:
    """Stable feedback outcome consumed by Adapters."""

    project: Path
    revision: int | None
    suggestion: str
    applied_rules: tuple[str, ...]
    tokens: FeedbackTokenChanges
    model: str
    output: Path | None
    dry_run: bool


@dataclass(frozen=True)
class RestoreRequest:
    """Caller-owned requirements for restoring an immutable Revision."""

    project: Path | None
    revision: int | None
    expected_revision: int | None


@dataclass(frozen=True)
class RevisionResult:
    """Stable result of restoring a historical Revision."""

    project: Path
    revision: int
    restored_from: int


@dataclass(frozen=True)
class ExportFileResult:
    """One file produced by an Export."""

    name: str
    bytes: int
    download_url: str
    preview_url: str

    @classmethod
    def from_mapping(cls, value: object) -> ExportFileResult:
        payload = _json_object(value)
        return cls(
            name=str(payload.get("name") or ""),
            bytes=int(payload.get("bytes") or 0),
            download_url=str(payload.get("download_url") or ""),
            preview_url=str(payload.get("preview_url") or ""),
        )

    def to_mapping(self) -> JsonObject:
        return {
            "name": self.name,
            "bytes": self.bytes,
            "download_url": self.download_url,
            "preview_url": self.preview_url,
        }


@dataclass(frozen=True)
class ExportWarningResult:
    """One compatibility or runtime warning from an Export."""

    code: str
    level: str
    message: str

    @classmethod
    def from_mapping(cls, value: object) -> ExportWarningResult:
        payload = _json_object(value)
        return cls(
            code=str(payload.get("code") or ""),
            level=str(payload.get("level") or "warning"),
            message=str(payload.get("message") or ""),
        )

    def to_mapping(self) -> JsonObject:
        return {"code": self.code, "level": self.level, "message": self.message}


@dataclass(frozen=True)
class ExportBrowserResult:
    """Browser runtime evidence recorded for an Export."""

    _payload: JsonObject = field(repr=False)

    @classmethod
    def from_mapping(cls, value: object) -> ExportBrowserResult:
        return cls(_json_object(value))

    def to_mapping(self) -> JsonObject:
        return copy.deepcopy(self._payload)


@dataclass(frozen=True)
class ExportRequest:
    """Caller-owned requirements for exporting an Artifact."""

    project_name: str
    format: str = "pdf"
    scope: str = "auto"
    pages: str | tuple[int | str, ...] = ""
    width: int | None = 1920
    height: int | None = 1080
    scale: int | None = 2
    paper: str = "A4"
    landscape: bool = False


@dataclass(frozen=True)
class ExportResult:
    """Stable Export outcome consumed by Adapters."""

    project_name: str
    export_id: str
    format: str
    files: tuple[ExportFileResult, ...]
    report: ExportFileResult
    warnings: tuple[ExportWarningResult, ...]
    compatibility_score: int
    browser: ExportBrowserResult

    def to_mapping(self) -> JsonObject:
        return {
            "project_name": self.project_name,
            "export_id": self.export_id,
            "format": self.format,
            "files": [item.to_mapping() for item in self.files],
            "report": self.report.to_mapping(),
            "warnings": [item.to_mapping() for item in self.warnings],
            "compatibility_score": self.compatibility_score,
            "browser": self.browser.to_mapping(),
        }


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
    run_feedback: FeedbackRunner
    restore_revision: RestoreRunner
    run_export: ExportRunner

    @classmethod
    def for_workspace(
        cls,
        workspace_root: str | Path,
        *,
        generation_root: str | Path | None = None,
        allow_environment_ai: bool = False,
        run_generation: GenerationRunner = pipeline.run_expert,
        run_feedback: FeedbackRunner = pipeline.run_feedback,
        restore_revision: RestoreRunner = revisions.restore,
        run_export: ExportRunner | None = None,
    ) -> StudioDependencies:
        from .server.inputs import InputStore
        from .server.settings import AISettingsStore

        workspace = Path(workspace_root).expanduser().resolve()
        output = Path(generation_root or workspace).expanduser().resolve()
        if run_export is None:
            from . import exporting
            run_export = exporting.export_project
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
            run_feedback=run_feedback,
            restore_revision=restore_revision,
            run_export=run_export,
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

    def feedback(self, request: FeedbackRequest) -> FeedbackResult:
        project, note = self._validate_feedback(request)
        allow_llm = False if request.quiet_llm else self.activate_ai()
        try:
            payload = self.dependencies.run_feedback(
                str(project),
                note,
                revise=not request.dry_run,
                allow_llm=allow_llm,
            )
            if not payload.get("ok"):
                message = str(payload.get("ask_user") or payload.get("error") or "反馈无法执行")
                raise FeedbackError(
                    "feedback_not_actionable",
                    message,
                    _json_object(payload),
                )
            revision_value = payload.get("revision")
            output_value = payload.get("output")
            rules = payload.get("applied_rules")
            return FeedbackResult(
                project=Path(str(payload.get("project") or project)).resolve(),
                revision=int(revision_value) if revision_value is not None else None,
                suggestion=str(payload.get("suggestion") or ""),
                applied_rules=tuple(str(item) for item in rules) if isinstance(rules, list) else (),
                tokens=FeedbackTokenChanges.from_mapping(payload.get("tokens")),
                model=str(payload.get("model") or "rules"),
                output=Path(str(output_value)).resolve() if output_value else None,
                dry_run=bool(payload.get("dry_run", request.dry_run)),
            )
        except FeedbackError:
            raise
        except revisions.RevisionError as error:
            raise FeedbackError(error.code, str(error)) from error
        except Exception as error:
            raise FeedbackError(
                "feedback_failed",
                "反馈迭代失败",
                {"cause": error.__class__.__name__},
            ) from error

    @staticmethod
    def _validate_feedback(request: FeedbackRequest) -> tuple[Path, str]:
        note = request.note.strip()
        if request.project is None or not note:
            raise FeedbackError("feedback_fields_required", "project 与 note 必填")
        return request.project.expanduser().resolve(), note

    def restore(self, request: RestoreRequest) -> RevisionResult:
        if request.project is None:
            raise RestoreError("project_required", "请选择需要恢复的项目")
        project = request.project.expanduser().resolve()
        try:
            state = self.dependencies.restore_revision(
                project,
                request.revision,
                request.expected_revision,
            )
            revision = state.get("revision")
            if type(revision) is not int or type(request.revision) is not int:
                raise RestoreError("restore_failed", "版本恢复失败")
            return RevisionResult(
                project=project,
                revision=revision,
                restored_from=request.revision,
            )
        except RestoreError:
            raise
        except revisions.RevisionError as error:
            raise RestoreError(error.code, str(error)) from error
        except Exception as error:
            raise RestoreError(
                "restore_failed",
                "版本恢复失败",
                {"cause": error.__class__.__name__},
            ) from error

    def export(self, request: ExportRequest) -> ExportResult:
        normalized = self._prepare_export(request)
        try:
            payload = self.dependencies.run_export(
                self.dependencies.workspace_root,
                normalized,
            )
            files = payload.get("files")
            warnings = payload.get("warnings")
            return ExportResult(
                project_name=str(payload.get("project_name") or normalized["project_name"]),
                export_id=str(payload.get("export_id") or ""),
                format=str(payload.get("format") or normalized["format"]),
                files=tuple(
                    ExportFileResult.from_mapping(item)
                    for item in files
                ) if isinstance(files, list) else (),
                report=ExportFileResult.from_mapping(payload.get("report")),
                warnings=tuple(
                    ExportWarningResult.from_mapping(item)
                    for item in warnings
                ) if isinstance(warnings, list) else (),
                compatibility_score=int(payload.get("compatibility_score") or 0),
                browser=ExportBrowserResult.from_mapping(payload.get("browser")),
            )
        except ExportError:
            raise
        except Exception as error:
            raise self._export_error(error) from error

    def validate_export(self, request: ExportRequest) -> None:
        """Validate an Export before scheduling asynchronous work."""
        self._prepare_export(request)

    def _prepare_export(self, request: ExportRequest) -> JsonObject:
        pages: JsonValue
        if isinstance(request.pages, tuple):
            pages = list(request.pages)
        else:
            pages = request.pages
        payload: JsonObject = {
            "project_name": request.project_name,
            "format": request.format,
            "scope": request.scope,
            "pages": pages,
            "width": request.width,
            "height": request.height,
            "scale": request.scale,
            "paper": request.paper,
            "landscape": request.landscape,
        }
        try:
            from . import exporting
            normalized = _json_object(exporting.normalize_export_request(payload))
            exporting.analyze_project(
                self.dependencies.workspace_root,
                str(normalized["project_name"]),
            )
            return normalized
        except ExportError:
            raise
        except Exception as error:
            raise self._export_error(error) from error

    @staticmethod
    def _export_error(error: Exception) -> ExportError:
        code = getattr(error, "code", None)
        message = getattr(error, "message", None)
        details = getattr(error, "details", None)
        if isinstance(code, str) and isinstance(message, str):
            return ExportError(code, message, _json_object(details))
        return ExportError(
            "export_failed",
            "导出失败",
            {"cause": error.__class__.__name__},
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
        prompt += self.dependencies.inputs.prompt_context(input_items)
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
