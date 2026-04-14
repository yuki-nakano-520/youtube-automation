"""
Google Trends RSS フィードから日本のトレンドトピックを取得するモジュール。
pytrends ライブラリの互換性問題を避けるため、直接 RSS を解析する方式を採用。
取得失敗時は空リストを返し、パイプラインを止めない。
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import requests

_TRENDS_RSS_URL = "https://trends.google.co.jp/trending/rss?geo=JP"


def fetch_trending_topics(count: int = 10) -> list[str]:
    """
    Google Trends RSS から日本のトレンドキーワードを取得する。

    Args:
        count: 取得するトピック数

    Returns:
        トレンドキーワードのリスト（取得失敗時は空リスト）
    """
    try:
        resp = requests.get(_TRENDS_RSS_URL, timeout=10)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        topics: list[str] = []
        for item in root.iter("item"):
            title_el = item.find("title")
            if title_el is not None and title_el.text:
                topics.append(title_el.text.strip())
            if len(topics) >= count:
                break
        return topics
    except Exception as e:
        print(f"  [warn] トレンド取得失敗 ({e})。トレンドなしで続行します。")
        return []
