"""Finish the v0.7.0 demo recording: captions, H3 opener, music, master.

与 finish_demo_film.py 同一条纪律：界面 footage 是真实录屏，本阶段不得重绘
任何 UI。唯一的合成元素是：

  - H3 抽象片头（assets/promo/opener-h3-2k.mp4，文生视频模型只出现在
    提示词禁止一切文字的抽象氛围里）
  - 字幕条（Pillow 渲染 PNG 叠加；drawtext 在本机 CJK 会乱码，不可用）
  - 配乐（assets/promo/brand-bed.mp3）与片头自带的环境音

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

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

FPS = 25
ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / ".tmp/demo-run-video-v070"
SESSION = WORK / "session.webm"
EVENTS = WORK / "events.json"
PROMO = ROOT / "assets" / "promo"
OPENER_SRC = PROMO / "opener-h3-2k.mp4"
MUSIC = PROMO / "brand-bed.mp3"
OUT = PROMO / "htmlninefox-demo-v070-16x9.mp4"
POSTER = PROMO / "poster-demo-v070.png"

W, H = 1920, 1080
PAPER = (244, 240, 231)
COBALT = (23, 60, 143)
MINT = (73, 184, 148)
WHITE = (255, 253, 246)
BOLD = r"C:\Windows\Fonts\msyhbd.ttc"

OPENER_FRAMES = 100          # H3 底版取 4.0s
OPENER_TAIL = 10             # 末帧定格 0.4s，让交叉溶解落稳
OPENER_XF = 12               # 0.48s 交叉溶解


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


def main() -> int:
    if not SESSION.exists() or not EVENTS.exists():
        raise SystemExit("先跑 record_demo_film_v070.py")
    events = json.loads(EVENTS.read_text(encoding="utf-8"))["events"]
    session_len = probe(SESSION)
    print(f"session {session_len:.1f}s, {len(events)} events")

    work = ROOT / ".tmp/demo-film-v070"
    work.mkdir(parents=True, exist_ok=True)

    # ---- 1. 会话归一化（1920×1080@25，去尾部 0.6s 定格）
    master = work / "session.mp4"
    run(["ffmpeg", "-y", "-i", str(SESSION),
         "-t", f"{session_len - 0.6:.2f}",
         "-r", str(FPS), "-c:v", "libx264", "-preset", "slow", "-crf", "18",
         "-pix_fmt", "yuv420p", str(master)])

    # ---- 2. 字条 PNG + 一次合成叠加（每个事件显示到下一事件为止）
    inputs = ["-i", str(master)]
    for i, e in enumerate(events):
        png = work / f"cap{i:02d}.png"
        caption_png(e["caption"], png)
        inputs += ["-i", str(png)]
    # 逐级叠：上一级输出作为下一级 base；enable 窗口取自 events.json 的真实时刻
    graph = []
    prev = "0:v"
    for i, e in enumerate(events):
        end = events[i + 1]["t"] if i + 1 < len(events) else e["t"] + 3.0
        end = min(end, session_len - 0.6)
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

    # ---- 3. H3 片头（原生环境音保留）归一化 + 定格
    opener = work / "opener.mp4"
    chain_v = (f"tpad=stop_mode=clone:stop_duration={OPENER_TAIL / FPS:.6f},"
               f"scale={W}:{H}:force_original_aspect_ratio=decrease:flags=lanczos,"
               f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0xF4F0E7,fps={FPS}")
    run(["ffmpeg", "-y", "-i", str(OPENER_SRC), "-vf", chain_v,
         "-frames:v", str(OPENER_FRAMES + OPENER_TAIL),
         "-c:a", "aac", "-b:a", "128k", "-ac", "2", "-ar", "48000",
         "-c:v", "libx264", "-preset", "slow", "-crf", "17",
         "-pix_fmt", "yuv420p", str(opener)])

    # ---- 4. 片头交叉溶解 + 配乐混音（片头环境音淡出，床乐淡入）
    xf = OPENER_XF / FPS
    offset = probe(opener) - xf
    total = probe(opener) + probe(captioned) - xf
    run(["ffmpeg", "-y", "-i", str(opener), "-i", str(captioned),
         "-i", str(MUSIC),
         "-filter_complex",
         f"[0:v][1:v]xfade=transition=fade:duration={xf:.2f}:offset={offset:.2f}[v];"
         f"[0:a]volume=1.0,afade=t=out:st={offset - 1.2:.2f}:d=1.4[a0];"
         f"[2:a]atrim=0:{total:.2f},volume=0.9,afade=t=in:st={offset:.2f}:d=1.6,"
         f"afade=t=out:st={max(0.0, total - 2.2):.2f}:d=2.2[a1];"
         f"[a0][a1]amix=inputs=2:duration=longest:dropout_transition=0[a]",
         "-map", "[v]", "-map", "[a]",
         "-r", str(FPS), "-c:v", "libx264", "-preset", "slow", "-crf", "17",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
         "-movflags", "+faststart", str(OUT)])
    print(f"master {OUT} {probe(OUT):.1f}s")

    # ---- 5. 海报帧（取成品滚动中段的一帧）
    run(["ffmpeg", "-y", "-ss", f"{offset + probe(captioned) * 0.62:.2f}",
         "-i", str(OUT), "-frames:v", "1", "-q:v", "2", str(POSTER)])
    print(f"poster {POSTER}")
    return 0


def tw_of(png: Path) -> int:
    with Image.open(png) as im:
        return im.width


if __name__ == "__main__":
    raise SystemExit(main())
