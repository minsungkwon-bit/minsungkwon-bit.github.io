"""
Mr. Slow SEO 랜딩 사이트 빌더 (multi-page)
============================================

생성 페이지:
  /                           — 메인 (전체 92트랙)
  /moods/<mood>/              — 무드별 변형 (5개: breakup, night-drive, cafe-mood, seoul-night, k-indie-2026)
  /tracks/<videoId>/          — 트랙 개별 (92개)
  /posts/<slug>/              — 주간 블로그 포스트

빌드:
  python3 build.py --domain https://YOUR.pages.dev

신규 주간 포스트 추가:
  python3 build.py --new-post   # 자동으로 이번 주 슬러그 생성

배포: README는 없음 - 아래 주석 참고
  1. python3 build.py --domain https://YOUR.pages.dev
  2. git init && git add . && git commit -m "init"
  3. Cloudflare Pages 또는 GitHub Pages에 push
  4. Google Search Console에 sitemap.xml 제출
"""

import argparse
import html
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

try:
    import og_image
    OG_AVAILABLE = True
except ImportError:
    OG_AVAILABLE = False
    print("⚠ Pillow 미설치 - OG 이미지 생성 스킵 (pip install Pillow)")

ROOT = Path(__file__).parent
FORCE_OG = False  # main()에서 --force-og 시 True
PLAYLIST_ID = "PLRaEryL4ESyhaPbFvdNFaKfI0PO-1JBiJ"
YT_MUSIC_URL = f"https://music.youtube.com/playlist?list={PLAYLIST_ID}"
YT_NORMAL_URL = f"https://www.youtube.com/playlist?list={PLAYLIST_ID}"
EMBED_URL = f"https://www.youtube.com/embed/videoseries?list={PLAYLIST_ID}"

PLAYLIST_NAME = "Mr. Slow"
TAGLINE_EN = "Korean pop vibe in Seoul right now"
TAGLINE_KO = "지금 서울의 K-인디·감성·슬로우 92곡"
OWNER = "Mr. Slow"
OWNER_HANDLE = "@alexiskwon"
OWNER_URL = "https://www.youtube.com/@alexiskwon"

ROOT_KEYWORDS = [
    "한국 인디 플레이리스트", "감성 K-pop 플레이리스트", "새벽 감성 노래 모음",
    "한국 슬로우 발라드", "전여친 플레이리스트", "이별 노래 추천",
    "Seoul indie playlist", "Korean R&B chill playlist", "K-indie slow songs 2026",
    "Korean breakup playlist", "YouTube Music K-pop playlist",
]


# ============================================================
# 공통 컴포넌트
# ============================================================

def safe(s: str) -> str:
    return html.escape(s or "", quote=True)


