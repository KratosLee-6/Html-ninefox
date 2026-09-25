# RC3-E 迭代记录：浏览器生命周期 Module 拆分

- 日期：2026-09-25
- 关联 Issue：#5
- 代码提交：见文末提交记录
- 上一阶段：RC3-D 崩溃可恢复 Project 提交与跨进程锁
- 下一阶段：正式版候选（#6：实机、安装包、截图、文档、附件回读）

## 目标

把 `index.html` 主内联脚本（约 1765 行、125 个顶层函数、40 个顶层全局）中的 Project、Generation、Revision、Export 业务拆成独立生命周期 Module，让 UI 状态、取消、重试、恢复、导出围绕稳定 Interface 工作，同时治理快速连续操作的竞态。

## 交付

### 四个生命周期 Module（沿用既有 IIFE + `window.Fox*` 模式）

| 文件 | 命名空间 | 职责 |
|---|---|---|
| `lifecycle-projects.js` | `FoxProjects` | 列表加载、重命名、复制、回收、画布节点同步 |
| `lifecycle-generation.js` | `FoxGeneration` | 推进流水线、任务轮询、进度环、局部重跑、取消/停止等待 |
| `lifecycle-revisions.js` | `FoxRevisions` | 版本面板、差异、命名、恢复、口语反馈迭代 |
| `lifecycle-exports.js` | `FoxExports` | 导出中心、preflight 分析、导出任务、下载、诊断包 |

**边界规则（验收 1 落地）**：draft 状态（`revisionDraft`、`exportDraft`、`generatingNodes`）成为模块私有；域间只通过命名空间 API 协作（如生成完成后调 `FoxProjects.load()`，恢复完成后调 `FoxProjects.updateNodes()`）；画布渲染经 `FoxGeneration.renderBadge` 读进度态，孤儿节点清理经模块 API。`exportDraft` / `revisionDraft` 不再是全局变量（回归测试断言 `typeof === 'undefined'`）。

**兼容垫片**：约 27 个一行式全局委托保留在主内联块，覆盖全部 onclick 与浏览器测试锚点（含补齐的 `updateRevisionSelection`、`createJobProgressReporter`）。`index.html` 从 2574 行缩至约 2040 行。

### 竞态治理与取消（验收 2、5）

- **生成 epoch 守卫**：每工作区只允许一个在途生成；重复推进被拒绝并提示；结果落地前校验守卫，过期请求静默丢弃。
- **取消生成**：推进等待期顶栏出现「✕ 取消生成」——排队任务经 `DELETE /api/jobs/:id` 真取消；已在执行的任务按服务端语义转为「停止等待」（终止轮询、清理进度环、明示任务仍在后台完成）。
- **导出 busy 守卫**：导出进行中禁用开始按钮，重复触发直接拒绝；请求 token 防止切换产物后旧结果覆盖新面板。
- **[hidden] 兜底 CSS**：`.btn` 的 display 规则会覆盖 UA 的 `[hidden]`（连带修复 `#btn-install` 的潜在老 bug），补全局 `[hidden]{display:none!important}`。

### 登记与门禁

`app.py` STATIC_FILES、CI `test.yml` node --check、`CONTRIBUTING.md` 命令清单、`sw.js`（APP_SHELL + CACHE_NAME 升为 `htmlninefox-shell-rc3e-lifecycle-20260925`）四处同步登记四个新文件。

## 验收勾稽（Issue #5）

| 验收项 | 结果 |
|---|---|
| 四 Module 不读彼此内部变量 | ✅ draft 私有化 + 命名空间 API 协作；测试断言全局 draft 消失 |
| 快速连续操作不覆盖新状态 | ✅ 生成 epoch 守卫 + 导出 busy/token + 版本面板既有请求序号（回归测试覆盖） |
| 三档动效偏好继续有效 | ✅ `test_motion_system` 4/4 |
| 布局与 100 nodes/99 edges 门禁不退化 | ✅ 全量 Chromium 套件通过（含 390px/768px 与画布门禁） |
| 成功、错误、取消、恢复、导出截图更新 | ✅ 4 张 RC3 状态截图原位再生 + 新增 `generation-cancel.png`（清单同步至 15 张） |

## 验证

```text
新增 lifecycle 测试            4 passed
全量 pytest                    238 passed, 1 skipped
Chromium e2e（CI 同款）        22 / 22 通过
node --check（11 个 JS）+ 内联语法门禁  通过
```

## 已知取舍

- 「重试」不新增 UI：recipe-rerun 局部重跑与重新推进已覆盖。
- 垫片保留全局入口名是刻意的：兼容 onclick 与测试锚点；模块内部封闭。
- `workbench-features.js` 仍是顶层全局混入（历史反例），未混入本提交，留作后续清理。

## 提交记录

经仓库所有者确认门禁误报后经 GitHub API 提交推送；CI 状态见 [main Actions](https://github.com/KratosLee-6/Html-ninefox/actions?query=branch%3Amain)。
