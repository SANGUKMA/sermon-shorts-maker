"""Kling I2V — 각 이미지를 10초 영상으로

이미 검증된 패턴:
  - 각 씬 사이 30초 대기 (Kling 동시성 한도 회피)
  - 429 발생 시 30s/90s/180s 백오프 재시도
  - 클립당 ~1분 (60s 생성 + 다운로드)
  - 10클립 총 ~12~15분
"""

import time
import logging
from pathlib import Path

from providers.video.kling_provider import KlingI2VProvider

logger = logging.getLogger(__name__)

DEFAULT_NEGATIVE = "blurry, distorted, text, watermark, low quality, deformed"


def generate_clips(
    scenes: list,
    image_paths: list,
    access_key: str,
    secret_key: str,
    clips_dir: Path,
    model: str = "kling-v2-6",
    duration: int = 10,
    mode: str = "std",
    cfg_scale: float = 0.5,
    poll_interval: int = 10,
    timeout: int = 600,
    inter_scene_delay: int = 30,
    progress_cb=None,
) -> list:
    """씬별로 Kling I2V 클립 생성. 각 씬 사이 30초 대기.

    scenes: [{"scene_id": int, "motion_prompt": str}, ...]
    image_paths: scenes와 같은 순서로 매칭된 이미지 경로
    progress_cb: optional callable(idx, total, msg)

    Returns: 생성된 mp4 경로 리스트 (실패 시 빈 문자열)
    """
    clips_dir.mkdir(parents=True, exist_ok=True)
    provider = KlingI2VProvider(
        access_key=access_key,
        secret_key=secret_key,
        model=model,
        duration=duration,
        mode=mode,
        cfg_scale=cfg_scale,
        poll_interval=poll_interval,
        timeout=timeout,
    )

    clip_paths = []
    errors = []
    for i, (sc, img) in enumerate(zip(scenes, image_paths)):
        out = clips_dir / f"scene_{sc['scene_id']:02d}.mp4"

        if out.exists():
            if progress_cb:
                progress_cb(i + 1, len(scenes), f"클립 {sc['scene_id']} 재사용")
            clip_paths.append(str(out))
            continue

        if progress_cb:
            progress_cb(i + 1, len(scenes), f"클립 {sc['scene_id']} 생성 중 (~1분)")

        # 429 백오프 재시도
        backoffs = [30, 90, 180]
        success = False
        last_err = ""
        for attempt, wait_after in enumerate(backoffs):
            try:
                provider.generate(
                    image_path=img,
                    output_path=str(out),
                    prompt=sc["motion_prompt"],
                    negative_prompt=DEFAULT_NEGATIVE,
                )
                success = True
                clip_paths.append(str(out))
                break
            except Exception as e:
                last_err = str(e)
                if "429" in last_err:
                    logger.warning(f"클립 {sc['scene_id']} 429 (시도 {attempt+1}/3) — {wait_after}s 대기")
                    if progress_cb:
                        progress_cb(i + 1, len(scenes),
                                    f"클립 {sc['scene_id']} 한도 초과, {wait_after}초 대기")
                    time.sleep(wait_after)
                    continue
                logger.error(f"클립 {sc['scene_id']} 실패: {e}")
                errors.append(f"씬 {sc['scene_id']}: {last_err[:200]}")
                clip_paths.append("")
                break

        if not success and len(clip_paths) <= i:
            clip_paths.append("")
            if last_err and not any(f"씬 {sc['scene_id']}:" in x for x in errors):
                errors.append(f"씬 {sc['scene_id']}: {last_err[:200]}")

        if i < len(scenes) - 1:
            time.sleep(inter_scene_delay)

    return clip_paths, errors
