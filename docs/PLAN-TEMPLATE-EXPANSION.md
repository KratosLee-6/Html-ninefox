# 模板库扩充与上游同步 · 评估与计划

**日期**：2026-10-18
**触发**：KX 问「项目引用的模板对应的仓库内容应该有更新，需不需要引入多一些选择模板」
**结论**：**需要，而且缺的不是几张卡，是两个结构性缺口**——① 六个产物意图只有两个有模板；② 六个联盟成员的元数据已经落后上游半年。先修数据，再扩数量。

---

## 1. 现状实测（2026-10-18）

### 1.1 我们手里有什么

| 层 | 数量 | 位置 |
|---|---|---|
| 风格令牌（preset） | **11** | `htmlninefox/generators/_tokens.py`（linear-light / vercel-dark / guizang-magazine / shadcn-dashboard / vibrant-poster / doc-clean / fox-pixel-garden / fox-duotone-studio / fox-editorial-ink / fox-swiss-signal / fox-soft-silver） |
| 产物意图（intent） | **6** | landing / deck / poster / dashboard / doc / archdoc |
| 画廊模板（可点击的真实 HTML） | **6** | `htmlninefox/templates/gallery/manifest.json` |
| 联盟成员（外部 skill + 本地 fallback） | **6** | `htmlninefox/data/alliance/*.yaml` |
| 设计源清单 | 12 | `htmlninefox/data/sources/design-galleries.yaml` |

### 1.2 缺口一：模板只覆盖 2 / 6 个意图

| 意图 | 画廊模板数 | 说明 |
|---|---:|---|
| deck | 4 | 4 张里有 3 张用同一个 preset（`guizang-magazine`）→ 同质 |
| landing | 2 | 一张 `fox-editorial-ink`、一张 `fox-pixel-garden` |
| poster | **0** | 有 `vibrant-poster` preset，没有一张可点的模板 |
| dashboard | **0** | 有 `shadcn-dashboard` preset，没有模板 |
| doc | **0** | 有 `doc-clean` preset，没有模板 |
| archdoc | **0** | 靠 Archify 或本地生成器兜底，画廊里看不见 |

**这条比「模板不够多」严重**：用户在侧栏点「版式」，只能看见 deck 和 landing —— 另外四类产物在界面里等于不存在，而生成器其实早就能出。

### 1.3 缺口二：联盟元数据落后上游（逐条已核）

