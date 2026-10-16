# v0.7.7 发布说明 · 改写吸收（paraphrased）+ 首启种子修复

**发布日期**：2026-10-12
**上一版**：v0.7.6（2026-10-12）
**性质**：新能力（需 LLM 才升级，**离线行为零变化**）+ 一处真实用户可触发
的前端缺陷修复。HTTP 的 page-blocks 响应新增 `paraphrased` 字段；项目数据
格式不变。

---

## 一句话

**provenance 三档补齐最后一块：配置 LLM 后，reference 类网页正文以改写
形态进入产物（预览即所得），忠实度门禁防假标签；同时修掉一个会让首启
工作台变空且被永久记住的「过早持久化」缺陷——它正是让视觉门禁超时的
真凶。不配置 LLM，改写通道与 v0.7.6 完全相同。**

---

## 三个前置决策（ROADMAP 定案记录）

| 决策 | 定案 | 理由 |
|---|---|---|
| 改写由谁做 | 配置了的 LLM（`llm.router`）；未配置/失败 → 回落 `structure_only` | LLM 是**能力升级而非能力依赖**——「离线可用」的产品承诺不被绑架 |
| 改写在哪一步 | page_blocks（审核台预览拆块时） | 用户看到并选择的就是改写后的文本——**预览即所得**；v0.7.4 的教训不允许生成时再变 |
| 忠实度如何验证 | `is_faithful`：字符三元组包含度 ≤ 0.5、长度比例 0.4–1.8、非空非原文 | 没有这条，改写通道就是带假标签的 verbatim 通道，字段级许可名存实亡 |

职责边界：`paraphrase.make_llm_rewriter` 只是运输层（调用失败归一为
None）；忠实度判定与 provenance 标注的 owner 是
`intake.page_blocks_from_candidate`（新增可选 `rewriter` 参数）。
open 许可的路径**永不调用**改写器。

---

## 使用

- **离线（默认）**：与 v0.7.6 完全一致——reference 类拆块只有结构，
  正文回落生成器自带文案。
- **配置 LLM 后**（环境变量或工作台设置，同现有 LLM 接入）：审核台
  「拆成分区」时，reference 类正文自动改写为原创表述，块标注
  `paraphrased`；产物携带的是改写文本，原文一字不现。改写调用走
  `brief_expert` 模型配置，带缓存。

---

## 门禁

| 门禁 | 拦什么 |
|---|---|
| `test_paraphrase_provenance.py`（8 条） | 忠实度门禁自身（真改过/照抄/缩写/空）；忠实改写 → paraphrased；不忠实或失败 → structure_only；open 路径零改写器调用；无改写器 = v0.7.6 行为；service 透出与掉线两态；运输层失败归一 |
| 真链验收 `verify_page_blocks_chain.py` 扩至 **17/17** | 假改写器注入 server 后走真实 HTTP：reference 拆块正文以改写形态随行，产物携带改写文本、原文一字不现 |
| 变异 `mutate_paraphrase_gates.py` | 忠实度放水 / 标签污染 / open 路径调用 / service 掉线——**4/4 CAUGHT** |

## Fixed · 首启种子被「过早持久化」杀死

boot 的六个加载器里 alliance 常常最慢，它完成后的同步延续会在**首启种子
写入之前**触发一次 `save()`——此刻画布是空的，226 字节的「空工作区」写进
localStorage，其 650ms 防抖再 PUT 到服务端；随后 `loadSaved` /
`loadRemoteWorkspace` 把空快照当成「已恢复」，种子在本次与后续每一次启动
都被杀掉。用户视角：**工作台打开是空的，且空态被永久记住**。

修复：`save()` 在 `allowNodeEnter`（初始化完成标记）之前是 no-op，boot
尾部显式落盘一次完整状态。

门禁 `tests/test_first_boot_seed.py`：route 延迟把 alliance 钉成最后完成
的加载器，确定性打开竞态窗；断言首启种子存活、服务端快照为完整 5 节点、
二次加载正确恢复。变异 `scripts/mutate_first_boot_gates.py` **1/1 CAUGHT**
（曾编码「拆 boot 尾部落盘」为第二个变异，验证 MISSED——fitAll 的相机
提交也会落盘，不构成回归，变异随之删除）。

---

## 验证

| 项 | 结果 |
|---|---|
| 全量回归（Windows 本机） | **667 passed / 4 skipped**（含本轮新增 8 条 paraphrased 门禁 + 1 条首启种子门禁；此前超时的视觉测试随首启修复转绿） |
| 真链验收 | 17/17 PASS |
| 变异验证 | paraphrased 4/4 CAUGHT；首启种子 1/1 CAUGHT |
| 发布元数据 | `check_release_version.py`：v0.7.7 一致 |

---

## 明确不在这一版

- `paraphrased` 的批量重改（用户对改写不满意时换一种说法重试）——
  预览即所得的模型下需要显式的「重新改写」交互，下一轮评估。
- C6 事件委托（有意推迟）；v0.8 方向（桌面壳等）按社区反馈另行安排。
