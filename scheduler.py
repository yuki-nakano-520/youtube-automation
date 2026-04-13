"""
YouTube Shorts 自動投稿スケジューラー

使い方:
  python scheduler.py           # スケジューラーを起動（常駐モード）
  python scheduler.py --now     # 即時1回実行して終了（動作確認用）
  python scheduler.py --status  # 登録済みスケジュール一覧を表示して終了

.env で以下の変数を設定してスケジュールをカスタマイズできます:
  POST_GENRES_CYCLE  投稿するジャンルの順番（カンマ区切り）
  POST_TIMES         投稿時刻（カンマ区切り、例: 09:00,21:00）
  POST_DAYS          投稿曜日（カンマ区切り、例: mon,wed,fri）
  POST_PRIVACY       公開設定（public / unlisted / private）
  POST_COUNT_PER_RUN 1回の実行で生成・投稿する本数
"""

import argparse
import logging
import sys
import time
from itertools import cycle
from pathlib import Path

import schedule

from config import (
    GENRES,
    POST_COUNT_PER_RUN,
    POST_DAYS,
    POST_GENRES_CYCLE,
    POST_PRIVACY,
    POST_TIMES,
)
from main import run

# ──────────────────────────────────────────
# ロガー設定
# ──────────────────────────────────────────

_LOG_DIR = Path(__file__).parent / "output" / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(_LOG_DIR / "scheduler.log", encoding="utf-8"),
    ],
)

_logger = logging.getLogger(__name__)

# ──────────────────────────────────────────
# ジャンルローテーション
# ──────────────────────────────────────────

# 設定されたジャンルのうち有効なものだけを使用
_valid_genres = [g for g in POST_GENRES_CYCLE if g in GENRES]
if not _valid_genres:
    _logger.warning("POST_GENRES_CYCLE に有効なジャンルがありません。デフォルト(trivia)を使用します。")
    _valid_genres = ["trivia"]

_genre_iter = cycle(_valid_genres)

# ──────────────────────────────────────────
# 投稿ジョブ
# ──────────────────────────────────────────

def _post_job() -> None:
    genre = next(_genre_iter)
    _logger.info(f"▶ 自動投稿ジョブ開始 — ジャンル: {GENRES[genre]}  本数: {POST_COUNT_PER_RUN}")
    try:
        run(
            genre=genre,
            count=POST_COUNT_PER_RUN,
            upload=True,
            privacy=POST_PRIVACY,
        )
        _logger.info("✅ 自動投稿ジョブ完了")
    except Exception as e:
        _logger.exception(f"❌ 自動投稿ジョブ失敗: {e}")


# ──────────────────────────────────────────
# スケジュール登録
# ──────────────────────────────────────────

_DAY_LABEL: dict[str, str] = {
    "mon": "月曜",
    "tue": "火曜",
    "wed": "水曜",
    "thu": "木曜",
    "fri": "金曜",
    "sat": "土曜",
    "sun": "日曜",
}

_DAY_ATTR: dict[str, str] = {
    "mon": "monday",
    "tue": "tuesday",
    "wed": "wednesday",
    "thu": "thursday",
    "fri": "friday",
    "sat": "saturday",
    "sun": "sunday",
}


def _register_schedules() -> int:
    """スケジュールを登録し、登録件数を返す。"""
    registered = 0
    for day_key in POST_DAYS:
        day_key = day_key.strip().lower()
        day_attr = _DAY_ATTR.get(day_key)
        if not day_attr:
            _logger.warning(f"⚠️  不明な曜日: '{day_key}'（スキップ）")
            continue
        for time_str in POST_TIMES:
            time_str = time_str.strip()
            getattr(schedule.every(), day_attr).at(time_str).do(_post_job)
            label = _DAY_LABEL.get(day_key, day_key)
            _logger.info(f"📅 スケジュール登録: 毎週{label} {time_str}  公開設定={POST_PRIVACY}")
            registered += 1
    return registered


def _print_status() -> None:
    _register_schedules()
    jobs = schedule.get_jobs()
    if not jobs:
        print("登録されたスケジュールはありません。")
        return
    print(f"\n登録済みスケジュール ({len(jobs)}件):")
    for job in jobs:
        print(f"  次回実行: {job.next_run}  [{job}]")


# ──────────────────────────────────────────
# エントリポイント
# ──────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="YouTube Shorts 自動投稿スケジューラー",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--now", action="store_true", help="即時1回実行して終了（動作確認用）")
    parser.add_argument("--status", action="store_true", help="登録済みスケジュール一覧を表示して終了")
    args = parser.parse_args()

    if args.status:
        _print_status()
        return

    if args.now:
        _logger.info("⚡ 即時実行モード（--now）")
        _post_job()
        return

    # 常駐モード
    _logger.info("🚀 スケジューラー起動")
    _logger.info(f"  ジャンルサイクル : {' → '.join(_valid_genres)}")
    _logger.info(f"  投稿時刻         : {', '.join(POST_TIMES)}")
    _logger.info(f"  投稿曜日         : {', '.join(POST_DAYS)}")
    _logger.info(f"  公開設定         : {POST_PRIVACY}")
    _logger.info(f"  1回あたりの本数  : {POST_COUNT_PER_RUN}")

    count = _register_schedules()
    if count == 0:
        _logger.error("有効なスケジュールが1件も登録されませんでした。設定を確認してください。")
        sys.exit(1)

    _logger.info("⏳ スケジュール待機中... (Ctrl+C で終了)")
    _logger.info(f"📋 ログ出力先: {_LOG_DIR / 'scheduler.log'}")

    try:
        while True:
            schedule.run_pending()
            time.sleep(30)
    except KeyboardInterrupt:
        _logger.info("🛑 スケジューラー停止")


if __name__ == "__main__":
    main()
