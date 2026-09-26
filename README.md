<div align="center">
  <img src="htmlninefox/server/static/logo-horizontal.svg" width="430" alt="Html九尾狐 Pixel Garden Logo">
  <h1>Html九尾狐 · HTML 创作工作台</h1>
  <p><strong>把文字、文件、图片和散落的 HTML 模板放进一张无限画布，经过分析、推荐、自由组合与反馈迭代，生成真正可交付的单文件 HTML。</strong></p>
  <p>个人开源项目 by <a href="https://github.com/KratosLee-6">KratosLee</a> · 默认中文 · 离线规则引擎可用 · AI 可选增强</p>
  <p><strong>简体中文</strong> · <a href="README.en.md">English</a></p>
</div>

<div align="center">

[![App Release](https://img.shields.io/badge/app-v0.5.0-173C8F)](https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.5.0)
[![DSH Plugin](https://img.shields.io/badge/DSH_plugin-0.1.0--preview.1-49B894)](https://github.com/KratosLee-6/Html-ninefox/releases/tag/dsh-htmlninefox-v0.1.0-preview.1)
[![Build Packages](https://github.com/KratosLee-6/Html-ninefox/actions/workflows/build-release-packages.yml/badge.svg)](https://github.com/KratosLee-6/Html-ninefox/actions/workflows/build-release-packages.yml)
[![Test CI](https://github.com/KratosLee-6/Html-ninefox/actions/workflows/test.yml/badge.svg)](https://github.com/KratosLee-6/Html-ninefox/actions/workflows/test.yml)
[![Tests](https://img.shields.io/badge/pytest-238%20passed%20%7C%201%20skipped-1F8A70)](docs/TEST-REPORT-v0.5.0.md)
[![Chromium E2E](https://img.shields.io/badge/Chromium%20E2E-22%2F22-173C8F)](docs/TEST-REPORT-v0.5.0.md)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB)](pyproject.toml)
[![License](https://img.shields.io/badge/License-MIT-D9A441)](LICENSE)

</div>

![Html九尾狐 v0.5.0 Pixel Garden 工作台](assets/screenshots/v0.5.0/workbench-paper-1440.png)

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

## 当前版本与最新进展（2026-09-25）

当前应用包版本为 `0.5.0`，对应稳定标签 `v0.5.0`（2026-09-25 发布）。v0.5.0 在 RC3 工程基线之上完成共享应用用例、崩溃可恢复 Project 提交与跨进程锁、浏览器生命周期 Module 拆分；Windows、Linux 与 Python 安装包由同名标签工作流构建并附带 SHA-256。

| 轨道 | 当前状态 | 查看 |
|---|---|---|
| 应用 Release | `v0.5.0` 稳定版，可直接下载安装 | [下载与发布说明](https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.5.0) |
| 发布验证 | 全量测试 `238 passed, 1 skipped`；Chromium e2e 双通道 `22/22`；附件回读校验一致 | [v0.5.0 测试报告](docs/TEST-REPORT-v0.5.0.md) |
| DeepSeek Harness 插件 | `0.1.0-preview.1`，独立于应用版本 | [插件预览版](https://github.com/KratosLee-6/Html-ninefox/releases/tag/dsh-htmlninefox-v0.1.0-preview.1) |

### 功能 ↔ 截图对照（v0.5.0 实拍集）

以下 18 张全部拍摄自 `v0.5.0` 发布版（顶栏版本徽标为 `v0.5.0`），每张对应一项真实功能：

**工作台与画布**

<table>
<tr>
<td width="50%"><img src="assets/screenshots/v0.5.0/workbench-paper-1440.png" alt="Pixel Paper 桌面工作台"><br><b>Pixel Paper 桌面工作台</b><br>三栏层级：素材库 · 无限画布工作区 · 检查器。</td>
<td width="50%"><img src="assets/screenshots/v0.5.0/workbench-night-1440.png" alt="夜蓝主题桌面工作台"><br><b>夜蓝主题桌面工作台</b><br>同一组件层级与品牌语义色的完整暗色主题。</td>
</tr>
<tr>
<td width="50%"><img src="assets/screenshots/v0.5.0/workbench-overview.png" alt="多工作区管理"><br><b>多工作区管理</b><br>工作区导航、识别色、独立推进与整组移动。</td>
<td width="50%"><img src="assets/screenshots/v0.5.0/workbench-tablet-768.png" alt="平板 768 布局"><br><b>平板 768 布局</b><br>侧栏折叠为顶栏抽屉，画布语义缩放。</td>
</tr>
<tr>
<td width="50%"><img src="assets/screenshots/v0.5.0/workbench-mobile-390.png" alt="移动任务视图"><br><b>移动任务视图</b><br>以工作区动作和节点卡片替代不可读的缩小画布。</td>
<td width="50%"><img src="assets/screenshots/v0.5.0/workbench-mobile-library.png" alt="移动端素材库"><br><b>移动端素材库</b><br>REAL HTML 模板卡片在移动端可直接浏览与拖入。</td>
</tr>
</table>

**输入与检查器**

<table>
<tr>
<td width="50%"><img src="assets/screenshots/v0.5.0/input-dialog-paper.png" alt="输入需求引导"><br><b>输入需求引导</b><br>文字、文件与图片统一入口，AI 分析后推荐组合。</td>
<td width="50%"><img src="assets/screenshots/v0.5.0/classic-pixel-garden.png" alt="经典表单模式"><br><b>经典表单模式</b><br>一句话 Brief 快速生成，与工作台同一品牌系统。</td>
</tr>
<tr>
<td width="50%"><img src="assets/screenshots/v0.5.0/selected-node-inspector.png" alt="需求节点检查器"><br><b>需求节点检查器</b><br>选中即编辑文字与附件，一键向所属工作区推进。</td>
<td width="50%"><img src="assets/screenshots/v0.5.0/generated-output-inspector.png" alt="产物节点检查器"><br><b>产物节点检查器</b><br>版本徽标、运行轨迹、采用学习、口语反馈与导出入口。</td>
</tr>
</table>

**Project Memory 与命令面板**

<table>
<tr>
<td width="50%"><img src="assets/screenshots/v0.5.0/project-memory-saved.png" alt="项目记忆"><br><b>项目记忆</b><br>品牌、受众、语气、禁忌、模板与长期说明本地保存，成功状态可见。</td>
<td width="50%"><img src="assets/screenshots/v0.5.0/command-palette-search.png" alt="命令面板"><br><b>命令面板</b><br>Ctrl+K 键盘打开、输入搜索、活动项与快捷键提示。</td>
</tr>
</table>

**导出中心（真实导出全流程）**

<table>
<tr>
<td width="50%"><img src="assets/screenshots/v0.5.0/export-center-ready.png" alt="导出分析就绪"><br><b>导出分析就绪</b><br>兼容性评分、分页模型、动态特性与本地引擎状态。</td>
<td width="50%"><img src="assets/screenshots/v0.5.0/export-center.png" alt="真实导出结果"><br><b>真实导出结果</b><br>deck 检测 7 页，实际产出 page-01.png 与 export-report.json 并可下载。</td>
</tr>
</table>

**版本、错误与取消**

<table>
<tr>
<td width="50%"><img src="assets/screenshots/v0.5.0/revision-restore-complete.png" alt="版本恢复"><br><b>版本恢复</b><br>真实把 rev0 恢复为新的 rev2，显示恢复来源、行级差异与成功 Toast。</td>
<td width="50%"><img src="assets/screenshots/v0.5.0/export-analysis-error.png" alt="受控错误"><br><b>受控错误</b><br>服务端返回项目不存在：按钮禁用、错误面板与 Toast 同步反馈。</td>
</tr>
<tr>
<td width="50%"><img src="assets/screenshots/v0.5.0/generation-cancel.png" alt="取消生成"><br><b>取消生成</b><br>等待期可取消：排队任务真取消，执行中诚实转为“停止等待”。</td>
<td width="50%"><img src="assets/screenshots/v0.5.0/workbench-paper-1440.png" alt="生成进度环"><br><b>生成进度环</b><br>真实 job.progress 驱动节点进度环，完成收敛、失败陶土橙。</td>
</tr>
</table>

完整 24 张（含 6 张真实产物输出图）见 [assets/screenshots/v0.5.0/](assets/screenshots/v0.5.0/)，清单与复现命令见[截图说明](assets/screenshots/README.md)。

## v0.5.0 稳定版核心能力

![崩溃可恢复提交与生命周期 Module](assets/screenshots/v0.5.0/generation-cancel.png)

- **🧠 Project Memory**：品牌、受众、语气、禁忌、模板、主色和字体保存在本地，可查看、编辑、关闭或清空。
- **♡ 明确采用后学习**：只有在产物检查器点击“采用此版本并学习”才会进入长期记忆，测试稿和失败稿不会污染偏好；分析、Recipe Run 和检查器会显示本次复用了什么（可解释复用）。
- **🛡 崩溃可恢复的 Project 提交**：统一 durable 原语 + 提交 journal，进程被 kill / 断电后自动回滚到上一个一致版本；跨进程文件锁让 CLI 与服务并发操作同一项目返回稳定 `project_busy`。
- **🧩 浏览器生命周期 Module + 取消生成**：Project / Generation / Revision / Export 拆分为独立 Module；每工作区单飞生成，等待期可取消——排队任务真取消，执行中诚实转为“停止等待”。
- **⏳ 版本历史与恢复**：反馈、重跑和恢复都保留 HTML + 生成状态快照；恢复生成新版本、不覆盖历史，支持命名与行级差异。
- **📤 Export Center**：产物节点直接导出 PDF、逐页 PNG 或完整长图，含兼容性评分与 `export-report.json`。
- **🔒 隐私边界**：API Key、附件正文与完整反馈原文不写入长期记忆或诊断包。

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

> [Export Center](docs/EXPORT-CENTER.md) 已完成 PDF / PNG 第一阶段。下一阶段提供高保真 PPTX，再推进受控范围内的可编辑 PPTX / DOCX。

## 看得见的真实效果

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

以下产物图由 `v0.5.0` 发布版的 e2e 验收流程真实生成：

| 落地页 | 数据看板 | 发布会 PPT |
|---|---|---|
| ![Landing](assets/screenshots/v0.5.0/output-landing.png) | ![Dashboard](assets/screenshots/v0.5.0/output-dashboard.png) | ![Deck](assets/screenshots/v0.5.0/output-deck.png) |

| 翻页交互 | 海报 | 架构文档 |
|---|---|---|
| ![Deck page 2](assets/screenshots/v0.5.0/output-deck-page2.png) | ![Poster](assets/screenshots/v0.5.0/output-poster.png) | ![Architecture document](assets/screenshots/v0.5.0/output-archdoc.png) |

## 版本历史

RC3-A～E 按 [`mattpocock/skills`](https://github.com/mattpocock/skills) 的 research、domain-modeling、codebase-design、TDD 与 code-review 方法完成架构加固，并以 `v0.5.0` 稳定版收口。

| 版本 | 日期 | 交付 | 记录 |
|---|---|---|---|
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

应用安装包请前往 [v0.5.0 Release](https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.5.0)。这是当前稳定版；DeepSeek Harness 插件使用[独立预览版](https://github.com/KratosLee-6/Html-ninefox/releases/tag/dsh-htmlninefox-v0.1.0-preview.1)，不要把插件版本当成应用版本。

| 平台 | 推荐文件 | 使用方式 |
|---|---|---|
| Windows 10/11 | `HtmlNineFox-Setup-0.5.0.exe` | 安装到当前用户，创建开始菜单入口 |
| Windows 10/11 | `HtmlNineFox-Windows-x64-0.5.0.zip` | 解压后运行 `HtmlNineFox.exe`，免安装 |
| Linux | `HtmlNineFox-Linux-0.5.0.run` | `chmod +x` 后运行，安装到当前用户目录 |
| Linux/审计 | `HtmlNineFox-Linux-0.5.0.tar.gz` | 可查看完整安装内容 |
| macOS 14+（Apple Silicon） | `HtmlNineFox-macOS-arm64-0.5.0.zip` | 解压后右键 HtmlNineFox.app →「打开」绕过 Gatekeeper（未做公证） |
| Python 3.10+ | `htmlninefox-0.5.0-py3-none-any.whl` | `python -m pip install ./htmlninefox-0.5.0-py3-none-any.whl` |
| Docker | 源码构建 | `docker compose up --build`；标签 CI 验证镜像但不上传镜像仓库 |

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

`v0.5.0` 稳定版已于 **2026-09-25** 发布，全部门禁在发布提交上复验通过：

| 验证项 | 结果 | 证据 |
|---|---:|---|
| Python / API / 存储 / 安全 / 浏览器测试 | **238 passed, 1 skipped** | [v0.5.0 测试报告](docs/TEST-REPORT-v0.5.0.md) |
| Chromium e2e（bundled Chromium + 系统 Edge/WebView2 引擎双通道） | **22 / 22 · 22 / 22** | [同一报告](docs/TEST-REPORT-v0.5.0.md) |
| 版本历史、恢复与 100 节点 | **通过** | [RC2 报告](docs/TEST-REPORT-RC2-20260918.md) |
| 动效、减少动态效果、竞态与资源打包 | **通过** | [动效交付记录](docs/ITERATION-MOTION-20260918.md) |
| DSH 插件与最终 tarball 安装 | **2 / 2 通过** | [接入与发布记录](docs/DEEPSEEK-HARNESS-INTEGRATION.md) |
| 发布附件 | 5 个包体 + SHA-256；wheel 与 Windows zip 回读校验一致；wheel 干净 venv 安装烟测通过 | [v0.5.0 Release](https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.5.0) |
| Windows 便携包真机烟测 | 打包 exe 启动 → 生成 → 真实 PNG 导出 | [同一报告](docs/TEST-REPORT-v0.5.0.md) |
| Docker 镜像 | 标签 CI 独立 job 构建并验证 | [构建工作流](.github/workflows/build-release-packages.yml) |
| LLM 接入 | MiniMax-M3 / Claude / GPT-4o 环境变量自动配置 | [配置文档](docs/INSTALL.md) |

发布命令、环境与限制见：[v0.5.0 测试报告](docs/TEST-REPORT-v0.5.0.md)。历史版本证据保留在 [v0.5.0rc3 测试报告](docs/TEST-REPORT-v0.5.0rc3.md)与 [v0.4.2-environment.txt](docs/test-evidence/v0.4.2-environment.txt)。

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

`v0.5.0` 是当前稳定版（2026-09-25 发布）：共享应用用例、崩溃可恢复 Project 提交与跨进程锁、浏览器生命周期 Module 全部收口，Windows / Linux / wheel / Docker 附件与 SHA-256 齐备。下一阶段按 ROADMAP 进入 v0.6：可编辑 PPTX / DOCX 导出与 Tauri 桌面 sidecar。

查看完整路线：[ROADMAP](docs/ROADMAP.md) · 查看变更：[CHANGELOG](CHANGELOG.md)

## 贡献与致谢

欢迎提交 Issue、模板、视觉系统、测试和 Skill 联盟适配。设计方法受到归藏、花叔 Design 和 Archify 等开源社区工作的启发；详细来源和许可审查见 [DESIGN-SOURCES](docs/DESIGN-SOURCES.md)。

### Skill Alliance 致谢（v0.3-v0.4）

Html九尾狐 v0.3-v0.4 的 PPT 生成模块参考了以下两位创作者的开源 Skill 作品，诚挚致谢：

- 🎨 **[宝玉 (JimLiu)](https://github.com/JimLiu)** — author of [baoyu-skills](https://github.com/JimLiu/baoyu-skills) (especially [baoyu-slide-deck](https://github.com/JimLiu/baoyu-skills/tree/main/skills/baoyu-slide-deck)). The "AI 画图生成每页 PPT · 17 套风格" image-based PPT approach inspired Html九尾狐 v0.3's `ppt_image` intent.

- 🎨 **[张咋啦 (zarazhangrui)](https://github.com/zarazhangrui)** — author of [frontend-slides](https://github.com/zarazhangrui/frontend-slides), [beautiful-html-templates](https://github.com/zarazhangrui/beautiful-html-templates), [beautiful-feishu-whiteboard](https://github.com/zarazhangrui/beautiful-feishu-whiteboard). The "避开 AI 紫渐变" + "28 套稳定出片" philosophy deeply shaped Html九尾狐 v0.3-v0.4's template library design.

### 设计系统致谢（v0.4）

- 🎨 **Pixel Garden 设计系统** — 深钴蓝 `#173C8F` + 薄荷绿 `#49B894` + 暖纸白 `#F4F0E7` 统一设计令牌，灵感来自电子杂志 × 电子墨水美学。

## 许可证

[MIT License](LICENSE) © 2026 **KratosLee · Html九尾狐项目组**
