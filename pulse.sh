#!/bin/zsh
# Defense Watch quote pulse — run by launchd every 10 minutes.
# Refreshes quotes and pushes to GitHub Pages. Exits quietly outside market hours.

export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin"
cd /Users/jobysodi/defense-watch || exit 1

# Gate: weekdays 8:55 AM - 4:35 PM ET only
ET_DOW=$(TZ=America/New_York date +%u)   # 1=Mon .. 7=Sun
ET_HM=$(TZ=America/New_York date +%H%M)
if [ "$ET_DOW" -gt 5 ] || [ "$ET_HM" -lt 0855 ] || [ "$ET_HM" -gt 1635 ]; then
  exit 0
fi

echo "--- pulse $(TZ=America/New_York date '+%Y-%m-%d %H:%M %Z')"

# Every 3rd run (~15 min), also refresh mover headlines + fast news feeds
COUNT=$(cat .pulse_count 2>/dev/null || echo 0)
COUNT=$(( (COUNT + 1) % 3 ))
echo "$COUNT" > .pulse_count
if [ "$COUNT" -eq 0 ]; then
  python3 fetch_data.py --news-light || exit 1
else
  python3 fetch_data.py --quotes-only || exit 1
fi

# Validate before publishing
python3 -c "import json; json.loads(open('data.js').read().split('=',1)[1].rstrip().rstrip(';'))" || exit 1

git add -A
git commit -m "quote pulse" || exit 0   # nothing to commit
git pull --rebase origin main
git push origin main
echo "pushed ok"
