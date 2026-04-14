"""
YouTube サムネイル生成モジュール（1280x720px）。
ジャンル別のカラーテーマ + 大きなトピックテキスト + バッジで構成。
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from config import FONT_CANDIDATES

THUMBNAIL_WIDTH = 1280
THUMBNAIL_HEIGHT = 720

# ジャンル別グラデーションカラー (top_color, bottom_color)
_GENRE_GRADIENTS: dict[str, tuple[tuple[int, int, int], tuple[int, int, int]]] = {
    "trivia":  ((75, 0, 130),   (30, 80, 220)),
    "history": ((120, 60, 10),  (200, 130, 40)),
    "science": ((0, 100, 120),  (0, 200, 160)),
    "money":   ((0, 90, 30),    (40, 180, 60)),
    "english": ((0, 60, 160),   (30, 140, 255)),
}

# ジャンル別バッジテキスト
_GENRE_BADGES: dict[str, str] = {
    "trivia":  "衝撃の豆知識！",
    "history": "歴史の真実！",
    "science": "科学の驚き！",
    "money":   "お金の豆知識！",
    "english": "英語フレーズ！",
}


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def _make_gradient_bg(
    color_top: tuple[int, int, int],
    color_bottom: tuple[int, int, int],
) -> np.ndarray:
    arr = np.zeros((THUMBNAIL_HEIGHT, THUMBNAIL_WIDTH, 3), dtype=np.uint8)
    for y in range(THUMBNAIL_HEIGHT):
        ratio = y / THUMBNAIL_HEIGHT
        r = int(color_top[0] + (color_bottom[0] - color_top[0]) * ratio)
        g = int(color_top[1] + (color_bottom[1] - color_top[1]) * ratio)
        b = int(color_top[2] + (color_bottom[2] - color_top[2]) * ratio)
        arr[y, :] = (r, g, b)
    return arr


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    dummy = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    for char in text:
        test = current + char
        bbox = dummy.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > max_width and current:
            lines.append(current)
            current = char
        else:
            current = test
    if current:
        lines.append(current)
    return lines


def _draw_outlined_text(
    draw: ImageDraw.ImageDraw,
    pos: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: tuple[int, int, int],
    outline_color: tuple[int, int, int] = (0, 0, 0),
    outline_size: int = 6,
) -> None:
    x, y = pos
    for ox in range(-outline_size, outline_size + 1):
        for oy in range(-outline_size, outline_size + 1):
            if ox * ox + oy * oy <= outline_size * outline_size:
                draw.text((x + ox, y + oy), text, font=font, fill=outline_color)
    draw.text((x, y), text, font=font, fill=fill)


def generate_thumbnail(
    topic: str,
    output_path: Path,
    genre: str = "trivia",
) -> Path:
    """
    YouTube サムネイル画像（1280x720 JPEG）を生成する。

    Args:
        topic: 動画トピック名（大きく表示）
        output_path: 出力先パス
        genre: ジャンルキー（カラーテーマに使用）

    Returns:
        生成された画像のPath
    """
    color_top, color_bottom = _GENRE_GRADIENTS.get(genre, _GENRE_GRADIENTS["trivia"])

    # グラデーション背景
    bg_arr = _make_gradient_bg(color_top, color_bottom)
    img = Image.fromarray(bg_arr, "RGB")

    # 暗いオーバーレイでテキストを読みやすく
    overlay = Image.new("RGBA", (THUMBNAIL_WIDTH, THUMBNAIL_HEIGHT), (0, 0, 0, 90))
    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay).convert("RGB")

    draw = ImageDraw.Draw(img)

    # ── バッジ（左上） ──
    badge_text = _GENRE_BADGES.get(genre, "🔥 豆知識！")
    badge_font = _load_font(48)
    badge_bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
    badge_w = badge_bbox[2] - badge_bbox[0] + 56
    badge_h = badge_bbox[3] - badge_bbox[1] + 22
    bx, by = 50, 42
    draw.rounded_rectangle(
        [bx, by, bx + badge_w, by + badge_h],
        radius=18,
        fill=(220, 30, 30),
    )
    draw.text((bx + 28, by + 11), badge_text, font=badge_font, fill=(255, 255, 255))

    # ── メインテキスト（トピック） ──
    max_text_width = THUMBNAIL_WIDTH - 140

    # 行数に応じてフォントサイズを調整
    for font_size in (110, 88, 70, 56):
        main_font = _load_font(font_size)
        lines = _wrap_text(topic, main_font, max_text_width)
        if len(lines) <= 3:
            break

    line_h = main_font.size + 24
    total_text_h = len(lines) * line_h
    # バッジ下端 + 余白 と 下部CTA上端 の中間に配置
    y_start = (THUMBNAIL_HEIGHT - total_text_h) // 2 + 20

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=main_font)
        lw = bbox[2] - bbox[0]
        lx = (THUMBNAIL_WIDTH - lw) // 2
        _draw_outlined_text(draw, (lx, y_start), line, main_font, fill=(255, 255, 255))
        y_start += line_h

    # ── 下部 CTA ──
    cta_font = _load_font(44)
    cta_text = "▶ 知ってた？"
    cta_bbox = draw.textbbox((0, 0), cta_text, font=cta_font)
    cta_w = cta_bbox[2] - cta_bbox[0]
    draw.text(
        ((THUMBNAIL_WIDTH - cta_w) // 2, THUMBNAIL_HEIGHT - 80),
        cta_text,
        font=cta_font,
        fill=(255, 230, 0),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), "JPEG", quality=95)
    return output_path
