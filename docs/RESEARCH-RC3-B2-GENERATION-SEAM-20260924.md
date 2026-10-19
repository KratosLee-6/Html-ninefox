# RC3-B2 生成用例 Seam 源码研究

- 日期：2026-09-24
- 任务：[Issue #1](https://github.com/KratosLee-6/Html-ninefox/issues/1)

## 当前调用链

CLI `expert` 自行校验空 prompt，直接调用 `pipeline.run_expert()`，再从松散字典输出 Rich 表格。[`cli.py`](../htmlninefox/cli.py) HTTP `/api/generate` 与异步 `/api/jobs` 都经过 `_generation_result()`；该方法解析附件、激活 AI 设置、读取 Project Memory 和私人图库、合并样式与组合参数、调用 pipeline、更新计数并重组响应。[`server/app.py`](../htmlninefox/server/app.py) DeepSeek Harness 只注册工作流，由 host shell 执行 `htmlninefox expert`，所以它是 CLI Adapter 的调用者，不是第三条 Python 调用链。[`workflow.md`](../integrations/deepseek-harness/workflow.md)

```text
CLI ───────────────> pipeline.run_expert
DSH -> shell -> CLI -> pipeline.run_expert
HTTP -> handler 编排 -> pipeline.run_expert
```

`pipeline.run_expert()` 同时完成分析、组合、生成、验证和交付，创建 Project，并写 HTML、Brief、Style、Assets、state、Revision 与 Recipe Run；失败时写失败 Recipe Run 后重新抛出任意异常。[`pipeline.py`](../htmlninefox/pipeline.py)

## 重复与契约

CLI 与 HTTP 分别处理 prompt 校验、参数装配、结果投影和错误映射。HTTP 独有附件、AI、Memory、图库与 usage side effect，因此同一 prompt 经 CLI/DSH 与 HTTP 时不保证相同上下文。共享 request 应包含 prompt、intent、skill、template、quiet_llm，以及分组后的附件、样式和组合选择；output root、stores、LLM、clock、ID、progress 属于依赖。共享 result 应包含 Project、files、intent、preset、route、verification、Recipe Run 与 Memory 结果；URL 和 Rich 文本由 Adapter 生成。应用错误统一为 `code/message/details`，不携带 HTTP status。

## 两个设计

**A：`generate(request, deps) -> result`**。单次调用清晰、容易直接测试，但 CLI、HTTP、Job 和未来 sidecar 都要理解并重复装配工作区 stores、settings、LLM、联盟 invoker、clock 和 writer；Feedback/Restore/Export 还会重复 deps 形状，公开 Interface 表面积偏大。

**B：`StudioApplication(deps).generate(request) -> result`**。构造时一次装配工作区依赖，调用方只学习 request/result，后续真实用例可复用 Project、Memory 与配置，Depth 和 Locality 更好。约束是 `StudioDependencies` 必须显式且不可变，禁止 service locator；对象不保存单次 request 或当前 Project，`generate()` 可并发；Job、HTTP status、URL 与 Rich 输出仍留在 Adapter。

**推荐 B。** CLI 与 HTTP 已是两个真实 Adapter，依赖也有明确工作区生命周期。纯函数可留在 `StudioApplication.generate()` 内部。目前选择容易逆转，不需要 ADR。

## 四步实施

1. 定义 `GenerationRequest`、`GenerationResult`、`GenerationError`、`StudioDependencies` 与 `StudioApplication.generate()`；首版继续委托 pipeline。
2. 把 `_generation_result()` 的附件、AI、Memory、图库和结果编排移入 Application；同步 HTTP 与 Job worker 调同一 seam，staging/rename 留在 Adapter。
3. CLI 改调同一 seam，保持命令、输出和 exit code；DSH 仍走 CLI，只固定 flag 到 request 的映射。
4. 增加 seam 成功与 `prompt_required` 失败测试，比较 CLI/HTTP 的 intent、preset、route、verification 和 Recipe stages，再跑完整门禁。

## 风险与验收

pipeline 创建了 `AllianceRouter`，但调用 `GenerateExpert` 时没有传 router/output path；结果可能报告联盟 route，而 Artifact 实际由本地 generator 生成。首切片只做 characterization，不顺手改变行为。

验收：HTTP endpoint、状态码、JSON 和 Project schema 不变；CLI/HTTP 对固定离线输入共享核心结果；Job staging、Revision 0、五阶段 Recipe Run 与 DSH CLI 映射保持；完整 pytest、JavaScript 门禁和 Chromium 22/22 通过。