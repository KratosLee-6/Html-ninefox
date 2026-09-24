# RC3-C 迭代记录：共享 Feedback、Restore 与 Export 用例

- 日期：2026-09-24
- 关联 Issue：#3
- 代码提交：`d8c1694`
- 代码 CI：[GitHub Actions #36005989933](https://github.com/KratosLee-6/Html-ninefox/actions/runs/36005989933)
- 上一阶段：RC3-B2 共享 Generation use case
- 下一阶段：RC3-D durable Project commit

## 目标

在 Generation seam 稳定后，把 Feedback Iteration、Restore 和 Export 依次迁移到共享应用 Interface。CLI、HTTP 与异步 Job 只转换输入、序列化结果和映射错误，不再直接编排对应业务步骤。

本轮保持 HTTP v1、Project schema、Revision 历史、Export Center Job、CLI 既有输出和 DSH 插件边界兼容。

## 稳定 Interface

```python
studio.feedback(FeedbackRequest(...)) -> FeedbackResult
studio.restore(RestoreRequest(...)) -> RevisionResult
studio.export(ExportRequest(...)) -> ExportResult
```

新增值对象覆盖：

- Feedback 的项目、自然语言要求、dry-run、规则、token 变化和模型来源。
- Restore 的目标 Revision、当前 Revision 冲突保护和新 Revision 结果。
- Export 的格式、范围、页码、视口、纸张、文件、报告、警告与浏览器证据。

错误统一使用稳定 `code / message / details`，由 CLI 映射退出码，由 HTTP Adapter 映射状态码。

## 用户可观察行为

### Feedback

- CLI 与 HTTP 对同一 Project 和反馈产生一致的 Revision、规则和设计 token。
- 模糊反馈返回 `feedback_not_actionable`，继续提示用户补充颜色、字号或布局等信息。
- 损坏的 Project 不再让 CLI 泄漏内部 `RevisionError`；CLI 返回退出码 2，HTTP 保持 `project_state_invalid` / 409。
- CLI `--dry-run` 继续只解析反馈，不创建新 Revision。

### Restore

- 新增 `htmlninefox restore` CLI 命令。
- Restore 需要 `--revision` 和 `--expected-revision`，并发修改返回 `revision_conflict`。
- 恢复历史版本会创建新的当前 Revision，保留恢复点之后的全部历史。
- HTTP `/api/projects/{name}/restore-revision` 的响应和错误码保持兼容。

### Export

- CLI 与 HTTP 异步 Job 通过同一 `ExportRequest / ExportResult`。
- 页码范围、格式、纸张、视口、兼容性分析和浏览器错误在应用 Interface 内统一。
- HTTP 提交 Job 前仍同步验证项目和参数；导出文件、报告、下载地址和兼容性分数保持不变。
- CLI PDF / PNG 输出继续生成 `export-report.json`。

## 架构结果

`htmlninefox/cli.py` 和 `htmlninefox/server/app.py` 已不再直接调用：

- `pipeline.run_feedback`
- `revisions.restore`
- `exporting.normalize_export_request`
- `exporting.export_project`

应用层通过延迟装配 server 与 Export 依赖，避免 CLI 新进程启动时形成循环导入。

## DeepSeek Harness

工作流新增：

- `FeedbackRequest` 参数映射。
- `htmlninefox restore` 与 `RestoreRequest` 参数映射。
- `ExportRequest` 参数映射。
- 明确 Restore 必须读取真实当前 Revision，不能猜测 `--expected-revision`。

插件源码安装引用固定到已验证代码提交 `d8c1694e77156032116bef3830009597f5289afd`。

## 验证

```text
application seams              20 passed
full pytest                    221 passed, 1 skipped
Chromium acceptance            22 / 22 passed
release / JavaScript gates     passed
DeepSeek Harness               2 / 2 passed
```

新增测试覆盖成功、模糊反馈、损坏 Project、Revision 冲突、非法导出格式、浏览器运行失败包装、CLI Restore 和真实 CLI PNG Export。

## 后续

RC3-D 将建立 durable Project commit：

1. 统一单文件 durable write。
2. 引入 Project prepare / commit / recover 边界。
3. 增加跨进程锁和稳定冲突错误。
4. 注入写入中断与崩溃恢复测试。
