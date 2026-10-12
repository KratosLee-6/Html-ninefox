"""A template id must give the same page at preview time and at generate time.

Live bug, found by the existing preview/generation agreement gate the moment
the machine running it had the optional ``templates`` extra (jinja2) installed:
GenerateExpert's second path silently took over ``landing``/``infographic``
generation and rendered ``templates/landing.html`` — a v0.2-era page speaking
the ``--primary`` variable dialect, with no ``--fox-*`` design tokens and no
motion layer — while the workbench preview always renders through the native
generators. Same template id, two different pages, and only on machines where
an optional extra happens to be installed, so CI never saw it.

The fix follows the v0.6-S13 deck precedent: intents that have a first-class
native renderer (and a preview surface) are declared in
``_INTENT_TEMPLATE_ALIAS_NO_FALLBACK`` and the dead template is deleted. The
gates below pin the declaration, the file absence, and the behavior itself.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from htmlninefox import pipeline  # noqa: E402
from htmlninefox.experts import generate_expert  # noqa: E402
from htmlninefox.experts.generate_expert import GenerateExpert  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def test_landing_and_infographic_generate_through_the_native_stack() -> None:
    """Direct unit gate on the defect: the expert must never answer
    ``jinja2:landing`` for the intents that own a native renderer.

    Where jinja2 is absent this passes trivially (the branch needs the
    optional import); where it is installed — the environment the bug lived
    in — this is exactly the line that goes red when the no-fallback
    declaration or the template file comes back.
    """
    expert = GenerateExpert()
    for intent in ("landing", "infographic"):
        result = expert.execute({
            "brief": {"goal": {"text": "做一个用于验证模板一致性的页面"},
                      "intent": intent},
            "style": {}, "assets": {}, "route": {"intent": intent},
        })
        generator = str(result.get("generator", ""))
        assert not generator.startswith("jinja2:"), (
            f"intent={intent} 落到了 Jinja2 模板兜底（generator={generator}）——"
            f"可选依赖 jinja2 一旦安装，预览（原生生成器）与生成就会给出两种页面")
        assert generator.startswith("local:"), (
            f"intent={intent} 应走原生生成器，实际 generator={generator}")


def test_no_previewable_intent_may_have_a_jinja2_alias_or_template() -> None:
    """The invariant, not the instance: every intent the workbench can preview
    renders through the native generators, so none of them may be claimable by
    the Jinja2 branch — neither through the alias table nor through a
    ``templates/<intent>.html`` file the default aliasing would find.
    """
    alias = set(generate_expert._INTENT_TEMPLATE_ALIAS)
    clash = alias & set(pipeline.PREVIEW_INTENTS)
    assert not clash, (
        f"预览面里的意图 {sorted(clash)} 同时在 Jinja2 别名表里——"
        f"装了 templates extras 的机器上预览与生成会分叉")
    for intent in pipeline.PREVIEW_INTENTS:
        declared = intent in generate_expert._INTENT_TEMPLATE_ALIAS_NO_FALLBACK
        assert declared, (
            f"意图 {intent} 可预览但不在 _INTENT_TEMPLATE_ALIAS_NO_FALLBACK 里——"
            f"模板文件一旦出现就会被 Jinja2 分支截走")
        legacy = ROOT / "htmlninefox" / "templates" / f"{intent}.html"
        assert not legacy.exists(), (
            f"{legacy.name} 仍然在包里——默认别名 intent→自身 会让它截走"
            f"可预览意图 {intent} 的生成路径")


def test_the_legacy_landing_template_is_gone_from_the_package() -> None:
    """templates/landing.html is the v0.2 page that hijacked landing
    generation on jinja2-equipped machines. Its absence is load-bearing.
    """
    legacy = ROOT / "htmlninefox" / "templates" / "landing.html"
    assert not legacy.exists(), (
        "templates/landing.html 复活了——它是 --primary 方言的 v0.2 遗留页，"
        "存在于包里就会在装有 jinja2 的环境下替换原生 landing 生成器")
