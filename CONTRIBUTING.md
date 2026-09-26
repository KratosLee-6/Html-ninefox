# Contributing to Html九尾狐

感谢你改进 Html九尾狐。项目当前是本地优先的 Python + 原生 Web 工作台，并包含 Playwright/Chromium 导出与 DeepSeek Harness 集成。提交前请以本文件、`CONTEXT.md` 和当前自动化门禁为准。

## 1. 准备环境

要求：

- Python 3.10+
- Node.js 22（只在验证前端语法和 DSH 插件时需要）
- Chromium（浏览器验收与 PDF/PNG 导出）

```bash
git clone https://github.com/YOUR-USERNAME/Html-ninefox.git
cd Html-ninefox
python -m venv .venv
```

Windows PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m playwright install chromium
```

macOS / Linux：

```bash
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m playwright install chromium
```

## 2. 先明确领域语言和公共 seam

开始功能或重构前：

- 阅读 [CONTEXT.md](CONTEXT.md)，沿用 Project、Workspace、Artifact、Revision、Restore、Recipe Run 等规范词。
- 阅读 [当前架构](docs/ARCHITECTURE.md)。
- 对 HTTP v1、CLI、项目格式或 Revision 行为的变更，先说明用户可观察行为和兼容策略。
- 测试应穿过与生产相同的 Interface。避免为内部实现细节写易碎测试。
- 只有出现难以逆转、缺少上下文会显得意外且存在真实取舍的决定时才新增 ADR。

## 3. 分支与提交

```bash
git checkout -b feat/short-description
# edit and test
git add <files>
git commit -m "feat: describe the user-visible change"
git push origin feat/short-description
```

提交信息使用 Conventional Commits：

- `feat:` 新能力
- `fix:` 缺陷修复
- `docs:` 仅文档
- `test:` 仅测试或测试基础设施
- `refactor:` 不改变用户行为的结构调整
- `chore:` 工具、依赖或维护
- `release:` 发布准备

不要在同一提交混入无关格式化、生成文件或本地工作区状态。

## 4. 代码约定

当前仓库的自动门禁是 pytest、版本一致性、JavaScript 语法、DSH 插件测试和 Chromium acceptance。项目尚未启用 ruff、black 或 mypy CI，因此不要把这些未配置工具描述成合并前硬门禁。

仍应遵守：

- Python 使用类型标注表达公共 Interface。
- 领域编排放在 Core / 应用用例中；HTTP、CLI 和插件只做 Adapter 转换。
- 不用 `dict[str, Any]` 扩展新的稳定跨 Module 协议；优先使用小 request/result 值对象。
- 文件写入复用项目已有可靠性 Module，不新增另一套临时文件规则。
- 原生 JavaScript 使用现有 Module 和设计令牌；不要为单个特效迁移整个前端框架。
- 动效必须可取消，遵守系统 / 减少 / 关闭偏好，并且不能成为业务成功条件。
- 公共行为、错误码、Project schema 或 HTTP v1 变化必须同步文档和兼容测试。

如果要引入 formatter、linter 或 type checker，请单独提交配置、依赖、基线修复和 CI 变更，让新门禁可以在本地真实复现。

## 5. 测试要求

按改动选择最小相关测试，然后在提交前运行完整门禁。

### Python 与浏览器测试

```powershell
python -m pytest -q -p no:cacheprovider
```

涉及浏览器用户路径或 Export 时：

```powershell
python e2e_verify.py
```

### 发布元数据与 JavaScript

```powershell
python scripts/check_release_version.py
python scripts/check_inline_js.py
node --check htmlninefox/server/static/canvas-engine.js
node --check htmlninefox/server/static/canvas-productivity.js
node --check htmlninefox/server/static/workbench-features.js
node --check htmlninefox/server/static/workbench-ui.js
node --check htmlninefox/server/static/motion-system.js
node --check htmlninefox/server/static/interaction-system.js
node --check htmlninefox/server/static/lifecycle-projects.js
node --check htmlninefox/server/static/lifecycle-generation.js
node --check htmlninefox/server/static/lifecycle-revisions.js
node --check htmlninefox/server/static/lifecycle-exports.js
node --check htmlninefox/server/static/lifecycle-intake.js
node --check htmlninefox/server/static/sw.js
```

### DeepSeek Harness 插件

仅在修改 `integrations/deepseek-harness/` 或相关 CLI 契约时运行：

```powershell
cd integrations/deepseek-harness
npm ci --ignore-scripts --no-audit --no-fund
npm test
```

### 测试应覆盖什么

- 新能力：一个成功路径和至少一个有意义的失败路径。
- Bug：先增加能捕获用户症状的回归测试，再修复。
- HTTP v1：响应字段、错误 code 和兼容行为。
- Project / Revision：失败回滚、历史保留和冲突行为。
- UI：用户可观察结果、键盘与动效关闭状态；不要只断言内部变量。
- 视觉改动：至少保存受影响 viewport 和业务状态的真实截图；新增 success、error 或 recovery 状态时，优先加入可复现的 Playwright 证据测试。
- 截图路径、命名和证据目录遵循 [`assets/screenshots/README.md`](assets/screenshots/README.md)。
- 性能：先保存基线和输入规模，再声明改善或没有退化。

测试文件当前平铺在 `tests/` 并按能力命名。请不要创建不存在的旧式 `tests/integration/` 或 `tests/security/` 结构，除非先提交并说明新的测试组织方案。

## 6. Pull Request 内容

PR 描述至少说明：

- 具体触发场景和之前的行为。
- 修改后的用户可观察行为。
- 选择的 Interface / seam，以及为何放在该 Module。
- 兼容性、数据迁移或失败恢复影响。
- 实际运行的测试命令和结果。
- UI 改动的前后截图；动效改动可附短视频或关键帧。

PR 保持单一目的。大规模重构应拆成“测试 seam → 一个纵向用例 → 后续迁移”，每一步都保持可运行。

## 7. 报告问题

Issue 请包含：

- 环境：操作系统、Python、Node、浏览器和 Html九尾狐版本。
- 精确复现步骤与最小输入。
- 预期和实际结果。
- 是否能稳定复现。
- 脱敏诊断包、错误 code、request id 或相关截图。

不要提交 API Key、项目私密正文或未脱敏的用户文件。

## 8. 参考资料

- [领域术语](CONTEXT.md)
- [当前架构](docs/ARCHITECTURE.md)
- [产品路线](docs/ROADMAP.md)
- [RC3 架构加固计划](docs/ITERATION-PLAN-POST-RC2-20260920.md)
- [mattpocock/skills 方法审计](docs/AUDIT-MATTPOCOCK-20260920.md)
- [Changelog](CHANGELOG.md)

项目采用 MIT License。参与讨论时请保持具体、耐心，并尊重用户数据与作品隐私。
