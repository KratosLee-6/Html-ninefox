# Html九尾狐 v0.3.0 Beta 2

> **默认中文说明 · English notes below**
> 个人开源项目 by **KratosLee · Html九尾狐项目组**

这是 Html九尾狐第一次把“真实模板库、多模态需求入口、AI 自主配置、无限画布组合和跨平台安装包”完整连接起来的公开 Beta。

![工作台总览](https://raw.githubusercontent.com/KratosLee-6/Html-ninefox/v0.3.0b2/assets/screenshots/v0.3.0b2/workbench-overview.png)

## 本版重点

- **6 套真实 HTML 模板 / 34 个页面**：支持完整预览、页面切换、整套加入与单页抽取。
- **文字、文件、图片统一输入**：执行“分析 → 推荐组合 → 直接生成 / 自定义编排”。
- **用户自主 AI 配置**：支持 OpenAI-compatible、Ollama 与自定义接口；Key 只保存在本地。
- **无限画布工作区**：支持整体拖动、重命名、颜色、多工作区、吸附和节点连接。
- **离线规则引擎**：没有 API Key 或 AI 不可用时仍能完成分析与生成。
- **跨平台交付**：Windows 便携版/安装器、Linux `.run/.tar.gz` 和 Python wheel。
- **个人项目署名**：当前源码和 Beta 2 包统一为 `KratosLee · Html九尾狐项目组`。

## 产品证据

| 需求分析与推荐 | 模板完整预览 |
|---|---|
| ![需求分析](https://raw.githubusercontent.com/KratosLee-6/Html-ninefox/v0.3.0b2/assets/screenshots/v0.3.0b2/guided-creation.png) | ![模板预览](https://raw.githubusercontent.com/KratosLee-6/Html-ninefox/v0.3.0b2/assets/screenshots/v0.3.0b2/gallery-preview.png) |

| AI 模型配置 | 夜蓝主题 |
|---|---|
| ![AI 设置](https://raw.githubusercontent.com/KratosLee-6/Html-ninefox/v0.3.0b2/assets/screenshots/v0.3.0b2/ai-settings.png) | ![夜蓝主题](https://raw.githubusercontent.com/KratosLee-6/Html-ninefox/v0.3.0b2/assets/screenshots/v0.3.0b2/workbench-night.png) |

## 下载选择

- **普通 Windows 用户**：优先下载 `HtmlNineFox-Setup-0.3.0b2.exe`。
- **Windows 免安装**：下载 ZIP，解压后双击 `HtmlNineFox.exe`。
- **Linux 用户**：下载 `.run`；需要审计安装内容时下载 `.tar.gz`。
- **Python 用户**：下载 `.whl`，使用 `pip install` 安装。

所有文件均提供对应的 `.sha256.txt`，完整校验值见 `SHA256SUMS.txt`。

## 测试结果

- **146/146 pytest passed**
- **20/20 Chromium E2E passed**
- 五类真实产物生成成功
- 两轮反馈迭代成功
- 工作区拖动、重命名、颜色、多工作区、双主题通过
- 工作台无 JavaScript 页面错误
- Windows 冻结版健康检查与 6 套图库通过

详细证据：[测试报告](https://github.com/KratosLee-6/Html-ninefox/blob/v0.3.0b2/docs/TEST-REPORT-v0.3.0b2.md)

## 已知状态

这是 Beta 版本。Windows 与 Linux 包已可用；Web/PWA 可从 macOS、iOS 和移动浏览器访问。原生 macOS、iOS、Android 与小程序仍在路线图中。

---

# English Release Notes

This is the first public beta that connects the real HTML template gallery, multimodal requirement input, user-managed AI configuration, infinite-canvas composition, revision history, and cross-platform packages into one complete workflow.

## Highlights

- **Six real HTML templates and 34 extractable pages** with full-work preview and page-level reuse.
- **Text, file, and image input** followed by analysis, recommendation, direct generation, or custom composition.
- **Bring your own AI endpoint** via OpenAI-compatible APIs, Ollama, or custom compatible services.
- **Offline rules remain available** when no API key is configured.
- **Infinite canvas workspaces** with movement, rename, colors, navigation, snapping, and node connections.
- **Windows, Linux, and Python packages** with SHA256 checksum files.
- Personal project attribution is consistently set to **KratosLee · Html九尾狐项目组**.

## Verification

- **146/146 pytest tests passed**
- **20/20 Chromium acceptance checks passed**
- Real landing, dashboard, deck, poster, and architecture-document outputs generated successfully
- Two revision flows passed
- Frozen Windows health and six-item gallery checks passed

See the full [test report](https://github.com/KratosLee-6/Html-ninefox/blob/v0.3.0b2/docs/TEST-REPORT-v0.3.0b2.md).
