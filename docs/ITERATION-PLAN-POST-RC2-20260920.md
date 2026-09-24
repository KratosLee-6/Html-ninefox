# RC2 后迭代计划：RC3 架构加固

- 制定日期：2026-09-20
- 最近校验：2026-09-24
- 输入：[mattpocock/skills 工程审计](AUDIT-MATTPOCOCK-20260920.md)
- 当前应用发布基线：`v0.5.0rc2`
- 当前 `main`：RC3-A、RC3-B1 与视觉基础切片已完成；完整测试 201 通过、1 跳过
- 目标：在扩展桌面端和更多生态 Adapter 前，让应用用例、持久化和浏览器工作台拥有稳定、可测试的 seam。

## 成功标准

RC3 完成时应满足：

1. `ARCHITECTURE.md`、`CONTRIBUTING.md`、CI 和真实目录一致。
2. HTTP、CLI 与至少一个外部 Adapter 复用同一应用用例，不复制生成、反馈、恢复或导出规则。
3. 项目多文件写入有清楚的 commit 边界、失败回滚和崩溃恢复测试。
4. 浏览器工作台的项目、生成、版本和导出生命周期各有小 Interface。
5. 现有用户行为、项目格式与 HTTP v1 保持兼容。
6. 每个阶段都能独立测试、评审和回滚。

## 执行原则

- 先固定公共 seam，再移动 Implementation。
- 每次只交付一个纵向用户能力，不按目录一次性重写。
- 只有出现第二个真实 Adapter 时才保留 seam；不要为假想未来添加接口。
- 测试穿过与生产相同的 Interface，避免读取内部状态。
- 新功能使用 TDD；已有缺陷和性能回归使用可复现的诊断循环。
- 每个阶段结束后，以阶段起点为 fixed point 做 Standards / Spec 双轴差异审查。

## RC3-A：可信工程基线

**目的**：让仓库文字成为可以执行的标准。

范围：

- 更新领域词汇、当前架构和贡献命令。
- 在 README 与 ROADMAP 暴露审计结论和本计划。
- 保留早期“5 agents / 3 sinks / 1 router”作为历史背景，不再作为当前结构。
- 明确当前 CI 真正运行的 pytest、发布元数据、JavaScript、DSH 和 Chromium 门禁。
- 配置 `AGENTS.md`、GitHub Issues、默认 triage 标签和 single-context 领域文档消费规则。

验收：

- 新贡献者只依赖 README / CONTRIBUTING 就能安装并跑完门禁。
- 文档不引用不存在的 `fox/`、`tests/integration/`、`tests/security/` 或未启用的 lint/type CI。
- 完整测试保持通过。

状态：**已完成（2026-09-21）**。配置与全项目复验见 [Matt Pocock skills setup 校验记录](VALIDATION-MATTPOCOCK-SETUP-20260921.md)。

## RC3-B：共享测试 seam 与应用用例首切片

**目的**：先降低安全重构成本，再让 transport Adapter 变薄。

第一步：共享 HTTP server fixture。

- 建立统一 pytest fixture，负责临时 workspace、server 启停、线程清理和 base URL。
- 迁移现有重复样板，保持测试观察行为不变。
- 不在这一阶段改 HTTP API。

状态：**已完成（2026-09-21）**。13 个工作台 HTTP 测试文件已迁移到统一 fixture，完整 pytest 与 Chromium 验收保持通过；实现与证据见 [RC3-B1 迭代记录](ITERATION-RC3-B1-20260921.md)。

并行完成的视觉基础（2026-09-24）：工作台主操作层级、四档响应式布局、语义缩放、本地 SVG Icon、组件状态、Paper / Pixel Night 主题与 14 张真实状态截图已经落地。该切片为后续浏览器业务 Module 提供稳定呈现层，不改变应用发布版本。详见 [RC3 视觉收敛记录](ITERATION-RC3-VISUAL-CONVERGENCE-20260924.md)。

第二步（当前下一步）：Design It Twice 比较生成用例方案。

候选 A：函数式应用服务。

```python
generate(request: GenerationRequest, deps: GenerationDeps) -> GenerationResult
```

候选 B：有状态应用服务。

```python
studio = StudioApplication(deps)
studio.generate(request) -> GenerationResult
```

选择标准：Interface 表面积、依赖注入难度、CLI/HTTP/DSH 复用、错误模型和测试成本。完成比较前不提前锁定方案。

首个纵向切片：

- 让 HTTP 生成和 CLI 生成经过同一 `generate` seam。
- 保持当前输出目录、Recipe Run、revision、Project Memory 和错误码行为。
- `_Handler` 只解析 transport 输入并序列化结果。

验收：

- 对同一固定输入，CLI 与 HTTP 的核心结果契约一致。
- 生成成功和一个失败路径有 seam 级测试。
- 现有 HTTP 与 Chromium 测试不变或只改 fixture。

