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

脚本会真实启动 exe，并验证版本、发行形态、首页、静态资源、**产物内容**与干净退出。

「内容」这一层不是形式检查：它断言冻结包经 HTTP 伺服出来的资源里确实带着
本版本新增或修复过的标记（尺度 token、`--on-accent`、PPTX 选项、动作派发表、
`expected_revision` 等）。收敛前的源码不具备这些符号，因此一份陈旧产物会在
这里被抓住，而不会带着「六个路由全通、体积正常」的假象一路走进 Release。
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

# Windows runner 的 stdout 是 cp1252，直接打印中文会在第一行就 UnicodeEncodeError。
# 本地控制台能打出来不代表 CI 能——这条正是把验证接进流水线之后才暴露的。
for _stream in (sys.stdout, sys.stderr):
    try:
        if (_stream.encoding or "").lower().replace("-", "") not in ("utf8", "cp936", "gbk"):
            _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # 已重定向到无 encoding 的流
        pass

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PORTS = [8620, *range(8621, 8641)]

# 路由名不等于文件名：/motion-lab 服务的是 motion-lab.html。
STATIC_ROUTES = ("/workbench-system.css", "/lifecycle-intake.js",
                 "/motion-lab", "/classic", "/sw.js", "/icon.svg")

# 为什么还要验内容
# ----------------
# 「文件存在且大于 200 字节」只能证明包里塞了东西，证明不了塞的是**这一版**的
# 东西。一份用旧源码打出来的包，能把上面六条路由全伺服出来、能报出正确的版本号，
# 却让用户拿到收敛前的界面与失效的按钮——而本项目这一版修的几乎全是这类
# 「服务端齐备、界面不可达 / 内容陈旧」的问题。只查体积，恰好查不到它们。
#
# 因此下面每条断言都锁定**本版本真正新增或修复过**的具体标记：
# 收敛前的工作台里不存在这些符号，所以一条陈旧产物会立刻被抓住。
CONTENT_EXPECTATIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    # 收敛前的 17 种字号 / 7 种字重 / 140 余个硬编码间距
    ("/workbench-system.css", ("--fs-", "--fw-", "--space-")),
    # 夜蓝主题主按钮对比度修复引入的语义令牌
    ("/", ("--on-accent",)),
    # 导出中心的 PPTX 选项（此前根本没登记）、动作派发表、批量抓取转发函数
    ("/", ("export-format", "PPTX", "FoxActions", "intakeFetchBatch")),
    # 幻灯片写回的并发保护、吸收批量的入口、revision 写回的唯一拥有者
    ("/lifecycle-slides.js", ("expected_revision",)),
    ("/lifecycle-intake.js", ("fetchBatch",)),
    ("/lifecycle-revisions.js", ("advanceNodeRevision",)),
)


def version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    return re.search(r'^version = "([^"]+)"', text, re.MULTILINE).group(1)


def probe_health(timeout: float = 90.0, proc=None) -> tuple[int, dict]:
    """按默认端口逐个探测。应用不读环境变量端口，用的是 launcher 的默认/回落。

    探测失败时把 exe 自己的输出打出来——否则 CI 日志只会显示「连不上」，
    而真正的崩溃原因（正是当初 desktop.py 那个 NameError）被管道吞掉了。
    """
    deadline = time.monotonic() + timeout
    last = ""
    while time.monotonic() < deadline:
        for port in DEFAULT_PORTS:
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=3) as raw:
                    return port, json.loads(raw.read().decode("utf-8"))
            except (urllib.error.URLError, ConnectionError, OSError) as exc:
                last = repr(exc)
        if proc is not None and proc.poll() is not None:
            break
        time.sleep(1.0)
    if proc is not None and proc.stdout is not None:
        try:
            out = proc.stdout.read()
            for enc in ("utf-8", "gbk", "cp1252", "latin-1"):
                print("产物自身输出：\n" + out.decode(enc, "replace"))
                break
        except (OSError, ValueError):
            pass
    raise SystemExit(f"产物在 {timeout:.0f}s 内没有提供服务：{last}")


def fetch(port: int, route: str, timeout: float = 10.0) -> bytes:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{route}", timeout=timeout) as raw:
        return raw.read()


def verify_content(port: int) -> int:
    """断言产物**伺服出来的**就是这一版的资源，而不只是「路由有响应」。

    抓的是冻结包经 HTTP 返回的字节，不是仓库里的源文件——这正是关键差别：
    源文件是对的、打进包的却是旧的，这道检查才抓得住。
    """
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
    if bad:
        print(f"  {bad} 项内容断言失败——产物很可能是用陈旧源码打出来的")
    return 1 if bad else 0


def verify(exe: Path, label: str) -> int:
    print(f"验证 {label}：{exe}")
    proc = subprocess.Popen([str(exe)], cwd=str(exe.parent),
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

        rc = verify_content(port)
        if rc:
            return rc
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
        print("\n产物验证通过：能启动、版本与形态正确、首页与静态资源完整、"
              "伺服内容与本版本一致。")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
