"""_tokens.py · 审美模板库 · 风格预设（Html九尾狐 v0.2「三重沉淀」的 token 层）

11 个风格预设 × 12 个 token（CSS 变量）。所有生成器只消费 token，
不 hardcode 颜色 —— 反馈迭代 = 改 token → 重渲染。

preset 结构：
{
  "id": "linear-light",
  "name": "Linear 浅色 · 克制工程师风",
  "tokens": {"bg": ..., "surface": ..., "text": ..., "muted": ...,
             "primary": ..., "primary_text": ..., "accent": ...,
             "border": ..., "radius": ..., "font_body": ..., "font_display": ...,
             "space": ...},
  "dark": False,
  "match_keywords": [...],
}
"""

from __future__ import annotations

import colorsys
from typing import Any, Dict

PRESETS: Dict[str, Dict[str, Any]] = {
    "linear-light": {
        "id": "linear-light",
        "name": "Linear 浅色 · 克制工程师风",
        "dark": False,
        "match_keywords": ["极简", "克制", "linear", "saas", "工具", "效率", "浅色"],
        "tokens": {
            "bg": "#FBFBFA", "surface": "#FFFFFF", "text": "#1A1A1A",
            "muted": "#6B6F76", "primary": "#5E6AD2", "primary_text": "#FFFFFF",
            "accent": "#0EA5E9", "border": "#E8E8E4", "radius": "10px",
            "font_body": "'Inter','PingFang SC','Microsoft YaHei',sans-serif",
            "font_display": "'Inter','PingFang SC','Microsoft YaHei',sans-serif",
            "space": "72px",
        },
    },
    "vercel-dark": {
        "id": "vercel-dark",
        "name": "Vercel 深色 · 极客暗夜",
        "dark": True,
        "match_keywords": ["深色", "dark", "暗", "geek", "开发者", "代码", "夜间"],
        "tokens": {
            "bg": "#0A0A0B", "surface": "#141415", "text": "#EDEDED",
            "muted": "#8F8F8F", "primary": "#4F46E5", "primary_text": "#FFFFFF",
            "accent": "#22D3EE", "border": "#26262A", "radius": "8px",
            "font_body": "'Inter','PingFang SC','Microsoft YaHei',sans-serif",
            "font_display": "'Inter','PingFang SC','Microsoft YaHei',sans-serif",
            "space": "64px",
        },
    },
    "guizang-magazine": {
        "id": "guizang-magazine",
        "name": "归藏电子杂志 · 衬线编辑风",
        "dark": False,
        "match_keywords": ["杂志", "编辑", "衬线", "serif", "叙事", "文化", "ppt", "发布会", "演讲"],
        "tokens": {
            "bg": "#F7F3EC", "surface": "#FFFDF8", "text": "#211D16",
            "muted": "#7A7263", "primary": "#B4530A", "primary_text": "#FFFDF8",
            "accent": "#3F6C51", "border": "#E5DDCE", "radius": "4px",
            "font_body": "'Georgia','Noto Serif SC','Songti SC','SimSun',serif",
            "font_display": "'Georgia','Noto Serif SC','Songti SC','SimSun',serif",
            "space": "88px",
        },
    },
    "shadcn-dashboard": {
        "id": "shadcn-dashboard",
        "name": "shadcn 看板 · 中性数据风",
        "dark": True,
        "match_keywords": ["看板", "dashboard", "后台", "admin", "数据", "监控", "bi"],
        "tokens": {
            "bg": "#09090B", "surface": "#111113", "text": "#FAFAFA",
            "muted": "#A1A1AA", "primary": "#10B981", "primary_text": "#052E22",
            "accent": "#F59E0B", "border": "#27272A", "radius": "12px",
            "font_body": "'Inter','PingFang SC','Microsoft YaHei',sans-serif",
            "font_display": "'Inter','PingFang SC','Microsoft YaHei',sans-serif",
            "space": "48px",
        },
    },
    "vibrant-poster": {
        "id": "vibrant-poster",
        "name": "高活力海报 · 大字报风",
        "dark": True,
        "match_keywords": ["海报", "poster", "宣传", "活动", "鲜艳", "活力", "霓虹", "大字"],
        "tokens": {
            "bg": "#12061F", "surface": "#1D0B33", "text": "#FFF7ED",
            "muted": "#C4B5FD", "primary": "#F43F5E", "primary_text": "#FFFFFF",
            "accent": "#FACC15", "border": "#3B1358", "radius": "16px",
            "font_body": "'Inter','PingFang SC','Microsoft YaHei',sans-serif",
            "font_display": "'Inter','PingFang SC','Microsoft YaHei',sans-serif",
            "space": "56px",
        },
    },
    "doc-clean": {
        "id": "doc-clean",
        "name": "Stripe 文档 · 专业清爽",
        "dark": False,
        "match_keywords": ["文档", "架构", "技术", "方案", "评审", "专业", "企业", "白皮书"],
        "tokens": {
            "bg": "#FFFFFF", "surface": "#F6F8FA", "text": "#0F172A",
            "muted": "#64748B", "primary": "#635BFF", "primary_text": "#FFFFFF",
            "accent": "#0EA5E9", "border": "#E2E8F0", "radius": "8px",
            "font_body": "'Inter','PingFang SC','Microsoft YaHei',sans-serif",
            "font_display": "'Inter','PingFang SC','Microsoft YaHei',sans-serif",
            "space": "64px",
        },
    },
    "fox-pixel-garden": {
        "id": "fox-pixel-garden",
        "name": "九尾狐像素花园 · 深蓝与薄荷",
        "dark": False,
        "visual_system": "pixel-garden",
        "origin": "Html九尾狐原创 · 参考细像素叙事语言",
        "match_keywords": ["像素", "pixel", "自然", "花园", "叙事", "蓝绿"],
        "tokens": {
            "bg": "#F3F0E8", "surface": "#FFFDF7", "text": "#11253B",
            "muted": "#5E716F", "primary": "#173C8F", "primary_text": "#F8F5EA",
            "accent": "#49B894", "border": "#B8C8BD", "radius": "3px",
            "font_body": "'Inter','PingFang SC','Microsoft YaHei',sans-serif",
            "font_display": "'Iowan Old Style','Georgia','Noto Serif SC',serif",
            "space": "92px",
        },
    },
    "fox-duotone-studio": {
        "id": "fox-duotone-studio",
        "name": "九尾狐双色工作室 · 暖白与电光蓝",
        "dark": False,
        "visual_system": "duotone-studio",
        "origin": "Html九尾狐原创 · 参考暖白产品页与深灰功能区",
        "match_keywords": ["双色", "duotone", "高级灰", "产品", "crm", "工作台"],
        "tokens": {
            "bg": "#F4F2EC", "surface": "#FBFAF6", "text": "#23262B",
            "muted": "#70747C", "primary": "#3477F6", "primary_text": "#FFFFFF",
            "accent": "#F0B24D", "border": "#D9D9D4", "radius": "14px",
            "font_body": "'Inter','PingFang SC','Microsoft YaHei',sans-serif",
            "font_display": "'Inter Tight','Inter','PingFang SC',sans-serif",
            "space": "84px",
        },
    },
    "fox-editorial-ink": {
        "id": "fox-editorial-ink",
        "name": "九尾狐编辑墨水 · 纸感叙事",
        "dark": False,
        "visual_system": "editorial-ink",
        "origin": "Html九尾狐独立适配 · Editorial / E-Ink 设计语言",
        "match_keywords": ["电子墨水", "纸感", "editorial", "杂志", "叙事", "观点"],
        "tokens": {
            "bg": "#F1EFE8", "surface": "#E8E4DB", "text": "#17191B",
            "muted": "#696860", "primary": "#173B67", "primary_text": "#F7F4EC",
            "accent": "#B95F43", "border": "#BDB9AF", "radius": "0px",
            "font_body": "'Inter','Noto Sans SC','PingFang SC',sans-serif",
            "font_display": "'Iowan Old Style','Georgia','Noto Serif SC',serif",
            "space": "96px",
        },
    },
    "fox-swiss-signal": {
        "id": "fox-swiss-signal",
        "name": "九尾狐瑞士信号 · 灰白与安全橙",
        "dark": False,
        "visual_system": "swiss-signal",
        "origin": "Html九尾狐独立适配 · Swiss International 设计语言",
        "match_keywords": ["瑞士", "swiss", "网格", "理性", "事实", "橙色"],
        "tokens": {
            "bg": "#F2F1EC", "surface": "#E5E6E3", "text": "#151617",
            "muted": "#5D6268", "primary": "#FF6B35", "primary_text": "#FFFFFF",
            "accent": "#2257D8", "border": "#AEB2B3", "radius": "0px",
            "font_body": "'Inter','Noto Sans SC','PingFang SC',sans-serif",
            "font_display": "'Arial Narrow','Inter Tight','PingFang SC',sans-serif",
            "space": "80px",
        },
    },
    "fox-soft-silver": {
        "id": "fox-soft-silver",
        "name": "九尾狐柔银界面 · 奶油灰与薄荷",
        "dark": False,
        "visual_system": "soft-silver",
        "origin": "Html九尾狐 Huashu Design 适配层",
        "match_keywords": ["柔和", "soft", "apple", "银色", "奶油", "原型"],
        "tokens": {
            "bg": "#ECEDEA", "surface": "#F8F8F5", "text": "#292D31",
            "muted": "#767B80", "primary": "#407D70", "primary_text": "#FFFFFF",
            "accent": "#D88B5B", "border": "#D2D5D1", "radius": "20px",
            "font_body": "'Inter','PingFang SC','Microsoft YaHei',sans-serif",
            "font_display": "'Inter Tight','Inter','PingFang SC',sans-serif",
            "space": "88px",
        },
    },
}

