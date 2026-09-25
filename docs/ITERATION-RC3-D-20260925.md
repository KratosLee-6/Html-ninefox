# RC3-D 迭代记录：崩溃可恢复的 Project 提交与跨进程锁

- 日期：2026-09-25
- 关联 Issue：#4
- 代码提交：待提交（本地门禁阻塞，见「验证」末尾说明）
- 上一阶段：RC3-C 共享 Feedback / Restore / Export 用例
- 下一阶段：RC3-E 浏览器生命周期 Module

## 目标

给 Project 多文件写入建立 prepare / commit / recover 边界，让 CLI 进程与 HTTP 服务进程对同一 Project 的并发写入返回稳定冲突，并让写入中断（含进程被 kill）在下次访问时确定性恢复。

## 交付

### 1. 统一 durable 原语（`htmlninefox/durable.py` 新模块）

- `atomic_write`：同目录 mkstemp + fsync + `os.replace` + POSIX 目录 fsync；Windows 上对并发替换同一目标时的共享冲突做有界重试。`revisions.atomic_write` 改为重导出，既有 monkeypatch 范式不变。
- `acquire_file_lock / release_file_lock`：msvcrt（Windows）/ flock（POSIX）双平台文件锁，带超时与 `LockBusyError`。零新增依赖。

原先的写点全部收敛到该原语：`ProjectStore._atomic_json`（消除固定 `.tmp` 名互踩）、`ProjectMemoryStore._write`（补 fsync）、AI 设置写入、`recipe_run.write_recipe_run`、`run_expert` 的全部产物与 `.foxstate.json`（原先为裸 `write_text`）。

### 2. Project 提交 journal 与恢复

- `revisions.commit()` 三段化：prepare 写 `.commit-journal.json`（target revision、kind、parent）→ 现有顺序写入（state 写入即提交点）→ 清理 journal；补偿分支同样清理。
- `load_state()` 自愈钩子：journal 存在时在锁内恢复——state 已到 target 说明提交完成，仅清理；否则确定性回滚：`output.html` 从 `rev{current}.html` 快照字节恢复、删除大于 current 的孤儿版本文件、清理 journal（journal 损坏时按版本号兜底，行为一致）。
- 回滚而非前滚：中断的尝试被丢弃，与既有补偿语义一致；用户重试即可。

### 3. 跨进程锁

- `revisions.project_lock()` 扩展为条带 RLock（进程内）+ 线程本地深度计数 + 最外层 `<输出根>/.locks/<项目名>.lock` 文件锁（默认 15s 超时）。所有既有 `@locked_project` / `with project_lock` 调用点自动获得跨进程互斥。
- 锁文件放在 Project 目录**外**：Windows 不允许改名含打开句柄的目录，放在目录内会让 rename/delete 在持锁时死锁（本轮回归测试发现并修正）。
- 超时抛 `project_busy`（HTTP 409，消息提示稍后重试），已加入 `_REVISION_ERROR_STATUSES`，Feedback / Restore 应用层映射自动生效。
- `rename / duplicate / delete` 项目操作现也在源 Project 锁内执行，跨进程冲突得到稳定 409 而非 `PermissionError` 500。

### 4. 生成目录原子发布

`run_expert` 改为先写 `.gen-<uuid>` 临时目录（dot 前缀，不进项目列表），全部产物完成后 rename 发布为 `html9n-<ts>`，失败清理临时目录。kill 在生成中途不再留下可见的半成品项目。

## 用户可观察行为

- CLI 与服务并发操作同一 Project：后到方得到「项目正被另一个进程修改，请稍后重试」（HTTP 409 / CLI 退出码 2），可安全重试，不再交叉写。
- 提交中断（断电 / kill / 磁盘满）后首次打开项目自动恢复到上一个一致版本，幽灵版本不再出现在历史里。
- 生成失败或中断不再产生半成品项目目录。

## 验证

```text
新增 durability 测试            12 passed
全量 pytest                    234 passed, 1 skipped
Chromium 验收（restore/交互）    3 passed
```

覆盖：snapshot 后 / output 后 / state 后三个中断点回滚、journal 损坏兜底、失败提交无 journal 残留、真实子进程跨进程锁阻塞与释放、同线程嵌套持锁、HTTP 黑盒 409 project_busy、生成失败零残留、原子发布完整性、并发原子写、20 版本连续提交一致性。

说明：本轮与 RC3-C 修复两个提交因本地 Mimosa 门禁误报（已合并测试代码的 127.0.0.1 fixture 调用被判定 SSRF）暂留工作区，门禁调整后分别提交推送，Issue #4 在 CI 绿后关闭。

## 已知取舍

- 回滚而非前滚：中断提交被丢弃，用户重试。
- `run_feedback` 持锁穿过 LLM 调用（装饰器粒度）：CLI 慢 LLM 期间同项目跨进程操作得到 409 busy；收窄临界区留待后续。
- 读路径仅在 journal 存在时加锁恢复；活跃提交的毫秒级窗口内跨进程读可能短暂 409（可重试），优于读到撕裂状态。

## 后续

RC3-E：Project、Generation、Revision、Export 浏览器生命周期 Module 与竞态治理（Issue #5）。