def base_css() -> str:
    return """*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#0a0a0f; --bg-2:#13131a; --fg:#f0f0f5; --muted:#888;
  --accent:#ff0033; --accent-2:#ff3360; --border:#222;
}
html{scroll-behavior:smooth}
body{
  font-family:-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Pretendard",
              "Noto Sans KR",sans-serif;
  background:var(--bg);color:var(--fg);line-height:1.6;min-height:100vh
}
a{color:inherit}
.wrap{max-width:880px;margin:0 auto;padding:24px 16px 80px}
header{text-align:center;padding:48px 0 32px}
nav.crumbs{font-size:13px;color:var(--muted);margin-bottom:20px;text-align:left}
nav.crumbs a{color:var(--muted);text-decoration:none;border-bottom:1px solid transparent}
nav.crumbs a:hover{border-color:var(--muted)}
.cover{
  width:280px;height:280px;margin:0 auto 24px;border-radius:16px;
  background-size:cover;background-position:center;
  box-shadow:0 12px 48px rgba(255,0,51,.15)
}
h1{font-size:clamp(28px,5vw,40px);font-weight:800;letter-spacing:-.02em;margin-bottom:8px}
.tagline{color:var(--muted);font-size:18px;margin-bottom:4px}
.tagline-ko{color:#bbb;font-size:15px;margin-bottom:24px}
.stats{display:flex;gap:20px;justify-content:center;color:var(--muted);font-size:14px;margin-bottom:32px;flex-wrap:wrap}
.cta{
  display:inline-flex;align-items:center;gap:10px;
  background:var(--accent);color:#fff;padding:16px 32px;
  border-radius:999px;text-decoration:none;font-weight:700;font-size:17px;
  transition:transform .15s,background .15s;
  box-shadow:0 4px 20px rgba(255,0,51,.35)
}
.cta:hover{background:var(--accent-2);transform:translateY(-1px)}
.cta-secondary{
  display:inline-block;color:var(--muted);text-decoration:none;
  font-size:14px;margin-top:12px;border-bottom:1px solid var(--border)
}
.embed-wrap{
  position:relative;width:100%;aspect-ratio:16/9;margin:40px 0;
  border-radius:12px;overflow:hidden;background:var(--bg-2)
}
.embed-wrap iframe{position:absolute;inset:0;width:100%;height:100%;border:0}
section{margin-top:40px}
h2{font-size:22px;margin-bottom:16px;font-weight:700}
.intro{color:#ccc;font-size:15px;line-height:1.8}
.intro p{margin-bottom:14px}
.intro strong{color:#fff}
.tracklist{list-style:none;display:grid;gap:4px}
.track a{display:flex;align-items:center;gap:12px;padding:8px;border-radius:8px;text-decoration:none;color:inherit;transition:background .12s}
.track a:hover{background:var(--bg-2)}
.track img{border-radius:4px;flex-shrink:0;object-fit:cover}
.track-meta{display:flex;flex-direction:column;min-width:0;flex:1}
.track-num{font-size:11px;color:var(--muted);font-variant-numeric:tabular-nums}
.track-title{font-size:15px;color:var(--fg);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.track-artist{font-size:13px;color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.mood-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-top:24px}
.mood-card{
  display:block;padding:20px;border-radius:12px;
  background:var(--bg-2);text-decoration:none;color:inherit;
  border:1px solid var(--border);transition:border-color .15s,transform .15s
}
.mood-card:hover{border-color:var(--accent);transform:translateY(-2px)}
.mood-card .mh{font-weight:700;margin-bottom:4px}
.mood-card .ms{font-size:13px;color:var(--muted)}
footer{margin-top:60px;padding-top:32px;border-top:1px solid var(--border);text-align:center;color:var(--muted);font-size:13px}
footer a{color:var(--muted)}
@media(max-width:600px){.cover{width:220px;height:220px}}
"""


def render_head(*, title: str, description: str, keywords: list, canonical: str,
                og_image: str, og_type: str = "music.playlist",
                schema_json: str = "") -> str:
    schema_block = f'<script type="application/ld+json">{schema_json}</script>' if schema_json else ""
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{safe(title)}</title>
<meta name="description" content="{safe(description)}">
<meta name="keywords" content="{safe(', '.join(keywords))}">
<meta name="author" content="{OWNER}">
<link rel="canonical" href="{canonical}">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{safe(title)}">
<meta property="og:description" content="{safe(description)}">
<meta property="og:image" content="{og_image}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:type" content="image/png">
<meta property="og:url" content="{canonical}">
<meta property="og:locale" content="ko_KR">
<meta property="og:locale:alternate" content="en_US">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{safe(title)}">
<meta name="twitter:description" content="{safe(description)}">
<meta name="twitter:image" content="{og_image}">
<link rel="preconnect" href="https://www.youtube.com">
<link rel="preconnect" href="https://i.ytimg.com">
<link rel="dns-prefetch" href="https://music.youtube.com">
{schema_block}
<style>{base_css()}</style>
</head>
<body>
<div class="wrap">"""


def render_footer() -> str:
    return f"""
<footer>
  <p>Curated by <a href="{OWNER_URL}" rel="noopener" target="_blank">{OWNER} ({OWNER_HANDLE})</a></p>
  <p style="margin-top:8px">
    <a href="{YT_MUSIC_URL}" rel="noopener" target="_blank">YouTube Music</a> ·
    <a href="{YT_NORMAL_URL}" rel="noopener" target="_blank">YouTube</a>
  </p>
