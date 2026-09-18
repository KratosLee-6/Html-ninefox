"""Extract inline JavaScript from the workbench HTML and validate it with Node.js."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML_FILES = [ROOT / "htmlninefox" / "server" / "static" / name
              for name in ("index.html", "motion-lab.html")]
TEMP = ROOT / ".tmp" / "inline-js-check.js"


def main() -> None:
    node = shutil.which("node")
    if not node:
        raise SystemExit("node executable not found")
    TEMP.parent.mkdir(parents=True, exist_ok=True)
    try:
        for html in HTML_FILES:
            scripts = re.findall(
                r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>",
                html.read_text(encoding="utf-8"), flags=re.IGNORECASE | re.DOTALL,
            )
            if not scripts:
                raise SystemExit(f"no inline scripts found in {html.name}")
            TEMP.write_text("\n;\n".join(scripts), encoding="utf-8")
            subprocess.run([node, "--check", str(TEMP)], check=True)
            print(f"{html.name}: inline JavaScript syntax valid: {len(scripts)} block(s)")
    finally:
        TEMP.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
