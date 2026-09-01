"""alliance/router.py · Skill 联盟路由器（v0.2 Day10 升级）

manifest 加载顺序：data/alliance/（种子）+ ~/.htmlninefox/alliance/（用户覆盖）。
v0.2 升级：invoke() 真实 subprocess 调 entry + 自动 fallback 链；route() 加权评分；
日志写入 ~/.htmlninefox/logs/alliance.log。
"""

from __future__ import annotations

import importlib
import json
import logging
import re
import shlex
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Sequence

from ..rules import CONTENT_TYPES

logger = logging.getLogger(__name__)

_SEED_DIR = Path(__file__).resolve().parent.parent / "data" / "alliance"
_USER_DIR = Path.home() / ".htmlninefox" / "alliance"
_LOG_DIR = Path.home() / ".htmlninefox" / "logs"

# 安全策略（P0 #1 fix）：白名单 entry 命令前缀。manifest 的 entry 必须以这些前缀之一开头，
# 否则视为不安全。设计理由：manifest 是用户从外部下载/接收的 YAML，恶意 entry 可 RCE。
# 白名单只放最常见的"安全起点"——具体 skill 自己负责解析 args。
_ALLOWED_ENTRY_HEADS: tuple[str, ...] = (
    "python ",
    "python3 ",
    "node ",
    "bash ",
    "sh ",
    "cmd ",
    "powershell ",
)

# shlex.split 不拆掉 `{topic}` 等占位符；但我们要保留 placeholder 让 _safe_substitute 来替换，
# 所以用 POSIX 友好且不做变量展开的 split + keep_quote=True，再走二次替换。
_PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")


