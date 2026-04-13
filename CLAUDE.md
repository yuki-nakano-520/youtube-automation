# YouTube Shorts 自動生成パイプライン — CLAUDE.md

## プロジェクト概要

Claude API・VOICEVOX・MoviePy を組み合わせて YouTube Shorts 動画を自動生成するPythonパイプライン。  
スクリプト生成 → 音声合成 → 背景素材取得 → 動画編集 → YouTube アップロード の5ステップで構成される。

---

## ディレクトリ構成

```
youtube-automation/
├── main.py                  # エントリポイント（CLIパーサー + run()関数）
├── config.py                # 全設定値の一元管理（.envから読み込み）
├── setup_fonts.py           # 日本語フォント初回セットアップ用スクリプト
├── requirements.txt         # Python依存パッケージ
├── .env                     # 実際のAPIキー（gitignore対象）
├── .env.example             # .envのテンプレート
├── pipeline/
│   ├── __init__.py
│   ├── script_generator.py  # Step1: Claude APIでスクリプト生成
│   ├── voice_generator.py   # Step2: VOICEVOX で音声合成
│   ├── media_fetcher.py     # Step3: Pexels/Pixabay から背景動画取得
│   ├── video_generator.py   # Step4: MoviePy で動画合成
│   └── youtube_uploader.py  # Step5: YouTube Data API v3 でアップロード
├── assets/
│   ├── fonts/               # NotoSansJP-Bold.ttf（setup_fonts.pyでDL）
│   ├── music/
│   │   ├── trivia/          # ジャンル別BGMフォルダ
│   │   ├── history/
│   │   ├── science/
│   │   ├── money/
│   │   └── english/
│   └── cache/               # 背景動画のキャッシュ（*.mp4）
├── output/
│   ├── topics_history.json  # 生成済みトピックの履歴（重複防止）
│   └── YYYYMMDD_HHMMSS/     # 動画ごとの作業ディレクトリ
│       ├── audio/           # hook.wav / body.wav / outro.wav
│       └── <トピック名>.mp4  # 完成動画
└── credentials/
    ├── client_secrets.json  # Google OAuth クライアントID（gitignore対象）
    └── youtube_token.json   # OAuth トークンキャッシュ（gitignore対象）
```

---

## パイプライン詳細

### Step 1: スクリプト生成 (`pipeline/script_generator.py`)

- **使用モデル**: `claude-haiku-4-5`（速度重視）
- `ShortScript` dataclass に `topic / hook / body / outro / hashtags / search_query` を格納
- `output/topics_history.json` に最大50件の履歴を保存し、直近20件を Claude プロンプトに渡して重複防止
- Claude に JSON のみ返させる（コードブロック不要）。レスポンスのコードブロックは手動でストリップ

### Step 2: 音声合成 (`pipeline/voice_generator.py`)

- **使用ツール**: VOICEVOX（ローカルHTTP API、デフォルト `http://localhost:50021`）
- `generate_voice()` が `/audio_query` → `/synthesis` の2ステップで WAV を生成
- `speedScale=1.1 / intonationScale=1.1` でテンポよく読み上げ
- `VoiceResult` に `audio_path / duration / char_timings` を格納
- `VoicevoxError` は接続失敗時にスロー（VOICEVOX未起動が最多ケース）

### Step 3: 背景素材取得 (`pipeline/media_fetcher.py`)

- **優先順位**: Pexels API → Pixabay API → グラデーション背景（フォールバック）
- `fetch_background_videos(keyword, count=3)` で複数本取得
- MD5ハッシュ名で `assets/cache/` にキャッシュ。同一キーワードは再DLしない
- どちらのAPIキーも未設定の場合は空リストを返す（エラーにしない）

### Step 4: 動画生成 (`pipeline/video_generator.py`)

- **解像度**: 1080×1920 (9:16 縦型)、30fps
- **字幕レイアウト**:
  - 上部（高さ380px）: 白パネル + 黒文字トピック名（フォントサイズ88）
  - 下部（Y=1480〜）: 黄色テキスト + 黒縁取り字幕（フォントサイズ68）
- `build_subtitles()` で元テキストをフレーズに分割し、音声尺を文字数比で按分してタイミング割り当て
- BGMは `assets/music/<ジャンル>/` からランダム選択、音量は `0.12`（ナレーションの12%）
- Pillow 10以降で `ANTIALIAS` が削除されたため、`PIL.Image.ANTIALIAS = PIL.Image.LANCZOS` のパッチを適用済み（MoviePy 1.x との互換性のため）
- `write_videofile()` は `codec=libx264 / audio_codec=aac`

