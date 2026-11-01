"""v0.8.7 发版取证：动效层双帧对比 + 门禁/变异/联盟真回显。

    evidence-motion-early.png   生成产物首帧（墨水标题入场进行中）
    evidence-motion-settled.png 终态（显形完成、光带呼吸中）
    evidence-motion-gates.txt   pytest 动效门禁 5 条真回显
    evidence-motion-mutation.txt 变异（ambient→linear）被门禁 CAUGHT 真回显
    evidence-alliance.txt       fox alliance list 真输出（motion-design 在列）

双帧对比是动效的诚实证据：同一产物、同一视口，只有时间不同。
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from playwright.sync_api import sync_playwright  # noqa: E402

from tests.conftest import WorkbenchServer  # noqa: E402
from tests.test_server_project_api import request as api_request  # noqa: E402

OUT = ROOT / "assets" / "screenshots" / "v0.8.7"
PROMPT = "做一个智能保温杯的产品落地页：三档控温，续航两周，极简设计"


def capture_terminal_evidence() -> None:
    """门禁/变异/联盟三份真回显——文本资产，卡片终端块只能引用这里的行。"""
    gates = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_motion_quality.py",
         "-v", "--no-header", "-p", "no:cacheprovider"],
        capture_output=True, text=True)
    (OUT / "evidence-motion-gates.txt").write_text(
        gates.stdout.strip() + "\n", encoding="utf-8")

    shared = ROOT / "htmlninefox" / "generators" / "_shared.py"
    original = shared.read_text(encoding="utf-8")
    mutated = original.replace(
        "animation: fox-ambient-drift 26s ease-in-out infinite alternate;",
        "animation: fox-ambient-drift 26s linear infinite alternate;")
    assert mutated != original, "变异锚点没找到"
    try:
        shared.write_text(mutated, encoding="utf-8")
        mutation = subprocess.run(
            [sys.executable, "-m", "pytest",
             "tests/test_motion_quality.py::test_ambient_loops_are_seamless_not_linear",
             "--no-header", "-p", "no:cacheprovider"],
            capture_output=True, text=True)
    finally:
        shared.write_text(original, encoding="utf-8")
    (OUT / "evidence-motion-mutation.txt").write_text(
        mutation.stdout.strip() + "\n", encoding="utf-8")
    assert "1 failed" in mutation.stdout, "变异必须被 CAUGHT，否则取证不成立"

    alliance = subprocess.run(
        [sys.executable, "-m", "htmlninefox", "alliance", "list"],
        capture_output=True, text=True)
    (OUT / "evidence-alliance.txt").write_text(
        alliance.stdout.strip() + "\n", encoding="utf-8")
    print("terminal evidence: gates / mutation / alliance")


def capture_motion_frames() -> None:
    with WorkbenchServer(Path(tempfile.mkdtemp())) as server:
        payload, _ = api_request(server.base_url, "/api/generate", "POST",
                                 {"prompt": PROMPT, "intent": "landing",
                                  "quiet_llm": True})
        preview = server.base_url + payload["preview_url"]
        print(f"生成项目: {payload['project_name']}")

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(preview, wait_until="domcontentloaded")
            # 900ms：墨水标题（700ms）已完成；1.8s 内容安全兜底未触发——
            # 再晚滚动，卡片会被兜底直接置终态，编排中段就抓不到了
            page.wait_for_timeout(900)
            page.evaluate(
                "document.querySelectorAll('.fox-reveal')[0]"
                "?.scrollIntoView({block:'center'})")
            page.wait_for_timeout(260)   # 0.6s 编排中段（stagger 后 ~40%）
            page.screenshot(path=OUT / "evidence-motion-reveal-mid.png")
            page.wait_for_timeout(2400)
            page.screenshot(path=OUT / "evidence-motion-reveal-settled.png")
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(500)
            page.screenshot(path=OUT / "evidence-motion-settled.png")
            browser.close()
        print("shots: reveal-mid / reveal-settled / hero-settled")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    capture_terminal_evidence()
    capture_motion_frames()
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
