# セットアップガイド

## 必要なもの

| ツール | 用途 | 入手先 |
|--------|------|--------|
| Python 3.10 以上 | 実行環境 | https://www.python.org/ |
| VOICEVOX | 音声合成（ナレーション生成） | https://voicevox.hiroshiba.jp/ |
| Anthropic API キー | スクリプト自動生成 | https://console.anthropic.com/ |
| Google Cloud アカウント | YouTube アップロード | https://console.cloud.google.com/ |
| Pexels または Pixabay API キー | 背景動画取得（任意） | 後述 |

---

## 1. リポジトリのセットアップ

```bash
cd youtube-automation

# 依存パッケージをインストール
pip install -r requirements.txt

# 環境変数ファイルを作成
cp .env.example .env
```

---

## 2. 日本語フォントのインストール

```bash
python setup_fonts.py
```

フォントの自動ダウンロードに失敗した場合は手動でインストールしてください。

```bash
# Ubuntu / WSL
sudo apt install fonts-noto-cjk

# macOS
brew install font-noto-sans-cjk-jp
```

---

## 3. VOICEVOX のセットアップ

1. https://voicevox.hiroshiba.jp/ からインストーラーをダウンロード
2. インストール後、VOICEVOX を起動する
3. デフォルトで `http://localhost:50021` で動作します

話者を変更したい場合は `.env` の `VOICEVOX_SPEAKER_ID` を変更してください。  
話者IDは VOICEVOX アプリ内で確認できます（ずんだもん=3）。

---

## 4. Anthropic API キーの設定

1. https://console.anthropic.com/ でAPIキーを発行
2. `.env` に記入する

```env
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxx
```

---

## 5. 背景動画APIキーの設定（任意）

設定しない場合はアニメーショングラデーション背景が使われます。  
どちらか一方だけでも動作します。

### Pexels（推奨）
1. https://www.pexels.com/api/ でAPIキーを発行（無料）
2. `.env` に記入する

```env
PEXELS_API_KEY=xxxxxxxxxxxxxxxxxx
```

### Pixabay
1. https://pixabay.com/api/docs/ でAPIキーを発行（無料）
2. `.env` に記入する

```env
PIXABAY_API_KEY=xxxxxxxxxxxxxxxxxx
```

---

## 6. YouTube アップロードのセットアップ

YouTube へのアップロードを使わない場合はこのステップをスキップできます。

### Google Cloud Console の設定

1. https://console.cloud.google.com/ でプロジェクトを作成
2. 「APIとサービス」→「ライブラリ」で **YouTube Data API v3** を検索して有効化
3. 「APIとサービス」→「OAuth 同意画面」を設定
   - User Type: **外部** を選択
   - アプリ名・メールアドレスを入力
   - 「テストユーザー」に自分の Google アカウントを追加
4. 「APIとサービス」→「認証情報」→「認証情報を作成」→「OAuth クライアント ID」
   - アプリケーションの種類: **デスクトップアプリ**
   - 作成後、**JSON をダウンロード**

### クライアントシークレットの配置

```bash
mkdir -p credentials
cp ~/Downloads/client_secret_*.json credentials/client_secrets.json
```

### 初回 OAuth 認証

```bash
python main.py --upload --privacy private
```

ブラウザが開いたら Google アカウントでログインして許可してください。  
`credentials/youtube_token.json` が生成されれば成功です。以降は自動で認証されます。

---

## 動作確認

```bash
# VOICEVOXを起動した状態で実行
python main.py

# 動画が output/ 以下に生成されれば成功
ls output/
```
