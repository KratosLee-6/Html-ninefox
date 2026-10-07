# -*- coding: utf-8 -*-
"""generate_h3_clips_v070.py · 用 MiniMax H3 生成品牌片头与片尾的氛围底版。

产物（供 finish_demo_film_v070.py 做品牌叠加）：
    片头氛围 5 秒与片尾氛围 5 秒各一段，写入发布素材目录。

用法（在仓库根目录执行，脚本位于 scripts 目录）：
    set MINIMAX_API_KEY=你的key
    python -m scripts.generate_h3_clips_v070            # 生成两个底版
    python -m scripts.generate_h3_clips_v070 --prompts  # 只打印提示词，可贴网页版

纪律（与 README 一致）：H3 只生成不含任何文字与 Logo 的抽象氛围；
文字与 Logo 由 finish 脚本用官方 SVG 渲染后确定性叠加——文生视频模型
画中文字会乱码，这是上一版就定下的边界。

提示词按官方三段式（参考素材说明 + 核心创意 + 画面过程说明）；
非叙事性音乐明确排除，成片的音乐由 finish 阶段统一铺。

出站请求的安全边界与产品 intake 同一条纪律：
  仅 https；主机名必须在平台域名白名单后缀内；连接前解析 DNS，
  任一 IP 非公网（私网、环回、保留）即拒绝；产物名只允许出现在
  脚本顶部的允许清单里，写入位置固定为发布素材目录。
"""
from __future__ import annotations

import argparse
import http.client
import ipaddress
import json
import os
import socket
import sys
import time
import urllib.parse
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
PROMO = (ROOT / "assets" / "promo").resolve()

# ---- 配置：平台若调整字段名或域名，只改这里 --------------------------------
API_HOST = "api.minimax.chat"          # 固定 API 主机（字面量）
ALLOWED_HOST_SUFFIX = ".minimax.chat"  # 文件下载主机的白名单后缀
MODEL = "H3"
DURATION = 5                           # H3 规格边界 4 到 15 秒
RESOLUTION = "1440p"                   # 官方推荐档；finish 阶段缩到 1920×1080
PROMPT_OPTIMIZER = True
# ---------------------------------------------------------------------------

OPEN_PROMPT = (
    "核心创意：在暖纸白色的平整纸面上，一幅极简抽象的光影动画——极细的浅灰方格"
    "网格纹理铺满画面，一道薄荷绿色（#49B894）的柔光与一道钴蓝色（#173C8F）的光带"
    "缓缓流动、交汇、再安静收敛，写实广告片质感，构图极简、留白充分，固定机位缓慢"
    "推近。"
    "画面过程：0到2秒，大全景，暖纸白色纸面（#F4F0E7）与浅灰方格网格静止，一道"
    "薄荷绿柔光从画面左侧缓缓流入；2到4秒，中景，钴蓝色光带自画面右下方缓缓滑行"
    "至中央，与薄荷绿柔光交汇处泛起细微光尘；4到5秒，两道光缓缓收敛成一条水平"
    "亮线，画面归于安静。"
    "非叙事性音乐：N/A。画面全程不得出现任何文字、字母、数字、Logo、水印或人物。"
)

CLOSE_PROMPT = (
    "核心创意：与开场同款的暖纸白纸面与浅灰方格网格，这一次光从安静中缓缓散开——"
    "钴蓝色（#173C8F）与薄荷绿色（#49B894）两条光带从画面中央的水平亮线向两侧"
    "舒展、上浮、消散，写实广告片质感，固定机位缓慢拉远，情绪是收束与余韵。"
    "画面过程：0到2秒，中景，画面中央一条水平薄荷绿亮线轻轻呼吸（明暗两次）；"
    "2到4秒，大全景，钴蓝光带自中央向右上方缓缓展开消散，薄荷光向左下铺开；"
    "4到5秒，只剩安静的暖纸白纸面与方格网格，微光归零。"
    "非叙事性音乐：N/A。画面全程不得出现任何文字、字母、数字、Logo、水印或人物。"
)

ALLOWED_OUTPUT_NAMES = ("h3-open-v070.mp4", "h3-close-v070.mp4")
CLIPS = [
    ("h3-open-v070.mp4", OPEN_PROMPT),
    ("h3-close-v070.mp4", CLOSE_PROMPT),
]


