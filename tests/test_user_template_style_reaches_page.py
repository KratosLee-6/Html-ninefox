"""A page's colours must actually reach the page the user generates.

This is a live bug, found while designing v0.7. The v0.7 design doc claimed
"the style half already has a bridge"; it does not, and the bridge is broken in
two places that compound.

  1. pipeline.py:203 resolves a template with `_tokens.get_preset(template)`,
     which is a built-in table lookup with a silent fallback. The preview path
     at pipeline.py:510-518 resolves user templates correctly. So a user
     previews a template in the page's own colours, presses generate, and gets
     the default palette — with nothing logged.

  2. `build_style_preset` (intake.py:1047) returns `colors` and `fonts` and no
     `tokens` key at all, while every consumer reads `tokens`
     (list_templates does `data.get("tokens", {})`, the generators read
     `preset["tokens"]`). So for a real intake preset there is nothing for even
     the preview to pick up: the colours sit in the file under keys nobody
     reads.

The gate below is written against the user-visible property, not the internals:
import a page as a style preset, generate, and read the colour out of the CSS.
Reading the resolution code and concluding would have been the mistake this
repository keeps making.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from htmlninefox import intake, pipeline  # noqa: E402
from htmlninefox.generators import _tokens  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# In no built-in preset, so finding it in a product page cannot be a coincidence.
SIGNATURE = "#FF00AA"
CANDIDATE = {
    "candidate_id": "c-probe",
    "title": "探针候选",
    "source": "probe",
    "license_class": "reference",
    "tokens": {"colors": [SIGNATURE, "#00FF00"], "fonts": ["ProbeDisplay", "ProbeBody"]},
}


def _assert_not_a_builtin(candidate: dict) -> None:
    """A signature that happens to equal a built-in colour proves nothing."""
    blob = json.dumps(_tokens.PRESETS, ensure_ascii=False).lower()
    for color in candidate["tokens"]["colors"]:
        assert color.lower() not in blob, (
            f"探针色 {color} 恰好和某个内置预设相同，这条门禁会假绿")


def test_the_style_preset_a_page_produces_has_the_shape_consumers_read() -> None:
    """`tokens` is the key every consumer reads. build_style_preset must emit it.

    Not a text check on a function name: the assertion is that the produced dict
    has the key `list_templates` and the generators actually look up.
    """
    preset = intake.build_style_preset(dict(CANDIDATE))
    assert "tokens" in preset, (
        f"build_style_preset 没有产出 tokens 键，消费方读不到任何东西。"
        f"它产出的键：{sorted(preset)}；颜色被放在 {sorted(preset.get('colors', {}))}，"
        f"而 list_templates 读的是 data.get('tokens', {{}})"
    )
    tokens = preset["tokens"]
    for key in ("primary", "accent", "bg"):
        assert key in tokens, f"tokens 里没有 {key}，实际有 {sorted(tokens)}"


def test_the_presets_colours_are_attributed_to_roles_not_document_order() -> None:
    """A page's background must not become its brand colour.

    Today build_style_preset takes colors[0] as primary and colors[1] as accent,
    purely by position in the extracted list — which is the order the colours
    happen to appear in the CSS, not their role. A page whose first two colours
    are its white background and its near-black text produces a white "brand"
    colour, and the result is a page that looks broken in a way nothing reports.
    """
    _assert_not_a_builtin(CANDIDATE)
    preset = intake.build_style_preset(dict(CANDIDATE))
    tokens = preset.get("tokens", {})
    assert tokens.get("primary", "").upper() == SIGNATURE, (
        f"页面自己的主色 {SIGNATURE} 没有落到 primary，拿到的是 "
        f"{tokens.get('primary')!r}——按文档顺序取色会把背景/正文当成品牌色")

    # And the two fonts should not be collapsed into one.
    fonts = preset.get("tokens", {}).get("fonts") or preset.get("fonts") or {}
    assert fonts.get("heading") == "ProbeDisplay" and fonts.get("body") == "ProbeBody", (
        f"页面声明了两种字体，但预设没有区分 heading/body：{fonts}")


def test_a_user_template_reaches_the_generated_page(tmp_path, monkeypatch) -> None:
    """The end-to-end one: generate with a user template and read the CSS.

    Preview already honours a user template; generation does not. This is the
    user-visible difference — same template, two different pages.
    """
    _assert_not_a_builtin(CANDIDATE)

    home = tmp_path / "home"
    tpl = home / ".htmlninefox" / "templates" / "user-probe"
    tpl.mkdir(parents=True)
    preset = intake.build_style_preset(dict(CANDIDATE))
    (tpl / "style.json").write_text(json.dumps(preset, ensure_ascii=False),
                                    encoding="utf-8")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))

    listed = next((i for i in pipeline.list_templates() if i["id"] == "user-probe"), None)
    assert listed is not None, "list_templates 没有看到磁盘上的用户模板"
    assert SIGNATURE.lower() in json.dumps(listed, ensure_ascii=False).lower(), (
        f"模板在 list_templates 里露出的内容不含页面主色：{listed}")

    out = tmp_path / "out"
    pipeline.run_expert("做一个用于验证模板配色的落地页", output=str(out),
                        quiet_llm=True, template="user-probe")
    produced = sorted(out.rglob("output.html"))
    assert produced, f"没有产出 output.html：{sorted(out.rglob('*'))[:10]}"
    html = produced[0].read_text(encoding="utf-8", errors="replace")
    assert SIGNATURE.lower() in html.lower(), (
        f"生成出来的页面里没有模板的主色 {SIGNATURE}——"
        f"pipeline.py:203 用 _tokens.get_preset(template) 查内置表，"
        f"用户模板不在表里，于是静默回落到默认预设。"
        f"页面里的 --fox-primary 是："
        f"{[l.strip() for l in html.splitlines() if '--fox-primary' in l][:1]}")


def test_preview_and_generation_agree_on_a_user_template(tmp_path, monkeypatch) -> None:
    """The invariant behind the previous test, stated directly.

    Two code paths resolve the same template id. They must not disagree, and
    the cheap way to keep them from drifting is to assert they agree.
    """
    home = tmp_path / "home"
    tpl = home / ".htmlninefox" / "templates" / "user-probe"
    tpl.mkdir(parents=True)
    preset = intake.build_style_preset(dict(CANDIDATE))
    (tpl / "style.json").write_text(json.dumps(preset, ensure_ascii=False),
                                    encoding="utf-8")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))

    preview = pipeline.render_template_preview("landing", "user-probe")
    out = tmp_path / "out"
    pipeline.run_expert("做一个用于验证模板配色的落地页", output=str(out),
                        quiet_llm=True, template="user-probe")
    generated = sorted(out.rglob("output.html"))[0].read_text(encoding="utf-8",
                                                              errors="replace")

    def primary(html: str) -> str:
        for line in html.splitlines():
            if "--fox-primary" in line:
                return line.strip()
        return "(没找到 --fox-primary)"

    assert primary(preview) == primary(generated), (
        f"同一个模板，预览与生成给出了不同的主色：\n"
        f"  预览 {primary(preview)}\n  生成 {primary(generated)}")


@pytest.mark.parametrize("colors,why", [
    (["#FFFFFF", "#000000", SIGNATURE],
     "白底黑字在前时，主色不能取到前两个"),
    ([SIGNATURE, "#FFFFFF", "#000000"],
     "主色在第一个时不受影响"),
    (["#000000", SIGNATURE],
     "正文在前时也不能被当成主色"),
])
def test_role_attribution_survives_awkward_colour_orders(colors, why) -> None:
    """Whatever order the CSS lists its colours in, the brand colour is the one
    the page actually uses as a brand colour — not simply the first one."""
    candidate = dict(CANDIDATE)
    candidate["tokens"] = {"colors": list(colors), "fonts": ["ProbeDisplay"]}
    preset = intake.build_style_preset(candidate)
    tokens = preset.get("tokens", {})
    primary = str(tokens.get("primary", "")).upper()
    assert primary == SIGNATURE, (
        f"颜色顺序 {colors} 下主色取成了 {primary}（{why}）")


def test_an_unknown_template_id_is_an_error_not_a_silent_default(tmp_path,
                                                                 monkeypatch) -> None:
    """A template that cannot be resolved must say so.

    The original defect was a silent fallback to the default preset, and the
    obvious "fix" for it would be to fall back in the other direction too — which
    turns a typo in a template id into a page in someone else's colours with no
    error. Asking for a template that does not exist is a mistake worth
    reporting.
    """
    home = tmp_path / "home"
    (home / ".htmlninefox" / "templates").mkdir(parents=True)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    with pytest.raises(ValueError, match="模板不存在"):
        pipeline._resolve_template_preset("no-such-template")


def test_a_partial_user_template_keeps_the_tokens_it_did_not_supply(
        tmp_path, monkeypatch) -> None:
    """A page's palette rarely covers every token the generators emit.

    Merging over the defaults is what keeps `--fox-border`, `--fox-muted`,
    `--fox-radius` and the rest present. Replacing instead of merging produces
    a page whose CSS is missing most of its variables, and the signature colour
    is still there — so a gate that only looks for the signature would pass.
    """
    home = tmp_path / "home"
    tpl = home / ".htmlninefox" / "templates" / "user-partial"
    tpl.mkdir(parents=True)
    (tpl / "style.json").write_text(json.dumps({
        "name": "只给了一个主色的模板",
        "tokens": {"primary": SIGNATURE},
    }, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))

    resolved = pipeline._resolve_template_preset("user-partial")
    default = _tokens.get_preset(_tokens.DEFAULT_PRESET)
    assert resolved["tokens"]["primary"].upper() == SIGNATURE, \
        "用户模板的主色没有生效"
    for key, value in default["tokens"].items():
        if key == "primary":
            continue
        assert key in resolved["tokens"], (
            f"用户模板没有提供 {key}，但它从产物里消失了——"
            f"合并被做成了整体替换，页面会缺一整排 CSS 变量。tokens={resolved['tokens']}")
        assert resolved["tokens"][key] == value, (
            f"{key} 应沿用默认值，实际变成了 {resolved['tokens'][key]!r}")
