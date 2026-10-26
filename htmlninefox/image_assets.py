"""Image asset intake (v0.8.4 secondary item): inspect an upload as a
candidate asset, never pretend it carries structure.

Two honesty rules (DESIGN-REVERSE-INTAKE §4):
1. **Dimensions come from the file itself** — PNG IHDR and JPEG SOF markers
   parsed with the standard library, so `inspect_image` always answers
   "what is this and how big" with zero optional dependencies.
2. **Text content is none of our business.** A picture has no structure;
   OCR/vision transcription is a provider decision (default off, and the
   interface says so). What we add beyond dimensions is the dominant colour
   — via Pillow in the optional `[image]` extra — so the proposal layer can
   match a real asset to an image-plan slot. Without Pillow we degrade to
   dimensions only and say so.
"""

from __future__ import annotations

import io
import struct
from typing import Any


class ImageAssetError(ValueError):
    """Not an image we can read — say so, do not half-inspect it."""

    code = "image_asset_invalid"


def _png_size(raw: bytes) -> tuple[str, int, int] | None:
    if raw[:8] != b"\x89PNG\r\n\x1a\n" or raw[12:16] != b"IHDR":
        return None
    width, height = struct.unpack(">II", raw[16:24])
    return "png", width, height


def _jpeg_size(raw: bytes) -> tuple[str, int, int] | None:
    if raw[:2] != b"\xff\xd8":
        return None
    offset = 2
    while offset + 9 < len(raw):
        if raw[offset] != 0xFF:  # 找 marker
            offset += 1
            continue
        marker = raw[offset + 1]
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:  # 无长度段
            offset += 2
            continue
        (segment_length,) = struct.unpack(">H", raw[offset + 2:offset + 4])
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            height, width = struct.unpack(
                ">HH", raw[offset + 5:offset + 9])
            return "jpeg", width, height
        offset += 2 + segment_length
    return None


def inspect_image(raw: bytes) -> dict[str, Any]:
    """Inspect uploaded bytes as an asset candidate.

    Returns {format, width, height, bytes, dominant_color?, color_source}.
    `dominant_color` only appears when the optional `[image]` extra
    (Pillow) is installed; `color_source` says which path answered.
    """
    if not raw:
        raise ImageAssetError("空文件不是可用的图片资产")
    parsed = _png_size(raw) or _jpeg_size(raw)
    if parsed is None:
        raise ImageAssetError("不是可识别的图片（仅支持 PNG / JPEG）")
    fmt, width, height = parsed

    result: dict[str, Any] = {
        "format": fmt,
        "width": width,
        "height": height,
        "bytes": len(raw),
    }

    try:
        from PIL import Image  # noqa: F401  ([image] extra 探测)
    except ImportError:
        result["color_source"] = "unavailable: pip install 'htmlninefox[image]'"
        return result

    try:
        image = Image.open(io.BytesIO(raw))
        image.thumbnail((64, 64))  # 主色是粗粒度信息，64px 足够且快
        quantized = image.convert("RGB").quantize(colors=1)
        r, g, b = quantized.getpalette()[:3]
    except Exception:
        # 尺寸来自文件头，永远有效；像素解不了（截断/损坏）就如实降级，
        # 不让整次检查失败。
        result["color_source"] = "decode_failed: dimensions from header only"
        return result
    result["dominant_color"] = f"#{r:02X}{g:02X}{b:02X}"
    result["color_source"] = "pillow"
    return result
