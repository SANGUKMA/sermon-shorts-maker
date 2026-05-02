"""제목 / 교회명 이미지 (PIL)

자동 폰트 축소 — 제목 길이가 길면 maxwidth에 맞춰 자동으로 사이즈 줄임.
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# 9:16 + 1:1 레이아웃
W = 1080
TOP_BAR_H = 560
BOTTOM_BAR_H = 280
NAVY_RGB = (15, 37, 87)
WHITE_RGB = (255, 255, 255)
DEEP_YELLOW_RGB = (240, 196, 25)

TITLE_FONT_SIZE_MAX = 120
SUBTITLE_FONT_SIZE_MAX = 85
CHURCH_FONT_SIZE_MAX = 60


def _fit_font_size(draw, text: str, max_size: int, max_width: int,
                    font_path: str) -> int:
    """텍스트가 max_width를 넘지 않는 가장 큰 폰트 크기."""
    for size in range(max_size, 30, -2):
        font = ImageFont.truetype(font_path, size)
        bb = draw.textbbox((0, 0), text, font=font)
        if (bb[2] - bb[0]) <= max_width:
            return size
    return 30


def render_title_image(
    title_line1: str,
    title_line2: str,
    out_path: Path,
    font_path: str,
):
    """상단 제목: 1080×TOP_BAR_H 네이비, 2줄 (흰색 + 진한 노란색)"""
    img = Image.new("RGB", (W, TOP_BAR_H), NAVY_RGB)
    d = ImageDraw.Draw(img)

    max_text_w = W - 80
    title_size = _fit_font_size(d, title_line1, TITLE_FONT_SIZE_MAX, max_text_w, font_path)
    sub_size = _fit_font_size(d, title_line2, SUBTITLE_FONT_SIZE_MAX, max_text_w, font_path)

    f1 = ImageFont.truetype(font_path, title_size)
    f2 = ImageFont.truetype(font_path, sub_size)

    bb1 = d.textbbox((0, 0), title_line1, font=f1)
    bb2 = d.textbbox((0, 0), title_line2, font=f2)
    h1 = bb1[3] - bb1[1]
    h2 = bb2[3] - bb2[1]
    gap = 40
    block_h = h1 + gap + h2
    y0 = (TOP_BAR_H - block_h) // 2 - bb1[1]

    tw1 = bb1[2] - bb1[0]
    d.text(((W - tw1) / 2 - bb1[0], y0),
           title_line1, font=f1, fill=WHITE_RGB)
    tw2 = bb2[2] - bb2[0]
    d.text(((W - tw2) / 2 - bb2[0], y0 + h1 + gap - bb2[1] + bb1[1]),
           title_line2, font=f2, fill=DEEP_YELLOW_RGB)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out_path))
    return title_size, sub_size


def render_church_image(
    church_name: str,
    out_path: Path,
    font_path: str,
):
    """하단 교회명: 1080×BOTTOM_BAR_H 네이비, 1/2 크기 흰색"""
    img = Image.new("RGB", (W, BOTTOM_BAR_H), NAVY_RGB)
    d = ImageDraw.Draw(img)

    max_text_w = W - 80
    size = _fit_font_size(d, church_name, CHURCH_FONT_SIZE_MAX, max_text_w, font_path)

    f = ImageFont.truetype(font_path, size)
    bb = d.textbbox((0, 0), church_name, font=f)
    tw = bb[2] - bb[0]
    th = bb[3] - bb[1]
    x = (W - tw) / 2 - bb[0]
    y = (BOTTOM_BAR_H - th) / 2 - bb[1]
    d.text((x, y), church_name, font=f, fill=WHITE_RGB)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out_path))
    return size
