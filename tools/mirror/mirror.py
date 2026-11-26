#!/usr/bin/env python3
# PLAIN ENGLISH (The triple mirror - GitHub, Postman, Drive - local half)
# Decides: Nothing about billing. Runs the file-side of the mirror that ends every billing run:
#   1. registry  - workspace captured_calls.md (+ any captured_calls_additions_*.md pulled from Drive)
#                  -> merged, PHI-gated -> docs/captured_calls.md
#   2. helpers   - every *.py / carriers.json / facilities.json in the workspace that is newer than
#                  the repo copy -> PHI-gated -> scripts/helpers/  (so a fresh container can restore);
#                  a stale Drive-overlaid copy of a protected helper (the PROTECTED table below) never overwrites the repo's
#   2a. feed registers (11/25/2026) - the Claimocity feed's registers in the workspace -> practices/ehpa/registers/. The batch registers
#                  (feed_import / feed_newcharts / feed_verify / feed_inspector / feed_fixholds / feed_recon and the order sweep's
#                  feed_order_sweep / _coverage / _resave / _fixclin) are copied - one main already has only by a FULLER copy (more
#                  rows), never by a shorter one, whatever the file times say, and not while the ingest of their stamp is still
#                  running (the step reads this machine's process list for that, nothing else). The standing files are MERGED with
#                  main's: the file register claimocity_ingest.json, the patient map (main's chart stays where the two disagree), the
#                  diagnosis cache (from the workspace ROOT, where the feed helpers keep it; main's id stays where the two hold
#                  different ids for a code), the insurance-intake register feed_in1_intake.json and, when a run wrote it,
#                  feed_dx_needed.json.
#                  Until then a run had to copy them by hand (feed runbook step e); three runs did not, and the next run read the
#                  same feed file again. `sync` scrubs them in place with the tree gate like every other register; `feed-registers`
#                  (this step alone, for a run that commits by hand) runs the tree gate over the registers folder itself before it
#                  returns, and exits non-zero when the gate fails - or when a standing file on main is no longer a JSON object
#                  (conflict markers): the run's own commit of that folder must not follow then.
#   2b. tree gate - phi_gate.py tree . before `git add -A`: registers / run artifacts scrubbed in place,
#                  digests / needs lists / run reports kept out (Drive only)  (10/6/2026)
#   3. postman   - docs/api_vocabulary.json -> docs/postman_effinger_amd.json (generated)
#   4. git       - commit, push main AND the project's synced branch: with the PAT when secrets/github_pat.key
#                  exists, otherwise through the session proxy (11/2/2026 - a cloud session with the repository
#                  attached needs no PAT: fetch + merge origin/main, push main, push the synced branch); only when
#                  the proxy says 403 ("not in this session's authorized repository set") leave HEAD on its own
#                  branch upstream and write a PACKAGE to /home/claude/unbilled/outbox/ - never retry the push.
#   The Drive and Postman legs are done by the run itself with the connectors (see docs/MIRROR.md):
#   this script prints exactly which files to upload and to which Drive folder.
# Rules it uses: no PHI on GitHub (phi_gate on every file that crosses); Drive is the PHI-OK copy;
#   the vocabulary is the source of the Postman collection; one commit per run, dated message.
# Never touches: AMD, Stedi, Drive, Postman. Only files and git (step 2a also reads, and only reads, the list of running processes).
# ---
import os, re, sys, glob, json, shutil, subprocess, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WS = os.environ.get("BILLING_WORKSPACE", "/home/claude/unbilled")
GATE = os.path.join(ROOT, "tools", "mirror", "phi_gate.py")
PMB = os.path.join(ROOT, "tools", "mirror", "postman_build.py")
REPO = "dreffinger/effinger-billing-backend"
BRANCHES = ["main", "claude/effinger-billing-backend-mirror-w74pqv"]   # main = record; 2nd = project's synced source
DRIVE = {"project files": "1-AsLUHMaeqvHq-fqWKUVKKUU4Xkw6XTt", "workspace mirror": "135OCbRNCnFLyVm2GBXk1XsE3lt0vnsrn",
         "github mirror": "1yr8X30h01-tPa0swclvtBFdAisiHzgJ8", "chat history": "1VCZfjSmok1fNNnYwf2yBTXlZ-zMUnAWU"}
TODAY = datetime.date.today().isoformat()

def sh(cmd, check=True, **kw):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=ROOT, **kw)
    if check and r.returncode:
        raise SystemExit("FAILED: %s\n%s%s" % (cmd, r.stdout, r.stderr))
    return r

