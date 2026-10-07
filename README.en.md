<div align="center">
  <img src="htmlninefox/server/static/logo-horizontal.svg" width="430" alt="HtmlNineFox Pixel Garden Logo">
  <h1>HtmlNineFox · HTML Creation Workbench</h1>
  <p><strong>Put text, files, images and scattered HTML templates on one infinite canvas — analyse, recommend, compose freely, iterate with feedback, and ship a truly deliverable single-file HTML.</strong></p>
  <p>Personal open-source project by <a href="https://github.com/KratosLee-6">KratosLee</a> · Offline rules engine included · AI optional</p>
  <p><a href="README.md">简体中文</a> · <strong>English</strong></p>
</div>

<div align="center">

[![App Release](https://img.shields.io/badge/app-v0.7.0-173C8F)](https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.7.0)
[![Tests](https://img.shields.io/badge/pytest-596%20passed%20%7C%202%20skipped-1F8A70)](docs/RELEASE-NOTES-v0.7.0.md)
[![Chromium E2E](https://img.shields.io/badge/Chromium%20E2E-22%2F22-173C8F)](docs/RELEASE-NOTES-v0.7.0.md)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB)](pyproject.toml)
[![License](https://img.shields.io/badge/License-MIT-D9A441)](LICENSE)

</div>


> 当前应用包版本为 `0.7.0`（2026-10-07 发布）· 完整功能与架构见下。

---

## Video

GitHub does not inline-play repository mp4 files: the narrated cut plays on the **release page**, the screen-recording cut is a direct file link.

- **[Narrated cut · 75s (v0.7.0 release page)](https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.7.0)** — voice-over + keynote-style motion graphics + a real operating recording: paste example.com → review → adopt → decompose and generate → the page's own prose shows up in the output. Driven by the t2 keynote grammar of [huashu-art-motion](https://github.com/alchaincyf/huashu-art-motion).
- [Screen-recording cut · 73s (raw file)](https://raw.githubusercontent.com/KratosLee-6/Html-ninefox/main/assets/promo/htmlninefox-demo-v070-16x9.mp4)

![v0.7.0 explainer poster](assets/promo/poster-demo-v070.png)

## v0.7.0 · Page decomposition (latest)

**Turn a real web page's sections into an editable project.**

<table>
<tr>
<td width="50%"><img src="assets/screenshots/v0.7.0/intake-page-blocks-pending.png" alt="Review workbench"><br><b>Paste a URL → review workbench</b><br>Candidates carry licence tags; open licences carry prose, reference-only carries structure.</td>
<td width="50%"><img src="assets/screenshots/v0.7.0/output-landing-with-page-sections.png" alt="Output"><br><b>The sections you took → in the output</b><br>All six content types consume the block channel.</td>
</tr>
</table>

- `POST /api/intake/page-blocks` re-cuts an approved candidate into generation-ready blocks (nested sections included) — read-only, never written back.
- Copyright per field: only `open` carries prose; others contribute structure and the output falls back to its own copy.
- Gates: `596 passed / 2 skipped` on Windows (CI `597/1`), 16 mutation scripts all caught, browser 22/22, real-chain 15/15. See the [release notes](docs/RELEASE-NOTES-v0.7.0.md).

## Architecture

```text
Design intake (12 sources / URL / ZIP)     Page decomposition (new in v0.7)
        ↓ review · three licence tiers              ↓ cut into blocks
        └────────────┬──────────────────────────────┘
                     ↓
  text / files / images / HTML → AI or offline rules → content type + template + sections
                     ↓
     infinite-canvas workspaces (compose / feedback / revisions)
                     ↓
              single-file HTML (six content types)
                     ↓
    export PDF / paginated PNG / long image / editable PPTX + report
```

| Module | Role |
|---|---|
| `intake.py` | Design intake: SSRF-guarded fetching (connection-level IP pinning), sources, review, page blocks |
| `pipeline.py` | Generation pipeline: brief → route → style → assets → compose → generate → verify, `.foxstate.json` state |
| `rules.py` + `generators/` | Offline rules engine and six renderers; all six consume the block channel |
| `server/app.py` | Zero-dependency local service: workbench API (intake / generate / feedback / revisions / export / slides) |
| `exporting.py` + `pptx_export.py` | PDF / PNG / long image + report; python-pptx mapped editable PPTX |
| `revisions.py` + `project_memory.py` | Revision snapshots and restore; learn-only-on-adoption local memory |

Full architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Modules

| Module | In one line | Details |
|---|---|---|
| 🖼 Infinite-canvas workbench | Text, files, images, HTML templates on one canvas | [UI guide](docs/UI-GUIDE.md) |
| 🕸 Design intake | 12 built-in sources + URL/ZIP, human review, three-tier licence enforced in code | [v0.6.0 notes](docs/RELEASE-NOTES-v0.6.0.md) |
| 🔎 Page decomposition (new) | Adopted candidates decompose straight into generation | [v0.7.0 notes](docs/RELEASE-NOTES-v0.7.0.md) |
| 📊 Editable PPTX | Standard .pptx with real text frames; in-workbench slide editing | [Export centre](docs/EXPORT-CENTER.md) |
| 📤 Export centre | PDF / paginated PNG / long image + compatibility report | [Export centre](docs/EXPORT-CENTER.md) |
| 🧠 Memory + revisions | Learn only on adoption; everything snapshots | [full archive](docs/HOMEPAGE-ARCHIVE.en.md) |

## Quick start

```bash
pip install htmlninefox
htmlninefox app                   # http://127.0.0.1:8620
htmlninefox expert "Build a SaaS landing page"
```

Windows / Linux / macOS packages and the wheel: [**v0.7.0 Release**](https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.7.0) (SHA-256 included).

## Version history

| Version | Date | In one line |
|---|---|---|
| **v0.7.0** | 2026-10-07 | **Page decomposition**; three green-but-broken defects found by real-chain verification and fixed |
| v0.6.4 | 2026-10-06 | Gate hardening; artefacts re-hashed byte-for-byte before publishing |
| v0.6.0 | 2026-10-01 | Design intake pipeline + editable PPTX |
| v0.5.0 | 2026-09-25 | RC3 wrap-up, all-platform packages |

Full log: [CHANGELOG](CHANGELOG.md).

---

📖 **More**: this homepage is a digest. The full feature-to-screenshot map, intake and PPTX deep dives, the complete trust-evidence table and acknowledgements live in [docs/HOMEPAGE-ARCHIVE.en.md](docs/HOMEPAGE-ARCHIVE.en.md) (Chinese [archive](docs/HOMEPAGE-ARCHIVE.md)).

Design methods inspired by GuiCang, Huashu Design (this explainer film uses the [huashu-art-motion](https://github.com/alchaincyf/huashu-art-motion) engine) and Archify — see [DESIGN-SOURCES](docs/DESIGN-SOURCES.md).

[MIT License](LICENSE) © 2026 **KratosLee · Html九尾狐项目组**
