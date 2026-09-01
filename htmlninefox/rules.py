"""rules.py · 离线规则引擎（Html九尾狐 v0.2 核心）

0 资金原则下的「无 LLM 也可用」底座：
  1. classify_intent()   —— 一句话需求 → 内容类型（landing/dashboard/deck/poster/archdoc）
  2. extract_brief()     —— 一句话需求 → Brief 标准 v0.1 结构化 JSON（离线兜底）
  3. parse_feedback()    —— 口语化反馈 → token 变更指令（离线反馈闭环）

所有规则匹配都返回 evidence（命中关键词），保证可解释、可测试。
LLM 可用时专家层优先走 LLM，规则引擎只作 fallback——但这个 fallback
必须"真实可用"，这是「可上线」与 demo 的分界线。
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

# ============================================================
# 1. 内容类型与意图分类
# ============================================================

CONTENT_TYPES = ("landing", "dashboard", "deck", "poster", "archdoc", "doc")

_INTENT_KEYWORDS: Dict[str, List[str]] = {
    "landing": [
        "落地页", "官网", "首页", "landing", "product page", "产品页",
        "营销页", "推广页", "介绍页", "主页", "saas", "定价", "pricing",
        "hero", "waitlist", "early access",
    ],
    "dashboard": [
        "看板", "仪表盘", "dashboard", "数据面板", "管理后台", "后台",
        "admin", "控制台", "console", "monitor", "监控", "报表", "bi",
        "kpi", "指标", "概览",
    ],
    "deck": [
        "ppt", "发布会", "幻灯片", "slides", "deck", "keynote", "路演",
        "演示", "演讲", "汇报", "分享会", "翻页", "pitch",
    ],
    "poster": [
        "海报", "poster", "宣传单", "传单", "封面图", "banner", "易拉宝",
        "大字报", "招生", "活动宣传", "展板", "邀请函", "announcement",
    ],
    "archdoc": [
        "架构图", "架构", "arch", "architecture",
        "设计文档", "rfc", "技术评审", "系统设计", "流程图",
        "readme", "spec",
    ],
    # 通用文档（报告/方案/纪要/白皮书）——以 HTML 为载体的文档
    "doc": [
        "文档", "报告", "汇报", "纪要", "说明书", "白皮书", "总结",
        "商业方案", "实施方案", "计划书", "doc", "report", "memo", "proposal",
    ],
}

# 每类内容的默认受众 / 成功指标（离线推断用）
_INTENT_DEFAULTS: Dict[str, Dict[str, str]] = {
    "landing": {
        "audience": "目标客户与潜在用户（首次到访）",
        "job_to_be_done": "快速理解产品价值并产生注册/咨询动作",
        "success_metric": "首屏停留 >10s，CTA 点击率 >3%",
    },
    "dashboard": {
        "audience": "内部运营/管理员（每日高频使用）",
        "job_to_be_done": "一眼掌握核心指标并定位异常",
        "success_metric": "关键 KPI 3 秒内可读，异常项可下钻",
    },
    "deck": {
        "audience": "现场/线上听众（大屏投喂）",
        "job_to_be_done": "跟随叙事节奏理解产品/方案主张",
        "success_metric": "每页一个主张，全场节奏 15-20 分钟",
    },
    "poster": {
        "audience": "路过的目标人群（3 秒注意力）",
        "job_to_be_done": "3 秒内接收主题+时间+行动指令",
        "success_metric": "主信息可远距离识别，行动指令清晰",
    },
    "archdoc": {
        "audience": "工程师/技术评审参与者",
        "job_to_be_done": "理解系统分层、依赖与关键决策",
        "success_metric": "评审会上无需额外口头补充",
    },
    "doc": {
        "audience": "相关方/决策者（阅读与评审）",
        "job_to_be_done": "快速掌握背景、要点与结论并做出决策",
        "success_metric": "5 分钟读完可决策，无需口头补充",
    },
}

# 受众/风格词抽取（中文优先，够用即可）
_AUDIENCE_HINTS: List[Tuple[str, str]] = [
    (r"设计师|designer", "设计师/前端"),
    (r"开发者|程序员|工程师|developer", "开发者"),
    (r"企业|b端|to ?b|客户", "企业客户/决策者"),
    (r"学生|校园|大学生", "学生群体"),
    (r"创作者|自媒体|博主", "内容创作者"),
    (r"运营|市场|增长", "运营/市场人员"),
    (r"管理者|老板|ceo|cto", "管理者/决策层"),
]

_TONE_HINTS: List[Tuple[str, str]] = [
    (r"深色|dark|暗黑|夜间", "dark"),
    (r"极简|克制|linear|vercel|notion", "minimal"),
    (r"杂志|编辑|serif|衬线", "editorial"),
    (r"活泼|鲜艳|活力|霓虹|gradient|渐变", "vibrant"),
    (r"专业|企业|商务|稳重|金融", "professional"),
    (r"科技|ai|未来|赛博|tech", "techy"),
]

_BRAND_RE = re.compile(
    r"[「「\"]([\w\u4e00-\u9fff·\- ]{1,20})[」」\"]"          # 「品牌」
    r"|(?:叫做?|名为?|品牌[是为]?)\s*([\w\u4e00-\u9fff·\-]{1,20})"
)

# 每类内容的 must_have 区块（asset_expert 离线规划用）
_INTENT_BLOCKS: Dict[str, List[str]] = {
    "landing": ["nav", "hero", "features", "showcase", "pricing", "faq", "cta_footer"],
    "dashboard": ["topbar", "kpi_row", "charts", "table", "activity"],
    "deck": ["cover", "problem", "solution", "demo", "metrics", "roadmap", "ending"],
    "poster": ["headline", "key_info", "details", "action_bar"],
    "archdoc": ["title", "layer_diagram", "flow", "component_table", "decisions"],
    "doc": ["title", "summary", "sections", "key_points", "table", "conclusion"],
}


def classify_intent(text: str) -> Tuple[str, float, List[str]]:
    """意图分类：返回 (intent, confidence, evidence)。

    confidence = 命中关键词权重归一（命中越多越确信）；
    无命中时按字面兜底为 landing（最高频场景）并给低置信度。
    """
    t = (text or "").lower()
    best, best_hits, best_evidence = "landing", 0, []
    for intent, kws in _INTENT_KEYWORDS.items():
        hits = [k for k in kws if k in t]
        if len(hits) > best_hits:
            best, best_hits, best_evidence = intent, len(hits), hits
    if best_hits == 0:
        return "landing", 0.35, []
    confidence = min(0.95, 0.55 + 0.13 * (best_hits - 1))
    return best, round(confidence, 2), best_evidence


def detect_tone(text: str) -> Tuple[str, List[str]]:
    """从需求文本里抽风格倾向，返回 (tone_key, evidence)。"""
    t = (text or "").lower()
    for pattern, tone in _TONE_HINTS:
        m = re.search(pattern, t)
        if m:
            return tone, [m.group(0)]
    return "minimal", []


_LEAD_VERB_RE = re.compile(
    r"^(请|帮我|帮忙|给我)?(做一个?|做份|做页|写一?份?|设计一?张?|生成一?个?|创建一?个?|制作一?张?|画一?张?)"
)
_TOPIC_MARK_RE = re.compile(r"^(主题是?|主推|关于|介绍|围绕|叫做?|名为?)")


def clean_headline(prompt: str) -> str:
    """从一句话需求提炼可上版面的主标题（去掉动作词和类型词）。"""
    text = (prompt or "").strip()
    clauses = [c.strip() for c in re.split(r"[，,。；;]", text) if c.strip()]
    # 优先取「主题是/主推/关于」后面的从句
    for c in clauses:
        m = _TOPIC_MARK_RE.match(c)
        if m and len(c) > len(m.group(0)):
            return c[len(m.group(0)):].strip()
    # 否则取第一个从句，去掉开头动作词
    head = clauses[0] if clauses else text
    head = _LEAD_VERB_RE.sub("", head).strip()
    return head or text[:40]


def detect_brand(text: str) -> str:
    """尽力抽品牌名；抽不到返回空串。"""
    m = _BRAND_RE.search(text or "")
    if not m:
        return ""
    return (m.group(1) or m.group(2) or "").strip()


def detect_audience(text: str) -> Tuple[str, List[str]]:
    t = (text or "").lower()
    for pattern, audience in _AUDIENCE_HINTS:
        m = re.search(pattern, t)
        if m:
            return audience, [m.group(0)]
    return "", []


# ============================================================
# 2. 离线 Brief 抽取（brief_expert fallback 的真实实现）
# ============================================================

def extract_brief(prompt: str) -> Dict[str, Any]:
    """一句话需求 → Brief 标准 v0.1 结构化 JSON（离线规则版）。

    与 LLM 版输出同构（brief/goal/context/content/style/constraints 五字段
    + confidence + missing_fields），保证下游不需要区分来源。
    """
    prompt = (prompt or "").strip()
    intent, intent_conf, evidence = classify_intent(prompt)
    tone, tone_ev = detect_tone(prompt)
    brand = detect_brand(prompt)
    audience, aud_ev = detect_audience(prompt)
    defaults = _INTENT_DEFAULTS[intent]

    missing: List[str] = []
    if not audience:
        audience = defaults["audience"]
        missing.append("goal.audience")
    if not brand:
        brand = "Your Product"
        missing.append("content.brand")

    # 内容要点：从 prompt 切出短句作为 must_have 候选
    chips = [s.strip() for s in re.split(r"[，,。;；/、]", prompt) if 2 <= len(s.strip()) <= 24]
    must_have = chips[:4] or [defaults["job_to_be_done"]]

    brief = {
        "goal": {
            "type": {"landing": "产品官网", "dashboard": "数据看板", "deck": "演示文稿",
                     "poster": "宣传海报", "archdoc": "技术文档", "doc": "文档/报告"}.get(intent, "产品官网"),
            "audience": audience,
            "job_to_be_done": defaults["job_to_be_done"],
            "success_metric": defaults["success_metric"],
        },
        "context": {
            "device": "通用（响应式）",
            "occasion": intent,
            "emotion": {"dark": "沉浸专注", "minimal": "克制专业", "editorial": "叙事质感",
                        "vibrant": "热情有力", "professional": "稳重可信", "techy": "未来科技"}.get(tone, "克制专业"),
        },
        "content": {
            "brand": brand,
            "core_message": prompt[:80],
            "headline": clean_headline(prompt),
            "must_have": must_have,
            "blocks": list(_INTENT_BLOCKS[intent]),
        },
        "style": {
            "tone": tone,
            "reference": _tone_references(tone, intent),
        },
        "constraints": {
            "forbidden": _tone_forbidden(tone),
            "technical": ["单文件 HTML，无外部依赖", "中文排版，含 viewport meta", "语义化标签"],
        },
    }

    return {
        "brief": brief,
        "confidence": round(min(0.85, 0.45 + intent_conf * 0.4), 2),
        "missing_fields": missing,
        "reasoning": f"离线规则引擎：intent={intent}（evidence={evidence or '默认'}），"
                     f"tone={tone}（evidence={tone_ev or '默认 minimal'}）",
        "_engine": "rules",
    }


def _tone_references(tone: str, intent: str) -> List[str]:
    refs = {
        "dark": ["Linear.app", "Vercel.com", "Raycast.com"],
        "minimal": ["Linear.app", "Notion.so", "Stripe.com"],
        "editorial": [" guizang 电子杂志风", "Medium.com", "The Verge"],
        "vibrant": ["Figma.com", "Duolingo.com", "Stripe.press"],
        "professional": ["Stripe.com", "IBM.com", "McKinsey.com"],
        "techy": ["OpenAI.com", "Vercel.com", "HuggingFace.co"],
    }.get(tone, ["Linear.app"])
    if intent == "deck":
        refs = ["guizang-ppt 电子杂志风", "Apple Keynote"] + refs[:1]
    if intent == "dashboard":
        refs = ["Grafana", "Linear Insights", "Vercel Analytics"]
    return refs


def _tone_forbidden(tone: str) -> List[str]:
    base = ["不要 emoji 堆砌当装饰", "不要超过 3 种主色", "不要默认浏览器蓝链接"]
    extra = {
        "dark": ["不要纯黑 #000 背景（用 #0A0A0B 级别的近黑）", "不要低对比灰字（对比度 ≥ 4.5:1）"],
        "minimal": ["不要渐变背景大色块", "不要插画师风格插图"],
        "vibrant": ["不要满屏高饱和（留白呼吸）", "不要彩虹渐变文字"],
        "editorial": ["不要无衬线通篇（标题需衬线对比）", "不要居中对称的 PPT 版式"],
        "professional": ["不要手写体", "不要游戏化元素"],
        "techy": ["不要廉价的发光标题", "不要 3D 挤压文字"],
    }.get(tone, [])
    return base + extra


# ============================================================
# 3. 离线反馈解析（feedback_expert fallback 的真实实现）
# ============================================================

_HEX_RE = re.compile(r"#[0-9A-Fa-f]{6}\b")
_SIZE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(px|rem|%)")

_FEEDBACK_RULES: List[Dict[str, Any]] = [
    # 全局明暗
    {"re": r"深色|暗一?[点些]|dark", "neg": r"浅|亮", "target": "global.theme", "op": "theme_dark",
     "suggestion": "切换为深色主题（背景近黑/文字浅灰/主色提亮）", "confidence": 0.75},
    {"re": r"浅色|亮一?[点些]|light", "neg": r"深", "target": "global.theme", "op": "theme_light",
     "suggestion": "切换为浅色主题（浅底深字）", "confidence": 0.75},
    # 颜色（先判明确方向，通用规则避开含方向的句子）
    {"re": r"浅一?[点些]|亮一?[点些]", "neg": None, "target": "global.colors", "op": "color_lighten",
     "suggestion": "主色整体提亮一档（HSL 亮度 +8%）", "confidence": 0.65},
    {"re": r"深一?[点些]|暗一?[点些]", "neg": None, "target": "global.colors", "op": "color_shift",
     "suggestion": "主色整体加深一档（HSL 亮度 -8%）", "confidence": 0.65},
    {"re": r"颜色|配色|色彩|主色|color", "neg": r"深|浅|亮|暗", "target": "global.colors", "op": "color_shift",
     "suggestion": "主色整体加深/调整一档（HSL 亮度 -8%）", "confidence": 0.6},
    # 圆角
    {"re": r"圆角|更圆|radius", "neg": None, "target": "global.radius", "op": "radius_up",
     "suggestion": "卡片圆角 +4px（更柔和）", "confidence": 0.7},
    {"re": r"锐利|硬朗|直角", "neg": None, "target": "global.radius", "op": "radius_down",
     "suggestion": "圆角减半（更锐利）", "confidence": 0.7},
    # 字号
    {"re": r"字.{0,3}大|大.{0,3}字|标题.{0,4}大|font.?size.{0,6}(up|big)", "neg": r"小一?点",
     "target": "global.font_scale", "op": "font_up", "suggestion": "全局字号 +8%", "confidence": 0.7},
    {"re": r"字.{0,3}小|小.{0,3}字|font.?size.{0,6}(down|small)", "neg": None,
     "target": "global.font_scale", "op": "font_down", "suggestion": "全局字号 -8%", "confidence": 0.7},
    # 间距
    {"re": r"宽松|留白|spacing.{0,6}(up|more)|呼吸", "neg": None,
     "target": "global.spacing", "op": "spacing_up", "suggestion": "区块间距 ×1.2（更宽松）", "confidence": 0.65},
    {"re": r"紧凑|密一?点|spacing.{0,6}(down|less)", "neg": None,
     "target": "global.spacing", "op": "spacing_down", "suggestion": "区块间距 ×0.85（更紧凑）", "confidence": 0.65},
    # 参考某产品
    {"re": r"参考\s*(linear|vercel|stripe|notion|figma|shadcn|apple)", "neg": None,
     "target": "global.reference", "op": "reference_preset", "suggestion": "对齐指定产品的风格预设",
     "confidence": 0.8},
]


def parse_feedback(note: str) -> Dict[str, Any]:
    """口语化反馈 → 结构化 token 变更（离线版）。

    返回与 feedback_expert LLM 版同构：
    {target_element, suggestion, confidence, actionable, tokens_extracted, rules}
    离线策略：宁可信其可用——命中规则即 actionable；完全不命中则 ask_user。
    """
    note = (note or "").strip()
    if not note:
        return {"actionable": False, "ask_user": "反馈内容为空", "confidence": 0.0,
                "target_element": "", "suggestion": "", "tokens_extracted": {}, "rules": []}

    tokens: Dict[str, Any] = {}
    rules_hit: List[str] = []
    suggestions: List[str] = []
    conf = 0.0

    for rule in _FEEDBACK_RULES:
        if re.search(rule["re"], note, re.IGNORECASE) and not (rule["neg"] and re.search(rule["neg"], note, re.IGNORECASE)):
            rules_hit.append(rule["op"])
            suggestions.append(rule["suggestion"])
            conf = max(conf, rule["confidence"])

    # 显式 hex 颜色
    hexes = _HEX_RE.findall(note)
    if hexes:
        tokens["primary_override"] = hexes[0].upper()
        rules_hit.append("hex_color")
        suggestions.append(f"主色覆盖为 {hexes[0].upper()}")
        conf = max(conf, 0.9)

    # 显式字号
    sizes = _SIZE_RE.findall(note)
    if sizes and re.search(r"字号|字体大小|font", note, re.IGNORECASE):
        tokens["font_size_override"] = f"{sizes[0][0]}{sizes[0][1]}"
        rules_hit.append("font_size")
        suggestions.append(f"基础字号设为 {sizes[0][0]}{sizes[0][1]}")
        conf = max(conf, 0.85)

    # 参考产品 → 预设
    m = re.search(r"参考\s*(linear|vercel|stripe|notion|figma|shadcn|apple)", note, re.IGNORECASE)
    if m:
        tokens["reference_preset"] = m.group(1).lower()
        conf = max(conf, 0.8)

    if not rules_hit:
        return {
            "actionable": False,
            "ask_user": "离线解析未能定位反馈（可说明：颜色/字号/间距/圆角/明暗，或给出 hex 值）；"
                        "安装 LLM 依赖后可解析任意口语反馈",
            "confidence": 0.3,
            "target_element": "",
            "suggestion": "",
            "tokens_extracted": {},
            "rules": [],
        }

    return {
        "target_element": "global",
        "suggestion": "；".join(suggestions[:3]),
        "confidence": conf,
        "actionable": True,
        "tokens_extracted": tokens,
        "rules": rules_hit,
    }
