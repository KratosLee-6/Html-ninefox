# Architecture · 架构详解

> How the 5 agents, 3 sinks, and 1 router fit together — with code-level details.

---

## 🏛️ Layer Diagram (分层架构)

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 4: CLI / API                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ fox.cli      │  │ fox.server   │  │ fox.workbench│ (v0.3)    │
│  │ (expert CLI) │  │ (HTTP API)   │  │ (web UI)     │           │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘           │
├─────────┼──────────────────┼──────────────────┼─────────────────┤
│  LAYER 3: ALLIANCE ROUTER                                       │
│  ┌──────────────────────────────────────────────────────┐       │
│  │  alliance/router.py (280 LOC)                        │       │
│  │  - Manifest loader (YAML)                            │       │
│  │  - Skill registry (in-memory + disk)                │       │
│  │  - Run orchestrator (sequential + parallel)         │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                  │
│  Manifests:                                                     │
│    alliance/manifests/brief.yaml                                │
│    alliance/manifests/style.yaml                                │
│    alliance/manifests/generate.yaml                            │
├──────────────────────────────────────────────────────────────────│
│  LAYER 2: 5 AGENTS                                              │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌────────┐│
│  │ brief   │  │ style   │  │ asset   │  │generate │  │feedback││
│  │ agent   │  │ agent   │  │ agent   │  │ agent   │  │ agent  ││
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └────────┘│
├──────────────────────────────────────────────────────────────────│
│  LAYER 1: 3 SINKS (沉淀)                                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ brief_lib   │  │ template_lib│  │ feedback_lib│              │
│  │ (历史 brief) │  │ (jinja 模板) │  │ (历史反馈)  │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Data Flow (数据流详解)

```
[user.txt]
   │
   ▼
[1] brief agent   → parses →  BriefSpec {audience, goal, style_hint, asset_list, constraints, raw_text}
   │                       → writes to brief_lib/<hash>.json
   ▼
[2] style agent   → picks  →  StyleProfile {template_id, grid, typography, colors, best_for}
   │                       (reads template_lib/manifests/*.yaml, keyword-scores, picks top-1)
   ▼
[3] asset agent   → fetches →  assets/hero.png + assets/icon_*.svg + assets/logos.svg
   │                       (Unsplash + Iconify, cached to assets/_cache/)
   ▼
[4] generate agent → renders →  output.html (Jinja2 + BriefSpec + StyleProfile)
   │                       (bleach-sanitizes all user text — XSS-safe)
   ▼
[5] feedback agent → scores  →  feedback.json {score 0.0-1.0, issues, suggestions, next_iteration}
   │                       → writes to feedback_lib/<hash>.json
   │
   └─► if score < 0.8 AND iter < 3: re-run [3]+[4] with notes
```

---

## 🔌 Alliance Router Protocol (联盟路由协议)

The router (`alliance/router.py`) is **pluggable**. Any community skill can register itself via a YAML manifest:

```yaml
# alliance/manifests/community_swiss_minimal.yaml
id: swiss_minimal_v1
display_name: Swiss Minimal
version: 1.0.0
author: community
entry_point: community_swiss_minimal:render
inputs:
  - brief_spec
  - style_profile
outputs:
  - html_string
dependencies:
  - jinja2>=3.0
test_coverage: 0.85
```

Router responsibilities:

1. **Load manifests** on startup (YAML → dataclass)
2. **Validate** deps (pip check)
3. **Resolve** skill by ID (cache + hot-reload)
4. **Invoke** with input/output contract enforcement
5. **Sandbox** skill execution (resource limits, no FS writes outside `output/`)
6. **Log** runs to `alliance/_logs/<run_id>.json`

```python
# alliance/router.py (excerpt)
class Router:
    def __init__(self, manifest_dir: Path = Path("alliance/manifests")):
        self.manifests = self._load_manifests(manifest_dir)
        self.skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        self.skills[skill.id] = skill

    def run(self, skill_id: str, **inputs) -> Any:
        skill = self.skills[skill_id]
        # contract enforcement, sandboxing, logging
        return skill.invoke(**inputs)
```

---

## 🧠 Triple Sinks (三重沉淀) Mechanism

```
brief_lib/      → historical BriefSpec JSON · used by brief agent (similarity search)
template_lib/   → YAML manifests + .j2 templates · used by style agent + generate
feedback_lib/   → FeedbackSpec JSON + _rules.json · used by feedback + generate (preemptive fixes)
```

Each sink has: **Write path** (agents write on every run) · **Read path** (agents read at start of relevant step) · **Index** (fast lookup by hash) · **Retention policy** (default: keep all; v0.3 adds age-based pruning).

Detailed layout (per-sink structure, retention rules, indexing strategy) lives in `docs/DESIGN.md` → "三重沉淀 Design".

---

## 🖼️ Architecture Diagrams (引用)

Internal `04_架构图/` has 4 PNG diagrams (Xigou Tech internal only). For open-source, this `ARCHITECTURE.md` and the ASCII diagrams above are the source of truth.

---

## 🧪 Test Architecture (测试架构)

```
tests/
├── integration/   # 4/4 ✅  (brief→html, style routing, feedback loop, alliance pluggable)
├── security/      # 12/12 ✅ (input validation, output sanitization, asset sandboxing, …)
└── unit/          # per-agent + router unit tests
```

Run all: `pytest tests/ -v`. CI rejects PRs that break existing tests.

---

<p align="center"><sub>🦊 5 agents · 3 sinks · 1 router · open MIT license</sub></p>
