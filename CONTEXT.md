# Html九尾狐领域术语

- **Project**：围绕一个持续创作目标保存要求、Workspace、Artifact、Revision、反馈和运行证据的本地创作单元。
- **Workspace**：用户组织要求、风格、素材、Skill 与 Artifact 的视觉编排空间。
- **Canvas Node**：Workspace 中可定位、选择、组合和连接的创作单元。
- **Generation Request**：一次生成所需的 Explicit Requirement 与用户选定上下文。
- **Artifact**：用户可以查看、继续修改、导出或交付的创作结果。
- **Revision**：某个 Artifact 及其生成上下文的不可变历史快照。
- **Restore**：从历史 Revision 创建新的当前 Revision；不会回退或覆盖已有历史。
- **Feedback Iteration**：针对现有 Artifact 提交自然语言修改要求并产生新 Revision 的一次迭代。
- **Export**：把 Artifact 转换为 PDF、PNG 等可交付格式，并记录兼容性或降级信息的操作。
- **Recipe Run**：一次可追踪、可恢复的创作执行，由分析、组合、生成、验证和交付阶段组成。
- **Project Memory**：用户明确采用 Artifact 后形成的长期偏好与项目知识。
- **Adoption Signal**：用户确认某个 Artifact 值得后续复用的明确行为。
- **Memory Recommendation**：一次 Generation Request 中从 Project Memory 匹配出的建议及其解释。
- **Explicit Requirement**：本次需求中用户明确提出的约束，优先级始终高于 Project Memory。

## 需要避免的混用

- 不把 Project 与 Artifact 混用：Project 是持续创作单元，Artifact 是其中一次可交付结果。
- 不把 Restore 称为“回滚覆盖”：Restore 会创建新 Revision，并保留被恢复版本之后的历史。
- 不把 Workspace 与 Project 混用：Workspace 是 Project 内的视觉编排空间。
- 不把 Recipe Run 与 Revision 混用：Recipe Run 描述执行过程，Revision 描述保存下来的历史结果。
- 不把预览、HTML 文件或导出包分别当成独立领域结果；它们是 Artifact 的呈现或交付形式。
