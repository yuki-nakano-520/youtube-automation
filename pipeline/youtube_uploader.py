"""
YouTube Data API v3 を使ったショート動画アップロードモジュール

初回実行時にブラウザが開き OAuth 認証が必要です。
認証後はトークンがファイルに保存され、次回以降は自動で再利用されます。

事前準備:
  1. Google Cloud Console でプロジェクトを作成
  2. YouTube Data API v3 を有効化
  3. OAuth 2.0 クライアントID（デスクトップアプリ）を作成してダウンロード
  4. ダウンロードした JSON を credentials/client_secrets.json に配置
"""

import json
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from config import (
    YOUTUBE_CATEGORY_ID,
    YOUTUBE_CLIENT_SECRETS_FILE,
    YOUTUBE_PRIVACY_STATUS,
    YOUTUBE_TOKEN_FILE,
)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

SHORTS_HASHTAG = "#Shorts"


class YouTubeUploadError(Exception):
    pass


def _get_credentials() -> Credentials:
    token_path = Path(YOUTUBE_TOKEN_FILE)
    creds: Credentials | None = None

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        secrets_path = Path(YOUTUBE_CLIENT_SECRETS_FILE)
        if not secrets_path.exists():
            raise YouTubeUploadError(
                f"クライアントシークレットファイルが見つかりません: {secrets_path}\n"
                "Google Cloud Console から OAuth 2.0 クライアントID をダウンロードして配置してください。"
            )
        flow = InstalledAppFlow.from_client_secrets_file(str(secrets_path), SCOPES)
        creds = flow.run_local_server(port=0)

    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(creds.to_json())
    return creds


def _build_description(topic: str, hashtags: list[str]) -> str:
    tags_str = " ".join(f"#{tag}" for tag in hashtags)
    return f"{topic} の豆知識！\n\n{tags_str} {SHORTS_HASHTAG}"


def upload_short(
    video_path: Path,
    title: str,
    hashtags: list[str],
    privacy_status: str = YOUTUBE_PRIVACY_STATUS,
    publish_at: str | None = None,
) -> str:
    """
    YouTube Shorts として動画をアップロードする。

    Args:
        publish_at: 予約投稿日時（ISO 8601形式、例: "2026-04-13T09:00:00+09:00"）。
                    指定した場合は privacyStatus を自動で "private" にセットし、
                    YouTube が指定日時に自動公開する。

    Returns:
        アップロードされた動画の YouTube URL
    """
    if not video_path.exists():
        raise YouTubeUploadError(f"動画ファイルが見つかりません: {video_path}")

    try:
        creds = _get_credentials()
    except Exception as e:
        raise YouTubeUploadError(f"認証に失敗しました: {e}") from e

    try:
        youtube = build("youtube", "v3", credentials=creds)
    except Exception as e:
        raise YouTubeUploadError(f"YouTube API クライアントの初期化に失敗しました: {e}") from e

    shorts_title = f"{title} {SHORTS_HASHTAG}"
    description = _build_description(title, hashtags)

    # publishAt を指定する場合、YouTube API の仕様で privacyStatus は "private" 必須
    status_body: dict = {
        "privacyStatus": "private" if publish_at else privacy_status,
        "selfDeclaredMadeForKids": False,
    }
    if publish_at:
        status_body["publishAt"] = publish_at

    body = {
        "snippet": {
            "title": shorts_title,
            "description": description,
            "tags": hashtags + ["Shorts", "ショート"],
            "categoryId": YOUTUBE_CATEGORY_ID,
        },
        "status": status_body,
    }

    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        resumable=True,
        chunksize=1024 * 1024 * 8,
    )

    try:
        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        print("  アップロード中...")
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                print(f"  進捗: {progress}%")

        video_id: str = response["id"]
        return f"https://www.youtube.com/shorts/{video_id}"

    except HttpError as e:
        error_content = json.loads(e.content.decode())
        error_message = error_content.get("error", {}).get("message", str(e))
        raise YouTubeUploadError(f"アップロードに失敗しました: {error_message}") from e
