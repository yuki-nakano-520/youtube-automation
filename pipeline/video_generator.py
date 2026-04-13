"""
YouTube Shorts動画生成モジュール。
- VOICEVOXタイミングデータを使った字幕同期
- Pexels背景動画 or アニメーショングラデーション背景
- 大きく中央に字幕テキスト表示
"""

import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import PIL.Image

# Pillow 10以降でANTIALIASが削除されたためMoviePy 1.xとの互換パッチ
if not hasattr(PIL.Image, "ANTIALIAS"):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from moviepy.editor import (
    AudioFileClip,
    ColorClip,
    CompositeVideoClip,
    ImageClip,
    VideoFileClip,
    concatenate_audioclips,
)
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from config import (
    ACCENT_COLOR,
    BACKGROUND_COLOR,
    BODY_FONT_SIZE,
    FONT_CANDIDATES,
    SHADOW_COLOR,
    TEXT_COLOR,
    TOPIC_FONT_SIZE,
    VIDEO_FPS,
    VIDEO_HEIGHT,
    VIDEO_WIDTH,
)
from pipeline.voice_generator import VoiceResult


# ──────────────────────────────────────────
# データ構造
# ──────────────────────────────────────────

@dataclass
class SubtitleEntry:
    text: str
    start: float
    end: float


# ──────────────────────────────────────────
# フォント
# ──────────────────────────────────────────

