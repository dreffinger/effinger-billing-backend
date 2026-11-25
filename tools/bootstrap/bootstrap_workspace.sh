#!/usr/bin/env bash
# bootstrap_workspace.sh - lay out /home/claude/unbilled inside a FRESH cloud container.
# Written 9/11/2026 for the "ehpa cloud" copy of the 2-hourly Backend billing run.
#
# The run (Claude) fetches every remote piece with the connectors (Google Drive, Gmail) or the
# attached GitHub repository; this script only does the LOCAL work: network self-check, file
# layout from the repo clone, the amd.py shim recipe, and a presence/absence manifest.
#
#   bash tools/bootstrap_workspace.sh net              # exit 0 = AdvancedMD reachable, 3 = blocked by the egress policy
#   bash tools/bootstrap_workspace.sh layout [REPO]    # copy helpers from the repo clone into the workspace (never clobbers newer files)
#   bash tools/bootstrap_workspace.sh check            # manifest of helpers / creds / state; exit 1 if a REQUIRED helper is missing
#
# Nothing here prints a secret. Nothing here logs in to AdvancedMD (that is amd.login_cached(), ONE attempt).
set -u
WS="${WS:-/home/claude/unbilled}"
REPO_DEFAULT="/home/claude/effinger-billing-backend"
mode="${1:-check}"

hdr() { printf '\n== %s ==\n' "$*"; }

probe() {  # probe <label> <url>  -> stdout: code only ("000" = tunnel refused / unreachable); label line goes to stderr
  local code
  code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 20 "$2" 2>/dev/null || true)
  [ -z "$code" ] && code="000"
  printf '  %-34s HTTP %s\n' "$1" "$code" >&2
  echo "$code"
}

