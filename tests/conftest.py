"""Shared pytest adapters for the Html九尾狐 workbench HTTP seam."""

from __future__ import annotations

import threading
from pathlib import Path
from types import TracebackType
from typing import Iterator

import pytest

from htmlninefox.server import app as server_app


class WorkbenchServer:
    """Context-managed workbench server with isolated project storage."""

    def __init__(self, output_root: Path) -> None:
        self.output_root = output_root
        self.base_url = ""
        self._server = None
        self._thread: threading.Thread | None = None
        self._previous_output_root: Path | None = None

    def __enter__(self) -> WorkbenchServer:
        if self._server is not None:
            raise RuntimeError("workbench test server is already running")
        self._previous_output_root = server_app._OUTPUT_ROOT
        server_app._OUTPUT_ROOT = self.output_root
        try:
            self._server = server_app.ThreadingHTTPServer(
                ("127.0.0.1", 0),
                server_app._Handler,
            )
            self._thread = threading.Thread(
                target=self._server.serve_forever,
                name="htmlninefox-test-http",
                daemon=True,
            )
            self._thread.start()
            self.base_url = f"http://127.0.0.1:{self._server.server_port}"
            return self
        except BaseException:
            self.close()
            raise

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        server = self._server
        thread = self._thread
        self._server = None
        self._thread = None
        try:
            if server is not None:
                if thread is not None and thread.is_alive():
                    server.shutdown()
                server.server_close()
                if thread is not None:
                    thread.join(timeout=3)
                    if thread.is_alive():
                        raise RuntimeError("workbench test server thread did not stop")
        finally:
            if self._previous_output_root is not None:
                server_app._OUTPUT_ROOT = self._previous_output_root
            self._previous_output_root = None
            self.base_url = ""


@pytest.fixture
def workbench_server(tmp_path: Path) -> Iterator[WorkbenchServer]:
    """Provide an isolated server adapter; tests choose the active lifetime."""

    server = WorkbenchServer(tmp_path)
    try:
        yield server
    finally:
        server.close()