## RC3-C：稳定 request/result 与剩余用例

**目的**：逐步替换跨 Module 的松散字典协议。

按使用频率引入：

1. `GenerationRequest` / `GenerationResult`
2. `FeedbackRequest` / `GenerationResult`
3. `RestoreRequest` / `RevisionResult`
4. `ExportRequest` / `ExportResult`

规则：

- 值对象只包含调用者必须知道的领域字段。
- HTTP JSON、CLI flags 和 DSH 参数由 Adapter 转换，不能进入领域对象。
- 错误使用稳定 code 和可读 message；transport 决定 HTTP status 或 CLI exit code。
- 一次只迁移一个用例，旧兼容入口在调用方迁移完后删除。

验收：

- `server/app.py` 不再编排生成、反馈、恢复和导出步骤。
- request/result 在 CLI 与 HTTP 至少两个 Adapter 中真实复用。
- HTTP v1 响应兼容测试通过。

## RC3-D：durable project commit

**目的**：给 Project 写入建立单一可靠性规则。

阶段 D1：统一单文件 durable write。

- 临时文件与目标文件位于同一目录。
- flush、fsync、原子 replace、临时文件清理和 Windows 错误映射集中实现。
- `revisions`、ProjectStore、JobManager、Project Memory、Recipe Run 逐步复用。

阶段 D2：定义 Project commit。

- 列出生成、反馈、恢复时必须一致提交的文件集合。
- 使用 manifest/journal 记录 prepare、commit、recover 状态。
- 失败时保留旧的完整状态，不留下半成品当前版本。

阶段 D3：跨进程协调。

- 为同一 Project 增加有超时和可诊断错误的锁。
- 不同 Project 仍可并行。
- 崩溃后可识别并恢复未完成 commit。

验收：

- 注入写入失败时，当前 Artifact、revision 索引和生成状态保持一致。
- 两个进程同时修改同一 Project 时，一个成功，另一个得到稳定冲突错误或安全重试。
- 恢复测试覆盖 prepare 后崩溃和 replace 中断。

## RC3-E：浏览器业务 Module

**目的**：让 UI 动效和产品状态围绕稳定生命周期工作。

按顺序提取：

1. Project lifecycle：打开、保存、复制、删除、恢复。
2. Generation lifecycle：分析、生成、取消、重试、结果就绪。
3. Revision history：加载、命名、差异、恢复。
4. Export Center：选项、任务状态、下载与兼容性报告。

每个 Module 应：

- 接收依赖和状态，返回结果或发出有限事件。
- 不直接读取其他 Module 的内部变量。
- 将可取消动效作为生命周期反馈，不把业务成功依赖在动画完成上。
- 尊重系统 / 减少 / 关闭三档动效偏好。

动效专项继续沿用现有计划：Anime.js 只在真实生成时间线对照试验通过、可离线打包、可取消且没有明显帧预算回归时采用；Motion Sites、Showreel Design、React Bits、Aceternity UI、Uiverse 主要用于规律和局部源码评估。

验收：

- 项目切换、生成重试、版本恢复和导出各有浏览器级测试。
- 快速连续操作不会产生过期动画覆盖新状态。
- 100 节点 / 99 连线门禁不退化。

## v0.6 启动门槛

桌面壳开发应在以下条件满足后启动：

- 应用用例可由 sidecar 直接复用。
- Project commit 对多进程和断电恢复有明确保证。
- `CONTRIBUTING.md` 的命令在 Windows 和 CI 都可执行。
- 20 revisions 与 100 nodes 的持续使用基线有记录。
- Safari 和 WebView2 至少完成核心路径实机验证。

## 阶段门禁

每个 RC3 增量至少运行：

```powershell
python scripts/check_release_version.py
python scripts/check_inline_js.py
node --check htmlninefox/server/static/canvas-engine.js
node --check htmlninefox/server/static/canvas-productivity.js
node --check htmlninefox/server/static/workbench-features.js
node --check htmlninefox/server/static/workbench-ui.js
node --check htmlninefox/server/static/motion-system.js
node --check htmlninefox/server/static/interaction-system.js
node --check htmlninefox/server/static/sw.js
python -m pytest tests -q -p no:cacheprovider
python e2e_verify.py
```

涉及 DSH 插件时再运行：

```powershell
cd integrations/deepseek-harness
npm ci --ignore-scripts --no-audit --no-fund
npm test
```

## 建议提交切分

1. `docs: align architecture and post-RC2 plan`
2. `test: centralize workbench server fixture`
3. `refactor: introduce shared generation use case`
4. `refactor: move feedback and revision use cases`
5. `fix: make project commits crash recoverable`
6. `refactor: isolate workbench lifecycle modules`

每个提交都保持产品可运行，不把 RC3 合并成一次大爆炸式重构。
