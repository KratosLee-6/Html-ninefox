# Html九尾狐 v0.5 · 统一交互系统 / Interaction System

> 状态：v0.5.0-rc1 Project Memory 基线
> 日期：2026-09-14
> 视觉方向：Pixel Garden / 像素花园

## 中文

### 目标

统一工作台的操作反馈、异步状态、弹窗行为和快捷入口，让用户始终知道“系统正在做什么、下一步能做什么、失败后如何恢复”。交互系统不替代业务模块，只提供稳定的小接口。

### 公共接口

`window.FoxInteraction` 提供：

- `initialize()`：初始化 Toast、键盘与弹窗事件。
- `notify(message, type, options)`：显示 `success / info / warning / error` 通知，并抑制短时间重复消息。
- `setBusy(target, busy, label)`：统一按钮禁用、`aria-busy`、忙碌标签与原文恢复。
- `registerDialog() / openDialog() / closeDialog()`：管理焦点进入、Tab 循环、Escape 关闭和焦点恢复。
- `registerCommand() / searchCommands() / runCommand()`：注册和执行全局操作。

### 视觉验收

![v0.5.0-beta1 工作台总览](../assets/screenshots/v0.5.0b1/workbench-overview.png)

![v0.5.0-beta1 导出中心](../assets/screenshots/v0.5.0b1/export-center.png)

![v0.5.0-beta2 Recipe Run](../assets/screenshots/v0.5.0b2/recipe-run.png)

![v0.5.0-rc1 智能整卡连接](../assets/screenshots/v0.5.0rc1/canvas-smart-linking.png)

![v0.5.0-rc1 双向框选](../assets/screenshots/v0.5.0rc1/canvas-directional-selection.png)

### v0.5.0-alpha1 已覆盖

- 底部工作区状态继续保留，同时用 Toast 提供即时、可见、可读屏的反馈。
- `Ctrl+K` 同时检索“操作”和“节点”，支持上下方向键、Enter 执行、Escape 关闭。
- 命令包含输入需求、推进生成、新建工作区、AI 配置、诊断、主题、撤销、重做、框选和适配全部。
- 输入需求、AI 设置、模板预览、导出中心和命令面板统一处理焦点。
- 主生成、工作区生成、导出、诊断、需求分析、附件上传、AI 保存和连接测试统一使用忙碌态。

### v0.5.0-beta1 画布交互

- 节点改为自由拖动，不再在拖动过程中强制 16px 网格取整；按住 `Alt` 可临时停用吸附。
- 对齐参考线采用 7px 捕获、14px 释放的磁吸滞回，减少临界位置反复跳动。
- 端口坐标由真实视觉边界换算为世界坐标，修复缩放、平移和 CSS 位移造成的连线错位。
- 输入端口采用 48px 捕获、76px 释放的连接滞回；可直接拖到目标卡片上，精确端口始终优先于整卡吸附。
- 指针松开前会处理最后一帧坐标，避免快速拖动或连线结束时回跳。
- SVG 连线使用非缩放描边，缩放画布后仍保持清晰一致的线宽。
- 贝塞尔曲线依据横纵距离自适应弯曲，短连线更紧凑、长连线更自然。
- 框选提供实时命中预览：左→右要求完整包含，右→左触碰即选，按住 Alt 可从当前选择中减选。
- 端口命中区域主要向卡片外侧扩展，不再抢占正文区域的节点拖动。
- 自动适配为工作区导航器预留空间，最低缩放提高到 30%，生成后标题和内容保持可读。

### Beta 1 验收门槛

- 卡片正文与工作区标题栏均可真实鼠标拖动。
- 缩放和平移后端口连线仍对准视觉中心，并能稳定吸附。
- HTML 预览、生成自动连线、反馈迭代、自动适配和工作区持久化保持正常。
- 浏览器运行过程中无未处理 JavaScript 错误。

### v0.5.0-beta2 Recipe Run

- 每次生成都记录 `Analyze → Compose → Generate → Verify → Deliver` 五个阶段。
- 每个阶段保存状态、开始/结束时间、耗时、模型或生成器、兜底情况以及脱敏后的输入输出摘要。
- 运行状态通过异步任务实时返回，并显示在当前工作区底部状态条和产物检查器中。
- HTML 质量门禁检查文档声明、HTML/Body 结构、viewport 和产物体积，并生成兼容性分数。
- 项目目录新增 `recipe-run.json`，同时把最近一次运行写入 `.foxstate.json`，重启后仍可查看。
- `Generate` 与 `Verify` 阶段提供局部重跑；上游分析和组合结果会标记为复用，不重新消耗模型。
- 局部重跑使用父运行 ID 串联历史，便于后续建设产物版本树和差异对比。

