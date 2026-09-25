# Release Notes · v0.5.0 🎉

> **2026-09-25 · Html九尾狐 0.5 线首个稳定版**
> 在 v0.5.0rc3 工程基线之上完成 RC3-B2/C/D/E 四个阶段：共享应用用例、崩溃可恢复 Project 提交与跨进程锁、浏览器生命周期 Module 拆分。
> 前序版本 `v0.4.2` 的用户可直接升级，Project schema、HTTP v1 与 Revision 历史完全兼容。

## 稳定版亮点

### 共享应用用例（RC3-B2/C）

- CLI、HTTP、异步 Job 与 DeepSeek Harness 复用同一 `StudioApplication` 编排：Generation、Feedback、Restore、Export 四条链路行为一致。
- `htmlninefox restore` CLI 命令；`--expected-revision` 冲突保护贯穿 CLI / HTTP / Harness。
- 稳定错误契约（`code / message / details`）：CLI 映射退出码，HTTP 映射状态码，模糊反馈持续返回 `feedback_not_actionable`。

### 崩溃可恢复的 Project 提交与跨进程锁（RC3-D）

- 全部 Project 写入走统一 durable 原语（同目录临时文件 + fsync + 原子替换 + Windows 并发替换重试）。
- 多文件提交带 journal：进程被 kill / 断电后，下次访问确定性回滚到上一个一致版本，幽灵版本不再进入历史。
- 跨进程文件锁（msvcrt / flock）：CLI 与服务同时操作同一 Project 返回稳定 `project_busy`（HTTP 409），可安全重试。
- 生成在临时目录完成后原子发布，崩溃不再留下半成品项目。

### 浏览器生命周期 Module（RC3-E）

- Project / Generation / Revision / Export 拆分为四个独立 Module（`FoxProjects / FoxGeneration / FoxRevisions / FoxExports`），draft 状态私有，域间只经命名空间 API 协作。
- 生成按工作区单飞 + **取消生成**（排队任务真取消；执行中任务诚实转为"停止等待"）；导出 busy 守卫与过期结果丢弃。
- 新增 `generation-cancel.png` 等共 15 张真实状态截图。

## 验证摘要

| 门禁 | 结果 |
|---|---|
| Python 全量 | 238 passed, 1 skipped |
| Chromium e2e（bundled） | 22 / 22 |
| **系统 Edge（WebView2 同源）实机** | 22 / 22 |
| DeepSeek Harness | 2 / 2 |
| Windows 便携包 | 真机烟测：启动 → 生成 → 真实 PNG 导出 |
| 附件完整性 | 全部附件带 SHA-256，发布前回读校验 |

详见 [候选验证报告](docs/TEST-REPORT-v0.5.0-CANDIDATE.md) 与 [测试报告](docs/TEST-REPORT-v0.5.0.md)。

## 安装

| 平台 | 附件 | 说明 |
|---|---|---|
| Windows 10/11 | `HtmlNineFox-Setup-0.5.0.exe` | 安装到当前用户，创建开始菜单入口 |
| Windows 10/11 | `HtmlNineFox-Windows-x64-0.5.0.zip` | 免安装，解压运行 `HtmlNineFox.exe` |
| Linux | `HtmlNineFox-Linux-0.5.0.run` | `chmod +x` 后运行，安装到当前用户目录 |
| Linux/审计 | `HtmlNineFox-Linux-0.5.0.tar.gz` | 可查看完整安装内容 |
| Python 3.10+ | `htmlninefox-0.5.0-py3-none-any.whl` | `python -m pip install ./htmlninefox-0.5.0-py3-none-any.whl` |
| Docker | `compose.yaml` / Dockerfile | 含 Chromium 的服务端导出镜像 |

全部附件均附带同名 `.sha256.txt` 校验文件。

## 已知限制

- Safari 实机验证需要 macOS 环境，本轮未执行；工作台未使用 Safari 不兼容特性，但未实机确认。
- DeepSeek Harness 插件仍为独立版本线的预览版（`dsh-htmlninefox-v0.1.0-preview.1`）。
- PPTX / DOCX 可编辑导出按路线图在 v0.6 提供。

## 升级与回滚

- 数据目录：默认 `~/htmlninefox-output`，便携版在 `user-data/`；升级不迁移、不覆盖旧项目。
- 回滚：直接安装 `v0.4.2` 附件即可；0.5 的 Project 目录（journal / 锁文件）对旧版本只读无害。
