"""스타일 프리셋 — Imagen prompt suffix"""

EUROPEAN_COMIC = (
    ", European comic book art style, ligne claire technique like Tintin or Moebius, "
    "uniform-weight clean black ink outlines, flat solid colors with no gradients, "
    "cel-shaded flat coloring, clear and crisp line art, "
    "Protestant Christian setting (NOT Catholic), modern and simple church atmosphere, "
    "absolutely no halos around heads, no saint statues, no ornate cathedral decoration, "
    "no gold filigree, no painted religious icons on walls, "
    "simple plain wooden cross only, modest church interior with wooden pews, "
    "natural daylight from plain windows (no stained glass with figures), "
    "warm but reserved color palette"
)

JAPANESE_ANIME = (
    ", Japanese anime style, cel-shaded animation, Studio Ghibli inspired, "
    "Makoto Shinkai cinematic lighting, vibrant colors, soft anime line art, "
    "painterly background, dramatic god rays, hand-drawn 2D animation feel, "
    "Kyoto Animation quality, beautifully detailed sky"
)

PRESETS = {
    "europe_comic": ("유럽 만화 (Tintin/Moebius, 개신교 분위기)", EUROPEAN_COMIC),
    "japanese_anime": ("일본 애니메이션 (Studio Ghibli, Makoto Shinkai)", JAPANESE_ANIME),
}
