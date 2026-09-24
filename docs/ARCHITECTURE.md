# Architecture · 当前架构

> 当前基线：`v0.5.0rc3`，更新于 2026-09-24。早期“5 agents · 3 sinks · 1 router”描述记录了项目起点，已经不足以说明当前 Project、Revision、Export、Memory、Job、Workspace 和插件能力。
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

当前 HTTP 和 CLI 都调用核心能力，但部分应用编排仍留在 HTTP handler 中。RC3 会建立明确的应用用例 Module，让所有 Adapter 复用相同 Interface。

## 分层与 Module

```text
┌──────────────────────────────────────────────────────────────┐
│ Entry Adapters                                               │
│ CLI · HTTP v1 · Web/PWA · desktop launcher · DSH plugin      │
├──────────────────────────────────────────────────────────────┤
│ Application orchestration                                    │
│ pipeline · feedback/rerun · revision/restore · export calls  │
│ RC3 target: explicit generate/feedback/restore/export use cases│
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

- `pipeline.py`：当前生成主链，组合需求、Skill、模板、意图、页面结构、Project Memory 和运行证据。
- `brief.py` / experts / generators：把用户输入转成可执行的创作规格和 HTML Artifact。
- `revisions.py`：创建、列出、命名、比较和 Restore Revision。
- `project_memory.py`：保存 Adoption Signal、匹配 Memory Recommendation，并服从 Explicit Requirement 优先级。
- `recipe_run.py`：记录分析、组合、生成、验证和交付阶段。
- `exporting.py`：隐藏浏览器选择、兼容性预检、PDF/PNG 分页和输出提交。

`exporting.py`、ProjectStore、ProjectMemoryStore 和 JobManager 已经具有较好的 Module depth。`pipeline.py` 和 HTTP handler 的 Interface 仍偏宽，是 RC3 的主要深化区域。

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

## 存储与一致性

Project 包含 Workspace 状态、Artifact、Revision、Recipe Run、Memory 和任务证据。当前实现已经具备单文件临时替换、部分 fsync、失败回滚和过期 Restore 冲突，但不同 Module 的写入策略仍不统一。

目标一致性规则：

1. 单文件写入使用同目录临时文件、flush、fsync 和原子 replace。
2. 一次 Project 操作涉及的文件集合以 Project commit 统一提交。
3. commit 中断后可以识别 prepare 状态并恢复到旧的完整状态或完成提交。
4. 同一 Project 的跨进程写入协调；不同 Project 可以并行。
5. 每次成功写入留下可诊断的 revision / job / request 信息。

这些是 RC3 计划，不能把当前 RC2 描述为已经完全支持多文件断电事务。

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
