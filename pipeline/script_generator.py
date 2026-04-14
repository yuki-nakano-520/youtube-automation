import json
from dataclasses import dataclass, field
from pathlib import Path

import anthropic

from config import ANTHROPIC_API_KEY, GENRES

_HISTORY_FILE = Path(__file__).parent.parent / "output" / "topics_history.json"
_MAX_HISTORY = 50


@dataclass
class ShortScript:
    topic: str
    hook: str
    body: str
    outro: str
    hashtags: list[str] = field(default_factory=list)
    search_query: str = ""  # Pexels検索用の英語キーワード

    @property
    def sections(self) -> dict[str, str]:
        return {"hook": self.hook, "body": self.body, "outro": self.outro}

    @property
    def full_text(self) -> str:
        return f"{self.hook}　{self.body}　{self.outro}"


def _load_topic_history() -> list[str]:
    if _HISTORY_FILE.exists():
        try:
            return json.loads(_HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save_topic(topic: str) -> None:
    history = _load_topic_history()
    if topic not in history:
        history.append(topic)
    history = history[-_MAX_HISTORY:]
    _HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    _HISTORY_FILE.write_text(
        json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def generate_script(
    genre_key: str = "trivia",
    trending_topics: list[str] | None = None,
) -> ShortScript:
    genre_label = GENRES.get(genre_key, GENRES["trivia"])
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    history = _load_topic_history()
    avoid_section = ""
    if history:
        recent = history[-20:]
        avoid_section = (
            "\n\n【絶対に使わないトピック（既出）】\n"
            + "\n".join(f"- {t}" for t in recent)
        )

    trending_section = ""
    if trending_topics:
        trending_section = (
            "\n\n【今日の日本のトレンドキーワード（関連する豆知識があれば積極活用）】\n"
            + "\n".join(f"- {t}" for t in trending_topics[:5])
        )

    prompt = f"""YouTubeショート動画（30〜45秒）用の「{genre_label}」スクリプトを作成してください。

以下のJSON形式のみで返してください：
{{
  "topic": "今回のトピック（例：カタツムリの歯は1万本以上ある）",
  "hook": "冒頭（1〜2文。以下のパターンを参考に視聴者を強く引き込む）",
  "body": "本題（3〜4文。具体的な数字・事実を含む豆知識）",
  "outro": "締め（1文。「〜だから〇〇なんだよ！」のような印象に残る言い方）",
  "hashtags": ["ハッシュタグ1", "ハッシュタグ2", "ハッシュタグ3", "ハッシュタグ4", "ハッシュタグ5"],
  "search_query": "トピックに関連する英語の映像検索キーワード（2〜3語、例：snail close up nature）"
}}

フックのパターン例（必ずどれか1つに近い形を使う）：
- 「〇〇って知ってた？実はヤバいことになってるんだよ！」
- 「え、これ知らないの？〇〇の衝撃の事実！」
- 「絶対に信じられない！〇〇の真実がヤバすぎる！」
- 「今すぐ友達に教えたい！〇〇って実は〜」
- 「학교では教えてくれない！〇〇の本当の姿とは？」
ポイント：疑問形・驚き・緊急感・損得感を必ず入れる

条件：
- 動物・食べ物・宇宙・人体・歴史・言語・テクノロジーなど幅広いジャンルから選ぶ
- 「バナナ」「ペンギン」「タコ」など偏らず多様なテーマを選ぶ
- 読み上げ時間が30〜45秒になる長さ
- わかりやすい口語体の日本語
- 「えっ本当に？」と思える驚きのある内容
- 具体的な数字を必ず1つ以上含める
- JSONのみを返す（コードブロック不要）{trending_section}{avoid_section}"""

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    data: dict = json.loads(raw.strip())

    script = ShortScript(
        topic=data["topic"],
        hook=data["hook"],
        body=data["body"],
        outro=data["outro"],
        hashtags=data.get("hashtags", []),
        search_query=data.get("search_query", data["topic"]),
    )
    _save_topic(script.topic)
    return script
