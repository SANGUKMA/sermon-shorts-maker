"""Imagen — 1:1 이미지 생성

Imagen 4의 aspect_ratio="1:1" 사용 (1024×1024 출력).
크롭 불필요 — 1:1 영상 영역에 그대로 사용.

batch_delay 기본 12초 — Imagen 무료 티어 분당 5회 한도 회피.
각 호출 시작/완료를 INFO 로그로 출력 (어디서 멈췄는지 진단 가능).
"""

import time
import logging
from pathlib import Path
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


def generate_image_1_1(
    client,
    model: str,
    prompt: str,
    style_suffix: str,
    output_path: str,
    scene_id: int = None,
):
    """Imagen 4 — 1:1 정사각형 이미지"""
    tag = f"scene {scene_id}" if scene_id is not None else "image"
    logger.info(f"  Imagen 호출 시작 — {tag}")
    t0 = time.time()
    full_prompt = prompt + style_suffix
    try:
        response = client.models.generate_images(
            model=model,
            prompt=full_prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="1:1",
            )
        )
    except Exception as e:
        elapsed = time.time() - t0
        logger.error(f"  Imagen 호출 실패 — {tag} ({elapsed:.1f}s): {type(e).__name__}: {e}")
        raise

    if not response.generated_images:
        raise ValueError("Imagen 응답에 이미지가 없음")
    img_bytes = response.generated_images[0].image.image_bytes
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_bytes(img_bytes)
    elapsed = time.time() - t0
    logger.info(f"  Imagen 호출 완료 — {tag} ({elapsed:.1f}s)")
    return output_path


def generate_images(
    scenes: list,
    api_key: str,
    images_dir: Path,
    style_suffix: str,
    model: str = "imagen-4.0-generate-001",
    batch_delay: float = 12.0,
    max_retries: int = 3,
    progress_cb=None,
) -> list:
    """씬 리스트를 받아 1:1 이미지를 N장 생성.

    scenes: [{"scene_id": int, "image_prompt": str}, ...]
    progress_cb: optional callable(idx, total, msg) — Streamlit 진행 표시용
    batch_delay: 각 이미지 사이 대기 (분당 한도 회피)

    Returns: 생성된 이미지 경로 리스트
    """
    images_dir.mkdir(parents=True, exist_ok=True)
    client = genai.Client(api_key=api_key)

    paths = []
    for i, sc in enumerate(scenes):
        out = images_dir / f"scene_{sc['scene_id']:02d}.png"
        if out.exists():
            logger.info(f"[{i+1}/{len(scenes)}] 이미지 {sc['scene_id']} 재사용")
            if progress_cb:
                progress_cb(i + 1, len(scenes), f"이미지 {sc['scene_id']} 재사용")
            paths.append(str(out))
            continue

        logger.info(f"[{i+1}/{len(scenes)}] 이미지 {sc['scene_id']} 생성 시작")
        if progress_cb:
            progress_cb(i + 1, len(scenes), f"이미지 {sc['scene_id']} 생성 중")

        for attempt in range(max_retries):
            try:
                generate_image_1_1(
                    client, model, sc["image_prompt"], style_suffix, str(out),
                    scene_id=sc['scene_id'],
                )
                paths.append(str(out))
                break
            except Exception as e:
                logger.warning(f"이미지 {sc['scene_id']} 시도 {attempt+1}/{max_retries} 실패: {type(e).__name__}: {e}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(5)

        if i < len(scenes) - 1:
            logger.info(f"  다음 이미지 전 {batch_delay}초 대기 (분당 한도 회피)")
            time.sleep(batch_delay)

    logger.info(f"이미지 생성 전체 완료: {len(paths)}장")
    return paths
