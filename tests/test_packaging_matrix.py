"""打包矩阵的门禁：每个平台的包都必须「构建、可装、可启动」三件事都有主。

背景：打包矩阵此前有两个平台级缺口——macOS 只有 Apple Silicon 包（Intel
用户无包可下），Linux 没有 .deb（只有 tar.gz 与 .run 自解压）。补齐的
macos-intel job、build_deb.py 与安装烟囱步骤由本文件锁死；关键是**验证器
本身也要被验证**：verify_unix_portable.py 若某天把内容断言悄悄放水，
正例（真启动完整产物必须通过）不会变红，负例（不完整产物必须失败）才会。

本文件三个执行级门禁在任何平台都能跑：
  - .deb 目录树真实构建（--stage-only）并逐项断言；
  - verify_unix_portable 对真实产物（python -m htmlninefox.desktop）全链通过；
  - verify_unix_portable 对**缺内容标记的假产物**必须拒绝——这是对验证器
    自己的变异检验， stub 服务器在测试进程内起在 8620。
结构门禁锁 workflow 的矩阵形状（macos-intel 在 Intel runner、.deb 进字节级
回读清单、publish 前置齐六个构建 job）。
"""
from __future__ import annotations

import io
import json
import re
import subprocess
import sys
import tarfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

WORKFLOW = ROOT / ".github" / "workflows" / "build-release-packages.yml"
WORKFLOW_TEXT = WORKFLOW.read_text(encoding="utf-8")


# ---------------------------------------------------------------- .deb 目录树

def _build_wheel_if_missing() -> Path:
    version = _pyproject_version()
    wheel = ROOT / "dist" / f"htmlninefox-{version}-py3-none-any.whl"
    if not wheel.exists():
        subprocess.run(
            [sys.executable, "-m", "pip", "wheel", str(ROOT), "--no-deps",
             "--wheel-dir", str(ROOT / "dist")],
            check=True, capture_output=True)
    assert wheel.exists()
    return wheel


def _pyproject_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    return re.search(r'^version = "([^"]+)"', text, re.MULTILINE).group(1)


def _stage_deb() -> Path:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "build_deb", ROOT / "packaging" / "linux" / "build_deb.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _build_wheel_if_missing()
    staging = ROOT / "build" / "linux-deb" / \
        f"htmlninefox_{_pyproject_version()}_all"
    return mod.stage_deb(_pyproject_version(), staging)


def test_deb_stage_tree_is_complete():
    staging = _stage_deb()
    control = (staging / "DEBIAN" / "control").read_text(encoding="utf-8")
    assert re.search(r"^Package: htmlninefox$", control, re.M), "包名缺失"
    assert f"Version: {_pyproject_version()}" in control, "版本与 pyproject 脱钩"
    assert re.search(r"^Architecture: all$", control, re.M)
    # postinst 要用 venv 构建环境；缺这条声明时 apt 会装出一个点不亮的包
    assert "python3-venv" in control, "Depends 缺 python3-venv——postinst 必败"
    if sys.platform != "win32":
        # 可执行位在 NTFS 上无法表示（os.chmod 只保留只读位）；POSIX 上直接
        # 断言。Windows 本机的端到端证明由 CI 的 .deb 安装烟囱承担——
        # postinst 不可执行时 dpkg 安装当场失败，烟囱步骤会红。
        for name in ("postinst", "postrm", "htmlninefox-app", "htmlninefox"):
            candidates = [staging / "DEBIAN" / name, staging / "usr" / "bin" / name]
            script = next((p for p in candidates if p.exists()), None)
            assert script is not None, f"{name} 不在目录树里"
            assert script.stat().st_mode & 0o111, \
                f"{name} 没有可执行位——dpkg 会跳过它"
    postrm = (staging / "DEBIAN" / "postrm").read_text(encoding="utf-8")
    assert '"upgrade"' in postrm, "postrm 缺升级守卫——升级会白白拆掉 venv"
    opt = staging / "opt" / "htmlninefox"
    shipped = list(opt.glob("htmlninefox-*-py3-none-any.whl"))
    assert len(shipped) == 1, f"包里应有且只有一个应用 wheel：{shipped}"
    assert list((opt / "wheels").glob("*.whl")), "离线 wheelhouse 是空的"
    for name in ("htmlninefox-app", "htmlninefox"):
        wrapper = staging / "usr" / "bin" / name
        assert wrapper.exists(), f"{name} 启动器缺失（可执行位见上方 POSIX 分支）"
    desktop = (staging / "usr" / "share" / "applications" / "htmlninefox.desktop"
               ).read_text(encoding="utf-8")
    assert "Exec=/usr/bin/htmlninefox-app" in desktop, "桌面入口与启动器脱钩"


