# v0.5.0 正式版长线迭代计划

- 制定日期：2026-09-24
- 起点：`v0.5.0rc3`
- 正式版目标：`v0.5.0`
- GitHub 总追踪：Issue #2
- 推荐目标日：2026-10-21
- 发布窗口：2026-10-14 ～ 2026-10-23
- 预计投入：12～18 个有效工作日，约 3～4 周

## 阶段和时间

| 阶段 | 时间窗口 | 交付 | GitHub |
|---|---|---|---|
| RC3-B2 | 2026-09-24 ～ 09-25 | CLI / HTTP / Job / DSH 共享 Generation use case | #1 |
| RC3-C | 2026-09-26 ～ 10-02 | Feedback、Restore、Export request/result | #3 |
| RC3-D | 2026-10-03 ～ 10-10 | durable Project commit、journal、跨进程锁、崩溃恢复 | #4 |
| RC3-E | 2026-10-11 ～ 10-16 | Project、Generation、Revision、Export 浏览器生命周期 Module | #5 |
| 正式版候选 | 2026-10-17 ～ 10-20 | 实机、安装包、截图、文档、附件回读 | #6 |
| v0.5.0 发布 | 目标 2026-10-21 | Git tag、Release、SHA-256、发布后监控 | #6 |
| 风险缓冲 | 2026-10-22 ～ 10-23 | Safari/WebView2 或打包环境问题 | #6 |

## 每阶段完成条件

每个阶段必须独立完成：

1. 一个可验收的纵向用户能力。
2. 对应 seam 的成功、失败和恢复测试。
3. 全量 Python、JavaScript 与 Chromium 回归。
4. 涉及 DSH 时运行插件 tarball 测试。
5. 更新 README、ROADMAP、CHANGELOG 和迭代记录。
6. 更新 GitHub Issue，提交并推送后等待 `main` CI 成功。

## 正式版退出条件

- CLI、HTTP 与 DSH 复用同一应用用例实现。
- Project 多文件写入有 prepare、commit 和 recover 边界。
- 同一 Project 的跨进程写入返回稳定冲突或安全重试。
- 20 revisions 与 100 nodes / 99 edges 持续使用不退化。
- Safari 与 WebView2 完成核心路径实机验证。
- Windows、Linux、wheel 与 Docker 构建和真实启动验证通过。
- Release 附件、SHA-256、截图、README 和版本号完全一致。

## 可能影响日期的外部条件

- Safari 实机需要可用的 macOS / Safari 环境。
- WebView2 需要 Windows 安装包实机回归。
- DSH 对话自动选用技能需要可用的 Harness 运行环境。
- 真实在线模型验收需要用户自行配置的模型凭证；离线能力不依赖凭证。

若外部环境按时可用，优先在 2026-10-21 发布；若实机或打包门禁发现问题，使用至 2026-10-23 的缓冲，不带已知数据一致性问题发布稳定版。
