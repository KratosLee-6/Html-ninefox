"""0.9.5-A OKLCH 品牌色约束门禁

纪律（融合 guizang-design 思路）：品牌色不直接用原色 —— 收进当前风格
在 OKLCH 空间的明度/彩度域，色相保留品牌识别；约束后保障文本对比度
（primary ≥4.5:1 / accent ≥3:1）。锚点从 preset 现色反推，11 家预设零数据变更。
"""

import json

from htmlninefox.experts.style_expert import StyleExpert
from htmlninefox.generators import _oklch as ok
from htmlninefox.generators import _tokens as tk

_REPRESENTATIVE = ["#4F46E5", "#00FF00", "#B4530A", "#173C8F",
                   "#FFFFFF", "#0A0A0B", "#F43F5E", "#5E6AD2"]


class TestConversions:
    def test_roundtrip_lossless(self):
        for hx in _REPRESENTATIVE:
            back = ok.oklch_to_hex(*ok.hex_to_oklch(hx))
            for i in (1, 3, 5):
                assert abs(int(back[i:i + 2], 16) - int(hx[i:i + 2], 16)) <= 1, \
                    f"{hx} 往返漂移 → {back}"

    def test_illegal_input_is_safe(self):
        assert ok.hex_to_oklch("nope") == (0.5, 0.0, 0.0)
        assert ok.oklch_to_hex(2.0, -1.0, 999).startswith("#"), "越界必须 clamp 成合法 hex"

    def test_wcag_reference_values(self):
        assert round(ok.wcag_contrast_ratio("#FFFFFF", "#000000"), 1) == 21.0
        assert abs(ok.wcag_contrast_ratio("#777777", "#FFFFFF") - 4.48) < 0.05


class TestConstrain:
    def test_neon_green_into_vercel_dark(self):
        # 荧光绿 L≈0.87 远超 vercel-dark 锚点域 → 收进域、绿相保留、对比达标
        r = ok.constrain_brand_color("#00FF00", "#4F46E5", "#FFFFFF")
        anchor_l, anchor_c, _ = ok.hex_to_oklch("#4F46E5")
        assert abs(r["L"] - anchor_l) <= 0.10 + 1e-6, "明度必须收进锚点域"
        assert r["C"] <= anchor_c * 1.25 + 0.02 + 1e-6, "彩度必须收进锚点域"
        assert 110 <= r["H"] <= 180, "绿相（品牌识别）必须保留"
        assert r["contrast"] >= 4.5
        assert r["adjusted"] is True
        assert "色相" in r["reason"] and "保留" in r["reason"], "理由必须可见"

    def test_in_domain_color_untouched(self):
        r = ok.constrain_brand_color("#5E6AD2", "#4F46E5", "#FFFFFF")
        assert r["adjusted"] is False
        assert "已在域内" in r["reason"]

    def test_illegal_falls_back_to_anchor(self):
        r = ok.constrain_brand_color("javascript:alert(1)", "#4F46E5", "#FFFFFF")
        assert r["hex"] == "#4F46E5" and r["adjusted"] is False

    def test_accent_uses_graphic_threshold(self):
        # accent 对 bg 只要求 3:1 图形部件档 —— 同一输入 accent 侧更容易达标
        r_primary = ok.constrain_brand_color("#FF00AA", "#4F46E5", "#FFFFFF",
                                             role="primary")
        r_accent = ok.constrain_brand_color("#FF00AA", "#0EA5E9", "#FBFBFA",
                                            role="accent")
        assert r_primary["contrast"] >= 4.5
        assert r_accent["contrast"] >= 3.0


class TestWiring:
    def test_apply_feedback_constrains_override(self):
        p = tk.apply_feedback(tk.get_preset("vercel-dark"),
                              {"primary_override": "#00FF00"}, [])
        assert p["tokens"]["primary"] != "#00FF00", "域外品牌色必须被收域"
        assert p.get("_brand_constraint"), "约束理由必须随 token 走"
        assert p["tokens"]["primary"].startswith("#")

    def test_style_expert_stub_chain(self, monkeypatch):
        # stub 给荧光色（llm.py style_refine 键控值）→ execute 出口必须已收域
        monkeypatch.setenv("HTMLNINEFOX_LLM_STUB", "1")
        out = StyleExpert().execute(
            {"brief": {"brief": {"style": {"tone": "dark"},
                                 "content": {"core_message": "看板"}}},
             "intent": "dashboard", "allow_llm": True})
        t = out["preset"]["tokens"]
        assert t["primary"] != "#00FF00", "stub 荧光色必须被收域"
        assert t["accent"] != "#FF00AA", "stub 荧光 accent 必须被收域"
        assert out["style_decision"].get("brand_constraint"), \
            "约束理由必须进 style_decision（决策可解释）"

    def test_mutation_removing_the_constraint_is_caught(self, monkeypatch):
        """变异验证：约束换成直通赋值 → 域外荧光色直进 token，
        本文件的全链断言必须 CAUGHT（同进程函数式变异）。"""
        import htmlninefox.generators._tokens as tk_mod

        def _passthrough(brand_hex, anchor_hex, text_hex, **kw):
            return {"hex": brand_hex, "adjusted": False, "contrast": 0.0,
                    "reason": "直通变异"}

        real = tk.apply_feedback(tk.get_preset("vercel-dark"),
                                 {"primary_override": "#00FF00"}, [])
        assert ok.hex_to_oklch(real["tokens"]["primary"])[0] < 0.75, "真实现必须收域"
        monkeypatch.setattr(tk_mod, "constrain_brand_color", _passthrough)
        mutated = tk_mod.apply_feedback(tk.get_preset("vercel-dark"),
                                        {"primary_override": "#00FF00"}, [])
        assert mutated["tokens"]["primary"] == "#00FF00", \
            "变异后域外色直进 token —— 收域断言在此必红（CAUGHT）"


def test_stub_style_refine_payload_is_domain_outside():
    """stub 键控值本身必须是域外荧光色 —— 它是约束链的确定性测试输入。"""
    from htmlninefox.llm import _stub_text_for_style_refine
    data = json.loads(_stub_text_for_style_refine())
    assert data["primary"] == "#00FF00" and ok.hex_to_oklch(data["primary"])[0] > 0.8
