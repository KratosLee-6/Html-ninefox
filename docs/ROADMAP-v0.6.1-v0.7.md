# 迭代计划 · v0.6.1 → v0.7

> 建立时间：2026-10-02
> 基线：`v0.6.0` tag `d36bcb3`（2026-10-01 发布）· main `11c687c2`
> 本文件是**经过核实**的排期基线。每项进排期前必须先核实现状——
> 历史上 `ROADMAP.md` §10 与 `PLAN-v0.6.0` §七-C 都曾把已完成或已撤回的条目列为待办。

---

## 一、为什么产品排期和内容排期是同一条线

账号数据（`_账号数据` + `07_.../06_基于数据的方向调整_2026-09-14.md`）：

> HTML九尾狐 3 篇合计曝光 5,987（52.8%）、观看 923（69.4%）、收藏 31（55.4%）。
> 「终于能直接安装了」点击率 19.40%——用户更愿意点击一个**明确、可感知、已经做成的结果**。

一个产品系列撑起账号一半以上流量。因此「迭代产品」与「做内容」不是两件事：
内容的说服力来自产品真的做到位，产品做完也必须有素材能讲。

**推论**：打磨型改进（"更准""效果更好"）在点击上天然吃亏。优先做**能做成新事情**的版本。

---

## 二、v0.6.1 · 修两个真缺陷（约 1 周）

只做两件，每件都配反向验证门禁。产出：tag `v0.6.1` + 一篇小红书。

### C3 · 幻灯片竞态守卫（唯一可复现的用户可见缺陷）

**已核实**：`lifecycle-slides.js` 只有 `draft.busy`（L42 / L54 / L72），无 token / seq / stale 守卫。保存进行中切换弹窗，上一个 deck 的 revision 号会写进新 deck 的节点。

C2 已在 `await` 前锁 `draft.nodeId`，堵了一半。

**做**：补 stale 守卫 + 回归门禁（去掉守卫必须变红）。

### C4 · 推荐与生成静默漂移

**已核实**：`_prompt_and_inputs`（`app.py:351`）与 `_prepare_generation`（`application.py:638`）逐字复制并存；两边测试各断言一半，**无任何断言要求两者一致**。工作台展示的版式可以和实际生成的悄悄不一样。

**做**：先加一条一致性断言把当前行为固定住（此时它可能变红，暴露既有漂移），再谈收敛。**本轮不删重复代码。**

> ### 1.2 实测结论（2026-10-02）：**绿**
>
> 新增 `tests/test_prompt_path_consistency.py`，5 条用例全通过。结论是：**两条路径在合法输入上产出完全一致**，当前并不存在已发生的漂移。四处被列为「差异」的写法，实际影响如下：
>
> | 差异 | 实测影响 |
> |---|---|
> | `str(item)` 强转只在 adapter 侧 | 只对非字符串 id 有意义。`GenerationRequest.input_ids` 类型是 `tuple[str, ...]`，而 `InputStore.describe` 本身按 `[0-9a-f]{32}` 过滤，非 hex 的 id 一律丢弃。已用 `test_non_string_input_id_does_not_break_the_adapter_path` 钉住 adapter 侧的承重墙 |
> | `_json_object()` 只在 application 侧 | **语义上是 no-op**：`describe()` 只 `append` `isinstance(meta, dict)` 的项，因此每项必然已是 dict。已用 `test_adapter_omits_non_dict_description_shape` 记录该事实 |
> | `prompt_required` 只在 application 侧 | adapter 在 `app.py::_api_analyze` 有等价守卫（handler 层），因此未纳入一致性断言，纳入会产生假阳性。已用 `test_application_path_rejects_empty_prompt_without_attachments` 单独立住 generate 侧的拒绝行为 |
> | 默认 prompt 串字面量重复两处 | 当前值相同故结果一致，但**这是一个没有门禁的重复字面量**——改一边就会静默漂移。已用 `test_attachment_only_input_yields_the_shared_default_prompt` 钉住该串 |
>
> **因此 C4 本轮的产出是「把不变量钉住」，不是「修一个 bug」。** 残留的真实债：两处默认串仍是两份字面量。合并它们属于纯重构，不在本轮，且应当与「让 adapter 委托给 application」一起做——否则只是把两份重复换成一份重复加一层间接。

