"""설교 원고 분석 — Claude로 챕터/씬 자동 생성

입력: 설교 전체 원고 (긴 텍스트, ~5000자)
출력: 9-10개 챕터 (~960자 합계) + 10개 씬 프롬프트
"""

import json
import anthropic


SYSTEM_PROMPT = """You are an expert at converting Korean Christian sermon manuscripts \
into short-form video scripts. You produce JSON outputs that strictly follow the \
requested schema. Korean cultural context, Protestant theological accuracy, and \
visual storytelling are your core competencies."""


def analyze_sermon(
    api_key: str,
    sermon_text: str,
    title: str,
    scripture: str,
    style_label: str,
    target_chars: int = 960,
    n_scenes: int = 10,
    model: str = "claude-sonnet-4-20250514",
) -> dict:
    """설교 텍스트를 분석해 챕터(나레이션용) + 씬(영상 프롬프트) JSON 반환.

    Returns: {
        "chapters": [{"chapter_title": str, "script": str}, ...],
        "scenes": [{"scene_id": int, "image_prompt": str, "motion_prompt": str}, ...]
    }
    """
    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""아래 한국어 설교 원고를 분석해서 약 100초 분량(1.2배속 TTS 기준 ~960자) 쇼츠 스크립트로 압축하고, {n_scenes}개의 시각 씬 프롬프트를 만들어 주세요.

설교 제목: {title}
본문: {scripture}

═════════════════ 설교 원고 ═════════════════
{sermon_text}
═══════════════════════════════════════════════

결과는 반드시 아래 JSON 스키마로만 응답 (다른 설명 금지):

{{
  "chapters": [
    {{"chapter_title": "도입", "script": "한국어 나레이션 텍스트, 약 100자"}},
    ...
  ],
  "scenes": [
    {{"scene_id": 1, "image_prompt": "...영어...", "motion_prompt": "...영어..."}},
    ...
  ]
}}

────── chapters 규칙 ──────
- 8~10개 챕터, 각 80~130자, 합계 ~{target_chars}자 (1.2배속 TTS로 ~100초)
- 헬라어/히브리어 음역어, 학문적 전문용어 모두 제거 ("프로스카르테레오" → "끝까지 매달림")
- 입말 문장 (긴 종속절보다 끊어지는 짧은 문장)
- 설교 핵심 흐름 보존: 도입 → 본문 → 핵심 메시지 → 적용 → 격려

────── scenes 규칙 ──────
- 정확히 {n_scenes}개 씬 (scene_id 1부터)
- image_prompt: 영어, Imagen 1:1 정사각형용
  - 'Vertical portrait composition' 같은 비율 지정 금지 (1:1이므로)
  - 'centered composition' 권장 (센터 크롭 대비)
  - 한국인 모델, 현대 한국 배경 또는 성경 시대 적절히
  - 스타일 지시: {style_label}
  - 필수 금지: halos around heads, saint statues, ornate cathedral, gold filigree, Catholic icons
  - 권장: simple wooden cross, modest Protestant church interior, plain windows
- motion_prompt: 영어, 10초 분량을 채우는 **3단계 시간순 동작** (~30단어), Kling I2V용
  - 반드시 "First, ... Then, ... Finally, ..." 또는 "초반/중반/후반" 구조로 서로 다른 3개 동작 명시
  - 한 동작이 반복/루프되지 않도록 각 단계는 시각적으로 구별되는 변화여야 함
    (예: First, gentle wind moves the leaves. Then, the person slowly turns toward the light. Finally, hands open in a quiet prayer gesture.)
  - 카메라 움직임은 부드럽게 (slow pan, subtle push-in 등)
  - 자연스러운 움직임 우선 (바람, 빛 변화, 인물의 작은 동작)

────── 챕터 ↔ 씬 매핑 ──────
- 챕터 흐름과 씬 흐름이 자연스럽게 매핑되도록 (1챕터 = 1~2씬 정도)
- 시각적 다양성 확보 (실내/실외, 인물/풍경, 클로즈업/와이드 골고루)

JSON만 응답하세요."""

    msg = client.messages.create(
        model=model,
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    text = msg.content[0].text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    start, end = text.find("{"), text.rfind("}") + 1
    data = json.loads(text[start:end])

    # 검증
    if "chapters" not in data or "scenes" not in data:
        raise ValueError("Claude 응답에 chapters/scenes가 없음")
    if not isinstance(data["chapters"], list) or len(data["chapters"]) < 5:
        raise ValueError(f"챕터 수가 너무 적음: {len(data.get('chapters', []))}")
    if not isinstance(data["scenes"], list) or len(data["scenes"]) != n_scenes:
        raise ValueError(f"씬 수가 {n_scenes}이 아님: {len(data.get('scenes', []))}")

    return data
