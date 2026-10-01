"""Rebuild the 30s HtmlNineFox brand film from real v0.6.0 captures.

Every UI frame in the film is a real screenshot from
`assets/screenshots/v0.6.0/`. Nothing generative is used for interface
footage on purpose: a text-to-video model hallucinates garbled CJK glyphs
instead of real UI text, so a generated interface shot is strictly worse
than the capture it would replace. The only non-capture frames are the
three static cards (title / slogan / end), rendered from HTML with
Playwright, whose brand mark is drawn from the project's own SVG source.

Requires ffmpeg + ffprobe and a Playwright chromium install.

    python scripts/make_promo_film.py

Writes `assets/promo/` in place. Every clip and the final master are
duration-checked before anything is overwritten: a clip that misses its
target length aborts the run rather than shipping a film whose metadata
looks right while the content is not.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "htmlninefox" / "server" / "static"
SHOTS = ROOT / "assets" / "screenshots" / "v0.6.0"
PROMO = ROOT / "assets" / "promo"
WORK = ROOT / "build" / "promo-film"

W, H, FPS = 1920, 1080, 25
XF = 0.5  # cross-fade duration
TARGET_SECONDS = 30.0

CJK_BOLD = r"C\:/Windows/Fonts/msyhbd.ttc"
CJK_REG = r"C\:/Windows/Fonts/msyh.ttc"

NAVY = "#0E1B3D"
COBALT = "#173C8F"
MINT = "#49B894"

# ---------------------------------------------------------------- shot script
# Each entry: (kind, source, duration, kicker, title, tags)
#   kind "card" -> HTML-rendered still card (title / slogan / end)
#   kind "shot" -> real screenshot with a scrim caption
#   kind "pair" -> two real screenshots cross-faded inside one clip
SCRIPT = {
    "zh": [
        ("card", "title", 3.5, "", "灵感，散落在各处", ""),
        ("card", "slogan", 3.0, "", "让灵感在 HTML 里生长", ""),
        ("shot", "workbench-overview.png", 5.0,
         "无限画布工作区", "一张画布，编排所有素材",
         "工作区 · 节点 · 端口连线 · 版本"),
        ("pair", ("workbench-paper-1440.png", "workbench-night-1440.png"), 4.5,
         "双主题", "两套主题，文字对比度全部达到 WCAG AA",
         "Pixel Paper / Pixel Night"),
        ("pair", ("intake-review-pending.png", "intake-approved-absorption.png"), 5.0,
         "设计吸收流水线", "把外部设计变成自己的六层素材",
         "审核台 · 三档许可 · CSP 沙箱"),
        ("pair", ("slide-editor-dialog.png", "export-center-pptx.png"), 4.5,
         "可编辑 PPTX", "编辑 → 写回 → 导出真正可编辑的 .pptx",
         "python-pptx · 诚实的降级报告"),
        ("pair", ("workbench-tablet-768.png", "workbench-mobile-390.png"), 3.5,
         "响应式", "桌面 · 平板 · 移动，同一工作台",
         "语义缩放 · 移动任务视图"),
        ("card", "end", 4.5, "", "导出的每一个像素，都真的存在", ""),
    ],
    "en": [
        ("card", "title", 3.5, "", "Ideas, scattered everywhere", ""),
        ("card", "slogan", 3.0, "", "Let ideas grow in HTML", ""),
        ("shot", "workbench-overview.png", 5.0,
         "INFINITE CANVAS", "One canvas for every asset",
         "Workspaces - Nodes - Ports - Revisions"),
        ("pair", ("workbench-paper-1440.png", "workbench-night-1440.png"), 4.5,
         "TWO THEMES", "Two themes, every text color above WCAG AA",
         "Pixel Paper / Pixel Night"),
        ("pair", ("intake-review-pending.png", "intake-approved-absorption.png"), 5.0,
         "DESIGN INTAKE", "Turn external designs into six asset layers",
         "Review workbench - License tiers - CSP sandbox"),
        ("pair", ("slide-editor-dialog.png", "export-center-pptx.png"), 4.5,
         "EDITABLE PPTX", "Edit, write back, export a truly editable .pptx",
         "python-pptx - honest degradation report"),
        ("pair", ("workbench-tablet-768.png", "workbench-mobile-390.png"), 3.5,
         "RESPONSIVE", "Desktop, tablet, mobile - one workbench",
         "Semantic zoom - mobile task view"),
        ("card", "end", 4.5, "", "Every pixel you export really exists", ""),
    ],
}

CARD_BODY = {
    "title": {
        "zh": (NAVY, "灵感，散落在各处", "文字 · 文件 · 图片 · HTML 模板"),
        "en": (NAVY, "Ideas, scattered everywhere",
               "Text · Files · Images · HTML templates"),
    },
    "slogan": {
        "zh": (COBALT, "让灵感在 HTML 里生长", "Html九尾狐 · v0.6.0"),
        "en": (COBALT, "Let ideas grow in HTML", "HtmlNineFox · v0.6.0"),
    },
    "end": {
        "zh": (NAVY, "导出的每一个像素，都真的存在",
               "Html九尾狐 · v0.6.0 · github.com/KratosLee-6/Html-ninefox"),
        "en": (NAVY, "Every pixel you export really exists",
               "HtmlNineFox · v0.6.0 · github.com/KratosLee-6/Html-ninefox"),
    },
}

CARD_CSS = """
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:1920px;height:1080px;overflow:hidden}
body{
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  background:
    radial-gradient(1200px 700px at 22% 18%, #1E3F86 0%, transparent 62%),
    radial-gradient(900px 600px at 82% 88%, #12306E 0%, transparent 60%),
    __BG__;
  color:#FFFDF6; font-family:"Microsoft YaHei","Segoe UI",sans-serif;
  position:relative;
}
.grid{position:absolute;inset:0;
  background-image:linear-gradient(rgba(111,145,210,.10) 1px,transparent 1px),
                   linear-gradient(90deg,rgba(111,145,210,.10) 1px,transparent 1px);
  background-size:64px 64px;
  mask-image:radial-gradient(circle at 50% 45%,#000 30%,transparent 78%);}
.mark{width:132px;height:132px;margin-bottom:54px;position:relative;z-index:2}
.rule{width:112px;height:7px;background:__MINT__;margin:0 0 46px;
      position:relative;z-index:2}
h1{font-size:92px;font-weight:800;letter-spacing:.02em;line-height:1.24;
   text-align:center;position:relative;z-index:2;max-width:1500px}
.sub{margin-top:40px;font-size:31px;font-weight:400;color:#A9C0EC;
     letter-spacing:.16em;text-align:center;position:relative;z-index:2}
.foot{position:absolute;bottom:74px;left:0;right:0;text-align:center;
      font-size:23px;letter-spacing:.2em;color:#6F8AC4;z-index:2}
h1.en{font-size:86px}
"""


def run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        sys.stderr.write(r.stderr.decode("utf-8", "replace")[-4000:])
        raise SystemExit(f"command failed: {' '.join(cmd[:2])}")


def probe_duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, check=True, encoding="utf-8",
    )
    return float(r.stdout.strip())


def probe_has_audio(path: Path) -> bool:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=index", "-of", "csv=p=0", str(path)],
        capture_output=True, check=True, encoding="utf-8",
    )
    return bool(r.stdout.strip())


def verify(out: Path, want: float, tol: float = 0.12) -> None:
    """Refuse to ship a clip whose length does not match the shot list."""
    got = probe_duration(out)
    if abs(got - want) > tol:
        raise SystemExit(
            f"{out.name}: duration {got:.2f}s, expected {want:.2f}s "
            f"-> refusing to ship a film built on a wrong-length clip"
        )
    if probe_has_audio(out):
        raise SystemExit(f"{out.name}: unexpected audio track in a silent film")
    print(f"  ok {out.name} {got:.2f}s")


# ------------------------------------------------------------- stage 1: cards
def render_cards() -> None:
    from playwright.sync_api import sync_playwright

    logo = (STATIC / "logo-mark.svg").read_text(encoding="utf-8")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": W, "height": H})
        for kind, langs in CARD_BODY.items():
            for lang, (bg, title, sub) in langs.items():
                css = (CARD_CSS.replace("__BG__", bg)
                                .replace("__MINT__", MINT))
                page.set_content(
                    f"<style>{css}</style>"
                    f'<div class="grid"></div>'
                    f'<div class="mark">{logo}</div>'
                    '<div class="rule"></div>'
                    f'<h1 class="{"en" if lang == "en" else ""}">{title}</h1>'
                    f'<div class="sub">{sub}</div>'
                    '<div class="foot">HTMLNINEFOX · PIXEL GARDEN</div>',
                    wait_until="load",
                )
                out = WORK / f"card-{kind}-{lang}.png"
                page.screenshot(path=str(out))
                print("card", out.name)
        browser.close()


# ------------------------------------------------------ stage 2: content clips
def caption_filter(kicker: str, title: str, tags: str) -> str:
    """Dark scrim + accent bar + kicker + title + tags, bottom-anchored.

    The dark band must start *above* the kicker. It used to begin at y=958
    while the kicker sat at y=944, so the mint label landed in the 0.30
    falloff strip and read as mint-on-paper-white over the light theme.
    """
    parts = [
        "drawbox=x=0:y=902:w=iw:h=178:color=black@0.30:t=fill",
        "drawbox=x=0:y=920:w=iw:h=160:color=black@0.58:t=fill",
        f"drawbox=x=120:y=948:w=7:h=88:color={MINT}@1.0:t=fill",
    ]
    if kicker:
        parts.append(
            f"drawtext=fontfile='{CJK_BOLD}':text='{kicker}':x=156:y=944:"
            f"fontsize=25:fontcolor={MINT}"
        )
    parts.append(
        f"drawtext=fontfile='{CJK_BOLD}':text='{title}':x=156:y=978:"
        f"fontsize=46:fontcolor=#FFFDF6"
    )
    if tags:
        parts.append(
            f"drawtext=fontfile='{CJK_REG}':text='{tags}':x=156:y=1034:"
            f"fontsize=25:fontcolor=#C3D2F0"
        )
    return ",".join(parts)


def kenburns(dur: float, z0: float, z1: float, cx: float, cy: float) -> str:
    frames = int(round(dur * FPS))
    return (
        f"scale=2560:1440:force_original_aspect_ratio=increase,"
        f"crop=2560:1440,"
        f"zoompan=z='min({z0}+({z1 - z0})*on/{frames},1.30)':"
        f"x='(iw-iw/zoom)*{cx}':y='(ih-ih/zoom)*{cy}':"
        f"d={frames}:s={W}x{H}:fps={FPS},"
        f"setsar=1"
    )


def build_still(src: Path, dur: float, out: Path, z0: float, z1: float,
                cx: float, cy: float, cap: str) -> None:
    """Ken Burns over one still.

    A single image is fed in (no `-loop`): zoompan emits `d` frames *per
    input frame*, so a looped input multiplies the clip length by `d`
    again. `-frames:v` pins the output to exactly one shot's worth.
    """
    frames = int(round(dur * FPS))
    chain = [kenburns(dur, z0, z1, cx, cy)]
    if cap:
        chain.append(cap)
    chain.append("format=yuv420p")
    run(["ffmpeg", "-y", "-i", str(src),
         "-vf", ",".join(chain), "-frames:v", str(frames), "-r", str(FPS),
         "-c:v", "libx264", "-preset", "slow", "-crf", "18",
         "-pix_fmt", "yuv420p", "-an", str(out)])


def build_paired(a: Path, b: Path, dur: float, out: Path, cap: str) -> None:
    """Two screenshots, half the segment each, cross-faded in the middle.

    Each side is rendered on its own first. Doing the Ken Burns and the
    xfade in one filter_complex looks tempting but is wrong: the output
    duration still comes out right while the zoom runs far past its
    intended range.
    """
    inner = XF
    side = dur / 2 + inner / 2
    ta = WORK / f"{out.stem}-a.mp4"
    tb = WORK / f"{out.stem}-b.mp4"
    build_still(a, side, ta, 1.0, 1.05, 0.45, 0.5, cap)
    build_still(b, side, tb, 1.05, 1.0, 0.55, 0.5, cap)
    run(["ffmpeg", "-y", "-i", str(ta), "-i", str(tb),
         "-filter_complex",
         f"[0:v][1:v]xfade=transition=fade:duration={inner}:"
         f"offset={side - inner:.3f},format=yuv420p[v]",
         "-map", "[v]", "-frames:v", str(int(round(dur * FPS))),
         "-r", str(FPS), "-c:v", "libx264", "-preset", "slow", "-crf", "18",
         "-pix_fmt", "yuv420p", "-an", str(out)])
    ta.unlink(missing_ok=True)
    tb.unlink(missing_ok=True)


def build_content_clips(lang: str) -> list[Path]:
    clips: list[Path] = []
    for idx, entry in enumerate(SCRIPT[lang]):
        kind, source, dur, kicker, title, tags = entry
        out = WORK / f"{lang}-clip{idx:02d}.mp4"
        if kind == "card":
            build_still(WORK / f"card-{source}-{lang}.png", dur, out,
                        1.0, 1.05, 0.5, 0.5, "")
        elif kind == "shot":
            build_still(SHOTS / source, dur, out, 1.0, 1.08, 0.5, 0.45,
                        caption_filter(kicker, title, tags))
        else:
            build_paired(SHOTS / source[0], SHOTS / source[1], dur, out,
                         caption_filter(kicker, title, tags))
        clips.append(out)
        verify(out, dur)
    return clips


# ------------------------------------------------------------ stage 3: master
def build_master(lang: str, clips: list[Path], out: Path) -> None:
    inputs: list[str] = []
    for c in clips:
        inputs += ["-i", str(c)]
    durations = [float(e[2]) for e in SCRIPT[lang]]
    steps, cur, offset = [], "[0:v]", 0.0
    for i in range(1, len(clips)):
        offset += durations[i - 1] - XF
        nxt = f"[x{i}]"
        steps.append(f"{cur}[{i}:v]xfade=transition=fade:"
                     f"duration={XF}:offset={offset:.3f}{nxt}")
        cur = nxt
    steps.append(f"{cur}format=yuv420p[v]")
    run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(steps),
         "-map", "[v]", "-r", str(FPS), "-c:v", "libx264", "-preset", "slow",
         "-crf", "19", "-pix_fmt", "yuv420p", "-an", "-movflags", "+faststart",
         str(out)])
    verify(out, TARGET_SECONDS, tol=0.25)


def poster(video: Path, out: Path, at: float = 8.0) -> None:
    run(["ffmpeg", "-y", "-ss", f"{at}", "-i", str(video), "-frames:v", "1",
         "-q:v", "2", str(out)])


def main() -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    PROMO.mkdir(parents=True, exist_ok=True)
    # Drop any clip left behind by an interrupted run: reusing a truncated
    # file would silently produce a film that is missing a shot.
    for stale in WORK.glob("*.mp4"):
        stale.unlink()

    if not (WORK / "card-title-zh.png").exists():
        render_cards()

    for lang in ("zh", "en"):
        name = ("htmlninefox-brand-film-30s-16x9.mp4" if lang == "zh"
                else "htmlninefox-brand-film-30s-16x9-en.mp4")
        final = WORK / f"final-{lang}.mp4"
        build_master(lang, build_content_clips(lang), final)
        # Only now, with the master verified, is the tracked file replaced.
        final.replace(PROMO / name)
        poster(PROMO / name, PROMO / f"poster-{lang}.png")
        target = PROMO / name
        print(f"done {name} {target.stat().st_size / 1e6:.2f} MB "
              f"{probe_duration(target):.2f}s")


if __name__ == "__main__":
    main()
