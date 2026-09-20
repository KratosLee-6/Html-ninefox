# mattpocock/skills 对 HtmlNineFox 的审计方法评估

- 日期：2026-09-20
- 上游仓库：[mattpocock/skills](https://github.com/mattpocock/skills)
- 固定来源提交：[`c55ee46073ed923f86ce59a5eb3b6d895095d1b7`](https://github.com/mattpocock/skills/tree/c55ee46073ed923f86ce59a5eb3b6d895095d1b7)
- 范围：只评估上游仓库中的工程技能；项目判断以当前 HtmlNineFox 仓库文件为证据。

## 结论

这套技能适合把 HtmlNineFox 的下一轮迭代拆成四个阶段：先用 `research` 固定事实，再用 `domain-modeling` 和 `codebase-design` 审计术语、接口与模块深度；实施时使用 `tdd` 或 `diagnosing-bugs`；完成一个明确增量后，再用 `code-review` 对固定基线做 Standards / Spec 双轴复核。

`code-review` 不是全仓架构审计器，它只审查 `HEAD` 相对固定点的差异。当前项目更应先做领域和模块审计，再将下一轮迭代拆成可审查的短差异。

## 适用技能与硬约束

### 1. `research`：审计的证据入口

工作流只有三步：后台研究者只查第一方资料；每项结论追溯到资料所有者；结果写入仓库中的单一 Markdown 文件，并逐项引用来源。当前记录本身按这个流程生成。来源：[research/SKILL.md](https://github.com/mattpocock/skills/blob/c55ee46073ed923f86ce59a5eb3b6d895095d1b7/skills/engineering/research/SKILL.md)。

对 HtmlNineFox 的约束：未来评估浏览器兼容、DeepSeek Harness、Playwright 或打包工具时，应优先引用对应官方仓库、规范或源码；不要把设计灵感站、博客和二手教程当成技术事实。

### 2. `domain-modeling`：先修正项目语言

精确工作流是：读取现有词汇表；发现冲突术语时立即指出；把模糊词替换为单一规范词；用具体边缘场景压力测试关系；再和代码交叉核验；术语一旦确定便立即更新 `CONTEXT.md`。`CONTEXT.md` 只能是领域词汇表，不能放实现细节、规格或临时笔记。ADR 也只能在“难以逆转、缺少上下文会显得意外、确实存在取舍”三个条件同时成立时创建。来源：[domain-modeling/SKILL.md](https://github.com/mattpocock/skills/blob/c55ee46073ed923f86ce59a5eb3b6d895095d1b7/skills/engineering/domain-modeling/SKILL.md)、[CONTEXT-FORMAT.md](https://github.com/mattpocock/skills/blob/c55ee46073ed923f86ce59a5eb3b6d895095d1b7/skills/engineering/domain-modeling/CONTEXT-FORMAT.md)、[ADR-FORMAT.md](https://github.com/mattpocock/skills/blob/c55ee46073ed923f86ce59a5eb3b6d895095d1b7/skills/engineering/domain-modeling/ADR-FORMAT.md)。

当前 [CONTEXT.md](../../CONTEXT.md) 已定义 Project、Recipe Run、Project Memory、Adoption Signal、Memory Recommendation 和 Explicit Requirement，但工作台中已经出现版本、修订、恢复、画布节点、连线、动效偏好、导出任务等高频概念。下一轮应先通过真实代码和用户场景判断哪些是领域概念，再补充规范词和 `_Avoid_`，不要把 HTTP 路由、文件锁、CSS 动画等实现词写进去。项目目前没有 `docs/adr/`；这不是缺陷，只有满足三项门槛的决定才应创建首个 ADR。

### 3. `codebase-design`：本轮全仓审计的主技能

它要求统一使用 **Module、Interface、Implementation、Depth、Seam、Adapter、Leverage、Locality** 这套词汇。核心判断包括：

- Interface 包含调用者必须知道的参数、约束、顺序、错误模式、配置和性能特征；不仅是类型签名。
- 用“删除测试”判断模块价值：删除后复杂度若散回多个调用者，模块有深度；复杂度若直接消失，它可能只是转发层。
- Interface 同时是测试面；测试必须穿过同一 seam，而不是越过接口读取内部状态。
- 只有一个 adapter 时，seam 仍是假设；至少两个合理 adapter 才说明变化点真实存在。
- 设计应接受依赖、返回结果，并缩小接口表面积。

来源：[codebase-design/SKILL.md](https://github.com/mattpocock/skills/blob/c55ee46073ed923f86ce59a5eb3b6d895095d1b7/skills/engineering/codebase-design/SKILL.md)。

深化模块前还要按依赖分类：进程内逻辑可直接合并；有本地替身的依赖用替身测试；自有远程服务用 port 加生产/内存 adapter；真正的第三方服务才用 mock。深化后要在新接口处重新测试，并删除已被覆盖的浅层单元测试，避免新旧测试叠层。来源：[DEEPENING.md](https://github.com/mattpocock/skills/blob/c55ee46073ed923f86ce59a5eb3b6d895095d1b7/skills/engineering/codebase-design/DEEPENING.md)。

当前候选审计簇包括：

- Python 服务端：`htmlninefox/server/app.py`、`storage.py`、`jobs.py`、`settings.py`，重点检查路由层是否承担了领域编排、存储事务和响应转换等多种变化原因。
- 浏览器工作台：`canvas-engine.js`、`canvas-productivity.js`、`workbench-features.js`、`interaction-system.js`、`motion-system.js`，重点检查项目版本、画布操作、反馈提示和动效生命周期是否各有清晰 seam，还是依赖全局 DOM 状态和跨文件调用约定。
- 外部适配：LLM provider、文件系统、Playwright、DeepSeek Harness 插件和打包入口，逐项确认是否真的存在两个 adapter；没有真实变化点时不要为了“可扩展”增加 port。

这些只是候选簇，文件较大本身不能证明设计浅。审计必须列出调用者需要掌握的完整 Interface，并执行删除测试后才能提出拆分或深化建议。

如果一个候选值得重构，应使用 “Design It Twice”：先写清约束和依赖分类，再并行提出至少三种差异明显的接口，分别优化最小接口、扩展性和默认调用路径；最后按 Depth、Locality 和 Seam placement 比较并给出主张。来源：[DESIGN-IT-TWICE.md](https://github.com/mattpocock/skills/blob/c55ee46073ed923f86ce59a5eb3b6d895095d1b7/skills/engineering/codebase-design/DESIGN-IT-TWICE.md)。

### 4. `tdd`：用于选定迭代项后的纵向实现

硬约束是先和用户确认要测试的 seam，再写测试；测试只验证公开接口可观察行为。每轮必须是一个 seam、一个失败测试、一个最小实现，按纵向 tracer bullet 前进。不能一次先写完所有测试，也不能在 red → green 循环中夹带重构；重构放到评审阶段。期望值必须来自规格、已验证示例或固定字面量，不能用与实现相同的算法重算。来源：[tdd/SKILL.md](https://github.com/mattpocock/skills/blob/c55ee46073ed923f86ce59a5eb3b6d895095d1b7/skills/engineering/tdd/SKILL.md)、[tests.md](https://github.com/mattpocock/skills/blob/c55ee46073ed923f86ce59a5eb3b6d895095d1b7/skills/engineering/tdd/tests.md)。

Mock 只放在系统边缘，例如第三方 API、时间、随机数或必要的文件系统 seam；项目自有模块和内部协作者不应互相 mock。来源：[mocking.md](https://github.com/mattpocock/skills/blob/c55ee46073ed923f86ce59a5eb3b6d895095d1b7/skills/engineering/tdd/mocking.md)。

对 HtmlNineFox，可优先把现有 HTTP 项目接口、CLI 命令、浏览器用户操作和导出产物视为待确认的公共 seam。不要因已有大量测试就继续按文件补测试；先判断哪些测试真正描述用户能力，哪些会因内部重排而破裂。

### 5. `diagnosing-bugs`：只在有具体缺陷或性能回归时启用

完整流程不可直接跳到读代码猜原因：

1. 先构造快速、确定、无人值守、能准确捕获用户症状的 red-capable 命令。
2. 重现并把输入、配置和步骤逐项删到最小。
3. 写出 3–5 个按概率排序且可证伪的假设，并说明每个预测。
4. 一次只验证一个变量；调试日志加唯一 `[DEBUG-...]` 前缀，性能问题先测基线再分析。
5. 在正确 seam 上先写失败回归测试，再修复，并重跑原始场景；若没有正确 seam，要把架构缺口明确记录。
6. 清理全部调试插桩和临时 harness，并在提交信息中记录最终原因。

无法构造反馈循环时必须停止猜测，列出已尝试方法并请求可复现环境或脱敏工件。来源：[diagnosing-bugs/SKILL.md](https://github.com/mattpocock/skills/blob/c55ee46073ed923f86ce59a5eb3b6d895095d1b7/skills/engineering/diagnosing-bugs/SKILL.md)。

### 6. `code-review`：用于迭代完成后的差异审查

必须先固定基线并验证可解析、差异非空，使用 `git diff <fixed-point>...HEAD` 和 `git log <fixed-point>..HEAD --oneline`。然后分别找到 Spec 来源和仓库 Standards 来源；Standards 轴还要应用技能内置的 Fowler smell baseline。两个轴必须由相互独立的并行审查者执行，最终按 `Standards` / `Spec` 分开呈现，不能合并排序。来源：[code-review/SKILL.md](https://github.com/mattpocock/skills/blob/c55ee46073ed923f86ce59a5eb3b6d895095d1b7/skills/engineering/code-review/SKILL.md)。

当前项目的限制：

- 没有 `docs/agents/issue-tracker.md`，因此该技能规定的 issue 自动追溯流程尚未配置；审查时需先补相应配置，或显式提供本地规格文件。
- [CONTRIBUTING.md](../../CONTRIBUTING.md) 是 Standards 来源，但其中仍引用 `fox/`、`tests/integration/`、`tests/security/` 和旧测试数量，与当前 `htmlninefox/` 和平铺测试结构不完全一致。开始 Standards 审查前，应先校正文档，否则“仓库标准优先”会把过期规范当成硬标准。
- 全仓现状没有天然 fixed point。完成下一轮明确增量后，可使用 `v0.5.0rc2` 或该增量的 merge-base 作为基线，并将对应迭代规格文件作为 Spec。

## 建议的迭代规划顺序

1. **语言审计**：用 `domain-modeling` 对照 `CONTEXT.md`、项目 API 和工作台交互，输出规范术语差异；只修改真正的领域词。
2. **模块深度审计**：用 `codebase-design` 为服务端项目生命周期和浏览器工作台两条主链绘制 Module / Interface / Seam / Adapter 清单，执行删除测试，选出 1–2 个高收益深化候选。
3. **修正文档基线**：更新 `CONTRIBUTING.md` 的真实包路径、测试结构和命令；若存在满足三项门槛的重大架构决定，再创建精简 ADR。
4. **接口方案比较**：对最高优先级候选运行 “Design It Twice”，明确依赖类别和测试 seam，选定一个接口方案。
5. **纵向交付**：功能增强使用 `tdd`；已有缺陷或性能问题使用 `diagnosing-bugs`。每次只交付一个可观察能力。
6. **双轴评审**：以固定提交或标签为基线运行 `code-review`，分别报告 Standards 与 Spec，再执行现有 Python、Node、浏览器和发布校验。

这套顺序能先修正项目语言和测试面，再决定是否重构，避免根据文件大小直接拆分，也避免为尚不存在的变化点添加抽象。
