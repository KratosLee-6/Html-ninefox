"""generators · 5 类内容真实生成器（Html九尾狐 v0.2「多内容」核心）

每个内容类型一个模块，统一契约：
    render(brief: dict, style: dict, assets: dict) -> str  # 完整单文件 HTML

风格由 CSS 变量驱动（_tokens.py 的 preset），feedback --revise 通过
「改 token → 重渲染」实现真实迭代。
"""

from . import _tokens
from .landing import render as render_landing
from .dashboard import render as render_dashboard
from .deck import render as render_deck
from .poster import render as render_poster
from .archdoc import render as render_archdoc
from .doc import render as render_doc

_RENDERERS = {
    "landing": render_landing,
    "dashboard": render_dashboard,
    "deck": render_deck,
    "poster": render_poster,
    "archdoc": render_archdoc,
    "doc": render_doc,
}


def render(intent: str, brief: dict, style: dict, assets: dict) -> str:
    """按内容类型路由到具体生成器；未知类型兜底 landing。

    style 兼容三种输入：preset dict（含 tokens）/ {"preset": …} / None（用默认预设）。
    """
    preset = style.get("preset") if isinstance(style, dict) and "preset" in style else style
    if not isinstance(preset, dict) or "tokens" not in preset:
        preset = dict(_tokens.get_preset(_tokens.DEFAULT_PRESET))
    fn = _RENDERERS.get(intent, render_landing)
    return fn(brief, preset, assets)
