# Html九尾狐 v0.4.1 测试与发布候选报告

> 验证日期：2026-09-05
> 结论：源码、CLI、API、wheel、Windows 便携包和 Linux 包版本已统一为 `0.4.1`。

## 自动化验证

| 项目 | 结果 | 证据 |
|---|---:|---|
| Python / API / 存储 / 安全 / 浏览器测试 | 153 / 153 passed | [pytest 原始日志](test-evidence/v0.4.1-pytest.txt) |
| Chromium 真实生成与工作台验收 | 20 / 20 passed | [E2E 原始日志](test-evidence/v0.4.1-chromium-e2e.txt) |
| JavaScript 语法 | 3 / 3 passed | [语法检查记录](test-evidence/v0.4.1-js-syntax.txt) |
| 发布元数据一致性 | passed | `python scripts/check_release_version.py --tag v0.4.1` |

## 包体验收

| 包体 | 结果 |
|---|---|
| Python wheel | 安装成功，CLI 返回 `v0.4.1`；76 个条目，工作台核心资源完整 |
| Windows 便携 ZIP | EXE 启动成功；健康接口返回 `0.4.1` 和 `windows-portable`；模板库可访问 |
| Linux `.run/.tar.gz` | 归档结构正确；`APP_VERSION=0.4.1` 构建时注入；wheel 已包含 |
| Windows Setup EXE | 本机缺少 Inno Setup，交由标签 CI 构建并生成 SHA256 |
| Docker | 本机 Docker daemon 未启动，交由标签 CI 的独立 Docker Job 验证 |

包体冒烟记录见 [v0.4.1-package-smoke.txt](test-evidence/v0.4.1-package-smoke.txt)，本地生成包校验值见 [v0.4.1-release-sha256.txt](test-evidence/v0.4.1-release-sha256.txt)。

## 发布链修复

- `pyproject.toml` 与 `htmlninefox.__version__` 统一为 `0.4.1`。
- CLI 帮助、健康接口、Docker 标签和安装文档跟随同一版本。
- Linux 安装脚本不再硬编码版本，构建时从 `pyproject.toml` 注入。
- 标签构建会拒绝与项目版本不一致的 Git tag。
- Windows 发布上传包含安装器和便携 ZIP；Linux 上传包含 `.run`、`.tar.gz`、wheel 和校验值。
- CI 补充 `canvas-productivity.js` 语法检查和 Docker 镜像构建。

## 已知边界

- Windows Setup EXE 和 Docker 镜像必须在推送 `v0.4.1` 标签后由 GitHub Actions 最终确认。
- 本次是发布可信度修复，不包含 Project Memory、Recipe Run 或 Office 导出实现。
- Office 导出方案见 [Export Center](EXPORT-CENTER.md)。

## English Summary

The v0.4.1 candidate passes 153 Python tests and 20 Chromium acceptance checks. The wheel, Windows portable package, and Linux packages were built and smoke-tested locally. The Windows installer and Docker image are intentionally verified by tag-triggered CI, where the release tag must match the package version.
