"""0.9.7 多页站点门禁

纪律（PLAN-v1.0 v0.9.7）：站点是**组装层**——每页由既有单文件生成器渲染
（同一 brief 的角色切片 + 同一 preset），单文件承诺原样保留。验收链：
analyze 识别站点 brief → site_plan → generate site=true → 三页落盘 →
页间导航真实可达 → bundle zip 含站点且回读可解析。
"""

import json
import urllib.parse
import zipfile
from pathlib import Path

import pytest

from htmlninefox.sites import (DEFAULT_PAGES, INDEX_SLUG, build_site,
                               default_site_plan, inject_nav, is_site_brief)

_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def workbench(tmp_path: Path):
    import sys
    sys.path.insert(0, str(_ROOT))
    from tests.conftest import WorkbenchServer
    with WorkbenchServer(tmp_path / "output") as server:
        yield server


# ============================================================
# 单元：识别 / 配方 / 导航注入
# ============================================================

def test_site_brief_detection():
    assert is_site_brief("做一个智能水杯官网")
    assert is_site_brief("给公司做一个多页站点")
    assert is_site_brief("整站改版")
    assert is_site_brief("企业网站，三个栏目")
    assert not is_site_brief("做一个产品介绍落地页")
    assert not is_site_brief("写一篇长文档")


def test_default_plan_shape():
    plan = default_site_plan(prompt="做一个官网", intent="landing")
    assert plan["kind"] == "site"
    slugs = [p["slug"] for p in plan["pages"]]
    assert slugs == ["index", "details", "about"]
    assert plan["pages"][1]["intent"] == "doc"
    assert plan["nav"] == slugs


def test_inject_nav_links_are_consistent():
    plan = default_site_plan(intent="landing")
    html = "<html><body><h1>首页</h1></body></html>"
    out = inject_nav(html, plan["pages"], INDEX_SLUG, brand="狐构")
    assert 'href="./index.html"' in out and 'href="./details.html"' in out
    assert 'aria-current="page"' in out
    assert out.index("fox-site-nav") > out.index("<body")
    # 无 body 的退化输入原样返回（不炸）
    assert inject_nav("<html></html>", plan["pages"], "index") == "<html></html>"


# ============================================================
# 单元：build_site 组装（真实 pipeline 产物）
# ============================================================

def test_build_site_pages_and_site_json(tmp_path: Path):
    from htmlninefox import pipeline
    generated = pipeline.run_expert(
        "做一个智能水杯的产品官网",
        output=str(tmp_path), quiet_llm=True)
    work = Path(generated["work"])
    report = build_site(work)
    site_dir = work / "site"
    # 三页落盘 + site.json
    slugs = [p["slug"] for p in report["pages"]]
    assert slugs == ["index", "details", "about"]
    for p in report["pages"]:
        assert (site_dir / Path(p["file"]).name).is_file()
    data = json.loads((site_dir / "site.json").read_text(encoding="utf-8"))
    assert data["kind"] == "site" and data["nav"] == slugs
    assert data["shared_preset_id"], "站点必须记录共享 preset"
    # 每页都有导航条且链接互相可达（相对链接全场景一致）
    for p in report["pages"]:
        html = (site_dir / Path(p["file"]).name).read_text(encoding="utf-8")
        assert 'data-site-nav="1"' in html
        for other in slugs:
            href = "./index.html" if other == "index" else f"./{other}.html"
            assert f'href="{href}"' in html, f"{p['slug']} 缺到 {other} 的链接"
    # 单文件承诺：index 与主产物同源（共享 preset），doc 页内容是切片不是复制
    index_html = (site_dir / "index.html").read_text(encoding="utf-8")
    main_html = (work / "output.html").read_text(encoding="utf-8")
    assert "--fox-primary" in index_html and "--fox-primary" in main_html
    details = (site_dir / "details.html").read_text(encoding="utf-8")
    assert "产品详情" in details and details != index_html


# ============================================================
# 变异验证：砍掉导航注入必须 CAUGHT
# ============================================================

