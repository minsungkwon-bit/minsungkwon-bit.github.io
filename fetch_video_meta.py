"""
트랙별 YouTube 업로드 날짜/길이 수집 → video_meta.json (VideoObject 보강용).
증분 처리: video_meta.json에 없는 videoId만 새로 가져옴.

사용:
  python3 fetch_video_meta.py            # tracks.json 기준 누락분 보강
종료 코드: 0=정상(보강 없거나 완료), 1=에러
"""
import json
import sys
from pathlib import Path

from yt_dlp import YoutubeDL

ROOT = Path(__file__).parent
TRACKS_FILE = ROOT / "tracks.json"
META_FILE = ROOT / "video_meta.json"


def iso_duration(sec) -> str | None:
    if not sec:
        return None
    sec = int(sec)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    out = "PT"
    if h:
        out += f"{h}H"
    return out + f"{m}M{s}S"


def main():
    if not TRACKS_FILE.exists():
        print("✖ tracks.json 없음", file=sys.stderr)
        sys.exit(1)
    tracks = json.loads(TRACKS_FILE.read_text(encoding="utf-8"))
    ids = [t["videoId"] for t in tracks]
    meta = json.loads(META_FILE.read_text(encoding="utf-8")) if META_FILE.exists() else {}

    missing = [v for v in ids if v not in meta]
    print(f"[meta] 트랙 {len(ids)} / 기존 메타 {len(meta)} / 신규 {len(missing)}")
    if not missing:
        print("[meta] 보강할 항목 없음")
        sys.exit(0)

    opts = {"quiet": True, "no_warnings": True, "skip_download": True,
            "ignoreerrors": True, "extract_flat": False}
    ok = 0
    with YoutubeDL(opts) as y:
        for i, v in enumerate(missing, 1):
            try:
                info = y.extract_info(f"https://www.youtube.com/watch?v={v}", download=False)
            except Exception as e:
                print(f"  [{i}/{len(missing)}] {v} 실패: {str(e)[:60]}")
                continue
            if not info:
                print(f"  [{i}/{len(missing)}] {v} 정보없음")
                continue
            ud = info.get("upload_date")  # YYYYMMDD
            iso_date = f"{ud[:4]}-{ud[4:6]}-{ud[6:]}" if ud and len(ud) == 8 else None
            meta[v] = {"uploadDate": iso_date, "duration": iso_duration(info.get("duration"))}
            ok += 1
            if i % 10 == 0 or i == len(missing):
                print(f"  [{i}/{len(missing)}] {v} → {iso_date}")
                # 중간 저장 (긴 작업 중 중단 대비)
                META_FILE.write_text(
                    json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    META_FILE.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[meta] 완료: 신규 {ok}개 / 총 {len(meta)}개 → video_meta.json")


if __name__ == "__main__":
    main()
