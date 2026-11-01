# v0.8.7 · 动效质量层

**发布日期**：2026-11-01
**主题**：接入 **LottieFiles/motion-design-skill**（MIT）——AI 生成的网页，
动效也过质检。impeccable（静态设计质量，0.8.4 接入）的另一半：**动效设计
质量**。评估全档见
[EVAL-motion-design-skill-20261101.md](EVAL-motion-design-skill-20261101.md)。

---

## 一、联盟第 8 位成员 · 首个 guidance-source 知识型成员

motion-design-skill 与以往成员都不同：它**没有 CLI、没有 python 模块**——
是一套「动效导演思维」（8 步清单 · 时长/缓动表 · 迪士尼十二律 UI 适配 ·
编排预算）。接入方式相应升级：

- 路由器新增 **`detect_paths` 探测**：skill 文件落位任一 agent 技能目录
  （`.agents` / `.claude` / `~/.agents` 等）即视为已装；
- **未安装照旧**：本地门禁与墨水落纸动效层完全自洽（fallback: skip），
  联盟纪律沿用——装了增强，不装不缺。

## 二、动效质量门禁（5 条，规则源自上游、自研实现并注明）

| 门禁 | 上游规则 | 我们的状态 |
|---|---|---|
| 时长 token 对齐元素类型表 | tooltip 80-120 / 按压 120-180 / 图标 150-250 / 卡片 200-350 | 90/140/180/200 全部在档 |
| 重量递增 + 入场>退场 | 轻 ≤ 中 ≤ 重；Enter > Exit | instant ≤ feedback ≤ enter ≤ panel；180 > 140 |
| linear 缓动禁令（CRITICAL #1） | linear 仅限 spinner/progress | 全库唯一 linear 恰是 btn-spin（白名单） |
| 显形非 opacity-only（CRITICAL #2） | 重要状态变化须伴随 transform | fox-reveal transition 同携 opacity+transform |
| stagger < 500ms 预算 | 总预算上限 | cap 360ms（步长 60ms，Standard 档） |
| （附）ink-in ∈ 戏剧档 / 循环缓动律 | 600-1200ms；循环=ease-in-out/sine | 700ms ✓；26s ease-in-out alternate ✓ |

**接入前审计零违规**——门禁的价值是把今天的不变量锁住，拦未来的回归
（只禁变差纪律，与间距 burn-down 同哲学）。

## 三、变异验证（门禁连自己都拦）

三连变异全部 **CAUGHT**：

| 变异 | 结果 |
|---|---|
| fox-ambient 循环改 linear | ✓ CAUGHT |
| fox-reveal 砍掉 transform（退化为 opacity-only） | ✓ CAUGHT——首版门禁查块不查行曾漏网，修正为查 transition 属性集后抓住 |
| stagger cap 360 → 900ms | ✓ CAUGHT |

## 四、战果 · 显形编排静默死亡（门禁立起来当天抓到）

浏览器采样 opacity 时间线实锤：卡片显形的 0.6s 编排**早已静默死亡**——
`.card` 的交互 transition（.18s）与 `.fox-reveal` 的编排 transition（.6s）
同特异性，后者声明顺序在前被整体覆盖，显形一直是瞬切（0→1 不足 100ms）。
修复：transition 移入 after-change 态（`.fox-in`，天然免疫后续覆盖），
入场完成后 JS 补 `.fox-done` 切回 .18s 交互档——入场电影感与 hover 响应两全；
reduced-motion / print 通路同步覆盖。修复后时间线：0→0.68→0.92→0.99。

## 五、门禁与证据

| 项 | 数字 |
|---|---|
| 新增门禁 | 动效质量 5 条（tests/test_motion_quality.py）+ 联盟 detect_paths 探测 1 条 |
| 全量 | **868 passed / 4 skipped**（2026-11-01 实测，14 分 08 秒） |
| CI | Test ✓（41f7fdc，7 分钟） |
| 取证 | scripts/capture_v087_shots.py：动效层双帧对比（墨水标题入场中 vs 终态）、门禁/变异终端真回显、联盟清单真输出 |

## 六、安装与升级

```
pip install --upgrade "htmlninefox[all]"   # 0.8.6 老用户同名命令
```

动效质量层零新依赖；想要 agent 侧也获得「动效导演」能力，另装
`npx skills add LottieFiles/motion-design-skill`（可选，互不影响）。

## 七、排期

- **生成端 guidance**：动效人格四原型（Playful/Premium/Corporate/Energetic）
  进 LLM 提示层——与 preset 扩族合并为「风格轴」设计
- **所见即所得 A1**（机主已拍板的 0.8.7 主线）顺延为 0.8.8 主线
