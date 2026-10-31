"""兼容别名（v0.9 更名）：内容已迁至 htmlninefox/intake_proposal.py。

该模块自 v0.8.4 起服务全部进料格式（DOCX/PPTX/PDF），名字不再只属于 docx。
本 shim 保留旧导入路径，预计 v0.10 移除。
"""
from .intake_proposal import *  # noqa: F401,F403
from .intake_proposal import INTENTS, ImagePlanItem, Proposal, propose  # noqa: F401