> 这五条用例自身也经过两轮修正才对：首版把两侧序列化写成不同格式（服务端按页 `||` 分组、DOM 侧全部 `|`），断言恒假；`_make_store` 又少写了 `InputStore` 自动追加的 `.inputs` 层，导致「仅附件」用例莫名抛 `prompt_required`。两处都是**门禁自己的 bug**，不是产品缺陷——但如果不实跑就提交，会得到一条「永远绿」的假门禁，而那正是本项目反复栽的形状。


> 这两条的共同形状正是本项目反复栽的同一种：**两边都在，但没人保证它们一致**。

---

## 三、v0.6.2 · 补齐内容资产（约 1 周，优先级高于技术债）

**已核实**：`assets/screenshots/v0.6.0/` 13 张，而 `v0.5.0/` 有 **19 张是 v0.6.0 没有的**。

缺失对应的都是**真实存在、未被删除**的功能：

| 缺口 | 对应功能 |
|---|---|
| `input-dialog-paper` | 统一需求入口 |
| `project-memory-saved` | Project Memory |
| `command-palette-search` | 命令面板 |
| `revision-restore-complete` | 版本历史与恢复 |
| `generation-cancel` | 生成取消 |
| `export-center` / `export-center-ready` / `export-analysis-error` | 导出中心与受控错误 |
| `output-*`（6 张） | 六类生成器产物 |
| `selected-node-inspector` / `generated-output-inspector` | 两个检查器 |
| `classic-pixel-garden` | 经典模式 |
| `workbench-mobile-library` | 移动端素材库 |
| `workbench-night` | 夜蓝主题（另一尺寸） |

**这不是技术债，是资产债，且直接卡住内容产出**：

- README 这些功能只能用 v0.5.0 旧图顶着（观感不一致）
- 40 秒宣传片里它们**只能缺席**（见 `scripts/make_promo_film.py` 的 `NOT_IN_FILM`）
- 小红书讲这些功能时没有配图可用

**做**：启动工作台按脚本走一遍这些状态重拍，不改任何产品代码。

**产出**：v0.6.0 截图补到约 24 张 → README 全量换新图 → 宣传片镜头从 12 扩到约 20（`CATALOGUE` 表加项即可，`validate_script()` 会强制校验）→ 小红书配图直接复用。

---

## 四、v0.7 · 网页反向拆解（v0.6 主线的另一半）

### 为什么不是原来的四个选项

原投票项 Word 导出 / 桌面版 / 吸收更准 / 生成效果打磨，**没有一个是新能力**：
Word 导出是加格式，桌面版是换打包方式，后两者是打磨。按第一节的推论，打磨型选项点击率天然吃亏。

### v0.7 主张

> **粘贴任意网址 → 安全抓取 → 拆成骨架 / 令牌 / 区块 → 直接进素材库，变成可编辑可复用的结构。**

这是 v0.6「设计吸收」的**镜像**：`设计 → 素材` 的下一步是 `活网站 → 结构`。原来做不到的事，现在做得到。

### 可行性（已核实）

`htmlninefox/intake.py`（37KB）已具备：

| 能力 | 位置 |
|---|---|
| SSRF 安全 URL 校验 | `validate_url` L127 |
| 逐跳重定向过门抓取 | `fetch_reference` L173 |
| HTML 骨架解析器 | `_SkeletonParser` L309 |
| 区块标签体系 | `SECTION_TAGS` L306 |
| 颜色 / 字体令牌抽取 | `COLOR_PATTERN` / `FONT_PATTERN` L284-285 |
| 证据落盘 | `save_evidence` L233 |
| 三档许可强制 | `LICENSE_CLASSES` L33 |

而 `SOURCE_KINDS = ("gallery", "components", "motion", "typography")`（L34）**没有"整页"这一类**。

因此 v0.7 主要是**加一个 `page` 源类型 + 一个粘贴入口**，复用约 80% 现有代码。

### 为什么这条最强

- 与 v0.6 构成完整叙事：吸收外部设计 → **现在能把一个活网站拆开带走**
- 天然 local-first，不引入账号与云，与产品定位不冲突
- 演示性极强：贴个网址出结果，正是账号数据显示有效的「明确可感知结果」形态
- 许可三档与 CSP 沙箱直接复用，合规姿态不需要重新论证

