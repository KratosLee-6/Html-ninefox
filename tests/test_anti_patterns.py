"""反模式门禁（v0.9 · impeccable B 档）。

检测思路参考 pbakaus/impeccable（88.7k★ · Apache-2.0）的确定性检测器，
规则为 Html九尾狐 自研实现，只保留与本设计系统相关的确定性子集：

1. 禁 bounce / elastic / 过冲缓动 —— 动效单时钟（v0.8.2）的自然延伸；
2. 禁卡片套卡片（.card 内嵌 .card）—— 反模式清单头号项；
3. 禁纯黑 #000 —— 一律用带色相的深色（本系统为 #0A0A0A 系）；
   color-mix 内与黑混合属于「调暗」而非「纯黑上灰字」，放行。

「彩底灰字」需要对比度上下文，确定性实现成本高于收益，归入读屏器审计
（v0.9 后续），此处不设。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "htmlninefox" / "server" / "static"
GALLERY = STATIC / "templates" / "gallery"

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

_EASING_RE = re.compile(r"bounce|elastic|ease-in-out-back|cubic-bezier\([^)]*"
                        r"(?:[2-9]\d\d|,\s*[2-9]\d)", re.I)
_CARD_NEST_RE = re.compile(r"\.card[^{},]*\.card")
_PURE_BLACK_RE = re.compile(r"#000\b|#000000\b", re.I)


def _css_targets() -> list[Path]:
    return list(STATIC.glob("*.css")) + list(GALLERY.glob("*.html"))


def test_no_bounce_or_elastic_easing():
    """动效单时钟的延伸：过冲缓动（bounce/elastic/back）一律不进产物。"""
    hits = []
    for path in _css_targets():
        for i, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if _EASING_RE.search(line):
                hits.append(f"{path.name}:{i}")
    assert not hits, f"过冲缓动出现于：{hits}"


def test_no_card_inside_card():
    """反模式清单头号项：卡片套卡片。选择器级检测（DOM 级归浏览器走查）。"""
    hits = []
    for path in _css_targets():
        text = path.read_text(encoding="utf-8", errors="replace")
        if _CARD_NEST_RE.search(text):
            hits.append(path.name)
    assert not hits, f"卡片套卡片选择器出现于：{hits}"


def test_no_pure_black_outside_mix():
    """纯黑一律带色相（本系统 #0A0A0A 系）；color-mix 调暗放行。"""
    hits = []
    for path in _css_targets():
        for i, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if _PURE_BLACK_RE.search(line) and "color-mix" not in line:
                hits.append(f"{path.name}:{i}")
    assert not hits, f"纯黑出现于（请改用带色相深色或 color-mix 调暗）：{hits}"
