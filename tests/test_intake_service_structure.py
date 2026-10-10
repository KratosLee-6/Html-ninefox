"""P1-7 结构门禁：intake 编排只允许住在 IntakeService。

审计（AUDIT-ARCHITECTURE-20260929 C8 / P1-7）：抓取、限速、候选存取、
许可治理、模板库导入的编排曾经全部内联在 `app.py` 的 `_Handler` 请求
方法里。提取之后：

  * `app.py` 不允许再出现编排原语（fetch_reference / extract_candidate /
    rate limiter wait）——那是编排回流到 handler 的信号；
  * handler 的 intake 方法必须是纯委托；
  * 限速器唯一实例住在 intake_service（app 保留同实例别名，既有测试
    按别名打补丁依然生效）。
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "htmlninefox" / "server" / "app.py"
SERVICE = ROOT / "htmlninefox" / "server" / "intake_service.py"

ORCHESTRATION_PRIMITIVES = (
    "intake.fetch_reference(",
    "intake.extract_candidate(",
    "intake.validate_url(url)",
    "_INTAKE_RATE_LIMITER.wait(",
    "INTAKE_RATE_LIMITER.wait(",
)


def test_app_handler_has_no_intake_orchestration():
    """编排回流到 handler 就是 P1-7 的回归。"""
    source = APP.read_text(encoding="utf-8")
    for primitive in ORCHESTRATION_PRIMITIVES:
        assert primitive not in source, (
            f"app.py 又出现了编排原语 {primitive!r}——intake 编排必须留在 "
            "IntakeService（P1-7 回归）")


def test_handler_intake_methods_are_pure_delegation():
    """每个 `_api_intake_*` 方法体必须是对 `self._intake_service()` 的单行委托。"""
    source = APP.read_text(encoding="utf-8")
    methods = [m for m in
               ("_api_intake_fetch", "_api_intake_fetch_batch", "_api_intake_zip",
                "_api_intake_decide", "_api_intake_motion_import",
                "_api_intake_components_import", "_api_intake_style_preset_create",
                "_api_intake_page_blocks")
               if f"def {m}" in source]
    assert methods, "找不到任何 intake 方法（签名全改了？重写本门禁）"
    for method in methods:
        start = source.index(f"def {method}")
        body = source[start:]
        body = body[:body.index("\n    def ")] if "\n    def " in body else body
        assert "return self._intake_service()." in body, (
            f"{method} 不是单行委托——intake 编排又回到了 handler（P1-7 回归）")


def test_rate_limiter_is_owned_by_the_service():
    """限速器唯一实例住在 intake_service；app 只有别名。"""
    service_source = SERVICE.read_text(encoding="utf-8")
    assert "INTAKE_RATE_LIMITER = intake.RateLimiter(" in service_source, \
        "限速器实例必须由 IntakeService 模块拥有"
    app_source = APP.read_text(encoding="utf-8")
    assert "intake.RateLimiter(" not in app_source, \
        "app.py 不得再造限速器实例（两实例 = 限速失效）"
    assert "_INTAKE_RATE_LIMITER" in app_source, \
        "app.py 需要保留同名别名，既有测试按它打补丁"
