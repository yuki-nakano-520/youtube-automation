import json
from dataclasses import dataclass, field
from pathlib import Path

import requests

from config import VOICEVOX_URL, VOICEVOX_SPEAKER_ID


class VoicevoxError(Exception):
    pass


@dataclass
class CharTiming:
    char: str
    start: float
    end: float


@dataclass
class VoiceResult:
    audio_path: Path
    duration: float
    char_timings: list[CharTiming] = field(default_factory=list)


def _check_voicevox() -> None:
    try:
        res = requests.get(f"{VOICEVOX_URL}/version", timeout=3)
        res.raise_for_status()
    except requests.exceptions.ConnectionError:
        raise VoicevoxError(
            f"VOICEVOXに接続できません。\n"
            f"VOICEVOXを起動してから再実行してください。\n"
            f"URL: {VOICEVOX_URL}"
        )


def _extract_char_timings(audio_query: dict, speed_scale: float) -> list[CharTiming]:
    """VOICEVOXのaudio_queryレスポンスからキャラクタータイミングを抽出する。"""
    timings: list[CharTiming] = []
    current_time = audio_query.get("prePhonemeLength", 0.0) / speed_scale

    for phrase in audio_query.get("accent_phrases", []):
        for mora in phrase.get("moras", []):
            consonant_len = (mora.get("consonant_length") or 0.0) / speed_scale
            vowel_len = mora.get("vowel_length", 0.0) / speed_scale
            duration = consonant_len + vowel_len

            text = mora.get("text", "")
            if text:
                timings.append(CharTiming(
                    char=text,
                    start=current_time,
                    end=current_time + duration,
                ))
            current_time += duration

        pause_mora = phrase.get("pause_mora")
        if pause_mora:
            current_time += pause_mora.get("vowel_length", 0.0) / speed_scale

    return timings


def generate_voice(
    text: str,
    output_path: str | Path,
    speaker_id: int | None = None,
    speed_scale: float = 1.1,
) -> VoiceResult:
    """
    VOICEVOXを使ってテキストをWAV音声に変換する。

    Returns:
        VoiceResult: 音声ファイルパスとタイミングデータ
    """
    _check_voicevox()

    sid = speaker_id if speaker_id is not None else VOICEVOX_SPEAKER_ID
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    query_res = requests.post(
        f"{VOICEVOX_URL}/audio_query",
        params={"text": text, "speaker": sid},
        timeout=30,
    )
    query_res.raise_for_status()
    audio_query: dict = query_res.json()

    audio_query["speedScale"] = speed_scale
    audio_query["intonationScale"] = 1.1
    audio_query["prePhonemeLength"] = 0.1
    audio_query["postPhonemeLength"] = 0.3

    char_timings = _extract_char_timings(audio_query, speed_scale)

    synthesis_res = requests.post(
        f"{VOICEVOX_URL}/synthesis",
        params={"speaker": sid},
        data=json.dumps(audio_query),
        headers={"Content-Type": "application/json"},
        timeout=60,
    )
    synthesis_res.raise_for_status()

    output_path.write_bytes(synthesis_res.content)

    # 実際の音声長を取得
    from moviepy.editor import AudioFileClip
    with AudioFileClip(str(output_path)) as clip:
        duration = clip.duration

    return VoiceResult(
        audio_path=output_path,
        duration=duration,
        char_timings=char_timings,
    )


def generate_voice_sections(
    sections: dict[str, str],
    output_dir: Path,
    speaker_id: int | None = None,
) -> dict[str, VoiceResult]:
    """
    スクリプトの各セクションごとに音声を生成する。

    Returns:
        セクション名 → VoiceResult のdict
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, VoiceResult] = {}

    for section_name, text in sections.items():
        path = output_dir / f"{section_name}.wav"
        print(f"  🎙️  [{section_name}] 音声生成中...")
        result[section_name] = generate_voice(text, path, speaker_id)

    return result