</footer>
</div></body></html>"""


def render_tracklist(tracks: list) -> str:
    items = []
    for i, t in enumerate(tracks, 1):
        thumb = f"https://i.ytimg.com/vi/{t['videoId']}/default.jpg"
        # 내부 트랙 페이지로 링크 (외부 클릭아웃 대신 SEO 자산 활용)
        href = f"/tracks/{t['videoId']}/"
        items.append(f"""
      <li class="track">
        <a href="{href}">
          <img src="{thumb}" alt="{safe(t['title'])} - {safe(t['artist'])}" loading="lazy" width="64" height="48">
          <div class="track-meta">
            <span class="track-num">{i:02d}</span>
            <span class="track-title">{safe(t['title'])}</span>
            <span class="track-artist">{safe(t['artist'])}</span>
          </div>
        </a>
      </li>""")
    return f'<ol class="tracklist">{"".join(items)}</ol>'


def render_mood_grid(moods: dict) -> str:
    cards = []
    for slug, m in moods.items():
        cards.append(f"""
    <a class="mood-card" href="/moods/{slug}/">
      <div class="mh">{safe(m['h1'])}</div>
      <div class="ms">{safe(m['tagline_ko'])}</div>
    </a>""")
    return f'<div class="mood-grid">{"".join(cards)}</div>'


def gen_og(*, slug: str, video_id: str, h1: str, tagline_en: str,
           tagline_ko: str, meta_right: str, out_root: Path, site_url: str) -> str:
    """OG 이미지 생성 (캐시 활용) - 절대 URL 반환"""
    rel = f"og/{slug}.png"
    abs_out = out_root / rel
    fallback_url = f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg"
    if not OG_AVAILABLE:
        return fallback_url
    if abs_out.exists() and not FORCE_OG:
        return f"{site_url.rstrip('/')}/{rel}"
    try:
        og_image.render_og(
            video_id=video_id, h1=h1,
            tagline_en=tagline_en, tagline_ko=tagline_ko,
            meta_right=meta_right, out_path=str(abs_out),
        )
        return f"{site_url.rstrip('/')}/{rel}"
    except Exception as e:
        print(f"  ⚠ OG 실패 ({slug}): {e}")
        return fallback_url


def make_schema_playlist(tracks: list, name: str, description: str, canonical: str) -> str:
    schema = {
        "@context": "https://schema.org",
        "@type": "MusicPlaylist",
        "name": name,
        "description": description,
        "url": canonical,
        "numTracks": len(tracks),
        "inLanguage": ["ko", "en"],
        "creator": {"@type": "Person", "name": OWNER, "url": OWNER_URL},
        "track": [
            {
                "@type": "MusicRecording",
                "name": t["title"],
                "byArtist": {"@type": "MusicGroup", "name": t["artist"]},
                "url": f"https://music.youtube.com/watch?v={t['videoId']}&list={PLAYLIST_ID}",
            }
            for t in tracks
        ],
    }
    return json.dumps(schema, ensure_ascii=False)


# ============================================================
# 페이지 렌더러
# ============================================================

def render_index(tracks: list, moods: dict, site_url: str, out_root: Path) -> str:
    canonical = site_url.rstrip("/") + "/"
    cover = f"https://i.ytimg.com/vi/{tracks[0]['videoId']}/maxresdefault.jpg"
    title = f"{PLAYLIST_NAME} — 한국 인디·감성 슬로우 플레이리스트 {len(tracks)}곡 | K-Indie 2026"
    desc = f"{TAGLINE_KO}. CHAD BURGER, 온시온, 시즈더데이, 김연, Crush, NELL 등 {len(tracks)}곡. YouTube Music에서 무료 재생."

    og_url = gen_og(
        slug="home", video_id=tracks[0]["videoId"],
        h1=PLAYLIST_NAME, tagline_en=TAGLINE_EN, tagline_ko=TAGLINE_KO,
        meta_right=f"{len(tracks)} tracks · Seoul Vibes",
        out_root=out_root, site_url=site_url,
    )

    head = render_head(
        title=title, description=desc, keywords=ROOT_KEYWORDS,
        canonical=canonical, og_image=og_url,
        schema_json=make_schema_playlist(tracks, PLAYLIST_NAME, desc, canonical),
    )

    body = f"""
<header>
  <div class="cover" style="background-image:url('{cover}')" role="img" aria-label="{PLAYLIST_NAME} cover"></div>
  <h1>{PLAYLIST_NAME}</h1>
  <p class="tagline">{TAGLINE_EN}</p>
  <p class="tagline-ko">{TAGLINE_KO}</p>
  <div class="stats">
    <span>📀 {len(tracks)} tracks</span>
    <span>🇰🇷 Korean Indie · R&amp;B · Slow Pop</span>
    <span>🌃 Seoul Vibes</span>
  </div>
  <p><a class="cta" href="{YT_MUSIC_URL}" rel="noopener" target="_blank">▶ YouTube Music에서 듣기</a></p>
  <p><a class="cta-secondary" href="{YT_NORMAL_URL}" rel="noopener" target="_blank">YouTube에서 듣기 (영상)</a></p>
</header>

<div class="embed-wrap">
  <iframe src="{EMBED_URL}" title="{PLAYLIST_NAME} player" loading="lazy"
    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
    referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>
</div>

