# 自動投稿スケジューラー

## 概要

`scheduler.py` を使うと、指定した曜日・時刻に自動で動画を生成して YouTube へアップロードできます。

---

## 前提条件

- [セットアップガイド](./setup.md) が完了していること
- YouTube アップロード用の OAuth 認証が完了していること（`credentials/youtube_token.json` が存在すること）
- VOICEVOX が起動していること

---

## 使い方

```bash
# 常駐モード（設定した曜日・時刻に自動実行）
python scheduler.py

# 即時1回実行して終了（動作確認用）
python scheduler.py --now

# 登録済みスケジュールの確認
python scheduler.py --status
```

---

## スケジュールの設定

`.env` ファイルで投稿スケジュールをカスタマイズします。

```env
# 投稿するジャンルの順番（サイクルで繰り返す）
POST_GENRES_CYCLE=trivia,history,science,money,english

# 投稿時刻（カンマ区切りで複数指定可）
POST_TIMES=09:00

# 投稿曜日（カンマ区切り）
POST_DAYS=mon,tue,wed,thu,fri,sat,sun

# 公開設定
POST_PRIVACY=public

# 1回の実行で生成・投稿する本数
POST_COUNT_PER_RUN=1
```

### 設定例

```env
# 平日の朝9時と夜9時に投稿
POST_DAYS=mon,tue,wed,thu,fri
POST_TIMES=09:00,21:00

# 毎日1本、雑学と歴史を交互に投稿
POST_GENRES_CYCLE=trivia,history
POST_COUNT_PER_RUN=1
```

### 曜日キー一覧

| キー | 曜日 |
|------|------|
| `mon` | 月曜 |
| `tue` | 火曜 |
| `wed` | 水曜 |
| `thu` | 木曜 |
| `fri` | 金曜 |
| `sat` | 土曜 |
| `sun` | 日曜 |

---

## ログ

実行ログは `output/logs/scheduler.log` に保存されます。

```bash
# リアルタイムでログを確認
tail -f output/logs/scheduler.log
```

---

## バックグラウンド常駐（WSL2 / Linux）

### nohup で起動

```bash
nohup python scheduler.py > /dev/null 2>&1 &
echo $! > scheduler.pid   # プロセスIDを保存

# 停止する場合
kill $(cat scheduler.pid)
```

### Windows タスクスケジューラで自動起動（WSL2 推奨）

PC 起動時に自動でスケジューラーを起動したい場合は Windows タスクスケジューラを使います。

1. スタートメニューで「タスクスケジューラ」を検索して開く
2. 「タスクの作成」をクリック
3. 各タブを以下のように設定する

**全般タブ**
- 名前: `YouTube Auto Scheduler`
- 「ユーザーがログオンしているかどうかにかかわらず実行する」を選択

**トリガータブ**
- 「新規」→ タスクの開始: **コンピューターの起動時**

**操作タブ**
- 「新規」→ 操作: **プログラムの開始**
- プログラム: `wsl.exe`
- 引数:
  ```
  -d Ubuntu -- bash -c "cd /mnt/c/Users/nakan/work/other/youtube-automation && nohup python scheduler.py >> output/logs/scheduler.log 2>&1"
  ```

4. 「OK」で保存

---

## systemd で常駐（WSL2 systemd 有効時）

`/etc/systemd/system/youtube-scheduler.service` を作成します。

```ini
[Unit]
Description=YouTube Shorts Auto Scheduler
After=network.target

[Service]
Type=simple
User=nakano
WorkingDirectory=/mnt/c/Users/nakan/work/other/youtube-automation
ExecStart=/usr/bin/python3 scheduler.py
Restart=on-failure
StandardOutput=append:/mnt/c/Users/nakan/work/other/youtube-automation/output/logs/scheduler.log
StandardError=append:/mnt/c/Users/nakan/work/other/youtube-automation/output/logs/scheduler.log

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable youtube-scheduler
sudo systemctl start youtube-scheduler
sudo systemctl status youtube-scheduler
```