def gate(src, dst):
    r = subprocess.run([sys.executable, GATE, src, dst], capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    if r.returncode:
        sys.stdout.write(r.stderr)
        raise SystemExit("phi_gate BLOCKED %s - fix the source (or add the name to secrets/pseudonyms.json) and rerun" % src)

# ---- 1. registry ---------------------------------------------------------------------------------
def merge_registry():
    base = os.path.join(WS, "captured_calls.md")
    if not os.path.exists(base):
        print("registry: no %s in the workspace - download it from Drive 'billing agent project files' first" % base)
        return False
    text = open(base).read()
    adds = sorted(glob.glob(os.path.join(WS, "captured_calls_additions_*.md")))
    merged = 0
    for a in adds:
        body = open(a).read().strip()
        if body and body[:200] not in text:
            text = text.rstrip() + "\n\n" + body + "\n"
            merged += 1
    if merged:
        open(base, "w").write(text)
        print("registry: merged %d additions file(s) into workspace captured_calls.md" % merged)
    dst = os.path.join(ROOT, "docs", "captured_calls.md")
    prior = open(dst).read() if os.path.exists(dst) else ""
    gate(base, dst)
    union_prior_record(dst, prior)
    return True

def _sections(text):
    """Split a registry into (header_line, body) blocks; header = any line starting with '#'."""
    out, cur, buf = [], None, []
    for line in text.splitlines():
        if line.startswith("#"):
            if cur is not None or buf:
                out.append((cur, "\n".join(buf)))
            cur, buf = line.strip(), [line]
        else:
            buf.append(line)
    if cur is not None or buf:
        out.append((cur, "\n".join(buf)))
    return out

def union_prior_record(dst, prior):
    """The gate re-derives docs/captured_calls.md from the workspace base, which may be an OLDER Drive copy
    than the repo record. Keep every prior-record section whose header is missing from the new copy
    (appended in their original order) so the record only ever grows. Lesson from the 9/12 runs."""
    if not prior.strip():
        return
    new = open(dst).read()
    have = {h for h, _ in _sections(new) if h}
    missing = [(h, b) for h, b in _sections(prior) if h and h not in have and b.strip()]
    if not missing:
        return
    text = new.rstrip() + "\n\n" + "\n\n".join(b.rstrip() for _, b in missing) + "\n"
    open(dst, "w").write(text)
    print("registry: union kept %d prior-record section(s) the Drive base did not carry" % len(missing))

# ---- 2. helpers ---------------------------------------------------------------------------------
HELPER_GLOBS = ["*.py", "*.sh", "carriers.json", "facilities.json"]
SKIP = {"vocab_seed.json"}
# 10/6/2026: the repository is the record for these seven. A workspace copy overlaid from Drive carries a fresh
# mtime but can be OLDER code (the pre-10/6 move_to_ins ignores --no-rebill; the old freq1_visit has no reroute);
# a copy that lacks its marker never overwrites scripts/helpers/, whatever its mtime says.
PROTECTED = {"amd.py": "_REBILLED", "resave.py": "set_insorder never sends a save when the visit's charges could not all be read", "freq1_visit.py": "def reroute",
             "move_to_ins.py": "--no-rebill", "ins_update.py": "_set_order", "dx_primary_fix.py": "--visits",
             "approval_submit.py": "LASTFIRST", "payreasons.py": "10/6: no patient name", "columns_scan.py": "NAMEKEY",
             # 11/10/2026: the feed import carries William's place-of-service rule (CCM in a nursing building = 32, visits by frequency);
             # a workspace copy from before the rule - or of an earlier version of it - must never go back on main. The marker is the
             # helper's own POS_RULE_VERSION line: when the rule is revised, change it here, in the helper, in claimocity_ingest.py and in
             # nightly/claimocity_feed_step.md step (c) together (tools/selftest/test_pos_rule.py checks that the four agree)
             # 11/25/2026 (rule version 2026-11-25.1, William: every CCM line is 32, never the skilled-nursing 31): a copy of the 11/10 version
             # still keeps a CCM line at 31 in a 'skilled-looking month' - it must not come back over the new one
             # 11/25/2026 (.2): the independent review of the I10 rule changed the import (what it says of a code past the twelfth place) and the report
             # (the diagnosis lines of the digest) - a copy from before those fixes must not come back either
             # 11/25/2026 (.3 - William the same day: inpatient rehab goes out at place of service 61; a feed patient with a wrong birth date goes to the chart he already has): the
             # import enters a rehab stay at HCA REHAB / 61, notes the feed's birth date against the chart's and asks for a message's chart by its own Claimocity id; the report says
             # all three - a copy from before must not come back over either
             "claimocity_import.py": 'POS_RULE_VERSION = "2026-11-25.5"', "claimocity_report.py": 'POS_REPORT_VERSION = "2026-11-25.5"',
             # the driver carries the guard for the same version line; the retry and inspector helpers each a sentence only their current version has
             "claimocity_ingest.py": 'POS_RULE_VERSION = "2026-11-25.5"', "claimocity_retry_dx.py": 'POS_RULE_VERSION = "2026-11-25.5"',
             # 11/10/2026 (quality code 1123F, version 2): the inspector step and the insurance check take the no-charge line off a held visit by
             # themselves (William's decision) - a copy from before that must not come back over them; the marker is a sentence only that version has.
             # Since the option code M0004 (the same day, step 3 of the change) the sentence is one only the version that knows the M0004 line has.
             # 11/10/2026 (round 7): the insurance check and resave.py read each visit's insurance-order LIST - a copy from before that skipped the visits
             # entered with no plan (84 never billed) and must not come back over them; their markers are sentences only the round-7 versions have
             # (resave.py above). feed_order_sweep.py is new that day: the daily listing and the owner-approved save
             # 11/12/2026 (rule version 2026-11-10.8, the quality code never switches itself off): the inspector step tries a visit stuck with its no-charge line again in
             # every run - a copy from before that leaves such a visit held for ever now that nothing switches the code off; its marker is the sentence only that version has
             # 11/25/2026 (William: a 99223 after follow-up hospital visits is a new admission - "that block is no longer valid"): the inspector step bypasses Pattern 692;
             # a copy from before holds such a visit and puts it on his turn again - its marker is now a sentence only the version with that rule has (it still carries the retry pass)
             # 11/25/2026 (William: the rehab unit's visits go out at 61 and are watched): the inspector step no longer moves any visit (it moved nursing-coded visits under the hospital
             # building to HCA REHAB at 31 - his word of 10/31: wrong) and never bypasses a place-of-service edit on a visit entered at 61; a copy from before moves visits again - its
             # marker is now a sentence only that version has (it still carries the Pattern 692 rule and the retry pass). The insurance check asks its paid look-up with the CHART's own
             # name and birth date (a feed patient with a wrong birth date): a copy from before asks with Claimocity's - its marker is now that sentence (it still carries the list rule)
             "claimocity_inspector.py": "A VISIT THE IMPORT ENTERED AT PLACE OF SERVICE 61 IS NEVER MOVED AND ITS PLACE-OF-SERVICE EDITS ARE NEVER BYPASSED BY THIS STEP", "claimocity_verify.py": "A NAME THAT IS ALIKE BUT NOT THE SAME IS HELD LIKE ANY OTHER NAME",
             # the same word for the insurance intake of existing charts, and the three steps of the identity rule with the rule itself (feed_identity.py): they only work together -
             # the resolve step refuses a match file of another version - and a copy of the match or new-chart step from before the rule makes the second charts again
             "feed_in1_intake.py": "THE SAME NAME IS THE SAME FIRST WORD AND NO OTHER SUFFIX",
             "claimocity_match.py": "THE MATCH STEP ONLY GATHERS: EVERY ENTRY IT WRITES IS UNDECIDED UNTIL claimocity_resolve.py APPLIES THE IDENTITY RULE",
             "claimocity_resolve.py": "NOR DOES A PATIENT WHOSE OWN CHART IS A SLIP AWAY",
             "claimocity_newcharts.py": "A NEW CHART IS MADE ONLY ON RULE 9 OF THE IDENTITY RULE, ONE PER CLAIMOCITY ID, NEVER WITH AN EMPTY BIRTH DATE",
             "feed_identity.py": 'IDENTITY_RULE_VERSION = "2026-11-26.5"',
             # the payment monitor of the rehab visits at 61 (new 11/25/2026): its own version line, changed with every revision
             "pos61_monitor.py": 'POS61_MONITOR_VERSION = "2026-11-25.4"',
             "insp_bypass_advisories.py": "692 added 11/25/2026 (a new admission - the header)",      # the advisory sweep of the same rule: a copy without 692 in its list never comes back over it
             # 11/11/2026 (round 8, the echo guard): resave.py's order save and feed_order_sweep.py never send a save when AdvancedMD did not return
             # all of a visit's charges. A copy from before sends a short or EMPTY list of charges after a failed history read, and a charge left out
             # of a full-visit save is voided: such a copy must not come back over them. Their markers (resave.py's above, the sweep's here) are now
             # sentences only the round-8 versions have - a round-7 copy is refused too; the insurance check keeps its round-7 sentence
             # 11/25/2026: the sweep sets a hospital visit's admission date by the standing rule and no longer keeps it for William ('two admission dates in one stay'); a copy from
             # before holds those visits again - its marker is now a sentence only that version has (it still carries the round-8 guard)
             "feed_order_sweep.py": "THE ADMISSION DATE IS SET BY THE STANDING RULE, NOT HELD FOR WILLIAM",
             # the denial table exists twice (boards/ and here); the workspace copy the bootstrap lays out first is this one - an older
             # workspace copy without the reporting-line rule (1123F / 1124F / M0004 always INFO, 11/10/2026) or Medicare's reason-58 rule must not come back over it
             "working_denials.py": 'REPORTING_CODES = {"1123F", "1124F", "M0004"}',
             # the AR ageing page: a reporting line never makes a visit read as denied (11/10/2026)
             "aging_refresh.py": 'INFO_REASONS = ("45", "253", "23", "94", "1", "2", "3", "246")',
             # the one function the ingest and the retry share to make the feed helpers the repository's on every run (11/10/2026, reviewers C2 / W1)
             # (11/25/2026: this sentence also stands in the copy from before that day's change - PROTECTED_ALSO below asks for a second one)
             "claimocity_helpers_current.py": "compared byte for byte with the clone's copy",
             # 11/25/2026 (the verification of the feed part): the parser and the download step had NO marker. The parser of that day survives a broken message and
             # counts every message that cannot be entered; the download step fetches a registered file again when the bucket's copy has another size. An older
             # workspace copy of either went back over the repository's - the markers are sentences only those versions have
             "feed_parse_dft_1028.py": "EVERY MESSAGE THAT CANNOT BE ENTERED AS IT CAME IS COUNTED BY FILE DATE AND MESSAGE NUMBER", "claimocity_gcs.py": "A REGISTERED FILE WHOSE COPY IN THE BUCKET HAS ANOTHER SIZE IS FETCHED AGAIN",
             # 11/25/2026 (independent review of the I10 rule): the diagnosis cache step never caches a fault as 'not in the list' and always resolves I10; the
             # reconciliation never hands the row of a message without a charge line to another message. A workspace copy from before that must not come back
             # over them - the markers are a sentence and a line only the fixed versions have
             "claimocity_dx.py": "no lookup answer in two tries", "claimocity_recon.py": "THE CHART OF A MESSAGE IS ITS OWN CLAIMOCITY ID'S",
             # 11/10/2026 look-ups part A: the copies from before ONE Medicare answer / claim status by need must never go back on main
             "stedi.py": "def medicare(", "precheck.py": "max_age_days=_month_age(dos)",
             # 11/25/2026 (William: "is stedi able to do that for free?"): the guard asks AdvancedMD's free eligibility check before it buys a vendor answer, and finds the
             # workspace's own cache; a workspace copy from before buys an answer for every check and can start with an empty cache - it must not come back over the new
             # one. The marker is the COUNTS line only the new guard has (until that day: "stedi.medicare(", which the old guard holds too).
             # 11/25/2026 (the rounds after the independent checks of the date-of-death work): the guard's marker is a line only the guard of those rounds has (it
             # keeps a death for good, reads a day in every shape, raises DayLost) - the line of before also stood in older guards; the Drive copy helper keeps the
             # earlier of two days and never lets a 'no death' note replace a death on record; the modifier-25 helper leaves the 99489 add-on alone for Humana
             "dg_drive.py": 'DG_DRIVE_RULE = "2026-11-26.1"', "mod25_addon.py": "NO MODIFIER 25 - HUMANA",
             "deceased_guard.py": 'DEATH_GUARD_RULE = "2026-11-26.1"', "death_check_review.py": 'DEATH_CHECK_REVIEW_VERSION = "2026-11-25.7"',
             "claimocity_void_deceased.py": "THE DAYS IT GOES BY ARE THE GUARD'S ONE CACHE, READ THROUGH THE GUARD - NEVER A CACHE FILE OF THE FEED'S OWN",
             "claim_status_sweep.py": "cs_rules.Ledger.open(", "claim_status_exact.py": "claim_status_sweep.run(",
             "sweep_full.py": "claim_status_sweep.main(",
             # 11/25/2026 (William: the board showed 0 on his turn while the evening email listed 18 charts): the one source of the
             # 'current face sheets needed' email and the board rules it is worked out with. A workspace copy of an earlier version must
             # never go back on main - the markers are the helpers' own version lines (tools/selftest/test_facesheets_needed.py checks
             # that they agree with this table; when a rule changes, change the line in the helper and here together, and in
             # boards/templates/tracker.html when it is a board rule)
             "facesheets_needed.py": 'FACESHEETS_NEEDED_VERSION = "2026-11-25.1"', "board_apply.py": 'BOARD_APPLY_VERSION = "2026-11-25.1"'}
# 11/25/2026 (the verification): a SECOND sentence a workspace copy must carry as well, for a helper whose marker above also stands in an older copy.
# The shared helper list grew that day from 8 to 17 helpers (the identity rule's steps travel with the others) and its marker stayed the same: an
# older copy with a fresher file time went back over the repository's, and nothing made the identity rule's helpers current in a workspace any more.
PROTECTED_ALSO = {"claimocity_helpers_current.py": "SINCE 11/25/2026 THE PARSER CARRIES A SENTENCE OF ITS OWN TOO",
                  "feed_order_sweep.py": "DEATH_UNCHECKED = "}      # the sweep that refuses ONE visit when the date of death could not be checked and goes on (a copy from before stops at that chart)
def sync_helpers():
    dst_dir = os.path.join(ROOT, "scripts", "helpers")
    os.makedirs(dst_dir, exist_ok=True)
    n = 0
    for g in HELPER_GLOBS:
        for src in glob.glob(os.path.join(WS, g)):
            name = os.path.basename(src)
            if name in SKIP or name.startswith("."):
                continue
            dst = os.path.join(dst_dir, name)
            if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
                continue
            markers = [m for m in (PROTECTED.get(name), PROTECTED_ALSO.get(name)) if m]
            if markers and os.path.exists(dst):
                text = open(src, errors="replace").read(); marker = next((m for m in markers if m not in text), None)
                if marker:
                    print("helpers: STALE workspace copy of %s skipped (no '%s' - the repo copy is newer code); copy the repo's back over the workspace" % (name, marker))
                    continue
            gate(src, dst); n += 1
    print("helpers: %d file(s) refreshed into scripts/helpers/" % n)

# ---- 2a. the Claimocity feed's registers (11/25/2026) ---------------------------------------------
# The feed's registers are written in the run's throw-away workspace. Until 11/25/2026 they reached main only when the run copied them by
# hand (nightly/claimocity_feed_step.md step e - prose). On 11/10, 11/21 and 11/24/2026 the morning run entered 60 / 84 / 26 visits in
# AdvancedMD and committed no feed register: the next fresh container took main's older file register, saw the same feed file as new and
# read it again (no visit was entered twice - the import checks the chart's live charges - but the batch records of 11/21 and 11/24 exist
# nowhere, and the feed page shows $0 for those files). Now every `sync` carries them. The rules below are the first version's as an
# independent review corrected them the same day, 11/25/2026 (each says what the review found):
#   - a batch register main does not have is copied. One BOTH sides have and that differs is decided by CONTENT, never by file time: the
#     copy with MORE rows is the one main gets (feed_import: created + skipped + failed; feed_recon: rows; any other family: the total of
#     its top-level lists - or its entries when it is keyed by chart and has no list at all, as feed_verify is; a document that is a list:
#     its length); with equal rows main's stays, because the tree gate may have scrubbed it. (Review: the first rule was "the newer file
#     wins". After a clone every file of main is newer than every restored one, so a short copy on main - a batch that was still being
#     entered when a run mirrored - could never be replaced by the full restored one, and main kept the short register for good.)
#   - the batch registers of a stamp whose ingest is STILL RUNNING are not carried this time: they are half written, and what the ingest
#     writes after this mirror would not follow them. The line says so for the top of the report; a later mirror of a workspace that
#     still holds them carries them - in a fresh container that is only what the state bundle brought along.
#   - the standing files are MERGED, so nothing either side knows is lost:
#       the file register (every file and run; for a file both know with the same content the EARLIEST registration stays - the run that
#         really entered its visits);
#       the patient map (a patient only the workspace knows is added; where the two disagree MAIN's chart stays and the line names the
#         feed patient, so that a person decides. Review: "the workspace answers" let a days-old restored map undo a correction made on
#         main, in every sync, also by a run that never ran the feed - and the ingest takes a known patient from the map as it is, so the
#         workspace's chart is never this run's fresher knowledge);
#       the diagnosis cache (a code main lacks is added; an id takes the place of main's "not in AdvancedMD", never the other way round;
#         where BOTH hold an id and the two differ MAIN's id stays and the line names the code, so that a person decides - the patient
#         map's rule), read from the workspace ROOT, where every feed helper keeps it (claimocity_ingest.py and claimocity_dx.py:
#         dx_cache_feed.json beside the helpers). The copy in the workspace's registers/ is only the bootstrap's snapshot of main and is
#         used only when the root file is missing. (Review: the first version merged that snapshot - main with an older copy of itself -
#         so no code a run learned ever reached main. The verification of the corrected step, the same day: with the root cache as the
#         source, "the workspace's id answers" was at work in every sync - a days-old cache restored from the state bundle wrote an old
#         id back over one corrected on main, without a word, also in a run that never ran the feed. claimocity_dx.py looks a code up
#         only while the cache holds no id for it, so the workspace's id is not this run's fresher knowledge.);
#       the insurance-intake register feed_in1_intake.json and, when a run wrote it, feed_dx_needed.json - entry by entry, see
#         _merge_intake and _merge_dx_needed. (Review: the intake register and the order sweep's coverage / resave / fixclin registers
#         hold state - a Medicaid check or a dated check is bought again, a visit saved again, when a fresh workspace lacks them - and the
#         first version left them to the runbook's prose.)
#       the register of the place-of-service-61 monitor pos61_monitor.json (11/25/2026) - never mixed: the LATER run's stays, whole
#         (_merge_pos61). It is the monitor's memory and the words the digest prints about the rehab visits.
#   - feed_identity_<stamp>.json (11/25/2026: which chart each new feed patient went to and by which rule - chart ids, rule numbers and
#     fixed words only; claimocity_ingest.py writes it from the match file, which itself never leaves the workspace) is a batch register
#     like the others.
# Never taken from the workspace: files whose home is main (feed_order_approved.json - the owner's word -, quality_exceptions.json and, since
# 11/25/2026, feed_same_person.json - William's standing word that a chart is a feed patient; the ingest copies main's file into the workspace).
# feed_same_person.json is written by hand in the clone, so the guard below looks at it like at a merged standing file (FEED_HOME_CHECKED): a half-written
# edit or the conflict markers of a pull never ride into a commit (11/25/2026, the verification - `sync` committed such a file like any other change).
# Nothing is deleted. A file that cannot be read is named and skipped - this step never stops the mirror: it never raises. (Only the
# subcommand `feed-registers` ends non-zero, AFTER the step, while a standing file on main is no longer JSON - feed_standing_unreadable.)
# The sweep's stamp carries seconds and, when two runs start in one second, "_2", "_3" ... behind it (feed_order_sweep.py).
FEED_BATCH = re.compile(r"^(feed_(import|newcharts|verify|inspector|fixholds|recon|identity|unreadable)_\d{8}T\d{4}ZR?|feed_order_(sweep|coverage|resave|fixclin)_\d{8}T\d{4,6}Z(_\d+)?)\.json$")
FEED_MERGED = ("claimocity_ingest.json", "claimocity_patient_map.json", "dx_cache_feed.json", "feed_in1_intake.json", "feed_dx_needed.json", "pos61_monitor.json")
FEED_HOME_CHECKED = ("feed_same_person.json", "feed_duplicate_charts.json")      # home is main and never merged from a workspace - but checked for being a JSON object before any commit (the second one: the charts William called duplicates, 11/25/2026 - claimocity_match.py never offers such a chart)
def _merge_ingest(main, ws):
    out = dict(main); files = dict(main.get("files") or {})
    for k, v in (ws.get("files") or {}).items():
        cur = files.get(k)
        if not isinstance(v, dict): continue
        if not isinstance(cur, dict): files[k] = v
        elif cur.get("sha256") != v.get("sha256"):                       # another content under the same name: the later registration answers
            if str(v.get("at") or "") > str(cur.get("at") or ""): files[k] = v
        elif str(v.get("at") or "~") < str(cur.get("at") or "~"): files[k] = v      # the same content: the first registration is the run that entered it
    runs = []; seen = set()
    for r in list(main.get("runs") or []) + list(ws.get("runs") or []):
        key = json.dumps(r, sort_keys=True)
        if key not in seen: seen.add(key); runs.append(r)
    runs.sort(key=lambda r: (str(r.get("at") or ""), str(r.get("stamp") or "")) if isinstance(r, dict) else ("", ""))
    for k, v in ws.items():
        if k not in out: out[k] = v
    out["files"] = files; out["runs"] = runs
    return out
def _merge_map(main, ws):
    out = dict(ws); out.update(main); return out                         # main's chart stays where the two disagree; a patient only the workspace knows is added
def _merge_dx(main, ws):
    out = dict(main)
    for k, v in ws.items():
        if k not in out or (v and not out[k]): out[k] = v                # a code main lacks is added; an id replaces main's "not in AdvancedMD" (null), never the other way round; where BOTH hold an id MAIN's stays (11/25/2026 - the step's line names the code)
    return out
def _stamp_key(s):
    """A stamp in any form the helpers write (20261122T1240Z, 2026-11-22T1240Z, 2026-11-22T12:55:00Z, a plain date) as a text that sorts by
    time: its digits, filled up to seconds. "" = no stamp - an empty text, a placeholder, a value of another kind."""
    d = re.sub(r"\D", "", s) if isinstance(s, str) else ""
    return d.ljust(14, "0") if len(d) >= 8 else ""
def _merge_intake(main, ws):
    """feed_in1_intake.json - {"<chart>|<carrier>": {outcome, stamp of the run, ins}}: one entry per chart and carrier, written by the ONE run
    that settled it (feed_in1_intake.py never asks again about a key it holds). Every key either side has stays. For a key both have the
    entry of the NEWER stamp stays, whole: an entry is one run's finding, and a mix of two entries would record an outcome no run saw. The
    same stamp on both sides is the same run's entry - main's stays (the tree gate may have scrubbed it, and a second mirror then changes
    nothing). No stamp on either side: nothing says which is newer, and the workspace's - this run's - stays. (11/25/2026)"""
    out = dict(main)
    for k, v in ws.items():
        if k not in out: out[k] = v; continue
        a = _stamp_key(v.get("stamp")) if isinstance(v, dict) else ""; b = _stamp_key(out[k].get("stamp")) if isinstance(out[k], dict) else ""
        if a > b or not (a or b): out[k] = v
    return out
def _merge_dx_needed(main, ws):
    """feed_dx_needed.json - {code: {first, last: the stamps of the first and of the latest batch that carried the code, visits: how many
    visits, emailed: the stamp of the email that named it, or ""}}. A code only one side knows stays as it is. For a code both know:
    first = the EARLIER stamp that is set, last = the LATER, visits = the LARGER, emailed = the LATER one that is set - so the first
    sighting is never lost and a code already written about is never taken for a new one. Any other field: main's, else the workspace's.
    A value that is no stamp (an empty text, a placeholder) counts as not set. A field whose name only BEGINS with first / last / emailed
    (first_seen, last_seen ...) follows the same rule: under the two bare names the privacy gate takes a stamp that holds a letter for a
    name part and writes its placeholder over it on main, so the helper that writes this register may have to name them otherwise. (11/25/2026)"""
    out = dict(main)
    for code, w in ws.items():
        m = out.get(code)
        if not (isinstance(m, dict) and isinstance(w, dict)):
            if code not in out or (isinstance(w, dict) and not isinstance(m, dict)): out[code] = w      # an entry beats what is no entry; otherwise main's stays
            continue
        e = dict(w); e.update(m)
        for k in e:
            both = (m.get(k), w.get(k))
            if k == "visits":
                counts = [x for x in both if isinstance(x, int) and not isinstance(x, bool)]
                if counts: e[k] = max(counts)
            elif isinstance(k, str) and k.startswith(("first", "last", "emailed")):
                given = [x for x in both if _stamp_key(x)]
                if given: e[k] = (min if k.startswith("first") else max)(given, key=_stamp_key)        # on a tie the first of the two: main's
        out[code] = e
    return out
def _merge_pos61(main, ws):
    """pos61_monitor.json - the register of ONE run of pos61_monitor.py (William 11/25/2026: the rehab visits at place of service 61 are
    watched until they are paid): the lines the digest prints, the counts, and the monitor's memory of every rehab visit it has read. It
    is one run's finding and is never mixed: the register of the LATER run (its "at") stays, whole - also when it holds fewer visits (a
    voided visit leaves the list). The same time on both sides is the same run's register - main's stays (the tree gate may have scrubbed
    it). No time on either side: nothing says which is later, and the workspace's - this run's - stays. Main holds none yet: the workspace's."""
    if not main: return ws
    a = _stamp_key(ws.get("at")); b = _stamp_key(main.get("at"))
    return ws if (a > b or not (a or b)) else main
# every merged file is written the way its helper writes it, so that a diff on main shows only the entries that changed
# (feed_dx_needed.json has no writer in the repository yet: one field a line, keys in order)
_FEED_MERGE = {"claimocity_ingest.json": (_merge_ingest, {"indent": 1}), "claimocity_patient_map.json": (_merge_map, {"indent": 0, "sort_keys": True}),
               "dx_cache_feed.json": (_merge_dx, {"indent": 0, "sort_keys": True}), "feed_in1_intake.json": (_merge_intake, {"indent": 1}),
               "feed_dx_needed.json": (_merge_dx_needed, {"indent": 1, "sort_keys": True}), "pos61_monitor.json": (_merge_pos61, {"indent": 1})}
def _feed_rows(name, doc):
    """How many rows a batch register holds - what "fuller" means when both sides have one (the rules above, 11/25/2026)."""
    if isinstance(doc, list): return len(doc)
    if not isinstance(doc, dict): return 0
    only = ("created", "skipped", "failed") if name.startswith("feed_import_") else ("rows",) if name.startswith("feed_recon_") else None
    lists = {k: v for k, v in doc.items() if isinstance(v, list)}
    if only is None and not lists: return len(doc)                       # keyed by chart, no list at all (feed_verify): its entries are its rows
    return sum(len(v) for k, v in lists.items() if only is None or k in only)
def _running_ingest_stamps():
    """The stamp of every claimocity_ingest.py that is running on this machine right now ("" for one started without --stamp), read from
    /proc/<pid>/cmdline - no outside command. The stamp is made the way the ingest makes it: digits, T and Z only. (11/25/2026, review:
    the runbook lets a run go on while its ingest still writes; the register carried then was a short one that stayed on main.)
    Only a Python process whose SCRIPT is the helper counts - not one that merely names it in an argument (a tail of its log, a grep, a
    commit message, a prompt text): a false 'still running' would hold registers back for nothing. The self-test replaces this function."""
    out = []
    try: pids = [p for p in os.listdir("/proc") if p.isdigit() and int(p) != os.getpid()]
    except OSError: return out                                           # no /proc on this machine: nothing can be seen
    for p in pids:
        try: argv = [x.decode("utf-8", "replace") for x in open("/proc/%s/cmdline" % p, "rb").read().split(b"\0") if x]
        except OSError: continue                                         # it ended meanwhile, or is not ours to read
        if not argv or not os.path.basename(argv[0]).startswith("python"): continue
        rest = argv[1:]
        while rest and rest[0].startswith("-"): rest = rest[1:]          # the interpreter's own switches (-u, -I)
        if not rest or os.path.basename(rest[0]) != "claimocity_ingest.py": continue
        args = rest[1:]; i = args.index("--stamp") if "--stamp" in args else -1
        out.append(re.sub(r"[^0-9TZ]", "", args[i + 1]) if 0 <= i < len(args) - 1 else "")
    return out
def sync_feed_registers():
    """Copy / merge the feed's registers from the workspace into practices/ehpa/registers/. Returns the number of files written. Prints ONE
    line that starts "feed registers: N file(s) carried into practices/ehpa/registers/" (the runbook, the prompts and the lessons quote that
    start); whatever a person has to see is said behind it, and the line then ends "TOP OF THE REPORT". Never raises.
    The feed runbook's step (e) quotes each of those wordings and says what a run does about it (11/25/2026: until then no text told a run
    to act on the ending, and the line could be printed without ever reaching William) - a wording changed here is changed there too;
    the self-test's last section holds the two together."""
    src_dir = os.path.join(WS, "registers"); dst_dir = os.path.join(ROOT, "practices", "ehpa", "registers"); live_dx = os.path.join(WS, "dx_cache_feed.json")
    if not os.path.isdir(src_dir) and not os.path.lexists(live_dx):
        print("feed registers: no %s in the workspace - nothing to carry" % src_dir); return 0
    copied = merged = 0; bad = []; fuller = []; differ = []; dxdiff = []; held = {}; running = []; notes = []
    try:
        os.makedirs(dst_dir, exist_ok=True)
        items = {name: os.path.join(src_dir, name) for name in os.listdir(src_dir)} if os.path.isdir(src_dir) else {}
        if os.path.lexists(live_dx): items["dx_cache_feed.json"] = live_dx       # the LIVE cache; the snapshot in registers/ only when there is none at the root
        try: running = sorted({s for s in (_running_ingest_stamps() or []) if isinstance(s, str)})
        except Exception as e: notes.append("the look for a running ingest failed (%s), so no register was held back" % type(e).__name__)
        for name in sorted(items):
            src = items[name]; dst = os.path.join(dst_dir, name)
            try:
                if FEED_BATCH.match(name):
                    if not os.path.isfile(src): continue
                    st = next((s for s in running if s and name.endswith("_%s.json" % s)), None)
                    if st: held[st] = held.get(st, 0) + 1; continue      # its ingest is still writing it
                    raw = open(src, "rb").read()
                    if os.path.lexists(dst):
                        cur = open(dst, "rb").read()
                        if cur == raw: continue
                        try: main_rows = _feed_rows(name, json.loads(cur.decode("utf-8")))
                        except Exception: main_rows = -1                  # main's copy cannot be read: any copy that can is the fuller one
                        try: ws_rows = _feed_rows(name, json.loads(raw.decode("utf-8")))
                        except Exception:
                            if main_rows >= 0: continue                   # the workspace copy cannot be read and main holds one that can: nothing to carry, nothing to say
                            raise
                        if ws_rows <= main_rows: continue                 # never a shorter copy over a fuller one; equal rows: main's stays
                        fuller.append("%s (%s -> %d rows)" % (name, main_rows if main_rows >= 0 else "unreadable", ws_rows))
                    else: json.loads(raw.decode("utf-8"))                 # a half-written register never goes to main
                    with open(dst, "wb") as fh: fh.write(raw)             # the bytes that were just read and checked - not a second read of a file a background helper (the sweep) may be writing
                    copied += 1
                elif name in _FEED_MERGE:
                    if not os.path.isfile(src): raise ValueError("not a file")
                    fn, fmt = _FEED_MERGE[name]
                    ws_obj = json.loads(open(src, "rb").read().decode("utf-8"))
                    if not isinstance(ws_obj, dict): raise ValueError("not a JSON object")
                    cur = open(dst, "rb").read().decode("utf-8") if os.path.lexists(dst) else ""
                    main_obj = json.loads(cur) if cur.strip() else {}     # an EMPTY file on main knows nothing; a broken one is named and left for a person
                    base = main_obj if isinstance(main_obj, dict) else {}
                    new = fn(base, ws_obj)
                    if name == "claimocity_patient_map.json":
                        differ = ["%s (main %s, workspace %s)" % (k, str(base[k])[:24], str(ws_obj[k])[:24]) for k in sorted(ws_obj) if k in base and base[k] != ws_obj[k]]
                    if name == "dx_cache_feed.json":                      # a code BOTH hold under two different ids: main's stayed (_merge_dx) - the line names it for a person
                        dxdiff = ["%s (main %s, workspace %s)" % (k, str(base[k])[:24], str(ws_obj[k])[:24]) for k in sorted(ws_obj) if base.get(k) and ws_obj[k] and base[k] != ws_obj[k]]
                    if new != main_obj:
                        text = json.dumps(new, **fmt)                     # made into text BEFORE the file is opened: a value that cannot be written leaves main's copy whole
                        with open(dst, "w", encoding="utf-8") as fh: fh.write(text)
                        merged += 1
            except Exception as e:
                bad.append("%s (%s)" % (name, type(e).__name__))
    except Exception as e:
        notes.append("the step stopped early (%s: %s)" % (type(e).__name__, str(e)[:160]))
    tail = []
    if fuller: tail.append("%d fuller workspace cop%s replaced main's shorter one: %s%s" % (len(fuller), "y" if len(fuller) == 1 else "ies", ", ".join(fuller[:10]), " (+%d more)" % (len(fuller) - 10) if len(fuller) > 10 else ""))
    if differ: tail.append("patient map: %d feed patient(s) differ - main's chart kept: %s%s (this workspace's map still names its own chart for them - a person decides which chart is right and corrects the other side)" % (
        len(differ), ", ".join(differ[:20]), " (+%d more)" % (len(differ) - 20) if len(differ) > 20 else ""))
    if dxdiff: tail.append("diagnosis cache: %d code(s) differ - main's id kept: %s%s (this workspace's cache still holds its own id for them and puts it on the charges it enters - a person decides which id is right and corrects the other side)" % (
        len(dxdiff), ", ".join(dxdiff[:20]), " (+%d more)" % (len(dxdiff) - 20) if len(dxdiff) > 20 else ""))
    if bad: tail.append("could not be read and left as they are on main: " + ", ".join(bad))
    tail += notes
    for s in running:      # last, so that the line ends "... not carried this time - TOP OF THE REPORT"
        tail.append(("an ingest is still running (stamp %s): its %d register(s) are not carried this time" % (s, held.get(s, 0))) if s else
                    "an ingest is still running (its stamp cannot be read from its command line, so no register is held back): a register it is still writing may be on main unfinished - mirror again when it has ended")
    line = "feed registers: %d file(s) carried into practices/ehpa/registers/ (%d batch register(s) copied, %d standing file(s) merged)%s%s" % (
        copied + merged, copied, merged, "".join(" - " + t for t in tail), " - TOP OF THE REPORT" if (differ or dxdiff or bad or notes or running) else "")
    try: print(line)
    except UnicodeError: print(line.encode("ascii", "replace").decode("ascii"))      # an odd character in a path never costs the line
    return copied + merged
def feed_standing_unreadable():
    """The standing feed files in practices/ehpa/registers/ that are there and are NOT a JSON object, each with what is wrong with it:
    "conflict markers", "empty", "no JSON object" or the kind of error. (11/25/2026, the verification of the corrected step: two runs that
    add their rows to the file register at the same place leave conflict markers in it after a pull with rebase. The step above names such
    a file and leaves it for a person - but `feed-registers` ended 0, so the run's own commit of the folder followed and put the markers
    on main, where the ingest of every later container stops before it reads a file: the feed is down until a person repairs main.) It
    looks at every standing file main holds, also one the workspace does not have - the step above never opens main's copy of those -
    and at William's standing word feed_same_person.json (FEED_HOME_CHECKED). Never raises."""
    out = []
    for name in tuple(_FEED_MERGE) + FEED_HOME_CHECKED:
        p = os.path.join(ROOT, "practices", "ehpa", "registers", name); raw = None
        if not os.path.lexists(p): continue
        try:
            raw = open(p, "rb").read()
            why = "" if isinstance(json.loads(raw.decode("utf-8")), dict) else "no JSON object"
        except Exception as e:
            why = "conflict markers" if raw and re.search(rb"(?m)^<{7} ", raw) and re.search(rb"(?m)^>{7} ", raw) else "empty" if raw is not None and not raw.strip() else type(e).__name__
        if why: out.append("%s (%s)" % (name, why))
    return out

def feed_standing_put_back():
    """`sync` only (11/25/2026, the check of the verification): a standing feed file that is no longer JSON must never ride into the end-of-run commit.
    `feed-registers` ends non-zero on such a file, but a run that did not act on that line still reaches `sync`, whose commit takes the whole tree - the
    checker replayed it with the real `sync`: the conflict markers of a stopped pull went to main in the file register, and the ingest of every later
    container stops there. So before the commit: for every standing file feed_standing_unreadable() names, the copy this checkout last COMMITTED comes
    back in its place (main's readable copy; the rows this run added to it are not lost for good - the next run's merge adds them again from its
    workspace). A file whose committed copy is unreadable too is left - nothing here can repair main, a person does. A file with no committed copy at
    all is moved out of the tree to <workspace>/outbox/unreadable/ (never deleted). -> one sentence per file, [] when all read as JSON. Never raises."""
    out = []
    for item in feed_standing_unreadable():
        name, _sep, why = item.partition(" ("); why = "(" + why
        rel = "practices/ehpa/registers/" + name; p = os.path.join(ROOT, rel)
        try:
            head = subprocess.run(["git", "-C", ROOT, "show", "HEAD:" + rel], capture_output=True)
            if head.returncode != 0:                                         # the checkout holds no committed copy of it
                keep = os.path.join(WS, "outbox", "unreadable"); os.makedirs(keep, exist_ok=True)
                dst = os.path.join(keep, "%s.%s" % (name, datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")))
                shutil.move(p, dst); out.append("%s %s - no committed copy: moved out of the tree to %s" % (name, why, dst)); continue
            try: readable = isinstance(json.loads(head.stdout.decode("utf-8")), dict)
            except Exception: readable = False
            if not readable:
                out.append("%s %s - the committed copy is not readable either: a person repairs it on main" % (name, why)); continue
            r = subprocess.run(["git", "-C", ROOT, "checkout", "HEAD", "--", rel], capture_output=True, text=True)
            if r.returncode != 0:                                            # git would not (a folder or a link in the file's place): the committed bytes are written here
                if os.path.isdir(p) and not os.path.islink(p): shutil.rmtree(p)
                elif os.path.lexists(p): os.remove(p)
                open(p, "wb").write(head.stdout)
            out.append("%s %s - the committed copy was put back" % (name, why))
        except Exception as e:
            out.append("%s %s - could not be put back (%s): commit NOTHING from practices/ehpa/registers" % (name, why, type(e).__name__))
    return out

def gate_tree(path=".", failed="nothing committed; fix the source and rerun"):
    """10/6/2026: everything `git add -A` would commit passes through phi_gate's tree mode first - registers,
    scan summaries and run artifacts under practices/ and nightly/runs/ were reaching GitHub with patient
    names in them. Names -> pseudonym or [name]; identifiers -> [MBI]/[SSN]/[member id]; a run digest, needs
    list / needs section or run report never enters the tree (Drive carries those).
    11/25/2026: `path` and `failed` - `mirror.py feed-registers` runs this same gate over practices/ehpa/registers alone and says in its own
    words what a failure means there (nothing is committed by that subcommand, so "nothing committed" would tell the run nothing)."""
    r = subprocess.run([sys.executable, GATE, "tree", path], capture_output=True, text=True, cwd=ROOT)
    sys.stdout.write(r.stdout)
    if r.returncode:
        sys.stdout.write(r.stderr)
        raise SystemExit("phi_gate tree FAILED - %s" % failed)

# ---- 3. postman ---------------------------------------------------------------------------------
def build_postman():
    r = subprocess.run([sys.executable, PMB], capture_output=True, text=True)
    sys.stdout.write(r.stdout + r.stderr)
    if r.returncode:
        raise SystemExit("postman build failed")

# ---- 4. git -------------------------------------------------------------------------------------
def token():
    for p in (os.path.join(ROOT, "secrets", "github_pat.key"), os.path.join(WS, "secrets", "github_pat.key")):
        if os.path.exists(p):
            return open(p).read().strip()
    return None

def commit_and_push(message):
    gate_tree()
    sh("git add -A")
    st = sh("git status --porcelain").stdout.strip()
    if not st:
        print("git: nothing changed since the last mirror")
    else:
        trailer = "\n\nCo-Authored-By: %s\nClaude-Session: %s" % (os.environ.get("CLAUDE_CO_AUTHOR", "Claude <noreply@anthropic.com>"), os.environ.get("CLAUDE_SESSION_URL", "(set CLAUDE_SESSION_URL to the running session before mirror.py sync)"))
        msgfile = os.path.join(WS, "outbox", ".commit_msg.txt"); os.makedirs(os.path.dirname(msgfile), exist_ok=True)
        open(msgfile, "w").write(message + trailer + "\n")   # 9/25: -F keeps the trailer on real lines (json.dumps through the shell left literal \n in the message)
        sh('git -c user.name="Claude" -c user.email="noreply@anthropic.com" commit -q -F %s' % json.dumps(msgfile))   # 9/22 stop-hook rule: commits are authored by Claude <noreply@anthropic.com>, never billing-mirror
        print("git: committed -> %s" % sh("git rev-parse --short HEAD").stdout.strip())
    tok = token()
    if not tok:
        print("git: no secrets/github_pat.key - pushing through the session proxy (the attached repository's own credential)")
        if push_via_proxy():
            return True
        return bundle()
    url = "https://x-access-token:%s@github.com/%s" % (tok, REPO)
    head = sh("git rev-parse --abbrev-ref HEAD").stdout.strip()
    for b in BRANCHES:
        r = sh("git push -q %s %s:refs/heads/%s" % (url, head, b), check=False)
        out = (r.stdout + r.stderr).replace(tok, "<PAT>")
        if r.returncode == 0:
            print("git: pushed -> %s" % b)
        elif "authorized repository set" in out or "403" in out:
            print("git: PUSH BLOCKED by the session proxy (repo not in this session's authorized sources) - not retrying")
            return bundle()
        else:
            print("git: push to %s failed:\n%s" % (b, out[-600:]))
            return bundle()
    return True

UNION = ["docs/captured_calls.md merge=union", "docs/captured_calls_additions_*.md merge=union", "practices/ehpa/rules.md merge=union",
         "needs_facesheet_list.md merge=union", "docs/SHARED_LESSONS.md merge=union", "practices/ehpa/registers/rebill_log.jsonl merge=union"]
# 11/10/2026 (second ops-and-text review): rules.md merges by union - EXCEPT that a bullet rewritten in place (the place-of-service rule, the clinician
# and building of a feed visit, the quality code 1123F with M0004, the initial nursing-facility visit) REPLACES its old copy instead of coming back
# beside it; both sides rewriting the same bullet stops as a conflict. tools/mirror/rules_merge.py does it; this registers it as git's merge driver
# for rules.md (repo-local config and .git/info/attributes, never committed). Its line goes after the union line: the later line wins.
RULES_DRIVER = os.path.join(ROOT, "tools", "mirror", "rules_merge.py")
RULES_ATTR = "practices/ehpa/rules.md merge=ehpa-rules"
def union_rules():
    """Append-only text files merge by union (both sides kept) when origin/main moved under us - the same list
    tools/mirror/apply_bundle.py uses; written to .git/info/attributes (repo-local, never committed). Idempotent.
    rules.md gets the ehpa-rules driver on top (a rewritten bullet replaces its old copy) whenever tools/mirror/rules_merge.py is there."""
    d = sh("git rev-parse --git-dir").stdout.strip()
    if not os.path.isabs(d):
        d = os.path.join(ROOT, d)
    f = os.path.join(d, "info", "attributes"); os.makedirs(os.path.dirname(f), exist_ok=True)
    have = open(f).read() if os.path.exists(f) else ""
    add = [r for r in UNION if r not in have]
    if add:
        open(f, "a").write(("" if not have or have.endswith("\n") else "\n") + "\n".join(add) + "\n")
    if os.path.exists(RULES_DRIVER):
        import shlex
        sh("git config merge.ehpa-rules.name %s" % shlex.quote("rules.md: union, a rewritten bullet replaces its old copy"))
        sh("git config merge.ehpa-rules.driver %s" % shlex.quote("%s %s %%O %%A %%B" % (shlex.quote(sys.executable), shlex.quote(RULES_DRIVER))))
        have = open(f).read().splitlines()
        if [l for l in have if l.startswith("practices/ehpa/rules.md ")][-1:] != [RULES_ATTR]:      # the driver's line must be the LAST one for rules.md
            open(f, "w").write("\n".join(l for l in have if l != RULES_ATTR) + "\n" + RULES_ATTR + "\n")

def push_via_proxy():
    """11/2/2026 (William: "make it permanent where I don't have to manually push anything"): a Claude Code cloud session with
    the repository attached pushes through the session proxy, which injects the repository's credential - no PAT, no Drive
    package, no pull request for William to merge. origin/main moves every few hours, so bring it in first (a merge commit;
    append-only files merge by union), then push main and the project's synced branch. A push that GitHub rejects as
    non-fast-forward (main moved again meanwhile) is retried once after another merge. Returns True when main carries HEAD;
    False when the proxy or GitHub refuses - HEAD is then left safe on its own branch upstream and the caller writes the package."""
    for attempt in (1, 2):
        r = sh("git fetch -q origin main", check=False)
        if r.returncode:
            print("git: fetch origin main failed - %s" % (r.stdout + r.stderr).strip()[-300:]); return False
        union_rules()
        if sh("git merge-base --is-ancestor origin/main HEAD", check=False).returncode != 0:
            m = sh('git -c user.name="Claude" -c user.email="noreply@anthropic.com" merge -q --no-edit origin/main', check=False)
            if m.returncode:
                sh("git merge --abort", check=False)
                print("git: merging origin/main CONFLICTS - resolve by hand, then rerun:\n%s" % (m.stdout + m.stderr).strip()[-600:]); return False
            print("git: merged origin/main -> %s" % sh("git rev-parse --short HEAD").stdout.strip())
        r = sh("git push -q origin HEAD:refs/heads/%s" % BRANCHES[0], check=False)
        out = (r.stdout + r.stderr).strip()
        if r.returncode == 0:
            print("git: pushed -> %s (session proxy)" % BRANCHES[0]); break
        if attempt == 1 and ("fetch first" in out or "non-fast-forward" in out):
            print("git: main moved during the push - merging it once more"); continue
        print("git: push to %s refused - %s" % (BRANCHES[0], out[-400:]))
        head = sh("git rev-parse --abbrev-ref HEAD", check=False).stdout.strip()
        if head and head != "HEAD" and head not in BRANCHES:
            r2 = sh("git push -q -u origin %s" % head, check=False)
            print("git: HEAD kept safe on origin/%s%s - open a pull request for it" % (head, "" if r2.returncode == 0 else " FAILED too"))
        return False
    for b in BRANCHES[1:]:
        r = sh("git push -q origin HEAD:refs/heads/%s" % b, check=False)
        print("git: pushed -> %s (session proxy)" % b if r.returncode == 0 else "git: push to %s failed (main is pushed; the synced branch catches up on the next mirror) - %s" % (b, (r.stdout + r.stderr).strip()[-300:]))
    return True

def bundle(slug="", base_ref=None):
    """Fallback when the push is blocked (William 9/23/2026): leave a PACKAGE the 2-hourly routine applies to the triple mirror -
    a thin git bundle (everything after origin/main when that ref is known, else --all), the same bundle as base64 TEXT (Drive
    text uploads survive; binaries download corrupt through the connector) and a JSON manifest with the sha256 the routine
    verifies before `tools/mirror/apply_bundle.py` pulls it and pushes main + the synced branch. Nothing learned waits for William."""
    import hashlib, base64, json as _json
    out = os.path.join(WS, "outbox"); os.makedirs(out, exist_ok=True)
    stem = "effinger-billing-backend_%s%s" % (TODAY, ("_" + slug) if slug else "")
    path = os.path.join(out, stem + ".bundle")
    base = sh("git rev-parse --verify -q %s" % (base_ref or "origin/main"), check=False).stdout.strip()   # base_ref: a follow-up package on top of an earlier package's head (its commits are not on origin yet)
    branch = sh("git rev-parse --abbrev-ref HEAD", check=False).stdout.strip() or "main"
    rng = "%s..%s" % (base_ref or "origin/main", branch) if base and sh("git merge-base --is-ancestor %s HEAD" % (base_ref or "origin/main"), check=False).returncode == 0 else "--all"
    sh("git bundle create -q %s %s" % (path, rng))   # thin: only the new commits, under the branch's own ref name (refs/heads/<branch>) so `git pull <bundle> <branch>` finds it
    raw = open(path, "rb").read(); sha = hashlib.sha256(raw).hexdigest()
    b64 = base64.b64encode(raw).decode(); open(path + ".b64", "w").write(b64)
    PART = 45000   # a Drive text upload through the connector is one tool call, capped well under this; parts of 45 KB survive (9/23 lesson)
    parts = []
    for i in range(0, len(b64), PART):
        name = "%s.bundle.b64.part%02d" % (stem, len(parts) + 1); chunk = b64[i:i + PART]
        chunk = "\n".join(chunk[j:j + 76] for j in range(0, len(chunk), 76)) + "\n"   # 76-char lines: a Read tool truncates very long lines; apply_bundle strips the whitespace again
        open(os.path.join(out, name), "w").write(chunk); parts.append({"name": name, "chars": len(chunk), "sha256": hashlib.sha256(chunk.encode()).hexdigest()})
    commits = sh("git log --format=%%h\\ %%s %s" % (rng if rng != "--all" else "-20"), check=False).stdout.strip().splitlines()
    man = {"package": stem, "bundle": stem + ".bundle.b64", "sha256": sha, "bytes": len(raw), "range": rng, "branch": branch, "base": base, "head": sh("git rev-parse HEAD").stdout.strip(),
           "commits": commits, "created": TODAY,
           "parts": parts,
           "apply": "download every part (PACKAGE_<stem>.bundle.b64.partNN, text) and tools/mirror/apply_bundle.py (loose copy 'PACKAGE_apply_bundle.py' in 'github mirror' when tools/mirror/ is not in main yet); "
                    "python3 apply_bundle.py <part01> <part02> ... --sha256 %s (it concatenates the parts, decodes, verifies, pulls refs/heads/%s = a fast-forward when main is still at base %s) "
                    "&& git push origin %s && git push origin HEAD:<synced branch>; then mirror.py sync (Postman regenerate + Drive copies). Without apply_bundle.py: cat parts > x.b64; base64 -d x.b64 > x.bundle; git bundle verify x.bundle; git pull --no-rebase x.bundle %s" % (sha, branch, base[:9], branch, branch)}
    _json.dump(man, open(os.path.join(out, stem + ".manifest.json"), "w"), indent=1)
    print("git: push blocked -> PACKAGE written: %s(.b64) + %s.manifest.json (sha256 %s, %d commits)" % (path, stem, sha[:12], len(commits)))
    print("     upload the PARTS (%d x <=45 KB text, PACKAGE_<stem>.bundle.b64.partNN) + the manifest (PACKAGE_<stem>.manifest.json) + a loose PACKAGE_apply_bundle.py to Drive 'github mirror' (%s)"
          " - the routine cannot read project docs, so Drive must carry the bytes; project_write the whole .b64 as mirror/outbox/%s.bundle.b64 too (byte-exact, for a chat session)."
          " The next routine run's GITHUB INBOX step applies it and pushes. William need not touch it." % (len(parts), DRIVE["github mirror"], stem))
    return False

# ---- driver -------------------------------------------------------------------------------------
def status():
    print("repo: %s  HEAD %s  branch %s" % (ROOT, sh("git rev-parse --short HEAD").stdout.strip(), sh("git rev-parse --abbrev-ref HEAD").stdout.strip()))
    print("unpushed vs origin/main: %s commit(s)" % sh("git rev-list --count origin/main..HEAD", check=False).stdout.strip())
    subprocess.run([sys.executable, PMB, "--check"])
    v = json.load(open(os.path.join(ROOT, "docs", "api_vocabulary.json")))
    print("vocabulary: %d calls in %d folders" % (len(v["calls"]), len({c["folder"] for c in v["calls"]})))
    print("pseudonym map: %s   PAT: %s" % ("present" if os.path.exists(os.path.join(ROOT, "secrets", "pseudonyms.json")) else "MISSING", "present" if token() else "missing"))

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        return status()
    if cmd == "sync":
        msg = sys.argv[2] if len(sys.argv) > 2 else "mirror %s" % TODAY
        merge_registry()
        sync_helpers()
        sync_feed_registers()
        _back = feed_standing_put_back()      # 11/25/2026: a standing feed file that is no longer JSON never rides into this commit (the function's own words)
        if _back: print("feed registers: NOT READABLE before the commit: %s (rows this run added to a file that was put back come to main with the next mirror) - TOP OF THE REPORT" % "; ".join(_back))
        build_postman()
        ok = commit_and_push(msg)
        print("\nNEXT (connector legs, in this order):")
        print(" Drive 'billing agent project files' (%s): rename the old captured_calls.md -> captured_calls_%s_pre-merge.md, upload the WORKSPACE copy %s/captured_calls.md (real names) as captured_calls.md; upload docs/postman_effinger_amd.json and trash the previous copy" % (DRIVE["project files"], TODAY, WS))
        print(" Drive 'workspace mirror' (%s): upload every helper changed this run + secrets/pseudonyms.json (PHI: Drive only)" % DRIVE["workspace mirror"])
        print(" Postman connector: updateCollection with docs/postman_effinger_amd.json (createCollection the first time)")
        print(" Drive 'chat history' (%s): the dated digest" % DRIVE["chat history"])
        if not ok:
            print(" Drive 'github mirror' (%s): the bundle from %s/outbox/" % (DRIVE["github mirror"], WS))
        return
    if cmd == "postman":
        return build_postman()
    if cmd == "feed-registers":      # 11/25/2026: only step 2a - for a run that commits by hand (the daily feed task): copies / merges the feed registers, commits nothing
        sync_feed_registers()
        # ... and scrubs what it carried before it returns (review of 11/25/2026). `sync` scrubs at its commit; this subcommand has no commit, so the
        # registers went raw from the workspace into the run's hand commit - the import writes the day a patient passed away beside the chart number of
        # a visit it skips, and this subcommand carries every batch register main lacks, older stamps restored from the state bundle included.
        gate_tree("practices/ehpa/registers", "the feed registers carried into practices/ehpa/registers/ are NOT scrubbed: commit nothing from that folder, fix the cause and run `mirror.py feed-registers` again")
        # ... and ends NON-ZERO while a standing file there is no longer a JSON object (the verification of 11/25/2026 - feed_standing_unreadable says what it found):
        # the `&&` behind this command in the run's own line then stops here, and nothing of the folder is added, committed or pushed. Behind the gate on purpose: what
        # was carried is scrubbed whatever happens next, and this line is the last one the run reads.
        unreadable = feed_standing_unreadable()
        if unreadable: raise SystemExit("feed registers: NOT READABLE on main: %s - commit NOTHING from practices/ehpa/registers: repair the file first (the feed runbook's step (e) says how), then run `mirror.py feed-registers` again - TOP OF THE REPORT" % ", ".join(unreadable))
        return
    sys.exit("usage: mirror.py [status|sync \"message\"|postman|feed-registers]")

if __name__ == "__main__":
    main()