<section class="intro">
  <h2>이 플레이리스트는 어떤 음악인가요?</h2>
  <p>
    <strong>{PLAYLIST_NAME}</strong>은 2026년 현재 서울의 인디·감성·슬로우 한국 음악
    <strong>{len(tracks)}곡</strong>을 모은 큐레이션입니다.
    <strong>CHAD BURGER</strong>, <strong>온시온(ONSEEON)</strong>, <strong>시즈더데이(seizetheday)</strong>,
    <strong>김연(Yyeon)</strong>, <strong>Hollow Young</strong>, <strong>Ourealgoat</strong>,
    <strong>melodywalk(전여친 playlist)</strong>, <strong>The Black Skirts</strong>, <strong>Crush</strong>,
    <strong>NELL</strong>, <strong>pH-1</strong>, <strong>ASH ISLAND</strong>, <strong>Stray Kids</strong> 등.
  </p>
  <p>새벽 운전, 늦은 밤 카페, 비 오는 창가, 이별 직후 — 그런 순간에 어울리는 <strong>슬로우 K-pop 플레이리스트</strong>입니다.</p>
</section>

<section>
  <h2>무드별로 듣기</h2>
  {render_mood_grid(moods)}
</section>

<section>
  <h2>전체 트랙리스트 ({len(tracks)}곡)</h2>
  {render_tracklist(tracks)}
</section>
"""
    return head + body + render_footer()


def render_mood(slug: str, mood: dict, tracks: list, moods: dict, site_url: str, out_root: Path) -> str:
    canonical = f"{site_url.rstrip('/')}/moods/{slug}/"
    cover = f"https://i.ytimg.com/vi/{tracks[0]['videoId']}/maxresdefault.jpg"
    og_url = gen_og(
        slug=f"mood-{slug}", video_id=tracks[0]["videoId"],
        h1=mood["h1"], tagline_en=mood["tagline_en"], tagline_ko=mood["tagline_ko"],
        meta_right=f"{len(tracks)} tracks · Mr. Slow",
        out_root=out_root, site_url=site_url,
    )

    # 하이라이트 트랙: 키워드 매칭되는 것 위로 (없으면 그냥 전체)
    highlight_keys = mood.get("highlight_keywords", [])
    if highlight_keys:
        matched, other = [], []
        for t in tracks:
            blob = (t["title"] + " " + t["artist"]).lower()
            if any(k.lower() in blob for k in highlight_keys):
                matched.append(t)
            else:
                other.append(t)
        display_tracks = matched + other
        highlight_section = (
            f'<p><strong>이 무드에 특히 잘 맞는 트랙 {len(matched)}곡</strong>이 위에 먼저 배치되어 있어요.</p>'
            if matched else ""
        )
    else:
        display_tracks = tracks
        highlight_section = ""

    head = render_head(
        title=mood["seo_title"],
        description=mood["seo_description"],
        keywords=mood["keywords"],
        canonical=canonical,
        og_image=og_url,
        schema_json=make_schema_playlist(
            tracks, f"{PLAYLIST_NAME} — {mood['h1']}", mood["seo_description"], canonical,
        ),
    )

    body = f"""
<nav class="crumbs">
  <a href="/">{PLAYLIST_NAME}</a> &nbsp;›&nbsp; <span>{safe(mood['h1'])}</span>
</nav>

<header>
  <div class="cover" style="background-image:url('{cover}')" role="img"></div>
  <h1>{safe(mood['h1'])}</h1>
  <p class="tagline">{safe(mood['tagline_en'])}</p>
  <p class="tagline-ko">{safe(mood['tagline_ko'])}</p>
  <div class="stats">
    <span>📀 {len(tracks)} tracks · Mr. Slow</span>
  </div>
  <p><a class="cta" href="{YT_MUSIC_URL}" rel="noopener" target="_blank">▶ YouTube Music에서 듣기</a></p>
</header>

<div class="embed-wrap">
  <iframe src="{EMBED_URL}" title="{safe(mood['h1'])} playlist" loading="lazy"
    allow="autoplay; encrypted-media; picture-in-picture" allowfullscreen></iframe>
</div>

<section class="intro">
  <h2>{safe(mood['h1'])} — 어떤 순간을 위한 음악인가요?</h2>
  <p>{safe(mood['intro_ko'])}</p>
  <p style="color:var(--muted);font-size:14px"><em>{safe(mood['intro_en'])}</em></p>
  {highlight_section}
</section>

<section>
  <h2>다른 무드로 듣기</h2>
  {render_mood_grid({k: v for k, v in moods.items() if k != slug})}
</section>

<section>
  <h2>트랙리스트</h2>
  {render_tracklist(display_tracks)}
