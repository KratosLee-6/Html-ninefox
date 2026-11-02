# v0.8.8 · 点选即改（所见即所得 A1）

**发布日期**：2026-11-02
**主题**：输出端「点哪里改哪里」的第一阶段——预览 iframe 里单击任意文字
直接改，Enter 保存出 rev。全部六类意图可用（deck 的幻灯片编辑自此不再
是唯一的原位编辑入口）。机主 2026-10-31 四选全的 A 项（A1 文本级 →
A2 样式级排 0.9.x）。

---

## 一、使用方式

画布选中产物节点 → 检查器 **✎ 点选编辑文字** → 预览里文字出现虚线轮廓 →
单击即整段全选 → 直接打字替换（或再点一次细定位局部修改）→ **Enter 保存**。
每次保存都是**新修订**（rev+1）：可对比、可回滚，与口语反馈共用同一套
版本机制。Esc 取消不留痕。

## 二、架构（复用为先）

| 层 | 实现 |
|---|---|
| 文本定位 | `_TextNodeMapper` 统一升级：恒收集全部可见文本（`slide=-1` 标记分区外），span 带全序列稳定 node id——点选枚举（`iter_text_nodes`）与幻灯片清单（`iter_slide_texts`）对同一 HTML 同源同号 |
| 应用编辑 | 复用 `apply_text_edits` 引擎（v0.6 为 deck 而建）——按 (slide, node id) 匹配字符跨度，原文校验后替换 |
| 并发防护 | 项目锁 + 乐观锁（`expected_revision`）+ **current 失配防护**：前端回传所见现文，服务端与映射表比对，不一致 409 拒改——枚举错位时宁可拒绝，绝不改错节点 |
| 版本 | `revisions.commit(kind="text-edit")`，走 `advanceNodeRevision` 唯一写回协议（C2） |
| HTTP | `GET /api/projects/<名>/text-nodes` · `PUT /api/projects/<名>/text` |

**实体并入文本流**：`&nbsp;` 等实体会把一个 DOM 文本节点拆成多段解析
data——mapper 以缓冲合并相邻 data/实体，按原文切片成单 span，规范化语义
与浏览器一致（`\xa0` 计入空白）；`title` 加入 SKIP（前端 walker 从 body
起步，head 文本不参与编辑）。

## 三、一致性门禁（v0.7.4 教训的直接应用）

`test_frontend_walker_matches_server_mapping`：真实渲染的 landing 里，
前端 walker（与 lifecycle-liveedit.js 同一套过滤器）与服务器映射表必须
**逐位对应**。首跑即抓到两类错位（服务器 85 vs DOM 81）：

1. `<title>` 文本被计入（head 文本不渲染）→ SKIP 增 title；
2. `&nbsp;` 把 DOM 单节点拆成服务器双 span → 实体并入缓冲。

**修完才发版**。配套端到端 UI 冒烟：注入产物节点 → 点检查器按钮 →
iframe 内点字改写 → Enter → 断言 rev1 落盘、枚举再读一致。

## 四、门禁与证据

| 门禁 | 数字 |
|---|---|
| tests/test_live_edit.py | **10 条**：landing 枚举 / 编辑往返出 rev / 恢复还原 / 过期版本 409 / 失配 409 / 越界 409 / 空 edits 400 / deck 分组回归护栏 / 浏览器一致性 / 端到端 UI 冒烟 |
| 变异验证 | 失配防护摘除 → CAUGHT；孤儿收集回退 → CAUGHT |
| 全量 | **878 passed / 4 skipped**（2026-11-02 实测） |
| 取证 | scripts/capture_v088_shots.py：进入编辑态实拍（虚线轮廓）/ 改写中 / 保存后 rev 徽章 |

## 五、安装与升级

```
pip install --upgrade "htmlninefox[all]"
```

零新依赖、零新 extra；点选即改属工作台本体能力。

## 六、排期

- **A2 样式级点选即改**（颜色/字号/间距 token 映射）：0.9.x，与 preset
  扩族的风格轴合并设计
- **多页站点（E）**：v1.0 主项
