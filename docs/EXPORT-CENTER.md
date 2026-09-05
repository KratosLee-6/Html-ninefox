# Html九尾狐 · Export Center 导出中心设计

> 状态：方案确定，尚未实现
> 版本规划：v0.4.2 起分阶段交付
> 原则：HTML 是唯一源文件，PDF / 图片 / PPTX / DOCX 是面向不同交付场景的派生格式。

## 1. 需求是否成立

成立，而且是产品从“能生成”走向“能交付”的关键能力。真实工作中，接收方经常不运行 HTML：

- 客户审阅、归档和打印需要 PDF。
- 微信、飞书、小红书和汇报群需要 PNG / JPEG 长图或逐页图片。
- 汇报现场和二次编辑需要 PPTX。
- 正式方案、合同附件和知识沉淀可能需要 DOCX。

但不能承诺任意复杂 HTML 都能无损、可编辑地转换为 PPTX 或 DOCX。导出中心必须明确区分“高保真分享”和“可编辑交付”。

## 2. 两种导出模式

### A. 高保真模式

目标是看起来与 HTML 一致：

- PDF：Chromium 打印管线，保留文字、矢量、链接和分页。
- PNG / JPEG / WebP：按页面或长页面截图，支持 1x / 2x / 3x 清晰度。
- PPTX 高保真版：每个 HTML 页面渲染为整页图片并放入幻灯片。

优点是视觉一致、实现稳定；限制是 PPTX 内部元素不能逐个编辑。

### B. 可编辑模式

目标是在 Office 中继续修改：

- PPTX 可编辑版：把受支持的文字、图片、基础图形、表格和图表映射为 PowerPoint 元素。
- DOCX 语义版：把标题、段落、列表、表格、图片、引用和分页映射为 Word 文档结构。

复杂 CSS、WebGL、滤镜、视频、动画、伪元素和自由布局无法可靠映射时，应自动扁平化为图片，并在导出报告中说明。

## 3. 格式策略

| 格式 | 默认模式 | 适用内容 | 可编辑性 | 保真度 |
|---|---|---|---:|---:|
| PDF | Chromium 打印 | 全部 HTML 产物 | 低 | 高 |
| PNG/JPEG/WebP | 页面截图 | 全部 HTML 产物 | 无 | 最高 |
| PPTX 高保真版 | 一页一图 | Deck、海报、汇报页面 | 低 | 最高 |
| PPTX 可编辑版 | DOM/组件映射 | 受约束的 Deck 模板 | 高 | 中高 |
| DOCX 语义版 | 文档模型映射 | Doc、Archdoc、报告 | 高 | 中高 |

Word 不应作为落地页、数据看板或自由画布作品的通用导出目标；这些内容默认导出 PDF 或图片。

## 4. 技术架构

```text
Artifact HTML + artifact.json
          ↓
    ExportAnalyzer
          ↓
      ExportPlan
  ┌───────┼────────┬──────────┐
  PDF   Image    PPTX       DOCX
  Chromium       fidelity   semantic
                 editable
          ↓
 export-report.json + files
```

建议新增：

- `ArtifactManifest`：产物类型、页面清单、尺寸、字体、资源、交互和导出能力。
- `ExportPlan`：页面范围、格式、清晰度、宽高比、保真/可编辑模式和降级项。
- `ExportAdapter`：PDF、Image、PPTX、DOCX 的统一适配器接口。
- `ExportJob`：异步状态、进度、错误、取消、重试和下载文件。
- `export-report.json`：记录字体替换、动画扁平化、不可编辑元素和失败页面。

## 5. 建议依赖

- PDF / 图片：Playwright Chromium，复用现有浏览器测试基础设施。
- PPTX：PptxGenJS；先交付“一页一图”，再支持受约束组件的可编辑映射。
- DOCX：python-docx 或等价 OOXML 生成器，只处理语义文档模型。
- 可选转换：LibreOffice headless 只作为本地增强，不作为核心正确性的唯一依赖。

所有导出默认在本地完成，不上传用户 HTML、文件或 API Key。

## 6. 产品界面

产物节点增加“导出”按钮，打开 Export Center：

1. 选择 PDF、图片、PPTX 或 DOCX。
2. 选择全部页面或页面范围。
3. PPTX 选择“视觉一致”或“可继续编辑”。
4. 设置画布尺寸、宽高比、图片倍率和是否嵌入字体。
5. 导出前显示兼容性评分与可能降级项。
6. 导出后提供文件、报告和重新导出入口。

推荐默认值：

- Landing / Dashboard / Poster：PDF + PNG。
- Deck：PPTX 高保真版 + PDF。
- Doc / Archdoc：PDF + DOCX 语义版。

## 7. 分阶段路线

### v0.4.2：可分享

- PDF 导出。
- 单页、逐页和长图 PNG 导出。
- 页面范围、倍率、纸张和宽高比。
- Export Job、进度、错误与下载。

### v0.5.0：可汇报

- PPTX 高保真版，一页 HTML 对应一页幻灯片。
- 演讲者备注、页面标题和章节信息写入 PPTX。
- 字体缺失、动画和视频的导出报告。

### v0.6.0：可编辑

- 为九尾狐受控模板建立文字、图片、形状、表格、图表组件协议。
- PPTX 可编辑模式，无法映射的局部元素自动扁平化。
- Doc / Archdoc 的 DOCX 语义导出。

## 8. 验收标准

- PDF 和图片与 HTML 截图的关键区域视觉差异可控。
- 导出失败不会损坏原始 HTML 或覆盖已有产物。
- 每次导出可重试、可取消、有明确错误和兼容性报告。
- PPTX 高保真模式不出现裁切、错页和字体漂移导致的布局破坏。
- DOCX 只承诺语义正确，不虚假承诺自由布局像素级一致。

## English Summary

The Export Center keeps HTML as the source of truth and derives PDF, images, PPTX, and DOCX for delivery. It separates visual-fidelity exports from editable exports. PDF and images come first, high-fidelity PPTX follows, and editable PPTX/DOCX are limited to supported semantic components with explicit fallback reporting.
