"""설교쇼츠제작에이전트 — Streamlit 메인 앱

흐름:
  1. 사용자 입력 (제목, 본문, 교회명, 설교 원고)
  2. Claude로 챕터 분할 + 씬 프롬프트 생성
  3. ElevenLabs TTS → mp3
  4. 제목/교회명 PIL 이미지
  5. Imagen 1:1 × 10 → 이미지
  6. Kling I2V 1:1 × 10 → 영상 클립 (~12분)
  7. FFmpeg 9:16 + 1:1 합성 → 최종 mp4
  8. 메타데이터 생성
  9. 다운로드 + 메타데이터 복사 UI

Streamlit Cloud 배포 시 secrets.toml에 모든 API 키 등록 필요.
"""

import sys
import time
import tempfile
import logging
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from pipeline.styles import PRESETS
from pipeline.analyze import analyze_sermon
from pipeline.tts import generate_tts
from pipeline.titles import render_title_image, render_church_image
from pipeline.images import generate_images
from pipeline.clips import generate_clips
from pipeline.compose import compose_final
from pipeline.metadata import generate_metadata


# ─── 페이지 설정 ─────────────────────────────────────────────────────
st.set_page_config(
    page_title="설교쇼츠제작에이전트",
    page_icon="🙏",
    layout="centered",
    initial_sidebar_state="expanded",
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

FONT_PATH = str(ROOT / "assets" / "fonts" / "NotoSansKR-Bold.otf")

# ─── Secrets 검증 ────────────────────────────────────────────────────
REQUIRED_SECRETS = [
    "ELEVENLABS_API_KEY", "ELEVENLABS_VOICE_ID",
    "GEMINI_API_KEY",
    "KLING_ACCESS_KEY", "KLING_SECRET_KEY",
    "ANTHROPIC_API_KEY",
]


def check_secrets():
    missing = [k for k in REQUIRED_SECRETS if k not in st.secrets]
    if missing:
        st.error(f"⚠️ Streamlit Secrets에 누락된 키: {', '.join(missing)}")
        st.info(
            "관리자에게 문의하세요. Streamlit Cloud의 App settings → Secrets 탭에 "
            "필요한 API 키를 등록해야 합니다."
        )
        st.stop()


# ─── 실행 디렉토리 (세션별 임시) ──────────────────────────────────────
def get_run_dir() -> Path:
    if "run_dir" not in st.session_state:
        st.session_state.run_dir = Path(tempfile.mkdtemp(prefix="shorts_"))
    return st.session_state.run_dir


# ─── 메인 파이프라인 ──────────────────────────────────────────────────
def run_pipeline(inputs: dict):
    """전체 생성 파이프라인. 진행 상황을 Streamlit UI에 표시."""
    run_dir = get_run_dir()
    images_dir = run_dir / "images"
    clips_dir = run_dir / "clips"
    audio_raw = run_dir / "narration_raw.mp3"
    audio_path = run_dir / "narration.mp3"
    srt_path = run_dir / "subtitles.srt"
    title_img = run_dir / "title.png"
    church_img = run_dir / "church.png"
    final_video = run_dir / "video_shorts.mp4"

    style_label, style_suffix = PRESETS[inputs["style_key"]]

    progress = st.progress(0, text="시작...")
    log_box = st.empty()

    def log(msg):
        log_box.info(msg)
        logging.info(msg)

    # ─── 1. 설교 분석 (Claude) ──────────────────────
    progress.progress(5, text="📖 설교 분석 중 (Claude)...")
    log("Claude로 설교 원고를 챕터/씬으로 분석합니다 (1~2분)")
    try:
        analysis = analyze_sermon(
            api_key=st.secrets["ANTHROPIC_API_KEY"],
            sermon_text=inputs["sermon_text"],
            title=inputs["title"],
            scripture=inputs["scripture"],
            style_label=style_label,
        )
    except Exception as e:
        st.error(f"설교 분석 실패: {e}")
        return None

    chapters = analysis["chapters"]
    scenes = analysis["scenes"]
    log(f"✓ 챕터 {len(chapters)}개 + 씬 {len(scenes)}개 생성")

    with st.expander("📝 자동 생성된 챕터 미리보기"):
        for i, ch in enumerate(chapters):
            st.markdown(f"**{i+1}. {ch.get('chapter_title', '')}** ({len(ch['script'])}자)")
            st.write(ch["script"])

    # ─── 2. 제목/교회명 이미지 ─────────────────────
    progress.progress(15, text="🎨 제목/교회명 이미지 생성...")
    render_title_image(inputs["title"], inputs["scripture"], title_img, FONT_PATH)
    render_church_image(inputs["church_name"], church_img, FONT_PATH)
    log("✓ 제목/교회명 이미지 완료")

    # ─── 3. TTS (ElevenLabs) ──────────────────────
    progress.progress(20, text="🎙️ 나레이션 생성 중 (ElevenLabs)...")
    duration = generate_tts(
        chapters=chapters,
        voice_id=st.secrets["ELEVENLABS_VOICE_ID"],
        api_key=st.secrets["ELEVENLABS_API_KEY"],
        audio_raw_path=str(audio_raw),
        audio_path=str(audio_path),
        srt_path=str(srt_path),
    )
    log(f"✓ 나레이션 {duration:.1f}초")

    # ─── 4. Imagen 이미지 (10장) ────────────────────
    progress.progress(30, text=f"🖼️ Imagen 이미지 생성 (0/{len(scenes)})...")

    def img_progress(idx, total, msg):
        pct = 30 + int(20 * idx / total)
        progress.progress(pct, text=f"🖼️ {msg} ({idx}/{total})")

    image_paths = generate_images(
        scenes=scenes,
        api_key=st.secrets["GEMINI_API_KEY"],
        images_dir=images_dir,
        style_suffix=style_suffix,
        progress_cb=img_progress,
    )
    log(f"✓ 이미지 {len(image_paths)}장 완료")

    # 이미지 미리보기
    with st.expander("🖼️ 생성된 이미지 미리보기", expanded=True):
        cols = st.columns(5)
        for i, p in enumerate(image_paths):
            cols[i % 5].image(p, caption=f"씬 {i+1}", use_container_width=True)

    # ─── 5. Kling I2V (10클립) ──────────────────────
    progress.progress(50, text=f"🎬 Kling I2V 영상 클립 생성 (0/{len(scenes)}, ~12분)...")

    def clip_progress(idx, total, msg):
        pct = 50 + int(35 * idx / total)
        progress.progress(pct, text=f"🎬 {msg} ({idx}/{total})")

    clip_paths = generate_clips(
        scenes=scenes,
        image_paths=image_paths,
        access_key=st.secrets["KLING_ACCESS_KEY"],
        secret_key=st.secrets["KLING_SECRET_KEY"],
        clips_dir=clips_dir,
        progress_cb=clip_progress,
    )
    success_count = sum(1 for c in clip_paths if c)
    log(f"✓ Kling 클립 {success_count}/{len(scenes)} 완료")

    if success_count < len(scenes) // 2:
        st.error(f"❌ Kling 생성 실패가 너무 많습니다 ({success_count}/{len(scenes)}). API 잔고를 확인하세요.")
        return None

    # ─── 6. FFmpeg 합성 ──────────────────────────────
    progress.progress(85, text="🎞️ 9:16 컴포지트 합성 중...")
    compose_final(
        clip_paths=clip_paths,
        audio_path=str(audio_path),
        title_img=str(title_img),
        church_img=str(church_img),
        output_path=str(final_video),
        bgm_path=None,  # MVP에선 BGM 없음
    )
    log(f"✓ 최종 영상 합성 완료")

    # ─── 7. 메타데이터 ───────────────────────────────
    progress.progress(95, text="📝 YouTube 메타데이터 생성...")
    sermon_summary = " ".join(ch["script"] for ch in chapters)
    metadata = generate_metadata(
        api_key=st.secrets["ANTHROPIC_API_KEY"],
        sermon_summary=sermon_summary,
        title=inputs["title"],
        scripture=inputs["scripture"],
        church_name=inputs["church_name"],
        duration_seconds=int(duration),
        style_label=style_label,
    )
    log("✓ 메타데이터 완료")

    progress.progress(100, text="✅ 모든 작업 완료!")
    log_box.empty()

    return {
        "video_path": final_video,
        "metadata": metadata,
        "duration": duration,
        "chapters": chapters,
        "scenes": scenes,
    }


# ═════════════════════════════════════════════════════════════════════
# UI
# ═════════════════════════════════════════════════════════════════════
st.title("🙏 설교쇼츠제작에이전트")
st.caption("설교 원고 → 약 1분 30초 유튜브 쇼츠 (자동)")

check_secrets()

# 사이드바
with st.sidebar:
    st.header("설정")
    style_key = st.selectbox(
        "그림 스타일",
        options=list(PRESETS.keys()),
        format_func=lambda k: PRESETS[k][0],
        index=0,
    )
    st.divider()
    st.caption(f"음성: `{st.secrets.get('ELEVENLABS_VOICE_ID', '미설정')[:8]}...`")
    if "app" in st.secrets:
        st.caption(f"기본 교회명: `{st.secrets['app'].get('default_church_name', '미설정')}`")
    st.divider()
    if st.button("🔄 새로 시작 (세션 초기화)"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

# ─── 1. 입력 ─────────────────────────────────────────────────────────
st.header("1. 설교 정보")

col1, col2 = st.columns(2)
with col1:
    sermon_title = st.text_input("설교 제목", placeholder="예: 사랑하라!")
with col2:
    scripture = st.text_input("성경 본문", placeholder="예: 요한복음 13:34-35")

default_church = st.secrets.get("app", {}).get("default_church_name", "")
church_name = st.text_input("교회명", value=default_church)

sermon_text = st.text_area(
    "설교 원고 (전체 또는 핵심 부분)",
    height=400,
    placeholder="여기에 설교 원고 전체를 붙여넣어 주세요.\n자동으로 1분 30초 분량의 핵심만 추출됩니다.",
)

# ─── 2. 생성 ─────────────────────────────────────────────────────────
st.header("2. 영상 생성")

st.warning(
    "⏱️ **약 15~20분 소요됩니다.** 생성 중에는 브라우저 탭을 닫지 마세요. "
    "탭을 닫으면 진행 상황이 사라집니다."
)

ready = bool(sermon_title and scripture and church_name and sermon_text)
generate_btn = st.button(
    "🎬 쇼츠 생성하기",
    type="primary",
    use_container_width=True,
    disabled=not ready or st.session_state.get("generating", False),
)

if generate_btn:
    st.session_state.generating = True
    st.session_state.result = None
    inputs = {
        "title": sermon_title,
        "scripture": scripture,
        "church_name": church_name,
        "sermon_text": sermon_text,
        "style_key": style_key,
    }
    try:
        result = run_pipeline(inputs)
        st.session_state.result = result
    except Exception as e:
        st.error(f"❌ 생성 중 오류: {e}")
        logging.exception("Pipeline error")
    finally:
        st.session_state.generating = False

# ─── 3. 결과 ─────────────────────────────────────────────────────────
if st.session_state.get("result"):
    result = st.session_state.result
    if result is None:
        st.stop()

    st.divider()
    st.header("3. 결과 — 다운로드 + 메타데이터")

    st.success(f"✅ 영상 생성 완료 ({result['duration']:.1f}초)")

    # 영상 미리보기 + 다운로드
    video_bytes = Path(result["video_path"]).read_bytes()
    st.video(video_bytes)
    st.download_button(
        "⬇️ mp4 다운로드",
        data=video_bytes,
        file_name=f"shorts_{int(time.time())}.mp4",
        mime="video/mp4",
        use_container_width=True,
        type="primary",
    )

    # 메타데이터
    meta = result["metadata"]
    st.subheader("📋 YouTube 메타데이터")
    st.markdown(f"**제목** ({len(meta['title'])}자)")
    st.code(meta["title"], language=None)

    st.markdown(f"**설명** ({len(meta['description'])}자)")
    st.code(meta["description"], language=None)

    st.markdown(f"**태그** ({len(meta['tags'])}개)")
    st.code(", ".join(meta["tags"]), language=None)

    st.markdown(f"**카테고리 ID**: `{meta['category_id']}` (People & Blogs)")

    st.info("💡 위 메타데이터를 복사해서 YouTube Studio 업로드 화면에 붙여넣으세요.")

# ─── 푸터 ────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "🛠️ ElevenLabs (TTS) · Imagen 4 (이미지) · Kling AI (I2V) · Anthropic Claude (분석/메타데이터)"
)