def _check_host(host: str) -> None:
    """主机必须在白名单后缀内，且 DNS 解析全部是公网地址。"""
    if not host or ":" in host or "/" in host:
        raise SystemExit(f"非法主机名：{host!r}")
    if host != API_HOST and not host.endswith(ALLOWED_HOST_SUFFIX):
        raise SystemExit(f"主机不在白名单内：{host}")
    for info in socket.getaddrinfo(host, 443):
        addr = ipaddress.ip_address(info[4][0])
        if not addr.is_global:
            raise SystemExit(f"主机解析到非公网地址（{addr}），拒绝连接：{host}")


def _https_json(host: str, path: str, key: str, *, body: dict | None = None) -> dict:
    """对白名单主机的 https JSON 请求；path 必须以斜杠开头。"""
    if not path.startswith("/"):
        raise SystemExit(f"非法路径：{path!r}")
    _check_host(host)
    conn = http.client.HTTPSConnection(host, 443, timeout=120)
    payload = json.dumps(body) if body is not None else None
    try:
        conn.request("POST" if body is not None else "GET", path,
                     body=payload,
                     headers={"Authorization": f"Bearer {key}",
                              "Content-Type": "application/json"})
        resp = conn.getresponse()
        return json.loads(resp.read().decode())
    finally:
        conn.close()


def _download(host: str, path: str, key: str, name: str) -> None:
    """下载生成的视频文件。主机走同一白名单；产物必须落在发布素材目录内。"""
    _check_host(host)
    if name not in ALLOWED_OUTPUT_NAMES:
        raise SystemExit(f"产物名不在允许清单内：{name}")
    out = (PROMO / name).resolve()
    try:
        out.relative_to(PROMO)
    except ValueError as exc:
        raise SystemExit(f"产物路径越界：{out}") from exc
    conn = http.client.HTTPSConnection(host, 443, timeout=300)
    try:
        conn.request("GET", path, headers={"Authorization": f"Bearer {key}"})
        resp = conn.getresponse()
        out.write_bytes(resp.read())
    finally:
        conn.close()


def generate_one(name: str, prompt: str, key: str) -> Path:
    if name not in ALLOWED_OUTPUT_NAMES:
        raise SystemExit(f"产物名不在允许清单内：{name}")
    out = PROMO / name
    if out.exists():
        print(f"[skip] {name} 已存在（删除后可重生成）")
        return out
    print(f"[task] {name} 提交生成…")
    resp = _https_json(API_HOST, "/v1/video_generation", key, body={
        "model": MODEL,
        "prompt": prompt,
        "duration": DURATION,
        "resolution": RESOLUTION,
        "prompt_optimizer": PROMPT_OPTIMIZER,
    })
    if resp.get("base_resp", {}).get("status_code") != 0:
        raise SystemExit("提交失败，请对照平台文档核对顶部配置字段：\n"
                         + json.dumps(resp, ensure_ascii=False))
    task_id = resp["task_id"]
    print(f"[task] task_id={task_id} 轮询中…")
    for _ in range(120):  # 最多 10 分钟
        time.sleep(5)
        q = _https_json(API_HOST,
                        "/v1/query/video_generation?task_id=" + task_id, key)
        status = q.get("status")
        if status == "Success":
            meta = _https_json(API_HOST,
                               "/v1/files/retrieve?file_id=" + q["file_id"], key)
            download = urllib.parse.urlsplit(meta["file"]["download_url"])
            _download(download.hostname, download.path, key, name)
            print(f"[done] {out}  {out.stat().st_size/1024/1024:.1f} MB")
            return out
        if status == "Fail":
            raise SystemExit(f"生成失败：{json.dumps(q, ensure_ascii=False)}")
        print(f"  … {status}")
    raise SystemExit("轮询超时（10 分钟），请稍后重查 task_id")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompts", action="store_true",
                    help="只打印提示词（供网页版粘贴）")
    args = ap.parse_args()
    if args.prompts:
        for name, prompt in CLIPS:
            print(f"\n===== {name} =====\n{prompt}")
        return 0
    key = os.environ.get("MINIMAX_API_KEY", "").strip()
    if not key:
        raise SystemExit(
            "缺少 MINIMAX_API_KEY 环境变量。没有 key 也可以：加 --prompts 参数"
            "打印提示词，贴进 MiniMax 网页版生成，下载后按允许清单里的名字"
            "放到发布素材目录。")
    PROMO.mkdir(parents=True, exist_ok=True)
    for name, prompt in CLIPS:
        generate_one(name, prompt, key)
    print("\n两个底版就绪。接下来在仓库根目录重跑品牌合成：")
    print("  python scripts" + os.sep + "finish_demo_film_v070.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
