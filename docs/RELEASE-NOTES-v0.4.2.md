# Html九尾狐 v0.4.2 · Export Center

> 发布日期：2026-09-08
> 个人开源项目：KratosLee · Html九尾狐项目组

## 本次重点

v0.4.2 把 HTML 从“只能在浏览器里看”推进到“可以直接交付”：产物节点现在可以导出 PDF 或 PNG，并附带兼容性分析与可追溯报告。

## 新增

- 产物检查器新增“导出 PDF / PNG”。
- 自动识别 `.slide`、`[data-page]`、`.page` 等分页结构。
- Deck 可逐页导出 PNG，连续网页可导出完整长图。
- PDF 支持 A4、Letter、A3 和横向纸张；分页 Deck 使用画布尺寸。
- 支持页码范围 `1-3,5`、320–3840 像素画布和 1x / 2x / 3x 图片倍率。
- 导出前显示兼容性评分、网络资源和动态内容风险。
- 每次导出生成独立目录与 `export-report.json`，不覆盖源 HTML。
- 新增 CLI：`htmlninefox export PROJECT --format pdf|png`。

## 运行环境

- Windows 安装包优先复用系统 Microsoft Edge，也支持 Chrome。
- Linux 使用 Chromium / Chrome；缺少浏览器时返回明确安装提示。
- Docker 镜像内置 Chromium，容器内可直接导出。
- 所有导出默认在本机完成，不上传 HTML、附件或 API Key。

## 参考与边界

本版本参考 [ppt-master](https://github.com/hugohe3/ppt-master) 的路由工作流、质量门禁和交付检查思路，建立 `Analyze → Route → Render → Verify → Deliver` 流程。v0.4.2 不声称生成可编辑 PPTX；高保真 PPTX 计划在 v0.5.0 基于逐页渲染实现，可编辑 PPTX / DOCX 只面向九尾狐受控组件。

## 已知限制

- 网络字体或远程图片在离线导出时可能缺失，报告会提示。
- 视频、动画、WebGL 和持续变化的数据会冻结为当前静态画面。
- PDF / PNG 保证视觉交付，不提供元素级编辑。

## 验证结果

- `159 / 159` Python、API、存储、安全、导出与浏览器测试通过。
- `22 / 22` Chromium 真实生成、无限画布与 Export Center 验收通过。
- wheel 隔离安装后真实 PNG 导出通过。
- Windows 便携包真实 PNG 导出通过，自动复用 Microsoft Edge。
- Linux 离线包包含 x86_64 / aarch64 Playwright 与 Python 3.10–3.13 平台依赖。
- 完整证据见 [TEST-REPORT-v0.4.2.md](TEST-REPORT-v0.4.2.md)。
