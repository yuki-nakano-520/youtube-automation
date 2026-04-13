"""
背景動画を取得するモジュール。
Pexels → Pixabay の順でフォールバックする。
どちらのAPIキーも未設定の場合はNoneを返す。
"""

import hashlib
import os
import random
from pathlib import Path

import requests

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "")
CACHE_DIR = Path(__file__).parent.parent / "assets" / "cache"


def _cache_path(key: str, ext: str) -> Path:
    h = hashlib.md5(key.encode()).hexdigest()[:12]
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{h}.{ext}"


def _download_file(url: str, dest: Path, timeout: int = 60) -> bool:
    """URLからファイルをダウンロードしてdestに保存する。"""
    try:
        res = requests.get(url, timeout=timeout, stream=True)
        res.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in res.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"  ⚠️  ダウンロード失敗 ({e})")
        if dest.exists():
            dest.unlink()
        return False


def _fetch_from_pexels(keyword: str, cached: Path) -> bool:
    """Pexels APIから背景動画を取得する。"""
    if not PEXELS_API_KEY:
        return False

    headers = {"Authorization": PEXELS_API_KEY}

    # portrait優先、なければlandscapeで試す
    for orientation in ["portrait", None]:
        params = {"query": keyword, "size": "medium", "per_page": 5}
        if orientation:
            params["orientation"] = orientation

        try:
            res = requests.get(
                "https://api.pexels.com/videos/search",
                headers=headers,
                params=params,
                timeout=10,
            )
            res.raise_for_status()
            videos = res.json().get("videos", [])
        except Exception as e:
            print(f"  ⚠️  Pexels検索失敗 ({e})")
            return False

        if videos:
            break
    else:
        return False

    # 結果からランダムに1本選択してSD品質ファイルを取得
    video = random.choice(videos)
    video_files = video.get("video_files", [])
    target = next((vf for vf in video_files if vf.get("quality") == "sd"), None)
    if not target and video_files:
        target = video_files[-1]
    if not target:
        return False

    print(f"  📹 Pexelsから動画取得中...")
    return _download_file(target["link"], cached)


def _fetch_from_pixabay(keyword: str, cached: Path) -> bool:
    """Pixabay APIから背景動画を取得する。"""
    if not PIXABAY_API_KEY:
        return False

    try:
        res = requests.get(
            "https://pixabay.com/api/videos/",
            params={
                "key": PIXABAY_API_KEY,
                "q": keyword,
                "video_type": "film",
                "per_page": 5,
                "lang": "ja",
            },
            timeout=10,
        )
        res.raise_for_status()
        hits = res.json().get("hits", [])
    except Exception as e:
        print(f"  ⚠️  Pixabay検索失敗 ({e})")
        return False

    if not hits:
        # 英語で再試行
        try:
            res = requests.get(
                "https://pixabay.com/api/videos/",
                params={
                    "key": PIXABAY_API_KEY,
                    "q": keyword,
                    "video_type": "film",
                    "per_page": 5,
                },
                timeout=10,
            )
            res.raise_for_status()
            hits = res.json().get("hits", [])
        except Exception:
            return False

    if not hits:
        return False

    # 結果からランダムに1本選択
    hit = random.choice(hits)
    videos = hit.get("videos", {})
    video_url = None
    for quality in ("medium", "small", "tiny"):
        v = videos.get(quality, {})
        if v.get("url"):
            video_url = v["url"]
            break

    if not video_url:
        return False

    print(f"  📹 Pixabayから動画取得中...")
    return _download_file(video_url, cached)


def _fetch_pexels_video_urls(keyword: str, count: int = 3) -> list[str]:
    """Pexelsから動画ダウンロードURLをcount件取得する。"""
    if not PEXELS_API_KEY:
        return []
    urls: list[str] = []
    for orientation in ["portrait", None]:
        params: dict = {"query": keyword, "size": "medium", "per_page": max(count * 2, 8)}
        if orientation:
            params["orientation"] = orientation
        try:
            res = requests.get(
                "https://api.pexels.com/videos/search",
                headers={"Authorization": PEXELS_API_KEY},
                params=params,
                timeout=10,
            )
            res.raise_for_status()
            videos = res.json().get("videos", [])
        except Exception:
            continue
        random.shuffle(videos)
        for video in videos:
            if len(urls) >= count:
                break
            video_files = video.get("video_files", [])
            target = next((vf for vf in video_files if vf.get("quality") == "sd"), None)
            if not target and video_files:
                target = video_files[-1]
            if target and target.get("link"):
                urls.append(target["link"])
        if urls:
            break
    return urls


def fetch_background_videos(keyword: str, count: int = 3) -> list[Path]:
    """
    キーワードに関連する背景動画をcount本取得する（重複なし）。
    キャッシュ済みのものは再ダウンロードしない。

    Returns:
        ダウンロードしたMP4のPathリスト（空の場合はグラデーション背景を使う）
    """
    if not PEXELS_API_KEY and not PIXABAY_API_KEY:
        return []

    results: list[Path] = []

    # キャッシュ確認
    cached_paths = [_cache_path(f"{keyword}_{i}", "mp4") for i in range(count)]
    if all(p.exists() for p in cached_paths):
        return cached_paths

    # Pexelsから複数URLを取得
    urls = _fetch_pexels_video_urls(keyword, count)

    if not urls:
        # フォールバック: Pixabayで1本だけ試みる
        single = _cache_path(keyword, "mp4")
        if not single.exists():
            _fetch_from_pixabay(keyword, single)
        if single.exists():
            return [single]
        print("  ⚠️  動画取得失敗。グラデーション背景を使用します。")
        return []

    print(f"  📹 Pexelsから動画を{len(urls)}本取得中...")
    for i, url in enumerate(urls[:count]):
        dest = cached_paths[i]
        if dest.exists():
            results.append(dest)
            continue
        if _download_file(url, dest):
            results.append(dest)

    return results


def fetch_background_video(keyword: str) -> Path | None:
    """後方互換用ラッパー。fetch_background_videos()を推奨。"""
    videos = fetch_background_videos(keyword, count=1)
    return videos[0] if videos else None


def fetch_background_image(keyword: str) -> Path | None:
    """
    キーワードに関連する背景画像をPexelsから取得する。

    Returns:
        ダウンロードしたJPGのPath、またはNone
    """
    if not PEXELS_API_KEY:
        return None

    cached = _cache_path(f"img_{keyword}", "jpg")
    if cached.exists():
        return cached

    try:
        res = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_API_KEY},
            params={
                "query": keyword,
                "orientation": "portrait",
                "size": "medium",
                "per_page": 3,
            },
            timeout=10,
        )
        res.raise_for_status()
        photos = res.json().get("photos", [])
        if not photos:
            return None

        img_url = photos[0]["src"]["large"]
        img_res = requests.get(img_url, timeout=30)
        img_res.raise_for_status()
        cached.write_bytes(img_res.content)
        return cached

    except Exception as e:
        print(f"  ⚠️  Pexels画像取得失敗 ({e})。")
        return None
