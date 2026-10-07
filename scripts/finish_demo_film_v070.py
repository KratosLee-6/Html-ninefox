# -*- coding: utf-8 -*-
"""Finish the v0.7.0 demo recording: brand open, captions, brand close, music.

与 finish_demo_film.py 同一条纪律：界面 footage 是真实录屏，本阶段不得重绘
任何 UI。合成元素只有三类：

  - H3 抽象片头/片尾底版（scripts/generate_h3_clips_v070.py 生成；缺省回退
    到 assets/promo/opener-h3-2k.mp4）。H3 画面**永远不含文字**——提示词
    明令禁止，这是文生视频模型唯一可用的形状。
  - 品牌叠加层：Logo 用官方 SVG 经 Chromium 渲染成透明 PNG，文字用 Pillow
    渲染成字幕条，全部确定性叠加在 H3 底版上（开头亮出品牌，结尾亮出
    项目一句话与 GitHub 地址）。
  - 字幕条（Pillow，drawtext 在本机 CJK 会乱码）与配乐（brand-bed.mp3）。

字幕时间轴来自 record_demo_film_v070.py 落下的 events.json——每条字幕
对应录制时真实发生的事件，不是事后编的时间表。

    python scripts/finish_demo_film_v070.py

产物：assets/promo/htmlninefox-demo-v070-16x9.mp4（+ 海报帧 poster-demo-v070.png）
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from PIL import Image, ImageDraw, ImageFilter, ImageFont  # noqa: E402

FPS = 25
ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / ".tmp/demo-run-video-v070"
SESSION = WORK / "session.webm"
EVENTS = WORK / "events.json"
STATIC = ROOT / "htmlninefox" / "server" / "static"
PROMO = ROOT / "assets" / "promo"
OPENER_PLATE = PROMO / "opener-h3-2k.mp4"          # 既有 H3 底版（回退用）
H3_OPEN = PROMO / "h3-open-v070.mp4"               # 本次 H3 生成的片头（可选）
H3_CLOSE = PROMO / "h3-close-v070.mp4"             # 本次 H3 生成的片尾（可选）
MUSIC = PROMO / "brand-bed.mp3"

# H3's native ambience, used for the opening card ONLY. Letting it
# ride inside the brand clip carried it under the music all the way
# through, which is what 'two copies of the audio' sounds like.
OPENING_AMBIENCE = ROOT / ".tmp" / "demo-film-v070" / "opening-ambience.wav"
OUT = PROMO / "htmlninefox-demo-v070-16x9.mp4"
POSTER = PROMO / "poster-demo-v070.png"

W, H = 1920, 1080
PAPER = (244, 240, 231)
COBALT = (23, 60, 143)
MINT = (73, 184, 148)
TERRA = (229, 122, 63)
GREY = (122, 132, 148)
WHITE = (255, 253, 246)
BOLD = r"C:\Windows\Fonts\msyhbd.ttc"

BRAND_LEN = 5.0          # 品牌片头/片尾各 5 秒
OPENER_FRAMES = 100
OPENER_TAIL = 10
XF = 12 / FPS            # 交叉溶解 0.48s


def run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    if r.returncode != 0:
        raise SystemExit(f"cmd failed: {' '.join(cmd[:6])}\n{r.stderr[-1200:]}")


def probe(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    return float(r.stdout.strip())


def caption_png(text: str, out: Path) -> None:
    """字幕条：暖纸白圆角条 + 钴蓝粗体 + 薄荷绿左耳。图内无 emoji（铁律）。"""
    f = ImageFont.truetype(BOLD, 40)
    tmp = Image.new("RGB", (10, 10))
    d = ImageDraw.Draw(tmp)
    tw = int(d.textlength(text, font=f))
    pad_x, bar_h = 44, 86
    img = Image.new("RGB", (tw + pad_x * 2 + 18, bar_h), (0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, img.width - 1, bar_h - 1], radius=14, fill=WHITE)
    d.rectangle([0, 14, 10, bar_h - 14], fill=MINT)
    d.text((pad_x + 18, (bar_h - 40) // 2 - 6), text, font=f, fill=COBALT)
    img.save(out)


def paper_frame() -> Image.Image:
    """暖纸底 + 网格纹 + 双层钴蓝边框（与配图同一套视觉）。"""
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    for x in range(0, W, 36):
        d.line([(x, 0), (x, H)], fill=(237, 233, 222), width=1)
    for y in range(0, H, 36):
        d.line([(0, y), (W, y)], fill=(237, 233, 222), width=1)
    d.rectangle([14, 14, W - 15, H - 15], outline=COBALT, width=5)
    d.rectangle([30, 30, W - 31, H - 31], outline=COBALT, width=1)
    return img


def render_logo_png(out: Path) -> None:
    """官方横版 SVG → 透明底 PNG（Chromium 渲染，2x 清晰度）。

    SVG 内容直接内联进页面：about:blank 页面加载 file:// 子资源会被拦，
    外链 img 只会渲染出一个破图框。
    """
    svg = (STATIC / "logo-horizontal.svg").resolve()
    svg_text = svg.read_text(encoding="utf-8")
    with _playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 900, "height": 230},
                                device_scale_factor=2)
        page.set_content(
            '<body style="margin:0;background:transparent">'
            f'<div style="width:840px">{svg_text}</div>'
            "</body>")
        page.wait_for_timeout(600)
        page.screenshot(path=str(out), omit_background=True)
        browser.close()


def _playwright():
    from playwright.sync_api import sync_playwright
    return sync_playwright()


def drop_shadow(img: Image.Image, offset: int = 12) -> Image.Image:
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle([0, 0, img.width, img.height],
                                 fill=TERRA + (110,))
    sh = sh.filter(ImageFilter.GaussianBlur(9))
    out = Image.new("RGBA", (img.width + offset, img.height + offset),
                    (0, 0, 0, 0))
    out.alpha_composite(sh, (offset, offset))
    out.alpha_composite(img.convert("RGBA"), (0, 0))
    return out


def brand_overlay(logo: Path, lines: list[tuple[str, int, tuple]],
                  out: Path, logo_y: int) -> Path:
    """Logo + 文字行合成一张整帧透明 PNG（叠加时整帧同进同出）。"""
    frame = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    logo_img = Image.open(logo).convert("RGBA")
    lw = 760
    lh = int(logo_img.height * lw / logo_img.width)
    logo_img = logo_img.resize((lw, lh), Image.LANCZOS)
    frame.alpha_composite(logo_img, ((W - lw) // 2, logo_y))
    text_img = Image.open(text_png_rgba(lines))
    frame.alpha_composite(text_img, ((W - text_img.width) // 2,
                                     logo_y + lh + 40))
    frame.save(out)
    return out


def text_png_rgba(lines: list[tuple[str, int, tuple]]) -> Path:
    out = WORK / "_brand-text.png"
    text_png_rgba_inner(lines, out)
    return out


def text_png_rgba_inner(lines: list[tuple[str, int, tuple]], out: Path) -> None:
    imgs = []
    for text, size, colour in lines:
        f = ImageFont.truetype(BOLD, size)
        tmp = ImageDraw.Draw(Image.new("RGB", (8, 8)))
        imgs.append((text, f, colour, int(tmp.textlength(text, font=f))))
    w = max(w for _, _, _, w in imgs) + 40
    h = sum(f.size + 30 for _, f, _, _ in imgs) + 16
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    y = 8
    for text, f, colour, tw in imgs:
        d.text(((w - tw) // 2, y), text, font=f, fill=colour + (255,))
        y += f.size + 30
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)


def captioned_session(work: Path) -> tuple[Path, float]:
    events = json.loads(EVENTS.read_text(encoding="utf-8"))["events"]
    session_len = probe(SESSION) - 0.6
    print(f"session {session_len:.1f}s, {len(events)} events")
    master = work / "session.mp4"
    run(["ffmpeg", "-y", "-i", str(SESSION), "-t", f"{session_len:.2f}",
         "-r", str(FPS), "-c:v", "libx264", "-preset", "slow", "-crf", "18",
         "-pix_fmt", "yuv420p", str(master)])
    inputs = ["-i", str(master)]
    graph = []
    prev = "0:v"
    for i, e in enumerate(events):
        png = work / f"cap{i:02d}.png"
        caption_png(e["caption"], png)
        inputs += ["-i", str(png)]
        end = events[i + 1]["t"] if i + 1 < len(events) else e["t"] + 3.0
        end = min(end, session_len)
        graph.append(
            f"[{i + 1}:v]format=rgba[c{i}];"
            f"[{prev}][c{i}]overlay=(W-w)/2:H-h-64:"
            f"enable='between(t,{e['t']:.2f},{end:.2f})'[v{i}]")
        prev = f"v{i}"
    captioned = work / "captioned.mp4"
    run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(graph),
         "-map", f"[v{len(events) - 1}]", "-r", str(FPS),
         "-c:v", "libx264", "-preset", "slow", "-crf", "18",
         "-pix_fmt", "yuv420p", str(captioned)])
    return captioned, session_len


def has_audio(path: Path) -> bool:
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-select_streams", "a",
         "-show_entries", "stream=index", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True)
    return bool(r.stdout.strip())


def build_brand_clip(backdrop: Path, overlay: Path, out: Path,
                     keep_audio: bool) -> float:
    """底版 + 整帧品牌叠加（alpha 淡入淡出）。要求保留音轨而底版没有时补静音。"""
    chain = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=decrease:"
             f"flags=lanczos,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0xF4F0E7,"
             f"setsar=1[base];"
             f"[1:v]format=rgba,"
             f"fade=t=in:st=0.4:d=0.8:alpha=1,"
             f"fade=t=out:st={BRAND_LEN - 1.1:.2f}:d=0.9:alpha=1[ov];"
             f"[base][ov]overlay=0:0,"
             f"fade=t=in:st=0:d=0.4:color=0xF4F0E7,"
             f"fade=t=out:st={BRAND_LEN - 0.7:.2f}:d=0.7:color=0xF4F0E7,"
             f"fps={FPS},settb=AVTB,format=yuv420p[v]")
    cmd = ["ffmpeg", "-y"]
    if backdrop.suffix.lower() == ".png":
        cmd += ["-loop", "1"]          # 静帧底版必须循环，否则输出只有一帧
    cmd += ["-i", str(backdrop), "-loop", "1",
            "-i", str(overlay)]        # 叠加层同样要循环：单帧会让 fade 只算
                                       # t=0 的一帧（alpha≈0）然后被 repeat 到结尾
    want_silent_track = keep_audio and not has_audio(backdrop)
    if want_silent_track:
        cmd += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
        chain += f";[2:a]atrim=0:{BRAND_LEN + 1:.2f}[a]"
        maps = ["-map", "[v]", "-map", "[a]", "-shortest"]
    elif keep_audio:
        maps = ["-map", "[v]", "-map", "0:a?"]
    else:
        maps = ["-map", "[v]"]
    cmd += ["-filter_complex", chain, *maps,
            "-t", f"{BRAND_LEN:.2f}", "-r", str(FPS),
            "-c:v", "libx264", "-preset", "slow", "-crf", "17",
            "-pix_fmt", "yuv420p"]
    if keep_audio:
        cmd += ["-c:a", "aac", "-b:a", "128k"]
    cmd += [str(out)]
    run(cmd)
    return probe(out)


def main() -> int:
    if not SESSION.exists() or not EVENTS.exists():
        raise SystemExit("先跑 record_demo_film_v070.py")
    work = ROOT / ".tmp/demo-film-v070"
    work.mkdir(parents=True, exist_ok=True)

    # ---- 1. 品牌叠加层（官方 SVG → 透明 PNG → 整帧）
    logo = work / "brand-logo.png"
    render_logo_png(logo)
    open_overlay = brand_overlay(
        logo, [("开源 HTML 创作工作台", 46, COBALT),
               ("把一句话，变成一个能打开的网页", 34, GREY)],
        work / "brand-open.png", logo_y=340)
    close_overlay = brand_overlay(
        logo, [("把一句话，变成一个能打开的网页", 42, COBALT),
               ("GitHub: KratosLee-6/Html-ninefox · v0.7.0", 34, GREY)],
        work / "brand-close.png", logo_y=380)

    # ---- 2. 片头底版：优先本次 H3 生成，缺省回退既有底版
    open_src = H3_OPEN if H3_OPEN.exists() else OPENER_PLATE
    print("[stage] brand open"); print(f"opener backdrop: {open_src.name}"
          + ("（H3 新生成）" if open_src == H3_OPEN else "（既有 H3 底版）"))
    brand_open = work / "brand-open.mp4"
    build_brand_clip(open_src, open_overlay, brand_open, keep_audio=False)

    if has_audio(open_src):
        run(["ffmpeg", "-y", "-i", str(open_src), "-vn",
             "-t", f"{BRAND_LEN:.2f}", "-ar", "48000", "-ac", "2",
             "-c:a", "pcm_s16le", str(OPENING_AMBIENCE)])
        print(f"opening ambience: {probe(OPENING_AMBIENCE):.1f}s")

    # ---- 3. 片尾底版：优先本次 H3 生成，缺省用暖纸静帧
    if H3_CLOSE.exists():
        close_src = H3_CLOSE
        print("close backdrop: h3-close-v070.mp4（H3 新生成）")
    else:
        still = work / "paper-still.png"
        paper_frame().save(still)
        close_src = still
        print("close backdrop: 暖纸静帧（未提供 h3-close-v070.mp4）")
    brand_close = work / "brand-close.mp4"
    print("[stage] brand close")
    build_brand_clip(close_src, close_overlay, brand_close, keep_audio=False)

    # ---- 4. 正片（字幕叠加）
    print("[stage] captions")
    captioned, session_len = captioned_session(work)

    # ---- 4b. 旁白轨：由 scripts/build_narration_track.py 直接写 PCM。
    # 三版 ffmpeg filtergraph 都报成功而产出不可听。
    print("[stage] narration")
    narration = ROOT / ".tmp" / "demo-film-v070" / "narration.wav"
    if not narration.exists():
        print("  没有 narration.wav，先跑 build_narration_track.py")
        narration = None

    # ---- 5. 三段交叉溶解 + 配乐 + 旁白
    print("[stage] final mix")
    total = BRAND_LEN + session_len + BRAND_LEN

    # Three sources with three jobs: the ambience for the card, the bed under
    # the body, the voice over it.
    have_amb = OPENING_AMBIENCE.exists()
    vo_input = (["-i", str(OPENING_AMBIENCE)] if have_amb else []) + \
               (["-i", str(narration)] if narration is not None else [])
    amb_i, vo_i = 4, (5 if have_amb else 4)

    # adelay takes one delay PER CHANNEL. A bare `adelay=5000` delays the LEFT
    # channel only and leaves the right where it was, which put one voice at
    # t+5s in the left speaker and the same voice at t in the right — "two
    # narrations, offset from each other". Measured by splitting the master:
    # left's first speech at 7.62s, right's at 2.62s, exactly BRAND_LEN apart.
    delay = f"{int(BRAND_LEN * 1000)}|{int(BRAND_LEN * 1000)}"

    parts = [
        f"[{amb_i}:a]afade=t=out:st={BRAND_LEN - 1.5:.2f}:d=1.5,"
        f"volume=2.8[amb];" if have_amb else None,
        # 0.16 puts the bed roughly 16 dB under the voice. At 0.5 the master
        # measured 12 of 13 lines 5 to 11 dB BELOW the music.
        f"[3:a]atrim=0:{total:.2f},volume=0.16,"
        f"afade=t=in:st={BRAND_LEN:.2f}:d=1.8,"
        f"afade=t=out:st={max(0.0, total - 2.6):.2f}:d=2.6[bed];",
        f"[{vo_i}:a]adelay={delay},highpass=f=90,volume=1.4[vo];",
    ]
    vo_graph = "".join(p for p in parts if p)
    sources = (["[amb]"] if have_amb else []) + ["[bed]"] + \
              (["[vo]"] if narration is not None else [])
    vo_mix = "".join(sources) + \
        f"amix=inputs={len(sources)}:duration=longest:dropout_transition=0[a];"

    run(["ffmpeg", "-y", "-i", str(brand_open), "-i", str(captioned),
         "-i", str(brand_close), "-i", str(MUSIC), *vo_input,
         "-filter_complex",
         "[0:v]fps=25,settb=AVTB,format=yuv420p[i0];"
         "[1:v]fps=25,settb=AVTB,format=yuv420p[i1];"
         "[2:v]fps=25,settb=AVTB,format=yuv420p[i2];"
         "[i0][i1][i2]concat=n=3:v=1:a=0[v];"
         + vo_graph + vo_mix,
         "-map", "[v]", "-map", "[a]",
         "-r", str(FPS), "-c:v", "libx264", "-preset", "slow", "-crf", "17",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
         "-movflags", "+faststart", str(OUT)])
    print(f"master {OUT} {probe(OUT):.1f}s")

    # ---- 6. 海报帧（取成品段中后部的一帧）
    run(["ffmpeg", "-y",
         "-ss", f"{BRAND_LEN + session_len * 0.62:.2f}", "-i", str(OUT),
         "-frames:v", "1", "-q:v", "2", str(POSTER)])
    print(f"poster {POSTER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
