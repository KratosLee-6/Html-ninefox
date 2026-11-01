# v0.8.6 · 手机预览 + 一键交付包

**发布日期**：2026-11-01
**主题**：输出端「最后一公里」界面化（快赢包 B+C）。来自 2026-10-31 前端感知
审计（[EVAL-FRONTEND-PERCEPTION-20261031.md](EVAL-FRONTEND-PERCEPTION-20261031.md)，
机主四选全 A+B+C+E）的两个小感知点先行；A（所见即所得编辑）排 0.8.7，
E（多页站点）排 v1.0 讨论。

---

## 一、手机预览二维码

顶栏新增 📱 按钮 → `/api/lan-preview`（GET）：

- 局域网地址枚举走 stdlib UDP 探测（connect 到 8.8.8.8 取本端地址）+ 主机名
  IP 兜底，**端口取 `server.server_address[1]` 实际监听口**，不猜配置值；
- 二维码走 `[qr]` extra（segno，纯 Python）出 SVG；**无 segno 降级为纯地址
  文本**，不静默装包——可选依赖纪律沿用；
- 无鉴权警示随响应随弹窗（「仅限可信局域网」），与 `--host 0.0.0.0` 文档
  承诺一致；
- ≤900px 窄屏顶栏自动收起该按钮（手机上不需要「发到手机」）。

## 二、一键交付包

导出弹窗新增 📦 一键交付包 → `/api/exports/bundle`（POST，后台任务）：

| 意图 | 组包格式 |
|---|---|
| deck | HTML + PDF + PPTX |
| doc / archdoc | HTML + PDF + DOCX |
| landing / poster / dashboard | HTML + PDF |

逐格式走既有 `export_project` 真链导出（含 export-report.json），加网页本体
`output.html` 打 zip 落盘到 `exports/<时间戳>-bundle/`；任务轮询复用 `/api/jobs`
既有机制。实组包映射以代码为准（无 PNG——PNG 导出属图像意图链，未入本批）。

## 三、门禁与证据

| 门禁 | 数字 |
|---|---|
| lan-preview（tests/test_phone_preview_bundle.py） | 非回环地址在场、二维码 SVG 在场（dev 装有 segno 必须出图）、端口=真实监听口、无鉴权警示在场 |
| 交付包 | doc 意图 zip 真链（html+pdf+docx 全在包内、>1KB）、deck/doc 双意图格式跟意图走、缺项目名报 `export_project_required` |
| 注册表 | `window.FoxPhone` 进 module_globals 白名单（新功能模块归位，非万能豁免） |
| 全量 | **861 passed / 4 skipped**（2026-11-01 实测，13 分钟） |

## 四、安装与升级

```
pip install --upgrade "htmlninefox[all]"   # 含 [qr]
pip install --upgrade "htmlninefox[qr]"    # 只要手机预览二维码
```

老用户升级同名命令；无 segno 时手机预览照常可用（地址文本降级）。

## 五、后续排期（机主已拍板）

1. **0.8.7**：所见即所得 A1——文本级点选即改（复用幻灯片原位编辑机制）
2. **0.9.0**：A2 样式级点选即改 + Tauri 壳 + impeccable C（preset 扩族）
3. **v1.0**：E 多页站点 + impeccable D（SKILL 流程吸收）
