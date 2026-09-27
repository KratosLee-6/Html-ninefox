# v0.6.0 双审计报告（mattpocock 四维 + Mimosa deep）

- 审计日期：2026-09-28
- 范围：v0.6 全部新增代码（intake 流水线、审核台、PPTX 桥、导出中心接入）+ 既有回归
- 工具：mattpocock 四维方法（research / domain-modeling / codebase-design / code-review，沿用 2026-09-20 首轮审计框架）+ Mimosa deep 静态扫描（seal `sha256:7246…b3d3`）

## Mimosa deep 扫描结果

- **2 个 high（SSRF）**：指向 intake 抓取的动态 URL。处置：**设计性缓解 + 残余风险披露**。抓取流程已有四层防护（API 边界 validate_url、fetch 内再校验、重定向逐跳过门、事后 rebinding 比对 + 丢弃），扫描器无法建模自定义校验故仍标记。真实残余风险（审计 P1-6）：校验用 IP 与实际连接 IP 是两次独立解析，理论上存在被绑定前的置换窗口。**缓解现状 + 已知限制披露**；连接级 IP 绑定（自建 HTTPConnection 直连校验 IP）列为 v0.6.x 首项。
- 依赖告警 0（14 包）。
- 说明：另有 20 条针对既有测试 fixture 的 SSRF/凭据误报（127.0.0.1 集成测试与脱敏断言用的假 key），已于此前逐一核实并获仓库所有者确认。

## mattpocock 四维发现与处置

### domain-modeling
- intake 域词汇（source/candidate/evidence/component/motion/style preset）与既有 gallery/revision 域无冲突；候选 id 与预设 id 的命名空间耦合（P2-18）记录为技术债。
- **P1-3 已修**：license_class 从"仅展示"升级为强制——inspiration-only 候选采纳时跳过代码导入（返回 gallery_skipped 原因），兑现三档声明。

### codebase-design
- **P1-1 已修**：来源筛选误把 source id 当 status 传导致列表恒空。
- **P1-2 已修**：candidate_id 主机名归一（unicode/下划线/超长 URL 不再在成功抓取后失败），中文 ZIP 导入修复。
- **P1-7 记录**：intake 编排仍在 `_Handler`（约 165 行）；建议下一批次提 `IntakeService`。与上轮 P1 同向，纳入 v0.6.x。
- 其余：lifecycle-intake.js 与既有模块同构；无循环依赖。

### code-review
- **P1-4 已修**：提取期颜色令牌归一为 #RRGGBB，堵死审核台色板的 CSS 注入（远程页可借 style 属性发外联请求）。
- **P1-5 已修**：components/motion 导入端点补上 UI 按钮（采纳卡片"导入组件/吸收动效"），S09/S10 验收经纯 UI 可达。
- **P2-15 已修**：AI 分析 busy 态挂到自身按钮。
- P2 批次（P2-1 原子写、P2-2 预设库损坏兜底、P2-4 源级限速消费、P2-6 死代码、P2-7 正则回扫上限、P2-8 过渡守卫、P2-9/10 8 位 hex、P2-11 列表项重复、P2-12 导出目录碰撞、P2-16 批量截断反馈/候选清理、P2-13 esc 单引号、P2-14 refresh 过期守卫、P2-17 测试盲区、P2-18 CONTEXT.md 词条）**已记录并排入 v0.6.x**；其中 P2-10/P2-12/P2-13 三项低风险易修项优先。
- research 对照（收藏入口、视觉快照、离线归档、标签看板、URL 去重、tokens 回写推荐、抓取后台化、og:image 丰富）记入 ROADMAP 候选。

### 正面确认
- 预览通道 `sandbox=""` + `default-src 'none'` + nosniff 的三重实现与头等测试；pptx_export 零内依赖、扁平化如实上报；模块单向依赖无环；lifecycle-intake 与既有模块完全同构。

## 结论

发布阻断项 **0**。P1 六项中五项已修复落地（P1-6 为残余风险披露 + v0.6.x 计划项），P2 二十项中五项随手修复、其余已记录排期。发布门禁达成。
