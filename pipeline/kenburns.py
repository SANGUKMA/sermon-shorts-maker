"""Ken Burns — 정지 이미지에 팬/줌 모션 (Kling 대체)

Kling I2V는 초당 0.3 unit이라 10씬 100초면 30 unit이 든다. 뒷부분 씬은
인물 미세 동작이 크게 중요하지 않아 ffmpeg zoompan으로 대체한다.

출력 규격은 Kling 클립과 반드시 같아야 한다 (960×960, h264, yuv420p).
concat 데뮤서가 해상도가 다른 입력을 이어붙이지 못하기 때문.
"""

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

SIZE = 960
FPS = 30

# 씬마다 다른 움직임 — 같은 방향만 반복되면 지루하다
MOVES = [
    ("push_in", "z='min(zoom+0.0004,1.18)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"),
    ("pull_out", "z='if(lte(zoom,1.0),1.18,max(1.001,zoom-0.0004))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"),
    ("pan_right", "z='1.15':x='(iw-iw/zoom)*(on/{frames})':y='ih/2-(ih/zoom/2)'"),
    ("pan_left", "z='1.15':x='(iw-iw/zoom)*(1-on/{frames})':y='ih/2-(ih/zoom/2)'"),
    ("pan_down", "z='1.15':x='iw/2-(iw/zoom/2)':y='(ih-ih/zoom)*(on/{frames})'"),
]


def generate_kenburns_clip(image_path: str, output_path: str,
                           duration: int = 10, move_idx: int = 0):
    """이미지 1장 → 팬/줌 모션 클립"""
    frames = duration * FPS
    name, expr = MOVES[move_idx % len(MOVES)]
    expr = expr.format(frames=frames)

    # zoompan은 원본 해상도에서 계산하면 픽셀 단위로 튄다.
    # 4배 업스케일 후 줌하고 최종 크기로 내려야 움직임이 매끄럽다.
    vf = (
        f"scale={SIZE*4}:{SIZE*4}:force_original_aspect_ratio=increase,"
        f"crop={SIZE*4}:{SIZE*4},"
        f"zoompan={expr}:d={frames}:s={SIZE}x{SIZE}:fps={FPS},"
        f"setsar=1"
    )
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
        "-loop", "1", "-i", image_path,
        "-vf", vf, "-t", str(duration),
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-r", str(FPS), "-an",
        output_path,
    ], check=True, capture_output=True, text=True, encoding="utf-8",
       errors="replace")
    return name


def generate_kenburns_clips(scenes: list, image_paths: list, clips_dir: Path,
                            duration: int = 10, progress_cb=None) -> list:
    """씬 리스트를 Ken Burns 클립으로. generate_clips와 같은 형태를 돌려준다.

    Returns: (clip_paths, errors) — Kling 쪽과 인터페이스 통일
    """
    clips_dir.mkdir(parents=True, exist_ok=True)
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
            progress_cb(i + 1, len(scenes), f"클립 {sc['scene_id']} 모션 생성")
        try:
            move = generate_kenburns_clip(img, str(out), duration, move_idx=i)
            logger.info(f"  Ken Burns 클립 {sc['scene_id']} ({move})")
            clip_paths.append(str(out))
        except Exception as e:
            logger.error(f"Ken Burns 클립 {sc['scene_id']} 실패: {e}")
            errors.append(f"씬 {sc['scene_id']}: {str(e)[:200]}")
            clip_paths.append("")

    return clip_paths, errors
