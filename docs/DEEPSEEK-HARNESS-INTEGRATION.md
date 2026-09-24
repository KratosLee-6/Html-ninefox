# DeepSeek Harness 接入调研与首版交付

日期：2026-09-18。插件版本：`dsh-htmlninefox@0.1.0-preview.1`。

## 决策

建议做轻量生态入口：让 Harness 用户在对话中发现九尾狐，完成 HTML 生成、反馈迭代和 PDF / PNG 导出。先收集安装成功率、首份产物完成率、反馈修改是否有效及导出失败原因，再决定是否投入结构化工具、聊天内预览或独立插件仓库。GitHub topic 可以帮助发现，但不能保证安装量或反馈量。

首版是原生 Cordis **技能工作流插件**：`apply(ctx)` 调用 `ctx.skills.register()`，由 Harness 现有技能工具加载指令，再使用宿主命令工具调用 Python CLI。它不是仅改名的 Codex 插件，也没有增加专用生成工具或 MCP server。九尾狐 Python 应用和导出浏览器独立安装；Harness 的模型凭据不会自动传入九尾狐。

## 官方规则与上传位置

依据官方仓库提交 `ddefc45fbc7f8e46dd73185e68295696d1297887` 查阅；实现另用已发布的 Harness `0.1.5-rc.2` 验证。官方 HEAD 当时已是 `0.1.6-alpha.2`，不能把源码 HEAD 和 npm latest 当成同一版本。

| 项目 | 已核实规则 | 九尾狐选择 |
| --- | --- | --- |
| 插件入口 | ESM JS / TS 模块导出 `apply`，用 `inject` 声明服务依赖 | 纯 JS，注入 `skills` |
| 可安装插件 | `package.json` 声明 `dsh.bundle.patch`，YAML patch 插入插件行 | 独立子目录，包名 `dsh-htmlninefox` |
| 发布代码 | 作者自己的 GitHub 仓库 | 当前 `Html-ninefox/integrations/deepseek-harness` |
| 可下载安装包 | 官方支持本地 tarball | `.tgz` 与 SHA-256 已上传本仓库插件预览 Release |
| 包注册表 | npm 可选，非唯一渠道 | 尚未发布；发布前核验名称归属，使用 `preview` 标签 |
| GitHub 安装 | git 依赖必须是可解析的 npm 包；TS 构建需 prepare 与用户授权 | 本目录直接运行 JS；当前根仓库是 Python 项目，不能用裸 `github:owner/Html-ninefox` 安装 |
| 被发现 | 官方建议仓库 topic `dsh-plugin` | 已添加 `dsh-plugin`、`deepseek-harness`；README 提供安装与反馈入口 |
| 向官方贡献 | 官方目前不接受外部 PR | 不向官方仓库提交插件 PR；用户问题走自己的 Issues，Harness 本身问题可到官方 Discussions |

源码、Release 资产和 npm 包是三个独立的发布动作。当前已发布源码、插件标签、GitHub Release 安装包及校验文件，并添加官方建议的 topic。npm 尚未发布：本机对官方 npm 注册表运行 `npm whoami` 返回 `ENEEDAUTH`，需要维护者登录账号；这不影响使用 DSH 官方支持的 tarball 安装。未建立独立插件仓库，也未向官方发布推广帖。

## 创建步骤与目录

```text
integrations/deepseek-harness/
  package.json          # dsh.bundle 元数据、包版本和打包白名单
  cordis.patch.yml      # 插入 dsh-htmlninefox 行
  index.js              # 注册技能，使用模块路径定位资源
  workflow.md           # 生成 / 修改 / 导出指令和适用边界
  README.md             # 安装、分发、验证范围和反馈入口
  LICENSE
  package-lock.json     # 固定测试依赖
  test/plugin.test.js   # 真实 Cordis / Harness 注册表与打包安装测试
```

包无需构建，生产环境无 npm 运行依赖、无安装脚本。`npm ci --ignore-scripts && npm test` 验证后，`npm pack --ignore-scripts` 生成 `dsh-htmlninefox-0.1.0-preview.1.tgz`。完整安装命令在 [插件 README](../integrations/deepseek-harness/README.md)。

在新的 Web profile 安装（先安装好 `dsh`）：

