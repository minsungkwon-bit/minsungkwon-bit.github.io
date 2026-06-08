#!/usr/bin/env bash
# 1회 동기화 사이클: sync → (변경 시) build → 고아 트랙 페이지 정리 → commit → push
# 사용: ./run_sync.sh [--no-push]
set -uo pipefail

cd "$(dirname "$0")"
PY=".venv/bin/python"
DOMAIN="https://minsungkwon-bit.github.io"
PUSH=1
[[ "${1:-}" == "--no-push" ]] && PUSH=0

ts() { date -u +'%Y-%m-%dT%H:%M:%SZ'; }
log() { echo "[$(ts)] $*"; }

log "▶ sync 시작"
"$PY" sync_playlist.py
RC=$?

if [[ $RC -eq 0 ]]; then
  log "변경 없음 — 종료"; exit 0
elif [[ $RC -ne 10 ]]; then
  log "✖ sync 에러(rc=$RC) — 빌드 중단"; exit 1
fi

log "변경 감지 → 빌드"
"$PY" build.py --domain "$DOMAIN" || { log "✖ build 실패"; exit 1; }

# 고아 트랙 페이지/OG 정리 (tracks.json에 없는 videoId 폴더 제거)
log "고아 트랙 페이지 정리"
"$PY" - <<'PY'
import json, shutil
from pathlib import Path
ids = {t["videoId"] for t in json.load(open("tracks.json"))}
removed = 0
tdir = Path("tracks")
if tdir.exists():
    for d in tdir.iterdir():
        if d.is_dir() and d.name not in ids:
            shutil.rmtree(d); removed += 1
            og = Path("og") / f"track-{d.name}.png"
            if og.exists(): og.unlink()
print(f"  고아 폴더 {removed}개 제거")
PY

if [[ $PUSH -eq 0 ]]; then
  log "● --no-push: 로컬 빌드까지만. git 변경분:"; git status -s | head; exit 0
fi

log "git commit & push"
git add -A
if git diff --staged --quiet; then
  log "스테이징 변경 없음 — push 스킵"; exit 0
fi
git commit -q -m "sync: playlist auto-sync $(ts)

🤖 10-min auto-sync" || { log "✖ commit 실패"; exit 1; }
GIT_TERMINAL_PROMPT=0 git push -q origin main || { log "✖ push 실패"; exit 1; }
log "✔ push 완료 — GitHub Pages 재배포 대기"
