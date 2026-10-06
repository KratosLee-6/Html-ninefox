"""Mutation check for the user-template style gates.

Seven gates turned red on today's code and green after two fixes. That is the
shape of a real fix, and it is also exactly why "it passes now" is not the
evidence — these mutations put each fix back the way it was and require a gate
to notice.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTAKE = ROOT / "htmlninefox" / "intake.py"
PIPELINE = ROOT / "htmlninefox" / "pipeline.py"
GATE = "tests/test_user_template_style_reaches_page.py"

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


class MutationFailure(RuntimeError):
    """The mutation did not change the file — hard failure."""


def _run(extra: list[str]) -> subprocess.CompletedProcess:
    import os
    return subprocess.run(
        [sys.executable, "-m", "pytest", GATE, *extra,
         "-q", "-p", "no:cacheprovider", "--no-header", "-x"],
        cwd=ROOT, capture_output=True, text=True, timeout=900,
        encoding="utf-8", errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"})


# --- each mutation takes (intake, pipeline) and returns the broken pair

def m_drop_tokens_key(intake: str, pipeline: str):
    """The original defect: the palette lands under colors/fonts and no consumer
    reads either, so everything falls back to the default preset."""
    old = '        # the key every consumer actually reads\n        "tokens": {'
    if old not in intake:
        raise MutationFailure("没找到 build_style_preset 里的 tokens 块")
    cut = intake.index(old)
    end = intake.index("},", intake.index('"font_body": font_body,', cut)) + 3
    return intake[:cut] + intake[end:], pipeline


def m_generation_ignores_user_templates(intake: str, pipeline: str):
    """The other original defect: the generation path looks the template up in
    the built-in table only, so a user template silently gets the default."""
    old = "            preset = dict(_resolve_template_preset(template))"
    if old not in pipeline:
        raise MutationFailure("没找到生成路径的 _resolve_template_preset 调用")
    return intake, pipeline.replace(
        old, "            preset = {**_tokens.get_preset(template), "
              '"_matched_by": f"user-template:{template}"}', 1)


def m_role_attribution_goes_back_to_document_order(intake: str, pipeline: str):
    """Primary becomes the first colour again.

    The first attempt at this mutation removed the near-white/near-black filter
    and the gate stayed green — correctly. The chroma sort does most of the
    attribution work on its own, so dropping the luminance bounds changed
    nothing the gate can see. This one removes the sort, which is the mechanism
    the order-independence property actually depends on.
    """
    old = "    brands.sort(key=_color_chroma, reverse=True)"
    if old not in intake:
        raise MutationFailure("没找到 _attribute_colors 里的色度排序")
    return intake.replace(old, "    brands = list(solid)", 1), pipeline


def m_fonts_collapse_to_one(intake: str, pipeline: str):
    old = '    return {"display": unique[0], "body": unique[-1]}'
    if old not in intake:
        raise MutationFailure("没找到 _attribute_fonts 的 display/body 拆分")
    return intake.replace(old, '    return {"display": unique[0], "body": unique[0]}', 1), pipeline


def m_resolver_raises_instead_of_falling_back(intake: str, pipeline: str):
    """A user template that does not resolve should not be a silent default —
    and neither should a missing one turn into a hard failure at generate time
    when the preview already handled it."""
    old = "    user = next((item for item in list_templates() if item[\"id\"] == preset_id), None)\n    if user is None:\n        raise ValueError(f\"模板不存在：{preset_id}\")"
    if old not in pipeline:
        raise MutationFailure("没找到 _resolve_template_preset 的 user 分支")
    new = ("    user = next((item for item in list_templates()\n"
           "                if item[\"id\"] == preset_id), None)\n"
           "    if user is None:\n"
           "        return {**_tokens.get_preset(_tokens.DEFAULT_PRESET),\n"
           "                \"_matched_by\": f\"user-template:{preset_id}\"}")
    return intake, pipeline.replace(old, new, 1)


def m_user_tokens_replace_instead_of_merge(intake: str, pipeline: str):
    """Replacing rather than merging means a page that only supplies a primary
    colour loses every other token the generators emit."""
    old = '        "tokens": {**default["tokens"], **user.get("tokens", {})},'
    if old not in pipeline:
        raise MutationFailure("没找到 _resolve_template_preset 的 token 合并")
    return intake, pipeline.replace(old, '        "tokens": dict(user.get("tokens", {})),', 1)


MUTATIONS = [
    ("M1 build_style_preset 不再产出 tokens（原缺陷）",
     m_drop_tokens_key, "test_the_style_preset_a_page_produces_has_the_shape_consumers_read"),
    ("M2 生成路径不再解析用户模板（原缺陷）",
     m_generation_ignores_user_templates, "test_a_user_template_reaches_the_generated_page"),
    ("M3 角色归因退回文档顺序（去掉色度排序）",
     m_role_attribution_goes_back_to_document_order,
     "test_role_attribution_survives_awkward_colour_orders"),
    ("M4 字体又被压成一个",
     m_fonts_collapse_to_one, "test_the_presets_colours_are_attributed_to_roles_not_document_order"),
    ("M5 用户模板解析不到时静默回落默认",
     m_resolver_raises_instead_of_falling_back,
     "test_an_unknown_template_id_is_an_error_not_a_silent_default"),
    ("M6 用户 token 整体替换而非合并",
     m_user_tokens_replace_instead_of_merge,
     "test_a_partial_user_template_keeps_the_tokens_it_did_not_supply"),
]


def main() -> int:
    files = (INTAKE, PIPELINE)
    original = {p: p.read_text(encoding="utf-8") for p in files}
    backup = Path(tempfile.mkdtemp(prefix="fox-style-backup-"))
    for p in files:
        shutil.copy2(p, backup / p.name)

    def restore() -> None:
        for p in files:
            shutil.copy2(backup / p.name, p)

    rows: list[tuple[str, str]] = []
    print("=" * 74)
    print("用户模板样式门禁 · 变异验证")
    print("=" * 74)
    try:
        clean = _run([])
        if clean.returncode != 0:
            print("基线就红：\n" + clean.stdout[-2500:])
            return 2
        print("基线：全过\n")

        for name, fn, gate in MUTATIONS:
            try:
                i2, p2 = fn(original[INTAKE], original[PIPELINE])
            except MutationFailure as exc:
                print(f"HARD FAIL  {name}\n          {exc}")
                rows.append((name, "HARD FAIL"))
                restore()
                continue

            if (i2, p2) == (original[INTAKE], original[PIPELINE]):
                print(f"HARD FAIL  {name}\n          变异没有改变任何内容")
                rows.append((name, "HARD FAIL"))
                continue

            INTAKE.write_text(i2, encoding="utf-8", newline="")
            PIPELINE.write_text(p2, encoding="utf-8", newline="")
            try:
                proc = _run(["-k", gate])
            finally:
                restore()

            if proc.returncode == 0:
                verdict = "MISSED"
            elif "no tests ran" in proc.stdout:
                verdict = "BROKEN SELECTOR"
            else:
                verdict = "CAUGHT"
            rows.append((name, verdict))
            print(f"{verdict:17} {name}")
    finally:
        restore()
        shutil.rmtree(backup, ignore_errors=True)
        for p in files:
            same = p.read_text(encoding="utf-8") == original[p]
            print(f"  还原 {p.name}: {'一致' if same else '不一致！'}")

    print("=" * 74)
    caught = sum(1 for _, v in rows if v == "CAUGHT")
    bad = [(n, v) for n, v in rows if v != "CAUGHT"]
    print(f"{caught}/{len(rows)} CAUGHT")
    for n, v in bad:
        print(f"  {v}  {n}")
    print("=" * 74)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
