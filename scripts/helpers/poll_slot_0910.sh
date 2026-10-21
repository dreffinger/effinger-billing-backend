#!/bin/bash
# poll the GitHub billing-button workflow until a run newer than #123 completes, or 09:47Z passes (then the engine pass runs on its own)
while true; do
  now=$(date -u +%H%M)
  line=$(curl -sS --max-time 20 "https://api.github.com/repos/dreffinger/effinger-billing-backend/actions/workflows/billing-button.yml/runs?per_page=1" | python3 -c "import json,sys; d=json.load(sys.stdin); r=d['workflow_runs'][0]; print(r['run_number'], r['status'], r['conclusion'], r['created_at'], r['updated_at'])" 2>/dev/null)
  echo "$(date -u +%H:%M:%SZ) $line"
  set -- $line
  if [ "${1:-0}" -gt 123 ] && [ "$2" = "completed" ]; then echo "SLOT_DONE $line"; exit 0; fi
  if [ "${1:-0}" -gt 123 ]; then :; elif [ "$now" -ge 0947 ]; then echo "NO_SLOT_BY_0947"; exit 0; fi
  if [ "$now" -ge 1005 ]; then echo "SLOT_TIMEOUT $line"; exit 0; fi
  sleep 45
done
