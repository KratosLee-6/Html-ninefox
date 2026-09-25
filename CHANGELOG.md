# Changelog

> 🦊 Personal project by [@KratosLee-6](https://github.com/KratosLee-6) · Not affiliated with any company · MIT licensed.

All notable changes to **Html九尾狐 / Fox-of-Nine-Tails HTML Studio** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

- Shared `StudioApplication.generate()` request/result seam for CLI, HTTP, asynchronous Jobs, and DeepSeek Harness parameter mapping.
- Stable `prompt_required` and `generation_failed` application errors, typed verification, Recipe Run, Memory, and composition values.
- A tracked v0.5.0 delivery map with RC3-C, durable Project commits, browser lifecycle Modules, and final release gates.
- Shared `FeedbackRequest / FeedbackResult`, `RestoreRequest / RevisionResult`, and `ExportRequest / ExportResult` application Interfaces.
- A `htmlninefox restore` CLI command with expected-Revision conflict protection.
- A `durable` module with the single atomic-write primitive (fsync, retry-on-Windows-replace) and a cross-process file lock (msvcrt/flock, bounded timeout).
- A prepare/commit/recover journal for Project commits: interrupted writes roll back deterministically on the next `load_state`, and phantom revisions never enter history.
- A stable `project_busy` 409 error when another process holds a Project lock.
- Crash-safe generation publication: `run_expert` stages in a dot-prefixed `.gen-` directory and publishes by rename.

### Changed

- CLI generation now reuses Project Memory and the same application orchestration as the workbench while preserving environment-variable AI discovery.
- HTTP generation handlers now translate transport data and serialize results; attachment-only Jobs validate through the shared application seam.
- DeepSeek Harness documents and tests Generation, Feedback, Restore, and Export mappings, including `--expected-revision`.
- CLI and HTTP Feedback, Restore, and Export now delegate business orchestration to `StudioApplication` while preserving HTTP v1 and Revision behavior.
- Every Project-rooted writer (ProjectStore JSON, Project Memory, AI settings, Recipe Run, generation artifacts, `.foxstate.json`) now goes through the shared fsync-backed atomic write.
- Project rename, duplicate, and delete now run under the source Project lock, turning cross-process collisions into stable `project_busy` responses.

- Four browser lifecycle modules (`FoxProjects`, `FoxGeneration`, `FoxRevisions`, `FoxExports`) extracted from the workbench monolith with private draft state, namespace APIs, and race guards; one in-flight generation per workspace with a cancel control, and an export busy guard with stale-result tokens.
- A `[hidden]` CSS fallback so `.btn` display rules can no longer un-hide hidden controls.

### Fixed

- `StudioApplication.restore()` now holds the per-project lock again; the RC3-C HTTP migration had bypassed `ProjectStore.restore_revision()`, letting concurrent restores of one project pass the revision-conflict check together on the threaded server. Regression-covered by a concurrent-restore test.

### Verified

- Full local suite: `238 passed, 1 skipped` (12 durability + 4 lifecycle tests); Chromium e2e `22/22`.
- Generation, Feedback, Restore, and Export seams: `20 passed`; Chromium acceptance: restore/interaction suites pass; DeepSeek Harness: `2/2`.

---

## [0.5.0-rc3] — 2026-09-24 · Pixel Garden Visual Convergence

### Added

- RC3 Pixel Garden visual convergence with a simplified primary-action header, local SVG icons, semantic node zoom, and responsive desktop, tablet, and mobile task layouts.
- Reproducible Playwright evidence for the command palette, saved Project Memory, controlled Export Center errors, and restore-as-new-version completion.
- Fourteen real RC3 screenshots covering themes, dialogs, inspectors, generated output, export readiness, responsive layouts, error feedback, and recovery lineage.

### Changed

- Unified the workbench and classic form mode around the existing Pixel Garden paper, cobalt, mint, and terracotta design tokens.
- Standardized desktop and mobile control sizes, focus-visible rings, selected, disabled, busy, success, and error states without adding React or Anime.js.
- Added live status semantics to Project Memory and Export Center feedback regions.
- Limited pytest discovery to the project test suite so root-level runs do not enter protected caches inside historical Windows release bundles.
- Updated the README, UI guide, and RC3 iteration record with current pages, state evidence, screenshots, validation results, and the next product-engineering milestones.

### Verified

- Inline JavaScript syntax and standalone workbench JavaScript checks pass.
- 20 focused Playwright and product tests pass across visual convergence, commands, memory, motion, interaction, revisions, and export states.
- The complete local suite passes with `201 passed, 1 skipped`.

---

## [0.5.0-rc2] — 2026-09-18 · Revision History and Native Motion

### Added

- Version labels, source diffs, parent and restore lineage, and restore-as-new-version for generated projects.
- Native motion preferences for system, reduced, and off modes, plus a local `/motion-lab` with six interaction samples.
- Browser acceptance gates for keyboard focus, 390px layouts, and a 100-node / 99-edge canvas workflow.
- A separately versioned DeepSeek Harness plugin preview for generation, feedback, and PDF / PNG export workflows.

### Changed

- Feedback, regeneration, and restore now preserve HTML and generation-state snapshots instead of overwriting history.
- Progress feedback uses stable stage updates, bounded visible notifications, cancellable animation cleanup, and an eight-target decoration budget.
- Release documentation now separates the `v0.5.0rc2` application prerelease from the DSH plugin preview and the stable `v0.4.2` application.

### Fixed

- Reject stale concurrent restores with a revision conflict and protect the current artifact when validation or atomic replacement fails.
- Preserve legacy HTML-only histories while clearly marking revisions that lack enough state for a full restore.
- Prevent stale dialog focus callbacks and generation animation cleanup from affecting a newer interaction.

### Verified

- Full Python, HTTP, storage, generation, export, accessibility, performance, and Chromium suites.
- Chromium end-to-end generation, revision, canvas, and export workflows.
- Wheel isolation smoke, tagged Windows and Linux package builds, checksum publication, and Docker runtime verification.

---

## [0.5.0-rc1] — 2026-09-14 · Project Memory

### Added

- v0.5 interaction system with typed Toast feedback, reversible button busy states, accessible dialog focus management, and a global command registry.
- Ctrl+K now searches both workbench actions and canvas nodes with keyboard navigation.
- Browser regression coverage for notifications, busy states, command execution, node search, Escape handling, and focus restoration.
- Recipe Run records Analyze, Compose, Generate, Verify, and Deliver stages with timing, model/generator, fallback usage, and summarized inputs and outputs.
- Per-project `recipe-run.json` evidence, HTML quality-gate reports, parent run links, and partial Generate/Verify reruns.
- Local Project Memory for brand, audience, tone, forbidden patterns, preferred templates, colors, fonts, and adopted design decisions.
- Explicit adoption signals, memory management APIs, an editable memory dialog, and reuse explanations in analysis, Recipe Run, and the artifact inspector.

### Changed

- Canvas dragging is now fluid rather than continuously rounded to a 16px grid, with `Alt` available to temporarily disable snapping.
- Alignment and connection targets now use acquisition/release hysteresis to prevent jitter and flickering near snap boundaries.
- Smart linking now accepts a 48px port radius, a 76px release radius, and whole-card drops, while exact ports outrank sticky card candidates.
- Marquee selection now previews hits live: left-to-right requires full containment, right-to-left selects intersections, and Alt subtracts from the selection.
- Connection curves adapt their control distance to horizontal and vertical separation for smoother short and long links.
- Port geometry is derived from rendered bounds and converted to world coordinates, keeping connections aligned through zoom and pan.
- Fit-to-content preserves workspace navigator space and uses a 30% minimum zoom so generated content remains readable.
- The active workspace timeline now switches from a generic checklist to the actual Recipe Run and stage durations after generation starts.
- Job state reads and atomic writes share one lock, preventing Windows polling races from leaving jobs stuck at `starting`.

### Fixed

- Process the final pointer position before drag or connection release, preventing fast interactions from ending one frame behind.
- Keep port hit areas from stealing pointer events from card content and keep connection stroke width stable while zooming.
- Prefer a newly reached exact input port over a previous whole-card sticky target, preventing links from landing on a nearby wrong node.

### Verified

- 179/179 Python tests pass, including Recipe Run, interaction, canvas, generation, storage, security, diagnostics, and export coverage.
- 22/22 Chromium product checks pass across generation, workspaces, templates, themes, and the Export Center.
- 17/17 focused canvas checks cover workspace and card dragging, snapping, port connections, Recipe Run details, partial verification reruns, HTML preview, generation, feedback iteration, fit, persistence, and JavaScript errors.

### Planned

- 100-node performance, accessibility gates, artifact diffs, and version trees.
- High-fidelity PPTX, then constrained editable PPTX and semantic DOCX.

---

## [0.4.2] — 2026-09-08 · Export Center

### Added

- Local-first PDF and PNG export from generated HTML projects.
- Preflight manifest with pagination detection, compatibility score, dynamic-content warnings, and runtime diagnostics.
- Page-range parsing, paginated Deck export, long-page PNG, image scaling, PDF paper selection, and landscape mode.
- Persistent export jobs, secure download URLs, and per-run `export-report.json` files.
- Export Center UI in output/history inspectors and the `htmlninefox export` CLI command.

### Packaging

- Playwright is now a runtime dependency while browsers remain locally selected.
- Windows packages collect the Playwright driver and reuse Edge or Chrome.
- Linux offline wheelhouses include Playwright, pyee, and cross-platform greenlet wheels.
- Docker images include Chromium for deterministic server-side export.

### Verified

- 159 Python, API, storage, security, export, and browser tests pass.
- 22/22 real Chromium generation, canvas interaction, and Export Center checks pass.
- Wheel and Windows portable builds complete real PNG export smoke tests.
- Linux offline archives contain x86_64/aarch64 Playwright plus CPython 3.10–3.13 platform wheels.

### Architecture

- Adopted a routed `Analyze → Route → Render → Verify → Deliver` export pipeline inspired by ppt-master's workflow and quality-gate approach.
- Kept visual-fidelity exports separate from future editable PPTX/DOCX mappings.

## [0.4.1] — 2026-09-05 · Release Integrity Repair

### Fixed

- Unified package, CLI, API, Docker, installation documentation, and download names on version 0.4.1.
- Added a release metadata guard that rejects mismatched Git tags before packaging.
- Linux installers now receive their version from pyproject.toml during the build instead of a hard-coded value.
- Corrected the README server description from FastAPI to the actual local Python HTTP service.
- Repaired v0.4.1 test-evidence links and added the missing canvas-productivity.js syntax check.

### Packaging

- Windows release uploads now include both the installer and portable ZIP with checksums.
- Linux release uploads now include .run, .tar.gz, wheel, and checksums.
- Tag builds now verify the Docker image in a dedicated CI job.

### Verified

- 153 Python, API, storage, security, generation, and browser tests pass.
- 20/20 Chromium generation and workbench acceptance checks pass.

### Design

- Added an Export Center architecture for PDF, images, high-fidelity PPTX, editable PPTX, and semantic DOCX.

---

## [0.4.0] — 2026-09-05 · Pixel Garden, Workbench and Private Template Compounding

### Added

- Pixel Garden visual identity, paper/night themes, branded logo, and five original NineFox style presets.
- Real LLM runtime settings for OpenAI-compatible, MiniMax, Anthropic, and local-compatible endpoints.
- Web workbench and Docker deployment path.
- Local-only private template packages imported from one HTML file or a complete resource folder.
- Safe asset copying, multi-page detection, page-role mapping, design-token extraction, and private-template deletion.
- Canvas undo/redo, marquee selection, grouped movement, node locking, minimap navigation, and Ctrl+K search.

### Changed

- Private template pages, colors, fonts, source metadata, and design tokens now influence generated deliverables.
- Imported HTML previews run under a restrictive CSP sandbox.
- Usage counts and intent-aware ranking prioritize previously successful private templates.

### Verified

- 153 tests pass, including private-template security, canvas productivity, API, generation, and browser coverage.

---

## [0.3.0] — 2026-09-03 · 🎉 Third Major Release · Skill Alliance 3 PPT Skills

> 🎉 **v0.3.0 = v0.3.0b2 + 3 飞书绝活大会 PPT 技能集成**

### ✨ Added — 3 PPT Skills (from 飞书绝活大会)

- **🖼 [baoyu-slide-deck](https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-slide-deck)** (by [宝玉 JimLiu](https://github.com/JimLiu))
  - AI 画图生成每页 PPT · 17 套风格 · 图片版 PPT
  - 模板：`htmlninefox/templates/baoyu-slide-deck.html`
- **📑 [frontend-slides](https://github.com/zarazhangrui/frontend-slides)** (by [张咋啦](https://github.com/zarazhangrui))
  - 3 版首页选 · 避开 AI 紫渐变 · 单 HTML 文件
  - 模板：`htmlninefox/templates/frontend-slides.html`
- **🎨 [beautiful-html-templates](https://github.com/zarazhangrui/beautiful-html-templates)** (by [张咋啦](https://github.com/zarazhangrui))
  - 28 套稳定模板 · 字体配色不动
  - 模板：`htmlninefox/templates/beautiful-html-templates.html`

### 🔧 Changed — 5 类意图 generate_expert

- `generate_expert.py` 升级到 5 类意图：landing + ppt_image + ppt_html + html_template + infographic
- `rules.py` 加 ppt_image / ppt_html / html_template 关键词触发
- 优先级链：联盟 skill > 本地模板 > 占位
- `data/alliance/` 新增 3 个 manifest 种子（baoyu-slide-deck / frontend-slides / beautiful-html-templates）

### 🙏 Acknowledgments (v0.3 新增)

- 🎨 **[宝玉 (JimLiu)](https://github.com/JimLiu)** — baoyu-skills / baoyu-slide-deck
- 🎨 **[张咋啦 (zarazhangrui)](https://github.com/zarazhangrui)** — frontend-slides / beautiful-html-templates / beautiful-feishu-whiteboard
- (继承 v0.2 起：歸藏 / 花叔 / tt-a1i)

### 🧪 Tests

- ✅ 4/4 集成测试 · 146/146 pytest · 20/20 Chromium E2E
- ✅ P0 shell 注入已修 · 12/12 安全测试

### 📦 下载

- Windows 安装器：`HtmlNineFox-Setup-0.3.0.exe`
- Windows 便携：`HtmlNineFox-Windows-x64-0.3.0.zip`
- Linux：`HtmlNineFox-Linux-0.3.0.run` / `.tar.gz`
- Python wheel：`htmlninefox-0.3.0-py3-none-any.whl`

> v0.3.0 release 暂复用 v0.3.0b2 资产；下次 CI 重新构建 v0.3.0 品牌包。

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

### Verified

- 146 Python/API/storage/security/browser tests pass.
- 20/20 real Chromium generation and workbench acceptance checks pass.
- Windows portable health, six-item gallery, wheel contents, Linux installer structure, and SHA256 manifests were validated.
- Screenshots and raw test logs are committed under `assets/screenshots/v0.3.0b2/` and `docs/test-evidence/`.

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