### 需一并处理

- **版权边界**：拆解活网站默认只取令牌与骨架，**不复制正文与图片**；`LICENSE_CLASSES` 的 inspiration-only 档在"用户自己指定的网址"上语义不同（他有权访问但未必有权再分发），需要一条独立规则而不是复用源站的许可档
- **P1-6 SSRF 连接级 IP 绑定**：这条入口让用户直接输入任意 URL，SSRF 残余风险的暴露面比 v0.6 的内置源更大，**建议在本版本一并关闭**
- 旧版 `esc()` 与 `SOURCE_KINDS` 扩展会同时影响抽取器分发表，需登记进 `test_generation_quality_gates.py`

### 仍并入排期的次要项

| 项 | 归属 | 说明 |
|---|---|---|
| Word 导出 | v0.6.2 之后 | 已出列至 v0.6.x，属格式扩展而非新能力 |
| 桌面壳（Tauri） | v0.7.x | 换打包方式，用户可感知但不构成新能力 |
| 吸收准确度提升 | 随 v0.7 | 由"整页拆解"自然带来更多真实候选，是副产品而非独立目标 |

---

## 五、长期 · 结构性债（不紧急，排固定节奏）

以下均**无故障，放置不会变坏**，但持续拖慢后续每个版本。

| 项 | 性质 | 备注 |
|---|---|---|
| **C7** 前端 12 个 classic script 共享顶层作用域 | 收益最大、风险最高 | 已核实：全部 `<script src>` 无 `type="module"`；`state.*` 无声明约束；**这些文件目前无法被单元测试** |
| P1-6 SSRF 连接级 IP 绑定 | 安全残余风险（已公开披露） | 建议随 v0.7 关闭 |
| C1 Project 锁三种写法并存 | 结构性 | 根因：`RestoreRunner` 的 Interface 未声明「被调方持有 Project 锁」 |
| C5 错误码三处硬编码 | 易漏 | 忘加映射表就静默变 500 |
| P1-7 + C8 提取 `IntakeService` | 结构性 | `app.py:141` 的 `_Handler` 仍承担 intake 编排 |

**C7 建议单独立项。** 它是唯一「不做会持续付利息」的：前端无法单测，意味着 C3、C4 这类缺陷只能靠人工与 e2e 兜——而 v0.6 挖出的三个死按钮全是这么漏掉的。

---

## 六、执行顺序与判据

```
v0.6.1  C3 + C4          修两个真缺陷           1 周
v0.6.2  补拍 19 张截图    补内容资产             1 周   ← 成本最低、见效最快
v0.7    网页反向拆解      新能力                 待启动
长期    C7 独立立项       前端可单测             大
        C1/C5/P1-6/P1-7  结构性债               零散
```

### 每阶段的验收判据

| 阶段 | 判据 |
|---|---|
| v0.6.1 | 全量回归 ≥387 通过；C3 门禁去掉守卫必须变红；C4 一致性断言通过 |
| v0.6.2 | `assets/screenshots/v0.6.0/` ≥24 张；README 无 v0.5.0 图；`validate_script()` 全绿 |
| v0.7 | 新增 `page` 源类型端到端可跑；`test_generation_quality_gates.py` 覆盖新分发表；P1-6 已关闭 |

---

## 七、贯穿全程的纪律

过去几轮出现过的失误，形状一致：**先声称、后验证**。

| 实际发生 | 判据脚本 |
|---|---|
| 视频文件名写 `60s` 实为 40s | `make_promo_film.py` 的 `film_seconds()` 从镜头表推导 |
| README 标"实测 846 字符"实为 1568 | `_check_copy.py` 四项校验（字数/星号/emoji/标签） |
| 「构建成功」被当作「能启动」 | `packaging/verify_portable.py` 真实启动 + 内容级断言 |
| 产物验证只查文件在不在 | 同上，按本版标记逐项核对伺服字节 |
| 排期照抄已过时的审计结论 | 本文件；进排期前先核实现状 |

**要求**：每个阶段收尾时，至少留一个能被脚本抓住的检查，而不是靠人记。
