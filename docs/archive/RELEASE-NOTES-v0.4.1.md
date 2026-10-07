# Html九尾狐 v0.4.1 · Release Integrity Repair

> 发布日期：2026-09-05
> 个人开源项目：KratosLee · Html九尾狐项目组

## 本次重点

v0.4.1 不继续堆功能，而是修复 v0.4.0 的发布可信度：源码、页面、CLI、API、安装包名称、Docker 标签、测试证据和 Git tag 现在由同一版本约束。

![v0.4.1 工作台](../assets/screenshots/v0.4.1/workbench-overview.png)

## 修复内容

- 版本统一为 `0.4.1`，工作台与健康接口不再显示 `0.3.0b2`。
- 新增发布元数据守卫，标签与包版本不一致时停止构建。
- Linux 安装脚本改为构建时动态注入版本。
- Windows GitHub Release 同时上传安装器和免安装 ZIP。
- Linux GitHub Release 上传 `.run`、`.tar.gz`、wheel 及 SHA256。
- 增加 Docker 独立构建 Job。
- CI 补充 `canvas-productivity.js` 语法检查。
- README 修正测试数字、失效证据链接和错误的 FastAPI 描述。

## 验证结果

- 153 / 153 Python、API、存储、安全、生成与浏览器测试通过。
- 20 / 20 Chromium 真实生成和工作台验收通过。
- Windows 便携 EXE、Linux 包和 wheel 完成真实包体冒烟验证。

完整证据见 [TEST-REPORT-v0.4.1.md](TEST-REPORT-v0.4.1.md)。

## 下载文件

- `HtmlNineFox-Setup-0.4.1.exe`：Windows 安装器，由标签 CI 构建。
- `HtmlNineFox-Windows-x64-0.4.1.zip`：Windows 免安装便携版。
- `HtmlNineFox-Linux-0.4.1.run`：Linux 用户级自解压安装包。
- `HtmlNineFox-Linux-0.4.1.tar.gz`：Linux 可审计归档。
- `htmlninefox-0.4.1-py3-none-any.whl`：Python wheel。

## 下一步：Export Center

HTML 仍然是唯一源文件。下一阶段按两条路径提供交付格式：

- 高保真分享：PDF、PNG/JPEG/WebP、PPTX 一页一图。
- 可编辑交付：受控组件映射为 PPTX，Doc / Archdoc 映射为语义 DOCX。

详细方案见 [docs/EXPORT-CENTER.md](EXPORT-CENTER.md)。

## English Summary

v0.4.1 repairs the release chain instead of adding unrelated features. Version metadata, package names, CI tags, documentation, and evidence now stay aligned. The next milestone is an Export Center for PDF, images, high-fidelity PPTX, constrained editable PPTX, and semantic DOCX.
