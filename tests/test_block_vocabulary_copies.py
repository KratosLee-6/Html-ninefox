"""The block vocabulary is written down three times, and nothing keeps them agreeing.

What is duplicated
------------------
    rules.py:135        _INTENT_BLOCKS      the authority; read by asset_expert
    pipeline.py:50      _PREVIEW_BLOCKS     byte-identical copy, no import
    user_gallery.py:28  BLOCKS_BY_INTENT    only 4 of the 6 intents

There is no import relationship between them and no test comparing them.
tests/test_rules.py:58 asserts rules._INTENT_BLOCKS against itself.

Why it matters
--------------
Every renderer decides what to emit with `if "nav" in blocks:`. An id nobody
recognises is not an error — that section just silently does not appear, with no
warning. Worse, the fallback `blocks_of(assets) or [hardcoded full set]`
(landing.py:118) hides the mistake rather than surfacing it.

The third copy is the sharper edge. `user_gallery._block_id` does a bare
`BLOCKS_BY_INTENT[intent]` (user_gallery.py:102). It is safe today only because
`_intent` (user_gallery.py:89-97) happens to return just dashboard / deck / doc
/ landing. Add `poster` to `_intent` and that line raises KeyError on the next
gallery import — and nothing in the repository connects the two functions well
enough for a test to notice. That coupling is what these gates make explicit.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from htmlninefox import pipeline, rules, user_gallery  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

AUTHORITY = rules._INTENT_BLOCKS


def test_the_preview_copy_is_identical_to_the_authority() -> None:
    """pipeline._PREVIEW_BLOCKS feeds template preview; drifting from the
    authority means the preview shows a different page than generation makes."""
    assert pipeline._PREVIEW_BLOCKS == AUTHORITY, (
        "两份 blocks 词表已经不一致：\n"
        f"  rules._INTENT_BLOCKS      = {AUTHORITY}\n"
        f"  pipeline._PREVIEW_BLOCKS  = {pipeline._PREVIEW_BLOCKS}\n"
        f"  多出来的 intent: {sorted(set(pipeline._PREVIEW_BLOCKS) - set(AUTHORITY))}\n"
        f"  缺失的 intent: {sorted(set(AUTHORITY) - set(pipeline._PREVIEW_BLOCKS))}\n"
        " 渲染器按 id 做成员判断，多余的 id 会让该 section 静默消失。")


def test_the_gallery_copy_agrees_wherever_it_claims_to_cover() -> None:
    """user_gallery 只覆盖 4 个 intent 是可以的（它不需要全套），但它覆盖的那几个
    必须与权威表逐字一致。"""
    unknown = sorted(set(user_gallery.BLOCKS_BY_INTENT) - set(AUTHORITY))
    assert not unknown, f"user_gallery 里有权威表不存在的 intent：{unknown}"

    drifted = {intent: blocks for intent, blocks in user_gallery.BLOCKS_BY_INTENT.items()
               if blocks != AUTHORITY[intent]}
    assert not drifted, (
        f"user_gallery 的 blocks 词表与权威表不一致：{drifted}\n"
        f"  权威表：{AUTHORITY}")


def test_every_intent_the_gallery_can_infer_is_a_key_it_can_look_up() -> None:
    """This is the one that prevents a real crash.

    `_block_id` does `BLOCKS_BY_INTENT[intent]`. It is safe today only because
    `_intent` returns a subset of those keys — an invariant written down in
    neither place and enforced by nothing.
    """
    inferable = _intents_the_gallery_can_infer()
    missing = sorted(inferable - set(user_gallery.BLOCKS_BY_INTENT))
    assert not missing, (
        f"_intent 可能返回这些 intent：{sorted(inferable)}，"
        f"但 user_gallery.BLOCKS_BY_INTENT 里没有 {missing}。\n"
        f"  _block_id 会对它们做裸字典查找（user_gallery.py:102），下一次导入素材库\n"
        f"  就会 KeyError。补进 BLOCKS_BY_INTENT，或让 _intent 别返回它们。")


def test_block_id_never_raises_for_any_intent_the_gallery_can_infer() -> None:
    """The behavioural version of the invariant above: actually call it.

    Reading _intent's return values out of its source is a text check and would
    be satisfiable by a comment. Calling _block_id is not — and it also covers
    the empty-vocabulary case, where `blocks[min(index, len-1)]` would index -1.
    """
    for intent in sorted(_intents_the_gallery_can_infer()):
        for name in ("封面", "价格", "FAQ", "随便一个名字"):
            for index in (0, 3, 99):
                try:
                    got = user_gallery._block_id(name, intent, index)
                except Exception as exc:  # noqa: BLE001 - that is the point
                    raise AssertionError(
                        f"_block_id({name!r}, {intent!r}, {index}) 抛了 "
                        f"{type(exc).__name__}: {exc}"
                    ) from exc
                assert got in AUTHORITY[intent], (
                    f"_block_id({name!r}, {intent!r}, {index}) 返回了 {got!r}，"
                    f"它不在 {intent} 的词表 {AUTHORITY[intent]} 里")


def _intents_the_gallery_can_infer() -> set[str]:
    """The intents `_intent` can actually return, read from its return statements.

    Parsed rather than grepped so a mention of an intent in a comment or a
    default cannot be mistaken for a possible return value.
    """
    source = (ROOT / "htmlninefox" / "user_gallery.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "_intent")
    found: set[str] = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str):
            found.add(node.value.value)
    assert found, "_intent 里没有解析到任何字面量返回值，解析器可能失效了"
    return found