# ------------------------------------------------- 验证器正例（真实产物通过）

def test_unix_verifier_accepts_a_real_product():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "packaging" / "verify_unix_portable.py"),
         "--entry", sys.executable,
         "--arg=-m", "--arg=htmlninefox.desktop", "--arg=--no-browser",
         "--expect-distribution", "python-app"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=180)
    assert proc.returncode == 0, (
        f"verify_unix_portable 拒绝了真实产物：\n{proc.stdout[-1500:]}")


# --------------------------------- 验证器负例（缺内容标记的产物必须被拒绝）

class _IncompleteProduct(BaseHTTPRequestHandler):
    """一个健康、首页、静态资源全对、**唯独缺内容标记**的假产物。

    verify_unix_portable 的价值全在内容断言上；这个 handler 就是它的变异
    试验台：验证器放水（比如哪天有人把 verify_content 改成永远通过），
    本条门禁立即变红。"""

    def log_message(self, *args):  # 静默
        pass

    def _send(self, body: bytes, ctype: str = "text/html") -> None:
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        route = self.path
        if route == "/api/health":
            self._send(json.dumps({
                "ok": True, "version": _pyproject_version(),
                "distribution": "python-app",
            }).encode(), "application/json")
        elif route == "/":
            self._send(("<html><body>Html九尾狐 · 像素花园工作台 "
                        "<span style='color:var(--on-accent)'>x</span></body>"
                        "</html>").encode())
        elif route == "/workbench-system.css":
            self._send((":root{--fs-base:14px;--fw-medium:500;"
                        "--space-2:8px}".encode() * 20), "text/css")
        elif route == "/fox-core.js":
            # 缺 window.FoxState——v0.7.5（C7 状态声明）引入的标记
            self._send(b"window.FoxActions = {};\n" * 50,
                       "application/javascript")
        elif route == "/lifecycle-slides.js":
            self._send(b"expected_revision: 0\n" * 20, "application/javascript")
        elif route == "/lifecycle-intake.js":
            self._send(b"function fetchBatch(){}\n" * 20,
                       "application/javascript")
        elif route in ("/motion-lab", "/classic", "/sw.js", "/icon.svg"):
            self._send(b"x" * 2048)
        else:
            self.send_response(404)
            self.end_headers()


@pytest.fixture()
def incomplete_product():
    httpd = ThreadingHTTPServer(("127.0.0.1", 8620), _IncompleteProduct)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield httpd
    httpd.shutdown()
    httpd.server_close()