</section>
"""
    return head + body + render_footer()


def render_track(track: dict, idx: int, tracks: list, moods: dict, site_url: str,
                 out_root: Path, lyrics_db: dict = None) -> str:
    vid = track["videoId"]
    canonical = f"{site_url.rstrip('/')}/tracks/{vid}/"
    cover = f"https://i.ytimg.com/vi/{vid}/maxresdefault.jpg"
    thumb = f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
    title_seo = f"{track['title']} — {track['artist']} | from {PLAYLIST_NAME} (Korean Indie Playlist)"

    # 가사 데이터 (있으면 description + 본문에 활용)
    lyrics = (lyrics_db or {}).get(vid, {}) if lyrics_db else {}
    has_lyrics = lyrics.get("hook") or lyrics.get("lines")
    if has_lyrics and lyrics.get("hook"):
        desc = f'"{lyrics["hook"]}" — {track["artist"]}「{track["title"]}」. {PLAYLIST_NAME} 플레이리스트 수록.'
    else:
        desc = f'"{track["title"]}" by {track["artist"]}. 한국 인디·감성·슬로우 플레이리스트 「{PLAYLIST_NAME}」에서 듣기.'

    og_url = gen_og(
        slug=f"track-{vid}", video_id=vid,
        h1=track["title"], tagline_en=track["artist"],
        tagline_ko=f"from {PLAYLIST_NAME} · Track {idx + 1} of {len(tracks)}",
        meta_right="Korean Indie · Slow Pop",
        out_root=out_root, site_url=site_url,
    )

    schema = {
        "@context": "https://schema.org",
        "@type": "MusicRecording",
        "name": track["title"],
        "byArtist": {"@type": "MusicGroup", "name": track["artist"]},
        "url": canonical,
        "inPlaylist": {
            "@type": "MusicPlaylist",
            "name": PLAYLIST_NAME,
            "url": site_url.rstrip("/") + "/",
        },
        "thumbnailUrl": cover,
    }

    kw = [track["title"], track["artist"], "한국 인디", "K-indie", PLAYLIST_NAME,
          f"{track['artist']} 노래", f"{track['title']} 가사", "Korean indie song"]
    if has_lyrics and lyrics.get("hook"):
        kw.insert(0, f'{lyrics["hook"][:30]}')  # 가사 단편 키워드
        # Schema에 lyrics 추가
        schema["lyrics"] = {
            "@type": "CreativeWork",
            "text": " / ".join(lyrics.get("lines", [])) or lyrics.get("hook", ""),
        }

    head = render_head(
        title=title_seo, description=desc,
        keywords=kw,
        canonical=canonical, og_image=og_url, og_type="music.song",
        schema_json=json.dumps(schema, ensure_ascii=False),
    )

    # 이전/다음 트랙 (재생 흐름 유지)
    prev_t = tracks[idx - 1] if idx > 0 else None
    next_t = tracks[idx + 1] if idx < len(tracks) - 1 else None

    nav_links = []
    if prev_t:
        nav_links.append(f'<a href="/tracks/{prev_t["videoId"]}/" style="color:var(--muted);text-decoration:none">‹ {safe(prev_t["title"])}</a>')
    if next_t:
        nav_links.append(f'<a href="/tracks/{next_t["videoId"]}/" style="color:var(--muted);text-decoration:none;margin-left:auto;text-align:right">{safe(next_t["title"])} ›</a>')
    nav_block = f'<div style="display:flex;justify-content:space-between;gap:20px;margin-top:32px;font-size:14px">{" ".join(nav_links)}</div>' if nav_links else ""

    embed_single = f"https://www.youtube.com/embed/{vid}?list={PLAYLIST_ID}"
    watch_url = f"https://music.youtube.com/watch?v={vid}&list={PLAYLIST_ID}"

    # 추천 트랙 (같은 아티스트 우선, 없으면 앞뒤)
    same_artist = [t for t in tracks if t["artist"] == track["artist"] and t["videoId"] != vid][:5]
    if len(same_artist) < 3:
        nearby = tracks[max(0, idx - 3):idx] + tracks[idx + 1:idx + 4]
        same_artist = (same_artist + [t for t in nearby if t["videoId"] != vid])[:5]

    # 가사 섹션 (있을 때만)
    lyrics_html = ""
    if has_lyrics:
        hook = lyrics.get("hook", "")
        lines = lyrics.get("lines", [])
        line_html = "".join(f"<p>{safe(l)}</p>" for l in lines) if lines else ""
        hook_html = f'<blockquote style="font-size:20px;color:#fff;border-left:3px solid var(--accent);padding:8px 16px;margin:16px 0">{safe(hook)}</blockquote>' if hook else ""
        lyrics_html = f"""
