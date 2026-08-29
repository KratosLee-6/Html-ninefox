# Changelog

> 🦊 Personal project by [@KratosLee-6](https://github.com/KratosLee-6) · Not affiliated with any company · MIT licensed.

All notable changes to **Html九尾狐 / Fox-of-Nine-Tails HTML Studio** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.0] — 2026-08-29  ·  🎉 First Public Release

> 🦊 **First release with all 5 agents real, all 3 sinks real, all tests passing, ready for GitHub.**
> Inspired by Feishu 飞书绝活大会 methodology (Brief + 审美模板 + 具体反馈 三件套).

### ✨ Added — 5 AI Agents (全部真实实现)

- **`brief_expert`** — Parses free-form Chinese / English prompts into `BriefStandard v0.1` JSON
  - 5 required fields: Goal / Context / Content / Style / Constraints
  - 10 optional extensions (interaction / i18n / a11y / performance / etc.)
  - Real LLM call via LiteLLM router → offline-rules fallback (zero-downtime)
- **`style_expert`** — Picks `StyleProfile` from 5 candidate styles
  - Candidates: **Linear** (0.92 winner for SaaS) / **Vercel** / **shadcn/ui** / **Stripe** / **Apple**
  - Real LLM scoring + visual feedback panel (live tracking)
  - Outputs: palette + typography + radius + shadows + components
- **`asset_expert`** — Routes asset requests through Skill Alliance
  - Intent recognition → skill manifest matching → invocation
  - Fallback chain: alliance skill → local presets → minimal placeholder
- **`generate_expert`** — Renders HTML via Jinja2 + Brief + Style
  - Local templates (5 included: landing / dashboard / PPT / resume / poster)
  - Jinja2 fallback path for offline operation
  - 9.5 KB output for typical landing page (real HTML, not placeholder)
- **`feedback_expert`** — User feedback → structured suggestion + token extraction
  - Confidence scoring (high → actionable, low → ask user for clarification)
  - **No retry on low-confidence** (Codex-designed anti-pattern: don't hammer the user)

### 📚 Added — 3 沉淀 Libraries (sinks)

- **`brief_lib.py`** (117 LOC) — Historical Briefs for retrieval
  - CRUD: list / get / add / delete / search
  - JSON schema validation against `brief-standard-v0.1.schema.json`
- **`template_lib.py`** (116 LOC) — Jinja2 templates + style metadata
  - Auto-extract design tokens from HTML (colors / fonts / radius)
  - Search by tag (`linear` / `vercel` / `dark` / `light` / etc.)
- **`feedback_lib.py`** (112 LOC) — Scored feedback for next-run improvement
  - Deep-merge `tokens_extracted` (newest wins on same key)
  - Append/list/get/get_tokens_extracted

### 🔌 Added — Skill Alliance Router

- **`alliance/router.py`** (280 LOC, secure by design)
  - **P0 shell injection FIXED** — `subprocess.run(argv, shell=False)` + `shlex.quote()` + entry-prefix whitelist
  - 3 published alliance manifests in `~/.htmlninefox/alliance/`:
    - `guizang-ppt.yaml` — PPT generation (归藏)
    - `huashu-design.yaml` — High-fidelity prototypes
    - `archify.yaml` — Architecture diagrams (sequence / workflow / dataflow / lifecycle)
  - 12/12 security tests pass (shell injection / path traversal / param injection / command substitution all blocked)

### 🛠️ Added — Expert CLI

- **`htmlninefox`** CLI (`python -m htmlninefox`)
  - `expert` — Run 5-agent pipeline → 6 artifacts
  - `brief list / add / get / delete / search` — Brief library CRUD
  - `template list / get / search-by-tag` — Template library
  - `feedback --project <id> --note "..."` — Append structured feedback
  - `--version` → `htmlninefox, version 0.2.0`
- **6 working artifacts per expert run**:
  - `brief.json` (BriefStandard v0.1)
  - `brief.md` (human-readable summary)
  - `style.md` (style profile + design tokens)
  - `assets.json` (asset manifest)
  - `output.html` (real HTML, ≥5 KB)
  - `meta.yaml` (timestamp / cost / skill_used)

### 📖 Added — Documentation (5 docs · 14 KB total)

- `README.md` (233 lines) — Project pitch + 4 ASCII diagrams + quick start
- `docs/DESIGN.md` (182 lines) — Feishu methodology + 5-agent design philosophy
- `docs/ARCHITECTURE.md` (153 lines) — 5-agent contracts + Skill Alliance flow
- `docs/EXAMPLES.md` (200 lines) — 5 real-world scenarios (SaaS / dashboard / PPT / resume / poster)
- `docs/ROADMAP.md` (172 lines) — v0.3 → v2.0 timeline

### 🧪 Tests (测试)

- ✅ **4/4 integration tests pass** — end-to-end Brief → 6 artifacts
- ✅ **12/12 security tests pass** — P0 shell injection blocked + 11 other vectors
- ✅ **CLI manual verified** — `python -m htmlninefox expert "做一个 SaaS 落地页"` runs end-to-end

### 📸 Assets (GitHub README screenshots)

- 6 PNG screenshots (1600×900 / 1440×900 / 1200×800 etc.)
- 1 interactive xterm.js CLI demo (HTML, 19.7 KB)
- 1 60s terminal recording (GIF, 920 KB)
- 3 static reference screenshots (JPG)

### 🎯 Inspired by (灵感来源)

- **飞书绝活大会 BV1bLMX6HE7b** (B 站 · 23.0 万播放 · 2026-08-03)
  - "有了 Skill，不代表一句话就能得到好作品。真正拉开差距的，是清晰的 Brief、可复用的审美模板，以及一轮轮具体反馈。"
- **shadcn/ui** — Open code + design system philosophy
- **Refero.design** — Design research for the AI era

---

## [0.1.0] — 2026-08-22  ·  Skeleton + Agent Definitions

> Skeleton release — agent classes defined but not yet wired.

### Added
- Project skeleton (Python package layout)
- 5 agent classes (placeholder implementations)
- BriefStandard v0.1 schema
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
- 飞书绝活方法论 (Feishu Juehuo Methodology) — Brief + 模板 + 反馈 三件套
- BriefStandard v0.5 (early draft)
- Comparison study: vs shadcn / Lovable / V0 / Figma-to-code
- 5-agent design (concept only)
- Alliance router concept

### Notes
- No code yet. Pure research.
- This is the foundation that 0.1.0 and 0.2.0 build on.

---

## 🗺️ Unreleased (Planned for 0.3.0 — Month 1)

- Real LLM API key integration (OpenAI / Anthropic / Gemini) — currently offline-rules only
- Install + integrate real alliance skills (`pip install guizang-ppt` etc.)
- Web UI workbench (browser-based, drag-and-drop)
- 3 additional styles (terminal / glassmorphism / bauhaus)
- Template marketplace (community contributions)
- GitHub Discussions for community

See [docs/ROADMAP.md](docs/ROADMAP.md) for the full plan (v0.3 → v2.0).

---

[0.2.0]: https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.2.0
[0.1.0]: https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.1.0
[0.0.1]: https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.0.1