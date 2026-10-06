# PLAIN ENGLISH (Build the GitHub mirror of the Cloud Practice project from the workspace, William 9/7-9/8/2026)
# Decides: Nothing about billing. Rebuilds /home/claude/effinger-billing-backend from /home/claude/unbilled: every script goes
#   into the folder for the part of the practice it serves (core / billing / eligibility / credentialing / claimocity / boards /
#   nightly / practices/ehpa / docs). Any script whose text holds a member number, MBI or Medicaid id is replaced in the repo
#   by its PLAIN ENGLISH header plus a "local only" note - the full file stays in the workspace. The README is generated
#   from the headers so every script has an English write-up.
# Rules it uses: no PHI on GitHub. Patient surnames and first names are swapped for stable pseudonyms on the way in, using
#   the map at <workspace>/.pseudonyms.json - which holds real names, so it never leaves the workspace and this script
#   refuses to run without it. Clinician names, the practice name and payers are not in the map and pass through. No tokens,
#   keys, logs, JSON results, patient_db or spreadsheets ever go in. `ehpa` = Effinger Health PA, the first practice folder.
# Never touches: AMD, Stedi, the boards, the workspace scripts themselves.
# ---
import os, re, shutil, json, glob, subprocess, datetime
SRC = "/home/claude/unbilled"; DST = "/home/claude/effinger-billing-backend"

# --- pseudonyms -------------------------------------------------------------
# Patient surnames and first names are swapped for stable pseudonyms on the way
# into the mirror. The map holds real names, so it lives in the workspace and is
# never committed. Clinician names (Garland-G, Pam), the practice name and payers
# are not in the map and pass through untouched. Suffixes are preserved because
# only the name token is mapped: "<name> Jr" -> "<pseudonym> Jr".
# Fail closed: without the map this refuses to build rather than publish names.
NAMES_FILE = os.path.join(SRC, ".pseudonyms.json")
if not os.path.exists(NAMES_FILE):
    raise SystemExit("missing %s - the pseudonym map must exist before the mirror "
                     "is built, or real patient names would be published" % NAMES_FILE)
_MAP = json.load(open(NAMES_FILE))
NAMES = _MAP["names"]              # {"<real surname>": "<pseudonym>", ...}
_LOWER = set(_MAP.get("lower", []))  # names also swapped in lowercase (filenames)
_pairs = []
for _old in sorted(NAMES, key=len, reverse=True):     # longest first: compound names before their fragments
    _new = NAMES[_old]
    _pairs += [(_old, _new), (_old.upper(), _new.upper())]
    if _old in _LOWER:
        _pairs.append((_old.lower(), _new.lower()))
_LOOKUP = dict(_pairs)
# Anchor on letters only: an apostrophe must not block a possessive ("<name>'s")
# or a name followed by a closing quote.
NAME_RE = re.compile(r"(?<![A-Za-z])(" +
                     "|".join(re.escape(o) for o, _ in _pairs) + r")(?![A-Za-z])")
def depersonalize(t):
    return NAME_RE.sub(lambda m: _LOOKUP[m.group(1)], t)
# CAT below lists script basenames in their PSEUDONYMIZED form, so this file can
# be committed. The workspace files still carry the real surnames, so map back
# the other way to find the source.
_REV = {}
for _o, _n in NAMES.items():
    if _o in _LOWER: _REV[_n.lower()] = _o.lower()
REV_RE = re.compile(r"(?<![A-Za-z])(" +
                    "|".join(re.escape(o) for o in sorted(_REV, key=len, reverse=True)) +
                    r")(?![A-Za-z])") if _REV else None
def srcname(n):
    """Pseudonymized basename -> the real filename in the workspace."""
    return REV_RE.sub(lambda m: _REV[m.group(1)], n) if REV_RE else n
def outname(n):
    """Real basename -> the pseudonymized name written into the mirror."""
    return depersonalize(n)
def copy_clean(src, dst):
    """shutil.copy, but the text is pseudonymized on the way through."""
    open(dst, "w").write(depersonalize(open(src, errors="replace").read()))
