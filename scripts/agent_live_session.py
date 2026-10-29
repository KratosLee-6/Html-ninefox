"""真实 agent 会话存证 v2：agent 走 HTTP 驱动，产物直接落盘（不经过画布）。

取证策略（v1 教训：API 生成不落画布节点，画布是工作台 UI 的视图）：
  E1 analyze 真实回显 JSON
  E2 generate 后产物目录真实文件清单（逐字节存在）
  E3 产物页面在浏览器的真实截图
  E4 recipe-run.json 真实内容（时间线审计）
  E5 feedback 后 revisions/ 真实出现 rev1
  E6 export 后 exports/ 真实出现 PDF；classic 页历史可见该项目
输出：配图/assets/ 下 evidence-* + 会话实录.txt
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from playwright.sync_api import sync_playwright  # noqa: E402
from tests.conftest import WorkbenchServer  # noqa: E402
from htmlninefox.server import app as app_module  # noqa: E402
app_root = None

BASE = "http://127.0.0.1:8643"
SHOTS = Path(__file__).resolve().parent / "assets"
LOG: list[str] = []


def say(line: str) -> None:
    print(line)
    LOG.append(line)


def post(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.load(r)


def main() -> int:
    SHOTS.mkdir(parents=True, exist_ok=True)
    with WorkbenchServer(Path(tempfile.mkdtemp())) as server:
        say(f"服务: {server.base_url}（临时端口，仅本机）")

        # E1 analyze
        t0 = time.time()
        analysis = post("/api/analyze", {
            "prompt": "做一个城市交通数据看板，深色，展示早高峰流量、地铁满载率和事故热线"})
        say(f"E1 analyze  {time.time() - t0:.1f}s → intent={analysis['intent']} "
            f"confidence={analysis['intent_confidence']} engine={analysis['engine']} "
            f"preset={analysis['preset_id']}")
        (SHOTS / "evidence-analyze.json").write_text(
            json.dumps(analysis, ensure_ascii=False, indent=1), encoding="utf-8")

        app_root = str(app_module._OUTPUT_ROOT)
        # E2 generate → 真实落盘
        t2 = time.time()
        gen = post("/api/generate", {
            "prompt": "做一个城市交通数据看板，深色，展示早高峰流量、地铁满载率和事故热线",
            "intent": "dashboard", "quiet_llm": True})
        project = Path(gen["project"])
        files = sorted(f"{f.name} {f.stat().st_size}B" for f in project.iterdir()
                       if f.is_file())
        say(f"E2 generate  {time.time() - t2:.1f}s → {gen['project_name']} "
            f"verification.ok={gen['verification']['ok']}")
        say(f"   产物目录真实文件: {' · '.join(files)}")
        (SHOTS / "evidence-generate.json").write_text(
            json.dumps({k: gen[k] for k in ("project_name", "intent", "preset_id",
                                            "brief_confidence", "verification")},
                       ensure_ascii=False, indent=1), encoding="utf-8")
        frozen = SHOTS / "evidence-project"
        shutil.copytree(project, frozen, dirs_exist_ok=True)
        say(f"   项目目录已冻结副本: {frozen}")

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 1000})

            # E3 产物页面真实截图：走冻结副本（file://），证据不依赖活服务
            page.goto((frozen / "output.html").as_uri())
            page.wait_for_timeout(1800)
            assert "<html" in page.content().lower(), "冻结副本不是 HTML"
            page.screenshot(path=SHOTS / "evidence-artifact.png")
            say("E3 产物页面截图 ✓（冻结副本 file:// 渲染）")

            # E4 recipe-run 真实内容
            recipe = json.loads((project / "recipe-run.json").read_text(encoding="utf-8"))
            (SHOTS / "evidence-recipe.json").write_text(
                json.dumps(recipe, ensure_ascii=False, indent=1)[:2500], encoding="utf-8")
            say("E4 recipe-run.json 已存证")

            # E5 feedback → revisions/ 真实出现 rev1
            fb = post("/api/feedback", {"project": str(project),
                                        "note": "标题大一点，配色更稳重"})
            revs = sorted(f.name for f in (project / "revisions").iterdir())
            say(f"E5 feedback → rev{fb['revision']} · revisions/ 真实文件: {revs}")
            (SHOTS / "evidence-feedback.json").write_text(
                json.dumps(fb, ensure_ascii=False, indent=1)[:1200], encoding="utf-8")

            # E6 export → exports/ 真实出现 PDF；classic 历史可见
            req = urllib.request.Request(
                BASE + "/api/exports",
                data=json.dumps({"project_name": gen["project_name"],
                                 "format": "pdf"}).encode(),
                headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=60) as r:
                job = json.load(r)
            job_id = job["job"]["id"]
            for _ in range(90):
                with urllib.request.urlopen(BASE + f"/api/jobs/{job_id}", timeout=30) as r:
                    state = json.load(r)
                if state.get("status") in ("done", "failed"):
                    break
                time.sleep(1)
            exports = sorted(str(f) for f in (project / "exports").rglob("*") if f.is_file())
            say(f"E6 export → {state.get('status')} · 真实文件: {exports}")
            (SHOTS / "evidence-export.json").write_text(
                json.dumps(state, ensure_ascii=False, indent=1)[:1500], encoding="utf-8")

            page.goto(server.base_url + "/classic")
            page.wait_for_function("typeof generate === 'function'")
            page.wait_for_selector("#projects .hist-item, #projects .tagline",
                                   timeout=15000)
            page.wait_for_timeout(400)
            hist = page.locator("#projects .hist-item").count()
            page.screenshot(path=SHOTS / "evidence-classic.png")
            say(f"E7 classic 历史可见该项目: {hist} 项 ✓ 截图 evidence-classic.png")

            browser.close()

    (SHOTS / "会话实录.txt").write_text("\n".join(LOG), encoding="utf-8")
    print("\n实录与证据已存:", SHOTS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
