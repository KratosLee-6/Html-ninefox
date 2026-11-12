"""fontsubset.py · 交付包字体子集化内嵌（v0.9.5-B，融合 guizang-design 字体工程思路）

问题：产物字体是系统字体栈（'Inter','PingFang SC',...），交付包发到没有
这些字体的机器上会 fallback 变丑。解法：交付包打 zip 时，按产物**实际
用字**把缓存的开源字体（OFL，Noto 家族）子集化成 woff 内嵌进 HTML 副本
——子集只有几十 KB，且不污染工作区原件（交付包独立副本）。

接缝纪律（与联盟路由同一套）：
  * fonttools 未装（[font] extra）或缓存无字体 → 照旧导出，报告照实说；
  * 字体文件不进 git —— `python -m htmlninefox.fontsubset fetch` 按需
    下载到 <output_root>/.settings/fonts/（jsdelivr 源，OFL 许可）；
  * 子集内嵌只发生在交付包副本上，工作区 output.html 保持原样。
"""
from __future__ import annotations

import base64
import io
import json
import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List

# 内嵌 family 前缀（注入产物 font 栈头部；产物 CSS 变量锚点由 base_css 生成，格式稳定）
EMBED_SANS = "FoxEmbed-Sans"
EMBED_SERIF = "FoxEmbed-Serif"

# 候选内置字体（OFL）：sans 配 Inter 栈、serif 配 Georgia/思源宋栈
FONT_CATALOG: List[Dict[str, str]] = [
    {"family": EMBED_SANS, "file": "NotoSansSC-Regular.woff2",
     "stack_role": "body",  # 前插进 --fox-font_body
     "source": "https://cdn.jsdelivr.net/fontsource/fonts/noto-sans-sc@latest/chinese-simplified-400-normal.woff2",
     "license": "OFL-1.1"},
    {"family": EMBED_SERIF, "file": "NotoSerifSC-Regular.woff2",
     "stack_role": "display",
     "source": "https://cdn.jsdelivr.net/fontsource/fonts/noto-serif-sc@latest/chinese-simplified-400-normal.woff2",
     "license": "OFL-1.1"},
]


def _build_var_res() -> Dict[str, re.Pattern[str]]:
    return {
        "body": re.compile(r"(--fox-font_body:\s*)([^;]+)"),
        "display": re.compile(r"(--fox-font_display:\s*)([^;]+)"),
    }


