"""TTS — ElevenLabs로 나레이션 생성

자매 repo의 ElevenLabsProvider를 그대로 사용. 챕터 단위로 음성 생성 후
ffmpeg atempo로 1.2배속 가속.
"""

import logging
import shutil
import subprocess
from pathlib import Path
from pydub import AudioSegment

from providers.tts.elevenlabs_provider import ElevenLabsProvider

logger = logging.getLogger(__name__)


def get_audio_duration(path: str) -> float:
    return len(AudioSegment.from_mp3(path)) / 1000.0


def speedup_audio(src: str, dst: str, factor: float = 1.2):
    """ffmpeg atempo로 음정 유지하며 가속. factor=1.0이면 단순 복사."""
    if abs(factor - 1.0) < 0.001:
        shutil.copy2(src, dst)
        return
    subprocess.run(
        ["ffmpeg", "-y", "-i", src, "-filter:a", f"atempo={factor}",
         "-vn", "-c:a", "libmp3lame", "-q:a", "2", dst],
        check=True, capture_output=True,
    )


def generate_tts(
    chapters: list,
    voice_id: str,
    api_key: str,
    audio_raw_path: str,
    audio_path: str,
    srt_path: str,
    speed: float = 1.2,
    model_id: str = "eleven_multilingual_v2",
    stability: float = 0.5,
    similarity_boost: float = 0.75,
) -> float:
    """챕터 리스트로 TTS 생성 → 가속본 mp3 + SRT.

    Returns: 최종 음성 길이(초)
    """
    if Path(audio_path).exists() and Path(srt_path).exists():
        logger.info(f"TTS 재사용: {audio_path}")
        return get_audio_duration(audio_path)

    cfg = {
        "voice_id": voice_id,
        "model_id": model_id,
        "stability": stability,
        "similarity_boost": similarity_boost,
    }
    provider = ElevenLabsProvider(api_key=api_key, cfg=cfg)
    Path(audio_raw_path).parent.mkdir(parents=True, exist_ok=True)
    provider.generate_chapters(chapters, audio_raw_path, srt_path)
    speedup_audio(audio_raw_path, audio_path, speed)
    return get_audio_duration(audio_path)