```sh
dsh --profile fox-demo --from-default-profile web --dump-config
dsh plugin --profile fox-demo add ./integrations/deepseek-harness
dsh --profile fox-demo --dump-config
dsh --profile fox-demo
```

此命令假定 cwd 是九尾狐仓库根目录。已有同名 profile 时换新名称。单独执行 `plugin add` 初始化的是 base profile，不自动包含 Web 界面。

## 本轮验证

| 验证 | 结果 |
| --- | --- |
| 真实 Cordis 4.0.2 + dsh-skill 0.1.5-rc.2 技能发现 / 读取 / 重载 / 卸载 | 通过 |
| `npm pack` 后在独立中文空格路径安装，读取包内资源 | 通过；2 项 Node 集成测试均通过 |
| 真实 `dsh plugin --profile ... add` | 通过；profile bundle 列表包含插件 |
| 从 `web` 模板创建 profile 并 `--dump-config` | 通过；Web 与九尾狐配置均存在 |
| Harness Web 启动 | 成功监听本机测试端口；未携带 token 的 HTTP 请求被鉴权拒绝，符合预期；未完成登录后 UI / 模型会话验收 |
| CLI 离线中文海报 → dry-run → 修改 → PDF → 长 PNG | 通过；产物 `document.pdf` 168130 字节、`full-page.png` 1030088 字节；两项兼容性报告均为 100 分 |
| 用户指定两组 pytest | **14 passed，12.10 秒** |
| 内联 JS 与 canvas-productivity / canvas-engine / workbench-features 语法 | 通过 |

测试 profile 使用隔离的 `.codex_tmp/harness-home`；本次没有修改用户现有 Harness 配置。测试服务已停止。没有调用付费模型，因此尚未验证“真实模型主动选用技能”的完整会话，也不宣称跨版本兼容。

安装过程发现的环境问题：直接另装内置 Web bundle 会遇到其依赖的构建策略拦截；最终使用官方 `--from-default-profile web` 复用内置组合，已成功。机器全局旧版 Python 包缺少 `export`，从本项目源码执行完整链路成功；插件指令已增加版本和导出命令检查，并固定已通过 CI 的应用源码安装版本。

CI 已加入插件测试步骤，与现有 Python / Chromium 验收一起运行。本轮未修改项目已有、尚未提交的 `SKILL.md` → `skill/` 迁移。

### GitHub 交付核验

