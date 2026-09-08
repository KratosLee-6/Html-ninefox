"""Extract inline JavaScript from the workbench HTML and validate it with Node.js."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "htmlninefox" / "server" / "static" / "index.html"
TEMP = ROOT / ".tmp" / "inline-js-check.js"


def main() -> None:
    node = shutil.which("node")
    if not node:
        raise SystemExit("node executable not found")
    text = HTML.read_text(encoding="utf-8")
    scripts = re.findall(
        r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not scripts:
        raise SystemExit("no inline scripts found in index.html")
    TEMP.parent.mkdir(parents=True, exist_ok=True)
    TEMP.write_text("\n;\n".join(scripts), encoding="utf-8")
    try:
        subprocess.run([node, "--check", str(TEMP)], check=True)
    finally:
        TEMP.unlink(missing_ok=True)
    print(f"inline JavaScript syntax valid: {len(scripts)} block(s)")


if __name__ == "__main__":
    main()
