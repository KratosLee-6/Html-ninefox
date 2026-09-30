"""验证打包产物**真的能跑**，而不只是「构建 job 变绿」。

为什么需要这道检查
------------------
CI 的打包 job 只**构建**产物，从不**执行**它。2026-09-29 的发布前本地验证
发现 `desktop.py` 用了 `sys.platform` 却从未 `import sys`——Windows 便携包与
安装器**一启动就崩**（`NameError: name 'sys' is not defined`），而 CI 全程
绿灯，因为源码测试套件从不走冻结入口这条路。

也就是说：**一个能通过全部测试、能让打包 job 变绿、却完全无法启动的发布物，
是这套流水线当时能生产出来的。**

用法
----
先在 Windows 上构建便携包，再执行本脚本：

    python packaging/windows/build_portable.py
    python packaging/verify_portable.py

macOS 产物同理可用 `packaging/verify_portable.py <解压目录> <app 可执行>`
的等价物在对应平台验证；本脚本针对 Windows 便携包。

脚本会真实启动 exe，并验证版本、发行形态、首页、静态资源与干净退出。
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PORTS = [8620, *range(8621, 8641)]

# 路由名不等于文件名：/motion-lab 服务的是 motion-lab.html。
STATIC_ROUTES = ("/workbench-system.css", "/lifecycle-intake.js",
                 "/motion-lab", "/classic", "/sw.js", "/icon.svg")


def version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    return re.search(r'^version = "([^"]+)"', text, re.MULTILINE).group(1)


def probe_health(timeout: float = 90.0) -> tuple[int, dict]:
    """按默认端口逐个探测。应用不读环境变量端口，用的是 launcher 的默认/回落。"""
    deadline = time.monotonic() + timeout
    last = ""
    while time.monotonic() < deadline:
        for port in DEFAULT_PORTS:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=3) as raw:
                    return port, json.loads(raw.read().decode("utf-8"))
            except (urllib.error.URLError, ConnectionError, OSError) as exc:
                last = repr(exc)
        time.sleep(1.0)
    raise SystemExit(f"产物在 {timeout:.0f}s 内没有提供服务：{last}")


def verify(exe: Path, label: str) -> int:
    print(f"验证 {label}：{exe}")
    proc = subprocess.Popen([str(exe)], cwd=str(exe.parent),
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    try:
        port, health = probe_health()
        print(f"  /api/health -> {health}")
        want = version()
        if health.get("version") != want:
            print(f"  版本不符：期望 {want}，实际 {health.get('version')}")
            return 1
        if health.get("distribution") != "windows-portable":
            print(f"  发行形态标注异常：{health.get('distribution')}")
            return 1
        print(f"  版本与发行形态一致：{want} / {health['distribution']}")

        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=10) as raw:
            page = raw.read().decode("utf-8", "replace")
        if "像素花园工作台" not in page and "Html九尾狐" not in page:
            print("  首页不含品牌标记")
            return 1
        print(f"  首页 {len(page)/1024:.0f} KB，含品牌标记")

        for route in STATIC_ROUTES:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}{route}", timeout=10) as raw:
                size = len(raw.read())
            print(f"  静态资源 {route} {size/1024:.0f} KB")
            if size < 200:
                print(f"  {route} 异常小，疑似未打进包")
                return 1
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
    print(f"  进程已关闭")
    return 0


def main() -> int:
    archives = sorted((ROOT / "release").glob("HtmlNineFox-Windows-x64-*.zip"))
    if not archives:
        print("release/ 下没有 Windows 便携包，先运行 packaging/windows/build_portable.py")
        return 2
    archive = archives[-1]
    work = ROOT / "build" / "verify-portable"
    work.mkdir(parents=True, exist_ok=True)
    print(f"解包：{archive.name} ({archive.stat().st_size/1e6:.1f} MB)")
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(work)
    exe = next(work.rglob("HtmlNineFox.exe"), None)
    if exe is None:
        print(f"{archive.name} 里没有 HtmlNineFox.exe")
        return 2
    code = verify(exe, archive.name)
    if code == 0:
        print("\n产物验证通过：能启动、版本与形态正确、首页与静态资源完整。")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
