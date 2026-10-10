"""C8 门禁：候选键与许可默认值只允许一个事实来源。

审计原话：「intake.py 写 15 个候选键，散在 5 处用 .get(键, 默认) 读回，
license_class 在三处默认 reference。键名写错会静默降级许可档位而无
测试失败。」

这里的四条门禁分别锁：

  1. 写入端序列化出的候选键 == CandidateKeys.ALL（双向：写多写少都红）；
  2. open 许可附带的 decorations 也在清单内；
  3. licence_of 对三档许可与缺键的行为；
  4. 结构扫描：server 包不允许出现 license_class 的裸读取，
     intake.py 的许可默认值只允许出现在 DEFAULT_LICENCE 一处。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from htmlninefox import intake  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

SOURCE_PAGE = """
<html><body><main>
  <section class="hero"><h2>本期要点</h2><p>营收同比增长百分之十二。</p></section>
  <section class="pricing"><h2>定价</h2><p>基础版每月 0 元。</p></section>
</main></body></html>
"""


def _candidate(license_class: str = "reference") -> dict:
    source = {"id": "gate-src", "name": "门禁源", "kind": "gallery",
              "license_class": license_class, "entry_url": "https://example.com/page"}
    evidence = {
        "url": "https://example.com/page", "final_url": "https://example.com/page",
        "status": 200, "content_type": "text/html; charset=utf-8",
        "body": SOURCE_PAGE.encode("utf-8"),
        "fetched_at": "2026-10-08T09:00:00",
        "body_sha256": "0" * 64,
    }
    return intake.extract_candidate(evidence, source=source)


def test_serialized_candidate_keys_are_exactly_declared():
    """写多（新键忘了进清单）写少（常量指向不存在的键）都红。

    `decorations` 只随 open 许可的抓取附带，所以 reference 候选的键集
    == 全集减去 decorations；open 候选 == 全集（下一条测）。
    """
    candidate = _candidate("reference")
    base = set(intake.CandidateKeys.ALL) - {intake.CandidateKeys.DECORATIONS}
    assert set(candidate.keys()) == base


def test_open_licence_keys_are_exactly_declared():
    candidate = _candidate("open")
    assert set(candidate.keys()) == set(intake.CandidateKeys.ALL)


def test_open_licence_extras_stay_declared():
    candidate = _candidate("open")
    assert "decorations" in intake.CandidateKeys.ALL
    assert set(candidate.keys()) <= set(intake.CandidateKeys.ALL)


@pytest.mark.parametrize("licence,expected", [
    ("open", "open"),
    ("reference", "reference"),
    ("inspiration-only", "inspiration-only"),
    (None, "reference"),
])
def test_licence_of_single_owner(licence, expected):
    candidate = {} if licence is None else {"license_class": licence}
    assert intake.licence_of(candidate) == expected


def test_server_package_never_reads_licence_keys_raw():
    """server 包不允许出现裸的许可读取；一律走 intake.licence_of。"""
    server_dir = ROOT / "htmlninefox" / "server"
    offenders = []
    for path in server_dir.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if '.get("license_class"' in text or ".get('license_class'" in text:
            offenders.append(str(path.relative_to(ROOT)))
        if 'or "reference"' in text:
            offenders.append(str(path.relative_to(ROOT)) + ' (or "reference")')
    assert not offenders, f"server 包存在裸许可读取：{offenders}"


def test_intake_licence_default_is_declared_once():
    """默认值的拥有者只有一个：DEFAULT_LICENCE 定义处。"""
    text = (ROOT / "htmlninefox" / "intake.py").read_text(encoding="utf-8")
    assert text.count('DEFAULT_LICENCE = "reference"') == 1
    assert 'or "reference"' not in text, \
        "intake.py 存在绕过 DEFAULT_LICENCE 的内联默认值"
