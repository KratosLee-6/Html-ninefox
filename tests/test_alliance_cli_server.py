"""测试联盟路由 + CLI 全命令冒烟 + Web API"""

import json
import threading
import urllib.request
from pathlib import Path

from click.testing import CliRunner

from htmlninefox import __version__
from htmlninefox.alliance.router import AllianceRouter
from htmlninefox.cli import main

RUNNER = CliRunner()


class TestAllianceRouter:
    def test_seeds_loaded(self):
        r = AllianceRouter()
        names = set(r.skills)
        assert {"guizang-ppt", "huashu-design", "archify"} <= names

    def test_route_fallback(self):
        r = AllianceRouter()
        d = r.route({}, "deck")
        assert d["skill"] == "guizang-ppt" and d["decision"] == "fallback"

    def test_route_local_when_no_skill(self):
        r = AllianceRouter()
        d = r.route({}, "dashboard")
        assert d["decision"] == "local" and d["skill"] is None

    def test_route_unknown_skill(self):
        r = AllianceRouter()
        d = r.route({}, "deck", skill_override="nonexistent")
        assert d["decision"] == "unknown-skill"

    def test_user_manifest_overrides(self, tmp_path, monkeypatch):
        user_dir = tmp_path / "alliance"
        user_dir.mkdir()
        (user_dir / "guizang-ppt.yaml").write_text(
            "name: guizang-ppt\nversion: 9.9.9\nintents: [deck]\n"
            "python_module: guizang_ppt\n", encoding="utf-8")
        monkeypatch.setattr("htmlninefox.alliance.router._USER_DIR", user_dir)
        r = AllianceRouter()
        assert r.skills["guizang-ppt"]["version"] == "9.9.9"
        assert r.skills["guizang-ppt"]["_source"] == "user"


class TestCli:
    def test_version(self):
        assert RUNNER.invoke(main, ["--version"]).exit_code == 0

    def test_expert_offline(self, tmp_path):
        res = RUNNER.invoke(main, ["expert", "做一个 SaaS 落地页，品牌「狐构」",
                                   "--quiet-llm", "-o", str(tmp_path)])
        assert res.exit_code == 0, res.output
        assert "landing" in res.output

    def test_expert_type_override(self, tmp_path):
        res = RUNNER.invoke(main, ["expert", "说点什么", "--type", "poster",
                                   "--quiet-llm", "-o", str(tmp_path)])
        assert res.exit_code == 0 and "poster" in res.output

    def test_expert_empty_prompt(self, tmp_path):
        res = RUNNER.invoke(main, ["expert", " ", "-o", str(tmp_path)])
        assert res.exit_code == 2

    def test_feedback_loop(self, tmp_path):
        RUNNER.invoke(main, ["expert", "做一个落地页", "--quiet-llm", "-o", str(tmp_path)])
        work = sorted(tmp_path.glob("html9n-*"))[-1]
        res = RUNNER.invoke(main, ["feedback", "--project", str(work),
                                   "--note", "颜色深一点"])
        assert res.exit_code == 0, res.output
        assert (work / "revisions" / "rev1.html").exists()

    def test_feedback_vague_exits_2(self, tmp_path):
        RUNNER.invoke(main, ["expert", "做一个落地页", "--quiet-llm", "-o", str(tmp_path)])
        work = sorted(tmp_path.glob("html9n-*"))[-1]
        res = RUNNER.invoke(main, ["feedback", "--project", str(work), "--note", "不好看"])
        assert res.exit_code == 2

    def test_template_list(self):
        res = RUNNER.invoke(main, ["template"])
        assert res.exit_code == 0 and "linear-light" in res.output

    def test_alliance_list(self):
        res = RUNNER.invoke(main, ["alliance", "list"])
        assert res.exit_code == 0 and "guizang-ppt" in res.output

    def test_brief_list(self):
        assert RUNNER.invoke(main, ["brief", "list"]).exit_code == 0


class TestWebApi:
    @classmethod
    def setup_class(cls):
        import tempfile
        import htmlninefox.server.app as mod
        cls.out_root = Path(tempfile.mkdtemp()) / "output"
        mod._OUTPUT_ROOT = cls.out_root
        cls.out_root.mkdir(parents=True, exist_ok=True)
        cls.server = threading.Thread(
            target=lambda: mod.ThreadingHTTPServer(
                ("127.0.0.1", 8631), mod._Handler).serve_forever(), daemon=True)
        cls.server.start()
        cls.base = "http://127.0.0.1:8631"

    def _get(self, path):
        return urllib.request.urlopen(self.base + path, timeout=10)

    def _post(self, path, data, expect=200):
        req = urllib.request.Request(self.base + path,
                                     data=json.dumps(data).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        try:
            return json.loads(urllib.request.urlopen(req, timeout=60).read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            assert e.code == expect, e.read().decode("utf-8")
            return json.loads(e.read().decode("utf-8"))

    def test_health_and_ui(self):
        h = json.loads(self._get("/api/health").read().decode("utf-8"))
        assert h["ok"] and h["version"] == __version__
        assert h["api_version"] == "v1"
        assert h["distribution"] == "python"
        ui = self._get("/").read().decode("utf-8")
        assert "Html" in ui and "manifest.webmanifest" in ui and "/canvas-engine.js" in ui
        assert "pixel-paper" in ui and "/logo-mark.svg" in ui
        engine = self._get("/canvas-engine.js").read().decode("utf-8")
        productivity = self._get("/canvas-productivity.js").read().decode("utf-8")
        assert "snapNode" in engine and "nearestInput" in engine
        assert "commitHistory" in productivity and "renderMinimap" in productivity

    def test_pwa_assets_and_capabilities(self):
        manifest = json.loads(self._get("/manifest.webmanifest").read().decode("utf-8"))
        assert manifest["display"] == "standalone" and manifest["start_url"].startswith("/")
        assert manifest["theme_color"] == "#173C8F"
        assert self._get("/logo-mark.svg").headers["Content-Type"].startswith("image/svg+xml")
        assert self._get("/logo-horizontal.svg").headers["Content-Type"].startswith("image/svg+xml")
        service_worker = self._get("/sw.js")
        assert service_worker.headers["Service-Worker-Allowed"] == "/"
        assert "htmlninefox-shell" in service_worker.read().decode("utf-8")
        capabilities = json.loads(self._get("/api/capabilities").read().decode("utf-8"))
        assert capabilities["api_version"] == "v1"
        assert capabilities["clients"]["pwa"] == "ready"
        assert capabilities["clients"]["windows"] == "beta"
        assert capabilities["clients"]["linux"] == "beta"
        assert capabilities["offline"]["workspace"] is True

    def test_generate_feedback_loop(self):
        d = self._post("/api/generate", {"prompt": "做一个深色数据看板", "quiet_llm": True})
        assert d["ok"] and d["intent"] == "dashboard"
        fb = self._post("/api/feedback", {"project": d["project"], "note": "颜色深一点"})
        assert fb["ok"] and fb["revision"] == 1
        html = self._get(d["preview_url"]).read().decode("utf-8")
        assert html.startswith("<!doctype html>")

    def test_generate_empty_prompt_400(self):
        self._post("/api/generate", {"prompt": ""}, expect=400)

    def test_projects_listed(self):
        items = json.loads(self._get("/api/projects").read().decode("utf-8"))["items"]
        assert any(i["intent"] == "dashboard" for i in items)
