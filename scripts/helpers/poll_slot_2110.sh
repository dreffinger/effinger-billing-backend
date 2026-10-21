#!/usr/bin/env bash
# PLAIN ENGLISH: poll the GitHub billing-button workflow (read-only) until a run newer than #129 has COMPLETED, or until 21:42Z with none started.
# Prints one line per state change; exits 0 when complete, 2 when nothing fired by the deadline, 3 if still running at 21:58Z.
url="https://api.github.com/repos/dreffinger/effinger-billing-backend/actions/workflows/billing-button.yml/runs?per_page=1"
last=""
while true; do
  now=$(date -u +%H%M)
  j=$(curl -sS --max-time 20 -H 'Accept: application/vnd.github+json' "$url" 2>/dev/null || true)
  line=$(python3 - "$j" <<'PY'
import json,sys
try:
    d=json.loads(sys.argv[1]); r=d["workflow_runs"][0]
    print(r["run_number"], r["status"], r.get("conclusion"), r["run_started_at"], r["updated_at"], r["id"])
except Exception as e:
    print("parse-error", str(e)[:80])
PY
)
  if [ "$line" != "$last" ]; then echo "$(date -u +%H:%M:%SZ) $line"; last="$line"; fi
  set -- $line
  if [ "$1" != "parse-error" ] && [ "$1" -gt 129 ] 2>/dev/null && [ "$2" = "completed" ]; then echo "SLOT_DONE $line"; exit 0; fi
  if [ "$now" -ge 2142 ] && { [ "$1" = "parse-error" ] || [ "$1" -le 129 ]; }; then echo "NO_SLOT_BY_2142"; exit 2; fi
  if [ "$now" -ge 2158 ]; then echo "SLOT_STILL_RUNNING_AT_2158 $line"; exit 3; fi
  sleep 30
done
