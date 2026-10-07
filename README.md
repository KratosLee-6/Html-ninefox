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


> 当前应用包版本为 `0.7.0`（2026-10-07 发布）· 完整功能与架构见下。

---

## ▶ 视频

> GitHub 不直接内联播放仓库里的 mp4：解说版在 **Release 页在线播放**，录屏版是原文件直链。

- **[解说版 · 75 秒（v0.7.0 Release 页）](https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.7.0)** — 人声解说 + 发布会式动画 + 真实操作录屏：贴入 example.com → 审核台 → 采纳 → 拆块生成 → 页面自己的正文出现在成品里。由 [huashu-art-motion](https://github.com/alchaincyf/huashu-art-motion) 引擎的 t2 发布会语法驱动，工程在 `film/v070-huashu/`（随仓库外的工作区维护）。
- [真实录屏版 · 73 秒（原文件）](https://raw.githubusercontent.com/KratosLee-6/Html-ninefox/main/assets/promo/htmlninefox-demo-v070-16x9.mp4) — 无解说，光标逐帧真实操作，片头/片尾为品牌帧。

![v0.7.0 解说版视频海报](assets/promo/poster-demo-v070.png)

## 🆕 v0.7.0 · 网页反向拆解（最新功能）

**把一个真实网页的分区，变成一个结构可编辑的项目。**

<table>
<tr>
<td width="50%"><img src="assets/screenshots/v0.7.0/intake-page-blocks-pending.png" alt="审核台"><br><b>贴一个公开网址 → 落进审核台</b><br>候选带许可标签；开放许可正文随行，仅参考只借结构。</td>
<td width="50%"><img src="assets/screenshots/v0.7.0/output-landing-with-page-sections.png" alt="成品"><br><b>拆下来的分区 → 出现在成品里</b><br>六个内容类型全部消费分块通道。</td>
</tr>
</table>

- `POST /api/intake/page-blocks` 把已采纳候选的分区切成生成通道认识的分块（嵌套小节也拆得开），**端点只读不写回**——携带正文必须由用户决定。
- 版权按字段：`open` 才随行原文；`reference` / `inspiration-only` 只带结构与顺序，生成回落自带文案。
- 门禁：Windows 本地 `596 passed / 2 skipped`，Linux CI `597 passed / 1 skipped`；16 个变异脚本全部 CAUGHT；浏览器 22/22；真实链路 15/15。
- 详见 [v0.7.0 发布说明](docs/RELEASE-NOTES-v0.7.0.md) · [设计文档](docs/DESIGN-v0.7-page-decomposition.md)。

## 🏗 整体架构

```text
设计吸收（12 源抓取 / URL / ZIP）        网页反向拆解（v0.7 新增）
        ↓ 审核台 · 三档许可                      ↓ 拆成分区
        └────────────┬───────────────────────────┘
                     ↓
   文字 / 文件 / 图片 / HTML  →  AI 或离线规则分析  →  推荐内容类型 + 模板 + 分区
                     ↓
        无限画布工作区（自由组合 / 反馈迭代 / 版本历史）
                     ↓
              生成单文件 HTML（六类内容）
                     ↓
       导出 PDF / 逐页 PNG / 长图 / 可编辑 PPTX + 兼容性报告
```

**重要后端模块**

| 模块 | 职责 |
|---|---|
| `intake.py` | 设计吸收：SSRF 防护抓取（连接级 IP 绑定）、来源注册、候选审核、风格预设、页面分块（`page_blocks_from_candidate`） |
| `pipeline.py` | 生成流水线：Brief → 路由 → 风格 → 素材 → 组合 → 生成 → 验证，`.foxstate.json` 状态落盘，反馈迭代确定性重渲染 |
| `rules.py` + `generators/` | 离线规则引擎与六个渲染器（landing/dashboard/deck/poster/archdoc/doc），分块通道全量消费 |
| `server/app.py` | 零依赖本地服务：工作台 API（intake / 生成 / 反馈 / 版本 / 导出 / 幻灯片编辑） |
| `exporting.py` + `pptx_export.py` | PDF / 逐页 PNG / 长图 + 兼容性报告；python-pptx 受控映射出可编辑 PPTX |
| `revisions.py` + `project_memory.py` | 版本历史快照与恢复；明确采用后才学习的本地偏好记忆 |

架构全文见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

## 🧩 功能板块

| 板块 | 一句话 | 详情 |
|---|---|---|
| 🖼 无限画布工作台 | 文字、文件、图片、HTML 模板放上画布，自由组合、推进生成 | [UI 手册](docs/UI-GUIDE.md) |
| 🕸 设计吸收 | 12 个内置源 + URL、ZIP 抓取，审核台人工确认，三档许可代码级强制 | [v0.6.0 发布说明](docs/RELEASE-NOTES-v0.6.0.md) |
| 🔎 网页反向拆解（新） | 采纳的候选拆成分区直接进生成，六类内容全消费 | [v0.7.0 发布说明](docs/RELEASE-NOTES-v0.7.0.md) |
| 📊 可编辑 PPTX | deck 导出标准 .pptx，PowerPoint 里真能改；工作台内幻灯片编辑闭环 | [导出中心](docs/EXPORT-CENTER.md) |
| 📤 导出中心 | PDF / 逐页 PNG / 长图 + 兼容性评分报告 | [导出中心](docs/EXPORT-CENTER.md) |
| 🧠 项目记忆 + 版本 | 明确采用才学习；反馈、重跑、恢复全留快照 | [归档·完整版](docs/HOMEPAGE-ARCHIVE.md) |

## 🚀 快速开始

```bash
pip install htmlninefox          # 或下载 Release 包 / docker compose up --build
htmlninefox app                  # 打开 http://127.0.0.1:8620
htmlninefox expert "做一个 SaaS 落地页"   # CLI 直接生成
```

Windows / Linux / macOS 安装包与 wheel 见 [**v0.7.0 Release**](https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.7.0)（全部附 SHA-256）。离线可用，API Key 可选。

## 📜 版本迭代

| 版本 | 日期 | 一句话 |
|---|---|---|
| **v0.7.0** | 2026-10-07 | **网页反向拆解**：页面分区 → 项目分区，六类全消费；发布前实测修复三个「全绿但坏了」 |
| v0.6.4 | 2026-10-06 | 门禁收口：发布物字节级回读；配色与 blocks 两个真缺陷 |
| v0.6.0 | 2026-10-01 | 设计吸收流水线 + 可编辑 PPTX 两条主线 |
| v0.5.0 | 2026-09-25 | RC3 收口，全平台安装包 |

完整逐版记录：[CHANGELOG](CHANGELOG.md) · 各版发布说明见 [docs/](docs/)。

---

📖 **更多**：主页只留速览。功能↔截图对照全表、设计吸收与 PPTX 详解、测试与信任证据全表、致谢等完整内容见 [docs/HOMEPAGE-ARCHIVE.md](docs/HOMEPAGE-ARCHIVE.md)（英文 [archive](docs/HOMEPAGE-ARCHIVE.en.md)）·
[安装指南](docs/INSTALL.md) · [架构](docs/ARCHITECTURE.md) · [路线图](docs/ROADMAP.md)

欢迎提交 Issue 与 PR。设计方法受归藏、花叔 Design（本次解说片引擎 [huashu-art-motion](https://github.com/alchaincyf/huashu-art-motion)）、Archify 等社区工作启发，详见 [DESIGN-SOURCES](docs/DESIGN-SOURCES.md)。

[MIT License](LICENSE) © 2026 **KratosLee · Html九尾狐项目组**