case "$mode" in
  net)
    hdr "network self-check ($(date -u +'%Y-%m-%d %H:%M UTC'))"
    a=$(probe "AMD login gateway" "https://partnerlogin.advancedmd.com/")
    b=$(probe "AMD REST (pm-api-103)" "https://pm-api-103.advancedmd.com/")
    c=$(probe "Stedi healthcare API" "https://healthcare.us.stedi.com/")
    g=$(probe "GitHub repo (via proxy)" "https://api.github.com/repos/dreffinger/effinger-billing-backend")
    if [ "$a" = "000" ] || [ "$b" = "000" ]; then
      echo "RESULT: AMD_BLOCKED - this environment's network policy refuses AdvancedMD (CONNECT 403 / host_not_allowed)."
      echo "        Fix: routine -> Edit -> environment (cloud icon) -> Network access: Custom -> allow *.advancedmd.com, healthcare.us.stedi.com, api.stedi.com (or Full)."
      exit 3
    fi
    [ "$c" = "000" ] && echo "WARN: Stedi unreachable - cascade lookups will skip to William/board."
    # Stedi credential mode (free call, no key sent): 200 = the environment API credential is attached by the proxy -> write no key file
    sc=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 20 "https://healthcare.us.stedi.com/2024-04-01/payers/search?query=medicare" 2>/dev/null || true)
    [ -z "$sc" ] && sc="000"
    if [ "$sc" = "200" ]; then echo "STEDI_CRED_OK: environment API credential attached - do NOT write secrets/stedi_live.key."; else echo "STEDI_CRED_MISSING (HTTP $sc): no environment credential for healthcare.us.stedi.com - fall back to the Gmail key (thread 1a083035f566f9fb) -> secrets/stedi_live.key."; fi
    if [ "$g" = "200" ]; then echo "GitHub: repository attached (API reachable)."; else echo "GitHub: repo NOT attached to this session (HTTP $g) - mirror.py will fall back to a bundle on Drive."; fi
    # Neon Postgres - the permanent store (11/6/2026): can this container reach the endpoint at all (HTTPS SQL route on 443)?
    n=$(probe "Neon endpoint (HTTPS SQL route)" "https://ep-proud-waterfall-bczdy4bi.c-16.us-east-1.aws.neon.tech/sql")
    if [ "$n" = "000" ]; then echo "NEON_BLOCKED: the egress policy refuses the Neon hosts - add ep-proud-waterfall-bczdy4bi.c-16.us-east-1.aws.neon.tech, ep-proud-waterfall-bczdy4bi-pooler.c-16.us-east-1.aws.neon.tech and console.neon.tech to Network access (routine -> Edit -> environment); tools/db/neon_db.py loads report 'no path to the database' until then."; else echo "NEON_REACHABLE (HTTP $n on 443 - python3 tools/db/neon_db.py egress-test tells 5432 vs 443 once the connection string is in place)."; fi
    echo "RESULT: AMD_OK"
    exit 0
    ;;

  layout)
    REPO="${2:-$REPO_DEFAULT}"
    mkdir -p "$WS" "$WS/secrets" "$WS/patient_db" "$WS/era_details" "$WS/outbox" "$WS/chat_history" "$WS/tools" "$WS/logs" "$WS/registers" "$WS/inbox"
    chmod 700 "$WS/secrets"
    if [ ! -d "$REPO" ]; then
      echo "layout: no repo clone at $REPO - skipping repo copy (Drive overlay only)."; exit 0
    fi
    hdr "layout from $REPO ($(git -C "$REPO" rev-parse --short HEAD 2>/dev/null || echo 'no git'))"
    n=0
    # 1) flat helpers first (highest fidelity to the nightly workspace), then module trees; never overwrite a NEWER workspace file
    for src in "$REPO/scripts/helpers" "$REPO/nightly/helpers" "$REPO/core" "$REPO/eligibility" "$REPO/boards" "$REPO/billing" "$REPO/credentialing"; do
      [ -d "$src" ] || continue
      while IFS= read -r -d '' f; do
        base=$(basename "$f")
        case "$base" in __init__.py|setup.py|conftest.py) continue;; esac
        dst="$WS/$base"
        if [ ! -e "$dst" ] || [ "$f" -nt "$dst" ]; then cp -p "$f" "$dst"; n=$((n+1)); fi
      done < <(find "$src" -maxdepth 2 -type f \( -name '*.py' -o -name '*.sh' \) -print0)
    done
    # 2) practice data: rich carriers map kept beside the simple one precheck.py expects
    [ -f "$REPO/practices/ehpa/carriers.json" ] && cp -p "$REPO/practices/ehpa/carriers.json" "$WS/carriers_rich.json"
    [ -f "$REPO/practices/ehpa/facilities.json" ] && [ ! -e "$WS/facilities.json" ] && cp -p "$REPO/practices/ehpa/facilities.json" "$WS/facilities.json"
    [ -f "$REPO/practices/ehpa/rules.md" ] && cp -p "$REPO/practices/ehpa/rules.md" "$WS/rules.md"
    # 2b) practice state kept in the repo (9/30/2026); patient_db/ and era_details/ are PHI and travel only in the Drive state bundle
    mkdir -p "$WS/registers"
    [ -d "$REPO/practices/ehpa/registers" ] && cp -pn "$REPO"/practices/ehpa/registers/* "$WS/registers/" 2>/dev/null
    for f in needs_facesheet_list.md laterality_flag_log.md; do [ -f "$REPO/practices/ehpa/$f" ] && [ ! -e "$WS/$f" ] && cp -p "$REPO/practices/ehpa/$f" "$WS/$f"; done
    # 2c) Claimocity feed helper needs a working cryptography (the image's system module panics under pyo3, 11/3-11/4/2026 x4):
    if ! python3 -c "import cryptography.hazmat.primitives.hashes" >/dev/null 2>&1; then
      python3 -m pip install -q --ignore-installed --target /home/claude/pylib cryptography cffi >/dev/null 2>&1 \
        && echo "layout: cryptography installed into /home/claude/pylib - run the feed helpers with PYTHONPATH=/home/claude/pylib CLOUDSDK_PYTHON=/usr/bin/python3" \
        || echo "layout: WARN cryptography pylib install failed - claimocity_gcs.py may panic (see captured_calls.md 11/3)"
    fi
    # 3) docs the run needs locally
    for d in docs/captured_calls.md docs/api_vocabulary.json docs/MIRROR.md; do
      [ -f "$REPO/$d" ] && [ ! -e "$WS/$(basename "$d")" ] && cp -p "$REPO/$d" "$WS/$(basename "$d")"
    done
    # 4) tools - missing ones are added; the state-bundle tool is REPLACED by the repository's copy (11/25/2026: the prompts take
    #    tools/ws_bundle.py from Drive first, and with 'cp -pn' an older Drive copy kept packing for ever - a fix on main never reached
    #    a run). This script itself is not replaced here: it is running; the prompts copy it from the clone before they start it.
    mkdir -p "$WS/tools"
    [ -f "$REPO/tools/bootstrap/ws_bundle.py" ] && cp -p "$REPO/tools/bootstrap/ws_bundle.py" "$WS/tools/ws_bundle.py"
    [ -d "$REPO/tools/bootstrap" ] && cp -pn "$REPO"/tools/bootstrap/* "$WS/tools/" 2>/dev/null
    # 5) amd.py shim recipe (restore recipe 9/10/2026): workspace amd.py = repo core/amd.py + compat shims appended
    if [ -f "$WS/amd.py" ] && ! grep -q '^def call(' "$WS/amd.py"; then
      shim=$(ls "$WS"/amd_shims_*.py 2>/dev/null | tail -n1)
      if [ -n "$shim" ]; then cat "$shim" >> "$WS/amd.py"; echo "layout: appended $(basename "$shim") to amd.py"; else echo "layout: WARN amd.py lacks call()/rest_post() and no amd_shims_*.py found - download it from Drive 'workspace mirror'"; fi
    fi
    # 6) simple carriers.json (code -> carN) is what precheck.py / claims_audit.py read; derive it from the rich map if missing
    if [ ! -f "$WS/carriers.json" ] && [ -f "$WS/carriers_rich.json" ]; then
      python3 - "$WS" <<'PY'
import json,sys,os
ws=sys.argv[1]; rich=json.load(open(os.path.join(ws,'carriers_rich.json')))
simple={}
for k,v in rich.items():
    if isinstance(v,(list,tuple)) and v and k.startswith('car'): simple[str(v[0])]=k
    elif isinstance(v,str) and v.startswith('car'): simple[k]=v
json.dump(simple,open(os.path.join(ws,'carriers.json'),'w'),indent=1)
print('layout: derived simple carriers.json with',len(simple),'codes')
PY
    fi
    # 7) OCR tooling (William 9/17/2026: "add the ability back to ocr a pdf") - scanned facesheets need pdftoppm + tesseract;
    #    the cloud container starts without them. Best effort, never fatal; Network access must allow apt/pip.
    if ! command -v tesseract >/dev/null 2>&1 || ! command -v pdftoppm >/dev/null 2>&1; then
      (apt-get update -q >/dev/null 2>&1 && apt-get install -y -q tesseract-ocr poppler-utils >/dev/null 2>&1) && echo "layout: OCR tools installed (tesseract, poppler-utils)" || echo "layout: WARN could not install tesseract/poppler (apt blocked?) - scanned PDFs cannot be OCRed this run"
    fi
    # 8) python deps the fresh image lacks (10/6/2026: /usr/local python3.11 had no `requests`; `pip` is the 3.13 one - use python3 -m pip)
    python3 -c "import requests" 2>/dev/null || python3 -m pip install -q requests >/dev/null 2>&1 || echo "layout: WARN could not pip-install requests - amd.py will not import"
    python3 -c "import pymupdf" 2>/dev/null || python3 -m pip install -q pymupdf >/dev/null 2>&1 || true
    python3 -c "import openpyxl, pypdf" 2>/dev/null || python3 -m pip install -q openpyxl pypdf >/dev/null 2>&1 || true
    python3 -c "import pg8000" 2>/dev/null || python3 -m pip install -q pg8000 >/dev/null 2>&1 || echo "layout: WARN could not pip-install pg8000 - neon_db.py falls back to the HTTPS SQL route"
    [ -s "$WS/secrets/neon_database_url" ] && mkdir -p "$REPO/secrets" && cp -p "$WS/secrets/neon_database_url" "$REPO/secrets/neon_database_url" && chmod 600 "$REPO/secrets/neon_database_url"
    chmod +x "$WS"/*.sh "$WS"/tools/*.sh 2>/dev/null
    echo "layout: copied/refreshed $n helper files into $WS"
    exit 0
    ;;

  check)
    hdr "workspace manifest $WS ($(date -u +'%Y-%m-%d %H:%M UTC'))"
    REQ="amd.py stedi.py elig271.py elig_amd.py resave.py precheck.py inspector_0907.py columns_scan.py unbilled_repair.py payreasons.py dx_primary_fix.py era_upload.py era_post.py era_fallback_0913b.py era_clear.py claimocity_in1.py add_ins.py ins_update.py freq1_visit.py patient_patch.py move_to_ins.py void_scan.py void_tx.py txh.py deceased_guard.py death_check_review.py death_off_record.py"
    OPT="amdw.py manual_post.py restore_charge.py era_manual_post.py era_details_pull.py columns_inspector2_0908.py working_denials.py working_denials_act.py availity_pdf.py availity_remits.py github_sync.py carriers.json facilities.json api_vocabulary.json"
    missing=0
    for f in $REQ; do if [ -f "$WS/$f" ]; then printf '  ok       %s\n' "$f"; else printf '  MISSING  %s   (required by the standing prompt)\n' "$f"; missing=$((missing+1)); fi; done
    for f in $OPT; do if [ -f "$WS/$f" ]; then printf '  ok       %s\n' "$f"; else printf '  absent   %s   (optional)\n' "$f"; fi; done
    hdr "credentials (presence only)"
    [ -s "$WS/.amd_cred.json" ] && echo "  ok       .amd_cred.json (AMD password, Gmail thread 1866ce7e2233e4c0)" || [ -n "${AMD_PSW:-}" ] && echo "  ok       AMD_PSW environment credential (no credential file needed)" || echo "  MISSING  .amd_cred.json  -> write {\"psw\": \"<from Gmail thread 1866ce7e2233e4c0>\"} (chmod 600)"
    [ -s "$WS/secrets/stedi_live.key" ] && echo "  ok       secrets/stedi_live.key (Gmail fallback, thread 1a083035f566f9fb)" || echo "  proxy    secrets/stedi_live.key absent - relying on the environment API credential (bootstrap net must have printed STEDI_CRED_OK)"
    if [ -n "${NEON_DATABASE_URL:-}" ]; then echo "  ok       NEON_DATABASE_URL environment variable (permanent store: Neon Postgres)"; elif [ -s "$WS/secrets/neon_database_url" ]; then echo "  ok       secrets/neon_database_url (permanent store: Neon Postgres; written from the Gmail thread 'neon database url')"; else echo "  absent   NEON_DATABASE_URL / secrets/neon_database_url -> the NEON_DATABASE_URL environment credential, else the Gmail thread 'neon database url' -> secrets/neon_database_url (neon_db.py loads print 'no connection string' and are skipped until one is in place; never Drive)"; fi
    [ -s "$WS/secrets/github_pat.key" ] && echo "  ok       secrets/github_pat.key (Gmail thread 'github claude token')" || echo "  absent   secrets/github_pat.key (only needed when the repo is not attached to the routine)"
    [ -s "$WS/secrets/pseudonyms.json" ] && echo "  ok       secrets/pseudonyms.json (Drive 'workspace mirror'; copy to <repo>/secrets/ before mirror.py)" || echo "  MISSING  secrets/pseudonyms.json -> Drive 'workspace mirror' pseudonyms.json"
    [ -e "$WS/.amd_login_lock" ] && echo "  LOCK     .amd_login_lock present - a prior login FAILED. Do NOT log in; report it and stop."
    hdr "state"
    for f in captured_calls.md needs_facesheet_list.md laterality_flag_log.md precheck_cache.json; do
      [ -f "$WS/$f" ] && printf '  ok       %-28s %s lines\n' "$f" "$(wc -l < "$WS/$f")" || printf '  absent   %-28s (starts empty this run unless restored from the Drive state bundle)\n' "$f"
    done
    printf '  patient_db/ %s patients, era_details/ %s checks\n' "$(ls "$WS/patient_db" 2>/dev/null | wc -l)" "$(ls "$WS/era_details" 2>/dev/null | wc -l)"
    if [ "$missing" -gt 0 ]; then echo "RESULT: $missing required helper(s) missing - restore from the attached repo (tools/bootstrap_workspace.sh layout) or the Drive state bundle before working the columns."; exit 1; fi
    echo "RESULT: workspace complete"
    exit 0
    ;;
  *) echo "usage: $0 net | layout [REPO] | check"; exit 2;;
esac
