"""YouTube 메타데이터 생성 — Anthropic Claude

설교 본문 + 채널 정보 → 제목/설명/태그/카테고리 JSON.
"""

import json
import anthropic


def generate_metadata(
    api_key: str,
    sermon_summary: str,
    title: str,
    scripture: str,
    church_name: str,
    pastor_name: str = "",
    duration_seconds: int = 100,
    style_label: str = "유럽 만화 일러스트 + Kling AI I2V 애니메이션",
    model: str = "claude-sonnet-4-6",
) -> dict:
    """설교 정보를 받아 YouTube 메타데이터 dict 반환.

    Returns: {"title": str, "description": str, "tags": list[str], "category_id": "22"}
    """
    client = anthropic.Anthropic(api_key=api_key)

    prompt = (
        "YouTube SEO 전문가로서 아래 기독교 설교 쇼츠의 메타데이터를 생성해줘.\n\n"
        f"영상 제목: {title}\n"
        f"본문: {scripture}\n"
        f"채널: {church_name}" + (f" ({pastor_name})" if pastor_name else "") + "\n"
        f"분량: 약 {duration_seconds//60}분 {duration_seconds%60}초 (YouTube Shorts, 9:16, 1:1 영상 영역)\n"
        f"스타일: {style_label}\n\n"
        f"설교 핵심 내용:\n{sermon_summary}\n\n"
        "반드시 아래 JSON으로만 응답 (다른 텍스트 없이):\n"
        '{"title": "...", "description": "...", "tags": [...]}\n\n'
        "규칙:\n"
        "- title: 95자 이내, 끝에 ' #Shorts' 포함, 영적 호기심을 끄는 호소형\n"
        "- description: 핵심 메시지 2~3줄 → 빈줄 → 본문 인용 → 빈줄 → "
        "설교 요점 3~4가지 → 빈줄 → 격려 한 줄 → 빈줄 → 채널 안내 → 빈줄 → 해시태그\n"
        "- tags: 15~20개 (한글/영문 병행, '설교', '쇼츠', '기독교', "
        f"'{church_name.replace(' ', '')}' 등 포함)\n"
        "- description 길이: 2000자 이내\n"
        "- category_id 는 포함하지 마"
    )

    msg = client.messages.create(
        model=model,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    start, end = text.find("{"), text.rfind("}") + 1
    meta = json.loads(text[start:end])

    # 보강
    title_out = meta.get("title", title).strip()
    if "#shorts" not in title_out.lower() and len(title_out) <= 92:
        title_out = f"{title_out} #Shorts"
    meta["title"] = title_out[:100]

    desc = meta.get("description", "").strip()
    if "#shorts" not in desc.lower():
        desc += "\n\n#Shorts"
    meta["description"] = desc[:5000]

    tags = meta.get("tags", [])
    lowered = {t.lower() for t in tags}
    must_haves = ["Shorts", "shorts", "설교", "쇼츠", "기독교", "주일설교",
                  church_name.replace(" ", "")]
    for must in must_haves:
        if must.lower() not in lowered:
            tags.append(must)
            lowered.add(must.lower())
    meta["tags"] = tags[:30]
    meta["category_id"] = "22"  # People & Blogs

    return meta
