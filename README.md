<div align="center">
  <img src="htmlninefox/server/static/logo-horizontal.svg" width="430" alt="Html九尾狐 Pixel Garden Logo">
  <h1>Html九尾狐 · HTML 创作工作台</h1>
  <p><strong>把文字、文件、图片和散落的 HTML 模板放进一张无限画布，经过分析、推荐、自由组合与反馈迭代，生成真正可交付的单文件 HTML。</strong></p>
  <p>个人开源项目 by <a href="https://github.com/KratosLee-6">KratosLee</a> · 默认中文 · 离线规则引擎可用 · AI 可选增强</p>
  <p><strong>简体中文</strong> · <a href="README.en.md">English</a></p>
</div>

<div align="center">

[![App Release](https://img.shields.io/badge/app-v0.7.0-173C8F)](https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.7.0)
[![DSH Plugin](https://img.shields.io/badge/DSH_plugin-0.1.0--preview.1-49B894)](https://github.com/KratosLee-6/Html-ninefox/releases/tag/dsh-htmlninefox-v0.1.0-preview.1)
[![Build Packages](https://github.com/KratosLee-6/Html-ninefox/actions/workflows/build-release-packages.yml/badge.svg)](https://github.com/KratosLee-6/Html-ninefox/actions/workflows/build-release-packages.yml)
[![Test CI](https://github.com/KratosLee-6/Html-ninefox/actions/workflows/test.yml/badge.svg)](https://github.com/KratosLee-6/Html-ninefox/actions/workflows/test.yml)
[![Tests](https://img.shields.io/badge/pytest-596%20passed%20%7C%202%20skipped-1F8A70)](docs/RELEASE-NOTES-v0.7.0.md)
[![Chromium E2E](https://img.shields.io/badge/Chromium%20E2E-22%2F22-173C8F)](docs/RELEASE-NOTES-v0.7.0.md)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB)](pyproject.toml)
[![License](https://img.shields.io/badge/License-MIT-D9A441)](LICENSE)

</div>

![Html九尾狐 Pixel Garden 工作台（v0.7.0 实拍）](assets/screenshots/v0.7.0/workbench-overview.png)

## 73 秒看完 v0.7.0 怎么把一个网页变成素材

[![播放 67s 网页反向拆解真实演示（中文版）](assets/promo/poster-demo-v070.png)](https://raw.githubusercontent.com/KratosLee-6/Html-ninefox/main/assets/promo/htmlninefox-demo-v070-16x9.mp4)

**真实链路**：贴入 `example.com`（Google Fonts 源 · 开放许可）→ 抓回来落审核台 → 采纳为模板 → 拆成分区并生成 → **页面自己的正文出现在生成的落地页里** → 回到工作台，它在侧栏 REAL HTML 模板库里。全程真实操作录屏，由 [`scripts/record_demo_film_v070.py`](scripts/record_demo_film_v070.py) 驱动 v0.7.0 真实运行服务录下；验收链路可自己重跑：[`scripts/verify_page_blocks_chain.py`](scripts/verify_page_blocks_chain.py)。开头 5 秒亮出品牌 Logo，结尾 5 秒收束到项目一句话与 GitHub 地址。

> **这不是动画，是录屏**：光标真的移动、网址真的一个个被敲进去、候选真的落进审核台、成品真的被滚动浏览。字幕条上的每句话对应录制时真实发生的事件（`events.json` 时间轴）。
>
> 由 MiniMax-H3 生成的只有**片头/片尾的抽象氛围底版**（暖纸、方格、钴蓝与薄荷光），提示词明令画面不含任何文字；Logo 与全部文字由官方 SVG 渲染后确定性叠加。界面演示**刻意不用**文生视频模型：模型会把中文渲染成乱码、按钮位置随机、连线毫无逻辑，那样的画面恰好与「可正常演示」相反。底版生成脚本：[`scripts/generate_h3_clips_v070.py`](scripts/generate_h3_clips_v070.py)（提示词内置，提供 API key 即可重生成；当前版本片头使用既有 H3 底版、片尾为暖纸静帧，新底版放入后重跑合成脚本自动替换）。

### 它演示的完整主线

| 时间 | 真实发生的事 |
|---|---|
| 0–5s | 品牌开场：H3 氛围底版 + 像素狐 Logo 与品牌句 |
| 5–15s | 「⋯」菜单 → 设计吸收，逐字贴入 `example.com`，选 Google Fonts 源（开放许可） |
| 15–26s | 真实抓取 → 候选「Example Domain」落审核台，带许可标签 |
| 26–36s | 采纳为模板 → 拆成分区并生成（真实 API） |
| 36–58s | 打开成品，滚过页面自己的正文；六类内容都能吃这份分块 |
| 58–68s | 回到工作台：Example Domain 已在侧栏 REAL HTML 模板库 |
| 68–73s | 品牌收尾：Logo + 项目一句话 + GitHub 地址 |

历史宣传片（v0.6.0 输入到导出全流程，50s 中英双语与 34s 静帧版）保留在 [assets/promo](assets/promo)。

## 它解决什么问题

很多 HTML、设计模板、参考文件和 AI Skill 散落在不同目录里。传统生成工具又常常只给出模板名字或线框，让人必须“猜”最终效果。

Html九尾狐把创作路径收束成一条可视化流程：

```text
文字 / 文件 / 图片 / HTML
          ↓
      AI 或离线规则分析
          ↓
  推荐内容类型 + 真实模板 + 页面组合
          ↓
A. 采用推荐直接生成
B. 进入无限画布，自定义组合版式 / 内容 / 风格 / 文件 / Skill
          ↓
      生成单文件 HTML
          ↓
  导出 PDF / 逐页 PNG / 长图 + 兼容性报告
          ↓
  用自然语言反馈，按版本继续迭代
```

## 当前版本与最新进展（v0.7.0 已发布）

当前应用包版本为 `0.7.0`，发布标签 `v0.7.0`。**v0.7.0 是里程碑版本：网页反向拆解——
把一个真实网页的分区，变成一个结构可编辑的项目。** 之前只能「用一段描述生成一个页面」；
现在可以把一个已存在页面的分区结构带进来，正文按许可决定带不带：

- **全链路打通**：`POST /api/intake/page-blocks` 把已采纳候选的分区重新切成生成通道
  认识的分块，**六个内容类型全部消费**（v0.6.4 只有 doc 一个——其余五个静默丢弃页面
  内容，landing 甚至渲染空白页）。端点**只读不写回**：携带页面正文必须由用户决定，
  不能成为一次抓取的副作用。
- **版权按字段判断**：`open` 许可才随行正文（verbatim），`reference` /
  `inspiration-only` 只带结构与顺序（structure_only，产物回落自带文案）。
  分块路径与整页进模板库的批准路径问**同一个规则函数**——本版同时修掉了一个
  既存矛盾：`reference` 许可曾一边被判「只给结构不给正文」，一边整页 HTML 被原样
  复制进模板库。
- **发布前实测翻出并修复三个「全绿但坏了」**（真实数据才看得见）：
  ① 生产形态的抓取**每次成功都在成功的瞬间崩**（`resolver=None` 进了重绑定检查，
  自 v0.6 抓取地基起随 v0.6.2 / v0.6.3 / v0.6.4 三次发布出门——所有测试都显式注入
  resolver，所以全绿）；② 真实端点产出的分块 heading == content，**每段正文在
  六个 intent 里渲染两遍**（「恰好一次」门禁的夹具 heading ≠ content，看不见自己
  端点的形状）；③ section 直接嵌套 section 仍被吞成一个摘要（非贪婪正则在内层
  闭合处截断，已修的只是「main 里放平级 section」一种形状）。三处各配
  「去掉修复必须变红」的门禁与变异。

> v0.6.2 的设计吸收抓取是坏的，**请跳过 v0.6.2**。
> v0.6.1（幻灯片编辑器竞态修复 + 真实操作录屏）、v0.6.0（设计吸收 + 可编辑 PPTX
> 两条主线）与 v0.6.3 / v0.6.4（门禁收口）的内容不受影响，
> 内容见各自的[发布说明](docs/RELEASE-NOTES-v0.6.0.md)。
> **建议从 v0.6.1 / v0.6.3 / v0.6.4 直接升级到 v0.7.0**。

| 轨道 | 当前状态 | 查看 |
|---|---|---|
| 应用 Release | `v0.7.0` 已发布（2026-10-07） | [发布页](https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.7.0) · [上一版 v0.6.4](https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.6.4) |
| 发布验证 | 全量测试 Windows 本地 `596 passed, 2 skipped`（Linux CI `597 passed, 1 skipped`）；**16 个变异脚本全部捕获**；真实链路实测 `15/15`；发布物字节级回读 | [v0.7.0 发布说明](docs/RELEASE-NOTES-v0.7.0.md) · [v0.7 设计文档](docs/DESIGN-v0.7-page-decomposition.md) |
| DeepSeek Harness 插件 | `0.1.0-preview.1`，独立于应用版本 | [插件预览版](https://github.com/KratosLee-6/Html-ninefox/releases/tag/dsh-htmlninefox-v0.1.0-preview.1) |


### 功能 ↔ 截图对照

#### 工作台与画布（v0.7.0 实拍，6 张）

以下 6 张拍摄自 `v0.7.0` 当前代码；1440 宽的桌面截图顶栏版本徽标为 `v0.7.0`：

<table>
<tr>
<td width="50%"><img src="assets/screenshots/v0.7.0/workbench-paper-1440.png" alt="Pixel Paper 桌面工作台"><br><b>Pixel Paper 桌面工作台</b><br>三栏层级：素材库 · 无限画布工作区 · 检查器。</td>
<td width="50%"><img src="assets/screenshots/v0.7.0/workbench-night-1440.png" alt="夜蓝主题桌面工作台"><br><b>夜蓝主题桌面工作台</b><br>同一组件层级的完整暗色主题；主按钮与弱化文字均已提到 WCAG AA 以上。</td>
</tr>
<tr>
<td width="50%"><img src="assets/screenshots/v0.7.0/workbench-overview.png" alt="多工作区管理"><br><b>多工作区管理</b><br>新建第二个工作区后的真实状态：导航卡并存、按真实几何参与画布避让，检查器直接改名与配色。</td>
<td width="50%"><img src="assets/screenshots/v0.7.0/workbench-tablet-768.png" alt="平板 768 布局"><br><b>平板 768 布局</b><br>侧栏折叠为顶栏抽屉，画布语义缩放。</td>
</tr>
<tr>
<td width="50%"><img src="assets/screenshots/v0.7.0/workbench-mobile-390.png" alt="移动任务视图"><br><b>移动任务视图</b><br>以工作区动作和节点卡片替代不可读的缩小画布；进度条只显示当前与失败步骤。</td>
<td width="50%"><img src="assets/screenshots/v0.7.0/sidebar-templates.png" alt="侧栏 REAL HTML 模板库"><br><b>侧栏 REAL HTML 模板库</b><br>模板名与描述上下堆叠、各夹 2 行，同屏比收敛前多露出一张卡。</td>
</tr>
</table>

#### 输入与检查器

<table>
<tr>
<td width="50%"><img src="assets/screenshots/v0.6.3/input-brief.png" alt="统一需求入口"><br><b>统一需求入口</b><br>文字、文件、图片走同一个入口，AI 分析后推荐组合。</td>
<td width="50%"><img src="assets/screenshots/v0.6.3/command-palette.png" alt="命令面板"><br><b>命令面板</b><br>Ctrl+K 键盘打开、输关键词直达，每个动作都带快捷键提示。</td>
</tr>
<tr>
<td width="50%"><img src="assets/screenshots/v0.6.3/node-inspector.png" alt="需求节点检查器"><br><b>需求节点检查器</b><br>选中即编辑文字与附件，一键向所属工作区推进。</td>
<td width="50%"><img src="assets/screenshots/v0.6.3/output-inspector.png" alt="产物节点检查器"><br><b>产物节点检查器</b><br>版本徽标、运行轨迹、采用学习、口语反馈与导出入口。</td>
</tr>
</table>

**Project Memory、命令与版本**

<table>
<tr>
<td width="50%"><img src="assets/screenshots/v0.6.3/project-memory.png" alt="项目记忆"><br><b>项目记忆</b><br>品牌、受众、语气、禁忌、模板与长期说明本地保存，下次生成直接复用。</td>
<td width="50%"><img src="assets/screenshots/v0.6.3/revision-restore.png" alt="版本历史与恢复"><br><b>版本历史与恢复</b><br>反馈、重跑、恢复都保留快照；恢复生成新版本，历史不覆盖。</td>
</tr>
<tr>
<td width="50%"><img src="assets/screenshots/v0.6.3/generation-cancel.png" alt="取消生成"><br><b>取消生成</b><br>等待期可取消：排队任务真取消，执行中诚实转为“停止等待”。</td>
<td width="50%"><img src="assets/screenshots/v0.6.3/classic.png" alt="经典表单模式"><br><b>经典表单模式</b><br>一句话 Brief 直接生成，和工作台同一套品牌系统。</td>
</tr>
</table>

**导出中心（真实导出全流程）**

<table>
<tr>
<td width="50%"><img src="assets/screenshots/v0.6.3/export-ready.png" alt="导出分析就绪"><br><b>导出分析就绪</b><br>兼容性评分、分页模型、动态特性与本地引擎状态；deck 产物额外放开 PPTX。</td>
<td width="50%"><img src="assets/screenshots/v0.6.3/export-center-pptx.png" alt="PPTX 导出结果"><br><b>PPTX 导出结果</b><br>导出完成给出 pptx 与报告两个下载项，报告列出可编辑元素与降级清单。</td>
</tr>
</table>

#### 全部截图清单

| 目录 | 张数 | 内容 |
|---|---:|---|
| `assets/screenshots/v0.7.0/` | **11** | 当前版本实拍：工作台 6 张 + 网页反向拆解真实链路 5 张（审核台 / 采纳 / 分区进成品 / 文档成品 / 入库闭环） |
| `assets/screenshots/v0.6.3/` | **23** | v0.6.3 版实拍：工作台与画布 7 张、输入与检查器 4 张、Project Memory / 版本 / 取消 / 经典模式 4 张、设计吸收 3 张、幻灯片编辑与 PPTX 导出 3 张、移动端素材库 1 张 |
| `assets/screenshots/v0.5.0/` | 24 | v0.5.0 完整实拍集（含 6 张真实产物输出图） |
| `assets/screenshots/v0.4.0/` | 5 | Pixel Garden、LLM、Docker、Export Center 的历史记录 |

> v0.6.0 的 23 张全部由可复跑的门禁产出（`tests/test_v060_visual_evidence_states.py` 与
> `tests/test_v061_visual_evidence_states.py`），不是手工截图；清单与重采命令见[截图说明](assets/screenshots/README.md)。
> 仍引用 `v0.5.0/` 的只有**六类生成器产物**——它们由生成器实跑产出而非 UI 截图，产物结构在 v0.7.0 未变。

## v0.5.0 稳定版核心能力（历史）

![崩溃可恢复提交与生命周期 Module](assets/screenshots/v0.6.3/generation-cancel.png)

- **🧠 Project Memory**：品牌、受众、语气、禁忌、模板、主色和字体保存在本地，可查看、编辑、关闭或清空。
- **♡ 明确采用后学习**：只有在产物检查器点击“采用此版本并学习”才会进入长期记忆，测试稿和失败稿不会污染偏好；分析、Recipe Run 和检查器会显示本次复用了什么（可解释复用）。
- **🛡 崩溃可恢复的 Project 提交**：统一 durable 原语 + 提交 journal，进程被 kill / 断电后自动回滚到上一个一致版本；跨进程文件锁让 CLI 与服务并发操作同一项目返回稳定 `project_busy`。
- **🧩 浏览器生命周期 Module + 取消生成**：Project / Generation / Revision / Export 拆分为独立 Module；每工作区单飞生成，等待期可取消——排队任务真取消，执行中诚实转为“停止等待”。
- **⏳ 版本历史与恢复**：反馈、重跑和恢复都保留 HTML + 生成状态快照；恢复生成新版本、不覆盖历史，支持命名与行级差异。
- **📤 Export Center**：产物节点直接导出 PDF、逐页 PNG 或完整长图，含兼容性评分与 `export-report.json`。
- **🔒 隐私边界**：API Key、附件正文与完整反馈原文不写入长期记忆或诊断包。

## 设计吸收流水线（v0.6 新增）

<table>
<tr>
<td width="50%"><img src="assets/screenshots/v0.6.3/intake-review-pending.png" alt="素材审核台"><br><b>素材审核台 · 待审核</b><br>许可三档徽标、来源徽标、令牌色板、骨架大纲与吸收指标面板。</td>
<td width="50%"><img src="assets/screenshots/v0.6.3/intake-approved-absorption.png" alt="已采纳与六层入库"><br><b>已采纳 · 六层入库</b><br>生成风格预设 / 导入组件 / 吸收动效，指标同步更新。</td>
</tr>
<tr>
<td width="50%"><img src="assets/screenshots/v0.6.3/intake-preview-sandbox.png" alt="CSP 沙箱预览"><br><b>CSP 沙箱预览</b><br>候选页面在无脚本沙箱内渲染，候选脚本永不执行。</td>
<td width="50%"><img src="assets/screenshots/v0.6.3/motion-lab-intake-motion.png" alt="动效实验室"><br><b>动效实验室</b><br>吸收到的原创动效经预算钳制，并尊重三档减少动效偏好。</td>
</tr>
</table>

把全世界的优秀设计变成自己的素材——模板、风格、组件、装饰、动效、内容六个层面，三条吸收通道：

- **✋ 手动导入**：粘贴单个/批量 URL（≤10 条），或导入 ZIP 模板包，全部进入审核台
- **🕸 预设源抓取**：内置 12 个设计源（Land-book、Lapa.ninja、Landingfolio、Awwwards、Codrops、Animista、Google Fonts…），按画廊/组件/动效/字体四类适配，安全抓取（拒私网/重绑定/限速）
- **🤖 AI 分析**：候选自动生成设计描述、标签、布局说明与内容配方（复用你的 AI 设置，无 Key 不影响其他功能）

所有素材经**审核台**人工确认后入库（沙箱预览 + 许可三档治理：开放可入库 / 仅参考重写 / 仅灵感板），审核台支持批量采用 / 拒绝与按来源筛选，吸收指标面板记录候选与入库情况；风格进面板、组件可拖拽参与生成、动效进 motion-lab——且全部尊重动效偏好与预算。六个层面（模板、风格、组件、装饰、动效、内容）都走同一条「吸收 → 审核 → 入库 → 使用」通路。

## 网页反向拆解（v0.7 新增）

<table>
<tr>
<td width="50%"><img src="assets/screenshots/v0.7.0/intake-page-blocks-pending.png" alt="审核台中的真实候选"><br><b>审核台 · 候选带许可标签</b><br>贴一个公开网址，页面落进审核台等你过目；v0.7 起可以把候选的分区直接拆成生成分块。</td>
<td width="50%"><img src="assets/screenshots/v0.7.0/output-landing-with-page-sections.png" alt="页面分区出现在生成的成品里"><br><b>拆下来的分区 · 真的出现在成品里</b><br>开放许可的页面，标题与正文随生成带走；六类内容全部消费这条通道。</td>
</tr>
</table>

v0.7 把「吸收」的终点从模板库延伸到了**生成**：`POST /api/intake/page-blocks` 把已采纳候选的
分区重新切成生成通道认识的分块（含嵌套小节），六个内容类型全部消费——版权按字段判断：

| 许可 | 分块携带正文 | 整页进入模板库 |
|---|---|---|
| `open` | ✅ `verbatim` | ✅ |
| `reference` | ❌ `structure_only`（生成回落自带文案） | ❌ |
| `inspiration-only` | ❌ `structure_only` | ❌ |

携带页面正文必须由用户决定：该端点只读不写回。真实链路验收脚本随仓库发布
（`scripts/verify_page_blocks_chain.py`），发布说明里有这条链路翻出并修掉的三个缺陷——
包括一个在 v0.6.2–v0.6.4 三个发布版本里「全绿却每次抓取成功即崩」的真问题。

## 可编辑 PPTX（v0.6 新增）

<table>
<tr>
<td width="50%"><img src="assets/screenshots/v0.6.3/slide-editor-dialog.png" alt="工作台内幻灯片编辑"><br><b>工作台内幻灯片编辑</b><br>按页列出全部可编辑文本节点，保存即生成新版本。</td>
<td width="50%"><img src="assets/screenshots/v0.6.3/export-center-pptx.png" alt="导出中心 PPTX"><br><b>导出中心 · PPTX</b><br>deck 产物放开 PPTX 格式，导出完成给出 pptx 与报告两个下载项。</td>
</tr>
</table>

- **📄 标准 .pptx 导出**：deck 产物经 python-pptx 导出为符合标准的 `.pptx`，在 PowerPoint / WPS 中文本框真正可编辑；无法映射的能力在降级报告中如实列出（[报告实录](assets/screenshots/v0.6.3/pptx-export-report.png)）。
- **🖥️ 工作台内幻灯片编辑**：产物检查器里打开结构化幻灯片对话框即可改写标题与要点，通过 `PUT /slides` 带 `expected_revision` 写回，版本冲突时明确提示而不是静默覆盖。
- **🔁 编辑闭环**：改完写回再导出，之前的编辑会保留在导出的 PPTX 中。

## 工作台完整能力

- **🖥️ Web 工作台**：`htmlninefox app` 一键启动本地 Web UI，实时预览 + 智能体日志 + 模板选择。
- **🤖 真实 LLM 接入**：MiniMax-M3 / Claude / GPT-4o 三家 API，环境变量自动配置，离线规则引擎兜底。
- **🤝 Skill 联盟**：baoyu-slide-deck（AI 画图 PPT）· frontend-slides（无 AI 紫渐变）· beautiful-html-templates（28 套稳定模板）。
- **真实 HTML 模板库**：6 套完整模板、34 个可单独预览和抽取的页面，不再只展示线框。
- **统一需求入口**：支持文字、TXT、Markdown、JSON、CSV、HTML 和常见图片。
- **推荐与自由组合双路径**：可以直接接受推荐，也可以在工作区拖入版式、页面、风格、文件和 Skill。
- **无限画布工作区**：支持整体拖动、重命名、独立颜色、多工作区导航、吸附和端口连线。
- **AI 模型自主配置**：支持 OpenAI-compatible、Ollama 和自定义兼容接口；API Key 只保存在本地。
- **离线可用**：没有 API Key 时继续使用确定性的规则引擎，不阻塞生成。
- **反馈迭代**：自然语言反馈转成设计 Token 修改并重渲染，保留 `rev1 / rev2 / ...` 历史。
- **🎨 Pixel Garden 设计系统**：深钴蓝 `#173C8F` + 薄荷绿 `#49B894` + 暖纸白 `#F4F0E7` 统一设计令牌，5 大视觉产物一致体验。
- **🐳 Docker 镜像**：`docker run htmlninefox` 跨平台部署，多阶段构建，compose.yaml 注入环境变量。
- **跨平台使用**：Windows 便携包/安装器、Linux `.run/.tar.gz`、Python CLI、Web/PWA、Docker。

> [Export Center](docs/EXPORT-CENTER.md) 支持四种真实导出格式：`PDF`、逐页 `PNG`、完整长图 `PNG`，以及 v0.6 补齐的 `.pptx`。前三者产出真实文件与 `export-report.json`；`.pptx` 经 python-pptx 受控映射，文本框在 PowerPoint / WPS 中真正可编辑，无法映射的能力在降级报告中如实列出。DOCX 语义导出已出列至 v0.6.x。

## 看得见的真实效果

> 以下 4 张拍摄自 `v0.4.0`（2026-09-08），是 Pixel Garden 设计语言定型的历史记录。这些界面（模板预览、AI 模型配置、Docker 部署）**功能仍然存在**，但版式已随 v0.5 / v0.6 的设计收敛变化，当前列表观感以 v0.6.0 实拍为准。

<table>
<tr>
<td width="50%"><img src="assets/screenshots/v0.4.0/pixel-garden-unified.png" alt="Pixel Garden 统一设计"><br><b>Pixel Garden 统一设计</b><br>5 大视觉产物统一为深钴蓝 + 薄荷绿 + 暖纸白，杂志感与像素识别并存。</td>
<td width="50%"><img src="assets/screenshots/v0.4.0/web-workbench.png" alt="模板预览对话框"><br><b>模板预览对话框</b><br>真实 HTML 模板逐页预览，整套加入工作区或抽取当前页。</td>
</tr>
<tr>
<td width="50%"><img src="assets/screenshots/v0.4.0/llm-integration.png" alt="AI 模型配置对话框"><br><b>AI 模型配置</b><br>OpenAI-compatible 接口 + API Key 本地保存、可测连接；无 Key 时离线规则兜底。</td>
<td width="50%"><img src="assets/screenshots/v0.4.0/docker-deploy.png" alt="Docker 部署"><br><b>Docker 一键部署</b><br>docker run htmlninefox 跨平台运行，多阶段构建，环境变量注入。</td>
</tr>
</table>

### 六类真实产物

以下产物图由 `v0.5.0` 发布版的 e2e 验收流程真实生成（六类生成器的产物结构在 v0.7.0 未变；这 6 张由生成器实跑产出而非 UI 截图，因此仍是 v0.5.0 版式；v0.7.0 的页面分块产物见[网页反向拆解](#网页反向拆解v07-新增)一节）：

| 落地页 | 数据看板 | 发布会 PPT |
|---|---|---|
| ![Landing](assets/screenshots/v0.5.0/output-landing.png) | ![Dashboard](assets/screenshots/v0.5.0/output-dashboard.png) | ![Deck](assets/screenshots/v0.5.0/output-deck.png) |

| 翻页交互 | 海报 | 架构文档 |
|---|---|---|
| ![Deck page 2](assets/screenshots/v0.5.0/output-deck-page2.png) | ![Poster](assets/screenshots/v0.5.0/output-poster.png) | ![Architecture document](assets/screenshots/v0.5.0/output-archdoc.png) |

## 版本历史

RC3-A～E 按 [`mattpocock/skills`](https://github.com/mattpocock/skills) 的 research、domain-modeling、codebase-design、TDD 与 code-review 方法完成架构加固，并以 `v0.5.0` 稳定版收口；v0.6 在其上交付设计吸收流水线与可编辑 PPTX。

| 版本 | 日期 | 交付 | 记录 |
|---|---|---|---|
| **v0.7.0** | 2026-10-07 | **网页反向拆解**：页面分区变成项目分区（`page_blocks_from_candidate` + `POST /api/intake/page-blocks`），六个内容类型全部消费分块通道，版权按字段三档；归档分支 `archive`。发布前实测翻出并修复三个「全绿但坏了」（生产形态抓取成功即崩——随 v0.6.2–v0.6.4 出门；真实端点分块正文渲染两遍；嵌套分区被吞）；门禁 Windows 本地 `596 passed, 2 skipped`、16 个变异脚本全部 CAUGHT、Chromium `22/22`、真实链路 `15/15` | [Release](https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.7.0) · [发布说明](docs/RELEASE-NOTES-v0.7.0.md) · [设计文档](docs/DESIGN-v0.7-page-decomposition.md) |
| v0.6.4 | 2026-10-06 | 门禁收口：发布物字节级回读（下载 250MB 逐字节核对后才转正式）；修页面配色从未到达成品、`blocks` 被压平；C7 前端内核两步完成；门禁 `499 passed, 1 skipped`、8 个变异脚本 67 个变异全捕获 | [Release](https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.6.4) · [发布说明](docs/RELEASE-NOTES-v0.6.4.md) |
| v0.6.3 | 2026-10-04 | 修复 v0.6.2 的出站抓取 100% 失败（headers 落 body 位、缺 `context`、SNI 回退 DNS）；变异测试翻出五条「门禁自己说谎」；门禁 `414 passed, 1 skipped` | [Release](https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.6.3) · [发布说明](docs/RELEASE-NOTES-v0.6.3.md) |
| v0.6.2 | 2026-10-04 | 设计吸收 SSRF 连接级 IP 绑定（安全补丁方向正确，实现有缺陷致抓取不可用，**请跳过**） | [发布说明](docs/RELEASE-NOTES-v0.6.2.md) |
| v0.6.1 | 2026-10-03 | 幻灯片编辑器竞态修复；50s 中英双语真实操作录屏（Playwright 驱动真实服务）；门禁 `403 passed` | [Release](https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.6.1) · [发布说明](docs/RELEASE-NOTES-v0.6.1.md) |
| **v0.6.0** | 2026-10-01 | 设计吸收流水线（多 URL / ZIP 导入、12 个内置设计源、三档许可、CSP 沙箱审核台、AI 设计分析、吸收指标）；可编辑 PPTX 导出 + 工作台内幻灯片编辑器；发布前设计收口（字号 7 档 / 字重 4 档 / 间距尺度 token、首屏画布缩放 0.33→0.80、对比度达 AA）；修 Windows 便携包启动即崩，并把产物验证加到内容级；门禁 `387 passed, 1 skipped`、Chromium / WebKit 各 `22/22` | [Release](https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.6.0) · [发布说明](docs/RELEASE-NOTES-v0.6.0.md) · [门禁证据](docs/test-evidence/v0.6.0-s17-20260929/README.md) |
| **v0.5.0 稳定版** | 2026-09-25 | RC3 收口，发布 Windows / Linux / wheel / Docker 附件与 SHA-256 | [Release](https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.5.0) · [测试报告](docs/TEST-REPORT-v0.5.0.md) |
| RC3-E | 2026-09-25 | 浏览器生命周期 Module 拆分、生成取消、导出竞态守卫 | [迭代记录](docs/ITERATION-RC3-E-20260925.md) |
| RC3-D | 2026-09-25 | 崩溃可恢复 Project 提交（journal 回滚）、跨进程文件锁、生成原子发布 | [迭代记录](docs/ITERATION-RC3-D-20260925.md) |
| RC3-B2 / C | 2026-09-24 | 共享 Generation / Feedback / Restore / Export 应用用例，CLI Restore | [RC3-C 记录](docs/ITERATION-RC3-C-20260924.md) |
| RC3 视觉收敛 | 2026-09-24 | 顶栏双主动作、四档响应式、语义缩放、组件状态统一、经典模式回归 Pixel Garden | [视觉收敛记录](docs/ITERATION-RC3-VISUAL-CONVERGENCE-20260924.md) |
| v0.5.0rc2 | 2026-09-18 | 版本历史与恢复、原生动效三档偏好、100 节点验收、无障碍、DSH 插件预览 | [RC2 报告](docs/TEST-REPORT-RC2-20260918.md) |
| v0.5.0rc1 | 2026-09-14 | Project Memory、命令面板、Recipe Run、交互系统 | [RC1 说明](docs/RELEASE-NOTES-v0.5.0rc1.md) |
| v0.4.2 稳定版 | 2026-09-08 | Export Center（PDF / PNG + 兼容性报告） | [发布说明](docs/RELEASE-NOTES-v0.4.2.md) |

历史版本的真实证据截图：

<table>
<tr>
<td width="50%"><img src="docs/test-evidence/harness-plugin-20260918/harness-plugin-enabled.png" alt="DeepSeek Harness 中 htmlninefox 插件已启用"><br><b>DSH 插件已启用（rc2）</b><br>最终 tarball 安装进新的 Web profile；插件列表显示 htmlninefox 为全局插件并处于启用状态。</td>
<td width="50%"><img src="docs/test-evidence/harness-plugin-20260918/generated-poster.png" alt="Harness 插件链路生成并导出的中文海报"><br><b>生成、修改与导出链路（rc2）</b><br>离线生成中文海报，执行 dry-run 与真实反馈，再导出 PDF 和完整 PNG；兼容性报告 100 分。</td>
</tr>
<tr>
<td width="50%"><img src="docs/test-evidence/motion-20260918/revision-history-desktop.png" alt="版本历史、差异与恢复"><br><b>版本历史与恢复（rc2）</b><br>查看父版本、恢复来源、命名与源码差异，历史版本恢复为新版本。</td>
<td width="50%"><img src="docs/test-evidence/motion-20260918/motion-lab-desktop.png" alt="原生动效样页"><br><b>动效实验室（rc2）</b><br>操作反馈、选中素材、建立连接、阶段切换、产物就绪与版本恢复六类动效。</td>
</tr>
</table>

## 下载与安装

v0.7.0 已于 2026-10-07 发布，安装包随 [v0.7.0 Release](https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.7.0) 提供。v0.6.1 / v0.6.3 / v0.6.4 用户可直接升级（**请跳过 v0.6.2**），项目 schema 与数据目录不变；v0.7 为既有项目新增页面分块能力，旧项目的 `blocks` 仍是 id 列表，行为不变。DeepSeek Harness 插件使用[独立预览版](https://github.com/KratosLee-6/Html-ninefox/releases/tag/dsh-htmlninefox-v0.1.0-preview.1)，不要把插件版本当成应用版本。

包体命名规则保持不变，版本号随发布版本推进。下列文件名按 `v0.7.0` 列出，与 Release 附件逐一对应：

| 平台 | 推荐文件 | 使用方式 |
|---|---|---|
| Windows 10/11 | `HtmlNineFox-Setup-0.7.0.exe` | 安装到当前用户，创建开始菜单入口 |
| Windows 10/11 | `HtmlNineFox-Windows-x64-0.7.0.zip` | 解压后运行 `HtmlNineFox.exe`，免安装 |
| Linux | `HtmlNineFox-Linux-0.7.0.run` | `chmod +x` 后运行，安装到当前用户目录 |
| Linux/审计 | `HtmlNineFox-Linux-0.7.0.tar.gz` | 可查看完整安装内容 |
| macOS 14+（Apple Silicon） | `HtmlNineFox-macOS-arm64-0.7.0.zip` | 解压后右键 HtmlNineFox.app →「打开」绕过 Gatekeeper（未做公证） |
| Python 3.10+ | `htmlninefox-0.7.0-py3-none-any.whl` | `python -m pip install ./htmlninefox-0.7.0-py3-none-any.whl` |
| Docker | 源码构建 | `docker compose up --build`；标签 CI 验证镜像但不上传镜像仓库 |

> **已验证范围**：每个发布产物在转正式前都会被发布流水线**下载回来逐字节核对**（v0.6.4 起）；Windows 便携包在 CI 中真实启动并核对内容版本。安装器与 Linux / macOS 产物在本机（Windows）不做实跑安装，如实以 CI 验证为准。

### 快速开始

```bash
# 1. 安装（任选其一）
pip install htmlninefox
# 或下载 release 包
# 或 docker run htmlninefox

# 2. 配置 LLM（可选，离线也可用）
export MINIMAX_API_KEY="***"
# 或 export OPENAI_API_KEY="***"
# 或 export ANTHROPIC_API_KEY="***"

# 3. 启动 Web 工作台
htmlninefox app
# 打开 http://127.0.0.1:8620

# 4. 或 CLI 直接生成
htmlninefox expert "做一个 SaaS 落地页"
```

### 从源码运行

```bash
git clone https://github.com/KratosLee-6/Html-ninefox.git
cd Html-ninefox

# 推荐：uv
uv sync
uv run htmlninefox app

# 或传统 Python
python -m pip install -e .
htmlninefox app
```

浏览器默认打开本地工作台。也可以使用：

```bash
htmlninefox expert "做一个 AI 产品发布会 PPT"
htmlninefox expert --type landing --template fox-pixel-garden "创作工具官网"
htmlninefox feedback --project output/html9n-<时间戳> --note "标题更大，颜色更稳重"
htmlninefox restore --project output/html9n-<时间戳> --revision 0 --expected-revision 2
htmlninefox export output/html9n-<时间戳> --format png --scope long
```

完整说明：[安装指南](docs/INSTALL.md) · [多种运行方式](docs/RUNNING-OPTIONS.md) · [UI 手册](docs/UI-GUIDE.md) · [VI 手册](docs/VI.md)

## 模板、内容与视觉系统

### 真实模板作品库

- 归藏 · 电子墨水发布会：6 页
- 归藏 · 靛蓝研究档案：6 页
- 归藏 · 瑞士信号系统：6 页
- 归藏 · 牛皮纸品牌故事：6 页
- 归藏 · 沙丘作品集：5 页
- 九尾狐 · 像素花园产品页：5 页

共 **6 套 / 34 页**，均为 Html九尾狐原创演示；采用归藏式编辑设计方法启发，没有复制许可不明的第三方模板。

### v0.4 开发预览：私人模板资产库

- 在“版式”栏导入一个独立 HTML，或导入包含 CSS、JavaScript、图片和字体的完整文件夹。
- 自动识别多 HTML 页面、`data-page`、`.page` 与 `.slide`，并提取页面角色、常见颜色和字体。
- 私人模板仅保存在当前输出目录的 `.library/gallery/`，不会自动提交到 Git 仓库。
- 生成时会使用导入模板的页面结构与视觉 Token；使用次数会成为下一次推荐信号。
- 画布支持撤销/重做、Shift 框选、多选移动、组合、锁定、小地图，以及 `Ctrl+K` 搜索定位。

使用说明：[私人 HTML 模板导入](docs/PRIVATE-TEMPLATE-IMPORT.md) · [v0.4 产品迭代与竞品拆解](docs/PRODUCT-ITERATION-v0.4.md)

### 六类生成器

`deck` 发布会 PPT · `doc` 文档 · `poster` 海报 · `landing` 落地页 · `dashboard` 数据看板 · `archdoc` 架构文档。

### 十一套视觉系统

内置基础预设与 Pixel Garden、Duotone Studio、Editorial Ink、Swiss Signal、Soft Silver 等结构级视觉系统。模板差异不仅是换颜色，而是排版、间距、卡片、网格和信息节奏的整体变化。

## AI 与隐私

- AI 是增强能力，不是运行前提。
- API Key 保存到当前输出目录的 `.settings/ai.json`，不会写入项目快照、诊断包或 Git 仓库。
- 设置读取接口只返回 `api_key_set`，不返回 Key 明文。
- 文件与图片输入保存在本地 `.inputs/`；单文件默认上限 8MB。
- 未启用 AI、连接失败或没有 Key 时，自动继续使用离线规则分析。

## 测试与信任证据

v0.7.0 的门禁已在 2026-10-07 实测通过：

| 验证项 | 结果 | 证据 |
|---|---:|---|
| Python + 浏览器测试套件（Windows 本机） | **596 passed, 2 skipped**（68 个测试文件；Linux CI 预期 597 passed / 1 skipped） | [v0.7.0 发布说明 · 验证](docs/RELEASE-NOTES-v0.7.0.md#验证) |
| 变异测试 | **16 个脚本全部 CAUGHT**（87 个变异零漏网；P1/P4 重写、新增 F1） | [同上](docs/RELEASE-NOTES-v0.7.0.md#验证) |
| 浏览器端到端（bundled Chromium） | **22 / 22** | `e2e_verify.py`（2026-10-07 实测） |
| 真实链路实测 | **15 / 15**：真实公网抓取 → SSRF 拒内网 → 拆块 → 六类 intent 各恰好一次 → 反馈迭代不丢 → 仅参考许可零正文 | [验收脚本](scripts/verify_page_blocks_chain.py)（已随仓库发布） |
| 发布元数据一致性（`check_release_version.py`） | **一致（v0.7.0）** | 本地实测 |
| 生产形态抓取门禁 | 按生产形状调用 `fetch_reference`，变异 F1 锁定 | [test_design_intake.py](tests/test_design_intake.py) |
| LLM 接入 | MiniMax-M3 / Claude / GPT-4o 环境变量自动配置 | [配置文档](docs/INSTALL.md) |

> **本轮门禁的做法**：延续「每一条新门禁都做反向验证——把对应修复去掉，测试必须变红」。
> v0.7.0 的额外教训是**夹具的形状也要像真实数据**：「恰好渲染一次」的门禁挡住了重复渲染，
> 却被自己端点 heading == content 的产出形状绕过；「按生产形态调用一次」胜过「按夹具形态
> 调用一百次」。详见[发布说明](docs/RELEASE-NOTES-v0.7.0.md)。

v0.6.0 的全部门禁已在 2026-09-29 复验通过：

| 验证项 | 结果 | 证据 |
|---|---:|---|
| Python + 浏览器测试套件 | **387 passed, 1 skipped**（v0.5.0 基线 303，本轮新增 84 条） | [v0.6.0 门禁证据](docs/test-evidence/v0.6.0-s17-20260929/README.md) |
| —— 设计体检 / 版式层级 / 动效行为 | 6 + 8 + 6 条 | [发布说明 · 验证](docs/RELEASE-NOTES-v0.6.0.md#验证) |
| —— 生成质量 | 50 条（板块划分顺序、内容质量、最终效果、端到端产物自足） | [同上](docs/RELEASE-NOTES-v0.6.0.md#验证) |
| —— 动作派发表 / 写回协议 / 冻结入口 | 4 + 2 + 5 条 | [同上](docs/RELEASE-NOTES-v0.6.0.md#验证) |
| JavaScript 语法（13 个 static JS + inline 检查） | **全部通过** | [同一证据](docs/test-evidence/v0.6.0-s17-20260929/README.md) |
| Chromium 验收（bundled Chromium） | **22 / 22** | [同一证据](docs/test-evidence/v0.6.0-s17-20260929/README.md) |
| WebKit（Safari 引擎）验收 | **22 / 22** | [同一证据](docs/test-evidence/v0.6.0-s17-20260929/README.md) |
| 打包产物实跑 | Windows / Linux / macOS / Docker 四个 job 全绿；**Windows 便携包真实启动通过** | [发布说明 · 验证](docs/RELEASE-NOTES-v0.6.0.md#验证) |
| 发布元数据一致性（`check_release_version.py`） | **一致** | [同一证据](docs/test-evidence/v0.6.0-s17-20260929/README.md) |
| DSH 插件与最终 tarball 安装 | **2 / 2 通过** | [接入与发布记录](docs/DEEPSEEK-HARNESS-INTEGRATION.md) |
| 版本历史、恢复与 100 节点 | **通过**（含在 pytest 套件内） | [RC2 报告](docs/TEST-REPORT-RC2-20260918.md) |
| 动效、减少动态效果、竞态与资源打包 | **通过** | [动效交付记录](docs/ITERATION-MOTION-20260918.md) |
| Docker 镜像 | 标签 CI 独立 job 构建并验证 | [构建工作流](.github/workflows/build-release-packages.yml) |
| LLM 接入 | MiniMax-M3 / Claude / GPT-4o 环境变量自动配置 | [配置文档](docs/INSTALL.md) |

> **本轮门禁的做法**：每一条新门禁都做过反向验证——把对应修复去掉，测试必须变红；否则视为无效门禁并重写。这条纪律是必要的，因为本轮被拦下的多数缺陷形态一致：**服务端能力实现齐备，界面却没有可达入口，也没有任何测试点击过它**。打包流水线也据此改成了「构建后必须真实执行产物」，否则一个启动即崩的包能一路带着全绿的四个 job 进入 Release。

v0.5.0 稳定版的发布证据保留在 [v0.5.0 测试报告](docs/TEST-REPORT-v0.5.0.md)（含发布附件与 SHA-256、Windows 便携包真机烟测），更早的证据见 [v0.5.0rc3 测试报告](docs/TEST-REPORT-v0.5.0rc3.md)与 [v0.4.2-environment.txt](docs/test-evidence/v0.4.2-environment.txt)。

```bash
python -m pytest tests -q -p no:cacheprovider
python e2e_verify.py
```

## 产物结构

```text
output/html9n-<时间戳>/
├── output.html
├── brief.json / brief.md
├── style.md
├── assets.json
├── .foxstate.json
├── revisions/
└── feedback.md
```

`.foxstate.json` 会记录模板、页面区块、附件、Skill 和选择模式，确保后续反馈迭代不是重新猜测。

## 当前状态与路线

当前仓库版本为 `v0.7.0`（已于 2026-10-07 发布）：**网页反向拆解**——把一个真实网页的分区变成一个结构可编辑的项目，六个内容类型全部消费分块通道，版权按字段三档；发布前实测翻出并修复三个「全绿但坏了」的缺陷（其中一个随 v0.6.2–v0.6.4 三次发布出门）。门禁 Windows 本地 `596 passed / 2 skipped`，16 个变异脚本全部 CAUGHT。`v0.6.4` 是上一稳定版（门禁收口 + 发布物字节级回读），`v0.6.0` 交付设计吸收与可编辑 PPTX 两条主线。下一阶段方向（桌面版 / Word 导出 / 拆解更聪明 / 生成效果打磨）按 [ROADMAP](docs/ROADMAP.md) 与社区反馈推进。

查看完整路线：[ROADMAP](docs/ROADMAP.md) · 查看变更：[CHANGELOG](CHANGELOG.md)

## 贡献与致谢

欢迎提交 Issue、模板、视觉系统、测试和 Skill 联盟适配。设计方法受到归藏、花叔 Design 和 Archify 等开源社区工作的启发；详细来源和许可审查见 [DESIGN-SOURCES](docs/DESIGN-SOURCES.md)。

### Skill Alliance 致谢（v0.3-v0.4）

Html九尾狐 v0.3-v0.4 的 PPT 生成模块参考了以下两位创作者的开源 Skill 作品，诚挚致谢：

- 🎨 **[宝玉 (JimLiu)](https://github.com/JimLiu)** — author of [baoyu-skills](https://github.com/JimLiu/baoyu-skills) (especially [baoyu-slide-deck](https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-slide-deck)). The "AI 画图生成每页 PPT · 17 套风格" image-based PPT approach inspired Html九尾狐 v0.3's `ppt_image` intent.

- 🎨 **[张咋啦 (zarazhangrui)](https://github.com/zarazhangrui)** — author of [frontend-slides](https://github.com/zarazhangrui/frontend-slides), [beautiful-html-templates](https://github.com/zarazhangrui/beautiful-html-templates), [beautiful-feishu-whiteboard](https://github.com/zarazhangrui/beautiful-feishu-whiteboard). The "避开 AI 紫渐变" + "28 套稳定出片" philosophy deeply shaped Html九尾狐 v0.3-v0.4's template library design.

### PPT 编辑工具致敬（v0.6）

v0.6 的可编辑 PPT 能力建立在两位前辈的工作之上，诚挚致谢：

- 🪄 **[Univer](https://github.com/dream-num/univer)（dream-num）** — Apache-2.0 的浏览器端 Office 套件引擎（Sheets / Docs / Slides / Canvas 一体）。v0.6 的工作台内幻灯片可视化编辑（近 1:1 PowerPoint 观感、PPT/PPTX 导入导出）基于 Univer Slides 构建，bundle 本地化保持离线优先。
- 📄 **[python-pptx](https://github.com/scanny/python-pptx)（Steve Canny）** — MIT 许可的 PowerPoint 文件库。v0.6 的服务端 .pptx 文件桥用它实现受控映射，让导出的 PPT 在 PowerPoint / WPS 中真正文本可编辑。

### 设计系统致谢（v0.4）

- 🎨 **Pixel Garden 设计系统** — 深钴蓝 `#173C8F` + 薄荷绿 `#49B894` + 暖纸白 `#F4F0E7` 统一设计令牌，灵感来自电子杂志 × 电子墨水美学。

## 许可证

[MIT License](LICENSE) © 2026 **KratosLee · Html九尾狐项目组**
