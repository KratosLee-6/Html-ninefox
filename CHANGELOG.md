# Changelog

> 🦊 Personal project by [@KratosLee-6](https://github.com/KratosLee-6) · Not affiliated with any company · MIT licensed.

All notable changes to **Html九尾狐 / Fox-of-Nine-Tails HTML Studio** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.3.0b2] — 2026-09-01 · Real Template Gallery & Guided AI Composition

### Added

- Six original, real-HTML showcase templates inspired by Guizang editorial and Swiss layout methods, with page-level preview and extraction.
- Guided creation entry for text, documents, and images: analyze, recommend a composition, accept it, or continue with custom canvas assembly.
- Local AI model settings for OpenAI-compatible endpoints with secret-safe API responses and a built-in connection test.
- Persistent composition metadata for selected gallery, pages, attachments, skills, and recommendation mode.

### Changed

- Layout, content, and style palettes now prioritize real rendered HTML rather than wireframe-only thumbnails.
- Canvas generation consumes selected page blocks, uploaded context, skills, colors, fonts, and templates.
- PWA cache and cross-platform package version advance to Beta 2.

---

## [0.3.0b1] — 2026-09-01 · Cross-platform Installable Beta 1

### Added

- Unified `htmlninefox app` launcher with health-based browser opening and automatic port fallback.
- Windows portable PyInstaller bundle, branded icon pipeline, SHA256 output, and Inno Setup installer definition.
- Linux user-level self-extracting `.run` installer and inspectable `.tar.gz` package.
- Dockerfile, Docker Compose, uv launchers, desktop entry, and local-network deployment guidance.
- Packaging automation for current Windows and Linux release artifacts.

### Changed

- Windows portable builds keep configuration, cache, projects, and output in a movable `user-data` directory.
- Runtime health responses expose the distribution channel; Windows and Linux clients are now marked beta.
- Installation documentation now separates portable, installed, container, PWA, and shared-server modes.

---

## [0.2.5] — 2026-09-01 · Pixel Garden Brand Workbench

### Added

- Final editable SVG brand system: app icon, standalone mark, and horizontal lockup combining a pixel fox with HTML angle brackets.
- Pixel Paper and Pixel Night UI themes with persisted theme preference and synchronized browser theme color.
- Complete visual identity and UI specifications in `docs/VI.md` and `docs/UI-GUIDE.md`.
- Archived v0.2.4 workbench snapshot for design comparison.

### Changed

- Replaced the black-purple AI aesthetic with warm paper, cobalt, mint, night-blue, compact radii, fine pixel accents, and restrained offset shadows.
- Updated canvas grid, panels, nodes, workspaces, status components, palette colors, focus states, and responsive brand lockup.
- New workspaces now start with `fox-pixel-garden` instead of the legacy Vercel dark preset.
- PWA manifest, service-worker cache, static routes, package version, screenshots, and tests now target v0.2.5.

---

## [0.2.4] — 2026-08-31 · Workspace Management & Visual Systems

### Added

- Persistent workspace navigator with one-click locate, active-workspace state, direct editing, and per-workspace material counts.
- Workspace names, six identification colors, legacy snapshot migration, and whole-workspace dragging that preserves child positions.
- Per-workspace creation progress replacing the unusable global infinite-canvas timeline.
- Five original visual systems: Pixel Garden, Duotone Studio, Editorial Ink, Swiss Signal, and Soft Silver.
- Three real brand/UI direction boards with Html × nine-tailed-fox logo concepts.
- Design-source and license audit for Huashu Design and Guizang PPT Skill.

### Changed

- The primary “推进生成” action now targets the active workspace instead of the last-created workspace.
- Generated output nodes retain their originating workspace identity.
- Workspace snapping aligns against other workspaces and no longer jumps toward its own child nodes.
- Template cards expose their visual-system origin and render structure-level differences instead of token-only recoloring.

### Verified

- 135 Python/API tests, 19 isolated Chromium acceptance checks, and 30 multi-intent rich-preview renders pass.

---

## [0.2.3] — 2026-08-31 · Smooth Canvas & Live Template Preview

### Added

- Real HTML thumbnails for all six layout types and six built-in visual presets.
- Large preview dialog and a dedicated `GET /api/template-preview` endpoint.
- Left/right input and output ports with expanded hit targets and candidate highlighting.
- Grid snapping, edge/center alignment guides, and workspace containment on drop.
- A dedicated `canvas-engine.js` geometry module shared by drag, snap, ports, and edges.

### Changed

- Pointer movement is batched through `requestAnimationFrame` and persistence happens after the interaction instead of on every move.
- Node positioning uses one world-coordinate model and `translate3d`, preventing zoom-related DOM/model drift.
- Edge endpoints are measured from real port positions instead of fixed node offsets.

### Verified

- 28 focused Python/API tests and 11 real Chromium canvas/preview checks pass.

---

## [0.2.2] — 2026-08-31 · Recoverable Workbench

### Added

- Project rename, duplicate, details, and recoverable soft delete.
- Canvas Schema v1 with atomic server snapshots and automatic backup recovery.
- Persistent asynchronous jobs with queued/running/succeeded/failed/cancelled states.
- Privacy-conscious one-click diagnostic zip.
- Unified HTTP error contract with stable codes and request IDs.

### Changed

- Web generation now submits a job and polls its state instead of blocking on one long request.
- Project and workspace filesystem behavior is concentrated in `ProjectStore`.

### Verified

- Full pytest suite, JavaScript parsing, wheel resource checks, and a real async generation flow.

---

## [0.2.1] — 2026-08-31 · Cross-platform Foundation

### Added

- Installable PWA shell, manifest, service worker, application icon, and install guidance.
- Responsive mobile drawers and Pointer Events canvas interactions.
- `GET /api/capabilities` for future desktop and mobile clients.
- Real Python package source and tests in the public repository.

### Fixed

- Windows GBK terminal crashes when Rich prints emoji.
- Broken `brief list` / `brief add` CLI calls.
- Jinja2 is optional again; the native generator remains the zero-dependency fallback.
- Default LiteLLM config and all PWA/template resources are included in package data.

### Verified

- 90 pytest tests pass in both the development tree and public repository.
- Fresh user-directory smoke test generates a valid HTML artifact.

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