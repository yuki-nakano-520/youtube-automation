# 使い方ガイド

## 基本的な使い方

```bash
# デフォルト設定で1本生成（ジャンル: trivia）
python main.py

# ジャンルを指定して生成
python main.py --genre history

# 複数本まとめて生成
python main.py --genre science --count 3

# 生成と同時に YouTube へアップロード
python main.py --upload --privacy public
```

---

## コマンドオプション一覧

| オプション | デフォルト | 説明 |
|-----------|-----------|------|
| `--genre` | `trivia` | ジャンルを指定 |
| `--count` | `1` | 生成する動画の本数 |
| `--upload` | なし | 生成後に YouTube へアップロードする |
| `--upload-only` | なし | 既存の動画ファイルをアップロードのみ行う |
| `--title` | ファイル名 | `--upload-only` 時のタイトル |
| `--tags` | 空 | `--upload-only` 時のハッシュタグ（カンマ区切り） |
| `--privacy` | `private` | 公開設定（`public` / `unlisted` / `private`） |

---

## ジャンル一覧

| キー | 内容 |
|------|------|
| `trivia` | 面白い雑学・豆知識 |
| `history` | 歴史の意外な真実 |
| `science` | 科学の不思議 |
| `money` | お金・経済の豆知識 |
| `english` | 使える英語フレーズ |

---

## 既存動画のアップロード

生成済みの動画を後からアップロードしたい場合に使います。

```bash
# ファイル名をタイトルとして使用（最もシンプル）
python main.py --upload-only output/20260411_152850/バナナは果物じゃない.mp4

# タイトルとタグを明示的に指定
python main.py --upload-only output/20260411_152850/バナナは果物じゃない.mp4 \
  --title "バナナは果物じゃない！？" \
  --tags "雑学,豆知識,バナナ" \
  --privacy public

# 非公開でアップロード（後から手動公開する場合）
python main.py --upload-only output/20260411_152850/バナナは果物じゃない.mp4 --privacy private
```

---

## 出力ファイルの構成

実行するたびにタイムスタンプ付きのフォルダが `output/` に作成されます。

```
output/
└── 20260411_152850/          # YYYYMMDD_HHMMSS
    ├── audio/
    │   ├── hook.wav          # 冒頭ナレーション音声
    │   ├── body.wav          # 本題ナレーション音声
    │   └── outro.wav         # 締めナレーション音声
    └── バナナは果物じゃない.mp4  # 完成動画
```

---

## BGM のカスタマイズ

`assets/music/<ジャンル>/` フォルダに音楽ファイルを置くと自動で使われます。

```
assets/music/
├── trivia/     # 雑学ジャンル用
├── history/    # 歴史ジャンル用
├── science/    # 科学ジャンル用
├── money/      # お金ジャンル用
└── english/    # 英語ジャンル用
```

対応フォーマット: `.mp3` / `.wav` / `.m4a` / `.ogg`  
ジャンル専用フォルダが空の場合は `assets/music/` 直下からランダムに選択されます。

---

## よくあるエラー

| エラー | 原因 | 対処 |
|--------|------|------|
| `VoicevoxError: VOICEVOXに接続できません` | VOICEVOX 未起動 | VOICEVOX アプリを起動してから再実行 |
| `OSError` (フォント関連) | 日本語フォント未インストール | `python setup_fonts.py` を実行 |
| `YouTubeUploadError: クライアントシークレット...` | `credentials/client_secrets.json` がない | [セットアップガイド](./setup.md) の手順6を参照 |
| `403 accessNotConfigured` | YouTube Data API v3 が未有効化 | Google Cloud Console で API を有効化 |
| `403 access_denied` | OAuth テストユーザー未登録 | Google Cloud Console で自分のアカウントをテストユーザーに追加 |