DEFAULT_PRESET = "linear-light"

# 参考产品 → 预设（反馈 "参考 vercel" 直接切预设）
REFERENCE_MAP = {
    "linear": "linear-light", "vercel": "vercel-dark", "stripe": "doc-clean",
    "notion": "linear-light", "figma": "vibrant-poster", "shadcn": "shadcn-dashboard",
    "apple": "linear-light", "guizang": "guizang-magazine",
}

# 每类内容 × 每种 tone 的默认预设（style_expert 规则匹配用）
INTENT_TONE_PRESET = {
    "landing": {"dark": "vercel-dark", "minimal": "linear-light", "editorial": "guizang-magazine",
                "vibrant": "vibrant-poster", "professional": "doc-clean", "techy": "vercel-dark"},
    "dashboard": {"dark": "shadcn-dashboard", "minimal": "doc-clean", "editorial": "doc-clean",
                  "vibrant": "shadcn-dashboard", "professional": "doc-clean", "techy": "shadcn-dashboard"},
    "deck": {"dark": "vercel-dark", "minimal": "guizang-magazine", "editorial": "guizang-magazine",
             "vibrant": "vibrant-poster", "professional": "doc-clean", "techy": "vercel-dark"},
    "poster": {"dark": "vibrant-poster", "minimal": "linear-light", "editorial": "guizang-magazine",
               "vibrant": "vibrant-poster", "professional": "doc-clean", "techy": "vibrant-poster"},
    "archdoc": {"dark": "vercel-dark", "minimal": "doc-clean", "editorial": "doc-clean",
                "vibrant": "doc-clean", "professional": "doc-clean", "techy": "vercel-dark"},
    "doc": {"dark": "vercel-dark", "minimal": "doc-clean", "editorial": "guizang-magazine",
            "vibrant": "doc-clean", "professional": "doc-clean", "techy": "doc-clean"},
}


