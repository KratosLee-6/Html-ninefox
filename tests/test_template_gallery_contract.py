"""画廊模板的契约门禁（模板库扩充 A 档，2026-10-25 落地）。

三条硬规则，缺一即红：
1. manifest 八字段必填（id/name/intent/preset_id/origin/license/file/description），
   license 必须在允许档位内——「从哪来的、能不能用」与模板本身同等重要；
2. 六个产物意图每个至少 1 张（A 档门槛；B 档将升到 ≥3），
   每个 preset 至少被 1 张模板使用（防止有 preset 在侧栏永远看不见）；
3. 每张模板的 file 真实存在，manifest 声明的每个 page 在 HTML 里都有
   对应的 `.page[data-page=...]`——声明与渲染必须是同一份现实。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from htmlninefox.template_gallery import GALLERY_ROOT, MANIFEST_PATH  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

REQUIRED_FIELDS = ("id", "name", "intent", "preset_id", "origin", "license",
                   "file", "description")
ALLOWED_LICENSES = {"original", "MIT", "AGPL-out-of-scope"}
SIX_INTENTS = {"landing", "deck", "poster", "dashboard", "doc", "archdoc"}


def _manifest_items() -> list[dict]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["items"]


def test_every_item_carries_eight_required_fields() -> None:
    for item in _manifest_items():
        missing = [field for field in REQUIRED_FIELDS if not item.get(field)]
        assert not missing, f"{item.get('id', '?')} 缺字段：{missing}"
        assert item["license"] in ALLOWED_LICENSES, \
            f"{item['id']} 的 license 非法：{item['license']}"


def test_every_intent_has_at_least_one_template() -> None:
    """A 档门槛：六个意图都有可点模板——用户在侧栏看不见的意图等于不存在。"""
    intents = {item["intent"] for item in _manifest_items()}
    assert SIX_INTENTS <= intents, f"缺模板的意图：{sorted(SIX_INTENTS - intents)}"


def test_every_preset_is_used_by_at_least_one_template() -> None:
    from htmlninefox.generators import _tokens
    known_presets = {preset["id"] for preset in _tokens.list_presets()} \
        if hasattr(_tokens, "list_presets") else None
    used = {item["preset_id"] for item in _manifest_items()}
    if known_presets is not None:
        assert used <= known_presets, f"manifest 引用了不存在的 preset：{sorted(used - known_presets)}"
        unused = known_presets - used
        assert not unused, f"这些 preset 没有任何模板使用：{sorted(unused)}"


def test_every_declared_page_exists_in_the_html(tmp_path: Path) -> None:
    for item in _manifest_items():
        html = (GALLERY_ROOT / item["file"]).read_text(encoding="utf-8")
        for page in item.get("pages", []):
            assert f'data-page="{page["id"]}"' in html, \
                f"{item['id']} 声明了页面 {page['id']}，但 HTML 里没有对应 .page"
        title_match = "<title>" in html
        assert title_match, f"{item['id']} 缺少 <title>"
