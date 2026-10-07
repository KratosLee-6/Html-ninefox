# Full homepage (archive)

> The complete homepage as of 2026-10-07, kept for reference. The new homepage
> keeps the latest features, architecture, modules, video and version history only.

<div align="center">
  <img src="htmlninefox/server/static/logo-horizontal.svg" width="430" alt="HtmlNineFox Pixel Garden Logo">
  <h1>HtmlNineFox · Visual HTML Creation Workbench</h1>
  <p><strong>Bring text, files, images, reusable HTML templates, and skills onto one infinite canvas. Analyze, recommend, compose, generate, and revise real single-file HTML deliverables.</strong></p>
  <p>A personal open-source project by <a href="https://github.com/KratosLee-6">KratosLee</a> · Offline rules included · AI is optional</p>
  <p><a href="README.md">简体中文</a> · <strong>English</strong></p>
</div>

<div align="center">

[![App Release](https://img.shields.io/badge/app-v0.7.0-173C8F)](https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.7.0)
[![DSH Plugin](https://img.shields.io/badge/DSH_plugin-0.1.0--preview.1-49B894)](https://github.com/KratosLee-6/Html-ninefox/releases/tag/dsh-htmlninefox-v0.1.0-preview.1)
[![Build Packages](https://github.com/KratosLee-6/Html-ninefox/actions/workflows/build-release-packages.yml/badge.svg)](https://github.com/KratosLee-6/Html-ninefox/actions/workflows/build-release-packages.yml)
[![Test CI](https://github.com/KratosLee-6/Html-ninefox/actions/workflows/test.yml/badge.svg)](https://github.com/KratosLee-6/Html-ninefox/actions/workflows/test.yml)
[![Tests](https://img.shields.io/badge/pytest-596%20passed%20%7C%202%20skipped-1F8A70)](docs/RELEASE-NOTES-v0.7.0.md)
[![Chromium E2E](https://img.shields.io/badge/Chromium%20E2E-22%2F22-173C8F)](docs/RELEASE-NOTES-v0.7.0.md)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB)](pyproject.toml)
[![License](https://img.shields.io/badge/License-MIT-D9A441)](LICENSE)

</div>

![HtmlNineFox Pixel Garden workbench (captured on v0.7.0)](assets/screenshots/v0.7.0/workbench-overview.png)

## Watch v0.7.0 turn a web page into an asset (73s)

[![Play the 67s page-decomposition real demo](assets/promo/poster-demo-v070.png)](https://raw.githubusercontent.com/KratosLee-6/Html-ninefox/main/assets/promo/htmlninefox-demo-v070-16x9.mp4)

**The real chain**: paste `example.com` (Google Fonts source · open licence) → the page lands in the review workbench → adopt as a template → cut into sections and generate → **the page's own prose appears inside the generated landing** → back at the workbench, it sits in the sidebar REAL HTML library. Every frame is a real recording: [`scripts/record_demo_film_v070.py`](scripts/record_demo_film_v070.py) drives the real v0.7.0 service; you can rerun the acceptance chain yourself via [`scripts/verify_page_blocks_chain.py`](scripts/verify_page_blocks_chain.py).

> **This is not animation, it is a screen recording.** The cursor really moves, the URL is really typed one character at a time, the candidate really lands in the review workbench, and the generated output is really scrolled through. Each caption bar matches an event that actually happened during the recording (the `events.json` timeline).
>
> The only generated elements are the **abstract open/close backdrops** (warm paper, square grid, cobalt and mint light), whose prompts forbid any text; the logo and every word are overlaid deterministically from the official SVG. Backdrop generator: [`scripts/generate_h3_clips_v070.py`](scripts/generate_h3_clips_v070.py). The opening 5s shows the brand logo, the closing 5s settles on the one-liner and the GitHub address. A text-to-video model is deliberately **not** used for interface footage: it renders CJK as garbled glyphs, places buttons arbitrarily and draws meaningless edges — the opposite of a working demonstration.

### The full storyline

| Time | What really happens |
|---|---|
| 0–5s | Brand open: H3 backdrop + pixel-fox logo and the brand line |
| 5–15s | The ⋯ menu → design intake; `example.com` typed in; Google Fonts source selected (open licence) |
| 15–26s | Real fetch → candidate "Example Domain" lands in the review workbench with its licence tag |
| 26–36s | Adopt as template → cut into sections and generate (real API) |
| 36–58s | Open the output and scroll past the page's own prose; all six content types consume these blocks |
| 58–68s | Back at the workbench: Example Domain sits in the sidebar REAL HTML library |
| 68–73s | Brand close: logo + one-liner + GitHub address |

The historical promo (v0.6.0 input-to-export flow, 50s/53s bilingual and 34s stills cuts) stays in [assets/promo](assets/promo).

## What it solves

HTML references, design templates, source files, and AI skills often live in separate folders. Many generators expose only template names or wireframes, forcing users to guess the final visual result.

HtmlNineFox turns the process into a visible workflow:

```text
Text / files / images / HTML
          ↓
     AI or offline analysis
          ↓
Recommended content type + real template + page recipe
          ↓
A. Accept and generate
B. Open the infinite canvas and compose layouts / content / styles / files / skills
          ↓
       Single-file HTML
          ↓
  Revise with natural language feedback, keeping rev history
```

## Current release and latest progress (v0.7.0, released)

The application version is `0.7.0`, shipped under the tag `v0.7.0` on 2026-10-07. **v0.7.0 is a milestone: reverse-decompose a web page — turn an existing page's sections into a structurally editable project.** Until now you could "generate a page from a description"; now you can bring in the section structure of a page that already exists, with the prose included or not, decided by licence:

- **The whole chain works.** `POST /api/intake/page-blocks` re-cuts an approved candidate's stored body into blocks the generation channel understands, and **all six content types consume them** (v0.6.4 had one — the other five silently dropped the page's content, and landing rendered a blank page). The endpoint is **read-only**: carrying a page's prose must be the user's decision, never a side effect of fetching.
- **Copyright is decided per field.** Only an `open` licence carries prose (`verbatim`); `reference` / `inspiration-only` contribute structure and order only (`structure_only`, the output falls back to its own copy). The block path and the approve path that imports a whole page into the template gallery now ask **one shared rule function** — this release also removes an existing contradiction where a `reference` page was told "structure only" on one path while its whole HTML was copied verbatim into the gallery on the other.
- **Three more green-but-broken defects, found by release verification against real data:**
  ① a production-shaped fetch **crashed the instant it succeeded** (`resolver=None` reached the post-fetch rebinding check — shipped in v0.6.2, v0.6.3 and v0.6.4, because every test injects a resolver); ② the real endpoint emitted `heading == content`, so **every page's prose rendered twice in all six intents** (the "exactly once" gate's fixture had a heading different from its content, so it could not see its own endpoint's shape); ③ a section directly inside a section was still swallowed into one summary (the non-greedy regex ended the outer match at the inner close — only the siblings-inside-a-container shape had been fixed). Each fix carries a gate that must go red when the fix is removed, plus mutations.

> Design-intake fetching was broken in v0.6.2 — **skip v0.6.2**. v0.6.1 (slide-editor race fix, real operating recordings), v0.6.0 (the design-intake and editable-PPTX pillars) and v0.6.3 / v0.6.4 (gate hardening) are unaffected — see their [release notes](docs/RELEASE-NOTES-v0.6.0.md). **Upgrading from v0.6.1 / v0.6.3 / v0.6.4 straight to v0.7.0 is recommended.**

| Track | Current state | Evidence |
|---|---|---|
| Application release | `v0.7.0`, released 2026-10-07 | [release page](https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.7.0) · [previous, v0.6.4](https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.6.4) |
| Release verification | Full suite `596 passed, 2 skipped` on Windows (`597 passed, 1 skipped` on Linux CI); **16 mutation scripts, all caught**; real-chain verification `15/15`; artefacts re-hashed after upload | [v0.7.0 release notes](docs/RELEASE-NOTES-v0.7.0.md) · [v0.7 design](docs/DESIGN-v0.7-page-decomposition.md) |


| DeepSeek Harness plugin | `0.1.0-preview.1`, versioned separately from the app | [plugin preview](https://github.com/KratosLee-6/Html-ninefox/releases/tag/dsh-htmlninefox-v0.1.0-preview.1) |

> **Fixed (release-blocking)**: the packaging pipeline used to only **build** artifacts, never **run** them — which let a Windows portable package that crashed the instant it started ship through four green build jobs. `desktop.py` used `sys.platform` without ever importing `sys`, and only the PyInstaller frozen entry point reaches that code, so the source test suite never loaded it. It is fixed now, with two new defenses: a static scan for unbound names in frozen entry points (`tests/test_frozen_entry_gates.py`), and a verification script that really launches the artifact (`packaging/verify_portable.py`). The same gate run also caught three defects of a recurring shape — the server side was complete, the UI was not: the export center had no PPTX option at all (so the headline feature was unreachable, and no test had ever clicked that dropdown), "batch fetch" called a function that was never defined, and the typography extractor was missing a parameter, which made the most permissive license tier produce no candidates at all. Full list in the [release notes](docs/RELEASE-NOTES-v0.6.0.md#修复).

### Feature-to-screenshot map

#### Workbench and canvas (v0.6.0 captures, 6 shots)

The six shots below were taken from the current `v0.7.0` code; the desktop captures carry the `v0.7.0` topbar badge:

<table>
<tr>
<td width="50%"><img src="assets/screenshots/v0.7.0/workbench-paper-1440.png" alt="Desktop workbench (Pixel Paper)"><br><b>Desktop workbench (Pixel Paper)</b><br>Three-column hierarchy: library · infinite-canvas workspaces · inspector.</td>
<td width="50%"><img src="assets/screenshots/v0.7.0/workbench-night-1440.png" alt="Desktop workbench (Pixel Night)"><br><b>Desktop workbench (Pixel Night)</b><br>Full dark theme on the same hierarchy; primary button and weak foreground text now clear WCAG AA.</td>
</tr>
<tr>
<td width="50%"><img src="assets/screenshots/v0.7.0/workbench-overview.png" alt="Workspace management"><br><b>Workspace management</b><br>Real state after creating a second workspace: nav cards side by side, and the inspector renames and recolors a workspace in place.</td>
<td width="50%"><img src="assets/screenshots/v0.7.0/workbench-tablet-768.png" alt="Tablet 768 layout"><br><b>Tablet 768 layout</b><br>Sidebar folds into topbar drawers; canvas keeps semantic zoom.</td>
</tr>
<tr>
<td width="50%"><img src="assets/screenshots/v0.7.0/workbench-mobile-390.png" alt="Mobile task view (390px)"><br><b>Mobile task view (390px)</b><br>Workspace actions and node cards replace an unreadable scaled canvas; the progress strip shows only the current and failed steps.</td>
<td width="50%"><img src="assets/screenshots/v0.7.0/sidebar-templates.png" alt="Sidebar REAL HTML template library"><br><b>Sidebar REAL HTML template library</b><br>Template name and description stack vertically, each clamped to 2 lines, revealing one more card per screen.</td>
</tr>
</table>

#### Input, inspectors, memory and revisions

All of the following are re-captured on the current `v0.6.0` build.

**Input & inspectors**

<table>
<tr>
<td width="50%"><img src="assets/screenshots/v0.6.3/input-brief.png" alt="One entry for everything"><br><b>One entry for everything</b><br>Text, files and images share a single entry; AI analysis recommends a composition.</td>
<td width="50%"><img src="assets/screenshots/v0.6.3/command-palette.png" alt="Command palette"><br><b>Command palette</b><br>Ctrl+K to open, type to jump, every action shows its shortcut.</td>
</tr>
<tr>
<td width="50%"><img src="assets/screenshots/v0.6.3/node-inspector.png" alt="Requirement node inspector"><br><b>Requirement node inspector</b><br>Edit text and attachments on selection; advance to the workspace.</td>
<td width="50%"><img src="assets/screenshots/v0.6.3/output-inspector.png" alt="Output node inspector"><br><b>Output node inspector</b><br>Revision badge, recipe run, adoption, conversational feedback, export entry.</td>
</tr>
</table>

**Project Memory, revisions & cancel**

<table>
<tr>
<td width="50%"><img src="assets/screenshots/v0.6.3/project-memory.png" alt="Project Memory"><br><b>Project Memory</b><br>Brand, audience, tone, forbidden patterns and templates stay local and are reused next time.</td>
<td width="50%"><img src="assets/screenshots/v0.6.3/revision-restore.png" alt="Revision history and restore"><br><b>Revision history and restore</b><br>Feedback, reruns and restores all snapshot; restore creates a new revision.</td>
</tr>
<tr>
<td width="50%"><img src="assets/screenshots/v0.6.3/generation-cancel.png" alt="Cancel generation"><br><b>Cancel generation</b><br>Queued jobs cancel for real; running jobs honestly switch to stop-waiting.</td>
<td width="50%"><img src="assets/screenshots/v0.6.3/classic.png" alt="Classic form mode"><br><b>Classic form mode</b><br>One-line Brief straight to HTML, same brand system as the workbench.</td>
</tr>
</table>

**Export Center (real export flow)**

<table>
<tr>
<td width="50%"><img src="assets/screenshots/v0.6.3/export-ready.png" alt="Export analysis ready"><br><b>Export analysis ready</b><br>Compatibility score, page model, dynamic features, engine status; PPTX is offered for deck artifacts.</td>
<td width="50%"><img src="assets/screenshots/v0.6.3/export-center-pptx.png" alt="PPTX export result"><br><b>PPTX export result</b><br>Both the .pptx and the report are downloadable; the report lists editable elements and degradations.</td>
</tr>
</table>
Full set of 24 (including 6 real generated outputs) lives in [assets/screenshots/v0.5.0/](assets/screenshots/v0.5.0/); the list and reproduction commands are in [the screenshots README](assets/screenshots/README.md).

> The v0.6.0 captures are all produced by re-runnable gates
> (`tests/test_v060_visual_evidence_states.py` and `tests/test_v061_visual_evidence_states.py`),
> not hand-shot. The only remaining `v0.5.0/` references are the **six generated
> artifacts** — they come from a real generator run rather than a UI screenshot,
> and the artifact structure is unchanged in v0.6.0.

#### Full screenshot inventory

| Directory | Count | Contents |
|---|---:|---|
| `assets/screenshots/v0.7.0/` | **11** | Current build: 6 workbench + 5 page-decomposition real-chain shots (review workbench / approved / page sections in output / doc output / adoption loop) |
| `assets/screenshots/v0.6.3/` | **23** | v0.6.3 build: 7 workbench, 4 input & inspectors, 4 memory/revision/cancel/classic, 3 design intake, 3 slide editor / PPTX, 1 mobile library, 1 report |
| `assets/screenshots/v0.5.0/` | 24 | Full v0.5.0 set, including 6 real generated-output shots |
| `assets/screenshots/v0.4.0/` | 5 | Historical: Pixel Garden, LLM config, Docker, Export Center |

See the [screenshot notes](assets/screenshots/README.md) for the full listing and reproduction commands.

## v0.5.0 Stable Capabilities (history)

![Crash-recoverable commits and lifecycle modules](assets/screenshots/v0.6.3/generation-cancel.png)

- **🧠 Project Memory**: Brand, audience, tone, forbidden patterns, template, primary color, and font stay local and remain editable, disableable, and clearable.
- **♡ Learn only after adoption**: Long-term memory changes only when the user explicitly selects "Adopt this version and learn"; analysis, Recipe Run, and the inspector explain what was reused (explainable reuse).
- **🛡 Crash-recoverable Project commits**: One durable write primitive plus a commit journal — a killed process or power loss rolls back deterministically to the last consistent revision; a cross-process file lock turns concurrent CLI/server access into a stable `project_busy` conflict.
- **🧩 Browser lifecycle modules + generation cancel**: Project / Generation / Revision / Export are isolated modules; one in-flight generation per workspace, cancellable while waiting — queued jobs cancel for real, running jobs honestly switch to stop-waiting.
- **⏳ Revision history and restore**: Feedback, reruns, and restores keep HTML + generation-state snapshots; restoring creates a new revision and never overwrites history.
- **📤 Export Center**: Export PDF, paginated PNG, or a full-page image with a compatibility score and `export-report.json`.
- **🔒 Privacy boundary**: API keys, attachment bodies, and full private feedback text stay out of long-term memory and diagnostics.

## Design intake pipeline (new in v0.6)

<table>
<tr>
<td width="50%"><img src="assets/screenshots/v0.6.3/intake-review-pending.png" alt="Review workbench"><br><b>Review workbench · pending</b><br>All three license tiers, source badges, token swatches, outline and intake metrics.</td>
<td width="50%"><img src="assets/screenshots/v0.6.3/intake-approved-absorption.png" alt="Approved and ingested"><br><b>Approved · ingested</b><br>Style preset, component import and motion absorption, with metrics updating live.</td>
</tr>
<tr>
<td width="50%"><img src="assets/screenshots/v0.6.3/intake-preview-sandbox.png" alt="CSP sandbox preview"><br><b>CSP sandbox preview</b><br>Candidate pages render in a scriptless sandbox; candidate scripts never run.</td>
<td width="50%"><img src="assets/screenshots/v0.6.3/motion-lab-intake-motion.png" alt="Motion lab"><br><b>Motion lab</b><br>Absorbed original motion clamped to budget, honoring reduced-motion preferences.</td>
</tr>
</table>

Turn the world's best designs into your own assets across six layers — templates, styles, components, decorations, motion, and content — through three intake channels:

- **✋ Manual import**: paste single or batch URLs (up to 10), or import a ZIP template pack — everything lands in the review workbench
- **🕸 Built-in source registry**: 12 design sources (Land-book, Lapa.ninja, Landingfolio, Awwwards, Codrops, Animista, Google Fonts…) across gallery/component/motion/typography kinds, fetched safely (private-network and rebinding rejection, per-source rate limits)
- **🤖 AI analysis**: candidates get design descriptions, tags, layout notes and content recipes from your configured LLM (optional; everything works without a key)

Every asset passes a **review workbench** (CSP-sandboxed preview + three-tier license governance: open / reference / inspiration-only) before entering the library — with batch adopt/reject, per-source filtering, and an intake metrics panel tracking candidates and ingested assets. Styles appear in the style panel, components drag onto the canvas to feed generation, motion styles land in the motion lab, all honoring motion preferences and budgets. All six layers (templates, styles, components, decorations, motion, content) share the same absorb → review → ingest → use path.

## Page decomposition (new in v0.7)

<table>
<tr>
<td width="50%"><img src="assets/screenshots/v0.7.0/intake-page-blocks-pending.png" alt="Review workbench with a real candidate"><br><b>Review workbench · candidate with a licence tag</b><br>Paste a public URL and the page lands in the review workbench; since v0.7 an approved candidate's sections can be cut into generation blocks.</td>
<td width="50%"><img src="assets/screenshots/v0.7.0/output-landing-with-page-sections.png" alt="Page sections inside the generated output"><br><b>The sections you took · really in the output</b><br>For an open-licensed page the headings and prose travel with the generation; all six content types consume the channel.</td>
</tr>
</table>

v0.7 extends "absorb" past the template gallery into **generation**: `POST /api/intake/page-blocks` re-cuts an approved candidate's sections into blocks the generation channel understands (nested sections included), and all six content types consume them — with copyright decided per field:

| Licence | Blocks carry prose | Whole page enters the template gallery |
|---|---|---|
| `open` | ✅ `verbatim` | ✅ |
| `reference` | ❌ `structure_only` (generation falls back to its own copy) | ❌ |
| `inspiration-only` | ❌ `structure_only` | ❌ |

Carrying a page's prose must be the user's decision: the endpoint is read-only and never writes back. The real-chain acceptance script ships with the repository (`scripts/verify_page_blocks_chain.py`); the release notes document the three green-but-broken defects this chain's verification found and fixed — including one where a production-shaped fetch crashed the instant it succeeded, shipped in v0.6.2–v0.6.4.

## Editable PPTX (new in v0.6)

<table>
<tr>
<td width="50%"><img src="assets/screenshots/v0.6.3/slide-editor-dialog.png" alt="In-workbench slide editor"><br><b>In-workbench slide editor</b><br>Every editable text node, page by page; saving creates a new revision.</td>
<td width="50%"><img src="assets/screenshots/v0.6.3/export-center-pptx.png" alt="Export center PPTX"><br><b>Export center · PPTX</b><br>PPTX is offered for deck artifacts; the run yields both the .pptx and its report.</td>
</tr>
</table>

- **📄 Standards-compliant .pptx export**: deck artifacts export through python-pptx into a standards-compliant `.pptx` whose text frames stay editable in PowerPoint / WPS; anything that cannot be mapped is listed honestly in the degradation report ([report as captured](assets/screenshots/v0.6.3/pptx-export-report.png)).
- **🖥️ In-workbench slide editing**: open the structured slides dialog in the output inspector to rewrite titles and bullets; `PUT /slides` writes back with `expected_revision`, so a version conflict is reported instead of silently overwritten.
- **🔁 A real edit loop**: export after writing back and your edits survive in the exported PPTX.

## Complete Workbench Features

- **✅ Trustworthy release metadata**: Version, CLI, API, packages, Docker tag, test evidence, and Git tag stay aligned.
- **🎨 Pixel Garden Design System**: Unified design tokens (cobalt `#173C8F` + mint `#49B894` + warm paper `#F4F0E7`) across 5 visual artifacts.
- **🤖 Real LLM Integration**: MiniMax-M3 / Claude / GPT-4o with env auto-config; offline rules engine as fallback.
- **🤝 Skill Alliance**: baoyu-slide-deck (image-based PPT) · frontend-slides (no AI gradient) · beautiful-html-templates (28 stable presets).
- **🖥️ Web Workbench**: `htmlninefox app` launches local Web UI with live preview, agent logs, and template selection.
- **🐳 Docker Image**: `docker run htmlninefox` for cross-platform deployment; multi-stage build with env injection.
- **Real HTML template library**: 6 complete templates with 34 individually previewable pages — no more wireframe guessing.
- **Unified input**: Text, TXT, Markdown, JSON, CSV, HTML, and common image formats.
- **Dual paths**: Accept recommendations directly, or compose layouts/pages/styles/files/skills on the canvas.
- **Infinite canvas workspaces**: Global coordinates, renaming, per-workspace colors, navigation, snapping, and port connections.
- **User-controlled AI**: OpenAI-compatible, Ollama, or custom endpoints; API keys stay local.
- **Offline capable**: Deterministic rules engine works without API keys.
- **Feedback iteration**: Natural language feedback → design token changes → re-render with `rev1 / rev2 / ...` history.
- **Cross-platform**: Windows installer/portable, Linux `.run/.tar.gz`, Python CLI, Web/PWA, Docker.

> The [Export Center](docs/EXPORT-CENTER.md) supports four real export formats: `PDF`, paginated `PNG`, a full-page long `PNG`, and — added in v0.6 — `.pptx`. The first three produce real files plus `export-report.json`; `.pptx` goes through python-pptx's controlled mapping, so text frames stay genuinely editable in PowerPoint / WPS, and anything that cannot be mapped is listed honestly in the degradation report. Semantic DOCX export has been deferred to v0.6.x.

## See it in action

> The four shots below were taken on `v0.4.0` (2026-09-08) and record the moment the Pixel Garden design language was settled. These screens (template preview, AI model configuration, Docker deployment) **still exist as features**, but their layout has moved on with the v0.5 / v0.6 design convergence — for the current look, use the v0.6.0 captures in the [feature map](#workbench-and-canvas-v060-captures-6-shots).

<table>
<tr>
<td width="50%"><img src="assets/screenshots/v0.4.0/pixel-garden-unified.png" alt="Pixel Garden unified design"><br><b>Pixel Garden Unified Design</b><br>5 visual artifacts unified with cobalt + mint + warm paper.</td>
<td width="50%"><img src="assets/screenshots/v0.4.0/web-workbench.png" alt="Template preview dialog"><br><b>Template preview dialog</b><br>Preview real HTML templates page by page; add the whole set or extract one page.</td>
</tr>
<tr>
<td width="50%"><img src="assets/screenshots/v0.4.0/llm-integration.png" alt="AI model configuration dialog"><br><b>AI model configuration</b><br>OpenAI-compatible endpoint, locally stored API key, connection test; offline rules without a key.</td>
<td width="50%"><img src="assets/screenshots/v0.4.0/docker-deploy.png" alt="Docker deployment"><br><b>Docker One-Click Deploy</b><br>docker run htmlninefox with multi-stage build and env injection.</td>
</tr>
</table>

### Six real output types

Generated by the e2e acceptance flow of the released `v0.5.0` (the artifact structure of all six generators is unchanged through v0.7.0 without page blocks):

| Landing | Dashboard | Deck |
|---|---|---|
| ![Landing](assets/screenshots/v0.5.0/output-landing.png) | ![Dashboard](assets/screenshots/v0.5.0/output-dashboard.png) | ![Deck](assets/screenshots/v0.5.0/output-deck.png) |

| Deck page 2 | Poster | Architecture document |
|---|---|---|
| ![Deck page 2](assets/screenshots/v0.5.0/output-deck-page2.png) | ![Poster](assets/screenshots/v0.5.0/output-poster.png) | ![Architecture document](assets/screenshots/v0.5.0/output-archdoc.png) |

## Download & Install

v0.7.0 was released on 2026-10-07; packages ship from the [v0.7.0 Release](https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.7.0). v0.6.1 / v0.6.3 / v0.6.4 users can upgrade in place (**skip v0.6.2**) — the project schema and data directory are unchanged; v0.7 adds page-block capability to existing projects while old projects keep their id-only `blocks` and behave exactly as before. The [DeepSeek Harness plugin preview](https://github.com/KratosLee-6/Html-ninefox/releases/tag/dsh-htmlninefox-v0.1.0-preview.1) is versioned separately.

Package naming is unchanged and the version segment follows the release. The filenames below are listed for `v0.7.0` and correspond one-to-one with the Release attachments:

| Platform | Recommended file | Usage |
|---|---|---|
| Windows 10/11 | `HtmlNineFox-Setup-0.7.0.exe` | Per-user installer with a Start menu entry |
| Windows 10/11 | `HtmlNineFox-Windows-x64-0.7.0.zip` | Extract and run `HtmlNineFox.exe`, no install needed |
| Linux | `HtmlNineFox-Linux-0.7.0.run` | `chmod +x` and run; installs to user directory |
| Linux / audit | `HtmlNineFox-Linux-0.7.0.tar.gz` | Inspectable full installation contents |
| macOS 14+ (Apple Silicon) | `HtmlNineFox-macOS-arm64-0.7.0.zip` | Extract, then right-click HtmlNineFox.app → Open to bypass Gatekeeper (unsigned) |
| Python 3.10+ | `htmlninefox-0.7.0-py3-none-any.whl` | `python -m pip install ./htmlninefox-0.7.0-py3-none-any.whl` |
| Docker | Build from source | `docker compose up --build`; tag CI verifies but does not publish the image |

> **What was actually verified**: since v0.6.4 every release artifact is **downloaded back and re-hashed byte-for-byte** by the release pipeline before the draft flips to published, and the Windows portable package is really launched in CI with a content-level check. Installers and the Linux / macOS artifacts are not exercised on this (Windows) machine; their verification is what CI runs, stated as such.

### Quick start

```bash
# 1. Install (choose one)
pip install htmlninefox
# or download release package
# or docker run htmlninefox

# 2. Configure LLM (optional; offline works too)
export MINIMAX_API_KEY="***"
# or export OPENAI_API_KEY="***"
# or export ANTHROPIC_API_KEY="***"

# 3. Launch Web workbench
htmlninefox app
# Open http://127.0.0.1:8620

# 4. Or direct CLI generation
htmlninefox expert "Build a SaaS landing page"

# 5. Revise or restore an existing Project
htmlninefox feedback --project ./output/ACTUAL-PROJECT --note "Make the title larger"
htmlninefox restore --project ./output/ACTUAL-PROJECT --revision 0 --expected-revision 2

# 6. Export an existing workbench project
htmlninefox export ./output/ACTUAL-PROJECT --format pdf
htmlninefox export ./output/ACTUAL-PROJECT --format png --scope pages --pages 1-3
```

## Version history

RC3-A through E completed the architecture hardening following the [`mattpocock/skills`](https://github.com/mattpocock/skills) research, domain-modeling, codebase-design, TDD, and code-review methods, and shipped as the stable `v0.5.0`; v0.6 builds on it with the design intake pipeline and editable PPTX; v0.7 turns an absorbed page into an editable project.

| Version | Date | Delivered | Record |
|---|---|---|---|
| **v0.7.0** | 2026-10-07 | **Page decomposition**: a page's own sections become a project's (`page_blocks_from_candidate` + `POST /api/intake/page-blocks`), all six content types consume the block channel, copyright decided per field across three licence tiers; `archive` branch added. Release verification against real data found and fixed three green-but-broken defects (a production-shaped fetch that crashed the instant it succeeded — shipped in v0.6.2–v0.6.4; the real endpoint's blocks rendered every page's prose twice; directly nested sections swallowed into one summary); gates `596 passed, 2 skipped` on Windows, 16 mutation scripts all caught, Chromium `22/22`, real-chain `15/15` | [Release](https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.7.0) · [release notes](docs/RELEASE-NOTES-v0.7.0.md) · [design doc](docs/DESIGN-v0.7-page-decomposition.md) |
| v0.6.4 | 2026-10-06 | Gate hardening: release artefacts downloaded back and re-hashed byte-for-byte before publishing; fixed a page's palette never reaching the output and `blocks` flattened to strings; C7 front-end kernel in two steps; gates `499 passed, 1 skipped`, 8 mutation scripts / 67 mutations all caught | [Release](https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.6.4) · [release notes](docs/RELEASE-NOTES-v0.6.4.md) |
| v0.6.3 | 2026-10-04 | Fixed v0.6.2's outbound fetch failing 100% of the time (headers landing in the body slot, missing `context`, SNI falling back to DNS); mutation testing exposed five lying gates; gates `414 passed, 1 skipped` | [Release](https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.6.3) · [release notes](docs/RELEASE-NOTES-v0.6.3.md) |
| v0.6.2 | 2026-10-04 | Connection-level IP pinning for design-intake fetches (the security direction was right; the implementation broke every fetch — **skip this release**) | [release notes](docs/RELEASE-NOTES-v0.6.2.md) |
| v0.6.1 | 2026-10-03 | Slide-editor race fix; 50s Chinese/English real-operation recordings (Playwright driving the real service); gates `403 passed` | [Release](https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.6.1) · [release notes](docs/RELEASE-NOTES-v0.6.1.md) |
| **v0.6.0** | 2026-10-01 | Design intake pipeline (multi-URL / ZIP import, 12 built-in design sources, three license tiers, CSP-sandboxed review workbench, AI design analysis, intake metrics); editable PPTX export plus the in-workbench slide editor; pre-release design convergence (7 font sizes / 4 weights / spacing scale tokens, first-paint canvas fit 0.33→0.80, contrast up to AA); fixed the Windows portable package crashing on startup and took artifact verification down to the content level; gates `387 passed, 1 skipped`, Chromium / WebKit `22/22` each | [Release](https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.6.0) · [release notes](docs/RELEASE-NOTES-v0.6.0.md) · [gate evidence](docs/test-evidence/v0.6.0-s17-20260929/README.md) |
| **v0.5.0 stable** | 2026-09-25 | RC3 wrap-up; Windows / Linux / wheel / Docker attachments with SHA-256 | [Release](https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.5.0) · [test report](docs/TEST-REPORT-v0.5.0.md) |
| RC3-E | 2026-09-25 | Browser lifecycle modules, generation cancel, export race guards | [iteration record](docs/ITERATION-RC3-E-20260925.md) |
| RC3-D | 2026-09-25 | Crash-recoverable Project commits (journal rollback), cross-process file locking, atomic generation publication | [iteration record](docs/ITERATION-RC3-D-20260925.md) |
| RC3-B2 / C | 2026-09-24 | Shared Generation / Feedback / Restore / Export use cases, CLI Restore | [RC3-C record](docs/ITERATION-RC3-C-20260924.md) |
| RC3 visual convergence | 2026-09-24 | Dual primary actions, four responsive tiers, semantic zoom, unified component states, classic mode back on Pixel Garden | [convergence record](docs/ITERATION-RC3-VISUAL-CONVERGENCE-20260924.md) |
| v0.5.0rc2 | 2026-09-18 | Revision history and restore, three-tier native motion, 100-node gate, accessibility, DSH plugin preview | [RC2 report](docs/TEST-REPORT-RC2-20260918.md) |
| v0.5.0rc1 | 2026-09-14 | Project Memory, command palette, Recipe Run, interaction system | [RC1 notes](docs/RELEASE-NOTES-v0.5.0rc1.md) |
| v0.4.2 stable | 2026-09-08 | Export Center (PDF / PNG with compatibility report) | [release notes](docs/RELEASE-NOTES-v0.4.2.md) |

Real evidence screenshots from historical releases:

<table>
<tr>
<td width="50%"><img src="docs/test-evidence/harness-plugin-20260918/harness-plugin-enabled.png" alt="htmlninefox plugin enabled in DeepSeek Harness"><br><b>DSH plugin enabled (rc2)</b><br>The final tarball installed into a fresh web profile; the plugin list shows htmlninefox as an enabled global plugin.</td>
<td width="50%"><img src="docs/test-evidence/harness-plugin-20260918/generated-poster.png" alt="Chinese poster generated and exported through the plugin"><br><b>Generate, revise, export chain (rc2)</b><br>Offline Chinese poster with dry-run and real feedback, then PDF and full-page PNG export; compatibility 100.</td>
</tr>
<tr>
<td width="50%"><img src="docs/test-evidence/motion-20260918/revision-history-desktop.png" alt="Revision history, diff and restore"><br><b>Revision history and restore (rc2)</b><br>Parent revision, restore source, labels, and line diffs; restoring creates a new revision.</td>
<td width="50%"><img src="docs/test-evidence/motion-20260918/motion-lab-desktop.png" alt="Native motion samples"><br><b>Motion lab (rc2)</b><br>Six sample interactions: feedback, selection, linking, stage changes, output ready, restore complete.</td>
</tr>
</table>

## Testing & Trust Evidence

All release gates for v0.7.0 were verified on October 7, 2026:

| Check | Result | Evidence |
|---|---:|---|
| Python + browser test suite (Windows local) | **596 passed, 2 skipped** (68 test files; Linux CI expected 597 passed / 1 skipped) | [v0.7.0 release notes · Verification](docs/RELEASE-NOTES-v0.7.0.md#验证) |
| Mutation testing | **16 scripts, all CAUGHT** (87 mutations, zero missed; P1/P4 rewritten, F1 added) | [same](docs/RELEASE-NOTES-v0.7.0.md#验证) |
| Browser end-to-end (bundled Chromium) | **22 / 22** | `e2e_verify.py` (verified 2026-10-07) |
| Real-chain verification | **15 / 15**: real public fetch → SSRF rejects private hosts → block cutting → six intents, each prose exactly once → feedback keeps the blocks → reference licence carries no prose | [acceptance script](scripts/verify_page_blocks_chain.py) (ships with the repo) |
| Release metadata consistency (`check_release_version.py`) | **consistent (v0.7.0)** | verified locally |
| Production-shaped fetch gate | `fetch_reference` called the way production calls it; mutation F1 locks it | [test_design_intake.py](tests/test_design_intake.py) |
| LLM integration | MiniMax-M3 / Claude / GPT-4o with env auto-config | [install docs](docs/INSTALL.md) |

> **How these gates were built this round**: the reverse-verification discipline stayed — remove the fix and the gate must go red. v0.7.0's additional lesson is that **the fixture's shape must look like real data**: the "exactly once" gate blocked double rendering but was bypassed by its own endpoint's heading == content shape. Calling the production shape once beats calling the fixture shape a hundred times. See the [release notes](docs/RELEASE-NOTES-v0.7.0.md).

All release gates for v0.6.0 were re-verified on September 29, 2026:

| Check | Result | Evidence |
|---|---:|---|
| Python + browser test suite | **387 passed, 1 skipped** (v0.5.0 baseline 303, 84 added this round) | [v0.6.0 gate evidence](docs/test-evidence/v0.6.0-s17-20260929/README.md) |
| —— design health / layout hierarchy / motion behavior | 6 + 8 + 6 | [Release notes · Verification](docs/RELEASE-NOTES-v0.6.0.md#验证) |
| —— generation quality | 50 (section order, content quality, final result, self-contained end-to-end artifacts) | [same](docs/RELEASE-NOTES-v0.6.0.md#验证) |
| —— action registry / revision write-back / frozen entry | 4 + 2 + 5 | [same](docs/RELEASE-NOTES-v0.6.0.md#验证) |
| JavaScript syntax (13 static JS files + inline check) | **all pass** | [same evidence](docs/test-evidence/v0.6.0-s17-20260929/README.md) |
| Chromium acceptance (bundled Chromium) | **22 / 22** | [same evidence](docs/test-evidence/v0.6.0-s17-20260929/README.md) |
| WebKit (Safari engine) acceptance | **22 / 22** | [same evidence](docs/test-evidence/v0.6.0-s17-20260929/README.md) |
| Built-package run | All four build jobs green (Windows / Linux / macOS / Docker); the **Windows portable package was really launched and passed** | [Release notes · Verification](docs/RELEASE-NOTES-v0.6.0.md#验证) |
| Release metadata consistency (`check_release_version.py`) | **consistent** | [same evidence](docs/test-evidence/v0.6.0-s17-20260929/README.md) |
| DSH registry and final tarball integration | **2 / 2 passed** | [integration record](docs/DEEPSEEK-HARNESS-INTEGRATION.md) |
| Revision history, restore, and the 100-node gate | **passed** (covered by the pytest suite) | [RC2 report](docs/TEST-REPORT-RC2-20260918.md) |
| Docker image | Dedicated tag-CI job builds and verifies | [build workflow](.github/workflows/build-release-packages.yml) |

> **How these gates were built this round**: every new gate was verified in reverse — remove the corresponding fix and the test must go red; otherwise the gate is discarded and rewritten. That discipline matters, because most defects caught this round share one shape: **the server-side capability was fully implemented, but the UI had no reachable entry point, and no test had ever clicked it.** The packaging workflow was changed on the same principle to "build, then actually run the artifact" — otherwise a package that crashes on startup can travel all the way to the Release behind four green jobs.

The published v0.5.0 release evidence — package attachments with SHA-256 and the Windows portable real-machine smoke — stays in the [v0.5.0 test report](docs/TEST-REPORT-v0.5.0.md); earlier evidence lives in the [v0.5.0rc3 test report](docs/TEST-REPORT-v0.5.0rc3.md) and [v0.4.2-environment.txt](docs/test-evidence/v0.4.2-environment.txt).

### Run from source

```bash
git clone https://github.com/KratosLee-6/Html-ninefox.git
cd Html-ninefox
pip install -e .
htmlninefox --help
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Design philosophy](docs/DESIGN.md)
- [Pixel Garden UI guide](docs/UI-GUIDE.md)
- [RC3 visual convergence record](docs/ITERATION-RC3-VISUAL-CONVERGENCE-20260924.md)
- [RC3-B2 shared Generation use case](docs/ITERATION-RC3-B2-20260924.md)
- [RC3-C shared Feedback, Restore, and Export use cases](docs/ITERATION-RC3-C-20260924.md)
- [RC3-D crash-recoverable commits and process locking](docs/ITERATION-RC3-D-20260925.md)
- [RC3-E isolated workbench lifecycle modules](docs/ITERATION-RC3-E-20260925.md)
- [v0.6.0 release notes](docs/RELEASE-NOTES-v0.6.0.md)
- [v0.6.0 test report](docs/TEST-REPORT-v0.6.0.md)
- [v0.6.0 stable delivery plan](docs/PLAN-v0.6.0-STABLE-20260927.md)
- [Pre-release design and architecture audits](docs/AUDIT-DESIGN-20260929.md) · [architecture](docs/AUDIT-ARCHITECTURE-20260929.md)
- [v0.5.0 stable delivery plan](docs/PLAN-v0.5.0-STABLE-20260924.md)
- [Examples](docs/EXAMPLES.md)
- [Roadmap](docs/ROADMAP.md)
- [Private template import](docs/PRIVATE-TEMPLATE-IMPORT.md)

## PPT editing tribute (v0.6)

The editable-PPT capability in v0.6 stands on two prior works, with gratitude:

- 🪄 **[Univer](https://github.com/dream-num/univer) (dream-num)** — the Apache-2.0 in-browser office engine (Sheets / Docs / Slides / Canvas in one runtime). The in-workbench slide visual editor (near-1:1 PowerPoint fidelity, PPT/PPTX import & export) is built on Univer Slides, vendored locally to stay offline-first.
- 📄 **[python-pptx](https://github.com/scanny/python-pptx) (Steve Canny)** — the MIT PowerPoint library powering the server-side .pptx bridge, so exported decks are truly text-editable in PowerPoint / WPS.

## Contributing

Issues and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT License · See [LICENSE](LICENSE)

---

<div align="center">
  <p><strong>让灵感在 HTML 里生长。</strong></p>
  <p>Html九尾狐 · Pixel Garden · 个人开源项目</p>
</div>