def get_preset(preset_id: str) -> Dict[str, Any]:
    return PRESETS.get(preset_id, PRESETS[DEFAULT_PRESET])


def match_preset(brief: dict, intent: str) -> Dict[str, Any]:
    """规则匹配：brief.style.tone + 内容类型 + 命中关键词 → 预设。

    返回 (preset, matched_by)；此处返回 dict，matched_by 放 preset["_matched_by"]。
    """
    payload = brief.get("brief", brief) if isinstance(brief, dict) else {}
    style = payload.get("style", {}) or {}
    tone = style.get("tone", "minimal")

    # 1) intent × tone 查表
    preset_id = INTENT_TONE_PRESET.get(intent, {}).get(tone)
    matched_by = f"intent×tone({intent}×{tone})"

    # 2) 用户原文覆盖（core_message 是用户原话；不扫机器生成的 reference）
    text = str(payload.get("content", {}).get("core_message", "")).lower()
    for kw, pid in REFERENCE_MAP.items():
        if kw in text:
            preset_id, matched_by = pid, f"reference:{kw}"
            break

    # 3) 拷贝返回（深拷 tokens，避免微调/反馈污染全局预设库）
    preset = get_preset(preset_id or DEFAULT_PRESET)
    preset = {**preset, "tokens": dict(preset["tokens"]), "_matched_by": matched_by}
    return preset


def css_vars(tokens: Dict[str, str]) -> str:
    """token dict → :root CSS 变量块。"""
    return "\n".join(f"  --fox-{k}: {v};" for k, v in tokens.items())


