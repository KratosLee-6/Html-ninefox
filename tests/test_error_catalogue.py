"""C5 门禁：ExportError 的 HTTP 状态只允许声明一处（raise 处）。

审计（AUDIT-ARCHITECTURE-20260929 C5）：状态码曾有三处硬编码——
`StoreError` 焊进持久化错误类型、exporting.py 各自硬写、app.py 再用
18 条硬编码表推回来；新增错误码忘加表就静默变 500。

v0.7.2 的修复：ExportError 自带 `status`（raise 处声明），底层
StoreError 的状态在 `StudioApplication._export_error` 转换时随行，
`_Handler._export_store_error` 直接消费 `error.status`。

门禁锁三件事：

  1. 转换行为：底层状态随行、意外错误回落 500；
  2. ExportError 默认 400（与历史行为一致）；
  3. 结构：app.py 的 export 方法体不再包含状态表/静默 500 兜底。
     （`_restore_store_error` / `_feedback_store_error` 的表是另一套
     码表，不在 C5 范围内。）
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from htmlninefox.application import ExportError, StudioApplication  # noqa: E402
from htmlninefox.exporting import StoreError  # noqa: E402
from htmlninefox.server import app as server_app  # noqa: E402


def _store_error(code: str, status: int) -> StoreError:
    try:
        raise StoreError(code, "页码超出范围", status)
    except StoreError as error:
        return error


def test_export_error_carries_declared_status():
    err = ExportError("export_page_limit", "太多页", status=413)
    assert err.status == 413


def test_export_error_defaults_to_400():
    err = ExportError("export_format_unsupported", "格式不支持")
    assert err.status == 400


def test_conversion_carries_status_from_store_error():
    """底层 StoreError（exporting.py 直接 raise）的状态必须在转换时随行。

    驱动真实的 StudioApplication._export_error 转换：StoreError 的
    status=413 转成 ExportError 后不得丢失（丢了就会落进 adapter 表的
    500 缺省——C5 的静默 500 通道回归）。
    """
    converted = StudioApplication._export_error(
        _store_error("export_page_limit", 413))
    assert converted.code == "export_page_limit"
    assert converted.status == 413


def test_conversion_fallback_is_500_for_unknown_errors():
    converted = StudioApplication._export_error(RuntimeError("boom"))
    assert converted.code == "export_failed"
    assert converted.status == 500


def test_export_store_error_consumes_error_status():
    handler = object.__new__(server_app._Handler)
    result = handler._export_store_error(
        ExportError("export_page_limit", "太多页", status=413))
    assert result.status == 413
    assert result.code == "export_page_limit"


def test_app_export_path_has_no_status_table():
    """C5 结构断言：export 方法体不得再有状态表或静默 500 兜底。"""
    source = (ROOT / "htmlninefox" / "server" / "app.py").read_text(encoding="utf-8")
    start = source.index("def _export_store_error")
    body = source[start:]
    body = body[:body.index("\n    def ")] if "\n    def " in body else body
    assert "statuses" not in body, "export 转换里又出现了硬编码状态表（C5 回归）"
