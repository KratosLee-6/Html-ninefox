"""Rebuild the Html九尾狐 brand film, one shot per documented feature.

Coverage contract
-----------------
Every UI shot maps 1:1 onto an item that actually ships in v0.6.0, and the
`shot_index()` table below is the single place that mapping lives. A shot
whose number has no row here is a bug, not a stylistic choice. The index
also records, for each shot, the feature it demonstrates and the source
capture it came from.

Framing
-------
Two framing bugs were fixed here.

1. 16:10 captures cropped into a 16:9 frame lost the top bar, and the top
   bar is where the `v0.6.0` version badge lives. The film is meant to let
   a viewer confirm which build they are looking at, so the source is now
   *fitted* and letterboxed with the brand paper colour instead of cropped.

2. `zoompan` computes `x = (iw - iw/zoom) * cx`, which is **0 at zoom=1**
   for any centre. Every shot therefore used to start at the top-left
   corner and drift inward. The zoom now runs 1.06 -> 1.00 so the centre
   offsets are meaningful and each shot starts centred and settles.

Requires ffmpeg + ffprobe and a Playwright chromium install.

    python scripts/make_promo_film.py
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
XF = 0.5

CJK_BOLD = r"C\:/Windows/Fonts/msyhbd.ttc"
CJK_REG = r"C\:/Windows/Fonts/msyh.ttc"

NAVY = "#0E1B3D"
COBALT = "#173C8F"
MINT = "#49B894"
PAPER = "#F4F0E7"

# ---------------------------------------------------------------- shot script
# ("card"|"shot"|"pair", source, seconds, kicker, title, tags, catalogue_id)
# Every catalogue_id must exist in CATALOGUE, or build fails.
SCRIPT = {
    "zh": [
        ("card", "title", 3.5, "", "灵感，散落在各处", "", None),
        ("card", "slogan", 3.0, "", "让灵感在 HTML 里生长", "", None),

        ("shot", "workbench-overview.png", 3.0,
         "无限画布工作区", "一张画布，编排所有素材",
         "工作区 · 节点 · 端口连线", "canvas"),
        ("shot", "sidebar-templates.png", 2.5,
         "真实 HTML 模板库", "6 套模板，34 个页面可单独抽",
         "每页都能预览和抽取", "templates"),
        ("shot", "workbench-paper-1440.png", 2.5,
         "Pixel Paper", "暖纸底，杂志感排版",
         "深钴蓝 + 薄荷绿 + 暖纸白", "theme-paper"),
        ("shot", "workbench-night-1440.png", 2.5,
         "Pixel Night", "同一套组件的完整暗色主题",
         "全部文字达到 WCAG AA", "theme-night"),
        ("shot", "workbench-tablet-768.png", 2.5,
         "响应式", "桌面 · 平板，同一工作台",
         "侧栏折叠，语义缩放", "responsive-tablet"),
        ("shot", "workbench-mobile-390.png", 2.5,
         "移动任务视图", "手机上换成能读懂的列表",
         "不再硬塞一张缩小的画布", "responsive-mobile"),

        ("pair", ("intake-review-pending.png", "intake-approved-absorption.png"), 4.0,
         "设计吸收流水线", "12 个设计源，抓回来的先过审核台",
         "许可三档 · CSP 沙箱", "intake-review"),
        ("pair", ("intake-approved-absorption.png", "intake-preview-sandbox.png"), 3.0,
         "CSP 沙箱预览", "候选页面在无脚本沙箱里渲染",
         "抓回来的脚本永不执行", "intake-sandbox"),
        ("shot", "motion-lab-intake-motion.png", 2.5,
         "动效实验室", "吸收到的动效进实验室",
         "预算钳制 · 尊重减少动效", "intake-motion"),

        ("shot", "slide-editor-dialog.png", 3.0,
         "可编辑 PPTX", "在 PowerPoint 里真能编辑",
         "不是把整页拍成一张图", "pptx-export"),
        ("shot", "export-center-pptx.png", 2.5,
         "导出中心", "PDF / 逐页 PNG / 长图 / PPTX",
         "附诚实的降级报告", "export"),
        ("shot", "pptx-export-report.png", 2.5,
         "降级报告", "做不到的部分，写在报告里",
         "不糊弄", "export-report"),

        ("card", "versions", 4.0, "", "", "", None),
        ("card", "end", 4.0, "", "导出的每一个像素，都真的存在", "", None),
    ],
    "en": [
        ("card", "title", 3.5, "", "Ideas, scattered everywhere", "", None),
        ("card", "slogan", 3.0, "", "Let ideas grow in HTML", "", None),

        ("shot", "workbench-overview.png", 3.0,
         "INFINITE CANVAS", "One canvas for every asset",
         "Workspaces - Nodes - Ports", "canvas"),
        ("shot", "sidebar-templates.png", 2.5,
         "REAL HTML TEMPLATES", "6 sets, 34 pages, each extractable",
         "Preview and extract any page", "templates"),
        ("shot", "workbench-paper-1440.png", 2.5,
         "PIXEL PAPER", "Warm paper, editorial rhythm",
         "Cobalt + mint + warm white", "theme-paper"),
        ("shot", "workbench-night-1440.png", 2.5,
         "PIXEL NIGHT", "The same system, fully dark",
         "Every text color above WCAG AA", "theme-night"),
        ("shot", "workbench-tablet-768.png", 2.5,
         "RESPONSIVE", "Desktop and tablet, one workbench",
         "Folded sidebar, semantic zoom", "responsive-tablet"),
        ("shot", "workbench-mobile-390.png", 2.5,
         "MOBILE TASK VIEW", "A readable list on a phone",
         "Not a shrunken canvas", "responsive-mobile"),

        ("pair", ("intake-review-pending.png", "intake-approved-absorption.png"), 4.0,
         "DESIGN INTAKE", "12 sources, every candidate reviewed",
         "Three license tiers - CSP sandbox", "intake-review"),
        ("pair", ("intake-approved-absorption.png", "intake-preview-sandbox.png"), 3.0,
         "CSP SANDBOX", "Candidates render with scripts off",
         "Fetched scripts never execute", "intake-sandbox"),
        ("shot", "motion-lab-intake-motion.png", 2.5,
         "MOTION LAB", "Absorbed motion goes to the lab",
         "Budget-clamped, reduced-motion aware", "intake-motion"),

        ("shot", "slide-editor-dialog.png", 3.0,
         "EDITABLE PPTX", "Genuinely editable in PowerPoint",
         "Not a flattened screenshot", "pptx-export"),
        ("shot", "export-center-pptx.png", 2.5,
         "EXPORT CENTER", "PDF / paginated PNG / long image / PPTX",
         "With an honest degradation report", "export"),
        ("shot", "pptx-export-report.png", 2.5,
         "DEGRADATION REPORT", "What could not be mapped is written down",
         "No glossing over it", "export-report"),

        ("card", "versions", 4.0, "", "", "", None),
        ("card", "end", 4.0, "", "Every pixel you export really exists", "", None),
    ],
}

# ---------------------------------------------------------------------------
# Catalogue: feature id -> (name, note). Present so the "all features are
# covered" claim in the README is checkable rather than asserted.
# ---------------------------------------------------------------------------
CATALOGUE = {
    "canvas": ("无限画布工作区", "Infinite canvas workspace"),
    "templates": ("真实 HTML 模板库 6 套 / 34 页", "Real HTML template library"),
    "theme-paper": ("Pixel Paper 纸白主题", "Pixel Paper theme"),
    "theme-night": ("Pixel Night 夜蓝主题", "Pixel Night theme"),
    "responsive-tablet": ("平板 768 响应式", "Tablet 768 layout"),
    "responsive-mobile": ("移动 390 任务视图", "Mobile 390 task view"),
    "intake-review": ("设计吸收 · 审核台 · 12 源 · 三档许可", "Design intake review"),
    "intake-sandbox": ("CSP 沙箱预览", "CSP sandbox preview"),
    "intake-motion": ("动效实验室", "Motion lab"),
    "pptx-export": ("可编辑 PPTX 导出与幻灯片编辑", "Editable PPTX"),
    "export": ("导出中心 PDF/PNG/长图/PPTX", "Export Center"),
    "export-report": ("诚实的降级报告", "Honest degradation report"),
}

# The features that ship but are not interface shots. They are real
# capabilities; the film simply has no capture of them, and saying so is
# better than implying the film is exhaustive.
NOT_IN_FILM = [
    ("Web 工作台一键启动 / CLI / Docker", "no single capture exists"),
    ("真实 LLM 接入（MiniMax-M3 / Claude / GPT-4o）", "settings dialog, not a v0.6 capture"),
    ("AI 模型自主配置与 API Key 仅本地保存", "settings dialog, not a v0.6 capture"),
    ("离线规则引擎兜底（无 Key 也能生成）", "no single capture exists"),
    ("统一需求入口（文字/文件/图片）", "input dialog, only captured on v0.5.0"),
    ("推荐与自由组合双路径", "recommendation state, not captured on v0.6.0"),
    ("Project Memory", "v0.5.0 capture only"),
    ("命令面板", "v0.5.0 capture only"),
    ("反馈迭代与版本历史 / 恢复", "v0.5.0 capture only"),
    ("生成取消", "v0.5.0 capture only"),
    ("六类生成器产物输出", "v0.5.0 e2e captures only"),
    ("十一套视觉系统", "per-preset captures not taken this round"),
    ("Skill 联盟模板", "v0.3-v0.4 heritage"),
    ("跨平台安装包", "packaging output, not interface footage"),
]

VERSIONS = {
    "zh": [
        ("v0.6.0", "2026-10-01", "设计吸收 + 可编辑 PPTX"),
        ("v0.5.0", "2026-09-25", "崩溃回滚 / 跨进程锁 / 取消生成"),
        ("v0.4.2", "2026-09-08", "Export Center"),
        ("v0.4.0", "2026-08", "Pixel Garden 设计系统"),
        ("v0.3.0", "2026-07", "Skill 联盟接入"),
    ],
    "en": [
        ("v0.6.0", "2026-10-01", "Design intake + editable PPTX"),
        ("v0.5.0", "2026-09-25", "Rollback / locking / cancel"),
        ("v0.4.2", "2026-09-08", "Export Center"),
        ("v0.4.0", "2026-08", "Pixel Garden design system"),
        ("v0.3.0", "2026-07", "Skill alliance"),
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
.mark{width:132px;height:132px;margin-bottom:46px;position:relative;z-index:2}
.rule{width:112px;height:7px;background:__MINT__;margin:0 0 42px;
      position:relative;z-index:2}
h1{font-size:88px;font-weight:800;letter-spacing:.02em;line-height:1.24;
   text-align:center;position:relative;z-index:2;max-width:1500px}
h1.en{font-size:80px}
.sub{margin-top:36px;font-size:30px;font-weight:400;color:#A9C0EC;
     letter-spacing:.16em;text-align:center;position:relative;z-index:2}
.foot{position:absolute;bottom:66px;left:0;right:0;text-align:center;
      font-size:22px;letter-spacing:.2em;color:#6F8AC4;z-index:2}
table{position:relative;z-index:2;border-collapse:collapse;font-size:27px}
td{padding:13px 30px;border-bottom:1px solid rgba(169,192,236,.26);color:#C9D8F2}
td.v{color:#FFFDF6;font-weight:700;white-space:nowrap}
td.d{color:#7E9ACB;white-space:nowrap;font-variant-numeric:tabular-nums}
td.n{color:#A9C0EC}
.dot{color:__MINT__;font-weight:700}
.caph{margin-bottom:26px;font-size:24px;letter-spacing:.2em;color:__MINT__}
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
        capture_output=True, check=True, encoding="utf-8")
    return float(r.stdout.strip())


def probe_has_audio(path: Path) -> bool:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a",
         "-show_entries", "stream=index", "-of", "csv=p=0", str(path)],
        capture_output=True, check=True, encoding="utf-8")
    return bool(r.stdout.strip())


def verify(out: Path, want: float, tol: float = 0.12) -> None:
    got = probe_duration(out)
    if abs(got - want) > tol:
        raise SystemExit(
            f"{out.name}: duration {got:.2f}s, expected {want:.2f}s "
            f"-> refusing to ship a film built on a wrong-length clip")
    if probe_has_audio(out):
        raise SystemExit(f"{out.name}: unexpected audio track in a silent film")
    print(f"  ok {out.name} {got:.2f}s")


def film_seconds(lang: str = "zh") -> float:
    """Length is derived from SCRIPT, never hard-coded.

    16 clips summing 47.5s minus 15 cross-fades of 0.5s = 40.0s. Hard-coding
    it is how the file ends up called `60s` while being 40s long.
    """
    d = [e[2] for e in SCRIPT[lang]]
    return d[0] + sum(x - XF for x in d[1:])


def validate_script() -> None:
    """Every shot must name a catalogue feature, or be an explicit card."""
    for lang, entries in SCRIPT.items():
        for kind, source, _d, _k, _t, _g, cat in entries:
            if kind == "card":
                if cat is not None:
                    raise SystemExit(f"{lang}: card {source} must not claim "
                                     f"a catalogue id ({cat})")
                continue
            if cat is None:
                raise SystemExit(f"{lang}: shot {source} has no catalogue id")
            if cat not in CATALOGUE:
                raise SystemExit(f"{lang}: unknown catalogue id {cat!r} "
                                 f"on {source}")
        ids = [e[6] for e in entries if e[0] != "card"]
        missing = sorted(set(CATALOGUE) - set(ids))
        if missing:
            raise SystemExit(
                f"{lang}: catalogue features with no shot: {missing} "
                f"-> the film would claim less coverage than it documents")
        print(f"  coverage {lang}: {len(ids)} shots, "
              f"{len(set(ids))} features, all catalogue ids used")


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
                    wait_until="load")
                out = WORK / f"card-{kind}-{lang}.png"
                page.screenshot(path=str(out))
                print("card", out.name)
        for lang, rows in VERSIONS.items():
            trs = "".join(
                f'<tr><td class="v">{v}</td><td class="d">{d}</td>'
                f'<td class="n">{n}</td></tr>' for v, d, n in rows)
            css = CARD_CSS.replace("__BG__", NAVY).replace("__MINT__", MINT)
            cap = "版本沿革" if lang == "zh" else "VERSION HISTORY"
            page.set_content(
                f"<style>{css}</style>"
                f'<div class="grid"></div>'
                f'<div class="caph">{cap}</div>'
                f"<table>{trs}</table>"
                '<div class="foot">HTMLNINEFOX · PIXEL GARDEN</div>',
                wait_until="load")
            out = WORK / f"card-versions-{lang}.png"
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
            f"fontsize=25:fontcolor={MINT}")
    parts.append(
        f"drawtext=fontfile='{CJK_BOLD}':text='{title}':x=156:y=978:"
        f"fontsize=44:fontcolor=#FFFDF6")
    if tags:
        parts.append(
            f"drawtext=fontfile='{CJK_REG}':text='{tags}':x=156:y=1032:"
            f"fontsize=25:fontcolor=#C3D2F0")
    return ",".join(parts)


def kenburns(dur: float) -> str:
    """Fit-and-letterbox, then a gentle settle.

    `scale=...:force_original_aspect_ratio=decrease` + `pad` keeps the whole
    capture including the top bar (and therefore the version badge) instead
    of cropping 16:10 into 16:9. The zoom runs 1.06 -> 1.00 because zoompan
    pins x and y to 0 at zoom=1, which made every shot start off-centre.
    """
    frames = int(round(dur * FPS))
    return (
        f"scale=2304:1296:force_original_aspect_ratio=decrease:flags=lanczos,"
        f"pad=2304:1296:(ow-iw)/2:(oh-ih)/2:color={PAPER},"
        f"zoompan=z='if(eq(on,0),1.06,max(0.0001,1.06-0.06*on/{frames}))':"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={frames}:s={W}x{H}:fps={FPS},"
        f"setsar=1"
    )


def build_still(src: Path, dur: float, out: Path, cap: str) -> None:
    frames = int(round(dur * FPS))
    chain = [kenburns(dur)]
    if cap:
        chain.append(cap)
    chain.append("format=yuv420p")
    run(["ffmpeg", "-y", "-i", str(src),
         "-vf", ",".join(chain), "-frames:v", str(frames), "-r", str(FPS),
         "-c:v", "libx264", "-preset", "slow", "-crf", "18",
         "-pix_fmt", "yuv420p", "-an", str(out)])


def build_paired(a: Path, b: Path, dur: float, out: Path, cap: str) -> None:
    inner = XF
    side = dur / 2 + inner / 2
    ta = WORK / f"{out.stem}-a.mp4"
    tb = WORK / f"{out.stem}-b.mp4"
    build_still(a, side, ta, cap)
    build_still(b, side, tb, cap)
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
    for idx, (kind, source, dur, kicker, title, tags, _cat) in enumerate(
            SCRIPT[lang]):
        out = WORK / f"{lang}-clip{idx:02d}.mp4"
        if kind == "card":
            build_still(WORK / f"card-{source}-{lang}.png", dur, out, "")
        elif kind == "shot":
            build_still(SHOTS / source, dur, out,
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
    total = durations[0] + sum(d - XF for d in durations[1:])
    verify(out, total, tol=0.4)
    if abs(total - film_seconds(lang)) > 1e-6:
        raise SystemExit(f"{lang}: built {total}s but the shot list says "
                         f"{film_seconds(lang)}s")


def poster(video: Path, out: Path, at: float) -> None:
    run(["ffmpeg", "-y", "-ss", f"{at}", "-i", str(video), "-frames:v", "1",
         "-q:v", "2", str(out)])


def main() -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    PROMO.mkdir(parents=True, exist_ok=True)
    for stale in WORK.glob("*.mp4"):
        stale.unlink()

    validate_script()
    if not (WORK / "card-versions-en.png").exists():
        render_cards()

    for lang in ("zh", "en"):
        seconds = int(round(film_seconds(lang)))
        stem = (f"htmlninefox-brand-film-{seconds}s-16x9" if lang == "zh"
                else f"htmlninefox-brand-film-{seconds}s-16x9-en")
        final = WORK / f"final-{lang}.mp4"
        build_master(lang, build_content_clips(lang), final)
        final.replace(PROMO / f"{stem}.mp4")
        target = PROMO / f"{stem}.mp4"
        print(f"done {target.name} {target.stat().st_size / 1e6:.2f} MB "
              f"{probe_duration(target):.2f}s")
        poster(target, PROMO / f"poster-{lang}.png", 12.0)


if __name__ == "__main__":
    main()
