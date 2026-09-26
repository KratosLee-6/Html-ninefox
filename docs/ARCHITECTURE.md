# Architecture · 当前架构

> 当前基线：`v0.5.0` 稳定版，更新于 2026-09-25。早期“5 agents · 3 sinks · 1 router”描述记录了项目起点，已经不足以说明当前 Project、Revision、Export、Memory、Job、Workspace 和插件能力。
>
> 工程审计：[mattpocock/skills 方法版审计](AUDIT-MATTPOCOCK-20260920.md) · 下一阶段：[RC3 架构加固计划](ITERATION-PLAN-POST-RC2-20260920.md)

## 系统边界

Html九尾狐是本地优先的 HTML 创作系统。Python Core 保存业务规则和文件产物；Web/PWA、CLI、桌面启动器和 DeepSeek Harness 是入口 Adapter。没有 API Key 时使用离线规则引擎，有配置时可调用兼容 LLM。

```text
CLI ───────────────┐
Web / PWA ────────┤
Desktop launcher ─┼──> Python Core ──> Project workspace / Artifact / Revision
DSH plugin ───────┘         │
                            ├──> offline rules or optional LLM
                            └──> Chromium export runtime
```

Generation、Feedback、Restore 与 Export 已通过 `StudioApplication` 形成共享应用 Interface。CLI、HTTP 同步入口和异步 Job 只负责 Adapter 转换、调度、序列化与错误状态映射；下一阶段转向 durable Project commit。

## 分层与 Module

```text
┌──────────────────────────────────────────────────────────────┐
│ Entry Adapters                                               │
│ CLI · HTTP v1 · Web/PWA · desktop launcher · DSH plugin      │
├──────────────────────────────────────────────────────────────┤
│ Application orchestration                                    │
│ StudioApplication: generate · feedback · restore · export    │
│ RC3 target: durable Project commit and recovery              │
├──────────────────────────────────────────────────────────────┤
│ Domain Modules                                               │
│ brief · composition · experts · generators · project memory  │
│ revisions · recipe run · template/user gallery               │
├──────────────────────────────────────────────────────────────┤
│ Infrastructure Modules                                       │
│ ProjectStore · JobManager · settings · diagnostics           │
│ local filesystem · optional LLM · Playwright/Chromium        │
└──────────────────────────────────────────────────────────────┘
```

### Entry Adapters

- `htmlninefox/cli.py`：命令行生成、反馈、导出和工作台入口。
- `htmlninefox/server/app.py`：HTTP v1、静态资源和 Web 工作台 transport。
- `htmlninefox/desktop.py`：本地桌面启动入口。
- `integrations/deepseek-harness/`：将 Harness 参数转换成 Html九尾狐 CLI 工作流。
- `htmlninefox/server/static/`：浏览器 Workspace、Canvas、Revision、Export 与动效交互。

Adapter 负责输入解析、认证或环境适配、响应序列化和错误映射。领域编排应逐步移入应用用例 Module。

### Domain 与应用 Module

- `application.py::StudioApplication`：共享 Generation、Feedback、Restore、Export request/result、错误模型、依赖装配和 Adapter 一致性。
- `pipeline.py`：生成 Implementation，组合需求、Skill、模板、意图、页面结构、Project Memory 和运行证据。
- `brief.py` / experts / generators：把用户输入转成可执行的创作规格和 HTML Artifact。
- `revisions.py`：创建、列出、命名、比较和 Restore Revision。
- `project_memory.py`：保存 Adoption Signal、匹配 Memory Recommendation，并服从 Explicit Requirement 优先级。
- `recipe_run.py`：记录分析、组合、生成、验证和交付阶段。
- `exporting.py`：隐藏浏览器选择、兼容性预检、PDF/PNG 分页和输出提交。

`exporting.py`、ProjectStore、ProjectMemoryStore 和 JobManager 已经具有较好的 Module depth。Generation、Feedback、Restore 与 Export 的应用编排已移入 `StudioApplication`；durable Project commit、跨进程锁、崩溃恢复和浏览器生命周期是 RC3 的主要深化区域。

### Infrastructure Module

- `server/storage.py::ProjectStore`：项目目录、Canvas Schema、项目 CRUD 与状态文件。
- `server/jobs.py::JobManager`：异步任务状态、持久化和启动恢复。
- `server/settings.py`：本地模型与运行设置。
- `server/diagnostics.py`：脱敏诊断包。
- `revisions.atomic_write()` 及各存储模块：当前分别实现文件写入可靠性；RC3 将统一 durable write 和 Project commit。

## 核心数据流

### 生成

```text
Explicit Requirement + selected Workspace context
  -> analysis and recommendation
  -> Generation Request
  -> pipeline / generator
  -> Artifact
  -> Revision + Recipe Run + project state
  -> preview or Export
```

### 反馈迭代

```text
current Artifact + feedback
  -> Feedback Iteration
  -> token/content changes
  -> new Artifact
  -> new Revision linked to parent
```

### 恢复

```text
historical Revision
  -> Restore request with expected current revision
  -> conflict check
  -> new current Revision with restore source
```

Restore 永远创建新 Revision，不覆盖历史。

### Project Memory

```text
Artifact adopted by user
  -> Adoption Signal
  -> safe preference extraction
  -> Project Memory
  -> explained recommendation on later Generation Request
```

未被采用的测试稿、失败稿、API Key、附件正文和完整反馈原文不应进入长期记忆。

## HTTP Interface v1

HTTP v1 是 Web/PWA 和未来轻客户端的兼容 seam。约束：

