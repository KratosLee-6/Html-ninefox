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

## 一·五、0.8.7 批次（进行中：动效质量层 + 所见即所得 A1）

| 项 | 说明 | 状态 |
|---|---|---|
| **motion-design-skill 接入** | LottieFiles 联盟新成员（guidance-source 知识型，`detect_paths` 探测技能目录落位）+ 动效质量门禁 5 条（时长表对齐 / linear 禁令 spinner 白名单 / 非 opacity-only / stagger<500ms / 循环缓动律；三连变异全 CAUGHT）。评估见 docs/EVAL-motion-design-skill-20261101.md | ✅ 本批 |
| **所见即所得 A1** | 文本级点选即改（复用幻灯片原位编辑机制 apply_text_edits，≈2 天） | 本批主线 |

## 二·五、0.8.6 快赢包（2026-10-31 机主四选全后插入排期）

| 项 | 说明 | 状态 |
|---|---|---|
| **手机预览二维码** | 工作台「发到手机」：枚举局域网地址（stdlib UDP 探测）→ 可选 `[qr]` extra（segno 纯 Python）渲染 SVG 二维码 → 无 segno 降级为地址文本；安全提示沿用（无鉴权仅限可信局域网） | ✅ 本批 |
| **一键交付包** | 导出中心「交付包」：按意图自动组包（doc/archdoc=HTML+PDF+DOCX · deck=HTML+PDF+PPTX · 其余意图=HTML+PDF）打 zip + 清单 | ✅ 本批 |

## 二·六、0.9.0 切分（2026-11-03 · 体验升级主线定稿）

**叙事**：从「网页工具」到「桌面创作应用」——0.8.x 把能力做厚（反拆/agent/
动效质检/点选即改），0.9.x 把体验做顺。

