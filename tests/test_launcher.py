from __future__ import annotations

import socket
from pathlib import Path

from htmlninefox import launcher


def test_find_available_port_skips_busy_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as busy:
        busy.bind(("127.0.0.1", 0))
        busy.listen(1)
        occupied = busy.getsockname()[1]
        selected = launcher.find_available_port("127.0.0.1", occupied, attempts=4)
        assert selected != occupied
        assert occupied < selected <= occupied + 3


def test_find_available_port_supports_ephemeral():
    assert launcher.find_available_port("127.0.0.1", 0) > 0


def test_configure_portable_data(monkeypatch, tmp_path):
    root = tmp_path / "portable data"
    configured = launcher.configure_portable_data(root)
    assert configured == root.resolve()
    assert root.is_dir()
    assert Path.home() == root.resolve()


def test_wait_and_open_browser_times_out_without_server():
    opened = []
    result = launcher.wait_and_open_browser(
        "http://127.0.0.1:1", timeout=0.01, opener=opened.append
    )
    assert result is False
    assert opened == []
