"""Private HTML gallery package import and learning behavior."""

from __future__ import annotations

import base64
from urllib.parse import quote

import pytest

from htmlninefox import template_gallery
from htmlninefox.user_gallery import UserGalleryError, UserGalleryStore


def encoded(path: str, content: str) -> dict[str, str]:
    return {"path": path, "data_base64": base64.b64encode(content.encode()).decode()}


def test_import_package_copies_assets_and_detects_pages(tmp_path):
    store = UserGalleryStore(tmp_path)
    item = store.import_files([
        encoded("index.html", """<!doctype html><title>我的演示</title>
            <link rel=\"stylesheet\" href=\"assets/style.css\">
            <section class=\"page\" data-page=\"cover\"><h1>封面</h1></section>
            <section class=\"page\" data-page=\"result\"><h1>结果</h1></section>"""),
        encoded("assets/style.css", "body{color:#123456;font-family:'Noto Serif SC',serif}"),
    ], tags=["演示", "个人"])

    assert item["intent"] == "deck"
    assert [page["id"] for page in item["pages"]] == ["cover", "result"]
    assert [page["block_id"] for page in item["pages"]] == ["cover", "metrics"]
    assert item["design_tokens"]["colors"] == ["#123456"]
    assert item["style_overrides"] == {"primary": "#123456", "font": "serif"}
    assert store.resolve_file(item["id"], "assets/style.css").read_text() == (
        "body{color:#123456;font-family:'Noto Serif SC',serif}")

    preview = template_gallery.render_gallery_preview(
        item["id"], "result", user_root=tmp_path)
    assert f'/api/gallery-assets/{quote(item["id"])}/' in preview
    assert "htmlninefox-private-template" in preview
    assert "querySelectorAll" in preview


def test_import_rejects_path_traversal_and_cleans_staging(tmp_path):
    store = UserGalleryStore(tmp_path)
    with pytest.raises(UserGalleryError):
        store.import_files([encoded("../outside.html", "<title>bad</title>")])
    assert list(tmp_path.iterdir()) == []


def test_used_private_template_becomes_recommendation(tmp_path):
    store = UserGalleryStore(tmp_path)
    item = store.import_files([
        encoded("index.html", "<title>常用报告</title><h1>Research report</h1>"),
    ])
    item["intent"] = "doc"
    manifest_path = tmp_path / item["id"] / "manifest.json"
    manifest_path.write_text(__import__("json").dumps(item, ensure_ascii=False), encoding="utf-8")
    store.record_use(item["id"])

    recommended = template_gallery.recommend_gallery("doc", user_root=tmp_path)
    assert recommended["id"] == item["id"]
    assert recommended["usage_count"] == 1


def test_private_ids_cannot_target_non_user_directories(tmp_path):
    store = UserGalleryStore(tmp_path / "gallery")

    assert store.delete("builtin-template") is False
    with pytest.raises(UserGalleryError, match="私人模板 ID 无效"):
        store.get("builtin-template")