### RC1 Project Memory

- 只有产物检查器中的明确采用信号才写入长期记忆。
- 本次明确需求优先，系统说明复用项与覆盖项。
- 项目记忆可查看、编辑、关闭和清空，并排除 API Key、附件正文和完整私人反馈。
- Analyze 与 Compose 阶段记录实际复用内容，产物状态持久化 memory_applied。

### Beta 2 验收门槛

- 生成任务完成后五个阶段均可见，并展示真实耗时与模型/生成器。
- 高频轮询不再与 Windows 原子状态文件写入冲突。
- 质量验证可在产物检查器中局部重跑，且保留父子运行关系。
- 运行记录与项目一起持久化，历史项目重新拖入画布后仍可查看。

### RC2 版本管理（本地增量，2026-09-18）

- 产物检查器进入版本差异弹窗，统一管理版本来源、命名、比较与恢复。
- 「恢复为新版本」保留已有版本，并还原生成配置；过期恢复请求返回冲突并刷新列表。
- 核心弹窗提供读屏名称、Tab 焦点循环、Escape 关闭与焦点恢复；预览 iframe 增加可读标题。
- 版本名按文本转义显示；390px 手机宽度下控件换行，内容区域滚动。
- 100 节点 / 99 连线覆盖渲染、框选、整体位移和持久化。此门禁测试耗时，不代表已达到 60fps。
- 详细边界见 [RC2 迭代记录](ITERATION-RC2-20260918.md)。

### 状态语义

| 状态 | 用途 | 颜色角色 |
| --- | --- | --- |
| Info | 正在分析、上传、生成或等待 | 钴蓝 |
| Success | 保存、生成、导出等操作完成 | 薄荷绿 |
| Warning | 可恢复但需要用户处理 | 陶土橙 |
| Error | 请求失败、运行失败或数据不可用 | 柔和红 |

### 后续阶段


- RC：Project Memory、产物版本差异、无障碍与 100 节点性能验收。

## English

### Goal

Provide one interaction layer for feedback, asynchronous controls, dialogs, and global commands. Users should always understand what the system is doing, what they can do next, and how to recover from failure.

### Public API

`window.FoxInteraction` exposes initialization, typed notifications, reversible busy states, accessible dialog focus management, and a registry for global commands.

### Alpha 1 Coverage

- Timeline messages also appear as deduplicated, screen-reader-friendly toasts.
- `Ctrl+K` searches actions and canvas nodes with arrow-key navigation and Enter execution.
- Preview, creation, AI settings, export, and command dialogs trap focus, close with Escape, and restore focus.
- Generation, export, diagnostics, uploads, analysis, AI saving, and connection tests share the same reversible busy-state behavior.

### Beta 1 Canvas Interaction

- Nodes move freely during drag instead of being continuously rounded to a 16px grid; holding `Alt` temporarily disables snapping.
- Alignment guides use 7px acquisition and 14px release hysteresis to avoid jitter near snap boundaries.
- Ports are measured from their rendered bounds and converted back to world coordinates, fixing connection offsets after zoom, pan, and CSS transforms.
- Connection targets use a 48px acquisition radius and 76px release radius, accept whole-card drops, and always prioritize an exact input port over a sticky card candidate.
- The final pointer position is processed before release, preventing end-of-drag and end-of-connection jumps.
- SVG connections use non-scaling strokes, port hit areas expand primarily outside cards, and fit-to-content preserves navigator space with a readable 30% minimum zoom.
- Adaptive Bézier controls keep short and long links visually smooth, while live marquee previews use full containment left-to-right and intersection selection right-to-left; Alt subtracts hits.

### Beta 1 Acceptance Gate

- Real pointer dragging works from both card content and workspace title bars.
- Ports remain visually centered and reliably connect after zooming and panning.
- HTML preview, generated links, feedback iteration, fit-to-content, persistence, and JavaScript error checks remain green.

### Beta 2 Recipe Run

- Every generation records `Analyze → Compose → Generate → Verify → Deliver` with status, timing, model or generator, fallback usage, and privacy-conscious input/output summaries.
- Live job snapshots appear in the active workspace timeline and output inspector.
- `recipe-run.json` is stored with the project, while the latest run is also embedded in `.foxstate.json`.
- The HTML quality gate checks document structure, viewport metadata, and output size.
- Generate and Verify support partial reruns, preserving upstream results and linking each rerun to its parent run.

### Next
RC adds Project Memory, artifact diffs, accessibility, and performance gates.
