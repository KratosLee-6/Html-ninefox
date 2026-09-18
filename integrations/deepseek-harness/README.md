# Html九尾狐 for DeepSeek Harness

`dsh-htmlninefox` · `0.1.0-preview.1` · MIT

在 Harness 中发现并加载 `htmlninefox` 创作技能，通过已有命令工具调用九尾狐，完成单文件 HTML 生成、反馈迭代与 PDF / PNG 导出。英文请求也可使用。

这是原生 Cordis **技能工作流插件**。当前没有独立的 `htmlninefox_generate` 工具、聊天内预览卡片或 MCP 服务；Python 应用需单独安装。插件不联网、不自动安装依赖、不收集遥测。此预览版源码在本仓库，**尚未发布 npm 或 GitHub Release 资产**。

## 安装

需要 Node.js 22+、可用的 DeepSeek Harness、Python 3.10+ 和 Git。首次安装 Python 应用建议使用虚拟环境。以下示例固定了已通过九尾狐 CI 的应用提交与本插件验证使用的 Harness 版本：

```sh
python -m pip install "git+https://github.com/KratosLee-6/Html-ninefox.git@72e08732c9cfa964edba6ef4de99e6d2afaa17e5"
htmlninefox version
npm install -g @deepseek-ai/dsh@0.1.5-rc.2
git clone https://github.com/KratosLee-6/Html-ninefox.git
cd Html-ninefox
dsh --profile fox-demo --from-default-profile web --dump-config
dsh plugin --profile fox-demo add ./integrations/deepseek-harness
dsh --profile fox-demo --dump-config
dsh --profile fox-demo
```

先从 `web` 模板建立新的 `fox-demo` profile，才能直接获得 Web 界面；若该名称已存在，请换一个新的 profile 名称。仅运行 `plugin add` 创建的默认 profile 只包含 base。无需再从 npm 单独安装内置 Web bundle。

在 Web UI 完成模型配置后，输入：

> 使用 htmlninefox 技能，离线规则生成一张中文活动海报，把产物保存到 ./fox-output。

Harness 自身对话需要模型配置；九尾狐的 `--quiet-llm` 仅表示其 Python 生成阶段不额外调用模型。插件安装后不会自动启动九尾狐工作台，也不共享 Harness API Key。

已安装的 profile 卸载插件：

```sh
dsh plugin --profile fox-demo remove dsh-htmlninefox
```

## 打包与分发

在插件目录执行：

```sh
npm ci --ignore-scripts
npm test
npm pack --ignore-scripts
```

得到 `dsh-htmlninefox-0.1.0-preview.1.tgz`，用户在文件所在目录安装：

```sh
dsh plugin --profile fox-demo add ./dsh-htmlninefox-0.1.0-preview.1.tgz
```

包内是直接可运行的 ESM JavaScript，没有安装脚本、构建脚本或运行依赖；测试依赖不进入生产安装。可将此 `.tgz` 上传到**本项目 GitHub Release 的附件区**。发布 npm 前先确认包名可用和 npm 账号归属，再执行 `npm publish --tag preview --access public`；发布成功后才可使用 `dsh plugin --profile fox-demo add dsh-htmlninefox@0.1.0-preview.1`。

不要使用 `dsh plugin add github:KratosLee-6/Html-ninefox`：仓库根目录是 Python 项目，不是这个 npm bundle。若以后建立独立插件仓库，把本目录文件放在仓库根目录，才可使用官方文档的 `github:owner/repo#commit` 安装方式。

## 验证范围

`npm test` 使用真实 `@deepseek-ai/cordis@4.0.2` 和 `@deepseek-ai/dsh-skill@0.1.5-rc.2`，验证发现、加载、重载、卸载以及 tarball 安装后的资源读取（含中文与空格路径）。这不代表已经验证真实模型选用技能或所有 Harness 版本；完整验收还应在用户实际配置的 Harness 会话完成生成 → 修改 → 导出。

## 反馈

请在 [九尾狐 Issues](https://github.com/KratosLee-6/Html-ninefox/issues) 提交系统、Harness / 插件 / 九尾狐版本、复现步骤、预期与实际结果及脱敏日志。插件不会自动发送用户提示词和产物。路线与官方来源见 [接入调研](../../docs/DEEPSEEK-HARNESS-INTEGRATION.md)。
