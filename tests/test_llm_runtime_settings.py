"""Runtime AI settings call an OpenAI-compatible endpoint without LiteLLM."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from htmlninefox.llm import HtmlNineFoxRouter, runtime_config_from_settings


def test_runtime_settings_use_direct_openai_compatible_http():
    captured = {}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            captured["path"] = self.path
            captured["authorization"] = self.headers.get("Authorization")
            captured["body"] = json.loads(self.rfile.read(length).decode("utf-8"))
            response = json.dumps({
                "choices": [{"message": {"content": "OK"}}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 1},
            }).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        config = runtime_config_from_settings({
            "provider": "openai-compatible",
            "model": "demo-model",
            "base_url": f"http://127.0.0.1:{server.server_address[1]}/v1",
            "api_key": "local-secret",
        })
        router = HtmlNineFoxRouter(config=config)
        result = router.call("只回复 OK", use_cache=False, max_tokens=16)
        assert result.text == "OK"
        assert captured["path"] == "/v1/chat/completions"
        assert captured["authorization"] == "Bearer local-secret"
        assert captured["body"]["model"] == "demo-model"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