class _CharCollector(HTMLParser):
    """收集产物可见文本用字（data 节点；script/style 不算）。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.chars: set[str] = set()
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self.chars.update(data)


def extract_used_chars(html_text: str) -> str:
    """产物可见文本的实际用字（含 ASCII 基础盘）。"""
    collector = _CharCollector()
    try:
        collector.feed(html_text)
    except Exception:  # noqa: BLE001 — 解析失败按全空处理（嵌入层会跳过）
        return ""
    chars = collector.chars | set("abcdefghijklmnopqrstuvwxyz"
                                  "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    return "".join(sorted(chars))


def font_capabilities(output_root: str | Path) -> Dict[str, Any]:
    """能力探测：fonttools 可用性 + 缓存字体清单（照实报，不猜）。"""
    try:
        import fontTools.subset  # noqa: F401
        fonttools = True
    except ImportError:
        fonttools = False
    cached = []
    for entry in FONT_CATALOG:
        path = _cache_dir(output_root) / entry["file"]
        if path.is_file() and path.stat().st_size > 1024:
            cached.append({**entry, "path": str(path),
                           "bytes": path.stat().st_size})
    return {"fonttools": fonttools, "cached_fonts": cached}


def _cache_dir(output_root: str | Path) -> Path:
    return Path(output_root) / ".settings" / "fonts"


def subset_font_woff(font_path: str | Path, chars: str) -> bytes:
    """按用字子集化 → woff 字节流（zlib 压缩，fonttools 自带，无 brotli 依赖）。"""
    from fontTools.subset import Options, Subsetter, load_font, save_font
    opts = Options()
    opts.flavor = "woff"
    opts.desubroutinize = True
    font = load_font(str(font_path), opts)
    subsetter = Subsetter(opts)
    subsetter.populate(text=chars)
    subsetter.subset(font)
    buf = io.BytesIO()
    save_font(font, buf, opts)
    return buf.getvalue()


def embed_fonts_into_html(html: str, output_root: str | Path,
                          chars: str | None = None) -> tuple[str, Dict[str, Any]]:
    """把缓存字体的用字子集以 data-URI @font-face 内嵌进 HTML 文本，
    并把产物 font 栈前插内嵌 family。返回 (新 html, 报告)。

    无 fonttools / 无缓存字体 → 原样返回 + 报告 embedded=False 照实说。
    """
    caps = font_capabilities(output_root)
    report: Dict[str, Any] = {"embedded": [], "skipped": [], "chars": 0}
    if not caps["fonttools"] or not caps["cached_fonts"]:
        report["skipped"] = ["fonttools 未装（pip install 'htmlninefox[font]'）" ]
        if caps["fonttools"]:
            report["skipped"] = ["缓存无字体（python -m htmlninefox.fontsubset fetch）"]
        return html, report
    used = chars if chars is not None else extract_used_chars(html)
    if len(used) < 8:
        report["skipped"] = ["可见文本过少，跳过子集化"]
        return html, report
    report["chars"] = len(used)
    faces: List[str] = []
    var_res = _build_var_res()
    new_html = html
    for entry in caps["cached_fonts"]:
        try:
            data = subset_font_woff(entry["path"], used)
        except Exception as e:  # noqa: BLE001 — 单字体失败不拖垮交付包
            report["skipped"].append(f"{entry['family']}: {e.__class__.__name__}")
            continue
        b64 = base64.b64encode(data).decode("ascii")
        faces.append(
            f"@font-face{{font-family:'{entry['family']}';"
            f"src:url(data:font/woff;base64,{b64}) format('woff');"
            f"font-weight:400;font-display:swap;}}")
        pattern = var_res[entry["stack_role"]]
        m = pattern.search(new_html)
        if m and entry["family"] not in m.group(2):
            new_html = pattern.sub(
                lambda mm: f"{mm.group(1)}'{entry['family']}',{mm.group(2)}",
                new_html, count=1)
        report["embedded"].append({"family": entry["family"],
                                   "bytes": len(data)})
    if faces:
        style = "<style>/* v0.9.5 交付包子集字体 */\n" + "\n".join(faces) + "</style>"
        new_html = re.sub(r"<head([^>]*)>",
                          lambda hm: f"<head{hm.group(1)}>\n{style}",
                          new_html, count=1)
    report["skipped"] = report["skipped"] or []
    return new_html, report


def fetch_font(entry: Dict[str, str], output_root: str | Path,
               timeout: float = 60.0) -> Path:
    """下载单只候选字体到缓存（jsdelivr 源；网络失败抛原始异常，由 CLI 报）。"""
    out = _cache_dir(output_root) / entry["file"]
    out.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(entry["source"],
                                 headers={"User-Agent": "htmlninefox/0.9.5"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        out.write_bytes(resp.read())
    return out


def main() -> int:  # pragma: no cover — 网络入口不进 CI
    import argparse
    parser = argparse.ArgumentParser(
        description="交付包字体缓存管理（OFL 开源字体，按需下载）")
    parser.add_argument("action", choices=["fetch", "list"],
                        help="fetch=下载候选字体；list=查看缓存与能力")
    parser.add_argument("--output-root", default=None,
                        help="默认与 server 同源：~/htmlninefox-output")
    args = parser.parse_args()
    root = args.output_root or str(Path.home() / "htmlninefox-output")
    caps = font_capabilities(root)
    if args.action == "list":
        print(json.dumps(caps, ensure_ascii=False, indent=1))
        return 0
    if not caps["fonttools"]:
        print("fonttools 未装：pip install 'htmlninefox[font]'")
        return 1
    for entry in FONT_CATALOG:
        path = fetch_font(entry, root)
        print(f"cached: {path} ({path.stat().st_size} bytes, {entry['license']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
