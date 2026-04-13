# 設定リファレンス

すべての設定は `.env` ファイルで管理します。`.env.example` をコピーして編集してください。

```bash
cp .env.example .env
```

---

## API キー

| 変数 | 必須 | デフォルト | 説明 |
|------|------|-----------|------|
| `ANTHROPIC_API_KEY` | 必須 | なし | Claude API キー。スクリプト生成に使用 |
| `PEXELS_API_KEY` | 任意 | 空 | Pexels APIキー。背景動画の取得に使用 |
| `PIXABAY_API_KEY` | 任意 | 空 | Pixabay APIキー。Pexels のフォールバック |

---

## VOICEVOX

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `VOICEVOX_URL` | `http://localhost:50021` | VOICEVOX エンジンのURL |
| `VOICEVOX_SPEAKER_ID` | `3` | 話者ID（3=ずんだもん） |

### 主な話者ID

| ID | キャラクター |
|----|------------|
| 1 | 四国めたん（あまあま） |
| 2 | ずんだもん（あまあま） |
| 3 | ずんだもん（ノーマル） |
| 8 | 春日部つむぎ |
| 10 | 雨晴はう |
| 13 | 青山龍星 |

全話者IDは VOICEVOX アプリ内またはエンジンの `/speakers` エンドポイントで確認できます。

---

## YouTube

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `YOUTUBE_CLIENT_SECRETS_FILE` | `credentials/client_secrets.json` | OAuth クライアントIDファイルのパス |
| `YOUTUBE_TOKEN_FILE` | `credentials/youtube_token.json` | OAuth トークンキャッシュのパス |
| `YOUTUBE_PRIVACY_STATUS` | `private` | デフォルトの公開設定（`public` / `unlisted` / `private`） |
| `YOUTUBE_CATEGORY_ID` | `22` | YouTube カテゴリID（22=ブログ・人） |

### YouTube カテゴリID（主要なもの）

| ID | カテゴリ |
|----|---------|
| 1 | 映画・アニメ |
| 10 | 音楽 |
| 17 | スポーツ |
| 22 | ブログ・人 |
| 24 | エンターテイメント |
| 27 | 教育 |
| 28 | 科学・技術 |

---

## 自動投稿スケジュール

| 変数 | デフォルト | 説明 |
|------|-----------|------|
| `POST_GENRES_CYCLE` | `trivia,history,science,money,english` | 投稿するジャンルの順番（カンマ区切り） |
| `POST_TIMES` | `09:00` | 投稿時刻（カンマ区切りで複数指定可） |
| `POST_DAYS` | `mon,tue,wed,thu,fri,sat,sun` | 投稿曜日（カンマ区切り） |
| `POST_PRIVACY` | `public` | スケジューラー経由での公開設定 |
| `POST_COUNT_PER_RUN` | `1` | 1回の実行で生成・投稿する本数 |

---

## 設定例

### 毎日1本・朝9時に雑学を公開投稿

```env
POST_GENRES_CYCLE=trivia
POST_TIMES=09:00
POST_DAYS=mon,tue,wed,thu,fri,sat,sun
POST_PRIVACY=public
POST_COUNT_PER_RUN=1
```

### 平日のみ・2ジャンルを交互に

```env
POST_GENRES_CYCLE=trivia,history
POST_TIMES=08:00
POST_DAYS=mon,tue,wed,thu,fri
POST_PRIVACY=public
POST_COUNT_PER_RUN=1
```

### 週2回・まとめて2本投稿

```env
POST_GENRES_CYCLE=trivia,history,science,money,english
POST_TIMES=10:00
POST_DAYS=mon,thu
POST_PRIVACY=public
POST_COUNT_PER_RUN=2
```