PHI = re.compile(r'[0-9][A-Z][A-Z0-9][0-9][A-Z][A-Z0-9][0-9][A-Z]{2}[0-9]{2}|"[0-9]{9,11}"|\b[0-9]{2}/[0-9]{2}/(19[0-9]{2}|20[0-4][0-9])\b.{0,40}\b(dob|DOB|born)\b|\b(dob|DOB|born)\b.{0,40}\b[0-9]{2}/[0-9]{2}/(19[0-9]{2}|20[0-4][0-9])\b')
CAT = {
 "core":            "amd stedi txh resave recode add_ins ins_update patient_patch move_to_ins freq1_visit freq7_visit manual_post void_tx restore_charge void_rules precheck parse835 pcc_parse facesheet_auth elig_amd mark_done scripts_manifest build_repo".split(),
 "billing/claims_center": "inspector_0906 inspector_0907 apply_inspector_fix fix_admit_dates complete_admit_exclusions resolve_admits unbilled_0906 unbilled_0907 unbilled_0907_scan excl_act_0907 fix_freq7_exclusions fix_tricare_exclusions clean_1900 scan_alf_codes".split(),
 "billing/era":     "era_alloc_post era_clear era_fix_0907 era_manual_post era_post era_upload era_zero wo_reversal_post wo_reversal_scan wo_post wo_direct".split(),
 "billing/rebill":  "rebill_driver rebill_patient_year rebill_to_seq rebill_under_effinger reset_freq_rebill resend_notonfile wrongpayer_rebill gv_rebill run_gv add_modifier_rebill fairbank_gv bramwell_rebill aet12_rebill_0907 fcc_rebill_0907 i63_apply i63_scan2 i63_scan_par i63_sweep co24_restore pr27_b pr27_medicare move_audit_to_ins audit_pr_transfer build_pr_audit_wb wexford_fix ridgeway_fix stanhope_sterling elig_fix refresh3 refresh4 batch_refresh work_0906 restore_rest".split(),
 "billing/writeoff": "writeoff_0905 writeoff_old writeoff_old_notonfile writeoff_over365_0907".split(),
 "billing/scans":   "pay_scan mcad_pay_scan scan_co24 void_scan blank_begindate_scan sweep_full claim_status_sweep awv_due".split(),
 "eligibility":     "denial_cascade denial_cascade2 denial_act_0906 denial_act2 denial_act3 stedi_pass2 disc_run held_elig_0908".split(),
 "credentialing":   "cred_check".split(),
 "claimocity":      "claimocity_in1".split(),
 "boards":          "build_money build_learning_app board_facilities board_identity".split(),
}
DESC = {"core": "Shared library: the AMD client (one login, XML + REST), Stedi client, transaction history, the full-echo resave that protects charges, plan add/update, address PATCH, balance moves, frequency-1 rebill, manual posting, voids, 835 and facesheet parsers, AMD eligibility.",
 "billing/claims_center": "The daily Claims Center columns - Charge Review, Claim Inspector, Unbilled, Exclusions - and the fixes each one needs (admission dates, modifiers, dx edits, releases, completions).",
 "billing/era": "ERA Center: posting checks the way the Post button does, $0 process-accepted lines, dismiss / restore, the write-off reversal pipeline, manual posts for unvalidated lines.",
 "billing/rebill": "Re-pointing claims at the right payer and re-sending them as original claims: payer switches, GV hospice, I63 stroke recodes, CO24 restores, and the dated one-off passes (each header says what it decided that night).",
 "billing/writeoff": "Write-off passes: not-on-file remnants, cascade untimely, and the over-365-day rule (primary claims past a year with any carrier).",
 "billing/scans": "Read-only scans: payments by carrier, CO24, voids, blank begin dates, full claim-status sweep (Stedi 276/277), AWV due list.",
 "eligibility": "The insurance cascade: patient database -> AMD eligibility (free 271) -> Stedi eligibility / discovery -> facesheet -> William. Denial cascades ask the payers what coverage really was and sort every denied claim into an action.",
 "credentialing": "Nightly credentialing check (NPPES, Medicare revalidation, OIG) feeding the Credentialing Board; the board template lives in boards/templates.",
 "claimocity": "Claimocity hospital charge feed (HL7 drop on Drive, Cloud Run pull every 30 min) compared against AMD insurance.",
 "boards": "Builders for the Money Ledger, Programming Lab and the board facility lines, plus the HTML templates of the three boards.",
}
MASK = re.compile(r'[0-9][A-Z][A-Z0-9][0-9][A-Z][A-Z0-9][0-9][A-Z]{2}[0-9]{2}|\b[0-9]{9,11}\b')
def header(path):
    lines = []
    for l in open(path, errors="replace"):
        if l.startswith("# ---"): break
        if l.startswith("#"): lines.append(l)
        elif lines: break
    return [MASK.sub(lambda m: m.group(0) if m.group(0) in ("1629515325", "1225327380", "1235128869", "117065068") else "<id>", l) for l in lines]
