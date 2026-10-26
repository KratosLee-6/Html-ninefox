"""产物预览 iframe 的 sandbox 门禁（v0.8.4 顺畅性走查产物）。

走查抓到的真问题：画布产物节点缩略图与检查器文件卡缩略图的 sandbox 只有
`allow-same-origin`——用户自己生成的页面（含动效系统）在这两处预览是死的，
控制台还刷 Blocked script execution 报错。修复后与 `#preview-frame` 同待遇
（`allow-scripts allow-same-origin`，内容是用户本机自己的产物）。

反向约束：intake 候选预览加载的是**外部网站**，必须保持无脚本——这条同时
锁死，防止「顺手统一」把不可信内容也放开。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "htmlninefox" / "server" / "static"

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def test_artifact_preview_iframes_allow_scripts():
    fox_core = (STATIC / "fox-core.js").read_text(encoding="utf-8")
    assert fox_core.count('sandbox="allow-scripts allow-same-origin"') >= 2, \
        "产物节点缩略图与文件卡缩略图必须允许脚本（用户自己的产物，动效要能动）"
    assert 'sandbox="allow-same-origin"' not in fox_core, \
        "存在只给 allow-same-origin 的 iframe——产物预览会静默变死页"


def test_intake_candidate_preview_stays_scriptless():
    """外部站点进不了的门：intake 候选预览不得引入 allow-scripts。"""
    intake = (STATIC / "lifecycle-intake.js").read_text(encoding="utf-8")
    assert "allow-scripts" not in intake, \
        "intake 候选预览加载外部网站，不允许脚本（SSRF/许可三档的既有边界）"
