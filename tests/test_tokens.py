"""测试 token 库：预设匹配 / 反馈应用 / 全局库不被污染"""

from htmlninefox.generators import _tokens as tk
from htmlninefox.generators import _oklch as ok


class TestMatchPreset:
    def test_dashboard_dark(self):
        brief = {"brief": {"style": {"tone": "dark"}, "content": {"core_message": "看板"}}}
        p = tk.match_preset(brief, "dashboard")
        assert p["id"] == "shadcn-dashboard"

    def test_deck_editorial(self):
        brief = {"brief": {"style": {"tone": "editorial"}, "content": {"core_message": "发布会"}}}
        p = tk.match_preset(brief, "deck")
        assert p["id"] == "guizang-magazine"

    def test_user_reference_overrides(self):
        brief = {"brief": {"style": {"tone": "minimal"},
                           "content": {"core_message": "参考 vercel 做一个首页"}}}
        p = tk.match_preset(brief, "landing")
        assert p["id"] == "vercel-dark"

    def test_machine_reference_not_scanned(self):
        # 生成的 reference 不应反过来影响匹配（v0.2 修复的回归测试）
        brief = {"brief": {"style": {"tone": "dark",
                                     "reference": ["Grafana", "Linear Insights", "Vercel Analytics"]},
                           "content": {"core_message": "看板"}}}
        p = tk.match_preset(brief, "dashboard")
        assert p["id"] == "shadcn-dashboard"

    def test_tokens_are_copied(self):
        brief = {"brief": {"style": {"tone": "dark"}, "content": {}}}
        p = tk.match_preset(brief, "dashboard")
        p["tokens"]["primary"] = "#000000"
        assert tk.PRESETS["shadcn-dashboard"]["tokens"]["primary"] != "#000000"


class TestApplyFeedback:
    def _base(self):
        return tk.get_preset("linear-light")

    def test_color_shift_darkens(self):
        p = tk.apply_feedback(self._base(), {}, ["color_shift"])
        assert p["tokens"]["primary"] != tk.PRESETS["linear-light"]["tokens"]["primary"]

    def test_color_lighten(self):
        p = tk.apply_feedback(self._base(), {}, ["color_lighten"])
        assert p["tokens"]["primary"] != tk.PRESETS["linear-light"]["tokens"]["primary"]

    def test_theme_switch(self):
        p = tk.apply_feedback(self._base(), {}, ["theme_dark"])
        assert p["dark"] is True
        assert p["tokens"]["bg"] == tk.PRESETS["vercel-dark"]["tokens"]["bg"]

    def test_hex_override(self):
        # v0.9.5 OKLCH：域外品牌色不直接用原色 —— 收进风格域并留理由
        p = tk.apply_feedback(self._base(), {"primary_override": "#FF5A00"}, [])
        assert p["tokens"]["primary"] != "#FF5A00", "域外品牌色必须被收进风格域"
        l, _, h = ok.hex_to_oklch(p["tokens"]["primary"])
        _, _, brand_h = ok.hex_to_oklch("#FF5A00")
        # 色相保留 ±8°：OKLCH→sRGB 色域边界的固有映射损失（深彩区 ~5°）
        assert abs(h - brand_h) <= 8.0, f"色相必须保留（±8°），实际漂移 {abs(h - brand_h):.1f}°"
        assert p.get("_brand_constraint"), "约束理由必须可见"
        ratio = ok.wcag_contrast_ratio(p["tokens"]["primary"],
                                       p["tokens"]["primary_text"])
        assert ratio >= 4.5, f"对比度必须 ≥4.5:1，实际 {ratio}"

    def test_hex_override_in_domain_stays(self):
        # 已在域内的温和色不被扰动（回归护栏）
        anchor = tk.PRESETS["linear-light"]["tokens"]["primary"]
        p = tk.apply_feedback(self._base(), {"primary_override": anchor}, [])
        assert p["tokens"]["primary"] == anchor
        assert not p.get("_brand_constraint")

    def test_hex_override_with_color_shift_stays_constrained(self):
        # 0.9.5 巡检 07 实锤：「主色改成 #xxx」会被规则解析同时命中
        # hex_color 与 color_shift——override 必须在 rules 之后落定，
        # 否则 shift 把收域结果拽出域（#00FF00 → #3ED535, L=0.77）
        p = tk.apply_feedback(self._base(), {"primary_override": "#00FF00"},
                              ["color_shift"])
        l, _, _ = ok.hex_to_oklch(p["tokens"]["primary"])
        anchor_l = ok.hex_to_oklch(tk.PRESETS["linear-light"]["tokens"]["primary"])[0]
        assert abs(l - anchor_l) <= 0.10 + 1e-6, f"明度必须收在锚点域，实际 L={l:.2f}"
        assert p.get("_brand_constraint"), "约束理由必须可见"

    def test_reference_preset_switch(self):
        p = tk.apply_feedback(self._base(), {"reference_preset": "stripe"}, [])
        assert p["tokens"]["primary"] == tk.PRESETS["doc-clean"]["tokens"]["primary"]

    def test_radius_and_font(self):
        p = tk.apply_feedback(self._base(), {}, ["radius_up", "font_up"])
        assert int(p["tokens"]["radius"][:-2]) > 10
        assert p["tokens"]["_font_scale"] > 1.0

    def test_global_library_untouched(self):
        before = dict(tk.PRESETS["linear-light"]["tokens"])
        tk.apply_feedback(self._base(), {"primary_override": "#123456"},
                          ["theme_dark", "color_shift", "font_up", "spacing_up"])
        assert tk.PRESETS["linear-light"]["tokens"] == before


class TestShiftColor:
    def test_direction(self):
        base = "#5E6AD2"
        darker = tk.shift_color(base, -0.2)
        lighter = tk.shift_color(base, 0.2)
        assert darker != base != lighter
        assert all(c.startswith("#") and len(c) == 7 for c in (darker, lighter))

    def test_invalid_passthrough(self):
        assert tk.shift_color("nope", 0.1) == "nope"
