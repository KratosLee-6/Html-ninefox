# v0.9.0 · 桌面壳 + 风格轴（Tauri 里程碑）

**发布日期**：2026-11-07
**主题**：从「网页工具」到「桌面创作应用」——Tauri 桌面壳（与便携包/
安装包**并存**，不是替代）+ 动效人格风格轴第一批。总纲见
[EVAL-AI-STYLE-DEEPEN-20261103.md](EVAL-AI-STYLE-DEEPEN-20261103.md)。

---

## 一、Tauri 桌面壳

| 件 | 说明 |
|---|---|
| 形态 | 双击即用、无浏览器、系统托盘（打开工作台/退出）、关窗即回收子进程 |
| sidecar 链路 | 照 verify_portable 纪律：选空闲端口 → spawn `HtmlNineFox.exe --no-browser --strict-port` → 原生 HTTP 轮询 `/api/health` 直到 200 → webview 导航工作台；45 秒超时在加载页照实报错 |
| sidecar 定位 | 环境变量 `HTMLNINEFOX_SIDECAR` > 主程序同目录 > `sidecar/HtmlNineFox/` > build_portable 产物路径 |
| 打包 | 发布流水线新增 **shell-bundle** job：windows job 的 onedir → `src-tauri/sidecar/` → `tauri build` 出 **NSIS 壳安装包**（cargo-tauri / npm 版 CLI 双适配） |
| CI | rust-shell.yml 三平台 cargo check（Windows/Ubuntu/macOS）；Tauri 编译零警告 |
| 承诺 | PyInstaller 便携包、Windows/Linux/macOS 安装包、Docker **全部照发**——壳是增量形态 |

**发布前人工清单**（桌面行为不进 CI）：双击启动 → 加载页 → 工作台出现；
托盘「打开工作台/退出」；关窗后 sidecar 进程消失。

## 二、风格轴第一批（0.9.1 前置，随本版发布）

- **动效人格四原型**（原则源自 LottieFiles/motion-design-skill · MIT）：
  灵动 Playful / 从容 Premium / 干练 Corporate / 锐利 Energetic——驱动
  **三轴**参数：ink 600-1200ms · stagger 步长/上限 · ambient 周期；
  全部落在 0.8.7 动效门禁内，reveal .6s 为固定锚点，词表外 tone 落干练兜底
- **覆盖矩阵门禁**：6 意图 × 4 原型 ≥ 1 可产出组合，空洞不可发版
  （变异验证 CAUGHT：砍掉 dashboard 的 energetic 映射立刻报洞）
- **理由永远可见**：`match_preset` 附中文推荐理由，规则引擎模式照给；
  「推荐组合」卡渲染 🎬 原型徽章 + 💡 理由行
- **画廊 tone 标签**：10 张模板 manifest 全带调性（完整性门禁）

## 三、门禁与证据

| 门禁 | 数字 |
|---|---|
| test_style_axis.py | 7 条：覆盖矩阵 / 参数范围 / 兜底映射 / 理由 / manifest 完整性 / 渲染端到端 / 变异 |
| 全量 | **885 passed / 4 skipped**（2026-11-03 实测 11 分 22 秒，诚实退出码） |
| CI | Test ✓ · Shell (Tauri) 三平台 ✓ · Test ✓（本发布前最后一次全量） |

## 四、安装

```
pip install --upgrade "htmlninefox[all]"        # Python 形态（照旧）
HtmlNineFox-Setup-0.9.0.exe                      # 桌面壳安装包（本版新增）
HtmlNineFox-Windows-x64-0.9.0.zip                # 便携包（照旧）
```

## 五、排期（0.9.x 已切分）

0.9.1 后半（调性选择器 + 配方时间线）→ 0.9.2 AI 生成深化（compose 推荐 +
槽位润色）→ 0.9.3 拆分语义增强 + 演示模式 → 0.9.4 拼装层 → 0.9.5 模板
B/C 档；A2 样式级编辑并入其中。v1.0 = 多页站点。
