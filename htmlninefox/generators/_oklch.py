"""_oklch.py · OKLCH 品牌色约束（v0.9.5，融合 guizang-design 思路）

品牌色不直接用原色 —— 收进当前风格在 OKLCH 空间的明度/彩度范围，
色相保留品牌识别；约束后保障文本对比度（WCAG 2.x ≥4.5:1 正文 / ≥3:1
图形部件），「不直接用原色」写进生成端。

纯 Python 数学（sRGB↔OKLCH 标准 Björn Ottosson 转换），无新依赖。
锚点从 preset 现有 primary/accent 反推 —— 11 家预设零数据变更。
"""
from __future__ import annotations

import math
from typing import Any, Dict

_HEX_RE = __import__("re").compile(r"^#[0-9A-Fa-f]{6}$")

# WCAG 阈值：primary 是按钮底色（配 primary_text 正文文字）→ 4.5:1；
# accent 多用于链接/装饰（配 bg）→ 3:1 图形部件档
_CONTRAST_PRIMARY = 4.5
_CONTRAST_ACCENT = 3.0

# 明度/彩度收域容差：锚点 ± 容差，宁可收窄不可放飞
_L_TOLERANCE = 0.10
_C_MIN_FLOOR = 0.04          # 彩度下限（太灰就不像品牌色了）
_C_MAX_FACTOR = 1.25         # 彩度上限 = 锚点彩度 × 1.25
_C_MAX_SLACK = 0.02
_L_HARD = (0.15, 0.97)       # 对比度救场时的明度硬边界


def _srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _linear_to_srgb(c: float) -> float:
    return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


def hex_to_oklch(hex_color: str) -> tuple[float, float, float]:
    """#RRGGBB → (L, C, H)。H 单位为度 [0, 360)。非法输入返回 (0.5, 0.0, 0.0)。"""
    h = (hex_color or "").lstrip("#")
    if len(h) != 6:
        return (0.5, 0.0, 0.0)
    try:
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    except ValueError:
        return (0.5, 0.0, 0.0)
    r, g, b = (_srgb_to_linear(v) for v in (r, g, b))
    # linear RGB → LMS（OKLab 矩阵），立方根，再转 OKLab
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = l ** (1 / 3), m ** (1 / 3), s ** (1 / 3)
    big_l = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    b2 = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    chroma = math.hypot(a, b2)
    hue = math.degrees(math.atan2(b2, a)) % 360.0
    return (big_l, chroma, hue)


def oklch_to_hex(big_l: float, chroma: float, hue: float) -> str:
    """(L, C, H) → #RRGGBB。分量越界按域 clamp（产物必须永远是合法 hex）。"""
    big_l = min(1.0, max(0.0, big_l))
    chroma = max(0.0, chroma)
    hr = math.radians(hue)
    a, b = chroma * math.cos(hr), chroma * math.sin(hr)
    l_ = big_l + 0.3963377774 * a + 0.2158037573 * b
    m_ = big_l - 0.1055613458 * a - 0.0638541728 * b
    s_ = big_l - 0.0894841775 * a - 1.2914855480 * b
    l_, m_, s_ = l_ ** 3, m_ ** 3, s_ ** 3
    r = +4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_
    g = -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_
    b2 = -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_
    r, g, b2 = (_linear_to_srgb(max(0.0, min(1.0, v))) for v in (r, g, b2))
    return "#{:02X}{:02X}{:02X}".format(round(r * 255), round(g * 255), round(b2 * 255))


def _relative_luminance(hex_color: str) -> float:
    h = (hex_color or "").lstrip("#")
    if len(h) != 6:
        return 0.0
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    r, g, b = (_srgb_to_linear(v) for v in (r, g, b))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def wcag_contrast_ratio(fg_hex: str, bg_hex: str) -> float:
    """WCAG 2.x 对比度比率（白 vs 黑 = 21.0）。"""
    lf, lb = _relative_luminance(fg_hex), _relative_luminance(bg_hex)
    lighter, darker = max(lf, lb), min(lf, lb)
    return (lighter + 0.05) / (darker + 0.05)


def _clamp_into_domain(l: float, c: float, anchor_l: float, anchor_c: float) -> tuple[float, float]:
    lo = max(_L_HARD[0], anchor_l - _L_TOLERANCE)
    hi = min(_L_HARD[1], anchor_l + _L_TOLERANCE)
    c_max = anchor_c * _C_MAX_FACTOR + _C_MAX_SLACK
    c_min = min(_C_MIN_FLOOR, c_max)  # 彩度上限极低的黑白风格也不至于死域
    return min(hi, max(lo, l)), min(c_max, max(c_min, c))


def constrain_brand_color(brand_hex: str, anchor_hex: str, text_hex: str,
                          *, role: str = "primary") -> Dict[str, Any]:
    """把品牌色收进锚点色（preset 原色）附近的明度/彩度域，色相保留。

    返回 {"hex", "L", "C", "H", "contrast", "adjusted", "reason"}。
    对比度不足时沿明度轴向远离文本亮度的方向步进，直到达标或硬边界。
    role="primary" 配 text_hex=primary_text（≥4.5:1）；
    role="accent" 配 text_hex=bg（≥3:1 图形部件档）。
    """
    if not _HEX_RE.match(brand_hex or ""):
        return {"hex": anchor_hex, "adjusted": False, "contrast": 0.0,
                "reason": "品牌色格式非法，保留原色"}
    brand_l, brand_c, brand_h = hex_to_oklch(brand_hex)
    anchor_l, anchor_c, _ = hex_to_oklch(anchor_hex)
    text_l, _, _ = hex_to_oklch(text_hex)
    l, c = _clamp_into_domain(brand_l, brand_c, anchor_l, anchor_c)
    threshold = _CONTRAST_PRIMARY if role == "primary" else _CONTRAST_ACCENT
    hex_out = oklch_to_hex(l, c, brand_h)
    ratio = wcag_contrast_ratio(hex_out, text_hex)
    if ratio < threshold:
        # 明度轴向步进：文本亮 → 往深走；文本暗 → 往亮走
        step = -0.02 if text_l >= 0.5 else 0.02
        while ratio < threshold and _L_HARD[0] < l < _L_HARD[1]:
            l = min(_L_HARD[1], max(_L_HARD[0], l + step))
            hex_out = oklch_to_hex(l, c, brand_h)
            ratio = wcag_contrast_ratio(hex_out, text_hex)
    adjusted = oklch_to_hex(*hex_to_oklch(brand_hex)) != hex_out
    parts = []
    if adjusted:
        if abs(l - brand_l) > 1e-6:
            parts.append(f"明度 {brand_l:.2f}→{l:.2f}")
        if abs(c - brand_c) > 1e-6:
            parts.append(f"彩度 {brand_c:.2f}→{c:.2f}")
        parts.append(f"色相 {brand_h:.0f}° 保留")
    reason = ("品牌色已收进风格域（{}），与文本对比 {:.1f}:1 达标"
              if ratio >= threshold else
              "品牌色已收进风格域（{}），对比 {:.1f}:1（域边界内最优）")
    return {"hex": hex_out, "L": l, "C": c, "H": brand_h,
            "contrast": round(ratio, 2), "adjusted": adjusted,
            "reason": reason.format("、".join(parts) or "原色已在域内", ratio)}
