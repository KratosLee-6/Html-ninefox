<div align="center">
  <img src="htmlninefox/server/static/logo-horizontal.svg" width="430" alt="HtmlNineFox Pixel Garden Logo">
  <h1>HtmlNineFox · Visual HTML Creation Workbench</h1>
  <p><strong>Bring text, files, images, reusable HTML templates, and skills onto one infinite canvas. Analyze, recommend, compose, generate, and revise real single-file HTML deliverables.</strong></p>
  <p>A personal open-source project by <a href="https://github.com/KratosLee-6">KratosLee</a> · Offline rules included · AI is optional</p>
  <p><a href="README.md">简体中文</a> · <strong>English</strong></p>
</div>

<div align="center">

[![Release](https://img.shields.io/github/v/release/KratosLee-6/Html-ninefox?include_prereleases&label=release)](https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.4.1)
[![Build Packages](https://github.com/KratosLee-6/Html-ninefox/actions/workflows/build-release-packages.yml/badge.svg)](https://github.com/KratosLee-6/Html-ninefox/actions/workflows/build-release-packages.yml)
[![Test CI](https://github.com/KratosLee-6/Html-ninefox/actions/workflows/test.yml/badge.svg)](https://github.com/KratosLee-6/Html-ninefox/actions/workflows/test.yml)
[![Tests](https://img.shields.io/badge/pytest-153%20passed-1F8A70)](docs/test-evidence/v0.4.1-pytest.txt)
[![Chromium E2E](https://img.shields.io/badge/Chromium%20E2E-20%2F20-173C8F)](docs/test-evidence/v0.4.1-chromium-e2e.txt)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB)](pyproject.toml)
[![License](https://img.shields.io/badge/License-MIT-D9A441)](LICENSE)

</div>

![HtmlNineFox v0.4.1 workbench](assets/screenshots/v0.4.1/workbench-overview.png)

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

## v0.4.1 Core Features

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

> The next delivery milestone is the [Export Center](docs/EXPORT-CENTER.md): PDF and images first, followed by high-fidelity PPTX and constrained editable PPTX/DOCX.
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

### Six real output types

| Landing | Dashboard | Deck |
|---|---|---|
| ![Landing](assets/screenshots/v0.3.0b2/output-landing.png) | ![Dashboard](assets/screenshots/v0.3.0b2/output-dashboard.png) | ![Deck](assets/screenshots/v0.3.0b2/output-deck.png) |

| Poster | Architecture document |
|---|---|
| ![Poster](assets/screenshots/v0.3.0b2/output-poster.png) | ![Architecture document](assets/screenshots/v0.3.0b2/output-archdoc.png) |

## Download & Install

Go to [v0.4.1 Release](https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.4.1) to download the latest version. See [RELEASE-NOTES-v0.4.1.md](docs/RELEASE-NOTES-v0.4.1.md).

| Platform | Recommended file | Usage |
|---|---|---|
| Windows 10/11 | `HtmlNineFox-Setup-0.4.1.exe` | Installer for regular users |
| Windows 10/11 | `HtmlNineFox-Windows-x64-0.4.1.zip` | Extract and run `HtmlNineFox.exe` |
| Linux | `HtmlNineFox-Linux-0.4.1.run` | `chmod +x` and run; installs to user directory |
| Linux / audit | `HtmlNineFox-Linux-0.4.1.tar.gz` | Inspectable full installation contents |
| Python 3.10+ | `htmlninefox-0.4.1-py3-none-any.whl` | Install with `pip install` |
| Docker | `htmlninefox:v0.4.1` | `docker run -p 8620:8620 -e MINIMAX_API_KEY=xxx htmlninefox` |

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

# 4. Or CLI direct generation
htmlninefox brief "Build a SaaS landing page"
```

### 从源码运行

```bash
git clone https://github.com/KratosLee-6/Html-ninefox.git
cd Html-ninefox
pip install -e .
htmlninefox --help
```

## 文档

- [架构设计](docs/ARCHITECTURE.md)
- [设计手册](docs/DESIGN.md)
- [使用示例](docs/EXAMPLES.md)
- [路线图](docs/ROADMAP.md)
- [私有模板导入](docs/PRIVATE-TEMPLATE-IMPORT.md)

## 贡献

欢迎提交 Issue 和 PR！详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可证

MIT License · 详见 [LICENSE](LICENSE)

---

<div align="center">
  <p><strong>让灵感在 HTML 里生长。</strong></p>
  <p>Html九尾狐 · Pixel Garden · 个人开源项目</p>
</div>