<section>
  <h2>가사 (Lyrics)</h2>
  {hook_html}
  <div class="intro" style="font-size:16px;line-height:2;color:#ddd">
    {line_html}
  </div>
  <p style="color:var(--muted);font-size:12px;margin-top:12px">
    * fair use 범위 내 단편. 전체 가사는 음원 서비스 또는 공식 채널에서 확인하세요.
  </p>
</section>"""

    related_html = ""
    if same_artist:
        related_html = f"""
<section>
  <h2>이 플레이리스트의 다른 곡</h2>
  {render_tracklist(same_artist)}
</section>"""

    body = f"""
<nav class="crumbs">
  <a href="/">{PLAYLIST_NAME}</a> &nbsp;›&nbsp;
  <a href="/#tracks">Tracks</a> &nbsp;›&nbsp;
  <span>{safe(track['title'])}</span>
</nav>

<header>
  <div class="cover" style="background-image:url('{cover}')" role="img" aria-label="{safe(track['title'])}"></div>
  <h1>{safe(track['title'])}</h1>
  <p class="tagline">{safe(track['artist'])}</p>
  <p class="tagline-ko">from <a href="/" style="color:#bbb;border-bottom:1px solid #444;text-decoration:none">{PLAYLIST_NAME}</a> playlist · Track {idx + 1} of {len(tracks)}</p>
  <p style="margin-top:24px">
    <a class="cta" href="{watch_url}" rel="noopener" target="_blank">▶ YouTube Music에서 듣기</a>
  </p>
</header>

<div class="embed-wrap">
  <iframe src="{embed_single}" title="{safe(track['title'])}" loading="lazy"
    allow="autoplay; encrypted-media; picture-in-picture" allowfullscreen></iframe>
</div>

<section class="intro">
  <p>
    <strong>{safe(track['title'])}</strong>은 <strong>{safe(track['artist'])}</strong>의 곡으로,
    한국 인디·감성·슬로우 큐레이션 플레이리스트 「{PLAYLIST_NAME}」에 수록된 92곡 중 {idx + 1}번째 트랙입니다.
  </p>
  <p>
    <a href="{YT_MUSIC_URL}" rel="noopener" target="_blank" style="color:var(--accent);border-bottom:1px solid var(--accent);text-decoration:none">전체 92곡 플레이리스트 듣기 →</a>
  </p>
</section>

{lyrics_html}

{related_html}

{nav_block}
"""
    return head + body + render_footer()


def render_weekly_post(post_slug: str, post_date: datetime, featured_tracks: list,
                      all_tracks: list, moods: dict, site_url: str, out_root: Path) -> str:
    canonical = f"{site_url.rstrip('/')}/posts/{post_slug}/"
    cover = f"https://i.ytimg.com/vi/{featured_tracks[0]['videoId']}/maxresdefault.jpg"
    week_num = post_date.isocalendar()[1]
    year = post_date.year

    title = f"{year}년 {week_num}주차 한국 인디 추천 5곡 — Mr. Slow Weekly"
    desc = f"이번 주 Mr. Slow 플레이리스트에서 꼭 들어볼 만한 한국 인디·감성 트랙 5곡. " + \
           ", ".join([f'{t["artist"]} - {t["title"]}' for t in featured_tracks[:3]])

    og_url = gen_og(
        slug=f"post-{post_slug}", video_id=featured_tracks[0]["videoId"],
        h1=f"Week {week_num} · 5곡 추천",
        tagline_en=f"Weekly pick from Mr. Slow",
        tagline_ko=f"{post_date.strftime('%Y.%m.%d')} · 한국 인디 신선 트랙",
        meta_right=f"5 tracks · Mr. Slow Weekly",
        out_root=out_root, site_url=site_url,
    )

    head = render_head(
        title=title, description=desc,
        keywords=["한국 인디 추천", "K-indie 주간 추천", "이번 주 신곡", "Korean indie weekly",
                  PLAYLIST_NAME, "Mr. Slow weekly"],
        canonical=canonical, og_image=og_url, og_type="article",
    )

    feat_html = []
    for i, t in enumerate(featured_tracks, 1):
        embed = f"https://www.youtube.com/embed/{t['videoId']}"
        feat_html.append(f"""
<section class="intro" style="margin-top:48px">
  <h2>{i}. {safe(t['title'])} — {safe(t['artist'])}</h2>
  <div class="embed-wrap" style="margin:16px 0 8px">
    <iframe src="{embed}" title="{safe(t['title'])}" loading="lazy"
      allow="autoplay; encrypted-media; picture-in-picture" allowfullscreen></iframe>
  </div>
  <p>
    <a href="/tracks/{t['videoId']}/" style="color:var(--accent);border-bottom:1px solid var(--accent);text-decoration:none">트랙 페이지 →</a>
  </p>
