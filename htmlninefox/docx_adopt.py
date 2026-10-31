"""兼容别名（v0.9 更名）：内容已迁至 htmlninefox/intake_adopt.py。

模块服务全部进料格式的采纳链；旧导入路径保留至 v0.10。
"""
from .intake_adopt import *  # noqa: F401,F403
from .intake_adopt import AdoptedPage, apply_overrides, adopt, sections_from_outline  # noqa: F401
