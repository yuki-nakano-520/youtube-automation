import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
ASSETS_DIR = BASE_DIR / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
VOICEVOX_URL = os.getenv("VOICEVOX_URL", "http://localhost:50021")
VOICEVOX_SPEAKER_ID = int(os.getenv("VOICEVOX_SPEAKER_ID", "3"))
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "")

YOUTUBE_CLIENT_SECRETS_FILE = os.getenv(
    "YOUTUBE_CLIENT_SECRETS_FILE",
    str(BASE_DIR / "credentials" / "client_secrets.json"),
)
YOUTUBE_TOKEN_FILE = os.getenv(
    "YOUTUBE_TOKEN_FILE",
    str(BASE_DIR / "credentials" / "youtube_token.json"),
)
YOUTUBE_PRIVACY_STATUS = os.getenv("YOUTUBE_PRIVACY_STATUS", "private")
YOUTUBE_CATEGORY_ID = os.getenv("YOUTUBE_CATEGORY_ID", "22")

# 自動投稿スケジュール設定
POST_GENRES_CYCLE = [
    g.strip()
    for g in os.getenv("POST_GENRES_CYCLE", "trivia,history,science,money,english").split(",")
]
POST_TIMES = [t.strip() for t in os.getenv("POST_TIMES", "09:00").split(",")]
POST_DAYS = [d.strip() for d in os.getenv("POST_DAYS", "mon,tue,wed,thu,fri,sat,sun").split(",")]
POST_PRIVACY = os.getenv("POST_PRIVACY", "public")
POST_COUNT_PER_RUN = int(os.getenv("POST_COUNT_PER_RUN", "1"))

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS = 30

FONT_CANDIDATES = [
    str(FONTS_DIR / "NotoSansJP-Bold.ttf"),
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJKjp-Bold.otf",
    "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
    "/usr/share/fonts/truetype/ipafont/ipagp.ttf",
    "C:/Windows/Fonts/meiryo.ttc",
    "C:/Windows/Fonts/YuGothM.ttc",
]

GENRES: dict[str, str] = {
    "trivia":   "面白い雑学・豆知識",
    "history":  "歴史の意外な真実",
    "science":  "科学の不思議",
    "money":    "お金・経済の豆知識",
    "english":  "使える英語フレーズ",
}
DEFAULT_GENRE = "trivia"

BACKGROUND_COLOR = (10, 12, 30)
ACCENT_COLOR = (100, 200, 255)
TEXT_COLOR = (255, 255, 255)
SHADOW_COLOR = (0, 0, 0)
TITLE_FONT_SIZE = 52
BODY_FONT_SIZE = 68
TOPIC_FONT_SIZE = 40
