"""
tracks_*.json에 없는 트랙 페이지 폴더/OG 이미지 정리 (모든 사이트).
build.py의 SITES 설정을 그대로 사용 → 새 사이트 추가 시 자동 반영.
"""
import shutil
from pathlib import Path

from build import SITES, ROOT


def main():
    removed = 0
    for cfg in SITES:
        tfile = ROOT / cfg["tracks_file"]
        if not tfile.exists():
            continue
        import json
        ids = {t["videoId"] for t in json.loads(tfile.read_text(encoding="utf-8"))}
        base = cfg["base"].strip("/")
        tdir = (ROOT / base / "tracks") if base else (ROOT / "tracks")
        if not tdir.exists():
            continue
        for sub in tdir.iterdir():
            if sub.is_dir() and sub.name not in ids:
                shutil.rmtree(sub)
                og = ROOT / "og" / f"track-{sub.name}.png"
                if og.exists():
                    og.unlink()
                removed += 1
    print(f"[prune] 고아 트랙 페이지 {removed}개 제거")


if __name__ == "__main__":
    main()
