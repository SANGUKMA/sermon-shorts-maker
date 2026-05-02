"""FFmpeg 합성 — 9:16 캔버스 + 1:1 영상 영역

레이아웃:
   y=   0..560   상단 네이비 (제목)
   y= 560..1640  영상 영역 1080×1080 (1:1)
   y=1640..1920  하단 네이비 (교회명)

기존 4:5 클립도 increase + crop으로 1:1 센터 크롭됨.
"""

import shutil
import subprocess
import tempfile
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# 캔버스
W = 1080
H = 1920
TOP_BAR_H = 560
VIDEO_H = 1080
BOTTOM_BAR_H = 280
NAVY_HEX = "0x0F2557"


def concat_clips(clip_paths: list, out_path: str, work_dir: Path):
    """N개 Kling 클립을 하나로 이어붙임 (재인코딩 통일)"""
    valid = [c for c in clip_paths if c and Path(c).exists()]
    if not valid:
        raise RuntimeError("유효한 Kling 클립이 없습니다")

    list_file = work_dir / "concat.txt"
    list_file.write_text(
        "\n".join(f"file '{Path(c).resolve().as_posix()}'" for c in valid),
        encoding="utf-8",
    )
    subprocess.run([
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
        "-f", "concat", "-safe", "0", "-i", str(list_file),
        "-c:v", "libx264", "-preset", "medium", "-crf", "16",
        "-pix_fmt", "yuv420p", "-r", "30",
        "-an", out_path,
    ], check=True, capture_output=True, text=True, encoding="utf-8",
       errors="replace")


def compose_final(
    clip_paths: list,
    audio_path: str,
    title_img: str,
    church_img: str,
    output_path: str,
    bgm_path: str = None,
    bgm_volume: float = 0.04,
):
    """4:5 또는 1:1 Kling 클립들을 9:16 캔버스에 합성.

    - 영상 영역(1:1)은 increase + crop으로 센터 크롭 (꽉 채움)
    - 끝 3초 정지프레임 (tpad)으로 나레이션 잘림 방지
    - BGM은 옵션 (파일 있으면 4% 볼륨으로 믹스)
    """
    work = Path(tempfile.mkdtemp(prefix="sermon_shorts_"))
    try:
        # 1) 클립 concat
        concat_path = work / "concat.mp4"
        concat_clips(clip_paths, str(concat_path), work)

        # 2) ASCII 작업 디렉토리에 입력 복사 (한글 경로 회피)
        in_video = work / "input.mp4"
        in_audio = work / "narration.mp3"
        in_title = work / "title.png"
        in_church = work / "church.png"
        out_a = work / "output.mp4"
        shutil.copy2(concat_path, in_video)
        shutil.copy2(audio_path, in_audio)
        shutil.copy2(title_img, in_title)
        shutil.copy2(church_img, in_church)

        bgm_input = []
        bgm_filter = ""
        bgm_map = "1:a"
        if bgm_path and Path(bgm_path).exists():
            in_bgm = work / "bgm.mp3"
            shutil.copy2(bgm_path, in_bgm)
            bgm_input = ["-stream_loop", "-1", "-i", "bgm.mp3"]
            bgm_filter = (
                ";[1:a]volume=1.0[an];"
                f"[4:a]volume={bgm_volume}[bgm];"
                "[an][bgm]amix=inputs=2:duration=first:normalize=0[aout]"
            )
            bgm_map = "[aout]"

        # 3) 비디오 필터 그래프
        # increase + crop = 영상 영역을 꽉 채우는 센터 크롭
        # tpad = 끝 3초 정지프레임 (나레이션 잘림 방지)
        video_filter = (
            f"color=c={NAVY_HEX}:s={W}x{H}:r=30,setpts=PTS-STARTPTS[bg];"
            f"[0:v]scale={W}:{VIDEO_H}:force_original_aspect_ratio=increase,"
            f"crop={W}:{VIDEO_H},"
            f"tpad=stop_duration=3:stop_mode=clone,"
            f"setsar=1[vid];"
            f"[bg][vid]overlay=0:{TOP_BAR_H}:shortest=1[v1];"
            f"[v1][2:v]overlay=0:0[v2];"
            f"[v2][3:v]overlay=0:{TOP_BAR_H + VIDEO_H}[vout]"
        )

        full_filter = video_filter + bgm_filter

        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning",
            "-i", "input.mp4",
            "-i", "narration.mp3",
            "-i", "title.png",
            "-i", "church.png",
            *bgm_input,
            "-filter_complex", full_filter,
            "-map", "[vout]", "-map", bgm_map,
            "-c:v", "libx264", "-preset", "medium", "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            "-shortest",
            "output.mp4",
        ]

        r = subprocess.run(cmd, cwd=str(work), capture_output=True,
                           text=True, encoding="utf-8", errors="replace",
                           timeout=900)
        if r.returncode != 0:
            logger.error(f"FFmpeg 에러:\n{r.stderr[:2000]}")
            raise subprocess.CalledProcessError(r.returncode, cmd)

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        if Path(output_path).exists():
            Path(output_path).unlink()
        shutil.copy2(out_a, output_path)
    finally:
        shutil.rmtree(work, ignore_errors=True)
