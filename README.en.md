<div align="center">
  <img src="htmlninefox/server/static/logo-horizontal.svg" width="430" alt="HtmlNineFox Pixel Garden Logo">
  <h1>HtmlNineFox · Visual HTML Creation Workbench</h1>
  <p><strong>Bring text, files, images, reusable HTML templates, and skills onto one infinite canvas. Analyze, recommend, compose, generate, and revise real single-file HTML deliverables.</strong></p>
  <p>A personal open-source project by <a href="https://github.com/KratosLee-6">KratosLee</a> · Offline rules included · AI is optional</p>
  <p><a href="README.md">简体中文</a> · <strong>English</strong></p>
</div>

<div align="center">

[![App Release](https://img.shields.io/badge/app-v0.5.0rc3-173C8F)](https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.5.0rc3)
[![DSH Plugin](https://img.shields.io/badge/DSH_plugin-0.1.0--preview.1-49B894)](https://github.com/KratosLee-6/Html-ninefox/releases/tag/dsh-htmlninefox-v0.1.0-preview.1)
[![Build Packages](https://github.com/KratosLee-6/Html-ninefox/actions/workflows/build-release-packages.yml/badge.svg)](https://github.com/KratosLee-6/Html-ninefox/actions/workflows/build-release-packages.yml)
[![Test CI](https://github.com/KratosLee-6/Html-ninefox/actions/workflows/test.yml/badge.svg)](https://github.com/KratosLee-6/Html-ninefox/actions/workflows/test.yml)
[![Tests](https://img.shields.io/badge/pytest-234%20passed%20%7C%201%20skipped-1F8A70)](docs/ITERATION-RC3-D-20260925.md)
[![Chromium E2E](https://img.shields.io/badge/Chromium%20E2E-22%2F22-173C8F)](docs/test-evidence/v0.4.2-chromium-e2e.txt)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB)](pyproject.toml)
[![License](https://img.shields.io/badge/License-MIT-D9A441)](LICENSE)

</div>

![HtmlNineFox RC3 Pixel Garden workbench](assets/screenshots/v0.5.0rc3-visual/workbench-paper-1440.png)

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

## Current release and `main` development snapshot (September 24, 2026)

The application version remains `0.5.0rc3`, published under the installable prerelease tag `v0.5.0rc3`, while `v0.4.2` remains the stable release. This RC3 prerelease packages the repository engineering baseline, shared workbench test-server fixture, and Pixel Garden visual and interaction convergence for Windows, Linux, and Python users.

| Track | Current state | Evidence |
|---|---|---|
| Application release | `v0.5.0rc3` prerelease, available as installable packages | [release](https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.5.0rc3) |
| RC3 application increment | RC3-D storage consistency is complete: one durable write primitive, commit journal with crash rollback, cross-process `.locks/` file locking, and atomic generation publication | [RC3-D record](docs/ITERATION-RC3-D-20260925.md) · [architecture](docs/ARCHITECTURE.md) |
| Current local verification | `234 passed, 1 skipped` including 12 durability tests; restore and interaction Chromium suites pass with real subprocess lock evidence | [RC3-D record](docs/ITERATION-RC3-D-20260925.md) |
| DeepSeek Harness plugin | Separately versioned `0.1.0-preview.1` | [plugin preview](https://github.com/KratosLee-6/Html-ninefox/releases/tag/dsh-htmlninefox-v0.1.0-preview.1) |

### RC3 visual and interaction convergence

The workbench keeps the existing Pixel Garden brand and native HTML/CSS/JavaScript architecture. No React migration, Anime.js dependency, external icon service, or unrelated example palette was introduced.

| Area | Delivered behavior |
|---|---|
| Information hierarchy | “Input requirements” and “Advance workspace” are the two primary actions; secondary tools move into the More menu |
| Responsive product flow | Full three-column desktop, inspector drawer, dual tablet drawers, and a readable mobile task view at `≤620px` |
| Semantic zoom | Overview below `0.78`, compact from `0.78` to `1`, and full editing detail at `≥1` |
| Component system | Consistent focus, selected, disabled, busy, success, error, and reduced-motion behavior with local SVG icons |
| Classic mode | Rejoined the same paper, cobalt, mint, terracotta, logo, typography, and form-state system |

<table>
<tr>
<td width="50%"><img src="assets/screenshots/v0.5.0rc3-visual/workbench-paper-1440.png" alt="RC3 Pixel Paper desktop workbench"><br><b>Desktop workbench</b><br>Three-column hierarchy and focused primary actions.</td>
<td width="50%"><img src="assets/screenshots/v0.5.0rc3-visual/workbench-mobile-390.png" alt="RC3 mobile task view"><br><b>Mobile task view</b><br>Workspace actions and node cards replace an unreadable scaled canvas.</td>
</tr>
<tr>
<td width="50%"><img src="assets/screenshots/v0.5.0rc3-visual/command-palette-search.png" alt="Command palette search"><br><b>Command palette</b><br>Keyboard search, active result, and shortcut feedback.</td>
<td width="50%"><img src="assets/screenshots/v0.5.0rc3-visual/revision-restore-complete.png" alt="Revision restore complete"><br><b>Restore complete</b><br>Real rev0 → rev2 restore with lineage and success feedback.</td>
</tr>
</table>

The RC3 evidence set contains 14 real screenshots, including Project Memory, controlled export errors, generated output, Export Center readiness, tablet drawers, and both themes.

## v0.5.0 RC Series Capabilities

![Project Memory and adoption signals](assets/screenshots/v0.5.0rc1/project-memory-dialog.png)

- **🧠 Project Memory**: Brand, audience, tone, forbidden patterns, template, primary color, and font stay local and remain editable, disableable, and clearable.
- **♡ Learn only after adoption**: Long-term memory changes only when the user explicitly selects “Adopt this version and learn.”
- **🔎 Explainable reuse**: Analysis, Recipe Run, and the artifact inspector show what was reused and what the current explicit request overrode.
- **🔒 Privacy boundary**: API keys, attachment bodies, and full private feedback text are excluded from long-term memory.
- **✅ RC1 verification**: 179/179 Python, API, storage, security, and Chromium browser tests pass.

> RC1 established the local project memory loop. RC2 adds revision history and restore, the 100-node gate, keyboard operation, and user-controlled motion.

## Complete Workbench Features

- **✅ Trustworthy release metadata**: Version, CLI, API, packages, Docker tag, test evidence, and Git tag stay aligned.
- **🎨 Pixel Garden Design System**: Unified design tokens (cobalt `#173C8F` + mint `#49B894` + warm paper `#F4F0E7`) across 5 visual artifacts.
- **🤖 Real LLM Integration**: MiniMax-M3 / Claude / GPT-4o with env auto-config; offline rules engine as fallback.
- **🖥️ Web Workbench**: `htmlninefox workbench` launches local Web UI with live preview, agent logs, and template selection.
- **🐳 Docker Image**: `docker run htmlninefox` for cross-platform deployment; multi-stage build with env injection.
- **Real HTML template library**: 6 complete templates with 34 individually previewable pages — no more wireframe guessing.
- **Unified input**: Text, TXT, Markdown, JSON, CSV, HTML, and common image formats.
- **Dual paths**: Accept recommendations directly, or compose layouts/pages/styles/files/skills on the canvas.
- **Infinite canvas workspaces**: Global coordinates, renaming, per-workspace colors, navigation, snapping, and port connections.
- **User-controlled AI**: OpenAI-compatible, Ollama, or custom endpoints; API keys stay local.
- **Offline capable**: Deterministic rules engine works without API keys.
- **Feedback iteration**: Natural language feedback → design token changes → re-render with `rev1 / rev2 / ...` history.
- **Cross-platform**: Windows installer/portable, Linux `.run/.tar.gz`, Python CLI, Web/PWA, Docker.

> The first [Export Center](docs/EXPORT-CENTER.md) milestone now ships PDF and PNG. High-fidelity PPTX comes next, followed by constrained editable PPTX/DOCX.
- 🎨 **Multiple PPT styles via Skill Alliance** (v0.3): baoyu-slide-deck (image) · frontend-slides (HTML, no AI gradient) · beautiful-html-templates (28 stable presets)

## See it in action

<table>
<tr>
<td width="50%"><img src="assets/screenshots/v0.4.0/pixel-garden-unified.png" alt="Pixel Garden unified design"><br><b>Pixel Garden Unified Design</b><br>5 visual artifacts unified with cobalt + mint + warm paper.</td>
<td width="50%"><img src="assets/screenshots/v0.4.0/web-workbench.png" alt="Web workbench"><br><b>Web Workbench</b><br>htmlninefox workbench: live preview, agent logs, template selection.</td>
</tr>
<tr>
<td width="50%"><img src="assets/screenshots/v0.4.0/llm-integration.png" alt="Real LLM integration"><br><b>Real LLM Integration</b><br>MiniMax-M3 / Claude / GPT-4o with env auto-config; offline fallback preserved.</td>
<td width="50%"><img src="assets/screenshots/v0.4.0/docker-deploy.png" alt="Docker deployment"><br><b>Docker One-Click Deploy</b><br>docker run htmlninefox with multi-stage build and env injection.</td>
</tr>
</table>

### Export Center

![v0.4.2 Export Center](assets/screenshots/v0.4.2/export-center.png)

Output nodes can export PDF, paginated PNG, or a full-page image. Preflight shows pagination, compatibility, dynamic-content, and remote-resource risks; delivery includes the files and `export-report.json`.

### Six real output types

| Landing | Dashboard | Deck |
|---|---|---|
| ![Landing](assets/screenshots/v0.3.0b2/output-landing.png) | ![Dashboard](assets/screenshots/v0.3.0b2/output-dashboard.png) | ![Deck](assets/screenshots/v0.3.0b2/output-deck.png) |

| Poster | Architecture document |
|---|---|
| ![Poster](assets/screenshots/v0.3.0b2/output-poster.png) | ![Architecture document](assets/screenshots/v0.3.0b2/output-archdoc.png) |

## Download & Install

Download application packages from the [v0.5.0rc3 Release](https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.5.0rc3). It is an application prerelease; [v0.4.2](https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.4.2) remains stable. The [DeepSeek Harness plugin preview](https://github.com/KratosLee-6/Html-ninefox/releases/tag/dsh-htmlninefox-v0.1.0-preview.1) is versioned separately.

| Platform | Recommended file | Usage |
|---|---|---|
| Windows 10/11 | `HtmlNineFox-Setup-0.5.0rc3.exe` | Per-user installer with a Start menu entry |
| Windows 10/11 | `HtmlNineFox-Windows-x64-0.5.0rc3.zip` | Extract and run `HtmlNineFox.exe` |
| Linux | `HtmlNineFox-Linux-0.5.0rc3.run` | `chmod +x` and run; installs to user directory |
| Linux / audit | `HtmlNineFox-Linux-0.5.0rc3.tar.gz` | Inspectable full installation contents |
| Python 3.10+ | `htmlninefox-0.5.0rc3-py3-none-any.whl` | `python -m pip install ./htmlninefox-0.5.0rc3-py3-none-any.whl` |
| Docker | Build from source | `docker compose up --build`; tag CI verifies but does not publish the image |

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
htmlninefox workbench
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

## Testing & Trust Evidence

The `v0.5.0rc3` release candidate was verified locally on **September 24, 2026**; `v0.4.2` remains the stable release.

| Check | Result | Evidence |
|---|---:|---|
| Full Python / API / storage / security / browser suite | **234 passed, 1 skipped** | [RC3-D record](docs/ITERATION-RC3-D-20260925.md) |
| Generation, Feedback, Restore, and Export application seams | **20 passed** | [RC3-C record](docs/ITERATION-RC3-C-20260924.md) |
| Focused command, memory, error, recovery, motion, interaction, revision, and export suite | **20 passed** | [reproducible Playwright gate](tests/test_rc3_visual_evidence_states.py) |
| Inline and standalone JavaScript syntax | **Passed** | [RC3 visual record](docs/ITERATION-RC3-VISUAL-CONVERGENCE-20260924.md) |
| Chromium generation and workbench acceptance | **22 / 22 passed** | [main Actions](https://github.com/KratosLee-6/Html-ninefox/actions?query=branch%3Amain) |
| DSH registry and final tarball integration | **2 / 2 passed** | [integration record](docs/DEEPSEEK-HARNESS-INTEGRATION.md) |
| RC3 package validation | Isolated wheel, packaged CSS/JS assets, CLI/workbench startup, tagged Windows/Linux assets, SHA-256 files, and Docker verification | [test report](docs/TEST-REPORT-v0.5.0rc3.md) |

The remaining product-engineering gaps are durable multi-file Project commits, cross-process coordination, crash recovery, browser lifecycle Modules, and Safari/WebView2 device validation.

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
- [v0.5.0 stable delivery plan](docs/PLAN-v0.5.0-STABLE-20260924.md)
- [Examples](docs/EXAMPLES.md)
- [Roadmap](docs/ROADMAP.md)
- [Private template import](docs/PRIVATE-TEMPLATE-IMPORT.md)

## Contributing

Issues and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT License · See [LICENSE](LICENSE)

---

<div align="center">
  <p><strong>让灵感在 HTML 里生长。</strong></p>
  <p>Html九尾狐 · Pixel Garden · 个人开源项目</p>
</div>