def what(lines):
    t = " ".join(l.strip("# \n") for l in lines)
    m = re.search(r"PLAIN ENGLISH \((.*?)\)\s*Decides:\s*(.*?)(?:\s*Rules it uses:|\s*Never touches:|$)", t)
    return (m.group(1), m.group(2)) if m else ("", t[:200])
# fresh tree
for d in ("core", "billing", "eligibility", "credentialing", "claimocity", "boards", "nightly", "practices", "docs", "scripts", "templates"):
    shutil.rmtree(os.path.join(DST, d), ignore_errors=True)
placed = {}; local_only = []
for cat, names in CAT.items():
    os.makedirs(os.path.join(DST, cat), exist_ok=True)
    for n in names:
        s = os.path.join(SRC, srcname(n) + ".py")
        if not os.path.exists(s): print("missing", srcname(n)); continue
        txt = open(s, errors="replace").read()
        for ok in ("1629515325", "1225327380", "1235128869", "117065068"): txt = txt.replace(ok, "NPI")
        dst = os.path.join(DST, cat, n + ".py")
        if PHI.search(txt):
            hdr = header(s)
            open(dst, "w").write(depersonalize("".join(hdr)) + "# ---\n# LOCAL ONLY: the body of this script carries patient identifiers (member numbers / dates of birth) in its data table,\n# so only the header is mirrored. The full file lives in the workspace (/home/claude/unbilled/%s.py) and in the practice's Drive project folder.\n" % n)
            local_only.append(n)
        else: open(dst, "w").write(depersonalize(txt))
        placed[n] = cat
allpy = {os.path.basename(p)[:-3] for p in glob.glob(SRC + "/*.py")}
print("unplaced:", sorted(allpy - set(placed)))
# boards templates, nightly, practice config, docs
os.makedirs(DST + "/boards/templates", exist_ok=True)
for t, s in (("money_template.html", SRC + "/money_template.html"), ("tracker.html", SRC + "/tracker.html"), ("cred_board.html", SRC + "/cred_board.html")):
    if os.path.exists(s): copy_clean(s, DST + "/boards/templates/" + t)
    else: print("template missing", s)
os.makedirs(DST + "/nightly", exist_ok=True)
copy_clean("/tmp/claude-0/-home-claude/f8f2f49c-f474-51d0-8966-696579307f2a/scratchpad/nightly_prompt_v5.txt", DST + "/nightly/nightly_task_prompt_v5.txt")
open(DST + "/nightly/README.md", "w").write("""# Nightly back-end run

One scheduled task (Anthropic scheduled task, ~11 pm Eastern) starts a fresh Claude session with `nightly_task_prompt_v5.txt`. In English the run is: log in to AMD once; work the four Claims Center columns (Charge Review, Claim Inspector, Unbilled, Exclusions) with the scripts in `billing/claims_center`; post or dismiss everything in ERA Center (`billing/era`); for every denial ask what coverage really was in the lookup order patient database -> AMD eligibility -> Stedi -> facesheet -> William (`eligibility/`); rebill as an original claim or write off by the practice rules in `practices/<code>/rules.md`; refresh the boards (`boards/`); run the credentialing check (`credentialing/`); on Sundays rescan payments; then write the chat digest to Drive.

A second loop polls Stedi Insurance Discovery every 30 minutes (`eligibility/disc_run.py --check`) and runs discovery over the held board cards the moment the enrollment goes live.
""")
os.makedirs(DST + "/practices/ehpa", exist_ok=True)
json.dump({"code": "ehpa", "name": "Effinger Health PA", "dba": "North Florida Senior Care", "group_npi": "1629515325", "tin": "81-4723941",
           "providers": {"1225327380": "William L. Effinger DO", "1235128869": "Pamela Garland-G ARNP"},
           "address": "1891 Capital Circle NE Suite 9, Tallahassee FL 32308-4486", "phone_fax": "888-698-2714",
           "amd": {"office_key": "152563", "api_user": "POI0712", "xml_gateway": "processrequest.aspx", "rest": "https://pm-api-103.advancedmd.com/api"},
           "stedi": {"enrolled_npi": "1629515325", "key": "secrets/stedi.key (never in git)"},
           "drive": {"project_files": "1-AsLUHMaeqvHq-fqWKUVKKUU4Xkw6XTt", "credentialing_files": "1kTkoNaetZVq6JLv5rNiEvN6r3eSAdkVA", "chat_history": "1VCZfjSmok1fNNnYwf2yBTXlZ-zMUnAWU",
                     "hca_facesheets": "1itL6N-3Xdu0QAtOA8BqtK9NeM3gb417W", "tmh_facesheets": "1uj5Sa9tmJHnV8VbMS42AjPAJtcpi-G2x", "pcc_facesheets": "1hEf4XJ6ppTH_UWva21JPW25g3uebKPAh", "claimocity_drop": "1XskJ8BJAC-YQRLRFBZ9lWuyEJiU1-htI"},
           "boards": {"insurance_refresh": "ae4bc5c4-1d6c-4ffc-bc78-3fc284ad262d", "credentialing": "5f3f4986-3553-4b70-b472-5f5757225d3a", "money_ledger": "2d2c85c6-903b-451a-ab53-bdc074703797", "billing_back_end_doc": "3dd11acd-e1b3-4298-9cb2-6b5601504630"}},
          open(DST + "/practices/ehpa/practice.json", "w"), indent=1)
