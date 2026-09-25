# Html九尾狐 · HTML 创作工作流

Help the user create a local HTML deliverable, revise it from feedback, and export
PDF or PNG when requested. Respond in the user's language. This skill uses the
host's existing shell tools and the separately installed Html九尾狐 Python CLI.
It does not add its own shell executor, bypass host approvals, or collect telemetry.

## Check the environment

Run `htmlninefox version`, `htmlninefox expert --help`,
`htmlninefox feedback --help`, `htmlninefox restore --help`, and
`htmlninefox export --help` first. If unavailable or missing the export command,
explain that this plugin does not include the Python application. The maintained
source install is:

```sh
python -m pip install "git+https://github.com/KratosLee-6/Html-ninefox.git@v0.5.0"
```

Use an existing suitable environment, or a project virtual environment. Respect
the host's installation and command approval policy. Python 3.10+ and Git are
required for this source install. Never claim that installing the npm plugin also
installs Python, Chromium or an API key. On a remote Harness host, files and the
CLI live on that host, not automatically on the user's laptop.
If multiple Python installations exist, use the selected environment's executable
consistently; a source checkout can mask an older global installation.

## Create a deliverable

Infer content type and style from the user's request. Ask only for missing facts
that materially affect the output. Use `htmlninefox template` to discover real
template IDs. Supported types: `landing`, `dashboard`, `deck`, `poster`, `archdoc`,
`doc`. Example:

```sh
htmlninefox expert "为狐构制作中文 SaaS 落地页，暖纸底、钴蓝强调色" --type landing --quiet-llm --output ./fox-output
```

`--quiet-llm` skips optional LLM enhancement and uses offline rules; it does not
produce the same fidelity as an AI-assisted workflow. Omit it only when the user
wants the application's separately configured AI provider. Harness credentials
are not automatically shared with Html九尾狐. Do not read, print or copy keys.

Run commands in the user's chosen workspace. Quote paths and user text for the
actual shell; never interpolate untrusted text into executable shell syntax.
Use the actual output directory printed by the CLI; do not guess timestamp names.
Inspect `output.html`, report where it lives, and explain any verification limits.
Do not claim the result is deployed or that PPTX/Word was produced.

## GenerationRequest mapping

The Harness workflow maps user intent to the same application request used by the
CLI and HTTP adapters:

| GenerationRequest field | CLI mapping |
| --- | --- |
| `prompt` | positional prompt text |
| `intent` | `--type` |
| `skill` | `--skill` when the user explicitly selects an installed alliance skill |
| `template` | `--template` after verifying the ID with `htmlninefox template` |
| `quiet_llm` | `--quiet-llm` |
| generation workspace | `--output` |

Do not invent flags for attachments, private-gallery IDs, color tokens, or fonts.
Those fields currently require the HTTP workbench adapter. Report that limitation
instead of silently dropping an explicit requirement.

## Revise an existing project

Use the exact generated project directory, replacing the illustrative path below:

```sh
htmlninefox feedback --project "./fox-output/ACTUAL-PROJECT" --note "标题大一点" --dry-run
htmlninefox feedback --project "./fox-output/ACTUAL-PROJECT" --note "标题大一点"
```

Check whether the dry run understood the requested change, then apply an already
authorized revision. Explain unsupported feedback instead of promising a change.
Revisions retain history. Do not delete history or silently write Project Memory;
learning preferences requires explicit adoption in the workbench.

### FeedbackRequest mapping

| FeedbackRequest field | CLI mapping |
| --- | --- |
| `project` | `--project` with the exact Project directory |
| `note` | `--note` with the user's requested change |
| `dry_run` | `--dry-run` when the user wants interpretation without creating a Revision |

## Restore a historical Revision

Read the current Revision from the Project state before restoring and use it as
`--expected-revision`. Never guess the current Revision. Restore creates a new
current Revision and keeps all later history:

```sh
htmlninefox restore --project "./fox-output/ACTUAL-PROJECT" --revision 0 --expected-revision 2
```

### RestoreRequest mapping

| RestoreRequest field | CLI mapping |
| --- | --- |
| `project` | `--project` with the exact Project directory |
| `revision` | `--revision` for the historical Revision to restore |
| `expected_revision` | `--expected-revision` with the current Revision for conflict protection |

## Export / open the workbench

```sh
htmlninefox export "./fox-output/ACTUAL-PROJECT" --format pdf --paper A4
htmlninefox export "./fox-output/ACTUAL-PROJECT" --format png --scope long
htmlninefox app --host 127.0.0.1 --output ./fox-output
```

### ExportRequest mapping

| ExportRequest field | CLI mapping |
| --- | --- |
| `project_name` / workspace root | positional Project path, or name plus `--output-root` |
| `format` | `--format pdf|png` |
| `scope` | `--scope auto|pages|long` |
| `pages` | `--pages` with a verified page range |
| `width`, `height`, `scale` | matching viewport options |
| `paper`, `landscape` | `--paper` and `--landscape` for PDF |

PDF/PNG needs local Edge/Chrome or Playwright Chromium. If the CLI reports a
missing browser, explain the dependency; the supported installation command is
`python -m playwright install chromium`. Check the export report and actual files
before reporting success. Start the persistent workbench only when requested;
use the host's supported background process mechanism. Bind locally by default.

## Optional feedback

When the user wants to report a problem, prepare a concise report containing OS,
Harness version, plugin version, `htmlninefox version`, reproduction steps,
expected/actual behavior and redacted logs. The user can submit it at
https://github.com/KratosLee-6/Html-ninefox/issues . Do not automatically upload
their prompts, generated pages, credentials, files or a report.
