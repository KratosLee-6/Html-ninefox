#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
APP_VERSION="__HTMLNINEFOX_VERSION__"
PREFIX=${HTMLNINEFOX_PREFIX:-"$HOME/.local/share/htmlninefox"}
BIN_DIR=${HTMLNINEFOX_BIN_DIR:-"$HOME/.local/bin"}
DESKTOP_DIR=${XDG_DATA_HOME:-"$HOME/.local/share"}/applications
PACKAGE_DIR="$PREFIX/package"
VENV_DIR="$PREFIX/venv"

if ! command -v python3 >/dev/null 2>&1; then
  echo "[错误] 需要 Python 3.10 或更高版本。" >&2
  exit 1
fi
python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' || {
  echo "[错误] 当前 Python 低于 3.10。" >&2
  exit 1
}

mkdir -p "$PREFIX" "$BIN_DIR" "$DESKTOP_DIR"
rm -rf "$PACKAGE_DIR"
mkdir -p "$PACKAGE_DIR"
cp "$SCRIPT_DIR/htmlninefox-$APP_VERSION-py3-none-any.whl" "$PACKAGE_DIR/"
cp "$SCRIPT_DIR/icon.svg" "$PACKAGE_DIR/"
if [ -d "$SCRIPT_DIR/wheels" ]; then cp -R "$SCRIPT_DIR/wheels" "$PACKAGE_DIR/"; fi

if [ ! -x "$VENV_DIR/bin/python" ]; then
  echo "[1/3] 创建独立 Python 环境..."
  python3 -m venv "$VENV_DIR" || {
    echo "[错误] 无法创建 venv。Debian/Ubuntu 请安装 python3-venv。" >&2
    exit 1
  }
fi

echo "[2/3] 安装 Html九尾狐 $APP_VERSION..."
if [ -d "$PACKAGE_DIR/wheels" ] && find "$PACKAGE_DIR/wheels" -type f -name '*.whl' | grep -q .; then
  "$VENV_DIR/bin/python" -m pip install --no-index --find-links "$PACKAGE_DIR/wheels" --upgrade "$PACKAGE_DIR/htmlninefox-$APP_VERSION-py3-none-any.whl"
else
  "$VENV_DIR/bin/python" -m pip install --upgrade "$PACKAGE_DIR/htmlninefox-$APP_VERSION-py3-none-any.whl"
fi

cat > "$BIN_DIR/htmlninefox-app" <<EOF
#!/bin/sh
exec "$VENV_DIR/bin/htmlninefox" app "$@"
EOF
chmod +x "$BIN_DIR/htmlninefox-app"
ln -sf "$VENV_DIR/bin/htmlninefox" "$BIN_DIR/htmlninefox"

cat > "$DESKTOP_DIR/htmlninefox.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Html九尾狐
Comment=Pixel Garden HTML 创作工作台
Exec=$BIN_DIR/htmlninefox-app
Icon=$PACKAGE_DIR/icon.svg
Terminal=true
Categories=Development;Graphics;Office;
StartupNotify=true
EOF
chmod 644 "$DESKTOP_DIR/htmlninefox.desktop"
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true

echo "[3/3] 安装完成。"
echo "命令：$BIN_DIR/htmlninefox-app"
echo "地址：http://127.0.0.1:8620"
if [ "${1:-}" != "--no-launch" ]; then exec "$BIN_DIR/htmlninefox-app"; fi