</section>""")

    body = f"""
<nav class="crumbs">
  <a href="/">{PLAYLIST_NAME}</a> &nbsp;›&nbsp;
  <a href="/posts/">Weekly</a> &nbsp;›&nbsp;
  <span>{year} W{week_num:02d}</span>
</nav>

<header style="padding:32px 0 16px">
  <p class="tagline-ko" style="margin-bottom:8px">{post_date.strftime('%Y년 %m월 %d일')} · Week {week_num}</p>
  <h1 style="font-size:32px">이번 주 한국 인디 추천 5곡</h1>
  <p class="tagline">{safe(PLAYLIST_NAME)} Weekly Pick</p>
</header>

<section class="intro">
  <p>매주 「{PLAYLIST_NAME}」 플레이리스트에서 골라 듣는 한국 인디·감성·슬로우 5곡. 이번 주는 이런 트랙들이 귀에 들어왔어요.</p>
</section>

{"".join(feat_html)}

<section style="margin-top:60px">
  <h2>전체 플레이리스트 듣기</h2>
  <p style="margin-bottom:24px"><a class="cta" href="{YT_MUSIC_URL}" rel="noopener" target="_blank">▶ YouTube Music에서 92곡 전체 듣기</a></p>
  {render_mood_grid(moods)}
</section>
"""
    return head + body + render_footer()


def render_posts_index(posts: list, moods: dict, site_url: str, out_root: Path) -> str:
    canonical = f"{site_url.rstrip('/')}/posts/"
    og_url = gen_og(
        slug="posts-index", video_id="DQ1V74sfmGE",
        h1="Weekly", tagline_en="Mr. Slow Weekly Picks",
        tagline_ko="매주 5곡씩 골라 듣는 한국 인디",
        meta_right=f"{len(posts)} posts archived",
        out_root=out_root, site_url=site_url,
    )
    head = render_head(
        title=f"Weekly — {PLAYLIST_NAME} 주간 추천",
        description=f"{PLAYLIST_NAME} 플레이리스트에서 매주 골라 듣는 한국 인디·감성 추천 트랙 아카이브.",
        keywords=["한국 인디 주간 추천", "K-indie weekly", PLAYLIST_NAME],
        canonical=canonical, og_image=og_url, og_type="website",
    )
    items = []
    for p in sorted(posts, key=lambda x: x["date"], reverse=True):
        items.append(f"""
<li style="padding:16px 0;border-bottom:1px solid var(--border)">
  <a href="/posts/{p['slug']}/" style="text-decoration:none;color:inherit;display:block">
    <div style="color:var(--muted);font-size:13px">{p['date']}</div>
    <div style="font-size:18px;margin-top:4px">{safe(p['title'])}</div>
  </a>
</li>""")
    body = f"""
<nav class="crumbs"><a href="/">{PLAYLIST_NAME}</a> &nbsp;›&nbsp; <span>Weekly</span></nav>
<header><h1>Weekly</h1><p class="tagline-ko">매주 5곡씩 골라 듣기</p></header>
<section><ul style="list-style:none">{"".join(items) if items else '<li style="color:var(--muted)">아직 포스트가 없습니다.</li>'}</ul></section>
"""
    return head + body + render_footer()


def render_sitemap(all_urls: list, site_url: str) -> str:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    base = site_url.rstrip("/")
    entries = []
    for path, priority, changefreq in all_urls:
        entries.append(f"""  <url>
    <loc>{base}{path}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>{changefreq}</changefreq>
    <priority>{priority}</priority>
  </url>""")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(entries)}
</urlset>
"""


def render_robots(site_url: str) -> str:
    return f"User-agent: *\nAllow: /\n\nSitemap: {site_url.rstrip('/')}/sitemap.xml\n"


# ============================================================
# 빌드 오케스트레이션
# ============================================================

def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load_posts_manifest(out: Path) -> list:
    f = out / "posts.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else []


def save_posts_manifest(out: Path, posts: list):
    (out / "posts.json").write_text(json.dumps(posts, ensure_ascii=False, indent=2), encoding="utf-8")


