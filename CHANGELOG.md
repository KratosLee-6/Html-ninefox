# Changelog

> 🦊 Personal project by [@KratosLee-6](https://github.com/KratosLee-6) · Not affiliated with any company · MIT licensed.

All notable changes to **Html九尾狐 / Fox-of-Nine-Tails HTML Studio** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

## [0.6.0] — 2026-11-08（目标） · 设计吸收流水线 + 可编辑 PPTX

> 目标发布窗口 2026-11-08（11-01 ～ 11-14）。版本号已切换，附件与 SHA-256 随 S21 发布回读。
> 门禁（2026-09-29，`e5f3664`）：303 passed / 1 skipped；JS 语法 13/13；DSH 插件 2/2；Chromium 22/22；WebKit 22/22。
> 证据：[S17 门禁报告](docs/test-evidence/v0.6.0-s17-20260929/README.md)、[双审计](docs/AUDIT-v0.6.0-20260928.md)。

**设计吸收（三条通道 → 素材审核台 → 六资产层）**
- 安全抓取框架：仅 http/https、解析校验拒私网/环回/重绑定、重定向逐跳过门、事后 rebinding 比对、体积上限、每源限速（`5de8d42`）。
- 源清单：内置 12 个设计源（四类 kind × 三档许可），支持用户目录同 id 覆盖（`d65b42c`）。
- 候选提取与审核台：骨架/令牌/意图猜测 → pending 审核；CSP 沙箱预览、批量采纳/拒绝、来源筛选、许可徽章、色板与大纲（`b5a722e`/`59a0cd3`/`8d3f34a`）。
- 手动导入增强：多 URL 批量（≤10 条逐条容错）+ ZIP 导入（24 文件/24MB 防穿越）（`4e6cdb3`）。
- 六资产层贯通：组件库（素材面板拖入生成）+ 渐变装饰（`97c88b7`）、动效原创样式（预算钳制 + reduced-motion 守卫 → motion-lab，`488f2e6`）、风格预设（→ 工作台风格面板，`82268ff`）、AI 分析通道（结构化 design brief + 标签，`9264a5c`）、吸收指标面板（`5f82bcf`）。
- 许可三档强制：inspiration-only 采纳跳过代码导入（`066905f`）。

**可编辑 PPTX（双层架构：工作台内编辑 + 服务端文件桥）**
- PPTX 文件桥：deck 产物 → python-pptx 受控映射 → 标准 .pptx（每页标题/要点文本框、对比度背景、页码脚注；扁平化如实上报）；往返验证文本可编辑（`3a3a384`）。
- 导出中心接入 pptx 格式 + 报告含可编辑元素数与降级清单（`e0d8f6d`）。
- 工作台内编辑闭环：幻灯片文本编辑 API（`PUT /slides` 带 `expected_revision` 并发保护，`4e893ea`）+ 结构化幻灯片编辑对话框（产物检查器「编辑幻灯片」入口，按页列出可编辑文本节点，保存后刷新 revision 徽章 / 检查器 / 实时预览，`a5d7a93`）。这是 v0.6 内可编辑 PPTX 的交付形态。
- Univer 可视化画布编辑器**降级为 S13U-b2 单独跟踪**：调研确认开源包只覆盖 slides 模型与 UI，PPTX 导入导出位于 Pro 档（`@univerjs-pro/slides*`）且 slides 无 UMD preset，集成需自建 vendor 构建管线。原 §七-B 的「Univer 作为工作台内可视化编辑层」决策据此修订，文件交付路径不受影响。

**质量与审计**
- 门禁：吸收压测 100 候选（创建 0.28s / 列表 40ms）+ 路径穿越全拒（`8d920be`）；WebKit 通道（Safari 引擎 22/22）+ Chromium 双通道 22/22；topbar 定位器歧义修复（同提交）。
- 双审计：mattpocock 四维（7 P1 中 5 修、2 记录）+ Mimosa deep（SSRF 设计性缓解 + 残余披露，见 [AUDIT-v0.6.0](docs/AUDIT-v0.6.0-20260928.md)）。

### Added

- The v0.6 design-intake foundation: a source registry (`data/sources/*.yaml` with user overrides), a safe reference fetcher (http/https only, resolved-host validation rejecting loopback/private/reserved addresses, hop-by-hop redirect validation, post-fetch DNS-rebinding check, size caps, per-source rate limiting), an evidence store under `.library/intake/`, and three built-in gallery/motion sources with license classes.
- The PPTX file bridge (V0.6-S13): deck artifacts export to editable PowerPoint files via python-pptx — per-slide title/body text frames, solid backgrounds with contrast-aware text colors, page footers, and a report of flattened visuals; `pptx` optional extra added.
- Kind-specific intake extractors: motion sources capture transitions, animation shorthands and keyframe names; component sources capture section-level candidates with bounded snippets; typography sources capture size and line-height scales — each candidate records its source kind.
- Intake candidate extraction and a review store: fetched pages become pending candidates with title, intent guess, color/font tokens, and a section-level skeleton; `CandidateStore` persists them under `.library/intake/candidates/` with pending/approved/rejected status.
- A macOS (Apple Silicon) portable package: PyInstaller `.app` bundle with an icns icon, `ditto` zip, SHA-256, and a dedicated `macos` job in the release workflow; the desktop channel reports `macos-portable` and capabilities advertise macOS as `beta`.
- v0.6 new-feature visual evidence (V0.6-S20): `assets/screenshots/v0.6.0/` ships 7 real captures — the review workbench (pending list with all three license tiers, CSP sandbox preview, approved state with style-preset/component/motion actions), the motion lab intake card, the in-workbench slide editor, the export center PPTX run, and the `export-report.json` body. Regenerate with `HTMLNINEFOX_V060_EVIDENCE_DIR=assets/screenshots/v0.6.0 pytest tests/test_v060_visual_evidence_states.py`; without that variable the file runs as a pure assertion gate and writes nothing.
- A measured design health gate (`tests/test_design_health_gates.py`, 6 checks) that locks the interface defects found by the 2026-09-29 design review: the batch-fetch wiring, node-head badge layout, narrow-viewport step labels, WCAG AA contrast in both themes, and theme-aware foreground on accent surfaces.
- A layout and information-hierarchy gate (`tests/test_layout_hierarchy_gates.py`, 8 checks) covering the canvas fit model, first-load zoom, canvas width usage, template-card height/line clamps, the intake metric strip, filter selected state, the batch-import reachability path, and modal backdrop blur.

### Fixed

- **首屏画布把内容缩到 0.33 倍，右侧空出 666px**：`canvasFitInsets()` 把左上角那块浮层「工作区导航卡」当成一条**通高左栏**来避让（`left: 导航卡右缘` = 290px），于是 916px 宽的画布只剩 446px 可用，缩放被压到 0.33，内容缩成一小团、右侧大片空置——用户第一眼看到的是「这软件怎么这么小」。现在按各浮层的真实几何分别计入上 / 下 / 右三边（导航卡计入 top、HUD 计入 right、小地图计入 bottom），不再预留通高左带；fit 留白由 90px 收到 36px，小地图由 196×130 收到 150×100。首屏缩放 **0.33 → 0.80**，画布内容利用率 39% → 42% 且居中。
- **侧栏模板卡因英文描述与标题并排 flex 而高度跳到 179px、标题断词换行**：`.pal-name` 是 flex 容器，模板名与英文描述是兄弟节点，描述一换行就把标题挤成断词换行并把卡片撑高。两者改为上下堆叠、各自夹 2 行，卡片高度稳定（实测 3 行 → 2 行），缩略图 104px → 86px，`REAL HTML` 徽标从缩略图左上（压住内容）移到左下。
- **审核台的吸收指标是一行调试字符串、四个筛选项无选中态**：指标改为指标条（数字为主、标签为辅，待审 / 已采纳 / 已拒绝带状态色条），并补回区块标题「吸收指标」；筛选按钮按当前状态切换主/次样式并带 `aria-pressed`。同时把弹窗背景模糊由 12px 降到 6px——此前工作台被糊成一片，失去「我在哪个界面」的上下文。
- **界面动作名没有编译期约束，漏一个就成死按钮（C6）**：`index.html` 此前用 44 个手写的 `function foo(){ return window.FoxBar.foo(); }` 转发函数，把 HTML 与模板字符串里的 `onclick="foo(...)"` 接到 lifecycle 模块，两侧没有任何约束——引用一个漏登记的名字只会在用户点击时抛 `ReferenceError`，而服务端、单元测试与 CI 全绿。S20 期间的 `intakeFetchBatch` 死按钮（「多 URL 批量」整条能力在界面上不可达）就是这个形状。转发函数收成唯一派发表 `window.FoxActions`，并新增门禁 `tests/test_action_registry.py`：任何被 HTML/JS 引用却没登记的动作名都会让 CI 失败。顺带把动作属性里的内联 `document.querySelector(...).click()` 换成具名的 `openZipPicker()`，并补上 `esc()` 漏转义的单引号——它会进入 `onclick="...('${esc(id)}')"` 这类 JS 字符串，当前 id 被服务端正则限死故不可利用，但会误导后来者。**有意未做**：把 112 处 `onclick` 整体迁到 `data-action` + 事件委托，因为 `data-*` 取值一律是字符串而节点 id 是数字，132 处迁移的回归风险高于其收益；派发表 + 静态门禁已堵死该缺陷类。
- **Artifact 前进到新 Revision 的写回协议复制 3 份、其中 2 份漏持久化，刷新后 revision 回退**：这条协议此前被复制在 `sendFeedback` / `slides.save` / `generation.rerun` 三处且互不一致。前两处改了内存里的 `node.data.revision`，却既没写 localStorage 也没提交服务端快照——而页面刷新时画布优先从 localStorage 的 `fox-canvas-v3` 恢复，于是**用户刷新后看到旧 rev 号，服务端 Artifact 却已是新 rev**。「编辑幻灯片」正是 v0.6.0 对外宣称的核心能力（成果 G4），这条路径会直接让承诺失真。协议现收进唯一拥有者 `window.FoxRevisions.advanceNodeRevision(nodeId, revision, options)`，由它决定是否破缓存预览、是否重绘检查器、是否持久化、是否刷新项目列表；三个调用点只留各自业务语义。门禁 `tests/test_artifact_revision_writeback.py` 锁住两件事：协议不得再出现第二份拼装，以及「改幻灯片 → 刷新 → revision 不得回退」。修的过程中确认两点并已记入审计文档：只调 `persistWorkspaceNow()` 不够（它只 PUT 服务端、不写 localStorage）；初版回归测试用 `add_init_script` 清 localStorage，会在 reload 时把被测对象擦掉导致恒过。
- **「批量抓取」按钮是死按钮，多 URL 批量能力在界面上不可达**：`index.html` 的批量导入区用 `onclick="intakeFetchBatch()"` 调用了一个**从未定义**的全局函数——`FoxIntake.fetchBatch` 明明存在于 `lifecycle-intake.js`，只是没接到全局名上。点击必然 `ReferenceError`，于是 S04「多 URL 批量（≤10 条逐条容错）」这条 v0.6.0 主线能力没有任何用户可达路径，而服务端与其测试全绿。已补转发函数。
- **`test_rapid_double_advance` 在 CI 上反复超时（长期唯一的主导抖动源）**：该用例原本用两次 `page.evaluate` 往返来模拟「快速二次推进」，再等待 `#tl-status` 出现守卫提示。问题在于 `#tl-status` 有两个写入者——`flash()` 与任务轮询器（`lifecycle-generation.js` 每次轮询都覆盖它），两次往返之间隔着一次网络往返，轮询完全可能先把提示盖掉，断言就永远等不到；本地因为机器快、窗口小而复现不出来（本地约 1/8 概率，CI 上 5 次失败里 3 次命中）。现在两次推进在**同一个 `page.evaluate` 里同步发出**：`advance()` 在第一个 `await` 之前就同步写入 `activeJobs`，所以第二次必然命中守卫，且此刻首次轮询尚未开始、提示不会被覆盖。断言同时从「等一条瞬态文本」升级为核对**真正的不变量**——被拒绝的那次不提交第二个 `POST /api/jobs`。本地压力 15/15 稳定通过。
- **夜蓝主题的主按钮对比度仅 2.44:1**：`.btn-primary` 等五处把 `color:#fff` 写死，而夜蓝主题的 `--accent` 是亮蓝 `#76A5FF`，白字压在上面几乎读不出来——受影响的是「推进当前工作区」这个全站最重的 CTA。新增 `--on-accent` 语义令牌（纸白 `#FFFFFF` / 夜蓝 `#0C1B2E`），五处统一改用它，保留品牌配色不变。
- **弱化文字对比度不达 WCAG AA**：版本号、栏目标题、模板英文描述、数量角标、状态字形共用一个 `--text-tertiary`，纸白主题下只有 3.17–3.51:1，而它们又只有 9–11px（小字本就要求 4.5:1）。夜蓝主题另有 9.5px 描述文字停在 3.98:1。两套主题的该值分别调整为 `#59676D` 与 `#A0B6BE`，在各自全部底色上均达 AA。
- **画布节点头部把类型徽标压成竖排单字**：`.node-head` 是 `flex-wrap:nowrap` 且标题没有收缩下限，中文模板名几乎必然触发——徽标被压到 12×21，两个汉字上下堆叠。现在标题先 `text-overflow:ellipsis` 截断，徽标 `flex:0 0 auto` 保持完整。
- **窄屏进度条只剩无含义的圆点**：`@media (max-width:760px)` 把五个步骤名全部 `display:none`，390px 下整条进度只剩三个 √ 和连接线，占着约 50px 却传达不了任何信息。改为只隐藏已完成/未开始的步骤名，**当前**与**失败**步骤的文字始终可见。
- **工作区与通知的关闭控件过小**：`.ws-head button` 固定 `height:22px`、`.fox-toast-close` 22×22，均低于项目自己声明的 `--control-touch:44px`。工作区按钮提到 28px，通知关闭提到 28px，并在 `pointer:coarse`（触屏）下分别提升到 44px / 36px。
- **导出中心没有 PPTX 选项，可编辑 PPTX 链路用户不可达（V0.6-S20 门禁发现）**：服务端 `SUPPORTED_FORMATS` 与 `lifecycle-exports.js` 的 pptx 分支（`syncOptions` 收起纸张/倍率字段）早已就绪，但 `static/index.html` 的 `#export-format` 只登记了 `pdf` / `png`。也就是说 S14 的验收条件「UI 选择 pptx → 任务完成 → 报告列出可编辑元素数与降级数」从未真正成立——成果 G4 在界面上无法触达，缺陷却完全不可见，因为没有任何测试点击过那个下拉框。`#export-format` 现登记 `PPTX 演示（可编辑 · deck 产物）`，`renderAnalysis` 依据 manifest 的 `intent` 只对 deck 产物放开（服务端对非 deck 本就返回 `export_format_unsupported`，不制造必然失败的选项）。门禁断言该选项真实存在且可选中，采集脚本不再注入临时 option。
- **所有 typography 候选在抽取阶段抛 `TypeError`，许可第三档「开放许可」整体不可达（V0.6-S20 门禁发现）**：`extract_candidate` 通过 `KIND_EXTRACTORS` 统一以 `(evidence, html_text, style_blob)` 三参派发，而 `extract_typography` 只声明了两个形参，签名与派发契约不一致。typography 是 `data/sources` 中**唯一**的 `open` 许可来源（fontshare / google-fonts），意味着审核台的许可三档治理里「开放许可」这一档在真实使用中永远无法产生候选，成果 G1/G2 的档位覆盖名存实亡。已把签名对齐到统一契约（附带说明该形参不参与计算），门禁改为无条件断言三档齐全。
- **PPTX 导出结果区渲染出一行 href=undefined 的失效下载按钮**：`lifecycle-exports.js` 无条件把 `result.report` 追加到 `result.files` 之后，但 pptx 路径的 `files` 里已经包含了 `export-report.json`，其顶层 `report` 只有 `name`/`bytes` 没有 `download_url`，于是同一份报告被渲染两次、其中一次链接失效。现在只在 `report.download_url` 存在时追加，PDF/PNG 路径行为不变。
- **Deck 生成在装有 jinja2 的环境下退化为落地页，导致整条可编辑 PPTX 链路失效（V0.6-S17 门禁发现）**：`generate_expert` 把 `deck` 别名到 `templates/landing.html`，因此凡安装了可选 `templates` extra 的环境，deck 请求都会渲染成 hero/features/pricing 落地页，产物里没有 `<section class="slide">`。结果是 PPTX 文件桥（`export_deck_pptx`）、幻灯片编辑 API（`PUT /slides`）与导出中心 pptx 全部失去输入——即 v0.6 成果 G4「可编辑 PPTX」在该环境下必然失败，且失败点在生成端、报错点在导出端，极难定位。deck 现在保持 intent 忠实：落到原生 `generators/deck.py`，产出真正的分页结构（实测 7 页 / 24 个可编辑元素），与联盟 manifest 声明的 `fallback: local:deck` 语义一致。已补回归测试锁定该不变量。

## [0.5.0] — 2026-09-25 · 🎉 First Stable Release of the 0.5 Line

> Stable release consolidating RC3-B2/C/D/E: shared application use cases,
> crash-recoverable Project commits with cross-process locking, and isolated
> browser lifecycle modules. Verified with 238 Python tests, 22/22 Chromium
> acceptance on both bundled Chromium and the real system Edge engine, and a
> real generation + PNG export smoke on the packaged Windows executable.

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

- Full local suite: `238 passed, 1 skipped` (12 durability + 4 lifecycle tests); Chromium e2e `22/22`; DeepSeek Harness: `2/2`.

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

[0.5.0]: https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.5.0
[0.2.0]: https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.2.0
[0.1.0]: https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.1.0
[0.0.1]: https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.0.1
