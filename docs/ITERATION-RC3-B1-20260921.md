# RC3-B1 共享工作台测试 Server Fixture 迭代记录

- 日期：2026-09-21
- 分支：`main`
- 应用基线：`v0.5.0rc2`
- 阶段计划：[RC3 架构加固](ITERATION-PLAN-POST-RC2-20260920.md)
- 前置审计：[mattpocock/skills 工程审计](AUDIT-MATTPOCOCK-20260920.md)

## 结论

RC3-B1 已完成。13 个直接启动 Html九尾狐工作台 `ThreadingHTTPServer` 的测试文件已迁移到统一的 pytest fixture。共享 Adapter 现在集中管理临时输出目录、随机端口、base URL、后台线程和异常清理，测试继续通过 HTTP 与浏览器公共行为验证产品，没有修改 HTTP v1、Project schema 或用户交互。

迁移同时暴露并修复了一个测试顺序依赖：`TestWebApi.test_projects_listed` 过去依赖前一个测试预先生成 dashboard。该测试现在自行调用 `/api/generate`，再按本次返回的 `project_name` 和 `dashboard` intent 验证项目列表。

## 共享 Interface

`tests/conftest.py` 提供 context-managed `workbench_server`：

```python
with workbench_server as server:
    base = server.base_url
    output_root = server.output_root
```

生命周期契约：

- 每个测试使用 pytest `tmp_path` 作为隔离的 `_OUTPUT_ROOT`。
- server 绑定本机随机端口，调用方只消费 `base_url`。
- 正常结束和异常退出都会关闭 server、回收线程并恢复原 `_OUTPUT_ROOT`。
- 清理会检查线程是否在 3 秒内退出；遗留线程会让测试明确失败。
- server 构造或线程启动失败时也会恢复全局状态并关闭已创建的 socket。

Fixture 返回 context manager，而不是在 fixture setup 阶段自动启动，使浏览器 fixture、class autouse fixture 和 API fixture 都能组合同一 Adapter，同时保留各测试原有主体缩进和资源作用域。

## 迁移范围

以下 13 个文件已移除重复的工作台 server 启停样板：

1. `tests/test_alliance_cli_server.py`
2. `tests/test_canvas_interaction_beta.py`
3. `tests/test_canvas_p1_beta.py`
4. `tests/test_canvas_productivity.py`
5. `tests/test_canvas_project_delete.py`
6. `tests/test_exports.py`
7. `tests/test_interaction_system.py`
8. `tests/test_motion_system.py`
9. `tests/test_project_memory_rc1.py`
10. `tests/test_rc2_revision_accessibility_performance.py`
11. `tests/test_recipe_run_beta2.py`
12. `tests/test_server_project_api.py`
13. `tests/test_workbench_creation_flow.py`

`tests/test_llm_runtime_settings.py` 保留自己的 `ThreadingHTTPServer`。它实现的是独立 OpenAI-compatible 假服务，使用测试专属 Handler，不读取工作台 `_OUTPUT_ROOT`，生命周期和协议边界均不同；合并它会把两个独立 Adapter 错误耦合。

## 验证结果

| 门禁 | 结果 |
|---|---:|
| 13 个迁移文件定向 pytest | **63 passed，80.22 秒** |
| 完整 pytest | **198 passed, 1 skipped，87.86 秒** |
| Python 静态编译 | **通过** |
| 直接 server 生命周期引用扫描 | **仅共享 fixture 与独立 LLM 假服务保留** |
| 发布元数据一致性 | **`v0.5.0rc2` 通过** |
| 内联 JavaScript | **通过** |
| 6 个独立 JavaScript 文件 `node --check` | **通过** |
| Chromium 真实生成与交互验收 | **22 / 22 通过** |

pytest 跳过项仍是 Windows 当前环境没有创建符号链接权限的既有条件。Chromium 验收在受限环境中无法写入用户级 `~/.htmlninefox` cache；相关缓存写入按设计非阻塞，22 项产品行为全部通过。

## 影响与边界

- 没有新增生产依赖。
- 没有改变 endpoint、响应字段、状态码、Project 文件格式或浏览器行为。
- 统一 fixture 只服务 Html九尾狐工作台 HTTP seam，不吸收其他协议的测试 server。
- 每个测试仍获得独立输出目录，避免项目、记忆、任务和导出记录跨测试泄漏。

## 下一步：RC3-B2 Design It Twice

下一轮比较两个真实生成用例方案：

1. 函数式 `generate(request, deps) -> result`
2. `StudioApplication(deps).generate(request) -> result`

比较将使用 CLI、HTTP 和 DeepSeek Harness 三个现有 Adapter，评估 Interface 表面积、依赖注入、稳定错误模型、Recipe Run / Project Memory 保真度和测试成本。选定方案后先交付一个生成用例纵向切片，再决定是否需要 ADR。
