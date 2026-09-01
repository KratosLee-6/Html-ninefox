"""测试 token 库：预设匹配 / 反馈应用 / 全局库不被污染"""

from htmlninefox.generators import _tokens as tk


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
        p = tk.apply_feedback(self._base(), {"primary_override": "#FF5A00"}, [])
        assert p["tokens"]["primary"] == "#FF5A00"

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
