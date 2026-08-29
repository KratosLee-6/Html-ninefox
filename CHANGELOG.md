# Changelog

All notable changes to **Html九尾狐 / Fox-of-Nine-Tails HTML Studio** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.0] — 2026-08-29  ·  First Public Release Candidate

> 🎉 **First release with all 5 agents real, all 3 sinks real, full integration tests passing.**

### ✨ Added (新增)

- **5 AI agents fully implemented** (not stubs):
  - `brief agent` — parses free-form text into `BriefSpec` (v1.0 schema)
  - `style agent` — picks `StyleProfile` from `template_lib` (5 styles: swiss / brutalist / editorial / playful / corporate)
  - `asset agent` — fetches images / icons / fonts based on Brief
  - `generate agent` — renders HTML via Jinja2 + BriefSpec + StyleProfile
  - `feedback agent` — scores output (0.0–1.0), loops back to asset/generate if < 0.8
- **3 沉淀 libraries (sinks)**:
  - `brief_lib/` — historical Briefs for retrieval
  - `template_lib/` — Jinja2 .j2 templates + style metadata
  - `feedback_lib/` — scored feedback for next-run improvement
- **Alliance router** (`alliance/router.py`, ~280 LOC):
  - Manifest loader (YAML)
  - 3 alliance manifests: `brief.yaml` / `style.yaml` / `generate.yaml`
  - Pluggable registry for community skills
- **Expert CLI** (`fox/cli.py`):
  - `python -m fox.cli expert --brief ... --style ... --output ...`
  - 6 working artifacts: landing / dashboard / PPT / resume / poster / blog
- **6 Jinja2 templates** under `fox/templates/`

### 🧪 Tests (测试)

- ✅ **4/4 integration tests pass** — end-to-end Brief → HTML
- ✅ **12/12 security tests pass** — input validation, output sanitization, sandboxing

### 📚 Documentation (文档)

- README.md with ASCII architecture diagrams
- docs/DESIGN.md (design philosophy)
- docs/ARCHITECTURE.md (5-agent contract details)
- docs/EXAMPLES.md (5 real-world scenarios)
- docs/ROADMAP.md (v0.3 → v2.0)

---

## [0.1.0] — 2026-08-22  ·  Skeleton + Agent Definitions

> Skeleton release — agent classes defined but not yet wired.

### Added
- Project skeleton (Python package layout)
- 5 agent classes (placeholder implementations)
- BriefSpec v0.9 schema (draft)
- Alliance manifest format (draft)
- 3 placeholder templates (landing / dashboard / resume)

### Known Limitations
- Asset agent returns hardcoded URLs
- Feedback agent is a stub (always returns score=0.5)
- No integration or security tests yet

---

## [0.0.1] — 2026-08-15  ·  Research + Planning

> Pre-alpha. Feasibility study + brief methodology design.

### Added
- 飞书绝活方法论 (Feishue Juehuo Methodology) — Brief + 模板 + 反馈 三件套
- BriefSpec v0.5 (early draft)
- Comparison study: vs shadcn / Lovable / V0 / Figma-to-code
- 5-agent design (concept only)
- Alliance router concept

### Notes
- No code yet. Pure research.
- This is the foundation that 0.1.0 and 0.2.0 build on.

---

## 🗺️ Unreleased (Planned for 0.3.0)

- Real LLM API key integration (OpenAI / Claude / Gemini)
- Web UI workbench (browser-based)
- 3 additional styles (terminal / glassmorphism / bauhaus)
- Template marketplace (community contributions)
- Discord community channel

See [docs/ROADMAP.md](docs/ROADMAP.md) for the full plan.

---

[0.2.0]: https://github.com/your-org/html-nine-tails/releases/tag/v0.2.0
[0.1.0]: https://github.com/your-org/html-nine-tails/releases/tag/v0.1.0
[0.0.1]: https://github.com/your-org/html-nine-tails/releases/tag/v0.0.1
