<div align="center">
  <img src="htmlninefox/server/static/logo-horizontal.svg" width="430" alt="HtmlNineFox Pixel Garden Logo">
  <h1>HtmlNineFox · Visual HTML Creation Workbench</h1>
  <p><strong>Bring text, files, images, reusable HTML templates, and skills onto one infinite canvas. Analyze, recommend, compose, generate, and revise real single-file HTML deliverables.</strong></p>
  <p>A personal open-source project by <a href="https://github.com/KratosLee-6">KratosLee</a> · Offline rules included · AI is optional</p>
  <p><a href="README.md">简体中文</a> · <strong>English</strong></p>
</div>

<div align="center">

[![App Release](https://img.shields.io/badge/app-v0.4.2-173C8F)](https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.4.2)
[![DSH Plugin](https://img.shields.io/badge/DSH_plugin-0.1.0--preview.1-49B894)](https://github.com/KratosLee-6/Html-ninefox/releases/tag/dsh-htmlninefox-v0.1.0-preview.1)
[![Build Packages](https://github.com/KratosLee-6/Html-ninefox/actions/workflows/build-release-packages.yml/badge.svg)](https://github.com/KratosLee-6/Html-ninefox/actions/workflows/build-release-packages.yml)
[![Test CI](https://github.com/KratosLee-6/Html-ninefox/actions/workflows/test.yml/badge.svg)](https://github.com/KratosLee-6/Html-ninefox/actions/workflows/test.yml)
[![Tests](https://img.shields.io/badge/pytest-199%20passed-1F8A70)](https://github.com/KratosLee-6/Html-ninefox/actions/runs/35353907293)
[![Chromium E2E](https://img.shields.io/badge/Chromium%20E2E-22%2F22-173C8F)](docs/test-evidence/v0.4.2-chromium-e2e.txt)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB)](pyproject.toml)
[![License](https://img.shields.io/badge/License-MIT-D9A441)](LICENSE)

</div>

![HtmlNineFox v0.4.2 workbench](assets/screenshots/v0.4.2/workbench-overview.png)

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

## Latest Development Snapshot (2026-09-18)

`main` still reports application version `0.5.0rc1`. RC2 revision history, native motion, and the DeepSeek Harness integration are complete development increments on that baseline, but there is no new RC2 application installer yet. The downloadable application release remains `v0.4.2`; the DSH plugin has its own `0.1.0-preview.1` release.

| Increment | Delivered behavior | Evidence |
|---|---|---|
| Revision history | HTML plus generation-state snapshots, labels, source diffs, lineage, conflict-aware restore-as-new-version, legacy history compatibility | [RC2 notes](docs/ITERATION-RC2-20260918.md) · [test report](docs/TEST-REPORT-RC2-20260918.md) |
| Accessibility and scale | Keyboard focus loop and restoration, 390px layout, 100 nodes / 99 edges render-select-move-save gate | [RC2 report](docs/TEST-REPORT-RC2-20260918.md) |
| Native motion | System/reduced/off preferences, cancellable animations, concurrency budget, retry cleanup, stage-based notifications, six `/motion-lab` samples | [motion delivery](docs/ITERATION-MOTION-20260918.md) |
| DeepSeek Harness | Native Cordis `dsh.bundle` skill workflow for generate → feedback → PDF / PNG, with tarball, SHA-256 and `dsh-plugin` topic | [plugin release](https://github.com/KratosLee-6/Html-ninefox/releases/tag/dsh-htmlninefox-v0.1.0-preview.1) · [guide](integrations/deepseek-harness/README.md) |

<table>
<tr>
<td width="50%"><img src="docs/test-evidence/harness-plugin-20260918/harness-plugin-enabled.png" alt="htmlninefox enabled in DeepSeek Harness"><br><b>Enabled in DSH</b><br>The final tarball is installed in a fresh Web profile and visible as an enabled global plugin.</td>
<td width="50%"><img src="docs/test-evidence/harness-plugin-20260918/generated-poster.png" alt="Chinese poster generated and exported through the tested workflow"><br><b>Generate, revise, export</b><br>Offline Chinese poster generation, dry-run and applied feedback, then PDF and full-page PNG export with a 100 compatibility score.</td>
</tr>
<tr>
<td width="50%"><img src="docs/test-evidence/motion-20260918/revision-history-desktop.png" alt="Revision history and restore UI"><br><b>Revision history</b><br>Labels, lineage, source diff and restore-as-new-version.</td>
<td width="50%"><img src="docs/test-evidence/motion-20260918/motion-lab-desktop.png" alt="Native motion lab"><br><b>Motion lab</b><br>Six interaction samples with user-controlled motion preferences.</td>
</tr>
</table>

Latest validation: **199 passed** on Linux CI, **22/22** Chromium acceptance checks, and **2/2** DSH registry and tarball integration tests. Remaining gaps include real-model DSH conversation selection, Safari / WebView2, cross-process writes, and crash-transaction recovery.

## v0.5.0 RC1 Preview

![Project Memory and adoption signals](assets/screenshots/v0.5.0rc1/project-memory-dialog.png)

- **🧠 Project Memory**: Brand, audience, tone, forbidden patterns, template, primary color, and font stay local and remain editable, disableable, and clearable.
- **♡ Learn only after adoption**: Long-term memory changes only when the user explicitly selects “Adopt this version and learn.”
- **🔎 Explainable reuse**: Analysis, Recipe Run, and the artifact inspector show what was reused and what the current explicit request overrode.
- **🔒 Privacy boundary**: API keys, attachment bodies, and full private feedback text are excluded from long-term memory.
- **✅ RC1 verification**: 179/179 Python, API, storage, security, and Chromium browser tests pass.

> RC1 completes the local project memory loop. The RC2 history, 100-node, and keyboard interaction work is described above.

## v0.4.2 Core Features

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

### v0.4.2 Export Center

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

Download application installers from the [v0.4.2 Release](https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.4.2). The `0.5.0rc1` / RC2 work on `main` does not have an application Release yet and must be run from source. The [DeepSeek Harness plugin preview](https://github.com/KratosLee-6/Html-ninefox/releases/tag/dsh-htmlninefox-v0.1.0-preview.1) is versioned separately.

| Platform | Recommended file | Usage |
|---|---|---|
| Windows 10/11 | `HtmlNineFox-Setup-0.4.2.exe` | Installer for regular users |
| Windows 10/11 | `HtmlNineFox-Windows-x64-0.4.2.zip` | Extract and run `HtmlNineFox.exe` |
| Linux | `HtmlNineFox-Linux-0.4.2.run` | `chmod +x` and run; installs to user directory |
| Linux / audit | `HtmlNineFox-Linux-0.4.2.tar.gz` | Inspectable full installation contents |
| Python 3.10+ | `htmlninefox-0.4.2-py3-none-any.whl` | Install with `pip install` |
| Docker | `htmlninefox:v0.4.2` | `docker run -p 8620:8620 -e MINIMAX_API_KEY=xxx htmlninefox` |

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

# 5. Export an existing workbench project
htmlninefox export PROJECT_NAME --format pdf
htmlninefox export PROJECT_NAME --format png --scope pages --pages 1-3
```

## Testing & Trust Evidence

Latest `main` validation completed on **September 18, 2026**. The `v0.4.2` package evidence remains available in its original report.

| Check | Result | Evidence |
|---|---:|---|
| Python / API / storage / security / browser tests | **199 passed** | [GitHub CI](https://github.com/KratosLee-6/Html-ninefox/actions/runs/35353907293) |
| Chromium generation and workbench acceptance | **22 / 22 passed** | [GitHub CI](https://github.com/KratosLee-6/Html-ninefox/actions/runs/35353907293) |
| Revision, motion and 100-node gates | **Passed** | [motion delivery](docs/ITERATION-MOTION-20260918.md) |
| DSH registry and final tarball integration | **2 / 2 passed** | [integration record](docs/DEEPSEEK-HARNESS-INTEGRATION.md) |
| Package smoke | Wheel and Windows portable export passed; Linux dual-architecture archive verified | [package smoke](docs/test-evidence/v0.4.2-package-smoke.txt) |
| Local release candidates | SHA256 recorded for wheel, Windows ZIP, Linux `.run`, and Linux `.tar.gz`; tag CI publishes official sidecars | [checksums](docs/test-evidence/v0.4.2-release-sha256.txt) |

See the full [v0.4.2 test report](docs/TEST-REPORT-v0.4.2.md) and [environment record](docs/test-evidence/v0.4.2-environment.txt).

### Run from source

```bash
git clone https://github.com/KratosLee-6/Html-ninefox.git
cd Html-ninefox
pip install -e .
htmlninefox --help
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Design guide](docs/DESIGN.md)
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
