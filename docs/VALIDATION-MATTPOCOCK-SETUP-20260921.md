# Matt Pocock Skills Setup 与全项目校验记录

- 日期：2026-09-21
- 仓库：`KratosLee-6/Html-ninefox`
- 分支：`main`
- 应用基线：`v0.5.0rc2`
- 使用技能：`setup-matt-pocock-skills`
- 关联审计：[mattpocock/skills 工程审计](AUDIT-MATTPOCOCK-20260920.md)
- 后续计划：[RC3 架构加固](ITERATION-PLAN-POST-RC2-20260920.md)

## 结论

仓库已完成 Matt Pocock 工程技能所依赖的基础配置：GitHub Issues 是唯一 issue tracker，默认五角色 triage 标签已配置，领域文档采用 single-context 布局，Agent 在开始工程工作前可从 `AGENTS.md` 找到 tracker、标签和领域文档规则。

当前代码与发布基线通过完整 Python、JavaScript、Chromium 和 DeepSeek Harness 门禁。下一项代码迭代应进入 RC3-B1：统一 pytest HTTP server fixture；完成后再使用 Design It Twice 固定应用用例 Interface。

## Setup 配置

| 配置 | 结果 | 位置 |
|---|---|---|
| Agent 入口 | 已创建 | [`AGENTS.md`](../AGENTS.md) |
| Issue tracker | GitHub Issues，PR 不进入默认 triage 队列 | [`docs/agents/issue-tracker.md`](agents/issue-tracker.md) |
| Triage 标签 | 默认五角色，无别名 | [`docs/agents/triage-labels.md`](agents/triage-labels.md) |
| Domain docs | single-context | [`docs/agents/domain.md`](agents/domain.md) |
| 领域词汇 | 根目录单一词汇表 | [`CONTEXT.md`](../CONTEXT.md) |
| ADR | 按需创建，不提前填充虚构决定 | [`docs/adr/`](adr/) |

GitHub 已回读确认以下标签存在：

- `needs-triage`
- `needs-info`
- `ready-for-agent`
- `ready-for-human`
- `wontfix`

当前仓库没有 Issue。后续工程任务可以由 `to-tickets` 或人工规划发布到 GitHub Issues。

## 全项目门禁

| 门禁 | 结果 |
|---|---:|
| 完整 pytest | **198 passed, 1 skipped，117.97 秒** |
| Chromium 端到端验收 | **22 / 22 通过** |
| DSH 插件注册、重载、卸载 | **通过** |
| DSH 发布 tarball 脱离源码安装 | **通过** |
| 发布元数据一致性 | `v0.5.0rc2` 通过 |
| 内联 JavaScript | 通过 |
| 6 个独立 JavaScript 文件 `node --check` | 通过 |
| Markdown 本地链接 | 通过 |

pytest 跳过项仍是 Windows 当前环境没有创建符号链接权限的既有条件。

Chromium 验收在受限环境下无法写入用户级 `~/.htmlninefox` brief/feedback cache，相关写入按设计非阻塞；生成、反馈、截图、Workspace、模板、Export 和控制台错误检查仍全部通过。

DSH 测试第一次在受限环境中因用户级 npm cache 返回 `EPERM`。使用正常本机权限重跑同一 `npm test` 后 **2 / 2 通过**，证明失败来自测试环境写权限，不是插件实现或 tarball 回归。

## 路线图校验

本轮修正三类历史漂移：

1. 删除“正式仓库无源码”的旧风险描述；当前公开仓库已有源码、Release 和 CI。
2. 将 GitHub Actions 标为已完成，并明确现有 pytest、JavaScript、DSH、Chromium 与版本门禁。
3. 将旧的配置向导、ZIP 和启动器优先序替换为 RC3-B～RC3-E 架构加固顺序。

## 后续迭代规划

### RC3-B1：共享测试 server fixture

目标：统一至少 13 个测试文件重复的 `ThreadingHTTPServer` 和后台线程样板。

验收：

- fixture 统一临时 workspace、server 启停、base URL 和线程清理。
- 迁移后所有测试继续从 HTTP 公共行为观察结果。
- 不改变 endpoint、响应字段和浏览器行为。
- 完整 pytest 与 Chromium 22/22 保持通过。

### RC3-B2：Design It Twice

比较两个真实方案：

1. 函数式 `generate(request, deps) -> result`
2. `StudioApplication(deps).generate(request) -> result`

选择时评估 Interface 表面积、CLI/HTTP/DSH 复用、错误模型、依赖注入和测试成本。形成实现方案后，如决策满足难逆转、真实取舍和缺少上下文会显得意外三项条件，再创建首个 ADR。

### RC3-C：共用应用用例

按 Generation、Feedback、Restore、Export 顺序引入 request/result，让 HTTP handler 只处理 transport。每次迁移一个纵向用例，保持 HTTP v1、Project schema 与当前 CLI 兼容。

### RC3-D：Project commit

统一 durable single-file write，定义一次 Project 操作的文件集合，再增加 journal、跨进程锁和崩溃恢复测试。

### RC3-E：浏览器生命周期 Module

按 Project、Generation、Revision、Export 生命周期提取 Module。动效作为可取消状态反馈，不成为业务成功条件，并继续执行三档偏好、竞态和 100 节点门禁。

## Issue tracker 使用建议

下一轮可以把 RC3-B 拆成一个 GitHub map issue 和两个子 issue：

- RC3-B1：共享 HTTP server fixture
- RC3-B2：生成应用用例 Design It Twice

完成规格后分别应用 `ready-for-agent` 或 `ready-for-human`。尚未形成可执行规格的请求使用 `needs-triage`；缺少复现或验收信息时使用 `needs-info`。
