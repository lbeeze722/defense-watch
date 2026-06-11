#!/bin/zsh
# Defense Watch pulse — run by launchd every 5 minutes.
# Market hours: quotes every run, fast news every 3rd run, full refresh hourly.
# Off hours: full refresh every 6 hours (keeps news current overnight/weekends).

export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin"
cd /Users/jobysodi/defense-watch || exit 1

# Don't overlap a still-running fetch
pgrep -qf "fetch_data.py" && exit 0

NOW=$(date +%s)
LAST_FULL=0
[ -f .last_full ] && LAST_FULL=$(stat -f %m .last_full)
FULL_AGE=$(( NOW - LAST_FULL ))

ET_DOW=$(TZ=America/New_York date +%u)   # 1=Mon .. 7=Sun
ET_HM=$(TZ=America/New_York date +%H%M)
MARKET=0
if [ "$ET_DOW" -le 5 ] && [ "$ET_HM" -ge 0855 ] && [ "$ET_HM" -le 1635 ]; then
  MARKET=1
fi

MODE=""
if [ "$MARKET" -eq 1 ]; then
  if [ "$FULL_AGE" -gt 3300 ]; then
    MODE="full"
  else
    COUNT=$(cat .pulse_count 2>/dev/null || echo 0)
    COUNT=$(( (COUNT + 1) % 3 ))
    echo "$COUNT" > .pulse_count
    if [ "$COUNT" -eq 0 ]; then MODE="--news-light"; else MODE="--quotes-only"; fi
  fi
else
  if [ "$FULL_AGE" -gt 21600 ]; then MODE="full"; else exit 0; fi
fi

echo "--- pulse $(TZ=America/New_York date '+%Y-%m-%d %H:%M %Z') mode=$MODE"
if [ "$MODE" = "full" ]; then
  python3 fetch_data.py || exit 1
  touch .last_full
else
  python3 fetch_data.py "$MODE" || exit 1
fi

# Validate before publishing
python3 -c "import json; json.loads(open('data.js').read().split('=',1)[1].rstrip().rstrip(';'))" || exit 1

git add -A
git commit -m "data pulse" || exit 0   # nothing to commit
git pull --rebase origin main
git push origin main
echo "pushed ok"
