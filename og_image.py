"""
OG 이미지 생성기 — 1200×630 PNG
================================

각 페이지마다 카카오톡/트위터/페이스북 공유 시 표시되는 카드 이미지를
미리 빌드해서 정적 파일로 서빙. PIL 사용 (헤드리스 브라우저 불필요).

폰트 폴백 체인:
  macOS: AppleSDGothicNeo.ttc
  Linux (GitHub Actions): Noto Sans CJK
  최후: PIL default (영문만, 한글 □)

캐시:
  YouTube 썸네일은 .cache_thumbs/ 에 다운로드 후 재사용
"""

import urllib.request
from functools import lru_cache
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 630
BG = (10, 10, 15)
FG = (255, 255, 255)
MUTED = (170, 170, 170)
DIM = (130, 130, 130)
ACCENT = (255, 0, 51)
COVER_SIZE = 460
COVER_X = 80
COVER_Y = (H - COVER_SIZE) // 2

# 폰트 후보 (앞에서부터 찾기)
FONT_BOLD_PATHS = [
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJKkr-Bold.otf",
]
FONT_REG_PATHS = [
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJKkr-Regular.otf",
]
# TTC 내 인덱스: AppleSDGothicNeo는 0=Regular, 5=Bold
TTC_BOLD_INDEX = 5
TTC_REG_INDEX = 0


@lru_cache(maxsize=64)
def load_font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    paths = FONT_BOLD_PATHS if weight == "bold" else FONT_REG_PATHS
    index = TTC_BOLD_INDEX if weight == "bold" else TTC_REG_INDEX
    for path in paths:
        if not Path(path).exists():
            continue
        try:
            if path.endswith(".ttc"):
                return ImageFont.truetype(path, size, index=index)
            return ImageFont.truetype(path, size)
        except (OSError, ValueError):
            continue
    return ImageFont.load_default()


def fetch_thumb(video_id: str) -> Image.Image:
    cache = Path(".cache_thumbs") / f"{video_id}.jpg"
    cache.parent.mkdir(exist_ok=True)
    if not cache.exists():
        for q in ("maxresdefault.jpg", "hqdefault.jpg", "default.jpg"):
            try:
                req = urllib.request.Request(
                    f"https://i.ytimg.com/vi/{video_id}/{q}",
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    cache.write_bytes(resp.read())
                break
            except Exception:
                continue
    return Image.open(cache).convert("RGB")


def rounded_mask(size: tuple, radius: int) -> Image.Image:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([(0, 0), size], radius=radius, fill=255)
    return mask


def wrap_text(draw, text: str, font, max_width: int) -> list:
    """한글·영문 혼합 가변폭 wrapping (단어/글자 하이브리드)"""
    words = []
    buf = ""
    for c in text:
        if c == " ":
            if buf:
                words.append(buf)
                buf = ""
            words.append(" ")
        elif "가" <= c <= "힯":  # 한글 음절
            if buf:
                words.append(buf)
                buf = ""
            words.append(c)
        else:
            buf += c
    if buf:
        words.append(buf)

    lines, current = [], ""
    for w in words:
        test = current + w
        bbox = draw.textbbox((0, 0), test, font=font)
        if (bbox[2] - bbox[0]) > max_width and current.strip():
            lines.append(current.rstrip())
            current = w.lstrip()
        else:
            current = test
    if current.strip():
        lines.append(current.rstrip())
    return lines


def render_og(*, video_id: str, h1: str, tagline_en: str = "",
              tagline_ko: str = "", meta_right: str = "",
              out_path: str) -> str:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # 좌측 커버 (라운드 마스크)
    try:
        thumb = fetch_thumb(video_id)
        short = min(thumb.size)
        l = (thumb.width - short) // 2
        t = (thumb.height - short) // 2
        cover = thumb.crop((l, t, l + short, t + short))
        cover = cover.resize((COVER_SIZE, COVER_SIZE), Image.LANCZOS)
        mask = rounded_mask((COVER_SIZE, COVER_SIZE), 24)
        img.paste(cover, (COVER_X, COVER_Y), mask)
    except Exception as e:
        d.rounded_rectangle(
            [(COVER_X, COVER_Y), (COVER_X + COVER_SIZE, COVER_Y + COVER_SIZE)],
            radius=24, fill=(30, 30, 40),
        )

    # 우측 텍스트 컬럼
    text_x = COVER_X + COVER_SIZE + 60
    text_w = W - text_x - 80

    # Brand
    f_brand = load_font("regular", 24)
    d.text((text_x, 80), "Mr. Slow", fill=ACCENT, font=f_brand)

    # H1
    f_h1 = load_font("bold", 56)
    lines = wrap_text(d, h1, f_h1, text_w)
    y = 130
    for line in lines[:3]:
        d.text((text_x, y), line, fill=FG, font=f_h1)
        y += 72

    # Tagline EN
    f_tag = load_font("regular", 26)
    y += 16
    if tagline_en:
        for line in wrap_text(d, tagline_en, f_tag, text_w)[:2]:
            d.text((text_x, y), line, fill=MUTED, font=f_tag)
            y += 38

    # Tagline KO
    if tagline_ko:
        y += 8
        for line in wrap_text(d, tagline_ko, f_tag, text_w)[:2]:
            d.text((text_x, y), line, fill=DIM, font=f_tag)
            y += 38

    # CTA bar
    f_cta = load_font("bold", 26)
    d.text((text_x, H - 90), "▶ YouTube Music", fill=ACCENT, font=f_cta)

    # Meta right (bottom-right corner)
    if meta_right:
        f_meta = load_font("regular", 22)
        bbox = d.textbbox((0, 0), meta_right, font=f_meta)
        meta_w = bbox[2] - bbox[0]
        d.text((W - meta_w - 60, H - 80), meta_right, fill=DIM, font=f_meta)

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, format="PNG", optimize=True)
    return str(out)


if __name__ == "__main__":
    # 빠른 셀프 테스트
    render_og(
        video_id="DQ1V74sfmGE",
        h1="Mr. Slow",
        tagline_en="Korean pop vibe in Seoul right now",
        tagline_ko="지금 서울의 K-인디·감성·슬로우 92곡",
        meta_right="92 tracks · Seoul Vibes",
        out_path="og/test.png",
    )
    print("Generated og/test.png")