def shift_color(hex_color: str, dl: float) -> str:
    """HSL 亮度偏移（反馈 '颜色深一点/浅一点' 用）。dl>0 变亮。"""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return hex_color
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    hh, ll, ss = colorsys.rgb_to_hls(r, g, b)
    ll = max(0.0, min(1.0, ll + dl))
    r, g, b = colorsys.hls_to_rgb(hh, ll, ss)
    return "#{:02X}{:02X}{:02X}".format(round(r * 255), round(g * 255), round(b * 255))


def scale_px(value: str, factor: float, minimum: float = 0.0) -> str:
    """'16px' → 按 factor 缩放；非 px 值原样返回。"""
    v = str(value).strip()
    if v.endswith("px"):
        try:
            return f"{max(minimum, round(float(v[:-2]) * factor))}px"
        except ValueError:
            return v
    return v


def apply_feedback(preset: Dict[str, Any], tokens_extracted: Dict[str, Any],
                   rules: list[str] | None = None) -> Dict[str, Any]:
    """把反馈解析出的变更应用到 token —— 真实迭代的核心。

    支持：theme_dark/theme_light、color_shift、radius_up/down、
    font_up/down、spacing_up/down、primary_override、font_size_override、
    reference_preset（直接切预设）。
    """
    rules = rules or []
    new = {**preset, "tokens": dict(preset["tokens"]), "_matched_by": preset.get("_matched_by", "feedback")}
    t = new["tokens"]

    if "reference_preset" in (tokens_extracted or {}):
        base = get_preset(REFERENCE_MAP.get(tokens_extracted["reference_preset"], preset["id"]))
        t.update(base["tokens"])
        new["id"] = base["id"]
        new["dark"] = base["dark"]
        new["_matched_by"] = f"feedback:reference({tokens_extracted['reference_preset']})"

    if tokens_extracted and tokens_extracted.get("primary_override"):
        t["primary"] = tokens_extracted["primary_override"]
    if tokens_extracted and tokens_extracted.get("font_size_override"):
        t["_font_base"] = tokens_extracted["font_size_override"]

    for rule in rules:
        if rule == "theme_dark" and not new["dark"]:
            t.update({"bg": "#0A0A0B", "surface": "#141415", "text": "#EDEDED",
                      "muted": "#8F8F8F", "border": "#26262A"})
            t["primary"] = shift_color(t["primary"], 0.12)
            new["dark"] = True
        elif rule == "theme_light" and new["dark"]:
            t.update({"bg": "#FBFBFA", "surface": "#FFFFFF", "text": "#1A1A1A",
                      "muted": "#6B6F76", "border": "#E8E8E4"})
            t["primary"] = shift_color(t["primary"], -0.10)
            new["dark"] = False
        elif rule == "color_shift":
            t["primary"] = shift_color(t["primary"], -0.08)
            t["accent"] = shift_color(t["accent"], -0.08)
        elif rule == "color_lighten":
            t["primary"] = shift_color(t["primary"], 0.08)
            t["accent"] = shift_color(t["accent"], 0.08)
        elif rule == "radius_up":
            t["radius"] = scale_px(t["radius"], 1.0, 0) if not t["radius"].endswith("px") else \
                f"{min(24, int(float(t['radius'][:-2])) + 4)}px"
        elif rule == "radius_down":
            try:
                t["radius"] = f"{max(0, int(float(t['radius'][:-2]) // 2))}px"
            except ValueError:
                pass
        elif rule == "font_up":
            t["_font_scale"] = min(1.4, float(t.get("_font_scale", 1.0)) * 1.08)
        elif rule == "font_down":
            t["_font_scale"] = max(0.7, float(t.get("_font_scale", 1.0)) * 0.92)
        elif rule == "spacing_up":
            t["space"] = scale_px(t["space"], 1.2, 16)
        elif rule == "spacing_down":
            t["space"] = scale_px(t["space"], 0.85, 16)

    return new


def tokens_to_style_md(preset: Dict[str, Any], intent: str) -> str:
    t = preset["tokens"]
    lines = [
        f"# Style Decision（{preset['name']}）", "",
        f"- **内容类型**: `{intent}`",
        f"- **匹配依据**: {preset.get('_matched_by', 'rules')}",
        f"- **明暗**: {'深色' if preset['dark'] else '浅色'}", "",
        "## Tokens（CSS 变量）", "",
        "| token | 值 |", "|---|---|",
    ]
    for k, v in t.items():
        if not k.startswith("_"):
            lines.append(f"| --fox-{k} | `{v}` |")
    lines += ["", "> 反馈迭代 = 修改本表 token 后重渲染（`htmlninefox feedback --revise`）。", ""]
    return "\n".join(lines)
