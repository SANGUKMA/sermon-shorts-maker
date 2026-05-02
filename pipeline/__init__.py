"""쇼츠 제작 파이프라인 모듈

순서:
  1. tts.py     — ElevenLabs로 나레이션 mp3 생성
  2. images.py  — Imagen 4로 1:1 이미지 N장 생성
  3. clips.py   — Kling I2V로 각 이미지를 10초 영상으로 (30s 딜레이 + 429 재시도)
  4. compose.py — FFmpeg로 9:16 캔버스에 합성 (상단 제목 / 1:1 영상 / 하단 교회명)
  5. metadata.py — Anthropic Claude로 YouTube 메타데이터 생성
  6. titles.py  — PIL로 제목/교회명 이미지 (자동 폰트 축소)
"""