| 批次 | 内容 | 体验升级 |
|---|---|---|
| **0.9.0** | **Tauri 桌面壳**：✅ 编译+CI 三平台绿（7abe9a7→ec3f9ff）；✅ 打包接线 packaging/shell/build_shell_bundle.py（onedir→sidecar→NSIS）+ scripts/verify_shell.py 验收（静态半场全 PASS）；⏳ 发布前人工清单（双击→托盘→关窗回收） | 桌面原生形态 |
| **0.9.5** | **OKLCH 品牌色约束 + 交付包字体子集化 + 联盟小批**（2026-11-12 落地，guizang-design 融合收尾）：①`generators/_oklch.py`——sRGB↔OKLCH 纯 Python 标准转换（往返 ±1/通道）+ WCAG 对比度；品牌色两入口（feedback `primary_override` / style_expert LLM 微调）**不再直接用原色**：收进锚点（preset 原色反推，11 家零数据变更）±0.10 明度 ×1.25 彩度域，色相保留（±8° gamut 容差），primary 对 primary_text ≥4.5:1、accent 对 bg ≥3:1，不足沿明度轴步进；`_brand_constraint` 理由随 token/style_decision 全程可见；②`fontsubset.py`——交付包**副本**按产物实际用字子集化内嵌（woff data-URI + font 栈前插，工作区原件永不动），`[font]` extra（fonttools+brotli，dev 同步），无 extra/无缓存照旧导出报告照实说，`python -m htmlninefox.fontsubset fetch/list`（OFL Noto 源，字体文件不进 git）；③联盟 manifest `dsh-guizang-design`（guidance-source，AGPL 红线交底）。stub `style_refine` 键控荧光色 = 约束链确定性输入；直通变异 CAUGHT | 品牌色不放飞；交付包离线不裸奔 |
| **0.9.4 后半** | **剧本入口 + 生成链记录**（2026-11-10 落地）：创建面板「工作流剧本」选择器（懒加载六条 + 描述展示）→ analyze/generate 请求带 workflow（`_validated_workflow` 400 workflow_invalid，与 tone 同一教训：server 内禁相对导入）→ pipeline compose 段记录剧本 → recipe-run 时间线可查；端到端门禁（one-article-three-outputs 进 recipe-run + 未知剧本 400）| 剧本从数据变成可点入口，多步玩法留痕 |
| **0.9.4 第一批** | **家族标签 + 工作流剧本**（2026-11-10 落地）：preset 11 家与画廊 10 张全体带 family（guizang/fox/shadcn/vercel…8 家族，未登记落 independent 不猜）+ 未知预设校验；`workflow_presets.py` 六条剧本（一文三出口/旧文档翻新/演讲回收/品牌套件/口语迭代/一键交付，每步引用 ability 而非实现）+ GET `/api/workflows(+/id)` 真链；schema 门禁（ability 白名单/说明完整/id 唯一）+ 变异 CAUGHT；家族两侧覆盖门禁（guizang/fox 同时落 preset 与模板）| 拼装层的语义地基：三出口一家人 + 剧本即路线图 |
| **0.9.3** | **语气档案**（2026-11-09 落地，融合 guizang-design 语气档案思路）：`voice_profile.py`（独立存储 .settings/voice-profile.json）——六类特征（常用词/禁词/句长节奏/开头/结尾/称呼）+ **≥2 处证据纪律**（滑窗 n-gram 跨样本计数，句子级证据；首跑实锤按文本取证据三撞一被误杀）；learn/edit/remove/clear 全套 API + 记忆面板「从素材学习语气」区；copy_expert 消费端（禁词叠加 + 档案摘要进 prompt 保留用户说法）| AI 保留你的口吻；无密钥档案仍当门禁 |
| **0.9.2** | **AI 生成深化**（2026-11-07 落地）：`copy_expert` 两个职责——compose 推荐 LLM 化（11 家预设挑一个 + 中文理由，preset_id 校验不过/无 AI = 规则结果照旧，记忆模板 > LLM > 规则）+ 槽位文案润色（**数字串双向一致**门禁：不许丢也不许发明；禁词/超长丢弃；宁缺勿错）+ `HTMLNINEFOX_LLM_STUB` env 门控测试接缝 + `/api/polish-slots`（无 AI 照实说 available=false）+ 推荐卡「✨ 文案润色」逐槽 diff 采纳（勾选+可改文本）→ content 通道（人审文案同一条 `_apply_caller_copy`）→ 产物印人采纳的文案（端到端闭环门禁） | LLM 只是建议，人握每一句 |
| **0.9.1 后半** | **调性选择器 + 配方时间线**（2026-11-07 落地）：创建面板调性选择（自动/6 词表，400 tone_invalid 校验）→ analyze/generate 全链贯通（pipeline 在 style_expert 前注入 brief，模板分支附 motion 参数）→ 端到端门禁（vibrant→0.6s/14s · editorial→0.9s/32s 进产物；无 tone 回归护栏）+ **配方时间线 AI 徽章**（recipe-run 端点 + recipeRunMarkup 每段 🤖 模型 / 📐 规则兜底 + file 节点 fetch 版时间线） | 调性可控可证；「哪段用了 AI」不再靠猜 |
| **0.9.1** | **风格轴第一批**（2026-11-03 落地）：MOTION_ARCHETYPES 四原型→动效参数三轴（ink/stagger/ambient，全在 0.8.7 门禁内；reveal .6s 固定锚点）+ 6×4 覆盖矩阵门禁（变异 CAUGHT）+ 画廊 manifest tone 标签 + match_preset 中文推荐理由 + analyze 载荷带 motion/reason + 推荐卡原型徽章；test_style_axis 7 门禁 | 生成时选调性，产物气质可控；理由永远可见 |
| 0.9.x | **AI × 风格模板总纲**（[EVAL-AI-STYLE-DEEPEN-20261103.md](EVAL-AI-STYLE-DEEPEN-20261103.md)）：0.9.1 风格轴+配方时间线 → 0.9.2 AI 生成深化（compose 推荐+槽位润色）→ 0.9.3 拆分语义增强+演示模式 → 0.9.4 拼装层 → 0.9.5 模板 B/C 档；A2 样式级编辑并入其中排期 | 六环节（推/拆/生/组/装/演）AI 全链路 + 调性矩阵 |
| 0.9.x | **风格轴**：动效人格四原型（Playful/Premium/Corporate/Energetic）+ preset 扩族进生成端 | 生成时选调性，产物气质可控 |
| 0.9.x | 模板市场 UI（B/C 档：画廊 18 张 + 外部库 34 套，分类/搜索/采用） | 选择像逛商店 |
| v1.0 | E 多页站点 + impeccable D | 输出端正主 |