for f in ("carriers.json", "facilities.json"): shutil.copy(SRC + "/" + f, DST + "/practices/ehpa/" + f)
open(DST + "/practices/ehpa/rules.md", "w").write("""# ehpa — Effinger Health PA: William's standing billing rules

- Medicare first, Medicaid / LTC second. Hospice patients: Medicare with modifier GV. A 9-digit AARP number is UHC Medicare Advantage (UNI20).
- PRIMARY claims more than 12 months from the date of service and unpaid are written off, any carrier — "no chance of it being resubmitted for actual payment" (9/7/2026).
- A SECONDARY / supplement balance is timely from the PRIMARY'S remit date, never the date of service — rebill it, never age it out (9/7/2026).
- Wrong-payer denials never stay on the patient balance. Medicaid crossover paying $0 on Medicare coinsurance = contractual write-off.
- UHC (UNI20) and Florida Blue (BCBS) visits older than 5/1/2026 are WORKED, no longer frozen (William 10/6/2026): first look for an answer already received (ERA / Availity / UHC portal export / a $0 posting) and post or work it; otherwise send ONCE (frequency 1, or 7 with the ICN when the payer already adjudicated) and add it to registers/tf_writeoff_watch.json; a timely-filing answer -> WOLATE write-off. Never send a claim older than 12 months to Medicare.
- Frequency 1 (original claim) before every rebill; frequency 7 only with the payer's ICN from William.
- No group numbers on any insurance plan. No SSNs anywhere.
- Address placeholder when a chart has no street address: line 1 = HCA (hospital), SNF (nursing home), ALF (ALF / home visit); zip 32308-4486; use the pop-up's Edit address.
- Insurance lookup order: patient database -> AMD eligibility (free 271) -> Stedi -> facesheet -> William. If AMD eligibility is down, skip to Stedi.
- Florida Medicaid's 271 names the SMMC plan; a patient in "SMMC MMA Capitated — FLORIDA COMMUNITY CARE" (FLO99) or Humana / Sunshine / Simply MMA is billed to that plan, not Medicaid fee-for-service.
- One AMD login attempt per run. Every call learned from a DevTools paste is written to docs/captured_calls.md the same night; not in the registry = not captured, ask instead of guessing.
- Protected health information travels only to William (SendUserFile, the boards, Gmail to himself) — never into this repository, a skill, or a public page.
""")
os.makedirs(DST + "/docs", exist_ok=True)
copy_clean(SRC + "/captured_calls.md", DST + "/docs/captured_calls.md"); copy_clean(SRC + "/postman_effinger_amd.json", DST + "/docs/postman_effinger_amd.json")
open(DST + "/docs/memory.md", "w").write("""# Where the project's memory lives

1. **This repository** — every script with its PLAIN ENGLISH header, the call registry (`docs/captured_calls.md`), the Postman mirror (`docs/postman_effinger_amd.json`), the nightly prompt, the board templates and each practice's non-secret configuration. Pushed as we go.
2. **The call registry** — `docs/captured_calls.md`: every AMD / Stedi call that has been captured from a DevTools paste or proven by probing, with its shape and the helper that wraps it. Regenerate the Postman collection whenever it changes.
3. **Postman** — William re-imports `docs/postman_effinger_amd.json` (token as `{{token}}`), his fallback for running the calls himself.
4. **Google Drive → aa claude folders → chat history** — one dated markdown digest per chat: decisions, rules given, calls captured, numbers, open items. Digests can name patients, so they stay in Drive, not here.
5. **The workspace** (`/home/claude/unbilled`) — scripts, logs, registers, `patient_db/` (eligibility answers per chart). Working data, never committed.
6. **Skills** in the Claude account — `advancedmd-api-reference`, `billing-easy-task…`, `billing-hard-task…`, the credentialing skill — the condensed operating rules Claude loads at the start of a run.
""")
env = "\n".join('export PYTHONPATH="$R/%s:$PYTHONPATH"' % c for c in CAT)
open(DST + "/env.sh", "w").write('# source env.sh from the repo root, then run any script from any folder\nR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"\n' + env + "\n")
# README
rows = {}
for n, cat in placed.items():
    t, d = what(header(os.path.join(SRC, n + ".py"))); rows.setdefault(cat, []).append((n, t, d[:220] + ("…" if len(d) > 220 else ""), n in local_only))
