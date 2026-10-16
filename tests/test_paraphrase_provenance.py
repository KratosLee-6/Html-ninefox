"""provenance 第三档 `paraphrased` 的门禁（v0.7.7）。

设计决策（ROADMAP 定案）的三条承重墙，每一条都有对应的失败形态：

  1. LLM 可用才升级——未配置/失败回落 structure_only，「离线可用」不破。
  2. 预览即所得——改写发生在 page_blocks（审核台预览拆块），不在生成时；
     用户选择的就是改写后的文本。
  3. 忠实度门禁——`paraphrased` 必须通过 `paraphrase.is_faithful`，否则
     退化为带假标签的 verbatim，字段级许可名存实亡。

另有一条成本纪律：open 路径**永不调用**改写器（verbatim 语义与开销不变）。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from htmlninefox import intake, paraphrase  # noqa: E402
from htmlninefox.server.intake_service import (  # noqa: E402
    INTAKE_RATE_LIMITER,
    IntakeService,
)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

SOURCE = ("九尾狐实测特征串甲：这一段必须出现在成品页面里，承载品牌的核心"
          "价值与产品承诺。")
REWRITE = ("狐九尾的链路验收：这句被重新表述过，品牌的核心价值与产品承诺"
           "依旧完整保留。")
PAGE = ("<html><body><main><section class=\"hero\"><h1>狐构产品</h1>"
        "<p>" + SOURCE + "</p></section></main></body></html>").encode("utf-8")
REF_CANDIDATE = {"license_class": "reference",
                 "final_url": "https://example.com/probe"}


def _blocks(rewriter=None, licence="reference"):
    candidate = dict(REF_CANDIDATE, license_class=licence)
    return intake.page_blocks_from_candidate(candidate, PAGE.decode("utf-8"),
                                             rewriter=rewriter)


# ------------------------------------------------------------ 忠实度门禁本身

def test_the_fidelity_gate_tells_a_rewrite_from_a_copy():
    assert paraphrase.is_faithful(SOURCE, REWRITE), \
        "真改写被误拒——OVERLAP_CEILING 或长度界调得过紧"
    for bad in (SOURCE,                      # 原样照抄
                SOURCE.replace("甲", "乙"),  # 一字之差
                "狐九尾。",                   # 丢光事实的缩写
                "",                          # 空
                None):                       # 类型外的输入
        assert not paraphrase.is_faithful(SOURCE, bad or ""), (
            f"不应通过忠实度门禁：{bad!r:.40}——paraphrased 会退化成假标签 verbatim")


# ------------------------------------------------------- 块级 provenance 规则

def test_a_faithful_rewrite_becomes_paraphrased():
    blocks = _blocks(rewriter=lambda source, heading: REWRITE)
    carrying = [b for b in blocks if b["provenance"] == "paraphrased"]
    assert carrying, "忠实改写没有被标注为 paraphrased"
    for block in carrying:
        assert block["content"] == REWRITE.strip(), "随行文本必须是改写后的"
        assert SOURCE[:10] not in block["content"], "改写文本里不应残留原文开头"


def test_an_unfaithful_rewrite_falls_back_to_structure_only():
    for bad in (SOURCE, "", None, "狐九尾。"):
        blocks = _blocks(rewriter=lambda source, heading, _bad=bad: _bad)
        assert all(b["provenance"] == "structure_only" and b["content"] == ""
                   for b in blocks), (
            f"不忠实/失败的改写结果 {bad!r:.20} 仍随行——忠实度门禁失效")


def test_open_licence_never_calls_the_rewriter():
    calls: list[str] = []

    def spy(source, heading):
        calls.append(source)
        return REWRITE

    blocks = _blocks(rewriter=spy, licence="open")
    assert calls == [], "open 路径调用了改写器——verbatim 语义与开销被破坏"
    assert all(b["provenance"] == "verbatim" and b["content"]
               for b in blocks if b.get("content") or b["provenance"] == "verbatim"), \
        "open 许可的 verbatim 行为被改写通道改变"


def test_no_rewriter_keeps_the_offline_behaviour():
    blocks = _blocks(rewriter=None)
    assert all(b["provenance"] == "structure_only" and b["content"] == ""
               for b in blocks), \
        "未配置改写器时行为必须与 v0.7.6 完全一致（structure_only）——" \
        "「离线可用」不允许被 LLM 能力绑架"


# ------------------------------------------------------- IntakeService 接线

class _GallerySpy:
    def import_files(self, files, *, name="", tags=None):
        return {"name": name}


class _RefuseGallery:
    def import_files(self, *_a, **_k):
        raise AssertionError("reference 许可不得整页导入模板库")


@pytest.fixture()
def service(tmp_path, monkeypatch):
    monkeypatch.setattr(INTAKE_RATE_LIMITER, "default_interval", 0.0)
    return IntakeService(output_root=tmp_path, gallery=_GallerySpy())


def _stub_fetch_and_approve(service, monkeypatch, licence="reference") -> str:
    evidence = {
        "url": "https://example.com/probe", "final_url": "https://example.com/probe",
        "followed": ["https://example.com/probe"], "status": 200,
        "content_type": "text/html; charset=utf-8", "body": PAGE,
        "body_sha256": "0" * 64, "body_bytes": len(PAGE),
        "fetched_at": "2026-10-12T09:00:00",
    }
    monkeypatch.setattr(intake, "fetch_reference", lambda url, **k: dict(evidence))
    out = service.fetch({"url": "https://example.com/probe", "source_id": None})
    cid = out["candidate"][intake.CandidateKeys.CANDIDATE_ID]
    service.candidates().set_status(cid, "approved")
    return cid


def test_service_page_blocks_reports_the_provenance_mix(service, monkeypatch):
    monkeypatch.setattr(service, "rewriter", lambda source, heading: REWRITE)
    cid = _stub_fetch_and_approve(service, monkeypatch, licence="reference")
    result = service.page_blocks({"candidate_id": cid})
    assert result["paraphrased"] is True, "service 未把 paraphrased 透出"
    assert result["carries_text"] is True
    assert any(b["provenance"] == "paraphrased" and b["content"] == REWRITE.strip()
               for b in result["blocks"])


def test_service_without_a_rewriter_stays_structure_only(service, monkeypatch):
    cid = _stub_fetch_and_approve(service, monkeypatch, licence="reference")
    result = service.page_blocks({"candidate_id": cid})
    assert result["paraphrased"] is False and result["carries_text"] is False
    assert all(b["content"] == "" for b in result["blocks"])


# ------------------------------------------------------- 运输层的失败归一

def test_the_llm_transport_normalises_every_failure_to_none():
    class _Boom:
        def call(self, *a, **k):
            raise RuntimeError("未配置 LLM")

    class _Empty:
        def call(self, *a, **k):
            class _R:
                def __str__(self):
                    return "   "
            return _R()

    assert paraphrase.make_llm_rewriter(_Boom())(SOURCE, "标题") is None, \
        "LLM 异常必须归一为 None（回落 structure_only），不得打断拆块"
    assert paraphrase.make_llm_rewriter(_Empty())(SOURCE, "标题") is None, \
        "空响应必须归一为 None"
    assert paraphrase.make_llm_rewriter(_Boom())("", "标题") is None, \
        "空原文不应发起 LLM 调用"