_font_cache: dict[int, ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if size in _font_cache:
        return _font_cache[size]
    for path in FONT_CANDIDATES:
        try:
            font = ImageFont.truetype(path, size)
            _font_cache[size] = font
            return font
        except (OSError, IOError):
            continue
    font = ImageFont.load_default()
    _font_cache[size] = font
    return font


# ──────────────────────────────────────────
# 字幕フレーズ生成
# ──────────────────────────────────────────

_BREAK_CHARS = set("。、！？!?,. ")
_MAX_PHRASE_CHARS = 10


def _split_text_into_phrases(text: str) -> list[str]:
    """元テキストを句読点・文字数で区切りフレーズリストに分割する。"""
    phrases: list[str] = []
    current = ""
    for char in text:
        current += char
        if char in _BREAK_CHARS or len(current) >= _MAX_PHRASE_CHARS:
            phrases.append(current)
            current = ""
    if current:
        phrases.append(current)
    return phrases


def build_subtitles(
    sections: dict[str, str],
    voice_results: dict[str, VoiceResult],
) -> list[SubtitleEntry]:
    """
    元テキストをフレーズに分割し、音声の総尺から時間を按分して字幕エントリを構築する。
    VOICEVOXのmora.textはカタカナ音素なので字幕表示には使わない。
    """
    section_order = ["hook", "body", "outro"]
    all_subtitles: list[SubtitleEntry] = []
    offset = 0.0

    for section in section_order:
        if section not in voice_results or section not in sections:
            continue
        vr = voice_results[section]
        original_text = sections[section]
        phrases = _split_text_into_phrases(original_text)
        total_chars = max(len(original_text), 1)

        elapsed = 0.0
        for phrase in phrases:
            phrase_duration = (len(phrase) / total_chars) * vr.duration
            all_subtitles.append(SubtitleEntry(
                text=phrase,
                start=offset + elapsed,
                end=offset + elapsed + phrase_duration,
            ))
            elapsed += phrase_duration

        offset += vr.duration

    return all_subtitles


# ──────────────────────────────────────────
# 背景生成
# ──────────────────────────────────────────

# グラデーションに使うカラーパレット（明るめ・見やすい色）
_GRADIENT_PALETTES = [
    [(40, 80, 160), (80, 30, 120), (20, 100, 140)],
    [(30, 120, 100), (60, 40, 140), (20, 80, 160)],
    [(120, 50, 30), (60, 30, 120), (20, 100, 120)],
]


def _lerp_color(c1: tuple, c2: tuple, t: float) -> tuple:
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def _make_gradient_frame(t: float, palette_idx: int = 0) -> np.ndarray:
    """時刻tに応じたアニメーショングラデーション背景を生成する（numpy配列）。"""
    palette = _GRADIENT_PALETTES[palette_idx % len(_GRADIENT_PALETTES)]
    period = 4.0  # 4秒でカラーサイクル

    phase = (t % period) / period
    if phase < 0.5:
        c_top = _lerp_color(palette[0], palette[1], phase * 2)
        c_bot = _lerp_color(palette[2], palette[0], phase * 2)
    else:
        c_top = _lerp_color(palette[1], palette[2], (phase - 0.5) * 2)
        c_bot = _lerp_color(palette[0], palette[2], (phase - 0.5) * 2)

    # 縦方向グラデーション
    arr = np.zeros((VIDEO_HEIGHT, VIDEO_WIDTH, 3), dtype=np.uint8)
    for y in range(VIDEO_HEIGHT):
        ratio = y / VIDEO_HEIGHT
        color = _lerp_color(c_top, c_bot, ratio)
        arr[y, :] = color

    return arr


def _resize_crop(clip: "VideoFileClip") -> "VideoFileClip":
    """動画を1080x1920にリサイズ＆クロップする。"""
    orig_w, orig_h = clip.size
    target_ratio = VIDEO_WIDTH / VIDEO_HEIGHT
    orig_ratio = orig_w / orig_h

    if orig_ratio > target_ratio:
        new_h = VIDEO_HEIGHT
        new_w = int(orig_w * VIDEO_HEIGHT / orig_h)
    else:
        new_w = VIDEO_WIDTH
        new_h = int(orig_h * VIDEO_WIDTH / orig_w)

    clip = clip.resize((new_w, new_h))
    x_center = new_w // 2
    y_center = new_h // 2
    return clip.crop(
        x1=x_center - VIDEO_WIDTH // 2,
        y1=y_center - VIDEO_HEIGHT // 2,
        x2=x_center + VIDEO_WIDTH // 2,
        y2=y_center + VIDEO_HEIGHT // 2,
    )


def _make_background_clip(
    total_duration: float,
    bg_video_paths: list[Path] | None = None,
) -> "ColorClip | VideoFileClip | ImageClip":
    """背景クリップを生成する。複数動画素材をつないで使う。"""
    valid_paths = [p for p in (bg_video_paths or []) if p.exists()]

    if valid_paths:
        try:
            from moviepy.editor import concatenate_videoclips
            clips = [_resize_crop(VideoFileClip(str(p))) for p in valid_paths]
            bg = concatenate_videoclips(clips, method="compose")

            # 尺が足りない場合は最後のクリップを追加して補う（同じ素材の繰り返しを最小化）
            while bg.duration < total_duration:
                extra = _resize_crop(VideoFileClip(str(valid_paths[-1])))
                bg = concatenate_videoclips([bg, extra], method="compose")

            bg = bg.subclip(0, total_duration)

            overlay = ColorClip(
                size=(VIDEO_WIDTH, VIDEO_HEIGHT),
                color=(0, 0, 0),
                duration=total_duration,
            ).set_opacity(0.15)

            return CompositeVideoClip([bg, overlay])
        except Exception as e:
            print(f"  ⚠️  背景動画読み込み失敗 ({e})。グラデーションを使用します。")

    # フォールバック: アニメーショングラデーション
    from moviepy.editor import VideoClip
    return VideoClip(
        lambda t: _make_gradient_frame(t),
        duration=total_duration,
    ).set_fps(VIDEO_FPS)


# ──────────────────────────────────────────
# 字幕描画
# ──────────────────────────────────────────

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


_MUSIC_DIR = Path(__file__).parent.parent / "assets" / "music"
_BGM_VOLUME = 0.12  # BGMの音量（ナレーションの12%）

_TITLE_PANEL_HEIGHT = 380   # 上部白パネルの高さ（px）
_SUBTITLE_Y = 1480          # 字幕の上端Y座標
_OUTLINE_SIZE = 10          # 縁取りの太さ（px）


def _draw_outlined_text(
    draw: ImageDraw.ImageDraw,
    pos: tuple[int, int],
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: tuple,
    outline: tuple = (0, 0, 0, 255),
    outline_size: int = _OUTLINE_SIZE,
) -> None:
    """縁取り付きテキストを描画する。"""
    x, y = pos
    for ox in range(-outline_size, outline_size + 1):
        for oy in range(-outline_size, outline_size + 1):
            if ox * ox + oy * oy <= outline_size * outline_size:
                draw.text((x + ox, y + oy), text, font=font, fill=outline)
    draw.text((x, y), text, font=font, fill=fill)


def _make_subtitle_image(text: str, topic: str) -> np.ndarray:
    """
    参考動画スタイルの字幕フレームを生成する（透過RGBA）。

    レイアウト:
      - 上部: 白パネル + 太い黒文字タイトル（固定）
      - 下部: 黄色テキスト + 黒縁取り字幕
    """
    img = Image.new("RGBA", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # ── 上部: 白いタイトルパネル ──
    draw.rectangle(
        [(0, 0), (VIDEO_WIDTH, _TITLE_PANEL_HEIGHT)],
        fill=(255, 255, 255, 235),
    )

    # タイトルテキスト（太黒、大きめ）
    title_font = _load_font(88)
    title_lines = _wrap_text(topic, title_font, VIDEO_WIDTH - 60)
    line_h = 100
    total_title_h = len(title_lines) * line_h
    y_title = (_TITLE_PANEL_HEIGHT - total_title_h) // 2

    for line in title_lines:
        tb = draw.textbbox((0, 0), line, font=title_font)
        lw = tb[2] - tb[0]
        lx = (VIDEO_WIDTH - lw) // 2
        # 薄いシャドウ
        draw.text((lx + 4, y_title + 4), line, font=title_font, fill=(80, 80, 80, 100))
        draw.text((lx, y_title), line, font=title_font, fill=(0, 0, 0, 255))
        y_title += line_h

    # ── 下部: 字幕（黄色 + 黒縁取り） ──
    body_font = _load_font(BODY_FONT_SIZE)
    max_width = VIDEO_WIDTH - 60
    lines = _wrap_text(text, body_font, max_width)
    sub_line_h = BODY_FONT_SIZE + 16
    total_sub_h = len(lines) * sub_line_h
    y = _SUBTITLE_Y

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=body_font)
        lw = bbox[2] - bbox[0]
        lx = (VIDEO_WIDTH - lw) // 2
        _draw_outlined_text(
            draw, (lx, y), line, body_font,
            fill=(255, 230, 0, 255),      # 黄色
            outline=(0, 0, 0, 255),
            outline_size=_OUTLINE_SIZE,
        )
        y += sub_line_h

    return np.array(img)


# ──────────────────────────────────────────
# BGM
# ──────────────────────────────────────────

def _get_bgm_clip(total_duration: float, genre: str = "trivia"):
    """ジャンル別フォルダからランダムにBGMを選択してループさせる。ファイルがなければNone。"""
    if not _MUSIC_DIR.exists():
        return None

    # ジャンル専用フォルダ → ルートフォルダの順でフォールバック
    search_dirs = [_MUSIC_DIR / genre, _MUSIC_DIR]
    music_files: list[Path] = []
    for d in search_dirs:
        if d.exists():
            music_files = [
                f for f in d.iterdir()
                if f.is_file() and f.suffix.lower() in (".mp3", ".wav", ".m4a", ".ogg")
            ]
        if music_files:
            break

    if not music_files:
        return None

    music_path = random.choice(music_files)
    try:
        bgm = AudioFileClip(str(music_path))
        if bgm.duration < total_duration:
            from moviepy.editor import concatenate_audioclips as _cat
            repeats = int(total_duration / bgm.duration) + 2
            bgm = _cat([bgm] * repeats)
        bgm = bgm.subclip(0, total_duration).volumex(_BGM_VOLUME)
        print(f"  🎵 BGM: {music_path.name}")
        return bgm
    except Exception as e:
        print(f"  ⚠️  BGM読み込み失敗 ({e})")
        return None


# ──────────────────────────────────────────
# メイン: 動画生成
# ──────────────────────────────────────────

def create_short(
    topic: str,
    sections: dict[str, str],
    voice_results: dict[str, VoiceResult],
    output_path: Path,
    bg_video_paths: list[Path] | None = None,
    genre: str = "trivia",
) -> Path:
    """
    字幕同期済みのYouTube Shorts動画を生成する。

    Args:
        topic: トピック名
        sections: セクション名 → テキスト
        voice_results: セクション名 → VoiceResult（音声+タイミング）
        output_path: 出力MP4パス
        bg_video_path: 背景動画パス（Noneの場合はグラデーション）

    Returns:
        生成された動画のPath
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    section_order = ["hook", "body", "outro"]
    audio_clips = []
    total_duration = 0.0

    for section in section_order:
        if section not in voice_results:
            continue
        vr = voice_results[section]
        clip = AudioFileClip(str(vr.audio_path))
        audio_clips.append(clip)
        total_duration += clip.duration

    print(f"  📹 総尺: {total_duration:.1f}秒")

    # 音声を結合
    from moviepy.editor import concatenate_audioclips, CompositeAudioClip
    combined_audio = concatenate_audioclips(audio_clips)

    # BGMをミックス
    bgm = _get_bgm_clip(total_duration, genre)
    if bgm:
        combined_audio = CompositeAudioClip([combined_audio, bgm])
        combined_audio = combined_audio.set_duration(total_duration)

    # 字幕エントリを構築
    subtitles = build_subtitles(sections, voice_results)

    # 字幕画像をキャッシュ（同じテキストは再生成しない）
    subtitle_image_cache: dict[str, np.ndarray] = {}
    for sub in subtitles:
        if sub.text not in subtitle_image_cache:
            subtitle_image_cache[sub.text] = _make_subtitle_image(sub.text, topic)

    # 字幕クリップを生成
    subtitle_clips = []
    for sub in subtitles:
        dur = max(sub.end - sub.start, 0.05)
        img_arr = subtitle_image_cache[sub.text]
        clip = (
            ImageClip(img_arr, ismask=False)
            .set_start(sub.start)
            .set_duration(dur)
            .set_position(("center", "center"))
        )
        subtitle_clips.append(clip)

    # 背景クリップ
    print("  🎨 背景生成中...")
    bg_clip = _make_background_clip(total_duration, bg_video_paths)

    # 全レイヤーを合成
    layers = [bg_clip] + subtitle_clips
    final = CompositeVideoClip(layers, size=(VIDEO_WIDTH, VIDEO_HEIGHT))
    final = final.set_audio(combined_audio)

    print(f"  💾 動画書き出し中: {output_path.name}")
    final.write_videofile(
        str(output_path),
        fps=VIDEO_FPS,
        codec="libx264",
        audio_codec="aac",
        temp_audiofile=str(output_path.parent / "temp_audio.m4a"),
        remove_temp=True,
        logger=None,
    )

    for clip in audio_clips:
        clip.close()
    final.close()

    return output_path
