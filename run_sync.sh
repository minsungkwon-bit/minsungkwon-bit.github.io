#!/usr/bin/env bash
# 1회 동기화 사이클: sync → (변경 시) build(전 사이트) → 고아 정리 → commit → push
# 사용: ./run_sync.sh [--playlist slow|low] [--no-push]
set -uo pipefail

cd "$(dirname "$0")"
PY=".venv/bin/python"
DOMAIN="https://minsungkwon-bit.github.io"
PLAYLIST="slow"
PUSH=1
for a in "$@"; do
  case "$a" in
    --no-push) PUSH=0 ;;
    slow|low) PLAYLIST="$a" ;;
  esac
done

ts() { date -u +'%Y-%m-%dT%H:%M:%SZ'; }
log() { echo "[$(ts)] $*"; }

log "▶ sync 시작 (playlist=$PLAYLIST)"
"$PY" sync_playlist.py --playlist "$PLAYLIST"
RC=$?

if [[ $RC -eq 0 ]]; then
  log "변경 없음 — 종료"; exit 0
elif [[ $RC -ne 10 ]]; then
  log "✖ sync 에러(rc=$RC) — 빌드 중단"; exit 1
fi

log "변경 감지 → 빌드(전 사이트)"
"$PY" build.py --domain "$DOMAIN" || { log "✖ build 실패"; exit 1; }

log "고아 트랙 페이지 정리"
"$PY" prune_orphans.py || { log "✖ prune 실패"; exit 1; }

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
