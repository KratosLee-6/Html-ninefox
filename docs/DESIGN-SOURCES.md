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