class AllianceRouter:
    def __init__(self) -> None:
        self.skills: Dict[str, Dict[str, Any]] = {}
        self._load_manifests()

    # ---------- manifest 加载 ----------
    def _load_manifests(self) -> None:
        for d in (_SEED_DIR, _USER_DIR):
            if not d.is_dir():
                continue
            for path in sorted(d.glob("*.yaml")) + sorted(d.glob("*.yml")):
                try:
                    import yaml
                    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                except Exception as e:  # noqa: BLE001
                    logger.warning("[alliance] manifest 解析失败 %s: %s", path, e)
                    continue
                name = data.get("name")
                if not name:
                    continue
                data["_manifest_path"] = str(path)
                data["_source"] = "user" if d == _USER_DIR else "seed"
                data["_installed"] = self._probe_installed(data)
                self.skills[name] = data  # 用户目录覆盖种子

    @staticmethod
    def _probe_installed(manifest: Dict[str, Any]) -> bool:
        mod = manifest.get("python_module")
        if not mod:
            return False
        try:
            importlib.import_module(mod)
            return True
        except Exception:  # noqa: BLE001
            return False

    def reload(self) -> None:
        self.skills.clear()
        self._load_manifests()

    # ---------- 查询 ----------
    def list_available_skills(self) -> List[Dict[str, Any]]:
        return [{"name": s["name"], "category": s.get("category", "unknown"),
                 "author": s.get("author", ""), "description": s.get("description", ""),
                 "intents": s.get("intents", []), "installed": s.get("_installed", False),
                 "source": s.get("_source", "seed"), "tags": s.get("tags", []),
                 "fallback": s.get("fallback", "")} for s in self.skills.values()]

    def describe_skill(self, skill: str) -> Dict[str, Any]:
        return self.skills.get(skill, {"name": skill, "category": "unknown", "status": "unknown"})

    def skills_for_intent(self, intent: str) -> List[Dict[str, Any]]:
        return [s for s in self.skills.values() if intent in (s.get("intents") or [])]

    # ---------- 路由决策 ----------
    def route(self, brief: Dict[str, Any], intent: str,
              skill_override: "str | None" = None) -> Dict[str, Any]:
        """返回 {intent, skill, decision, output_path, candidates}；decision ∈ local/fallback/installed/unknown-skill"""
        if intent not in CONTENT_TYPES:
            intent = "landing"
        decision: Dict[str, Any] = {
            "intent": intent, "skill": None, "decision": "local",
            "output_path": None, "fallback_of": None, "candidates": [],
        }
        candidates = self._score_candidates(brief, intent)
        decision["candidates"] = [
            {"name": c["name"], "score": c["_score"], "installed": c.get("_installed", False)}
            for c in candidates
        ]
        if skill_override:
            s = self.skills.get(skill_override)
            if not s:
                decision["decision"] = "unknown-skill"
                decision["skill"] = skill_override
                return decision
            candidates = [s] + candidates
        if not candidates:
            return decision
        chosen = candidates[0]
        decision["skill"] = chosen["name"]
        decision["_score"] = chosen["_score"]
        if chosen.get("_installed"):
            decision["decision"] = "installed"
        else:
            decision["decision"] = "fallback"
            decision["fallback_of"] = chosen.get("fallback", "local")
        return decision

    def _score_candidates(self, brief: Dict[str, Any], intent: str) -> List[Dict[str, Any]]:
        """4 维加权：intent(0.5) + tag 命中(+0.15) + installed(+0.20) + user-override(+0.05)"""
        text_blob = json.dumps(brief, ensure_ascii=False).lower() if brief else ""
        if isinstance(brief, dict):
            text_blob += " " + str(brief.get("content", {}).get("core_message", ""))
        cands = self.skills_for_intent(intent)
        for c in cands:
            score = 0.5
            tags = [t.lower() for t in (c.get("tags") or [])]
            for tag in tags:
                if tag and tag in text_blob:
                    score += 0.15
            if c.get("_installed"):
                score += 0.20
            if c.get("_source") == "user":
                score += 0.05
            c["_score"] = round(score, 3)
        return sorted(cands, key=lambda c: c["_score"], reverse=True)

    # ---------- 真实调用（v0.2 新增） ----------
    def invoke(self, skill_name: str, params: Dict[str, Any],
               timeout_s: int = 120) -> Dict[str, Any]:
        """调用联盟 skill entry。失败 → 自动按 manifest.fallback 找下一个候选。
        返回 {success, skill, stdout, stderr, returncode, output_path, fallback_used, error}
        """
        result = self._invoke_once(skill_name, params, timeout_s)
        if not result["success"]:
            fb = self.skills.get(skill_name, {}).get("fallback", "")
            if fb.startswith("local:"):
                fb_intent = fb.split(":", 1)[1]
                tried = {skill_name}
                for cand in self.skills_for_intent(fb_intent):
                    if cand["name"] in tried:
                        continue
                    tried.add(cand["name"])
                    alt = self._invoke_once(cand["name"], params, timeout_s)
                    alt["fallback_used"] = True
                    alt["fallback_from"] = skill_name
                    if alt["success"]:
                        result = alt
                        break
                else:
                    result.setdefault("fallback_used", True)
        self._log_call(skill_name, params, result)
        return result

    def _invoke_once(self, skill_name: str, params: Dict[str, Any],
                     timeout_s: int) -> Dict[str, Any]:
        manifest = self.skills.get(skill_name)
        if not manifest:
            return self._err(skill_name, f"unknown skill: {skill_name}")
        if not manifest.get("_installed"):
            return self._err(skill_name, f"skill not installed: {skill_name}")
        entry = manifest.get("entry", "")
        if not entry:
            return self._err(skill_name, "manifest.entry missing")

        # P0 #1 安全修复：用 shlex.split + 占位符替换 + 重新 quote，构造列表式 argv，
        # 配合 shell=False，杜绝 `; rm -rf` / `| sh` / `$(...)` 等注入。
        ok, cmd_argv_or_err = self._build_safe_argv(entry, params)
        if not ok:
            return self._err(skill_name, f"unsafe manifest.entry rejected: {cmd_argv_or_err}")

        out_path = params.get("output")
        try:
            proc = subprocess.run(cmd_argv_or_err, shell=False, capture_output=True, text=True,
                                  timeout=timeout_s, encoding="utf-8", errors="replace")
            ok = proc.returncode == 0
            return {
                "success": ok and bool(out_path and Path(str(out_path)).exists()),
                "skill": skill_name, "stdout": proc.stdout[-2000:], "stderr": proc.stderr[-1000:],
                "returncode": proc.returncode, "output_path": str(out_path) if out_path else None,
                "fallback_used": False,
                "error": None if ok else (proc.stderr or "subprocess failed")[-200:],
            }
        except subprocess.TimeoutExpired:
            return self._err(skill_name, f"timeout after {timeout_s}s")
        except Exception as e:  # noqa: BLE001
            return self._err(skill_name, f"{e.__class__.__name__}: {e}")

    # ---------- 安全（P0 #1 fix） ----------
    @classmethod
    def _sanitize_entry(cls, entry: str) -> str:
        """入口白名单校验：必须是已知解释器/命令开头，且不含可疑 shell 元字符。"""
        stripped = entry.lstrip()
        if not stripped:
            raise ValueError("empty entry")
        if not any(stripped.startswith(h) for h in _ALLOWED_ENTRY_HEADS):
            raise ValueError(f"entry head not in whitelist: {stripped[:32]!r}")
        # 防御性：即便白名单通过，仍拒绝裸 shell 重定向 / 管道 / 命令替换 / 背景运行
        for bad in (";", "&&", "||", "|", "`", "$(", ">", "<", "\n", "&"):
            if bad in stripped:
                raise ValueError(f"shell metachar in entry: {bad!r}")
        return stripped

    @classmethod
    def _safe_substitute(cls, argv: Sequence[str], params: Dict[str, Any]) -> List[str]:
        """对 argv 中每个 token，替换 {key} → shlex.quote(str(params[key]))，未知 key → 留空串。"""
        out: List[str] = []
        for token in argv:
            def repl(m: re.Match[str]) -> str:
                key = m.group(1)
                if key not in params:
                    return ""
                return shlex.quote(str(params[key]))
            out.append(_PLACEHOLDER_RE.sub(repl, token))
        return out

    @classmethod
    def _build_safe_argv(cls, entry: str, params: Dict[str, Any]) -> "tuple[bool, List[str] | str]":
        """把 manifest.entry 转成安全 argv 列表。返回 (True, [...]) 或 (False, error_msg)。"""
        try:
            safe_entry = cls._sanitize_entry(entry)
        except ValueError as e:
            return False, str(e)
        # POSIX 风格分词；manifest.entry 一般不用 Windows quoting，所以 shlex 足够。
        # Windows 下 shlex 可能报 ValueError——回退到简单 split。
        try:
            base = shlex.split(safe_entry, posix=True)
        except ValueError:
            base = safe_entry.split()
        if not base:
            return False, "entry splits to empty argv"
        return True, cls._safe_substitute(base, params)

    @staticmethod
    def _err(skill: str, msg: str) -> Dict[str, Any]:
        return {"success": False, "skill": skill, "error": msg,
                "output_path": None, "fallback_used": False, "stdout": "", "stderr": "",
                "returncode": -1}

    def _log_call(self, skill_name: str, params: Dict[str, Any],
                  result: Dict[str, Any]) -> None:
        try:
            _LOG_DIR.mkdir(parents=True, exist_ok=True)
            line = json.dumps({
                "ts": datetime.now().isoformat(timespec="seconds"),
                "skill": skill_name,
                "params_keys": sorted(params.keys()),
                "success": result.get("success"),
                "fallback_used": result.get("fallback_used", False),
                "returncode": result.get("returncode"),
                "error": (result.get("error") or "")[:120],
            }, ensure_ascii=False)
            (_LOG_DIR / "alliance.log").open("a", encoding="utf-8").write(line + "\n")
        except Exception:  # noqa: BLE001
            pass
