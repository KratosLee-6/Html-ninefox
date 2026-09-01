"""Cross-platform application launcher for Html九尾狐."""

from __future__ import annotations

import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path
from typing import Callable


def find_available_port(host: str, preferred: int, attempts: int = 20) -> int:
    """Return the preferred port or the next available TCP port."""
    candidates = [preferred] if preferred == 0 else range(preferred, preferred + attempts)
    for candidate in candidates:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind((host, candidate))
            except OSError:
                continue
            return int(probe.getsockname()[1])
    raise RuntimeError(f"{host}:{preferred} 起连续 {attempts} 个端口均不可用")


def wait_and_open_browser(
    url: str,
    timeout: float = 20.0,
    opener: Callable[[str], object] = webbrowser.open,
) -> bool:
    """Wait for the local health endpoint, then open the browser once."""
    health_url = url.rstrip("/") + "/api/health"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(health_url, timeout=1.0) as response:
                if response.status == 200:
                    opener(url)
                    return True
        except OSError:
            time.sleep(0.15)
    return False


def configure_portable_data(root: str | Path | None) -> Path | None:
    """Route user state and generated files beside a portable bundle."""
    if root is None:
        return None
    data_root = Path(root).expanduser().resolve()
    data_root.mkdir(parents=True, exist_ok=True)
    os.environ["HTMLNINEFOX_HOME"] = str(data_root)
    os.environ["HOME"] = str(data_root)
    if os.name == "nt":
        os.environ["USERPROFILE"] = str(data_root)
    return data_root


def launch_workspace(
    host: str = "127.0.0.1",
    port: int = 8620,
    output: str | None = None,
    *,
    open_browser: bool = True,
    fallback_port: bool = True,
    portable_root: str | Path | None = None,
    distribution: str = "python",
) -> None:
    """Start the Web/PWA workspace with optional browser and portable data."""
    data_root = configure_portable_data(portable_root)
    selected_port = find_available_port(host, port) if fallback_port else port
    if data_root is not None and output is None:
        output = str(data_root / "output")
    os.environ["HTMLNINEFOX_DISTRIBUTION"] = distribution
    url_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    url = f"http://{url_host}:{selected_port}"
    if open_browser:
        threading.Thread(target=wait_and_open_browser, args=(url,), daemon=True).start()
    from .server import app

    app.serve(host, selected_port, output)


def frozen_portable_root() -> Path | None:
    """Return the writable data folder for a frozen portable executable."""
    if not getattr(sys, "frozen", False):
        return None
    return Path(sys.executable).resolve().parent / "user-data"
