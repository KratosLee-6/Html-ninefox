# Html九尾狐工程审计：mattpocock/skills 方法版

- 审计日期：2026-09-20
- 项目基线：`v0.5.0rc2` 后的 `main`
- 方法来源：[`mattpocock/skills@c55ee46073ed923f86ce59a5eb3b6d895095d1b7`](https://github.com/mattpocock/skills/tree/c55ee46073ed923f86ce59a5eb3b6d895095d1b7)
- 详细上游研究：[mattpocock/skills 审计方法评估](research/MATTPocock-SKILLS-AUDIT-20260920.md)
- 后续执行计划：[RC2 后迭代计划](ITERATION-PLAN-POST-RC2-20260920.md)

## 审计结论

Html九尾狐已经越过“原型拼装”阶段：项目、版本、恢复、导出、Project Memory、任务恢复、浏览器验收和 DeepSeek Harness 插件均有真实实现与自动测试。当前主要风险不是缺少功能，而是应用层接口、持久化规则和工程文档没有跟上产品复杂度。

下一轮不应按文件大小机械拆分，也不应先为假想扩展添加抽象。优先建立 CLI、HTTP、未来桌面 sidecar 和 DSH 插件可以共同调用的应用用例 Module；随后统一 durable write 与项目事务边界；最后按真实业务 seam 继续拆浏览器工作台。

## 方法与范围

本次使用以下技能视角：

- `research`：只用上游仓库、当前源码、测试和 CI 作为事实来源。
- `domain-modeling`：检查领域词是否覆盖用户实际操作，并将规范词写回 `CONTEXT.md`。
- `codebase-design`：用 Module、Interface、Implementation、Depth、Seam、Adapter、Leverage、Locality 评估结构。
- `code-review`：只借用 Standards 与 Fowler smell 基线；它本身适合固定点差异审查，不代替全仓架构审计。

审计覆盖 Python Core、HTTP 服务、本地存储、版本历史、导出、浏览器工作台、测试结构、CI、架构文档和贡献指南。未把未提交的 `SKILL.md` / `skill/` 迁移内容纳入判断。

## 验证基线

2026-09-20 本机复验结果：

| 门禁 | 结果 |
|---|---:|
| 完整 pytest | **198 passed, 1 skipped** |
| 内联 JavaScript 语法 | 通过 |
| 6 个独立 JavaScript 文件 `node --check` | 通过 |
| 发布版本元数据 | `v0.5.0rc2` 一致 |

跳过项是 Windows 环境没有创建符号链接权限的既有条件，不是本轮回归。

## 当前 Module 地图

| 区域 | 主要 Module | 当前职责 | 评价 |
|---|---|---|---|
| 生成核心 | `pipeline.py`、experts、generators | 分析、组合、生成、反馈与运行证据 | 能力完整，公开输入仍以宽参数和字典为主 |
| HTTP Adapter | `server/app.py` | 静态资源、路由、解析、错误、项目、生成、导出、任务 | 变化原因过多，是最高优先级深化候选 |
| 项目存储 | `server/storage.py` | 项目目录、Canvas Schema、项目 CRUD | 较深的 Module，应继续收拢项目持久化规则 |
| 版本历史 | `revisions.py` | revision、差异、命名、恢复与原子写 | 隐藏了较多复杂度，但 Interface 偏宽 |
| 长期记忆 | `project_memory.py` | 采用信号、建议、长期偏好 | 调用面集中，领域边界较清楚 |
| 异步任务 | `server/jobs.py` | 任务状态、持久化、恢复 | 深度较好，需纳入统一写入规则 |
| 导出 | `exporting.py` | 浏览器选择、预检、PDF/PNG、输出提交 | 当前最成熟的深 Module 之一 |
| 浏览器工作台 | `index.html` 与静态 JS Modules | 项目、画布、生成、版本、导出、动效 | 已开始模块化，但业务状态仍集中在大页面 |

## 主要发现

### P0：工程文档与真实门禁不一致

旧 `ARCHITECTURE.md` 仍描述 5 agents、3 sinks、1 router，并引用不存在的分层测试目录。旧 `CONTRIBUTING.md` 要求对 `fox/` 运行 ruff、black、mypy，但当前包名是 `htmlninefox/`，项目依赖和 CI 也没有这些门禁。

这会让贡献者按错误命令工作，也会让后续 Standards 审查把过期文字当成硬标准。本轮已同步重写架构概览、贡献指南和领域词汇表。

### P1：HTTP Adapter 承担领域编排

`htmlninefox/server/app.py` 约 31 KB，单个 `_Handler` 同时处理传输、静态资源、路由选择、参数校验、错误映射、项目生命周期、生成、反馈、版本、导出、图库、记忆和任务。大量 `if path == ...` / `startswith(...)` 让每项产品增量都可能修改同一文件。

建议建立应用用例 Module，先覆盖已有的第二个调用方，而不是先定义抽象 Protocol：

```text
GenerateRequest -> generate() -> GenerationResult
FeedbackRequest -> feedback() -> GenerationResult
RestoreRequest  -> restore()  -> RevisionResult
ExportRequest   -> export()   -> ExportResult
```

HTTP、CLI、桌面 sidecar 和 DSH 只负责各自 transport 的解析与序列化。

### P1：持久化原子性规则分散

`revisions.py`、`server/storage.py`、`server/jobs.py`、`project_memory.py`、Recipe Run 和 pipeline 各自采用不同写文件方式。已有单文件临时替换与失败回滚，但一次项目操作涉及多个文件时，没有统一 transaction 边界；跨进程并发写入和断电恢复也仍是 RC2 已知限制。

应先统一一个深 Module，隐藏临时文件、flush、fsync、replace、回滚和 journal 规则，再定义哪些文件属于同一次 Project commit。跨进程锁应在事务边界明确后加入。

### P1：pipeline Interface 过宽，领域数据依赖松散字典

`run_expert()` 接收 prompt、skill、template、intent、style overrides、composition、memory context、progress callback 等数据簇。源码中约有 190 行出现 `dict[str, Any]` 或 `Dict[str, Any]`，生成、反馈、恢复和导出状态经常以嵌套字典跨 Module 传递。

不建议一次性全量类型化。先在 CLI/HTTP 共用 seam 引入少量稳定值对象：`GenerationRequest`、`GenerationResult`、`RevisionId`、`RestoreRequest`、`ExportRequest`。值对象要减少调用者必须记住的字段组合和错误模式。

### P2：浏览器工作台仍以大页面为状态中心

`index.html` 超过 2,500 行，`workbench-features.js`、`canvas-productivity.js` 等已经承担部分独立行为，但项目生命周期、生成生命周期、revision 和导出状态仍相互穿插。

下一轮应按业务 seam 提取 Project lifecycle、Generation lifecycle、Revision history、Export Center。不要仅以“文件太长”为理由拆文件；每次提取都要有明确 Interface 和穿过该 Interface 的浏览器验收。

### P2：测试 server 启动样板重复

至少 13 个测试文件直接创建 `ThreadingHTTPServer` 和后台线程。共享 pytest fixture 可以统一启动、关闭、临时目录和失败清理，减少端口与线程泄漏风险，并为以后替换 HTTP Adapter 提供单一测试 seam。

这是低风险、可单独交付的第一项代码改进。

## 模块深度判断

| Module | 删除后复杂度会怎样 | 判断 |
|---|---|---|
| `exporting.py` | 浏览器探测、分页、兼容性和提交规则会散回多个调用者 | 深，保留并深化 |
| `ProjectStore` | 项目目录、Canvas Schema 和 CRUD 规则会散开 | 深，适合作为项目持久化入口 |
| `JobManager` | 任务恢复和状态写入会散开 | 深，纳入统一 durable write |
| `ProjectMemoryStore` | 采用信号与偏好规则会回到 HTTP/pipeline | 深，维持领域边界 |
| `revisions.py` | 版本规则会散回调用方，但当前公开函数较多 | 有深度，需收窄 Interface |
| `_Handler` | 删除后大量业务编排仍然存在，只是失去 transport 包装 | Adapter 过厚，应把业务用例移出 |

## 领域语言修订

本轮将以下词加入 `CONTEXT.md`：

- Artifact：用户可查看、导出或交付的创作结果。
- Revision：Artifact 与生成上下文的不可变历史快照。
- Restore：从历史 Revision 创建新的当前 Revision，不覆盖历史。
- Workspace：组织需求、风格、素材、Skill 和 Artifact 的视觉编排空间。
- Canvas Node：Workspace 中可定位、选择和连接的创作单元。
- Generation Request：一次生成所需的明确要求与选定上下文。
- Feedback Iteration：针对现有 Artifact 的一次自然语言修改请求及其新结果。
- Export：将 Artifact 转换为可交付格式并记录兼容性信息的操作。

目前没有发现同时满足“难逆转、缺少上下文会显得意外、存在真实取舍”的新决定，因此不创建 ADR。

## 风险排序

| 优先级 | 风险 | 影响 | 首个可验收动作 |
|---|---|---|---|
| P0 | 文档与工程现实漂移 | 贡献和审查标准失真 | 合并本轮文档基线 |
| P1 | HTTP Adapter 继续膨胀 | 每项功能改动互相干扰 | 提取一个生成用例纵向切片 |
| P1 | 多文件写入没有事务边界 | 断电或多进程时状态不一致 | 定义 Project commit 文件集合 |
| P1 | 字典协议扩散 | 字段组合和错误模式难验证 | 在共用 seam 引入 request/result |
| P2 | 前端状态集中 | UI 迭代易产生竞态 | 提取 Project lifecycle Module |
| P2 | 测试启动重复 | 维护与清理不一致 | 新建共享 server fixture |

## 不建议现在做的事

- 不为只有一个实现的内部依赖批量创建 Protocol。
- 不以 LOC 为唯一依据重写 `index.html` 或 `server/app.py`。
- 不一次性替换全部字典或全面改成新的框架。
- 不在应用用例和事务边界稳定前启动 Tauri 桌面壳复制业务规则。
- 不把设计灵感站的效果代码直接纳入核心依赖；动效资源继续按许可、离线打包、可取消和帧性能门禁逐项验证。

## 审计后的推荐方向

下一阶段命名为 **RC3 架构加固**。它先恢复可信工程基线，再依次交付共享测试 seam、应用用例 Module、稳定 request/result、durable project commit 和前端业务 Module。详细范围、验收标准与退出条件见[执行计划](ITERATION-PLAN-POST-RC2-20260920.md)。