- 源码已推送 `main`：[6dea899](https://github.com/KratosLee-6/Html-ninefox/commit/6dea8996ec125aefc1c60a1b69ec7e28d50c0ac2)。
- [GitHub Actions #35350016631](https://github.com/KratosLee-6/Html-ninefox/actions/runs/35350016631)：**success**。
- Linux / Node.js 22：插件 **2 项通过**；Python / 浏览器 **197 passed，61.80 秒**；Chromium 端到端 **22/22 通过**。
- 此段为 CI 通过后的文档追记；npm、Release 附件和 `dsh-plugin` 仓库 topic 尚未发布或修改。

### 正式执行插件预览发布（2026-09-18）

- [公开 Release](https://github.com/KratosLee-6/Html-ninefox/releases/tag/dsh-htmlninefox-v0.1.0-preview.1)：非草稿、预览发布；插件标签为 `dsh-htmlninefox-v0.1.0-preview.1`，指向提交 `2de697f`。
- 附件：`dsh-htmlninefox-0.1.0-preview.1.tgz`（6124 字节）及 `SHA256SUMS.txt`。
- 安装包 SHA-256：`a00fbece75ef02fce190d2e5af03e2f83b92944bb74ca79b676174172d24f431`。
- 发布前再次执行插件集成测试，**2/2 通过**；用真实 DSH `0.1.5-rc.2` 将最终 tarball 安装进新的 Web profile，`--dump-config` 正确显示插件层。
- 发布后重新下载两个附件，校验和与本地已测试包完全一致；GitHub API 记录的附件 digest 一致。
- GitHub 仓库 topics 已核验包含 `dsh-plugin` 与 `deepseek-harness`。
- 使用独立插件标签及 `--latest=false`，主应用的 GitHub Latest Release 仍为 `v0.4.2`。
- 本次仅变更发布文档，运行代码沿用上节通过完整 CI 的实现；未修改此前已有的 Skill 迁移。

### 发布页截图与首页补全（2026-09-18）

- Release 新增 `harness-plugin-enabled.png`：最终 tarball 安装后的 DSH Web 插件列表，显示 `htmlninefox` 为启用中的全局插件。
- Release 新增 `generated-poster.png`：同轮离线生成、反馈修改并导出的完整 PNG；对应 PDF / PNG 兼容性均为 100 分。
- 两张图片都作为 Release 资产上传，并嵌入发布正文；GitHub API 返回各自的 SHA-256 digest。
- 项目中保留[截图来源与实测表](test-evidence/harness-plugin-20260918/README.md)，首页同时展示 DSH 状态、生成结果、版本恢复和动效实验室四张真实截图。
- 首页已改为完整开发快照，补齐功能矩阵、版本口径、最新 CI、当前限制和下载入口；原先指向不存在 `v0.5.0rc1` Release 的链接已修正为稳定应用 `v0.4.2` 与独立 DSH 插件预览版。
- 首页补全提交首次 CI 暴露旧发布门禁强制要求未发布的 `v0.5.0rc1` Release 链接。校验已调整为：日常开发分支要求 README 明示源码版本；只有真正构建 `v*` 应用标签时，才要求匹配的 Release 链接。新增 2 项回归测试，确保删除假链接不会削弱正式标签检查。
- 最终 [GitHub Actions #35353907293](https://github.com/KratosLee-6/Html-ninefox/actions/runs/35353907293) 全部通过：发布元数据门禁、插件 2/2、Python / 浏览器 **199 passed，64.24 秒**、JavaScript 语法与 Chromium **22/22**。

## 反馈与下一步

### 与应用 v0.5.0rc3 的版本边界

- 主应用现已进入 [`v0.5.0rc3`](https://github.com/KratosLee-6/Html-ninefox/releases/tag/v0.5.0rc3) 预发布，提供 Windows、Linux 与 Python 安装包。
- DSH 插件仍为独立的 `dsh-htmlninefox@0.1.0-preview.1`，插件 Release 只包含 `.tgz`、校验文件和实测截图。
- 应用升级不会自动安装或升级 DSH 插件；插件通过宿主命令调用本机已安装的九尾狐 CLI。
- npm 发布仍暂缓，GitHub tarball 是当前经过验证的插件安装渠道。

1. 小范围试用：用户在自己的 Harness 配置下完成海报 / deck / dashboard 各一个，报告安装、生成、修改、导出的结果。
2. `.tgz` Release 附件已发布；后续插件更新递增独立版本，重新测试并生成校验文件。
3. 验证实际需求后，增加结构化工具：生成、反馈、导出分别注册 `ctx.tools`，处理取消、并发、路径边界和清晰错误。
4. 用户需要频繁安装时，再考虑独立仓库或 npm；有预览需求后再接 Harness 客户端扩展。

反馈入口是 [九尾狐 Issues](https://github.com/KratosLee-6/Html-ninefox/issues)。推荐包含版本、系统、复现步骤、预期/实际结果与脱敏日志；不自动上传内容或收集遥测。

## 官方来源

- [README：开发者预览与社区发现](https://github.com/deepseek-ai/deepseek-harness/blob/ddefc45fbc7f8e46dd73185e68295696d1297887/README.md)
- [Contributing：暂不接受外部 PR；使用 dsh-plugin topic](https://github.com/deepseek-ai/deepseek-harness/blob/ddefc45fbc7f8e46dd73185e68295696d1297887/CONTRIBUTING.md)
- [第一个插件](https://github.com/deepseek-ai/deepseek-harness/blob/ddefc45fbc7f8e46dd73185e68295696d1297887/docs/user/develop/basic/index.zh.md)
- [打包与安装：bundle、profile、npm、GitHub、tarball](https://github.com/deepseek-ai/deepseek-harness/blob/ddefc45fbc7f8e46dd73185e68295696d1297887/docs/user/develop/basic/publish.zh.md)
- [技能服务及注册契约](https://github.com/deepseek-ai/deepseek-harness/blob/ddefc45fbc7f8e46dd73185e68295696d1297887/docs/subsystems/skills.zh.md)
- [工具开发教程](https://github.com/deepseek-ai/deepseek-harness/blob/ddefc45fbc7f8e46dd73185e68295696d1297887/docs/user/develop/basic/tool.zh.md)
