"""脱敏示例文档：任何对外截图、演示与测试都只许用它。

规则（2026-10-20 起）：仓库里不得出现真实客户名、真实项目标题、真实文件路径。
这份生成器造一份**结构真实、内容虚构**的商务方案：星野智造（客户）／栖木云（乙方），
三十来个章节、六张表，够跑完整解析与渲染。
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

CLIENT = "星野智造"
VENDOR = "栖木云"
TITLE = f"{CLIENT}全域数字化营销与增长平台方案"

CONTENT_TYPES = (
    "<?xml version='1.0' encoding='UTF-8'?>"
    "<Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'>"
    "<Default Extension='xml' ContentType='application/xml'/>"
    "<Override PartName='/word/document.xml' ContentType='application/vnd.openxmlformats-"
    "officedocument.wordprocessingml.document.main+xml'/></Types>")
RELS = (
    "<?xml version='1.0' encoding='UTF-8'?>"
    "<Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'>"
    "<Relationship Id='rId1' Type='http://schemas.openxmlformats.org/officeDocument/2006/"
    "relationships/officeDocument' Target='word/document.xml'/></Relationships>")


def _p(text: str, style: str = "") -> str:
    ppr = f"<w:pPr><w:pStyle w:val='{style}'/></w:pPr>" if style else ""
    return f"<w:p>{ppr}<w:r><w:t>{text}</w:t></w:r></w:p>"


def _table(rows: list[list[str]]) -> str:
    body = ""
    for row in rows:
        cells = "".join(
            f"<w:tc><w:p><w:r><w:t>{cell}</w:t></w:r></w:p></w:tc>" for cell in row)
        body += f"<w:tr>{cells}</w:tr>"
    return f"<w:tbl>{body}</w:tbl>"


SECTIONS: list[tuple[str, list[str]]] = [
    ("一、执行摘要", [
        "本方案面向区域制造企业的品牌与获客一体化需求，给出可分期交付的数字化底座。",
        "首期聚焦内容生产、线索归集与经营看板三条主线，后续按季度扩展渠道与自动化。",
    ]),
    ("二、业务现状与问题", [
        "现有内容分散在三个团队，素材复用率低，渠道数据无法回收到统一口径。",
        "线索从落地页到销售跟进缺少状态机，导致同一客户被重复触达。",
    ]),
    ("三、总体方案", [
        "以内容中台为起点，向上承接品牌表达，向下打通渠道投放与线索流转。",
        "所有模块共用一套主数据，避免二次录入与口径漂移。",
    ]),
    ("四、内容中台", [
        "支持模板化生产、版本留痕与素材授权管理，输出物可直接进入渠道。",
    ]),
    ("五、渠道投放", [
        "统一管理搜索、信息流与私域三条触达路径，投放计划与素材绑定。",
    ]),
    ("六、线索与销售协同", [
        "线索按来源、行业与意向分层，自动分配至对应销售并记录每次跟进。",
    ]),
    ("七、经营看板", [
        "以周为单位呈现投入、产出与转化，指标口径与财务口径对齐。",
    ]),
    ("八、数据与合规", [
        "个人数据最小化采集，留痕可追溯；跨境传输按属地要求单独评估。",
    ]),
    ("九、实施计划", [
        "首期 8 周完成内容中台与看板上线，第 9 周进入试运行。",
    ]),
    ("十、验收标准", [
        "以可核验的功能清单与数据口径为准，验收不依赖主观描述。",
    ]),
    ("十一、服务与保障", [
        "提供工作日响应与季度巡检，重大变更走变更评审。",
    ]),
    ("十二、报价说明", [
        "按模块组合计价，超出范围的部分单独立项，不在本方案内承诺。",
    ]),
    ("十三、品牌与内容资产", [
        "现有素材重新编目，按行业、场景与渠道三维归档，避免重复生产。",
        "对外口径统一到品牌手册，渠道侧不再各自改写。",
    ]),
    ("十四、素材生产流程", [
        "从选题到发布设四道关口：选题评审、事实核验、视觉校对、发布登记。",
    ]),
    ("十五、渠道组合策略", [
        "搜索承接确定性需求，信息流做场景教育，私域承担复购与转介绍。",
    ]),
    ("十六、线索分层规则", [
        "按行业匹配度、预算区间与决策角色三项打分，分层结果直接决定跟进节奏。",
    ]),
    ("十七、销售协同机制", [
        "线索进入跟进后 24 小时内必须首次触达，超时自动回收并重新分配。",
    ]),
    ("十八、指标体系", [
        "投入侧看获客成本与内容复用率，产出侧看有效线索与签约周期。",
    ]),
    ("十九、数据看板设计", [
        "看板按角色分三层：经营层看趋势，管理层看结构，执行层看当日待办。",
    ]),
    ("二十、权限与审计", [
        "按岗位授予最小权限，导出行为全量留痕，异常访问触发复核。",
    ]),
    ("二十一、上线与迁移", [
        "历史数据清洗后分批迁移，迁移期间双轨运行两周。",
    ]),
    ("二十二、培训与交接", [
        "提供两轮岗位培训与一份操作手册，交接以录屏与清单为准。",
    ]),
    ("二十三、风险与预案", [
        "识别出四类主要风险：数据口径分歧、渠道政策变化、人员流动、预算推迟。",
        "每类风险对应一个可执行的预案，不在出现问题时临时拍板。",
    ]),
    ("二十四、下一步", [
        "确认范围与排期后启动首期，首周完成主数据与权限基线。",
    ]),
]


def build_plan_docx(path: Path) -> Path:
    body = [_p(TITLE, "Title"), _p("版本 1.0 ｜ 2026-10 ｜ 商务讨论稿")]
    body.append(_table([
        ["项目", "内容"],
        ["客户", CLIENT],
        ["服务方", VENDOR],
        ["周期", "首期 8 周"],
        ["范围", "内容中台 · 渠道投放 · 线索协同 · 经营看板"],
    ]))
    for heading, paragraphs in SECTIONS:
        body.append(_p(heading, "Heading1"))
        for text in paragraphs:
            body.append(_p(text))
    body.append(_p("附：指标口径", "Heading2"))
    body.append(_table([
        ["指标", "口径", "频率"],
        ["内容产出", "已发布且进入渠道的素材数", "周"],
        ["有效线索", "通过资质校验并进入跟进的线索", "日"],
        ["转化周期", "首次触达到签约的中位天数", "月"],
        ["复购率", "近 12 个月重复采购客户占比", "季"],
    ]))
    body.append(_p("以上口径由双方在启动会上确认后固化。"))

    document = ("<?xml version='1.0' encoding='UTF-8'?>"
                "<w:document xmlns:w='http://schemas.openxmlformats.org/wordprocessingml/2006/main'>"
                f"<w:body>{''.join(body)}</w:body></w:document>")
    core = ("<?xml version='1.0' encoding='UTF-8'?>"
            "<cp:coreProperties xmlns:cp='http://schemas.openxmlformats.org/package/2006/"
            "metadata/core-properties' xmlns:dc='http://purl.org/dc/elements/1.1/'>"
            f"<dc:title>{TITLE}</dc:title></cp:coreProperties>")

    path.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as pack:
        pack.writestr("[Content_Types].xml", CONTENT_TYPES)
        pack.writestr("_rels/.rels", RELS)
        pack.writestr("word/document.xml", document)
        pack.writestr("docProps/core.xml", core)
    path.write_bytes(buffer.getvalue())
    return path


if __name__ == "__main__":
    import sys

    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("demo-plan.docx")
    print(build_plan_docx(target), target.stat().st_size, "bytes")