## 二·七、融合评估：dsh-guizang-design（2026-11-09）

**评估档**：[EVAL-guizang-design-20261109.md](EVAL-guizang-design-20261109.md)。
同作者（歸藏）的 dsh 插件 = guizang-ppt 的设计系统统一 + 工程化封装。核心可吸收
点：**语气档案**（≥2 证据/条，喂 copy_expert 润色与去 AI 味）、**家族标签**
（preset/模板三形态一家的语义，拼装层前提）、**OKLCH 品牌色约束**（进风格
明度/彩度范围）、**六条工作流剧本**（一文三出口/演讲回收/品牌套件 → 拼装层
第一批直接参考）、字体子集化导出。**AGPL 红线**：只学思路与事实层，不复制
代码/主题 CSS/文案；humanizer-zh（MIT）可参考实现。切分：联盟 manifest（小 ✅）
→ 0.9.3 语气档案 ✅ → 0.9.4 家族+工作流 ✅ → 0.9.5 OKLCH+字体子集 ✅（2026-11-12 全落地）。

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

## 二·五、0.9.0 前置核查（2026-10-31 实测 · 全部就绪）

| 前置项 | 实测结果 | 判定 |
|---|---|---|
| Rust 工具链 | rustc/cargo **1.98.1**（.cargo/bin 在 PATH） | ✅ |
| Tauri CLI | **tauri-cli 2.12.0**（cargo tauri 可用） | ✅ |
| WebView2 | 156.0.4314（Win11 预装，webview 运行时） | ✅ |
| Node | v24.15.0（仅 npx 安装器用；壳构建走 cargo tauri） | ✅ |
| Sidecar 二进制 | **复用现有 PyInstaller 产物**——HtmlNineFox.exe 本身就是 server+启动器（`--port/--no-browser/--strict-port`），无需新建打包变体 | ✅ 策略定 |
| 图标 | packaging/windows/htmlninefox.ico 在位（Tauri 需转多尺寸 ico/png） | ✅ 源在 |
| CI Rust 位 | ⬜ src-tauri 落地后加 job（dtolnay/rust-toolchain + tauri build 编译验证，先 Windows） | 待壳动工 |
| OSS 0.8.4/0.8.5 | ⬜ **仍未上传**（HEAD 404）——发版帖置顶评论依赖 | 机主动作 |

**Sidecar 架构决策（记录）**：Tauri 壳 = 窗口 + webview（加载 127.0.0.1:端口）+
sidecar（复用 PyInstaller onedir 产物的 HtmlNineFox.exe，`--no-browser
--strict-port --port <空闲>`）+ 托盘。Rust 主程序职责：spawn sidecar →
轮询 /api/health 直到 200（verify_portable 纪律）→ 导航 webview → 退出时回收子进程。
**并存承诺**：PyInstaller 便携包与安装包照发，Tauri 是增量形态不是替代。

### 0.9.0 动工顺序（前置已清，随时可开工）

1. `cargo tauri init` 脚手架（src-tauri/，窗口标题/图标指向现有 ico）
2. Rust 主程序：sidecar spawn + 健康轮询 + 托盘 + 端口冲突处理（strict-port 失败换端口重试）
3. tauri.conf.json：externalBin/resources 指向 PyInstaller onedir 产物布局
4. CI：Rust job（Windows 先行）+ 构建流水线加 Tauri 安装包产物
5. 验收：verify_portable 式脚本——装完/启动后真探测 /api/health 与版本号
6. 发版 0.9.0（RELEASE-NOTES/版本同步/tag；OSS 补 0.8.4/0.8.5/0.9.0 三版）

---

## 三、惯例承诺（沿用）

每功能配真链门禁 + 变异验证；可选依赖只提示不代装；新功能过 VISION 三问；
数字全部实测进文档。MCP 额外纪律：**工具返回规整数据 + limitations**，
HTTP 错误映射为带 code 的工具错误，agent 不用猜。
