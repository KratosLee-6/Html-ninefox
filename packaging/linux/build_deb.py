"""Build the Debian package: HtmlNineFox-Linux-amd64-<version>.deb.

与 install.sh 同一安装模型（/opt 下的离线 wheel + 安装时构建 venv），但交给
dpkg 管理：升级/卸载有语义，桌面入口与启动器在包里而不是安装脚本里。
产物以 -Zxz 压缩——scripts/verify_release_assets.py 用标准库 tarfile 读
data.tar.xz 做字节级回读，zstd 是标准库读不了的。

--stage-only 只构建目录树不调 dpkg-deb（任何平台可用）：目录树逻辑由
tests/test_packaging_matrix.py 在本机锁死，dpkg-deb 与安装烟囱在 CI 的
ubuntu runner 上真实执行。
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RELEASE = ROOT / "release"
BUILD = ROOT / "build" / "linux-deb"
TEMPLATES = ROOT / "packaging" / "linux"
WHEELHOUSE = TEMPLATES / "wheels"


def version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    return re.search(r'^version = "([^"]+)"', text, re.MULTILINE).group(1)


def _control(release_version: str) -> str:
    # Depends 里的 python3-venv 是硬性声明：postinst 要用 venv，缺它
    # apt install 会如实失败，而不是装完一个点不亮的包。
    return f"""Package: htmlninefox
Version: {release_version}
Section: devel
Priority: optional
Architecture: all
Depends: python3 (>= 3.10), python3-venv
Maintainer: KratosLee <kratoslee@aliyun.com>
Homepage: https://github.com/KratosLee-6/Html-ninefox
Description: Html九尾狐 · 本地优先的可视化 HTML 创作工作台
 贴入需求或吸收既有页面，生成可直接交付的 HTML / PPTX / PNG / PDF 产物。
 安装到 /opt/htmlninefox，安装时构建独立 venv（离线 wheels 兜底，不需联网）；
 数据与产物保存在用户目录。
"""


def _postinst(release_version: str) -> str:
    return f"""#!/bin/sh
set -eu

VENV_DIR=/opt/htmlninefox/venv
WHEEL=/opt/htmlninefox/htmlninefox-{release_version}-py3-none-any.whl

if [ ! -x "$VENV_DIR/bin/python" ]; then
  echo "[htmlninefox] 构建独立 Python 环境..."
  python3 -m venv "$VENV_DIR"
fi

echo "[htmlninefox] 安装 Html九尾狐 {release_version}..."
if [ -d /opt/htmlninefox/wheels ] && find /opt/htmlninefox/wheels -type f -name '*.whl' | grep -q .; then
  "$VENV_DIR/bin/python" -m pip install --no-index \\
    --find-links /opt/htmlninefox/wheels --upgrade "$WHEEL"
else
  "$VENV_DIR/bin/python" -m pip install --upgrade "$WHEEL"
fi

command -v update-desktop-database >/dev/null 2>&1 \\
  && update-desktop-database /usr/share/applications >/dev/null 2>&1 || true

echo "[htmlninefox] 完成：命令 /usr/bin/htmlninefox-app，地址 http://127.0.0.1:8620"
"""


def _postrm() -> str:
    return """#!/bin/sh
set -eu

# 升级路径（postrm upgrade <new>）不能拆 venv：新版本 postinst 还要复用它。
[ "${1:-}" = "upgrade" ] && exit 0

rm -rf /opt/htmlninefox/venv
command -v update-desktop-database >/dev/null 2>&1 \\
  && update-desktop-database /usr/share/applications >/dev/null 2>&1 || true
"""


def _launcher(release_version: str) -> str:
    return """#!/bin/sh
exec /opt/htmlninefox/venv/bin/htmlninefox app "$@"
"""


def _cli(release_version: str) -> str:
    return """#!/bin/sh
exec /opt/htmlninefox/venv/bin/htmlninefox "$@"
"""


def _desktop() -> str:
    return """[Desktop Entry]
Type=Application
Name=Html九尾狐
Comment=Pixel Garden HTML 创作工作台
Exec=/usr/bin/htmlninefox-app
Icon=/opt/htmlninefox/icon.svg
Terminal=true
Categories=Development;Graphics;Office;
StartupNotify=true
"""


def stage_deb(release_version: str, staging: Path) -> Path:
    """构建包目录树。纯文件操作，任何平台可运行（测试在 Windows 上也要能跑）。"""
    if staging.exists():
        shutil.rmtree(staging)
    deb = staging / "DEBIAN"
    opt = staging / "opt" / "htmlninefox"
    bin_dir = staging / "usr" / "bin"
    apps = staging / "usr" / "share" / "applications"
    for directory in (deb, opt, bin_dir, apps):
        directory.mkdir(parents=True, exist_ok=True)

    wheel = ROOT / "dist" / f"htmlninefox-{release_version}-py3-none-any.whl"
    if not wheel.exists():
        raise SystemExit(f"missing wheel: {wheel}")
    shutil.copy2(wheel, opt / wheel.name)
    shutil.copy2(ROOT / "htmlninefox" / "server" / "static" / "icon.svg",
                 opt / "icon.svg")
    if WHEELHOUSE.exists():
        shutil.copytree(WHEELHOUSE, opt / "wheels")

    (deb / "control").write_text(_control(release_version), encoding="utf-8",
                                 newline="\n")
    (deb / "postinst").write_text(_postinst(release_version), encoding="utf-8",
                                  newline="\n")
    (deb / "postrm").write_text(_postrm(), encoding="utf-8", newline="\n")
    (bin_dir / "htmlninefox-app").write_text(_launcher(release_version),
                                             encoding="utf-8", newline="\n")
    (bin_dir / "htmlninefox").write_text(_cli(release_version),
                                         encoding="utf-8", newline="\n")
    (apps / "htmlninefox.desktop").write_text(_desktop(), encoding="utf-8",
                                              newline="\n")
    for name in ("postinst", "postrm"):
        os.chmod(deb / name, 0o755)
    for name in ("htmlninefox-app", "htmlninefox"):
        os.chmod(bin_dir / name, 0o755)
    return staging


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage-only", action="store_true",
                    help="只构建目录树，不调 dpkg-deb（任意平台可用，供测试）")
    args = ap.parse_args()
    release_version = version()

    staging = stage_deb(release_version, BUILD / f"htmlninefox_{release_version}_all")
    if args.stage_only:
        print(f"staged={staging}")
        return 0

    RELEASE.mkdir(parents=True, exist_ok=True)
    deb = RELEASE / f"HtmlNineFox-Linux-amd64-{release_version}.deb"
    if deb.exists():
        deb.unlink()
    # -Zxz：data.tar.xz 是标准库 tarfile 可读的格式，发布回读依赖这一点；
    # --root-owner-group：构建机上没有 root 也能产出 root:root 归属。
    subprocess.run(
        ["dpkg-deb", "--root-owner-group", "-Zxz", "--build",
         str(staging), str(deb)],
        check=True,
    )
    digest = hashlib.sha256(deb.read_bytes()).hexdigest().upper()
    (deb.with_suffix(deb.suffix + ".sha256.txt")).write_text(
        f"{digest}  {deb.name}\n", encoding="ascii")
    print(f"deb={deb} sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
