# v0.9 迭代规划 · Agent 一等公民 + 交付层收尾

**制定日期**：2026-10-31
**性质**：版本规划。北极星见 [VISION.md](VISION.md)；输入矩阵已清零
（DOCX/PPTX/PDF ✅，图片=资产），v0.9 主战场：**agent 一等公民化 + 质量与卫生**。
**发布切分**：本期可交付内容以 **0.8.5（Agent 与卫生）** 先行小步发版；
**0.9.0 保留给 Tauri 壳里程碑**（机主已拍板：与 PyInstaller 并存）。

---

## 一、本批落地（0.8.5 · Agent 与卫生）

| 项 | 说明 | 状态 |
|---|---|---|
| **MCP 服务** | `htmlninefox/mcp_server.py`（`[mcp]` extra，mcp 2.x）：stdio 服务暴露 `intake_decompose`（规划原名）+ 生成/采纳/反馈/能力查询，内部复用 HTTP API（不另起服务，照 DESIGN-REVERSE-INTAKE 决策） | ✅ 0.8.5（门禁含 stdio 真 MCP 握手） |
| **模块更名清理** | `docx_proposal.py → intake_proposal.py`、`docx_adopt.py → intake_adopt.py`（v0.8.3 记录的纯 churn 项）：这两个模块自 v0.8.4 起服务全部四种格式，名字早就不诚实了。旧路径留兼容 shim | ✅ 0.8.5（shim 至 v0.10） |
| **impeccable B 档 · 反模式门禁** | 从其 62 条检测规则挑确定性子集自研实现进测试（思路参考 Apache-2.0，注明来源）：禁 bounce/elastic 缓动、禁卡片套卡片、禁纯黑 | ✅ 0.8.5（tests/test_anti_patterns.py） |
| **Agent 调用指南** | docs/AGENT-GUIDE.md 四通路实测手册 | ✅ 0.8.5 |

## 二、v0.9 后续（已圈范围，未动工）

1. **Tauri 桌面壳**（0.9.0 里程碑）：决策已定（并存 / Rust 进 CI）；验收沿用
   verify_portable 纪律（启动后真探测健康端点）
2. **模板 B/C 档**：画廊 18 张（六意图 × ≥3，覆盖矩阵门禁）→ 外部库 34 套
   （beautiful-html-templates，MIT）+ preset 扩族（huashu/impeccable 调性轴）
   + `scripts/check_upstream.py` 月度巡检
3. **读屏器审计**：键盘专项划走的另一半（role/aria 全面走查）
4. **impeccable C/D 路径**：C=preset 扩族灵感源；D=PRODUCT.md 式 durable-truth
   顺序吸收进 SKILL 指南
5. **间距 burn-down**：95 处基线，只禁变差
6. **下一北极星讨论**：输入缺口清零后，主战场转向**输出端**（多页站？模板生态？）

---

## 三、惯例承诺（沿用）

每功能配真链门禁 + 变异验证；可选依赖只提示不代装；新功能过 VISION 三问；
数字全部实测进文档。MCP 额外纪律：**工具返回规整数据 + limitations**，
HTTP 错误映射为带 code 的工具错误，agent 不用猜。