- v1 可以增加可选字段；删除字段或改变字段语义需要新版本。
- 错误响应提供稳定 code、可读 message 和 request id。
- 写操作限制在配置的 workspace / project root 内。
- Revision Restore 使用乐观并发检查，过期请求返回冲突。
- 超过一秒的长任务应进入 Job 模型并可查询状态。

当前具体 endpoint 以 `server/app.py` 和相应 API 测试为准。RC3 会把 endpoint transport 与应用用例分离，但保持 v1 响应兼容。

## 浏览器工作台

`server/static/index.html` 是当前应用壳，配合以下 JS Module：

- `canvas-engine.js`：Canvas 节点与连线基础行为。
- `canvas-productivity.js`：框选、批量移动、导航和生产力操作。
- `workbench-features.js`：工作台功能增强。
- `workbench-ui.js`：工作台布局模式、Icon、抽屉、命令面板与状态呈现。
- `interaction-system.js`：选择、提示和通用交互反馈。
- `motion-system.js`：可取消动效、并发预算和动效偏好。
- `sw.js`：PWA 缓存与离线壳。

视觉样式由 `pixel-garden-tokens.css` 提供品牌令牌，`workbench-system.css` 提供响应式布局、语义缩放、组件状态和 reduced-motion 收敛层。

动效是状态反馈，不是业务成功条件。所有关键行为必须在系统 / 减少 / 关闭三档动效偏好下完成。

RC3 将按 Project lifecycle、Generation lifecycle、Revision history、Export Center 四个业务 seam 继续拆分，避免只按文件长度拆分。

### 生命周期 Module（RC3-E）

`index.html` 主内联脚本只保留共享平台层（画布模型 `nodes/edges/camera`、DOM 引用、`api/flash/esc` 工具、检查器/时间线渲染与初始化）。四个业务域拆为独立经典脚本，沿用 IIFE + `window.Fox*` 出口：

- `lifecycle-projects.js` → `FoxProjects`（列表/重命名/复制/回收/画布同步）
- `lifecycle-generation.js` → `FoxGeneration`（推进、轮询、进度环、局部重跑、取消）
- `lifecycle-revisions.js` → `FoxRevisions`（差异、命名、恢复、反馈迭代）
- `lifecycle-exports.js` → `FoxExports`（导出中心、分析、任务、诊断）

draft 状态模块私有；域间只经命名空间 API 协作；约 27 个全局入口名保留为委托垫片，兼容 onclick 与浏览器测试锚点。生成按工作区单飞（epoch 守卫）并支持取消/停止等待；导出带 busy 守卫与过期结果丢弃。

## 存储与一致性

Project 包含 Workspace 状态、Artifact、Revision、Recipe Run、Memory 和任务证据。RC3-D 起全部 Project-rooted 写入统一走 `htmlninefox/durable.py` 的 `atomic_write`（同目录 mkstemp、fsync、原子 replace、POSIX 目录 fsync、Windows 并发替换重试）；Project 多文件提交带 journal 恢复；跨进程并发由文件锁协调。

一致性规则（RC3-D 已实现）：

1. 单文件写入使用同目录临时文件、flush、fsync 和原子 replace。
2. `revisions.commit()` 三段化：先写 `.commit-journal.json`（prepare），再按 snapshot → output → state 顺序提交（`.foxstate.json` 写入即提交点），成功后清理 journal。
3. commit 中断（异常、kill、断电）后，下一次 `load_state()` 在 Project 锁内确定性回滚：output 从 `rev{current}.html` 快照恢复，大于 current 的孤儿版本文件删除，journal 清理；state 已到 target 时仅清理 journal。
4. 同一 Project 的跨进程写入通过 `<输出根>/.locks/<项目名>.lock` 文件锁互斥（msvcrt/flock 双平台，默认 15s 超时），冲突返回稳定 `project_busy`（HTTP 409）；锁文件放在 Project 目录外，避免 Windows 上持锁 rename 目录失败。不同 Project 可并行。
5. 每次成功写入留下可诊断的 revision / job / request 信息；生成在 `.gen-` 临时目录完成后以 rename 原子发布。

仍未覆盖：Workspace 快照走主/备双文件恢复而非 journal；`feedback.md` 追加与导出报告为单文件写；这些场景的最坏结果是丢失一次追加记录，不破坏 revision 一致性。

## 安全边界

- API Key 只保存在本地设置或环境变量，不写入 Project、Memory、诊断包或前端日志。
- 文件访问必须限制在 workspace 和允许的素材范围内，拒绝路径穿越。
- 用户文本输出时执行上下文相关转义；生成的完整 HTML 在隔离预览环境中运行。
- 诊断包默认脱敏。
- Export 由本地 Playwright/Chromium 执行，不依赖远程截图服务。

## 测试架构

当前测试平铺在 `tests/`，按能力命名，不存在 `tests/integration/` 或 `tests/security/` 子目录。主要测试面：

- Python Core 与生成器
- HTTP v1 与 ProjectStore
- Revision、Restore、Memory、Job 和诊断
- Export 与真实 Chromium
- Canvas、Workspace、动效、键盘和 100 节点验收
- 发布版本一致性
- DSH 插件注册与打包

CI 运行发布元数据校验、完整 pytest、JavaScript 语法、DeepSeek Harness 插件测试和 Chromium acceptance。具体命令见 [CONTRIBUTING.md](../CONTRIBUTING.md)。

## 历史架构说明

项目早期以“5 agents、3 sinks、1 router”表达 brief、style、asset、generate、feedback 和联盟路由。这些概念仍能解释部分生成来源，但已经不再是完整的运行时分层。当前架构判断应以本文件、源码、HTTP 测试和 `CONTEXT.md` 为准。
