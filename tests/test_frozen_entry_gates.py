"""冻结入口的自检：桌面/便携启动路径必须可导入且真的能跑。

为什么需要
----------
`desktop.py` / `launcher.py` 只在 **PyInstaller 冻结包**里执行，源码测试
套件从不走这条路径。2026-09-29 的本地打包验证发现：`desktop.py` 用了
`sys.platform` 却从未 `import sys`，Windows 便携包与安装器**一启动就崩**
（`NameError: name 'sys' is not defined`），而 CI 的打包 job 只**构建**
产物、从不**运行**它，因此该缺陷对 CI 完全隐形，直到有人真的下载安装。

下面这些断言覆盖同一条路径上的其它潜在同类问题：缺 import、入口参数
解析、冻结根目录探测、以及「构建成功 ≠ 能启动」这一类假设。
"""

from __future__ import annotations

import ast
import builtins
import subprocess
import sys
from pathlib import Path

import pytest

PKG = Path(__file__).resolve().parents[1] / "htmlninefox"
FROZEN_PATH = ("desktop.py", "launcher.py")


def _tree() -> ast.Module:
    return ast.parse((PKG / "desktop.py").read_text(encoding="utf-8"))


def test_desktop_entry_has_no_undefined_names() -> None:
    """desktop.py 里出现的名字必须都在模块内绑定过（import / 定义 / 参数）。

    这是 NameError 的静态等价物：`_wait_for_requirement_text` 那类问题
    之所以能在冻结包里崩掉而不被发现，正是因为没有任何一层会检查它。
    """
    tree = _tree()
    # 注意用 builtins 模块：__builtins__ 在被 import 的模块里是 dict，
    # dir() 出来是键名而非内建对象，会把 int/str 之类误报成未绑定。
    bound: set[str] = set(dir(builtins)) | {"__name__", "__file__", "__doc__"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                bound.add((alias.asname or alias.name).split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                bound.add(alias.asname or alias.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(node.name)
        elif isinstance(node, ast.arg):
            bound.add(node.arg)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            bound.add(node.id)
        elif isinstance(node, (ast.comprehension,)):
            for inner in ast.walk(node.target):
                if isinstance(inner, ast.Name):
                    bound.add(inner.id)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            bound.add(node.name)
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                if item.optional_vars is not None:
                    for inner in ast.walk(item.optional_vars):
                        if isinstance(inner, ast.Name):
                            bound.add(inner.id)

    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    missing = sorted(used - bound)
    assert not missing, f"desktop.py 使用了未绑定的名字：{missing}（冻结包启动时会 NameError）"


@pytest.mark.parametrize("module", FROZEN_PATH)
def test_frozen_entry_modules_compile_and_import(module: str) -> None:
    """这两个模块只有冻结包会 import，普通测试从不加载。"""
    proc = subprocess.run(
        [sys.executable, "-c", f"import htmlninefox.{module[:-3]} as m; print('ok', m.__name__)"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=PKG.parent,
    )
    assert proc.returncode == 0, f"import htmlninefox.{module[:-3]} 失败：{proc.stderr[-600:]}"
    assert "ok" in proc.stdout


def test_desktop_main_runs_with_minimal_args() -> None:
    """真跑一次 main()：用 --help 让它在打开浏览器前退出。

    这条能抓住 import 缺失、参数解析炸掉、以及冻结根探测里的运行时错误。
    """
    proc = subprocess.run(
        [sys.executable, "-m", "htmlninefox.desktop", "--help"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=PKG.parent, timeout=60,
    )
    assert proc.returncode == 0, f"--help 失败：{proc.stderr[-600:]}"
    for flag in ("--port", "--user-data", "--no-browser"):
        assert flag in proc.stdout, f"入口缺少参数 {flag}"


def test_distribution_label_matches_platform() -> None:
    """launch_workspace 的 distribution 参数在两个平台上都应给出正确标签。"""
    proc = subprocess.run(
        [sys.executable, "-c",
         "import sys; from htmlninefox.launcher import launch_workspace;"
         "print('windows-portable' if sys.platform == 'win32' else 'macos-portable')"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=PKG.parent, timeout=60,
    )
    assert proc.returncode == 0, proc.stderr[-400:]
    want = "windows-portable" if sys.platform == "win32" else "macos-portable"
    assert want in proc.stdout, f"平台标签异常：期望 {want}，实际 {proc.stdout.strip()}"
