# 评估 · LottieFiles/motion-design-skill 接入（v0.8.7 批次）

**日期**：2026-11-01
**上游**：https://github.com/LottieFiles/motion-design-skill · MIT · v1.0.0
**定位**：impeccable（静态设计质量）的另一半——**动效设计质量**。哲学层、
实现无关（CSS/GSAP/Lottie/Spring 通吃），教 agent「先像动效导演一样想，
再写一行动画代码」。

---

## 一、上游内容盘点（当日实测拉取）

| 层 | 内容 | 对我们的价值 |
|---|---|---|
| SKILL.md | 8 步清单 · 动效人格四原型 · 时长表 · 缓动表 · 属性选择 · 质量律（CRITICAL×4 + HIGH×4） | **确定性规则可直接落地为门禁** |
| director/ | 三支柱 · 迪士尼十二律 UI 适配 · 情绪→动效映射 · 编排 · 叙事结构 · a11y/性能适配 | 生成端 guidance 的灵感源（排期） |
| patterns/ | 进出场 · 状态反馈 · 环境动效 · 多元素编排配方 | preset 扩族（huashu/impeccable 调性轴）时的动效轴 |
| reference/ | 时长缓动查表 · 质量清单 · 问题排查（animation smells） | 门禁对照表来源 |

**CRITICAL 四律**（原文口径）：
1. 空间位移禁 linear——linear 仅限 spinner/progress
2. 重要状态变化不得 opacity-only——须伴随 position/scale
3. 位移超 1/3 屏幕须有中间关键帧
4. 三层动效（primary + secondary + ambient）

**时长表**（元素类型 → ms）：tooltip 80-120 · 按压 120-180 · 图标 150-250 ·
卡片 200-350 · 弹窗 300-400 · 页面转场 400-600 · 戏剧性揭示 600-1200。
方向律：入场=减速（ease-out）、退场=加速（ease-in）、循环=ease-in-out/sine；
入场比退场长 30-50%；stagger 总预算 **< 500ms**。

---

## 二、现有动效家底 × 上游规则对齐审计（逐条实测）

| 我们的资产 | 实测值 | 上游规则 | 判定 |
|---|---|---|---|
| `--motion-instant` 90ms | tooltip 档 80-120 | ✓ |
| `--motion-feedback` 140ms | 按压档 120-180 | ✓ |
| `--motion-enter` 180ms | 图标档 150-250 | ✓ |
| `--motion-panel` 200ms | 卡片档 200-350（下沿） | ✓ |
| `--motion-exit` 140ms | enter>exit（180>140） | ✓（30-50% 差距为努力方向，不硬门禁） |
| fox-ink-in 700ms | 戏剧档 600-1200 | ✓ |
| fox-reveal stagger cap 360ms（步长 60ms） | 总预算 <500ms；Standard 档 50-100ms | ✓ |
| fox-reveal transition | opacity+transform 同行（非 opacity-only） | ✓ CRITICAL #2 |
| fox-ambient 26s ease-in-out alternate | 循环=ease-in-out/sine | ✓ 方向律 |
| 全库 linear 缓动唯一一处 | `btn-spin 720ms linear infinite` | spinner 白名单例外 | ✓ CRITICAL #1 |
| reduced-motion / print / settle 三通路 | 静态终态 | a11y 适配章 | ✓（test_ambient_motion 既有） |

**结论**：零违规——门禁的价值是**把今天的不变量锁住，拦未来的回归**（只禁变差纪律）。

---

## 三、本批落地（0.8.7）

1. **联盟成员**：`data/alliance/motion-design.yaml`——**guidance-source** 新类型
   （知识型成员：无 CLI、无 python 模块）；路由器新增 `detect_paths` 探测
   （`.agents`/`.claude`/`~/.agents` 等技能目录落位任一命中即已装；未装 fallback: skip）。
2. **动效质量门禁**（`tests/test_motion_quality.py` 5 条，规则源自上游、自研实现并注明）：
   - 时长 token 对齐元素类型表 + 重量递增 + 入场>退场
   - linear 缓动禁令（spinner/progress 白名单）——扫工作台 CSS/JS + 墨水落纸层
   - reveal 非 opacity-only（查 transition 属性集）+ stagger cap < 500ms
   - ink-in ∈ 戏剧档
   - ambient 循环必须 ease-in-out/sine
3. **变异验证**：三连变异全部 CAUGHT（ambient 改 linear ✓ · reveal 砍 transform ✓
   ——首版门禁漏网后修正为查 transition 行 · cap 涨到 900 ✓）。

## 四、排期（未动工）

1. **生成端 guidance**：六意图渲染器的 LLM 提示层引入动效人格四原型
   （Playful/Premium/Corporate/Energetic）+ 时长表摘录——与 preset 扩族
   （huashu/impeccable 调性轴）合并为一个「风格轴」设计，避免两次动管线
2. **CRITICAL #3（1/3 屏）与三层动效**：需要运行时几何感知，归读屏器审计批
3. **Xiaohongshu**：随 0.8.7 发布帖带一段（「门禁连动效都管」叙事）
