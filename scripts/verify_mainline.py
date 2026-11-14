"""verify_mainline.py · 0.9.x 主线功能可用性巡检（真实 serve + 离线规则引擎）

测试套件绿 ≠ 真实服务可用。本脚本起真实 server（不配任何密钥，纯规则引擎），
对当前 main 的核心功能逐项真链验证，输出 PASS/FAIL 矩阵；任何 FAIL 退出码 1。

覆盖：health/capabilities · workflows(0.9.4) · analyze(tone+motion+core_message,
0.9.1/0.9.2) · tone 非法 400 · generate(tone+workflow 真产物) · recipe-run 徽章与
剧本留痕(0.9.1/0.9.4) · feedback hex → OKLCH 收域(0.9.5) · voice-profile learn(0.9.3)
· polish-slots 无 AI 照实说(0.9.2) · 画廊/模板 · PDF 导出 · **交付包字体子集
@font-face 实证(0.9.5 挂账收尾)**。

    python -I scripts/verify_mainline.py [--port 8633] [--keep]
"""
from __future__ import annotations

import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

RESULTS: list[tuple[str, str, str]] = []  # (item, status, note)


def check(item: str, fn) -> bool:
    try:
        note = fn()
        RESULTS.append((item, "PASS", str(note or "")))
        return True
    except Exception as error:  # noqa: BLE001
        RESULTS.append((item, "FAIL", f"{error.__class__.__name__}: {error}"))
        return False


