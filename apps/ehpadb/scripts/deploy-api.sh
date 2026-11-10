#!/usr/bin/env bash
# PLAIN ENGLISH: deploy the ehpa applications Function with the Neon API instead of the neon CLI. Builds the browser bundle,
# bundles and zips the Function, uploads the zip to the branch's deploy endpoint, then waits until Neon reports the deployment
# completed (or failed) and checks /health on the Function's own URL.
#   scripts/deploy-api.sh preview                      the upo-preview branch (optimization/.preview_branch holds its id)
#   scripts/deploy-api.sh prod                         the production branch - the live app at app.ehpa.dev
#   scripts/deploy-api.sh preview --env-json '{"ALLOWED_EMAILS":"a@b.c","SESSION_IDLE_MINUTES":"30"}'   also replace the environment
# Without --env-json the deployment keeps the environment it already has (ALLOWED_EMAILS, SESSION_IDLE_MINUTES).
# The Neon API key is never in this file or in the repository: in the ehpa cloud environment the network proxy adds it to every
# request to console.neon.tech; anywhere else, export NEON_API_KEY first.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; repo="$(cd "$here/../.." && pwd)"
PROJECT="steep-rain-79347575"; SLUG="ehpadb"; PROD_BRANCH="br-morning-mode-bcbgg49q"
target="${1:-}"; shift || true
case "$target" in
  prod) BRANCH="$PROD_BRANCH" ;;
  preview) BRANCH="$(cat "$repo/optimization/.preview_branch" 2>/dev/null || true)"; [ -n "$BRANCH" ] || { echo "deploy: optimization/.preview_branch is missing (the preview branch id, br-...)"; exit 2; } ;;
  *) echo "deploy: say preview or prod"; exit 2 ;;
esac
[ "$target" = prod ] || [ "$BRANCH" != "$PROD_BRANCH" ] || { echo "deploy: the preview branch id equals production"; exit 2; }
ENVJSON=""; while [ $# -gt 0 ]; do case "$1" in --env-json) ENVJSON="$2"; shift 2 ;; *) echo "deploy: unknown option $1"; exit 2 ;; esac; done
API="https://console.neon.tech/api/v2/projects/$PROJECT/branches/$BRANCH/functions/$SLUG"
AUTH=(-H "Authorization: Bearer ${NEON_API_KEY:-proxy-injected}" -H "Accept: application/json")

cd "$here"
node scripts/bundle-client.mjs
node scripts/bundle-function.mjs
args=(-F "zip=@dist/function.zip;type=application/zip" -F "runtime=nodejs24")
[ -z "$ENVJSON" ] || args+=(-F "environment=$ENVJSON")
code=$(curl -sS -m 180 -o dist/deploy.json -w '%{http_code}' -X POST "${AUTH[@]}" "${args[@]}" "$API/deployments")
[ "$code" = 200 ] || [ "$code" = 201 ] || [ "$code" = 202 ] || { echo "deploy: upload answered HTTP $code: $(head -c 400 dist/deploy.json)"; exit 1; }
id=$(python3 -c "import json;d=json.load(open('dist/deploy.json'));d=d.get('deployment',d);print(d.get('id',''))")
echo "deploy: uploaded to $target ($BRANCH), deployment $id"
for i in $(seq 1 60); do
  curl -sS -m 30 "${AUTH[@]}" -o dist/function.json "$API"
  read -r st url <<<"$(python3 -c "
import json;d=json.load(open('dist/function.json'));d=d.get('function',d);c=d.get('current_deployment') or {}
print((c.get('status') or '?') + ':' + str(c.get('id')), d.get('invocation_url',''))")"
  case "$st" in completed:"$id") break ;; failed:*) echo "deploy: FAILED ($st): $(head -c 600 dist/function.json)"; exit 1 ;; esac
  python3 -c "import time;time.sleep(4)"
done
[ "${st%%:*}" = completed ] || { echo "deploy: still $st after 4 minutes"; exit 1; }
health=$(curl -sS -m 30 -o /dev/null -w '%{http_code}' "${url%/}/health")
echo "deploy: $st on $target - $url - /health answered $health"
[ "$health" = 200 ]
