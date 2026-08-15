# CLAUDE.md

## 프로젝트 컨텍스트 (이 repo만의 가드레일)

이 repo는 **다른 교회 목사님이 사용할 공개 Streamlit 앱**입니다. 개인 실험용 자매 repo(`C:/dev/영상자동화`)와는 청자/목적/배포 모델이 다릅니다.

### 절대 지켜야 할 규칙

- **API 키는 Streamlit Secrets만 사용**. 절대 repo에 커밋 금지. `.streamlit/secrets.toml`은 `.gitignore`에 등록되어 있음.
- **ElevenLabs 보이스 ID는 Streamlit Secrets에서 읽기**. `Professor ma`(W9zbcgJ4rDpkhoG8WtRU)는 자매 repo 사용자 본인 음성 클론 — **이 앱에서 사용 금지**. 사용자(다른 목사)가 제공한 본인 voice_id만 사용.
- **YouTube 자동 업로드 코드 추가 금지**. v1 MVP는 mp4 다운로드 + 메타데이터 표시까지만. OAuth 흐름·refresh token 저장 로직 추가하지 말 것. 사용자가 수동으로 YouTube Studio에 업로드.
- **레이아웃은 9:16 캔버스 + 1:1 영상 영역 고정**. 1080×1920 외부, 1080×1080 내부. 자매 repo 패턴 답습.
- **폰트 경로는 `assets/fonts/NotoSansKR-Bold.ttf` 사용**. Windows 경로(`C:/Windows/Fonts/...`) 절대 사용 금지 — Streamlit Cloud는 Linux.
- **Streamlit Cloud는 ephemeral 파일시스템**. 영구 저장 가정 코드 금지. 생성 결과는 사용자가 즉시 다운로드해야 한다는 가정으로 작성.

### 자매 repo (코드 출처)

- 경로: `C:/dev/영상자동화/`
- 동일한 patterns: `make_*_sermon_shorts.py`, `gen_*_metadata.py` (이 repo의 `pipeline/` 모듈로 추출)
- providers/ 폴더는 자매 repo에서 복사 — 1년에 한두 번 변경 시 수동 sync
- 자매 repo는 본인(개발자)의 개인 작업용. 이 repo는 외부 사용자용

### 기술 스택

- Streamlit (UI)
- ElevenLabs API (TTS, voice clone)
- Google Imagen 4 API (1:1 이미지 생성)
- Kling AI API (I2V, std mode v2-6, 10s)
- Anthropic Claude API (메타데이터 생성)
- FFmpeg (합성)
- PIL/Pillow (제목/교회명 이미지)

### 사용량 제어 (이미 학습한 위험)

- Kling API는 **계정별 동시성 한도** 있음. 각 클립 사이 30초 대기 + 429 백오프 필수. 예전에 8개 연속 제출하다 모두 실패한 경험.
- **Kling 429는 두 가지 뜻**. 진짜 rate limit이면 백오프가 맞지만, 응답 본문 `code:1102`("Account balance not enough")는 기다려도 절대 안 풀린다. `raise_for_status()`는 본문을 버리므로 429일 때 본문을 직접 읽어야 구분 가능. `pipeline/clips.py`가 1102면 즉시 중단하도록 처리됨 — 안 그러면 10씬 × 30/90/180초 = **약 50분 대기 후 실패**.
- **Kling 웹 크레딧 ≠ API 리소스 팩**. app.klingai.com 화면에 크레딧이 남아 있어도 API는 1102를 낸다. `GET /account/costs`의 `resource_pack_subscribe_infos`가 비어 있으면 팩이 없는 것. 별도 구매 필요.
- **리소스 팩은 구매 직후 API에 즉시 반영되지 않는다.** 팩 `effective_time` 이후 37초 시점 호출이 여전히 1102였고, 그 다음 시도에서 통과. 구매 직후 실패하면 키·코드부터 의심하지 말고 1분쯤 뒤 재시도할 것.
- Imagen은 분당 6초 정도 batch_delay 권장.
- ElevenLabs Professor ma(W9zbcgJ4rDpkhoG8WtRU) 같은 voice_id를 다른 사람이 사용하면 안 됨.

### 향후 변동축 (확장 시 고려)

- 다중 교회 지원 (현재는 1 deployment = 1 pastor)
- YouTube 자동 업로드 추가 (v2 — 현재는 수동)
- 음성 선택 UI (지금은 secrets에 박힌 voice_id만)
- 스타일 프리셋 추가 (Japanese anime / European comic 외)

---

## 코딩 원칙 (출처: forrestchang/andrej-karpathy-skills)

Behavioral guidelines to reduce common LLM coding mistakes.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

### 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

### 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
