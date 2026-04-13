"""
日本語フォントをダウンロードするセットアップスクリプト。
初回のみ実行してください: python setup_fonts.py
"""

import urllib.request
from pathlib import Path

FONTS_DIR = Path(__file__).parent / "assets" / "fonts"

FONTS = {
    "NotoSansJP-Bold.ttf": "https://github.com/notofonts/noto-cjk/raw/main/Sans/OTF/Japanese/NotoSansCJKjp-Bold.otf",
}

# GitHub Releases からの別URLも試す
FONTS_FALLBACK = {
    "NotoSansJP-Bold.ttf": (
        "https://github.com/google/fonts/raw/main/ofl/notosansjp/NotoSansJP%5Bwght%5D.ttf"
    ),
}


def download_font(filename: str, url: str) -> bool:
    dest = FONTS_DIR / filename
    if dest.exists():
        print(f"✅ {filename} は既に存在します。")
        return True

    print(f"⬇️  {filename} をダウンロード中...")
    try:
        FONTS_DIR.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, dest)
        print(f"✅ {filename} を保存しました: {dest}")
        return True
    except Exception as e:
        print(f"❌ ダウンロード失敗: {e}")
        return False


def main() -> None:
    print("🔤 日本語フォントのセットアップ")
    print("=" * 40)

    for filename, url in FONTS.items():
        if not download_font(filename, url):
            fallback = FONTS_FALLBACK.get(filename)
            if fallback:
                print(f"   フォールバックURLを試します...")
                download_font(filename, fallback)

    print("\n📌 フォントが見つからない場合は手動でインストール:")
    print("   Ubuntu/WSL: sudo apt install fonts-noto-cjk")
    print("   macOS: brew install font-noto-sans-cjk-jp")
    print(f"   または {FONTS_DIR} に NotoSansJP-Bold.ttf を配置してください。")


if __name__ == "__main__":
    main()
