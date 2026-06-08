#!/usr/bin/env bash
# 10분마다 run_sync.sh 실행 (백그라운드 데몬). 로그: sync.log
# 시작: nohup ./loop_sync.sh > /dev/null 2>&1 &
# 중지: kill $(cat sync_loop.pid)
set -uo pipefail
cd "$(dirname "$0")"
INTERVAL="${1:-600}"   # 기본 600초 = 10분
echo $$ > sync_loop.pid
echo "[$(date -u +%FT%TZ)] ▶▶ loop 시작 (interval=${INTERVAL}s, pid=$$)" >> sync.log
trap 'echo "[$(date -u +%FT%TZ)] ■ loop 종료 (pid=$$)" >> sync.log; rm -f sync_loop.pid; exit 0' TERM INT
while true; do
  ./run_sync.sh >> sync.log 2>&1
  sleep "$INTERVAL"
done
