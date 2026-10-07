# -*- coding: utf-8 -*-
"""verify_page_blocks_chain.py · v0.7.0 发布验收：页面拆解真实链路实测。

e2e_verify.py 覆盖「描述 → 生成」；本脚本覆盖 v0.7 的另一半「页面 → 项目」，
且不用夹具，按生产形状走真实 HTTP：

  1. 真实公网抓取（example.com，内置 land-book 来源）——传输成功路径，
     v0.6.2 坏过、v0.7.0 发布前又翻出「生产形态必崩」的正是这条路；
     SSRF 门禁对环回的拒绝也顺带验证（按设计拒绝）。
  2. 富内容测试页（进程内证据注入 CandidateStore，与 tests/test_intake_workbench.py
     的 stub_fetch 同缝）→ approve → /api/intake/page-blocks 拆块
     → /api/generate 六类 intent → 断言页面正文按计数出现 → 反馈迭代不丢。
  3. reference 许可：正文一字不随行（structure_only），整页不进模板库。

运行：python scripts/verify_page_blocks_chain.py
除 example.com 外全部请求只发往本机环回固定端口；测试来源 YAML 在 finally 清理。
"""
from __future__ import annotations

import hashlib
import http.client
import json
import re
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(REPO))
sys.stdout.reconfigure(encoding="utf-8")

APP_HOST = "127.0.0.1"
APP_PORT = 8642

ALPHA = "九尾狐实测特征串甲：这一段必须出现在成品页面里。"
BETA = "九尾狐实测特征串乙：嵌套分区里的文字，同样必须出现在成品里。"

PAGE = ("<!doctype html>\n<html lang=\"zh-CN\"><head><meta charset=\"utf-8\">"
        "<title>狐构产品页</title></head>\n<body>\n<main>\n"
        "  <section class=\"hero\"><h1>狐构·把想法变成可交付的成果</h1>\n"
        "    <p>" + ALPHA + "</p></section>\n"
        "  <section class=\"features\"><h2>为什么选我们</h2>\n"
        "    <p>容器自己的说明文字。</p>\n"
        "    <section class=\"nested\"><h3>怎么开始</h3><p>" + BETA + "</p></section>\n"
        "  </section>\n</main>\n</body></html>")

results = []
_cleanup_paths: list[Path] = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  {detail}" if detail else ""))


def api(method, path, body=None):
    """POST/GET 工作台 API。host/port 为模块常量，path 为字面量。"""
    conn = http.client.HTTPConnection(APP_HOST, APP_PORT, timeout=180)
    payload = json.dumps(body) if body is not None else None
    try:
        conn.request(method, path, body=payload,
                     headers={"Content-Type": "application/json"})
        resp = conn.getresponse()
        return json.loads(resp.read().decode())
    finally:
        conn.close()


def body_of(html):
    m = re.search(r"<body[^>]*>(.*)</body>", html, re.S)
    return m.group(1) if m else ""


def write_source(source_id: str, name: str, license_class: str) -> None:
    """把测试来源写进用户来源注册表（产品读取 ~/.htmlninefox/sources）。"""
    extra = Path.home() / ".htmlninefox" / "sources"
    extra.mkdir(parents=True, exist_ok=True)
    path = extra / f"{source_id}.yaml"
    path.write_text(yaml.safe_dump({
        "id": source_id, "name": name, "kind": "gallery",
        "license_class": license_class, "entry_url": "https://example.com/",
        "notes": "页面拆解链路验收临时来源（跑完即删）",
    }, allow_unicode=True), encoding="utf-8")
    _cleanup_paths.append(path)


