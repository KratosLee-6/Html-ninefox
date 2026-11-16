"""sites.py · 多页站点组装层（v0.9.7，PLAN-v1.0 输出端质变）

站点 = 多个单文件页 + 共享 token + 站内导航。**组装层，不是新引擎**：
每页都由既有单文件生成器渲染（同一 brief 的角色切片 + 同一 preset），
单文件承诺原样保留——任何一页拿出来仍是可独立交付的单文件 HTML。

结构（工作区与交付 zip 同构，导航链接全场景一致）：
    site/index.html   首页（= 主产物 output.html 内容 + 站点导航）
    site/<slug>.html  子页（brief 的角色切片换 intent 渲染）
    site/site.json    页面清单/共享令牌/导航树 —— 机器形态（agent 可消费）

默认配方三页：index（主意图）/ details（doc）/ about（landing 变体）。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

SITE_DIR = "site"
SITE_FILE = "site.json"
INDEX_SLUG = "index"

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")

# 默认站点配方：slug → (intent, 角色标题后缀, content.blocks 覆盖)
# about 复用 landing 渲染器但砍掉营销块——同一家族的不同页面，不是同一段内容复制三遍
DEFAULT_PAGES: List[Dict[str, Any]] = [
    {"slug": INDEX_SLUG, "intent": None, "label": "首页",
     "title_suffix": "", "blocks": None},
    {"slug": "details", "intent": "doc", "label": "产品详情",
     "title_suffix": " · 产品详情", "blocks": None},
    {"slug": "about", "intent": "landing", "label": "关于我们",
     "title_suffix": " · 关于我们",
     "blocks": ["nav", "hero", "features", "faq", "cta_footer"]},
]


def default_site_plan(prompt: str = "", intent: str | None = None) -> Dict[str, Any]:
    """站点类 brief 的默认多页配方（机器形态，analyze/generate 共用）。"""
    pages = []
    for spec in DEFAULT_PAGES:
        pages.append({
            "slug": spec["slug"],
            "intent": spec["intent"] or (intent or "landing"),
            "label": spec["label"],
            "title_suffix": spec["title_suffix"],
            **({"blocks": spec["blocks"]} if spec["blocks"] else {}),
        })
    return {
        "kind": "site",
        "prompt_excerpt": (prompt or "")[:80],
        "pages": pages,
        "nav": [p["slug"] for p in pages],
        "shared": "preset/tone/assets 与主产物同源（组装层不重跑生成）",
    }


def is_site_brief(prompt: str) -> bool:
    """站点类 brief 识别：官网/站点/多页/整站/网站。"""
    return bool(re.search(r"官网|站点|整站|多页|网站", prompt or ""))


def _page_brief(base_brief: dict, spec: dict) -> dict:
    """brief 的角色切片：换标题、砍块，content 其他字段原样保留。"""
    brief = json.loads(json.dumps(base_brief, ensure_ascii=False))
    content = brief.setdefault("content", {})
    brand = str(content.get("brand") or "Your Product")
    base_headline = str(content.get("headline") or brand)
    suffix = spec.get("title_suffix") or ""
    content["headline"] = f"{base_headline}{suffix}" if suffix else base_headline
    if spec.get("blocks"):
        content["blocks"] = list(spec["blocks"])
    return brief


def inject_nav(html: str, pages: List[Dict[str, Any]], current: str,
               brand: str = "") -> str:
    """页面顶部插站点导航条（自包含样式，链接相对全场景一致）。"""
    items = []
    for p in pages:
        slug = p["slug"]
        href = "./index.html" if slug == INDEX_SLUG else f"./{slug}.html"
        aria = ' aria-current="page"' if slug == current else ""
        items.append(f'<a href="{href}"{aria}>{p["label"]}</a>')
    nav = (
        '<nav class="fox-site-nav" data-site-nav="1" aria-label="站点导航">'
        f'<span class="fox-site-brand">{brand}</span>'
        + "".join(items) + "</nav>"
        "<style>.fox-site-nav{display:flex;gap:20px;align-items:center;"
        "padding:12px 32px;border-bottom:1px solid var(--fox-border,#E8E8E4);"
        "font-size:.9rem;flex-wrap:wrap}"
        ".fox-site-nav a{color:var(--fox-text,#1A1A1A);text-decoration:none;"
        "opacity:.75}.fox-site-nav a[aria-current]{opacity:1;font-weight:700;"
        "color:var(--fox-primary,#5E6AD2)}"
        ".fox-site-brand{font-weight:800;letter-spacing:.02em;"
        "color:var(--fox-text,#1A1A1A);margin-right:8px}</style>"
    )
    marker = re.search(r"<body[^>]*>", html)
    if not marker:
        return html
    at = marker.end()
    return html[:at] + "\n" + nav + html[at:]


def build_site(work: Path, *, intent_hint: str | None = None) -> Dict[str, Any]:
    """在项目目录组装站点（组装层：读 .foxstate，逐页渲染，不重跑生成）。

    返回报告 {"pages": [...], "site_json": 路径, "bytes": 总字节}；
    状态不可读（缺 .foxstate）时抛 ValueError。
    """
    from . import generators, revisions

    state = revisions.load_state(work)
    brief = state.get("brief") or {}
    preset = state.get("preset") or {}
    assets = state.get("assets") or {}
    main_intent = state.get("intent") or intent_hint or "landing"
    brand = str((brief.get("content") or {}).get("brand") or "Your Product")

    plan = default_site_plan(intent=main_intent)
    site_dir = work / SITE_DIR
    site_dir.mkdir(parents=True, exist_ok=True)

    written: List[Dict[str, Any]] = []
    total = 0
    for spec in plan["pages"]:
        slug = spec["slug"]
        if not _SLUG_RE.match(slug):
            raise ValueError(f"非法站点页 slug：{slug}")
        if slug == INDEX_SLUG:
            html = (work / "output.html").read_text(encoding="utf-8")
        else:
            page_brief = _page_brief(brief, spec)
            html = generators.render(spec["intent"], page_brief,
                                     {"preset": dict(preset)}, dict(assets))
        html = inject_nav(html, plan["pages"], slug, brand=brand)
        out = site_dir / f"{slug}.html"
        out.write_text(html, encoding="utf-8")
        total += len(html.encode("utf-8"))
        written.append({"slug": slug, "intent": spec["intent"], "label": spec["label"],
                        "file": f"{SITE_DIR}/{slug}.html", "bytes": len(html.encode("utf-8"))})

    site_json = {
        "kind": "site",
        "main_intent": main_intent,
        "shared_preset_id": state.get("preset_id"),
        "pages": written,
        "nav": plan["nav"],
    }
    (site_dir / SITE_FILE).write_text(
        json.dumps(site_json, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"pages": written, "site_json": str(site_dir / SITE_FILE),
            "bytes": total, "plan": plan}


def site_files(work: Path) -> List[Path]:
    """站点全部文件（无 site 目录返回空列表）——交付组包用。"""
    site_dir = work / SITE_DIR
    if not site_dir.is_dir():
        return []
    return sorted(p for p in site_dir.iterdir() if p.is_file())
