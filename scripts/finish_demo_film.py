"""Finish the recorded session: captions, music, H3 opener, final master.

The interface footage is a real recording, not a generated or composited
one, so this stage must not repaint any UI. The only synthetic elements are:

  - an H3 abstract opener (its prompt forbids all text, which is the only
    reason a text-to-video model is usable here at all)
  - caption bars carrying the real numbers the product reported
  - the music bed and action SFX

Captions are rendered by Pillow to PNG and overlaid. drawtext is unusable on
this machine: inline CJK arrives as codepage mojibake, textfile under this
repo's CJK path makes the whole filtergraph unparseable, and this ffmpeg
build has no `charset` option to force UTF-8.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

FPS = 25
ROOT = Path(__file__).resolve().parent.parent
REPO = ROOT
FILM = ROOT.parent / "film"
OUT = ROOT / ".tmp/demo-final"
SESSION = ROOT / ".tmp/demo-run-video/session.webm"
OPENER = ROOT / "assets/promo/opener-h3-2k.mp4"
BED = ROOT / "assets/promo/brand-bed.mp3"
SFX = FILM / "sfx"

PAPER = (0xF4, 0xF0, 0xE7)
INK = (0x17, 0x28, 0x3D)
W, H = 1920, 1080

# 96 frames of opener: with the 46.64s recording this lands the film on
# exactly 50.00s (46.88s trimmed + 3.44s of opener - the 0.4s overlap), which
# is why this value is not 90. Verified by the whole-second gate below.
OPENER_FRAMES = 96
OPENER_XF = 10
MUSIC_VOL = 0.26
SFX_VOL = 0.7


def run(cmd: list[str], cwd: Path | None = None) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=cwd)
    if r.returncode != 0:
        raise SystemExit(f"ffmpeg failed:\n{' '.join(cmd[:10])}...\n"
                         f"{r.stderr[-1800:]}")


def probe(p: Path, entries: str) -> str:
    return subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", entries, "-of", "csv=p=0",
         str(p)], capture_output=True, text=True).stdout.strip()


def caption_png(text: str, out: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 36)
    tb = d.textbbox((0, 0), text, font=font)
    tw, th = tb[2] - tb[0], tb[3] - tb[1]
    x, y = (W - tw) // 2, H - th - 64
    d.rounded_rectangle([x - 20, y - 18, x + tw + 20, y + th + 18],
                        radius=6, fill=(*PAPER, 238))
    d.text((x, y - tb[1]), text, font=font, fill=(*INK, 255))
    img.save(out)


# Caption timings are measured against the real recording, whose runtime is
# derived from the file rather than assumed. Each cue sits over the moment the
# thing it names is actually on screen.
#
# The English set is a separate recording (scripts/record_demo_film.py --lang
# en) whose runtime and reported numbers differ — 50.36s and 72% confidence
# against the Chinese 46.64s and 67%. Every figure below is the one that
# recording actually produced; nothing is carried over.
CAPTIONS_ZH = [
    (1.2, 5.4, "打开工作台"),
    (5.4, 9.0, "点「输入需求」，写下你真正想要的东西"),
    (9.0, 12.0, "一句话就够，不必先想清楚结构"),
    (13.4, 19.0, "它会告诉你自己有多确定 · 置信度 67%"),
    (19.0, 27.5, "采用推荐并生成 · 需求分析 8ms → 保存交付 40ms"),
    (27.5, 33.0, "六个真实区块，真实文案"),
    (33.0, 37.5, "是真页面，不是效果图 · rev0"),
    (38.5, 46.6, "交付前先给你打分 · 兼容性 100"),
]

CAPTIONS_EN = [
    (1.4, 6.0, "Open the workbench"),
    (6.0, 9.4, "Click New requirement and type what you actually want"),
    (9.4, 13.0, "One sentence is enough — no structure needed up front"),
    (14.0, 21.0, "It tells you how sure it is · 72% confidence"),
    (21.0, 30.0, "Adopt and generate · analysis 8ms → delivery 40ms"),
    (30.0, 36.0, "Six real sections, real copy"),
    (36.0, 40.5, "A real page, not a mockup · rev0"),
    (41.5, 50.3, "Scored before you ship it · compatibility 100"),
]

SFX_CUES = [
    (5.6, "click.wav"),      # panel opens
    (9.2, "typing.wav"),     # characters land
    (13.6, "resolve.wav"),   # analysis returns
    (19.2, "ding-dong.wav"), # generation starts
    (33.4, "pop.wav"),       # output node focused
    (38.8, "sweep.wav"),     # export centre opens
]


def main() -> int:
    lang = "zh"
    if "--lang" in sys.argv:
        lang = sys.argv[sys.argv.index("--lang") + 1]
    if lang not in ("zh", "en"):
        raise SystemExit(f"unknown --lang {lang!r}")

    captions = CAPTIONS_ZH if lang == "zh" else CAPTIONS_EN
    suffix = "" if lang == "zh" else f"-{lang}"
    # SESSION/OUT are the zh baselines; derive the per-language paths from the
    # same parent. Building them off SESSION.parent would nest them as
    # .tmp/demo-run-video/demo-run-video-en.
    session = ROOT / f".tmp/demo-run-video{suffix}/session.webm"
    out_dir = ROOT / f".tmp/demo-final{suffix}"
    cpath = Path(tempfile.gettempdir()) / f"fox-demo-captions{suffix}"

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cpath.mkdir(parents=True, exist_ok=True)

    assert session.exists(), f"run record_demo_film.py --lang {lang} first"
    sess_dur = float(probe(session, "format=duration"))
    sess_frames = int(round(sess_dur * FPS))
    total_frames = OPENER_FRAMES + sess_frames - OPENER_XF
    total_s = total_frames / FPS
    print(f"session {sess_dur:.3f}s / {sess_frames} frames; "
          f"+ opener {OPENER_FRAMES} - xfade {OPENER_XF} = {total_s:.3f}s")
    if abs(total_s - round(total_s)) > 1e-9:
        # The filename must equal the runtime, and this project has already
        # broken that three times. A real recording cannot be lengthened, so
        # the only honest move is to trim to a whole second.
        #
        # Both roundings must be tried. An earlier version only considered
        # round() (i.e. always up) and refused the English cut outright even
        # though flooring it was perfectly feasible: 50.36s + 3.44s of opener
        # = 53.80s, and 53s needs only 49.56s of session, which the 50.36s
        # recording comfortably covers.
        opener_s = (OPENER_FRAMES - OPENER_XF) / FPS
        best = None
        for target in (int(total_s), int(total_s) + 1):
            want_sess = target - opener_s
            if want_sess <= sess_dur and want_sess > 0:
                best = (target, want_sess)
                break
        if best is None:
            raise SystemExit(
                f"cannot land on a whole second: session is {sess_dur:.3f}s "
                f"and the opener is {opener_s:.3f}s. "
                f"Re-record with a slightly different length, or change "
                f"OPENER_FRAMES.")
        target, want_sess = best
        sess_frames = int(round(want_sess * FPS))
        total_frames = OPENER_FRAMES + sess_frames - OPENER_XF
        total_s = total_frames / FPS
        print(f"  trimmed session {sess_dur:.3f}s -> {want_sess:.3f}s "
              f"to land on {target}s exactly")

    # ---- captions as transparent PNGs, burned in over the recording
    for i, (a, b, text) in enumerate(captions, 1):
        if a >= total_s:
            break
        caption_png(text, cpath / f"c{i:02d}.png")

    inputs = ["-i", str(session)]
    for i, (a, b, _t) in enumerate(captions, 1):
        if a >= total_s:
            break
        inputs += ["-i", str(cpath / f"c{i:02d}.png")]

    # Shift body captions by the opener.
    shift = (OPENER_FRAMES - OPENER_XF) / FPS
    # Label the graph by construction: each overlay consumes vn-1 and emits
    # vn, so the final label is the number of captions actually applied. An
    # earlier version counted from 1 and asked for v8 where v7 existed, which
    # ffmpeg reports as a valid-looking error deep in a stream dump.
    steps: list[str] = []
    n = 1
    for i, (a, b, _t) in enumerate(captions, 1):
        if a >= total_s:
            break
        s = a + shift
        e = min(b + shift, total_s)
        steps.append(f"[v{n-1}][{i}:v]overlay=0:0:format=auto:"
                     f"enable='between(t,{s:.3f},{e:.3f})'[v{n}]")
        n += 1
    final_label = f"[v{n-1}]"

    labelled = out_dir / "labelled.mov"
    run(["ffmpeg", "-y", *inputs, "-filter_complex",
         "[0:v]fps=25,scale=1920:1080,format=rgba[v0];"
         + ";".join(steps)
         + f";{final_label}format=yuv420p[v]",
         "-map", "[v]", "-t", f"{sess_frames/FPS:.4f}",
         "-c:v", "libx264", "-preset", "slow", "-crf", "18",
         "-r", str(FPS), str(labelled)])

    # ---- H3 opener in front
    spliced = out_dir / "spliced.mp4"
    run(["ffmpeg", "-y", "-i", str(OPENER), "-i", str(labelled),
         "-filter_complex",
         f"[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,"
         f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0xF4F0E7,fps={FPS},"
         f"settb=AVTB,trim=end_frame={OPENER_FRAMES},setpts=PTS-STARTPTS[op];"
         f"[1:v]settb=AVTB[b];"
         f"[op][b]xfade=transition=fade:duration={OPENER_XF/FPS:.3f}"
         f":offset={(OPENER_FRAMES-OPENER_XF)/FPS:.3f}[v]",
         "-map", "[v]", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
         "-pix_fmt", "yuv420p", "-r", str(FPS), str(spliced)])

    # ---- music + SFX
    ainputs = ["-i", str(BED)]
    delays = []
    for j, (at, f) in enumerate(SFX_CUES):
        wav = SFX / f
        assert wav.exists(), f"missing {wav}"
        ainputs += ["-i", str(wav)]
        ms = int((at + shift) * 1000)
        delays.append(f"[{j+2}:a]adelay={ms}|{ms},volume={SFX_VOL}[s{j}]")
    labels = "".join(f"[s{j}]" for j in range(len(delays)))
    # Pad the audio to exactly the picture length, then drop -shortest.
    # -shortest was ending the film up to 4 frames early whenever the mixed
    # track came in marginally shorter than the video (observed: 49.84s vs a
    # planned 50.00s), which is a silent truncation of the last shot.
    af = (f"[1:a]atrim=0:{total_s},asetpts=PTS-STARTPTS,afade=t=in:st=0:d=1.6,"
          f"afade=t=out:st={total_s-2.2:.3f}:d=2.2,volume={MUSIC_VOL}[bed];"
          + ";".join(delays)
          + f";[bed]{labels}amix=inputs={1+len(delays)}:duration=longest:"
            f"dropout_transition=0,apad,atrim=end={total_s},"
            f"asetpts=PTS-STARTPTS,alimiter=limit=0.92[a]")

    final = out_dir / "final.mp4"
    run(["ffmpeg", "-y", "-i", str(spliced), *ainputs, "-filter_complex", af,
         "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac",
         "-b:a", "192k", "-ar", "48000", "-ac", "2", str(final)])

    dur = float(probe(final, "format=duration"))
    print(f"\nfinal: {dur:.6f}s / {int(round(dur*FPS))} frames")
    # One frame of tolerance: container duration can round down a fraction.
    if abs(dur - total_s) > 1.0 / FPS + 0.02:
        raise SystemExit(f"final {dur}s != planned {total_s}s")
    print(probe(final, "stream=codec_name,nb_frames,width,height,sample_rate,"
                       "channels").replace("\n", "  "))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
