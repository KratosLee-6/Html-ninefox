# RC3-B2：共享 Generation Use Case

- 日期：2026-09-24
- GitHub 任务：Issue #1
- 状态：实现完成，等待 `main` CI 回读
- 目标：让 CLI、HTTP 同步生成、异步 Job 与 DeepSeek Harness 经过同一 Generation Interface。

## Design It Twice

### 候选 A：函数式应用服务

```python
generate(request: GenerationRequest, deps: GenerationDependencies) -> GenerationResult
```

优点是单次调用直观，纯函数容易替换和测试。缺点是 CLI、HTTP、Job 和未来 sidecar 都必须了解并重复装配 workspace、输入、AI 设置、Project Memory、私人图库、生成目录和 pipeline runner；继续加入 Feedback、Restore 与 Export 后，依赖参数会在多个 Adapter 中重复增长。

### 候选 B：有状态应用 Module

```python
studio = StudioApplication(dependencies)
result = studio.generate(request)
```

`StudioApplication` 只保存不可变的 workspace 依赖，不保存当前 Project 或单次 request。调用方只需要构造 `GenerationRequest`，结果通过 `GenerationResult`、`VerificationResult`、`RecipeRunResult` 和 `MemoryApplicationResult` 返回。

### 选择

选择候选 B。它让依赖装配集中在一个位置，CLI、HTTP 与 Job Adapter 的 Interface 更小，并能在 RC3-C 继续加入 Feedback、Restore 与 Export，而不让每个 Adapter 重复理解底层 stores。内部仍可保留纯函数和可注入的 `GenerationRunner`，因此该选择可逆，不需要 ADR。

## 已实现

- 新增 `htmlninefox/application.py`，定义共享 Generation request/result、错误模型和 workspace 依赖。
- CLI `expert` 改用 `StudioApplication.generate()`，保留输出目录、表格、exit code 和环境变量 AI 自动发现。
- HTTP `/api/generate` 只负责 JSON → request 与 result → JSON 转换。
- 异步 `/api/jobs` 使用同一 request 校验与 generation seam；附件可以在没有文字 Prompt 时触发有效生成。
- Job staging、最终 rename、Project schema、Revision 0 和 Recipe Run 五阶段保持不变。
- `prompt_required` 与 `generation_failed` 成为 transport 无关的稳定应用错误。
- DeepSeek Harness 工作流记录 `prompt`、`--type`、`--skill`、`--template`、`--quiet-llm` 和 `--output` 到 `GenerationRequest` 的映射，并由真实 CLI 生成状态验证。
- 共享结果使用小值对象包装 Verification、Recipe Run、Memory 和组合块，不新增 `dict[str, Any]` 跨 Module 协议。

## 用户可观察行为

- 同一固定离线需求通过 CLI 或 HTTP 时，intent、preset、route、Verification、Recipe stages 和 Project Memory 应用保持一致。
- CLI 仍会在没有本地 AI 设置时探测 MiniMax、OpenAI 或 Anthropic 环境变量；`--quiet-llm` 继续强制离线。
- HTTP 同步生成和异步 Job 使用同一业务规则。
- 无文字 Prompt 但有有效附件的异步任务现在可以生成 Artifact。
- pipeline 运行失败不会泄漏不稳定异常类型，而是返回 `generation_failed`。

## 验证

```text
release metadata               passed
inline / standalone JavaScript passed
Generation seam tests          7 passed
full pytest                     208 passed, 1 skipped
Chromium acceptance             22 / 22 passed
DeepSeek Harness                2 / 2 passed
```

完整命令沿用 `docs/ITERATION-PLAN-POST-RC2-20260920.md` 的 RC3 阶段门禁。

## 后续

RC3-C 按一次一个用例推进：

1. FeedbackRequest / FeedbackResult
2. RestoreRequest / RevisionResult
3. ExportRequest / ExportResult

迁移时继续保持 HTTP v1、CLI 输出、Project schema 和现有 Revision 语义兼容。