class Api:
    def __init__(self, base: str) -> None:
        self.base = base

    def get(self, path: str, timeout: float = 30.0):
        with urllib.request.urlopen(self.base + path, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))

    def post(self, path: str, body: dict, timeout: float = 180.0):
        req = urllib.request.Request(
            self.base + path, data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8")), r.status
        except urllib.error.HTTPError as error:
            return json.loads(error.read().decode("utf-8")), error.code


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8633)
    parser.add_argument("--keep", action="store_true", help="保留巡检生成的项目")
    args = parser.parse_args()
    port = args.port
    base = f"http://127.0.0.1:{port}"

    def wait_job(job_id: str, timeout_s: float = 300.0) -> dict:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            job = api.get(f"/api/jobs/{job_id}")
            if job.get("status") in ("done", "succeeded", "completed"):
                return job
            if job.get("status") in ("failed", "error"):
                raise AssertionError(f"job 失败: {str(job)[:200]}")
            time.sleep(2)
        raise AssertionError(f"job 超时 {timeout_s}s: {job_id}")

    from htmlninefox.fontsubset import FONT_CATALOG, fetch_font

    proc = subprocess.Popen(
        [sys.executable, "-I", "-m", "htmlninefox", "serve",
         "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    api = Api(base)
    try:
        for _ in range(60):
            try:
                if api.get("/api/health", timeout=2).get("ok"):
                    break
            except Exception:
                time.sleep(1)
        else:
            raise SystemExit("server not healthy in 60s")

        project_name = ""

        # 1. 健康与能力
        def _health():
            h = api.get("/api/health")
            assert h.get("ok") or h.get("api_version"), h
            caps = api.get("/api/capabilities")
            assert caps.get("features"), f"capabilities 无 features: {caps}"
            return f"api_version={caps.get('api_version')} · features={len(caps.get('features', []))}"
        check("01 health + capabilities", _health)

        # 2. 工作流剧本（0.9.4）
        def _workflows():
            data = api.get("/api/workflows")
            ids = [w["id"] for w in data.get("workflows", [])]
            assert len(ids) == 6, f"剧本数量 {len(ids)}"
            one = api.get("/api/workflows/one-article-three-outputs")
            abilities = {s["ability"] for s in one["workflow"]["steps"]}
            assert abilities <= {"generate", "intake", "adopt", "feedback",
                                 "export"}, abilities
            return f"6 条 + ability 白名单 ✓"
        check("02 workflows 六条剧本 + 详情真链 (0.9.4)", _workflows)

        # 3. analyze：tone + workflow → motion/理由/core_message（0.9.1/0.9.2）
        analyze_payload = {
            "prompt": "做一个面向开发者的性能监控看板，深色，强调数据密度",
            "tone": "vibrant",
            "workflow": "one-article-three-outputs",
        }

        def _analyze():
            data, code = api.post("/api/analyze", analyze_payload)
            assert code == 200, (code, data)
            assert data.get("motion"), "motion 原型缺失"
            assert data.get("style_reason"), "推荐理由缺失"
            assert data.get("core_message"), "core_message 缺失 (0.9.2)"
            return f"motion={data['motion'].get('id', data['motion']) if isinstance(data['motion'], dict) else data['motion']}"
        check("03 analyze tone+workflow → 动效/理由/core_message", _analyze)

        # 4. tone 非法 400（0.9.1 校验）
        def _tone_invalid():
            data, code = api.post("/api/analyze", {**analyze_payload, "tone": "霓虹辣妹"})
            assert code == 400, (code, data)
            return "400 tone_invalid ✓"
        check("04 analyze 非法 tone → 400", _tone_invalid)

        # 5. generate 真产物（tone+workflow 进产物）
        def _generate():
            nonlocal project_name
            data, code = api.post("/api/generate", analyze_payload, timeout=300)
            assert code == 200 and data.get("ok"), (code, str(data)[:200])
            project_name = data.get("project") or (data.get("result") or {}).get("project") or ""
            assert project_name, f"无项目名: {str(data)[:200]}"
            out = Path.home() / "htmlninefox-output" / Path(project_name).name / "output.html"
            assert out.is_file(), f"产物不存在 {out}"
            html = out.read_text(encoding="utf-8")
            assert "fox-" in html, "动效层缺失"
            return f"project={Path(project_name).name}"
        check("05 generate tone+workflow → 真产物落盘", _generate)

        # 6. recipe-run 徽章与剧本留痕（0.9.1/0.9.4）
        def _recipe():
            name = Path(project_name).name
            data = api.get(f"/api/projects/{name}/recipe-run")
            stages = data.get("stages") or []
            assert len(stages) >= 4, f"stages={len(stages)}"
            blob = json.dumps(data, ensure_ascii=False)
            assert "one-article-three-outputs" in blob, "剧本未进时间线"
            return f"{len(stages)} 段 + 剧本留痕 ✓"
        check("06 recipe-run 时间线 + 剧本留痕", _recipe)

        # 7. feedback hex → OKLCH 收域（0.9.5 真链）
        def _feedback_constraint():
            name = Path(project_name).name
            data, code = api.post("/api/feedback", {
                "project": name, "note": "主色改成 #00FF00"})
            assert code == 200 and data.get("ok"), (code, str(data)[:200])
            out = (Path.home() / "htmlninefox-output" / name / "output.html")
            html = out.read_text(encoding="utf-8")
            assert "#00FF00" not in html.upper() or "--fox-primary:#00FF00" not in html.replace(" ", "").lower(), \
                "荧光绿原样进产物——收域链断了"
            from htmlninefox.generators._oklch import hex_to_oklch
            import re as _re
            m = _re.search(r"--fox-primary:\s*(#[0-9A-Fa-f]{6})", html)
            assert m, "产物缺 --fox-primary"
            l, c, h = hex_to_oklch(m.group(1))
            assert l < 0.75, f"明度未收域 L={l:.2f}"
            return f"primary={m.group(1)} L={l:.2f}（收域 ✓）"
        check("07 feedback hex → OKLCH 收域进产物 (0.9.5)", _feedback_constraint)

        # 8. voice-profile learn（0.9.3）
        def _voice():
            api.post("/api/voice-profile/clear", {})
            data, code = api.post("/api/voice-profile/learn", {"samples": [
                "狐构的交付速度很快。狐构交付的内容可以直接用。",
                "我们狐构一向把日期盯得死。狐构说话算数。",
            ]})
            assert code == 200 and data.get("ok"), (code, str(data)[:200])
            profile = api.get("/api/voice-profile").get("profile") or {}
            entries = profile.get("entries") or {}
            kinds = [k for k, v in entries.items() if v]
            assert kinds, f"档案空: {str(profile)[:150]}"
            return f"特征类 {kinds}（≥2 证据入档 ✓）"
        check("08 voice-profile learn ≥2 证据入档 (0.9.3)", _voice)

        # 9. polish-slots 无 AI 照实说（0.9.2 诚实降级）
        def _polish():
            data, code = api.post("/api/polish-slots", {
                "prompt": "做一个开发者看板",
                "slots": {"headline": "性能监控一屏尽览", "cta": "立即接入"}})
            assert code == 200, (code, str(data)[:200])
            assert data.get("available") is False, data
            assert data.get("reason"), "降级原因缺失"
            return "available=false + 中文原因 ✓"
        check("09 polish-slots 无密钥 → 照实说 available=false", _polish)

        # 10. 画廊与模板
        def _gallery():
            g = api.get("/api/gallery")
            items = g.get("items") or g.get("templates") or []
            assert len(items) >= 10, len(items)
            t = api.get("/api/templates")
            assert t.get("ok", True), t
            return f"画廊 {len(items)} 张"
        check("10 画廊 10 张 + 模板清单", _gallery)

        # 11. PDF 导出真链（异步 job → 轮询）
        def _export_pdf():
            name = Path(project_name).name
            data, code = api.post("/api/exports", {
                "project_name": name, "format": "pdf", "scope": "auto",
                "paper": "A4", "landscape": False}, timeout=60)
            assert code in (200, 202), (code, str(data)[:200])
            if code == 202:
                job = wait_job(data["job"]["id"])
                result = job.get("result") or {}
            else:
                result = data
            files = result.get("files") or []
            export_id = result.get("export_id") or ""
            root = Path.home() / "htmlninefox-output" / name / "exports" / export_id
            assert export_id and any((root / f["name"]).is_file() for f in files), \
                (export_id, files)
            return f"{export_id[:18]}… {len(files)} 文件"
        check("11 PDF 导出真链（异步 job，playwright chromium）", _export_pdf)

        # 12. 交付包 + 字体子集 @font-face（0.9.5 挂账收尾）
        def _bundle_fonts():
            name = Path(project_name).name
            entry = dict(FONT_CATALOG[0])
            entry["source"] = entry["source"].replace(
                "cdn.jsdelivr.net", "unpkg.com").replace(
                "fontsource/fonts", "npm/@fontsource/noto-sans-sc@5.0.18/files")
            try:
                fetch_font(entry, Path.home() / "htmlninefox-output", timeout=45)
            except Exception as error:  # noqa: BLE001
                if not any((Path.home() / "htmlninefox-output" / ".settings" / "fonts").glob("*.woff2")):
                    raise
            data, code = api.post("/api/exports/bundle", {"project_name": name},
                                  timeout=60)
            assert code in (200, 202), (code, str(data)[:200])
            if code == 202:
                job = wait_job(data["job"]["id"])
                data = job.get("result") or {}
            assert data.get("ok"), str(data)[:200]
            fonts = data.get("fonts") or {}
            assert fonts.get("embedded"), f"字体内嵌报告空: {fonts}"
            zip_path = Path(data["zip"])
            assert zip_path.is_file(), zip_path
            with zipfile.ZipFile(zip_path) as zf:
                html = zf.read("output.html").decode("utf-8")
            assert "@font-face" in html and "data:font/woff;base64," in html, \
                "交付包 zip 内无子集字体"
            sizes = ", ".join(f"{e['family']} {e['bytes'] // 1024}KB"
                              for e in fonts["embedded"])
            return f"fonts=[{sizes}], zip {zip_path.stat().st_size // 1024}KB 内含 @font-face ✓"
        check("12 交付包字体子集 @font-face 实证 (0.9.5 挂账收尾)", _bundle_fonts)

    finally:
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                       capture_output=True)

    print()
    fails = 0
    for item, status, note in RESULTS:
        if status == "FAIL":
            fails += 1
        print(f"{item}  [{status}]  {note}")
    print(f"\n== {len(RESULTS) - fails}/{len(RESULTS)} PASS ==")
    if not args.keep and project_name:
        import shutil
        target = Path.home() / "htmlninefox-output" / Path(project_name).name
        if target.is_dir():
            shutil.rmtree(target, ignore_errors=True)
        print("(巡检项目已清理；--keep 保留)")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
