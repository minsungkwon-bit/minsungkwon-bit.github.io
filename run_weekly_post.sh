#!/usr/bin/env bash
# 주간 블로그 포스트 발행: sync(있으면) → build --new-post → commit → push.
# run_sync.sh 와 달리 트랙 변경이 없어도 항상 build --new-post 를 돌려
# 이번 주차 포스트(YYYY-Www-fresh-finds)를 생성한다. 이미 있으면 build.py가 스킵.
# 사용: ./run_weekly_post.sh [--no-push]
set -uo pipefail

cd "$(dirname "$0")"
PY=".venv/bin/python"
DOMAIN="https://minsungkwon-bit.github.io"
PUSH=1
[[ "${1:-}" == "--no-push" ]] && PUSH=0

ts() { date -u +'%Y-%m-%dT%H:%M:%SZ'; }
log() { echo "[$(ts)] $*"; }

# 1) 트랙 최신화 (best-effort; 실패해도 포스트 발행은 진행)
log "▶ sync (best-effort)"
"$PY" sync_playlist.py
RC=$?
if [[ $RC -eq 10 ]]; then
  log "트랙 변경 감지됨"
elif [[ $RC -eq 0 ]]; then
  log "트랙 변경 없음"
else
  log "⚠ sync rc=$RC — 무시하고 포스트 발행 계속"
fi

# 2) 이번 주차 포스트 생성 + 전체 사이트 빌드
log "build --new-post"
"$PY" build.py --domain "$DOMAIN" --new-post || { log "✖ build 실패"; exit 1; }

# 3) 고아 트랙 페이지/OG 정리 (run_sync.sh 와 동일)
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
  log "● --no-push: 로컬 빌드까지만. git 변경분:"; git status -s | head -20; exit 0
fi

log "git commit & push"
git add -A
if git diff --staged --quiet; then
  log "스테이징 변경 없음 — push 스킵 (이번 주 포스트 이미 발행됨)"; exit 0
fi
git commit -q -m "post: weekly blog auto-publish $(ts)

🤖 weekly post" || { log "✖ commit 실패"; exit 1; }
GIT_TERMINAL_PROMPT=0 git push -q origin main || { log "✖ push 실패"; exit 1; }
log "✔ push 완료 — GitHub Pages 재배포 대기"