def test_mutation_dropping_nav_injection_is_caught(tmp_path: Path):
    """变异验证：砍掉导航注入 → 「每页必须带 data-site-nav」门禁 CAUGHT
    （同进程函数式变异，参照 test_style_axis 形态）。"""
    import htmlninefox.sites as sites

    def _gate(report, work: Path) -> None:
        for p in report["pages"]:
            html = (work / p["file"]).read_text(encoding="utf-8")
            assert 'data-site-nav="1"' in html, f"{p['slug']} 缺站点导航"

    import htmlninefox.generators as _gen  # noqa: F401 — 确保 render 路径可用
    real = sites.inject_nav
    try:
        sites.inject_nav = lambda html, pages, current, brand="": html
        from htmlninefox import pipeline
        generated = pipeline.run_expert(
            "做一个智能水杯的产品官网",
            output=str(tmp_path), quiet_llm=True)
        work = Path(generated["work"])
        mutated = sites.build_site(work)
        try:
            _gate(mutated, work)
        except AssertionError as error:
            assert "缺站点导航" in str(error)
        else:
            raise AssertionError("砍掉导航注入后门禁必须 CAUGHT")
    finally:
        sites.inject_nav = real
    # 还原后同门禁必须真过（第二份产物，互不污染）
    from htmlninefox import pipeline
    generated = pipeline.run_expert(
        "做一个智能水杯的产品官网",
        output=str(tmp_path), quiet_llm=True)
    work = Path(generated["work"])
    _gate(sites.build_site(work), work)


# ============================================================
# 端到端：analyze 识别 → generate site=true → bundle zip 回读
# ============================================================

def test_analyze_detects_site_plan(workbench):
    import sys as _sys
    _sys.path.insert(0, str(_ROOT))
    from tests.test_server_project_api import request as api_request
    data, _ = api_request(workbench.base_url, "/api/analyze", "POST", {
        "prompt": "做一个智能水杯官网，含产品详情和公司介绍", "quiet_llm": True})
    assert data.get("site_plan"), "站点类 brief 必须产出 site_plan"
    assert [p["slug"] for p in data["site_plan"]["pages"]] == \
        ["index", "details", "about"]
    plain, _ = api_request(workbench.base_url, "/api/analyze", "POST", {
        "prompt": "做一个产品介绍落地页", "quiet_llm": True})
    assert plain.get("site_plan") is None, "非站点 brief 不得误报 site_plan"


def test_generate_site_e2e_and_bundle(workbench):
    import sys as _sys
    _sys.path.insert(0, str(_ROOT))
    from tests.test_server_project_api import request as api_request
    base = workbench.base_url
    result, _ = api_request(base, "/api/generate", "POST", {
        "prompt": "做一个智能水杯的产品官网",
        "workflow": "one-article-three-outputs", "site": True, "quiet_llm": True})
    name = result["project_name"]
    # generate 载荷带站点报告与预览链接（机器形态）
    assert result.get("site") and result["site"]["pages"], result.get("site")
    assert result.get("site_preview_url", "").endswith("/site/index.html")
    # 工作区三页落盘
    site_dir = workbench.output_root / name / "site"
    for fname in ("index.html", "details.html", "about.html", "site.json"):
        assert (site_dir / fname).is_file(), fname
    # 交付包（异步 job → 轮询）：site/ 全部入 zip，回读可解析、导航链接自洽
    submitted, _ = api_request(base, "/api/exports/bundle", "POST",
                               {"project_name": name}, expected=202)
    import time as _time
    deadline = _time.time() + 120
    while True:
        job = api_request(base, "/api/jobs/" + urllib.parse.quote(
            submitted["job"]["id"]), "GET")[0]
        if job.get("status") in ("done", "succeeded", "completed"):
            bundle = job.get("result") or {}
            break
        assert job.get("status") not in ("failed", "error"), str(job)[:200]
        assert _time.time() < deadline, "bundle job 超时"
        _time.sleep(1)
    assert bundle.get("site", {}).get("pages"), f"bundle 缺 site 报告: {bundle}"
    zip_path = Path(bundle["zip"])
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        for fname in ("site/index.html", "site/details.html",
                      "site/about.html", "site/site.json"):
            assert fname in names, f"zip 缺 {fname}"
        index_html = zf.read("site/index.html").decode("utf-8")
        assert 'href="./details.html"' in index_html
        sj = json.loads(zf.read("site/site.json").decode("utf-8"))
        assert sj["kind"] == "site" and len(sj["pages"]) == 3