def inject_candidate(out_root: Path, source_id: str) -> str:
    """进程内证据直存 CandidateStore（stub_fetch 同缝，绕不开 SSRF 门禁对
    环回的拒绝——那是设计），随后 approve/page-blocks 全部走真实 HTTP API。"""
    from htmlninefox import intake
    body = PAGE.encode("utf-8")
    evidence = {
        "url": "https://example.com/fox-verify", "final_url": "https://example.com/fox-verify",
        "followed": ["https://example.com/fox-verify"], "status": 200,
        "content_type": "text/html; charset=utf-8", "body": body,
        "body_sha256": hashlib.sha256(body).hexdigest(), "body_bytes": len(body),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
    source = intake.find_source(source_id, extra_dir=Path.home() / ".htmlninefox" / "sources")
    candidate = intake.extract_candidate(evidence, source=source)
    saved = intake.CandidateStore(out_root).save(candidate, evidence)
    return saved["candidate_id"]


def main():
    from htmlninefox.server import app as server_app
    out_root = REPO / ".tmp" / "pageblocks-chain-projects"
    out_root.mkdir(parents=True, exist_ok=True)
    server_app._OUTPUT_ROOT = out_root
    srv = ThreadingHTTPServer((APP_HOST, APP_PORT), server_app._Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(0.5)
    try:
        run(out_root)
    finally:
        srv.shutdown()
        for path in _cleanup_paths:
            path.unlink(missing_ok=True)
    failed = [r for r in results if not r[1]]
    print(f"\n===== 页面拆解真实链路：{len(results) - len(failed)}/{len(results)} PASS =====")
    return 1 if failed else 0


def run(out_root):
    # ---- 链路 1：真实公网抓取 + SSRF 拒绝环回 ----
    write_source("fox-verify-open", "验收开放许可", "open")
    write_source("fox-verify-ref", "验收参考许可", "reference")
    real = api("POST", "/api/intake/fetch",
               {"url": "https://example.com/", "source_id": "land-book"})
    check("真实公网抓取成功（example.com → 200，传输链路可用）",
          real.get("ok") is True and bool(real.get("candidate", {}).get("candidate_id")),
          f"status={real.get('candidate', {}).get('status')} error={real.get('error')}")
    loopback = api("POST", "/api/intake/fetch",
                   {"url": "http://127.0.0.1:8620/api/health", "source_id": "land-book"})
    check("SSRF 门禁拒绝环回地址（按设计拒绝）",
          loopback.get("error", {}).get("code") == "intake_host_forbidden")

    # ---- 链路 2：open 许可全链路 ----
    cid = inject_candidate(out_root, "fox-verify-open")
    dec = api("POST", "/api/intake/candidates/" + cid + "/approve")
    check("批准：open 许可整页进模板库", dec.get("gallery_item") is not None
          and dec.get("gallery_skipped") is None)

    pb = api("POST", "/api/intake/page-blocks", {"candidate_id": cid})
    blocks = pb["blocks"]
    texts = [b.get("content", "") for b in blocks]
    check("拆块：嵌套分区被切开而非吞成一个 main",
          len(blocks) >= 2 and any(BETA in t for t in texts),
          f"{len(blocks)} blocks")
    check("拆块：heading 与 content 不重复（不会渲染两遍）",
          all(b["heading"] != b["content"] for b in blocks if b.get("content")))
    check("拆块：open 许可正文随行（verbatim）",
          pb["carries_text"] is True
          and all(b["provenance"] == "verbatim" for b in blocks if b.get("content")))

    for intent in ["landing", "dashboard", "deck", "poster", "archdoc", "doc"]:
        gen = api("POST", "/api/generate", {
            "prompt": "做一个狐构品牌的" + intent + "页面", "intent": intent,
            "quiet_llm": True, "blocks": blocks})
        proj = Path(gen["project"])
        html = (proj / "output.html").read_text(encoding="utf-8")
        body = body_of(html)
        ok = (ALPHA in body and BETA in body
              and body.count(ALPHA) == 1 and body.count(BETA) == 1)
        check(f"生成 {intent}：页面正文出现且各恰好一次", ok,
              f"{len(html)}B · {gen['preset_id']}")

    gen = api("POST", "/api/generate", {
        "prompt": "做一个狐构品牌的落地页", "intent": "landing",
        "quiet_llm": True, "blocks": blocks})
    proj = Path(gen["project"])
    before = (proj / "output.html").read_text(encoding="utf-8")
    api("POST", "/api/feedback", {"project": str(proj), "note": "颜色深一点",
                                  "revise": True})
    after = (proj / "output.html").read_text(encoding="utf-8")
    check("反馈迭代：分块正文不丢", ALPHA in body_of(after) and after != before)

    # ---- 链路 3：reference 许可 ----
    cid2 = inject_candidate(out_root, "fox-verify-ref")
    dec2 = api("POST", "/api/intake/candidates/" + cid2 + "/approve")
    pb2 = api("POST", "/api/intake/page-blocks", {"candidate_id": cid2})
    check("批准：reference 许可跳过模板库导入",
          dec2.get("gallery_item") is None
          and "reference" in (dec2.get("gallery_skipped") or ""))
    gen2 = api("POST", "/api/generate", {
        "prompt": "做一个狐构品牌的落地页", "intent": "landing",
        "quiet_llm": True, "blocks": pb2["blocks"]})
    html2 = (Path(gen2["project"]) / "output.html").read_text(encoding="utf-8")
    check("reference 许可：正文一字不出现，产物回落自带文案",
          ALPHA not in html2 and BETA not in html2
          and pb2["carries_text"] is False)


if __name__ == "__main__":
    sys.exit(main())
