#!/usr/bin/env bash
# Rebuilds /home/claude/unbilled on an empty container (nightly + 2-hourly routines). Idempotent.
# Fixes the 9/30/2026 gaps: money_template.html, openpyxl, registers, carriers, AMD credential file.
set -e
R="${1:-$(cd "$(dirname "$0")/.." && pwd)}"; W=/home/claude/unbilled
mkdir -p "$W/registers" "$R/secrets"
for d in core billing/* eligibility credentialing boards; do cp "$R"/$d/*.py "$W"/ 2>/dev/null || true; done
cp "$R"/scripts/helpers/*.py "$W"/ 2>/dev/null || true
cp "$R"/boards/templates/*.html "$W"/ 2>/dev/null || true
cp "$R"/practices/ehpa/{carriers.json,facilities.json,practice.json,rules.md} "$W/registers/" 2>/dev/null || true
cp "$R"/practices/ehpa/carriers.json "$W"/
cp -r "$R"/practices/ehpa/registers/. "$W/registers/" 2>/dev/null || true
cp "$R"/docs/captured_calls.md "$W"/ 2>/dev/null || true
python3 -c "import openpyxl, requests" 2>/dev/null || python3 -m pip install -q openpyxl requests 2>/dev/null || true
python3 -c "import pg8000" 2>/dev/null || python3 -m pip install -q pg8000 2>/dev/null || true   # Neon Postgres driver (pure Python); neon_db.py falls back to HTTPS SQL without it
if [ -n "${AMD_PSW:-}" ]; then python3 -c "import os,json;json.dump({'psw':os.environ['AMD_PSW']},open('$W/.amd_cred.json','w'))"; chmod 600 "$W/.amd_cred.json"; fi
# Still needed from Drive 'workspace mirror' (135OCbRNCnFLyVm2GBXk1XsE3lt0vnsrn): pseudonyms.json -> $R/secrets/, void_rules.json, precheck_cache.json, cred_nppes_snapshot.json
# Neon (the permanent store): NEON_DATABASE_URL environment credential first; else the Gmail thread 'neon database url' -> $W/secrets/neon_database_url AND $R/secrets/ (chmod 600) - never Drive, never committed
echo "bootstrap done: $(ls "$W" | wc -l) files in $W"
