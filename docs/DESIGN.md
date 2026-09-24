# Design Philosophy · 产品与交互设计原则

> 当前设计基线：Pixel Garden v1.1 · 校验日期：2026-09-24
> 应用发布基线：`v0.5.0rc2`；本文件同时描述其后的 RC3 `main` 视觉基础切片。

Html九尾狐面向需要交付真实 HTML 的创作者。它把需求、文件、图片、模板与 Skill 放进一个可观察的工作空间，让用户能看到推荐依据、控制组合方式、检查生成结果、继续反馈修改，并保留每次 Revision。

## 1. 要解决的问题

纯 AI 生成器速度快，但生成上下文、选择依据和历史变化常常不透明。纯模板系统稳定，却难以根据具体内容和目标调整。Html九尾狐在两者之间建立一条可控的产品链路：用真实模板和明确约束保证可预期性，用可选 AI 或离线规则完成分析与生成，用 Workspace、Revision 和 Project Memory 保留用户控制权与长期积累。

产品的核心价值不是“生成一次页面”，而是让同一个 Project 可以持续完成：

```text
Explicit Requirement
        ↓
Workspace 组合（内容 / 模板 / 文件 / Skill）
        ↓
分析与 Generation Request
        ↓
Artifact + Revision + Recipe Run
        ↓
预览 / Feedback Iteration / Restore
        ↓
Export 与交付
        ↓
用户明确采用后写入 Project Memory
```

领域术语以仓库根目录的 [CONTEXT.md](../CONTEXT.md) 为准。

## 2. 产品设计原则

### 2.1 先展示真实 HTML

模板卡片、生成结果和历史版本尽量呈现真实 HTML 预览。用户不应仅凭模板名称、抽象线框或营销描述猜测最终结果。

### 2.2 组合过程由用户控制

系统可以推荐内容类型、模板、页面配方和历史偏好，但用户可以接受推荐，也可以在 Workspace 中重新组合节点。Explicit Requirement 始终高于 Project Memory，自动推荐必须说明来源与覆盖关系。

### 2.3 本地优先且可解释

项目、Artifact、Revision 和 Memory 默认保存在本地。API Key 不进入项目文件；离线规则在没有模型配置时仍能工作。分析、生成、反馈、恢复和导出需要呈现状态、失败原因和可诊断信息。

### 2.4 历史只追加，不静默覆盖

每次生成与反馈产生新的 Revision。Restore 从旧 Revision 创建一个新的当前 Revision，保留恢复点之后的历史。用户看到的是可追踪的演进链，而不是被覆盖的单一文件。

### 2.5 动效服务于状态理解

动效用于连接建立、节点选择、任务进行、结果出现和恢复完成等反馈。它必须可取消，不能成为业务成功条件，并遵守系统、减少、关闭三档偏好。当前产品保持原生 CSS/WAAPI 路线；只有真实时间线编排出现明确收益并通过离线、性能和无障碍门禁时，才评估新增运行时依赖。

### 2.6 跨尺寸保持任务可完成

桌面显示完整三栏工作台；中等宽度将检查器或素材区变为抽屉；手机使用可阅读的任务视图呈现 Workspace 与节点，而不是缩小整张无限画布。语义缩放在概览、紧凑和详情层级逐步增加信息密度。

### 2.7 无障碍属于组件契约

按钮、输入框、节点、弹窗、检查器和命令面板必须具备清晰的 focus、selected、disabled、busy、success 与 error 状态。键盘路径、状态播报、对比度和 reduced-motion 与视觉样式同时验收。

## 3. Pixel Garden 视觉方向

Pixel Garden 以暖纸白、花园钴蓝、嫩芽薄荷和陶土橙构成统一品牌。像素细节负责识别，编辑感排版与清晰边界负责长时间使用。品牌不使用与项目无关的渐变、霓虹或示例配色，也不把工具界面做成装饰性的游戏面板。

视觉层级遵循：

1. 当前任务和主要操作最醒目。
2. Workspace 与 Artifact 承担主要内容空间。
3. 检查器、Project Memory、Export Center 和历史记录按需展开。
4. 状态颜色只表达选择、成功、提醒或错误，不作为大面积装饰。
5. Icon 使用仓库内 SVG，并共享尺寸、描边和可访问名称规则。

品牌色、Logo、安全区和字体规则见 [VI 手册](VI.md)，组件、布局、状态与响应式规则见 [UI 指南](UI-GUIDE.md)。

## 4. 真实产品闭环

| 阶段 | 用户应看见什么 | 系统必须保留什么 |
|---|---|---|
| 输入 | 明确需求、附件和限制 | Explicit Requirement |
| 分析 | 推荐类型、模板、Memory 命中与覆盖解释 | Generation Request 与分析证据 |
| 组合 | 可编辑节点、连线、Workspace 与检查器 | Canvas schema 与用户选择 |
| 生成 | 进行状态、可取消反馈和真实 HTML | Artifact、Revision、Recipe Run |
| 反馈 | 修改要求、差异和新结果 | 新 Revision，不覆盖旧历史 |
| 恢复 | 目标版本、血缘和完成状态 | 新的 Restore Revision |
| 导出 | 格式、分页、兼容性和失败原因 | 交付文件与 export report |
| 采用 | 用户明确确认值得复用 | Adoption Signal 与 Project Memory |

## 5. 当前实现边界与后续方向

2026-09-24 的 RC3 视觉基础切片已完成主操作层级、四档响应式布局、语义缩放、本地 SVG Icon、组件状态、两套主题与 14 张真实截图。下一阶段优先建立共享 Generation use case、稳定 request/result、durable Project commit 和浏览器业务 Module；视觉工作围绕这些真实生命周期补充状态，而不是脱离产品流程继续堆叠特效。

相关资料：

- [当前架构](ARCHITECTURE.md)
- [产品路线](ROADMAP.md)
- [RC3 架构加固计划](ITERATION-PLAN-POST-RC2-20260920.md)
- [RC3 视觉收敛记录](ITERATION-RC3-VISUAL-CONVERGENCE-20260924.md)
- [截图与验收证据](../assets/screenshots/README.md)