def add_new_weekly_post(out: Path, tracks: list) -> str:
    """오늘 날짜 기준 새 주간 포스트 만들고 manifest에 추가"""
    today = datetime.utcnow()
    year, week, _ = today.isocalendar()
    slug = f"{year}-W{week:02d}-fresh-finds"

    posts = load_posts_manifest(out)
    if any(p["slug"] == slug for p in posts):
        print(f"      이번 주 포스트 ({slug}) 이미 존재 - 스킵")
        return slug

    # 결정론적 5곡 선택 (week 번호 시드)
    import random
    rng = random.Random(year * 100 + week)
    featured_ids = rng.sample(range(len(tracks)), 5)
    featured = [tracks[i] for i in featured_ids]

    posts.append({
        "slug": slug,
        "date": today.strftime("%Y-%m-%d"),
        "title": f"{year}년 {week}주차 한국 인디 추천 5곡",
        "featured_video_ids": [t["videoId"] for t in featured],
    })
    save_posts_manifest(out, posts)
    print(f"      신규 포스트 추가: {slug}")
    return slug


def main():
    global FORCE_OG
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", default="https://mr-slow.pages.dev")
    ap.add_argument("--out", default=str(ROOT))
    ap.add_argument("--new-post", action="store_true",
                    help="이번 주 신규 포스트 생성 후 빌드")
    ap.add_argument("--force-og", action="store_true",
                    help="OG 이미지 재생성 (디자인 변경 시)")
    args = ap.parse_args()
    FORCE_OG = args.force_og

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    tracks = json.loads((ROOT / "tracks.json").read_text(encoding="utf-8"))
    moods = json.loads((ROOT / "moods.json").read_text(encoding="utf-8"))

    # lyrics.json (선택) - 없거나 비어있어도 동작
    lyrics_db = {}
    lyrics_file = ROOT / "lyrics.json"
    if lyrics_file.exists():
        raw = json.loads(lyrics_file.read_text(encoding="utf-8"))
        lyrics_db = {k: v for k, v in raw.items()
                     if not k.startswith("_") and (v.get("hook") or v.get("lines"))}

    print(f"[1] 도메인: {args.domain}")
    print(f"[2] 트랙 {len(tracks)}개 / 무드 {len(moods)}개 / 가사 {len(lyrics_db)}개 로드")

    # 신규 포스트 추가 옵션
    if args.new_post:
        add_new_weekly_post(out, tracks)
    else:
        # 첫 실행이면 시작용 포스트 1개 자동 생성
        if not load_posts_manifest(out):
            add_new_weekly_post(out, tracks)

    posts = load_posts_manifest(out)
    print(f"[3] 포스트 {len(posts)}개")

    all_urls = [("/", "1.0", "weekly")]

    # 1) 메인
    write(out / "index.html", render_index(tracks, moods, args.domain, out))

    # 2) 무드 페이지 (5개)
    for slug, mood in moods.items():
        write(out / "moods" / slug / "index.html",
              render_mood(slug, mood, tracks, moods, args.domain, out))
        all_urls.append((f"/moods/{slug}/", "0.9", "monthly"))

    # 3) 트랙 페이지 (중복 videoId 제거)
    seen_ids = set()
    for i, t in enumerate(tracks):
        if t["videoId"] in seen_ids:
            continue
        seen_ids.add(t["videoId"])
        write(out / "tracks" / t["videoId"] / "index.html",
              render_track(t, i, tracks, moods, args.domain, out, lyrics_db))
        all_urls.append((f"/tracks/{t['videoId']}/", "0.7", "monthly"))

    # 4) 주간 포스트
    for p in posts:
        post_date = datetime.fromisoformat(p["date"])
        featured = [t for t in tracks if t["videoId"] in p["featured_video_ids"]]
        write(out / "posts" / p["slug"] / "index.html",
              render_weekly_post(p["slug"], post_date, featured, tracks, moods, args.domain, out))
        all_urls.append((f"/posts/{p['slug']}/", "0.8", "yearly"))

    # 포스트 인덱스
    write(out / "posts" / "index.html",
          render_posts_index(posts, moods, args.domain, out))
    all_urls.append(("/posts/", "0.6", "weekly"))

    # 5) sitemap / robots / .nojekyll
    write(out / "sitemap.xml", render_sitemap(all_urls, args.domain))
    write(out / "robots.txt", render_robots(args.domain))
    write(out / ".nojekyll", "")

    # 통계
    total_files = (
        1                      # index
        + len(moods)           # moods
        + len(tracks)          # tracks
        + len(posts) + 1       # posts + index
        + 3                    # sitemap, robots, nojekyll
    )
    print(f"[4] 생성:")
    print(f"      1 × root index")
    print(f"      {len(moods)} × mood pages")
    print(f"      {len(seen_ids)} × track pages")
    print(f"      {len(posts) + 1} × posts (+index)")
    print(f"      sitemap.xml ({len(all_urls)} URLs)")
    print(f"      = {total_files} 파일")
    print(f"[5] 출력: {out.resolve()}")


if __name__ == "__main__":
    main()