| 成员 | 我们写的 | 上游实测（2026-10-18，GitHub API） | 判定 |
|---|---|---|---|
| archify | 「5 种验证过的架构图」 | **85.2k★，MIT，当日仍有推送**；描述已扩成「把想法/计划/代码变成可交互架构图」 | ⚠️ 能力口径过期 |
| baoyu-slide-deck | `JimLiu/baoyu-slide-deck`，「17 套风格」 | **原仓库 404**；作者已并入 [`JimLiu/baoyu-skills`](https://github.com/JimLiu/baoyu-skills)（26.7k★，MIT，2026-09-10） | ❌ 死链，**已修** |
| beautiful-html-templates | 「28 套模板」 | **实测 34 个 `.html`**（MIT） | ⚠️ 少报 6 套 |
| frontend-slides | 「3 版首页候选」 | 30.8k★，MIT，2026-06-23 | ✅ 基本一致 |
| guizang-ppt-skill | 「README 声称 MIT，LICENSE 是 AGPL，冲突」 | **GitHub 已明确标 AGPL-3.0**；28.1k★ | ✅ 结案为 AGPL，**已改** |
| huashu-design | `version: 1.0.0`，「新设计先出三个方向」 | **tag v3.0.0**；描述含 20 条设计哲学 / 5 维评审 / MP4 导出；提交说明提到 84 种风格样张与「六候选挑三」 | ❌ 落后一个大版本，**已改** |

> 已改的文件：`data/alliance/*.yaml` 全部加了 `upstream_checked_at / upstream_license / upstream_version`；baoyu 换正确仓库地址；guizang 许可结案；huashu 版本号 1.0.0 → 3.0.0。

---

## 2. 提案：三档推进

### A 档 · 现在就能做（v0.8.1 期间，不阻塞 DOCX）

1. **补齐四个空意图各 1 张模板**（poster / dashboard / doc / archdoc），让侧栏「版式」在六类里都有东西可点。
   - doc、archdoc 各 1 张：用现有 `doc-clean` 与 Archify 产物做**原创**模板；
   - poster 1 张：`vibrant-poster` 已存在，只缺 manifest 条目与真实 HTML；
   - dashboard 1 张：`shadcn-dashboard` 同理。
2. **manifest 增加两个必填字段**：`origin`（明确写「原创 / 方法参考 / 直接引入」）与 `license`（MIT / AGPL-out-of-scope / original）。缺字段的条目在测试里直接红。
3. **同质化修正**：deck 的 4 张里有一张换 preset（如 `fox-editorial-ink`），避免「四张卡一个样」。

**成本**：约 1.5 天（4 个 HTML + manifest + 渲染门禁）。**收益**：六类意图在界面上全部可见。

### B 档 · v0.8.2 与界面版一起做

4. **画廊扩到 18 张 = 6 意图 × 3 张**，每个意图至少跨 2 个 preset。
5. **卡片可读性与模板数量联动**：v0.8.2 的 B3-3 已定「更大更少」，所以「18 张」不等于「一屏 18 张」——按意图分组 + 折叠，避免侧栏变成长列表。
6. **覆盖矩阵门禁**：`tests/test_template_coverage.py`，断言每个 intent ≥3 张、每个 preset 至少被 1 张模板使用（防止有 preset 永远看不见）。

**成本**：约 3 天（12 个新模板）。**收益**：用户「先看真实 HTML 再选」的产品承诺对六类产物都成立。

### C 档 · v0.9 起，接外部库

7. **beautiful-html-templates 34 套**（MIT，可整条入库，保留其版权声明）：挑 10–12 套覆盖 doc / dashboard / landing / poster，作为「现成即用」档；其余作为参考板。
8. **huashu-design v3.0 的风格库**（MIT）：它是「20 条设计哲学 + 84 种风格样张」，适合**扩 preset**而不是扩模板——把 11 个 preset 按「编辑 / 技术 / 柔和 / 高对比」四族各补 2–3 个，形成 18–20 个 preset 的选择面。
9. **上游巡检**：新增 `scripts/check_upstream.py`，读 6 个 manifest 的 `homepage`，比对 stars / pushed_at / license / 最新 tag，输出差异。挂月度 cron，结果进飞书。
   —— 这次能发现 baoyu 404 与 huashu 落后一个版本，说明「人肉记版本号」不可持续。

**成本**：约 4–5 天。**收益**：模板供给从「6 张」变成「34 + 18」，且不再需要靠记忆维护上游状态。

---

## 3. 合规规则（每条入库都必须满足）

| 来源许可 | 允许 | 禁止 | 落法 |
|---|---|---|---|
| MIT（beautiful-html-templates、huashu、frontend-slides、archify、baoyu-skills） | 整条引入、改、商用 | 抹掉版权声明 | manifest 写 `origin` + `license: MIT` + 原仓库链接；文件头保留原作者声明 |
| **AGPL-3.0（guizang-ppt-skill）** | 只借鉴方法/版式原则 | **复制代码、模板、资产** | manifest 写 `license: AGPL-out-of-scope`；HTML 必须是 clean-room（结构、类名、令牌全自研） |
| 画廊/灵感站（land-book 等 12 源） | 参考结构、提取令牌 | 复制整页/图片 | 走现有「许可三档」通道，产物必须原创重渲染 |

**命名风险（需要决定）**：`templates/gallery/guizang-*.html` 与 `preset_id: guizang-magazine` 里的 `guizang-` 前缀，会让外部读者以为是从 AGPL 仓库复制来的。建议改成中性名（如 `fox-ink-deck`、`fox-editorial-ink` 已是中性），并在 manifest 的 `origin` 里写清「方法参考：归藏式编辑设计」。改名属于对外可见变更，建议放进 v0.8.2 一起做。

---

## 4. 验收门禁（不新增空口承诺）

1. `manifest.json` schema：`id / name / intent / preset_id / origin / license / file` 八字段必填，缺一即红。
2. 每个 intent ≥ 1 张（A 档）→ ≥ 3 张（B 档）。
3. 每张模板真实渲染：iframe 200、无 JS 错误、`<title>` 与 manifest 一致（沿用现有 content-marker 纪律）。
4. 每个 preset 至少被 1 张模板使用。
5. 上游巡检脚本对 6 个 manifest 全部能取到 `pushed_at`；404 即报「死链」。

---

## 5. 建议顺序

```
A 档（4 张补空意图 + manifest 字段 + 同质化）   ← 现在，可与 v0.8.1 并行
        ↓
B 档（18 张 + 覆盖矩阵门禁 + 分组折叠）        ← v0.8.2 界面版
        ↓
C 档（外部库 34 套 + preset 扩族 + 月度巡检）  ← v0.9
```

## 6. 需要 KX 一句话

1. **A 档现在就做吗？**（4 张模板，约 1.5 天，不影响 DOCX 主线）
2. **`guizang-` 前缀改中性名**（`fox-ink-*`）——改，还是保留「标明灵感来源」？
