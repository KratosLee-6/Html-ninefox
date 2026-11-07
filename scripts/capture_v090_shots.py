"""v0.9.0 发版取证：真桌面壳窗口 + 风格轴推荐卡（全部真实运行）。

    evidence-shell-loader.png     Tauri 壳加载页（🦊 呼吸 + 启动文案，真窗口）
    evidence-shell-workbench.png  壳内工作台（sidecar 健康后 webview 导航完成）
    evidence-style-recommend.png  推荐组合卡：🎬 动效人格徽章 + 💡 中文理由

壳取证走 win32 PrintWindow（PW_RENDERFULLCONTENT，WebView2 可捕获）；
窗口与 sidecar 均为真实进程，取证后回收。风格轴走真实 analyze 派发。
"""
from __future__ import annotations

import ctypes
import subprocess
import sys
import tempfile
import time
import urllib.parse
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

OUT = ROOT / "assets" / "screenshots" / "v0.9.0"
SHELL_EXE = ROOT / "src-tauri" / "target" / "debug" / "htmlninefox-shell.exe"
WINDOW_TITLE_MARK = "Html九尾狐"

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32


def find_window() -> int | None:
    import win32gui  # pywin32；取证脚本本地依赖

    found = []

    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if WINDOW_TITLE_MARK in title:
                found.append(hwnd)
        return True

    win32gui.EnumWindows(callback, None)
    return found[0] if found else None


def capture_window(hwnd: int, target: Path) -> None:
    import win32gui
    import win32ui
    from PIL import Image

    left, top, right, bottom = win32gui.GetClientRect(hwnd)
    width, height = right - left, bottom - top
    hwnd_dc = win32gui.GetWindowDC(hwnd)
    mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
    save_dc = mfc_dc.CreateCompatibleDC()
    bitmap = win32ui.CreateBitmap()
    bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
    save_dc.SelectObject(bitmap)
    # PW_RENDERFULLCONTENT：DX 合成窗口（WebView2）也能抓到
    user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 2)
    info = bitmap.GetInfo()
    raw = bitmap.GetBitmapBits(True)
    Image.frombuffer("RGB", (info["bmWidth"], info["bmHeight"]), raw, "raw", "BGRX", 0, 1)\
        .save(target)
    win32gui.DeleteObject(bitmap.GetHandle())
    save_dc.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwnd_dc)


def capture_shell() -> None:
    if not SHELL_EXE.is_file():
        raise SystemExit(f"壳二进制不存在：{SHELL_EXE}——先 cargo build")
    shell = subprocess.Popen([str(SHELL_EXE)], cwd=ROOT)
    try:
        hwnd = None
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            hwnd = find_window()
            if hwnd:
                break
            time.sleep(0.4)
        if not hwnd:
            raise SystemExit("30 秒内未发现壳窗口")
        time.sleep(1.0)   # 加载页已渲染
        capture_window(hwnd, OUT / "evidence-shell-loader.png")
        print("shot: evidence-shell-loader.png")

        # sidecar 冷启动 + 健康轮询 + 导航：给足时间后拍工作台
        time.sleep(14)
        capture_window(hwnd, OUT / "evidence-shell-workbench.png")
        print("shot: evidence-shell-workbench.png")
    finally:
        subprocess.run(["taskkill", "/PID", str(shell.pid), "/T", "/F"],
                       capture_output=True)
        time.sleep(1.5)   # 壳的退出链回收 sidecar


def capture_style_recommend() -> None:
    import tempfile

    from playwright.sync_api import sync_playwright

    from tests.conftest import WorkbenchServer
    from tests.test_server_project_api import request as api_request

    with WorkbenchServer(Path(tempfile.mkdtemp())) as server:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1180, "height": 1000})
            page.goto(server.base_url + "/")
            page.wait_for_function("typeof window.FoxActions === 'object'")
            page.click("#btn-create")   # 打开「输入需求与素材」面板
            page.wait_for_selector("#creation-prompt", state="visible",
                                   timeout=15000)
            page.fill("#creation-prompt",
                      "做一个面向开发者的性能监控看板，深色，强调数据密度")
            page.click("#creation-analyze")
            page.wait_for_function(
                """() => document.querySelector('#creation-analysis')?.innerHTML
                  .includes('🎬')""", timeout=30000)
            page.wait_for_timeout(400)
            page.locator("#create-modal .flow-dialog").screenshot(
                path=OUT / "evidence-style-recommend.png")
            print("shot: evidence-style-recommend.png")
            browser.close()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    capture_shell()
    capture_style_recommend()
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
