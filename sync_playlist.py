"""
YouTube(공개 플레이리스트) → tracks.json 동기화 (yt-dlp 기반)
=============================================================
- yt-dlp `extract_flat`로 videoId·제목·채널을 안정적으로 가져옴 (인증/쿠키 불필요)
- videoId 순서까지 라이브 플레이리스트와 동일하게 맞춤 (삭제곡 제거 포함)
- 기존 tracks.json의 정제된 title/artist는 보존 (videoId 매칭),
  신규 트랙만 채널명에서 best-effort 아티스트 추출 ("- Topic" 등 정리)

사용:
  python3 sync_playlist.py              # tracks.json 갱신
  python3 sync_playlist.py --dry-run    # 변경만 출력, 파일 미수정

종료 코드: 0=변경없음, 10=변경있음, 1=에러
"""

import argparse
import json
import re
import sys
from pathlib import Path

import random

from yt_dlp import YoutubeDL

from build import SITES  # 단일 설정 소스 (playlist_id / tracks_file / shuffle)

ROOT = Path(__file__).parent
SITE_BY_KEY = {c["key"]: c for c in SITES}
DEFAULT_KEY = "slow"


def clean_artist(channel: str) -> str:
    """채널명 → best-effort 아티스트명."""
    a = (channel or "").strip()
    a = re.sub(r"\s*-\s*Topic$", "", a)          # YouTube Music 자동 채널
    a = re.sub(r"\s*[-–|]\s*.*?(playlist|플레이리스트).*$", "", a, flags=re.I)
    return a.strip() or "Unknown"


def fetch_live(playlist_id: str) -> list:
    """라이브 플레이리스트를 {videoId,title,channel} 순서대로 반환."""
    url = f"https://www.youtube.com/playlist?list={playlist_id}"
    opts = {
        "quiet": True, "no_warnings": True,
        "extract_flat": True, "skip_download": True,
        "ignoreerrors": True,
    }
    with YoutubeDL(opts) as y:
        info = y.extract_info(url, download=False)
    out, seen = [], set()
    for e in (info or {}).get("entries", []):
        if not e:
            continue
        vid = e.get("id")
        title = (e.get("title") or "").strip()
        if not vid or vid in seen or not title:
            continue
        if title in ("[Private video]", "[Deleted video]", "[Unavailable video]"):
            continue
        seen.add(vid)
        out.append({
            "videoId": vid,
            "title": title,
            "channel": e.get("uploader") or e.get("channel") or "",
        })
    return out


def load_existing(tracks_file: Path) -> list:
    if tracks_file.exists():
        return json.loads(tracks_file.read_text(encoding="utf-8"))
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--playlist", default=DEFAULT_KEY, choices=list(SITE_BY_KEY),
                    help="동기화할 플레이리스트 키 (slow=Mr.Slow, low=Mr.Low)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg = SITE_BY_KEY[args.playlist]
    playlist_id = cfg["playlist_id"]
    tracks_file = ROOT / cfg["tracks_file"]
    shuffle = cfg.get("shuffle", False)
    print(f"[sync] 대상: {args.playlist} ({playlist_id}) → {cfg['tracks_file']}"
          f"{' [shuffle]' if shuffle else ''}")

    try:
        live = fetch_live(playlist_id)
    except Exception as e:
        print(f"✖ 플레이리스트 가져오기 실패: {e}", file=sys.stderr)
        sys.exit(1)

    if not live:
        print(f"✖ 트랙 0개 — 안전을 위해 {cfg['tracks_file']} 덮어쓰지 않음", file=sys.stderr)
        sys.exit(1)

    old = load_existing(tracks_file)
    old_by_id = {t["videoId"]: t for t in old}

    # 라이브 순서대로 재구성: 기존 정제 메타 보존, 신규는 채널명 정리
    new, added = [], []
    for t in live:
        vid = t["videoId"]
        if vid in old_by_id:
            prev = old_by_id[vid]
            new.append({"videoId": vid,
                        "title": prev.get("title") or t["title"],
                        "artist": prev.get("artist") or clean_artist(t["channel"])})
        else:
            entry = {"videoId": vid, "title": t["title"],
                     "artist": clean_artist(t["channel"])}
            new.append(entry)
            added.append(entry)

    live_ids = {t["videoId"] for t in live}
    removed = [t for t in old if t["videoId"] not in live_ids]

    print(f"[sync] 라이브 {len(new)}곡 / 기존 {len(old)}곡")
    for t in added:
        print(f"   + {t['artist']} - {t['title']}  ({t['videoId']})")
    for t in removed:
        print(f"   - {t.get('artist')} - {t.get('title')}  ({t['videoId']})")

    set_changed = bool(added or removed)
    order_changed = [t["videoId"] for t in old] != [t["videoId"] for t in new]

    # 셔플 사이트: 매 실행마다 순서를 새로 섞어 리프레시 (집합 유지)
    if shuffle:
        random.shuffle(new)

    changed = set_changed or order_changed or shuffle
    if not changed:
        print("[sync] 변경 없음")
        sys.exit(0)

    if args.dry_run:
        extra = " / 셔플" if shuffle else ""
        print(f"[sync] (dry-run) 신규 {len(added)} / 삭제 {len(removed)}{extra} — 파일 미수정")
        sys.exit(10)

    tracks_file.write_text(
        json.dumps(new, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[sync] {cfg['tracks_file']} 갱신 완료 "
          f"(신규 {len(added)} / 삭제 {len(removed)}{' / 셔플' if shuffle else ''} → 총 {len(new)})")
    sys.exit(10)


if __name__ == "__main__":
    main()
