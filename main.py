"""
YouTube Shorts 自動生成パイプライン
使い方: python3 main.py [--genre trivia] [--count 1] [--upload] [--privacy private]
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from config import DEFAULT_GENRE, GENRES, OUTPUT_DIR, YOUTUBE_PRIVACY_STATUS
from pipeline.media_fetcher import fetch_background_videos
from pipeline.script_generator import ShortScript, generate_script
from pipeline.video_generator import create_short
from pipeline.voice_generator import VoicevoxError, generate_voice_sections
from pipeline.youtube_uploader import YouTubeUploadError, upload_short


def run(
    genre: str = DEFAULT_GENRE,
    count: int = 1,
    upload: bool = False,
    privacy: str = YOUTUBE_PRIVACY_STATUS,
) -> None:
    if genre not in GENRES:
        print(f"❌ 無効なジャンル: {genre}")
        print(f"   有効なジャンル: {', '.join(GENRES.keys())}")
        sys.exit(1)

    print(f"\n🎬 YouTube Shorts 自動生成 — {GENRES[genre]}")
    print("=" * 50)

    for i in range(count):
        if count > 1:
            print(f"\n▶ [{i + 1}/{count}本目]")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        work_dir = OUTPUT_DIR / timestamp

        try:
            # Step 1: スクリプト生成
            print("\n📝 Step 1: スクリプト生成中...")
            script: ShortScript = generate_script(genre)
            print(f"  トピック: {script.topic}")
            print(f"  Hook   : {script.hook[:30]}...")
            print(f"  Body   : {script.body[:30]}...")
            print(f"  Outro  : {script.outro[:30]}...")

            # Step 2: 音声生成
            print("\n🎙️  Step 2: 音声生成中 (VOICEVOX)...")
            voice_results = generate_voice_sections(
                sections=script.sections,
                output_dir=work_dir / "audio",
            )

            # Step 3: 背景素材取得（Pexels APIキーがあれば）
            print("\n🖼️  Step 3: 背景素材取得中...")
            print(f"  🔍 検索キーワード: {script.search_query}")
            bg_videos = fetch_background_videos(script.search_query, count=3)
            if bg_videos:
                print(f"  ✅ 背景動画取得: {len(bg_videos)}本")
            else:
                print("  ℹ️  グラデーション背景を使用します（Pexels APIキー未設定）")

            # Step 4: 動画生成
            print("\n🎬 Step 4: 動画生成中 (MoviePy)...")
            output_video = work_dir / f"{script.topic}.mp4"
            create_short(
                topic=script.topic,
                sections=script.sections,
                voice_results=voice_results,
                output_path=output_video,
                bg_video_paths=bg_videos or None,
                genre=genre,
            )

            # 完了
            print(f"\n✅ 動画生成完了！")
            print(f"   📁 {output_video}")
            print(f"\n📣 YouTube説明文:")
            print(f"   {script.topic} の豆知識！\n")
            print(f"   {' '.join(f'#{tag}' for tag in script.hashtags)}")

            # Step 5: YouTube アップロード（オプション）
            if upload:
                print(f"\n📤 Step 5: YouTube へアップロード中 (公開設定: {privacy})...")
                video_url = upload_short(
                    video_path=output_video,
                    title=script.topic,
                    hashtags=script.hashtags,
                    privacy_status=privacy,
                )
                print(f"  ✅ アップロード完了！")
                print(f"  🔗 {video_url}")

        except VoicevoxError as e:
            print(f"\n❌ VOICEVOX エラー: {e}")
            sys.exit(1)
        except YouTubeUploadError as e:
            print(f"\n❌ YouTube アップロード エラー: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ エラーが発生しました: {e}")
            raise


def upload_only(
    video_path: Path,
    title: str | None,
    tags: list[str],
    privacy: str,
) -> None:
    if not video_path.exists():
        print(f"❌ ファイルが見つかりません: {video_path}")
        raise SystemExit(1)

    resolved_title = title or video_path.stem
    print(f"\n📤 アップロード開始")
    print(f"   ファイル  : {video_path}")
    print(f"   タイトル  : {resolved_title}")
    print(f"   公開設定  : {privacy}")

    try:
        video_url = upload_short(
            video_path=video_path,
            title=resolved_title,
            hashtags=tags,
            privacy_status=privacy,
        )
        print(f"\n✅ アップロード完了！")
        print(f"   🔗 {video_url}")
    except YouTubeUploadError as e:
        print(f"\n❌ YouTube アップロード エラー: {e}")
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="YouTube Shorts 自動生成")
    parser.add_argument(
        "--genre",
        default=DEFAULT_GENRE,
        choices=list(GENRES.keys()),
        help=f"ジャンル (default: {DEFAULT_GENRE})",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="生成する動画の本数 (default: 1)",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="生成後に YouTube へ自動アップロードする",
    )
    parser.add_argument(
        "--upload-only",
        metavar="VIDEO_PATH",
        help="既存の動画ファイルをアップロードのみ行う（生成をスキップ）",
    )
    parser.add_argument(
        "--title",
        help="--upload-only 時のタイトル（省略時はファイル名を使用）",
    )
    parser.add_argument(
        "--tags",
        default="",
        help="--upload-only 時のハッシュタグ（カンマ区切り、例: 雑学,豆知識）",
    )
    parser.add_argument(
        "--privacy",
        default=YOUTUBE_PRIVACY_STATUS,
        choices=["private", "unlisted", "public"],
        help=f"公開設定 (default: {YOUTUBE_PRIVACY_STATUS})",
    )
    args = parser.parse_args()

    if args.upload_only:
        tag_list = [t.strip() for t in args.tags.split(",") if t.strip()]
        upload_only(
            video_path=Path(args.upload_only),
            title=args.title,
            tags=tag_list,
            privacy=args.privacy,
        )
        return

    run(genre=args.genre, count=args.count, upload=args.upload, privacy=args.privacy)


if __name__ == "__main__":
    main()
