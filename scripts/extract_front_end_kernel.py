"""Move the inline front-end kernel out of index.html, byte for byte.

The whole shared kernel — api, flash, select, timeline, fitAll, the inspector,
the palette — lives in one 81k inline <script> inside index.html, and the
twelve external .js files call into it as bare globals. That is the actual
shape of C7: the front end cannot be unit tested because its core is trapped
in HTML.

The move itself is mechanical, and mechanically verifying it is the point:
this script asserts the extracted text is character-identical to what was
inside the <script> tags. An 81k move reviewed by eye is not reviewable, so
the check is done by the machine.

It also refuses to run twice — double extraction would find a different
block and quietly produce a second copy.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "htmlninefox" / "server" / "static" / "index.html"
TARGET = INDEX.parent / "fox-core.js"

INLINE = re.compile(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", re.S)

BANNER = """/* fox-core.js · front-end kernel, extracted from index.html verbatim
 *
 * Do not "tidy" this file. Every character matters: it was moved out of an
 * inline <script> so that tests can load it, and the move was verified
 * byte-for-byte. Behaviour must stay identical, so any edit here is a
 * behaviour change until proven otherwise by tests/test_frontend_kernel_loadable.py
 * and the mutation run in scripts/mutate_frontend_kernel_gates.py.
 *
 * Sections, in order: state & constants, camera, nodes, edges, groups,
 * workspaces, inspector, palette, recipe progress, data loading & init.
 */
"""


def main() -> int:
    if TARGET.exists():
        print(f"refusing to run twice: {TARGET.name} already exists")
        print("if the page is broken, restore index.html from git first")
        return 1

    html = INDEX.read_text(encoding="utf-8")
    blocks = list(INLINE.finditer(html))
    if len(blocks) != 2:
        print(f"expected 2 inline blocks, found {len(blocks)}; "
              f"index.html changed — re-read before moving anything")
        return 1

    block = blocks[1]
    body = block.group(1)
    if len(body) < 40000:
        print(f"block 2 is only {len(body)} chars; not the kernel, aborting")
        return 1

    for required in ("function api(", "function flash(", "function select(",
                     "function timeline(", "function fitAll("):
        if required not in body:
            print(f"block 2 does not define {required}; aborting")
            return 1

    new_html = html[:block.start()] + '<script src="/fox-core.js"></script>' \
        + html[block.end():]

    # Byte-level proof, before anything is written.
    if len(new_html) >= len(html):
        print("replacement did not shrink the document; aborting")
        return 1

    INDEX.write_text(new_html, encoding="utf-8", newline="")
    TARGET.write_text(BANNER + body, encoding="utf-8", newline="")

    # Verify by re-reading both files from disk, not by trusting the writes.
    check = INDEX.read_text(encoding="utf-8")
    written = TARGET.read_text(encoding="utf-8")
    if '<script src="/fox-core.js"></script>' not in check:
        print("index.html does not reference fox-core.js")
        return 1
    if written[len(BANNER):] != body:
        print("fox-core.js content does not match the original inline body")
        return 1
    if INLINE.search(check) and len(list(INLINE.finditer(check))) != 1:
        print("unexpected number of inline blocks remain in index.html")
        return 1

    print(f"moved {len(body)} chars "
          f"({body.count(chr(10)) + 1} lines) out of index.html")
    print(f"  index.html: {len(html)} -> {len(check)} chars")
    print(f"  {TARGET.name}: {len(written)} chars "
          f"(banner {len(BANNER)} + body {len(body)})")
    print("\nrun next: python -m pytest tests -q -p no:cacheprovider")
    print("and:        python e2e_verify.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