def test_unix_verifier_rejects_a_product_missing_content_markers(
        incomplete_product):
    # 入口指向一个立即退出的假命令：验证器应先被 8620 上已在监听的
    # 假产物喂饱健康检查，随后死在内容断言上，退出码非零。
    if sys.platform == "win32":
        entry = "cmd"
        args = ["--arg=/c", "--arg=exit"]
    else:
        entry = "true"
        args = []
    proc = subprocess.run(
        [sys.executable, str(ROOT / "packaging" / "verify_unix_portable.py"),
         "--entry", entry, *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=180)
    assert proc.returncode != 0, (
        "verify_unix_portable 放水了：一个缺 window.FoxState 标记的产物"
        "通过了验证——内容断言已失效，陈旧产物将一路走进 Release")
    assert "FoxState" in (proc.stdout + proc.stderr), (
        f"失败原因不是内容断言：\n{proc.stdout[-800:]}")


# ------------------------------------------------------- workflow 矩阵形状

def test_workflow_covers_the_full_packaging_matrix():
    assert re.search(r"macos-intel:\s*$", WORKFLOW_TEXT, re.M), \
        "workflow 缺 macos-intel job——Intel 用户无包可下"
    assert "runs-on: macos-13" in WORKFLOW_TEXT, \
        "macos-intel 必须跑在 Intel runner（PyInstaller 不能交叉编译）"
    assert 'name: htmlninefox-macos-intel' in WORKFLOW_TEXT, \
        "Intel 包没有自己的 artifact 名"
    assert 'needs: [windows, linux, macos, macos-intel, docker, package-payload]' \
        in WORKFLOW_TEXT, "publish-draft 未等待 macos-intel——Intel 包可能缺席发布"
    assert '--asset "*.deb"' in WORKFLOW_TEXT, \
        ".deb 未进字节级回读清单——坏包可以在验证眼皮下溜进发布"
    assert "packaging/linux/build_deb.py" in WORKFLOW_TEXT, \
        "linux job 不再构建 .deb"
    assert "verify_unix_portable.py --entry htmlninefox-app" in WORKFLOW_TEXT, \
        ".deb 装完没有真实启动验证"
    assert WORKFLOW_TEXT.count("--expect-distribution macos-portable") == 2, \
        "arm64 与 x64 两个 macOS 包都必须被真实启动验证"


def test_deb_smoke_flag_matches_the_cli_entrypoint():
    """v0.7.6 首次构建的真实缺陷：烟囱把 desktop 入口的 --no-browser 传给了
    click 入口 `htmlninefox app`（它的旗子是 --no-open-browser），产物装好
    之后起不来——所有单元测试全绿，只有真启动能暴露。本门禁把「workflow
    传给 .deb 冒烟的旗子」与「CLI 入口实际接受的旗子」在 CI 之外就锁死：
    从 workflow 里抽出旗子，去问 `python -m htmlninefox app --help`。"""
    smoke = re.search(
        r"verify_unix_portable\.py --entry htmlninefox-app \\\n\s+(--arg=[^\s\\]+)",
        WORKFLOW_TEXT)
    assert smoke, "找不到 .deb 烟囱的启动旗子"
    flag = smoke.group(1)
    help_text = subprocess.run(
        [sys.executable, "-m", "htmlninefox", "app", "--help"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=60)
    assert help_text.returncode == 0, f"cli app --help 失败：{help_text.stderr[-300:]}"
    assert flag.replace("--arg=", "") in help_text.stdout, (
        f"workflow 给 .deb 烟囱传的旗子 {flag} 不被 `htmlninefox app` 接受"
        f"——入口失配，产物装好了也起不来（这正是 v0.7.6 首次构建的失败）。\n"
        f"app --help 实际接受：\n{help_text.stdout}")


# ----------------------------------------------------- .deb 字节回读读得动

def test_release_asset_reader_understands_deb(tmp_path, monkeypatch):
    """check_archive / check_static_payload 的 .deb 分支：手工构造一个
    结构完整的 ar 归档（debian-binary + control.tar.gz + data.tar.xz，
    内含带前端的应用 wheel），回读逻辑必须能声明它完整、能找到前端；
    抽掉 data.tar 后必须报缺失。"""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "verify_release_assets", ROOT / "scripts" / "verify_release_assets.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    version = _pyproject_version()
    wheel = _build_wheel_if_missing()

    def _member(name: str, data: bytes, out: io.BytesIO) -> None:
        header = name.ljust(16).encode("ascii")
        header += b"0".ljust(12) + b"0".ljust(6) + b"0".ljust(6)
        header += b"644".ljust(8) + str(len(data)).encode("ascii").ljust(10)
        header += b"`\n"
        out.write(header + data)
        if len(data) % 2:
            out.write(b"\n")

    def _build_deb(dest: Path, with_data: bool = True) -> None:
        import io as _io
        ar = _io.BytesIO()
        ar.write(b"!<arch>\n")
        _member("debian-binary", b"2.0\n", ar)
        control = _io.BytesIO()
        with tarfile.open(fileobj=control, mode="w") as t:
            info = tarfile.TarInfo("./control")
            payload = f"Package: htmlninefox\nVersion: {version}\n".encode()
            info.size = len(payload)
            t.addfile(info, _io.BytesIO(payload))
        _member("control.tar.gz", control.getvalue(), ar)
        if with_data:
            data_tar = _io.BytesIO()
            with tarfile.open(fileobj=data_tar, mode="w:xz") as t:
                wheel_bytes = wheel.read_bytes()
                info = tarfile.TarInfo(
                    f"./opt/htmlninefox/htmlninefox-{version}-py3-none-any.whl")
                info.size = len(wheel_bytes)
                t.addfile(info, _io.BytesIO(wheel_bytes))
            _member("data.tar.xz", data_tar.getvalue(), ar)
        dest.write_bytes(ar.getvalue())

    good = tmp_path / "good.deb"
    _build_deb(good)
    assert mod.check_archive(good) == [], \
        f"结构完整的 deb 被回读写爆：{mod.check_archive(good)}"

    # repo/tag 只被 gh() 用；测试里 monkeypatch 掉清单来源
    monkeypatch.setattr(mod, "gh", lambda *a, **k: json.dumps([
        {"name": "index.html", "type": "file"},
        {"name": "workbench-system.css", "type": "file"},
    ]))
    problems = mod.check_static_payload("repo", "tag", good)
    assert problems == [], f"deb 里的前端没被找到：{problems}"

    bad = tmp_path / "bad.deb"
    _build_deb(bad, with_data=False)
    problems = mod.check_archive(bad)
    assert any("data.tar" in p for p in problems), \
        f"缺 data.tar 的 deb 未被识别：{problems}"
