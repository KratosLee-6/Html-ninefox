# Screenshots · 产品截图与验收证据

截图按版本目录保存。历史目录记录当时发布状态；`v0.5.0rc3-visual/` 记录 2026-09-24 发布的 `v0.5.0rc3` 视觉基础切片。

## 目录清单

| 目录 | 用途 |
|---|---|
| `v0.3.0b2/` | 早期工作台、图库、引导创作和多类输出 |
| `v0.4.0/` ～ `v0.4.2/` | Pixel Garden、LLM、Docker、Export Center 与发布工作台 |
| `v0.5.0a1/` ～ `v0.5.0rc2/` | 交互、Recipe Run、Project Memory、Revision 与 RC2 发布证据 |
| 0.5.0rc3/ | Chromium 发布验收生成的纸白、夜蓝与 Export Center 截图 |
| `v0.5.0rc3-visual/` | `v0.5.0rc3` 的响应式、组件状态与恢复/错误证据 |

## RC3 视觉证据（15 张）

### 布局、主题与响应式

- `workbench-paper-1440.png`
- `workbench-night-1440.png`
- `workbench-tablet-768.png`
- `workbench-mobile-390.png`
- `workbench-mobile-library.png`
- `classic-pixel-garden.png`

### 组件与业务状态

- `input-dialog-paper.png`
- `command-palette-search.png`
- `selected-node-inspector.png`
- `generated-output-inspector.png`
- `project-memory-saved.png`
- `export-center-ready.png`
- `export-analysis-error.png`
- `revision-restore-complete.png`
- `generation-cancel.png`

这些截图覆盖默认、选中、搜索、保存成功、生成完成、导出就绪、受控错误、恢复完成和取消等待等可观察状态。完整说明见 [RC3 视觉收敛记录](../../docs/ITERATION-RC3-VISUAL-CONVERGENCE-20260924.md)。

## 命名与拍摄要求

- 工作台截图采用 `功能-主题-宽度.png` 或 `业务状态.png`。
- 标准验收 viewport 为 `1440×900`、`768×1024` 和 `390×844`。
- 同一组截图使用同一浏览器缩放、字体环境和测试数据。
- 截图必须呈现真实页面，且敏感信息、API Key、用户私密正文已移除。
- 错误截图使用可控失败注入，避免依赖网络偶发故障。
- 更新现有主视觉时，同时更新中英文 README、迭代记录和本清单。

## 可复现采集

`tests/test_rc3_visual_evidence_states.py` 通过真实工作台路径生成命令搜索、Project Memory 保存、Export 分析错误和 Revision Restore 完成状态。`tests/test_rc3e_lifecycle_modules.py` 追加生成取消等待状态（`generation-cancel.png`）。默认测试使用临时目录；需要重新生成仓库证据时，可将 `HTMLNINEFOX_RC3_EVIDENCE_DIR` 指向：

```text
assets/screenshots/v0.5.0rc3-visual
```

提交前至少运行相关浏览器测试、JavaScript 语法检查和 `git diff --check`，并确认所有 Markdown 图片路径存在。
