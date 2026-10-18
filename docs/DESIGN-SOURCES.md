# 设计来源与接入边界

> 审计日期：2026-08-31

## 已核验项目

### Huashu Design

- GitHub：`https://github.com/alchaincyf/huashu-design`
- 本地来源：`C:\Users\Admin\.agents\skills\huashu-design`
- 本地 `LICENSE`：MIT。
- 接入策略：保留为 Skill 联盟设计顾问；九尾狐只接入“先出三方向、再定稿”的流程与独立实现的视觉 token，不复制演示资产。

### Guizang PPT Skill

- GitHub：`https://github.com/op7418/guizang-ppt-skill`
- 本地来源：`C:\Users\Admin\.agents\skills\guizang-ppt-skill`
- 许可证状态：本地 README 声称 2026-05-14 起为 MIT，但本地根目录 `LICENSE` 内容仍为 AGPL-3.0；两者冲突。
- 接入策略：在许可证冲突解决前，不复制其模板、脚本和资产；仅依据公开的编辑设计、电子墨水与瑞士国际主义原则，做 clean-room 原生适配。

## 九尾狐原生适配

本轮新增五个可真实渲染的视觉系统：

- `fox-pixel-garden`：细像素叙事、深钴蓝与薄荷绿。
- `fox-duotone-studio`：暖白、渐变灰、石墨功能区与电光蓝。
- `fox-editorial-ink`：纸感、衬线标题、发丝线和编辑排版。
- `fox-swiss-signal`：16 列网格、直角、安全橙与钴蓝。
- `fox-soft-silver`：奶油灰、柔银层次和双层卡片。

这些预设的代码与 token 均在 Html九尾狐仓库内独立实现；第三方项目只作为研究来源和联盟入口。

## 后续导入规则

1. 只从项目官方 GitHub 仓库读取来源与许可证。
2. 许可证不明确或文件互相冲突时，默认不 vendor 代码。
3. 可优先接入 manifest、提示词路由和用户自行安装的 Skill；代码复制必须保留许可证与版权声明。
4. 每个外部适配器必须提供离线 fallback，不能阻断九尾狐核心生成链路。

---

## 2026-10-18 复核（GitHub API 实测）

| 来源 | 星标 | 许可（GitHub 标注） | 最近推送 | 与我们的差异 |
|---|---:|---|---|---|
| [tt-a1i/archify](https://github.com/tt-a1i/archify) | 85.2k | MIT | 2026-10-18 | 描述已扩为「把想法/计划/代码变成可交互架构图」，我们仍写「5 种图」 |
| [alchaincyf/huashu-design](https://github.com/alchaincyf/huashu-design) | 25.3k | MIT | 2026-10-17 | 上游 tag **v3.0.0**；我们有 manifest 还写 1.0.0、口径「三个方向」 |
| [op7418/guizang-ppt-skill](https://github.com/op7418/guizang-ppt-skill) | 28.1k | **AGPL-3.0** | 2026-08-07 | **许可冲突结案**：就是 AGPL，不是 MIT |
| [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills) | 26.7k | MIT | 2026-09-10 | 原 `JimLiu/baoyu-slide-deck` 已 404，作者并入单仓 |
| [zarazhangrui/beautiful-html-templates](https://github.com/zarazhangrui/beautiful-html-templates) | 4.8k | MIT | 2026-06-09 | 实测 **34 个 .html**，我们长期写 28 |
| [zarazhangrui/frontend-slides](https://github.com/zarazhangrui/frontend-slides) | 30.8k | MIT | 2026-06-23 | 口径一致 |

### 结案两条

1. **归藏（guizang-ppt-skill）= AGPL-3.0，不再是「有争议」。** 由此：仓库内 `templates/gallery/guizang-*.html` 与 `preset_id: guizang-magazine` 必须是 clean-room 原创；不复制其代码、模板与资产。为避免外部误读为 AGPL 派生，建议把这些 id 改成中性名（`fox-ink-*`），在 manifest 的 `origin` 字段里注明「方法参考：归藏式编辑设计」。
2. **署名与引用规则**已落到根目录 [NOTICE.md](../NOTICE.md)：MIT 代码可商用，名称/Logo/Pixel Garden 视觉保留；引用格式见 [CITATION.cff](../CITATION.cff)。

模板供给的扩充计划（含 6 意图覆盖缺口、34 套 MIT 模板引入、月度上游巡检）见 [PLAN-TEMPLATE-EXPANSION.md](PLAN-TEMPLATE-EXPANSION.md)。
