# Html九尾狐 v0.4.2 测试报告

> 验证日期：2026-09-08
> 范围：Export Center、无限画布、生成链路、发布包与离线依赖

## 结论

本次 v0.4.2 验收通过。PDF / PNG 导出中心已达到可交付状态：HTML 保持唯一源文件，导出前执行兼容性分析，导出后生成独立文件与 `export-report.json`。

## 自动化结果

| 验证项 | 结果 | 原始证据 |
|---|---:|---|
| Python / API / 存储 / 安全 / 导出 / 浏览器测试 | **159 / 159** | [v0.4.2-pytest.txt](test-evidence/v0.4.2-pytest.txt) |
| Chromium 生成、画布交互与导出中心 E2E | **22 / 22** | [v0.4.2-chromium-e2e.txt](test-evidence/v0.4.2-chromium-e2e.txt) |
| JavaScript 语法 | **4 / 4** | [v0.4.2-js-syntax.txt](test-evidence/v0.4.2-js-syntax.txt) |
| 发布包冒烟 | **通过** | [v0.4.2-package-smoke.txt](test-evidence/v0.4.2-package-smoke.txt) |
| 本地候选发布文件 SHA256 | **已记录** | [v0.4.2-release-sha256.txt](test-evidence/v0.4.2-release-sha256.txt) |

## Export Center 覆盖

- 自动识别 `.slide`、`[data-page]`、`.page` 分页结构。
- PDF 支持分页 Deck、A4 / Letter / A3 与横向纸张。
- PNG 支持逐页、指定页码、完整长图与 1x / 2x / 3x。
- 导出前报告网络资源、动画、音视频与 WebGL 静态化风险。
- 导出任务通过异步 JobManager 执行，下载接口返回正确 MIME 与附件文件名。
- 工作台 Export Center 的格式联动、参数显隐、任务状态和下载入口完成真实浏览器验收。

## 发布包验证

- **Python wheel**：对 `release/htmlninefox-0.4.2-py3-none-any.whl` 隔离安装后真实导出 PNG 成功。
- **Windows 便携 ZIP**：`HtmlNineFox.exe` 启动后真实导出 PNG 成功，并自动复用 Microsoft Edge。
- **Linux `.run/.tar.gz`**：归档结构校验通过，包含 x86_64 / aarch64 Playwright wheel，以及 CPython 3.10–3.13 的 PyYAML / greenlet。
- **Docker**：Dockerfile 内置 Chromium，标签发布工作流执行容器运行时冒烟。

本报告中的 SHA256 对应本地候选包；正式 GitHub Release 由标签 CI 重建，并随资产发布对应的 `.sha256.txt`。

## 已知边界

- 动画、视频、音频和 WebGL 导出为静态画面。
- 网络字体和远程图片在离线环境可能缺失，兼容性报告会明确提示。
- v0.4.2 的 PDF / PNG 目标是视觉交付，不承诺元素级编辑。高保真 PPTX 与受控可编辑 Office 导出分别规划在 v0.5.0 和 v0.6.0。

## 可复现命令

```bash
python -m pytest tests -q -p no:cacheprovider
python e2e_verify.py
python scripts/check_inline_js.py
python scripts/check_release_version.py --tag v0.4.2
```
