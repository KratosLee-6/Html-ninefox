"""Image asset intake gates (v0.8.4 secondary item).

PNG fixture is a hand-built IHDR (stdlib only). JPEG fixture is produced
with Pillow — deliberately a dev dependency that does not skip on
ImportError (same discipline as cryptography in test_ssrf_tls_pinning):
the dominant-colour path is exactly what CI must see running.
"""

from __future__ import annotations

import io
import struct

import pytest

from htmlninefox.image_assets import ImageAssetError, inspect_image

PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n"
    + struct.pack(">I", 13) + b"IHDR"
    + struct.pack(">IIBBBBB", 7, 5, 8, 2, 0, 0, 0)
    + b"\x00\x00\x00\x00" + b"\x00\x00\x00\x00"  # 占位 CRC（inspect 不校验）
    + b"\x00\x00\x00\x00IEND\xaeB`\x82")


def build_jpeg() -> bytes:
    from PIL import Image
    buffer = io.BytesIO()
    Image.new("RGB", (40, 20), (36, 62, 143)).save(buffer, format="JPEG")
    return buffer.getvalue()


def test_png_dimensions_from_the_header_alone():
    result = inspect_image(PNG_BYTES)

    assert result["format"] == "png"
    assert (result["width"], result["height"]) == (7, 5)
    assert result["bytes"] == len(PNG_BYTES)


def test_undecodable_pixels_degrade_to_dimensions_honestly():
    """头部合法但无像素数据：尺寸照答，主色如实说「解不了」，不报错。"""
    result = inspect_image(PNG_BYTES)

    assert result["color_source"].startswith("decode_failed")
    assert "dominant_color" not in result


def test_jpeg_dimensions_and_dominant_color():
    result = inspect_image(build_jpeg())

    assert result["format"] == "jpeg"
    assert (result["width"], result["height"]) == (40, 20)
    # JPEG 有损，主色允许 ±3/255 漂移；纯色图的主色必须落在填充色近旁
    dominant = result["dominant_color"]
    r, g, b = (int(dominant[i:i + 2], 16) for i in (1, 3, 5))
    assert abs(r - 36) <= 3 and abs(g - 62) <= 3 and abs(b - 143) <= 3
    assert result["color_source"] == "pillow"


def test_unknown_bytes_say_so():
    with pytest.raises(ImageAssetError) as excinfo:
        inspect_image(b"GIF89a not supported on purpose")
    assert "PNG / JPEG" in str(excinfo.value)


def test_empty_upload_says_so():
    with pytest.raises(ImageAssetError):
        inspect_image(b"")
