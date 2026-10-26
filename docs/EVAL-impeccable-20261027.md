# 评估：pbakaus/impeccable（88.7k★）对 Html九尾狐 的价值

**日期**：2026-10-27
**触发**：机主提议参考该项目提升设计能力
**性质**：评估文档，不占版本号；触发条件满足才升级立项

---

## 一、它是什么（2026-10-27 GitHub 实测）

| 项 | 实测 |
|---|---|
| 定位 | "让 AI harness 更懂设计的语言"——给 AI 编码 agent 的**设计指导层** |
| 数据 | **88,733 ★** · Apache-2.0 · **当日仍有推送**（活跃头部项目） |
| 组成 | 1 个 skill + **24 个命令** + **62 条确定性检测器规则** + 浏览器实机迭代 |
| 安装 | `npx impeccable install`（自包含二进制，无运行时依赖）；支持 claude/cursor/codex/hermes 等 15+ harness |
| 来源 | 源自 Anthropic frontend-design skill 的演进 |

**24 个命令**按工作流分层：`craft`（全流程）→ `init`（写 PRODUCT.md 产品真相）→
`critique/audit`（评审与技术审计）→ `polish/bolder/quieter/distill`（打磨调性）→
`animate/colorize/typeset/layout`（专项）→ `harden/onboard/clarify`（工程细节）→
`live/generate`（浏览器实机变体）。

**反模式清单**（它对"AI 味设计"的诊断）：Inter 滥用、紫蓝渐变、卡片套卡片、
彩底灰字、纯黑纯灰、圆角方块图标盖在每个标题上、bounce/elastic 缓动。

---

## 二、与 Html九尾狐 的关系：正交互补，不冲突

| | impeccable | Html九尾狐 |
|---|---|---|
| 层次 | **质量层**：指导 AI agent 在已有代码上做出好设计 | **交付层**：从需求/文档生成可交付网页并管理版本迭代 |
| 输入 | 已有的前端项目 | 一句话 / DOCX / PPTX / URL |
| 输出 | 改进建议 + 62 规则检测结果 + 浏览器内迭代 | 单文件 HTML + 版本历史 + 五格式导出 |
| 形态 | skill + CLI 检测器 | 服务 + 工作台 + 生成器 |

**互补结论**：impeccable 管"好不好看、对不对"，Html九尾狐 管"从哪来、到哪去"。
两者天然是上下游。

---

## 三、三条可落地的路径（按成本排序）

### A 档 · 联盟接入（最低成本，≈半天）

把 impeccable 注册为 Html九尾狐 **联盟成员**：`data/alliance/impeccable.yaml`
（Apache-2.0 可安全引入），接管 `critique`/`audit` 环节——用户在审核台生成的
产物可一键请 impeccable 做 62 规则体检。未安装自动本地兜底（联盟纪律不变）。

### B 档 · 反模式门禁（中成本，≈1 天）

从它的 **62 条确定性检测器**里挑出与设计契约不重叠的条目（如"卡片套卡片"
"彩底灰字""圆角方块图标"），改写进 `tests/test_design_contract.py` 的规则域
（规则思想参考 + **自研实现**，Apache-2.0 保留来源声明）——让"AI 味设计"
在发版前被机器拦下，与 v0.8.2「间距 burn-down」同一手法。

### C 档 · preset 扩族的灵感源（v0.9，呼应 PLAN-TEMPLATE-EXPANSION C 档）

huashu-design 的 84 风格样张已在 C 档排队；impeccable 的调性轴
（bolder/quieter/distill）可作为 11 个 preset 向 18–20 个扩族时的**分层依据**
（编辑 / 技术 / 柔和 / 高对比 → 加"更收敛/更大胆"两轴）。

### D 档 · 流程借鉴（零成本，写进 SKILL 指南）

`init → PRODUCT.md` 的做法（先把"受众/用途/约束/语气"固化成 durable truth，
再谈视觉）与 Html九尾狐 的 Project Memory 同构——SKILL.md 的用户指引可借鉴
此顺序：先问材料真相，再出提案。

---

## 四、建议

**A 档立即做**（联盟门槛低、互相导流价值高：88.7k★ 的项目社区正是
"AI + 设计"的精准受众）；**B 档随 v0.8.4/v0.9 择机**；**C 档并入
PLAN-TEMPLATE-EXPANSION C 档**；**D 档下次 SKILL 文档修订时吸收**。

合规注意：Apache-2.0 允许引入但需保留版权与许可声明；联盟 yaml 的
`origin/license/upstream_*` 字段照 2026-10-18 巡检纪律填写。

---

## 五、决定记录

- 2026-10-27 机主提出参考此项目 → 本评估完成，四路径待机主勾选。