R = ["# Cloud Practice — Effinger Health PA (`ehpa`)", "",
     "One project for running a medical practice's back office with Claude: the **daily back-end billing run**, the **insurance cascade** (who really covers the patient), **credentialing**, the **Claimocity** hospital charge feed, and the three live boards (Insurance Refresh, Credentialing, Money Ledger). It grew out of cleaning up Effinger Health PA / North Florida Senior Care (Tallahassee, FL) on AdvancedMD, and is laid out so the same scripts can clean up another practice by adding a `practices/<code>/` folder.", "",
     "Every script starts with a PLAIN ENGLISH header — what it decides, which of William's rules it uses, what it never touches — and this README is generated from those headers. **No credentials and no patient data are in this repository**: tokens come from the login cache, the Stedi key from `secrets/`, logs / results / `patient_db/` stay in the workspace, and the %d scripts whose data tables hold member numbers are mirrored as header-only stubs (marked *local only* below)." % len(local_only), "",
     "## Layout", "", "| Folder | What lives there |", "|---|---|"]
R += ["| `%s/` | %s |" % (c, DESC[c]) for c in CAT] + ["| `nightly/` | The scheduled nightly run: the prompt the task starts from and, in English, what a run does. |", "| `practices/ehpa/` | Effinger Health PA: NPIs, office key, carrier and facility ids, Drive folder ids, board ids, and `rules.md` — William's standing billing rules. Add `practices/<code>/` for the next practice. |", "| `docs/` | `captured_calls.md` (the call registry), `postman_effinger_amd.json` (Postman mirror), `memory.md` (where everything is remembered). |", "",
      "Run anything with `source env.sh` from the repo root (it puts every folder on PYTHONPATH; the scripts import each other flat, exactly as they run in the workspace).", "", "## Scripts", ""]
for c in CAT:
    R += ["### `%s/`" % c, "", DESC[c], "", "| Script | What it is | What it decides |", "|---|---|---|"]
    R += ["| `%s.py`%s | %s | %s |" % (n, " *(local only)*" if lo else "", t.replace("|", "/"), d.replace("|", "/")) for n, t, d, lo in sorted(rows.get(c, []))]
    R.append("")
R += ["## History", "", "- 2026-09-07 — first mirror (104 scripts) as `effinger-billing-backend`.", "- 2026-09-08 — reorganized as the Cloud Practice project: folders by function, `practices/ehpa`, PHI-bearing scripts reduced to stubs, README generated from headers."]
open(DST + "/README.md", "w").write(depersonalize("\n".join(R)) + "\n")
open(DST + "/.gitignore", "w").write("*.log\n*.xlsx\n*.csv\n*.xml\n*.json\n!docs/postman_effinger_amd.json\n!practices/**/*.json\npatient_db/\nsecrets/\n.session.json\n.amd_cred.json\n__pycache__/\n*.tgz\n")
print("placed", len(placed), "local-only", local_only)