### Step 5: YouTube アップロード (`pipeline/youtube_uploader.py`)

- **認証**: OAuth 2.0（デスクトップアプリ）。初回はブラウザが開く
- トークンを `credentials/youtube_token.json` にキャッシュ（有効期限切れは自動リフレッシュ）
- タイトルに `#Shorts` を付与することで YouTube がショートと認識
- `YouTubeUploadError` でAPIエラーをラップ

---

## 設定値 (`config.py`)

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `ANTHROPIC_API_KEY` | 必須 | Claude APIキー |
| `VOICEVOX_URL` | `http://localhost:50021` | VOICEVOX エンドポイント |
| `VOICEVOX_SPEAKER_ID` | `3` | 話者ID（ずんだもん等） |
| `PEXELS_API_KEY` | 空（任意） | Pexels APIキー |
| `PIXABAY_API_KEY` | 空（任意） | Pixabay APIキー |
| `YOUTUBE_CLIENT_SECRETS_FILE` | `credentials/client_secrets.json` | OAuth クライアントID |
| `YOUTUBE_PRIVACY_STATUS` | `private` | デフォルト公開設定 |
| `VIDEO_WIDTH/HEIGHT` | `1080/1920` | 動画解像度（変更非推奨） |

---

## 使い方

```bash
# 初回セットアップ
cp .env.example .env
# .env を編集して ANTHROPIC_API_KEY を設定

# フォントセットアップ（初回のみ）
python setup_fonts.py

# 雑学ジャンルで1本生成（VOICEVOXを先に起動すること）
python main.py

# ジャンル指定・複数本生成・アップロード
python main.py --genre history --count 3 --upload --privacy unlisted
```

**利用可能ジャンル**: `trivia`（雑学）/ `history`（歴史）/ `science`（科学）/ `money`（お金）/ `english`（英語）

---

## 開発上の注意点

### 型付け
- TypeScript ではなく Python（型ヒント使用）
- `any` 相当の使用は避け、適切な型を明示する（例: `dict[str, str]`、`list[Path]`）
- クラスは `dataclass` を優先。継承が必要な場合のみ通常クラスを使う（例: `VoicevoxError(Exception)`）

### 外部依存
- **MoviePy**: `1.x` 系を使用（`2.x` は非互換）。`requirements.txt` で上限固定済み
- **Pillow**: `10.x` 系。`ANTIALIAS` 削除への対処が `video_generator.py` 冒頭に記載
- **VOICEVOX**: ローカルプロセスとして別途起動が必要。`VoicevoxError` の主因

### ハードコード回避
- 設定値はすべて `config.py` に集約し `.env` で上書きできる設計
- 動画サイズ・フォントサイズ・音量などは定数として `config.py` に定義

### エラーハンドリング
- `VoicevoxError` / `YouTubeUploadError` はパイプライン固有の例外として定義済み
- `main.py` のトップレベルで捕捉して `sys.exit(1)` する設計
- システム境界（外部API呼び出し）でのみバリデーション・例外処理を行う

### BGM配置
- `assets/music/<ジャンル>/` に MP3/WAV/M4A/OGG を置くと自動的に使われる
- ジャンル専用フォルダがなければ `assets/music/` 直下からフォールバック

### 背景動画キャッシュ
- `assets/cache/` は gitignore 対象。不要になったら手動削除する
- キャッシュキーは `<keyword>_<index>` の MD5（先頭12文字）

---

## よくあるエラー

| エラー | 原因 | 対処 |
|--------|------|------|
| `VoicevoxError: VOICEVOXに接続できません` | VOICEVOX 未起動 | VOICEVOX アプリを起動してから再実行 |
| `OSError` in `_load_font` | フォント未インストール | `python setup_fonts.py` または `sudo apt install fonts-noto-cjk` |
| `YouTubeUploadError: クライアントシークレット...` | `credentials/client_secrets.json` が存在しない | Google Cloud Console から OAuth クライアントID をダウンロードして配置 |
| `json.JSONDecodeError` in `generate_script` | Claude のレスポンスが JSON 以外 | 基本的に自動リトライなし。再実行で解決することが多い |
