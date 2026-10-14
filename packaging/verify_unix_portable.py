"""验证 macOS / Linux 产物**真的能跑**——与 verify_portable.py 同一纪律的 unix 版。

Windows 便携包有 verify_portable.py（真实启动 + 健康检查 + 产物内容断言）；
此前 macOS .app 与 Linux .deb 只有构建 job 变绿，从不被执行——正是
2026-09-29 desktop.py 缺 import sys 那次事故留下的盲区在两个平台上原样
存在：一个能让全部测试变绿、打包 job 变绿、却无法启动的发布物。

用法（见各平台构建脚本的 workflow 步骤）：

    python packaging/verify_unix_portable.py \
        --entry <可执行或命令> [--arg X]... \
        --expect-distribution macos-portable|python-app

流程与 verify_portable 一致：真实启动 → 探测 /api/health（版本 + 发行形态）
→ 首页品牌标记 → 静态资源非空 → **内容标记**（断言伺服出来的字节带着本
版本新增过的符号，陈旧产物在这里被抓住）→ 干净退出。
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PORTS = [8620, *range(8621, 8641)]

# 路由名不等于文件名：/motion-lab 服务的是 motion-lab.html。
STATIC_ROUTES = ("/workbench-system.css", "/lifecycle-intake.js",
                 "/motion-lab", "/classic", "/sw.js", "/icon.svg")

# 内容标记锁定的是「本版本真正新增过」的符号，与 verify_portable 同一原则：
# 一份用陈旧源码打出来的包能把六条路由全伺服出来、版本号都对，唯独没有
# 这些符号。FoxState 是 v0.7.5（C7 状态声明）引入的；window.FoxActions 与
# expected_revision 是更早的动作派发表与写回协议。断言留在 /fox-core.js 与
# lifecycle 模块上，而不是曾经承载过它们的 / 上。
CONTENT_EXPECTATIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("/workbench-system.css", ("--fs-", "--fw-", "--space-")),
    ("/", ("--on-accent", "Html九尾狐")),
    ("/fox-core.js", ("window.FoxActions", "window.FoxState")),
    ("/lifecycle-slides.js", ("expected_revision",)),
    ("/lifecycle-intake.js", ("fetchBatch",)),
)


def version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    return re.search(r'^version = "([^"]+)"', text, re.MULTILINE).group(1)


def probe_health(timeout: float = 90.0, proc=None) -> tuple[int, dict]:
    deadline = time.monotonic() + timeout
    last = ""
    while time.monotonic() < deadline:
        for port in DEFAULT_PORTS:
            try:
                with urllib.request.urlopen(
                        f"http://127.0.0.1:{port}/api/health", timeout=3) as raw:
                    return port, json.loads(raw.read().decode("utf-8"))
            except (urllib.error.URLError, ConnectionError, OSError) as exc:
                last = repr(exc)
        if proc is not None and proc.poll() is not None:
            break
        time.sleep(1.0)
    if proc is not None and proc.stdout is not None:
        try:
            out = proc.stdout.read() if hasattr(proc.stdout, "read") else b""
            if out:
                print("产物自身输出：\n" + out.decode("utf-8", "replace")[-2000:])
        except (OSError, ValueError):
            pass
    raise SystemExit(f"产物在 {timeout:.0f}s 内没有提供服务：{last}")


def fetch(port: int, route: str, timeout: float = 10.0) -> bytes:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{route}", timeout=timeout) as raw:
        return raw.read()


def verify_content(port: int) -> int:
    served: dict[str, str] = {}
    bad = 0
    for route, markers in CONTENT_EXPECTATIONS:
        if route not in served:
            served[route] = fetch(port, route).decode("utf-8", "replace")
        body = served[route]
        missing = [m for m in markers if m not in body]
        if missing:
            print(f"  产物内容不符：{route} 缺少 {missing}")
            bad += 1
        else:
            print(f"  产物内容符合：{route} 含 {list(markers)}")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="启动 unix 产物并验证健康/版本/内容")
    ap.add_argument("--entry", required=True,
                    help="要启动的可执行文件或命令（PATH 内可执行名亦可）")
    ap.add_argument("--arg", action="append", default=[],
                    help="传给产物的参数，可重复；通常 --arg --no-browser")
    ap.add_argument("--expect-distribution", default=None,
                    help="断言 /api/health 的 distribution 字段")
    ap.add_argument("--cwd", default=None, help="产物的工作目录")
    args = ap.parse_args()

    entry = args.entry if Path(args.entry).is_absolute() or "/" not in args.entry \
        else str(Path(args.entry).resolve())
    cmd = [entry, *args.arg]
    print(f"验证：{cmd}")
    proc = subprocess.Popen(cmd, cwd=args.cwd,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        port, health = probe_health(proc=proc)
        print(f"  /api/health -> {health}")
        if not health.get("ok"):
            print("  health 未回报 ok")
            return 1
        want = version()
        if health.get("version") != want:
            print(f"  版本不符：期望 {want}，实际 {health.get('version')}")
            return 1
        if args.expect_distribution and health.get("distribution") != args.expect_distribution:
            print(f"  发行形态不符：期望 {args.expect_distribution}，"
                  f"实际 {health.get('distribution')}")
            return 1
        print(f"  版本与发行形态一致：{want} / {health.get('distribution')}")

        page = fetch(port, "/").decode("utf-8", "replace")
        if "像素花园工作台" not in page and "Html九尾狐" not in page:
            print("  首页不含品牌标记")
            return 1
        print(f"  首页 {len(page)/1024:.0f} KB，含品牌标记")

        for route in STATIC_ROUTES:
            size = len(fetch(port, route))
            print(f"  静态资源 {route} {size/1024:.0f} KB")
            if size < 200:
                print(f"  {route} 异常小，疑似未打进包")
                return 1

        if verify_content(port):
            print("  内容断言失败——产物很可能是用陈旧源码打出来的")
            return 1
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except (subprocess.TimeoutExpired, OSError):
            proc.kill()
    print("  进程已关闭")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
