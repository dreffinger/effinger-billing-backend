#!/usr/bin/env bash
# PLAIN ENGLISH: poll the GitHub billing-button workflow (read-only) until a run newer than #127 has COMPLETED, or until 15:42Z with none started.
# Prints one line per state change; exits 0 when complete, 2 when nothing fired by the deadline.
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
  if [ "$1" != "parse-error" ] && [ "$1" -gt 127 ] 2>/dev/null && [ "$2" = "completed" ]; then echo "SLOT_DONE $line"; exit 0; fi
  if [ "$now" -ge 1742 ] && { [ "$1" = "parse-error" ] || [ "$1" -le 127 ]; }; then echo "NO_SLOT_BY_1742"; exit 2; fi
  if [ "$now" -ge 1758 ]; then echo "SLOT_STILL_RUNNING_AT_1758 $line"; exit 3; fi
  sleep 30
done
