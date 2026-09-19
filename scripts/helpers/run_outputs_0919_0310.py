# PLAIN ENGLISH (run outputs for the 11pm ET 9/18/2026 slot - ehpa cloud run 2026-09-19T0310Z)
# Decides: nothing. Reads this run's column scan (scan_0912/summary_before.json), the ERA before/after snapshots and the
#   unbilled/AET12 verify registers, then writes: "_run report 9-19 0310.csv"; board_updates_2026-09-19T0310Z.json (Insurance
#   Refresh Board inbox file: appends on the standing rows, one new row for the Center Pointe admit whose chart was verified
#   against Pam's sheet, the pseudonymized duplicate rows closed, one row for William about the board's inbox registry);
#   a needs_facesheet_list.md section, the captured_calls additions file and the chat-history digest (--final).
# Never touches: AMD, the board databases. Names/member ids on the board only. Row ids come from inbox/rowids_0310.json
#   (real ids live outside the mirrored script - PHI gate).
import csv, json, os, datetime, sys
S = "2026-09-19T0310Z"; SRC = "11pm ET 9/18 columns run (ehpa cloud)"; W = "9/18"; SLOT = "11 PM ET 9/18"
NOW = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
IDS = json.load(open("inbox/rowids_0310.json"))
MIRROR = open("mirror_result.txt").read().strip() if os.path.exists("mirror_result.txt") else "pending"
def load(p, d):
    try: return json.load(open(p))
    except Exception: return d
def f(x):
    try: return float(x or 0)
    except Exception: return 0.0
before = load("scan_0912/summary_before.json", {})
eb = load("era_checks_before_%s.json" % S, []); ea = load("era_checks_after_%s.json" % S, [])
nb, ab = len(eb), round(sum(f(c.get("unpostedamount")) for c in eb), 2); na, aa = len(ea), round(sum(f(c.get("unpostedamount")) for c in ea), 2)
ver = load("registers/aet12_verify_%s.json" % S, []); aet_bal = round(sum(f(c.get("insbal")) for c in ver), 2); aet_paid = round(sum(f(c.get("paid")) for c in ver), 2)
ovb = before.get("overview", {}); ua = before.get("unbilled", []); runs_n = ovb.get("claimrunstatuscount", "?")
ERA_TXT = ("%d unposted checks / $%.2f before -> %d / $%.2f after. ERA Center empty the whole run: locks release-expired sent; era_post --all-unposted 0 checks; "
           "fallback dry + live 0 lines; era_clear 0 looked at, 0 dismissed; 0 addpayments faults; no new 835s or Availity files in 'bht Optum era downloads' / 'treasury payments' "
           "(nothing modified there after 22:00Z 9/18); no MA63/M76/M64 work." % (nb, ab, na, aa))
THORNEY_TXT = ("Pam admit email 02:53Z 9/19 ('New admit Center Pointe', PCC Clinical Resident Profile photo, admitted 09/18/2026 from HCA Florida Capital Rehab, orig admit 03/11/2022): "
             "chart pat25994 found by name (DOB matches). Chart already carries Medicare seq 1 (MBI = the sheet's Medicare Beneficiary ID) and Florida Blue seq 2 (policy = the sheet's BCBS Insurance Policy #), "
             "patient order 1,2, no group numbers. AMD free 271: Medicare ACTIVE (Part A 2/1/2007, Part B 7/1/2014, Part D BCBS Association only, no Advantage entity, not deceased); "
             "Florida Blue ACTIVE (STANDARD SECONDARY = Medigap, Medicare primary over 65). No open charges on the chart yet - the Center Pointe visits bill Medicare first when they land. "
             "Address line 1 was blank (line 2 held the facility street): line 1 set to the home street the sheet and CMS agree on, zip 32308 (PATCH 200). Nothing for William.")
rows = []
def add(col, status, patient="", dos="", carrier="", error="", action="", check="", payer="", visit="", amount=""):
    rows.append(dict(column=col, status=status, patient=patient, dos=dos, carrier=carrier, error=error, action=action, checkid=check, payer=payer, visit=visit, amount=amount))
add("Charge Review", "count", action="0 -> 0 (getreviewcharges empty before and after)")
add("Claim Inspector", "count", action="0 -> 0 (getclaiminspectorbatches empty before and after)")
for r in ua:
    err = (r.get("_errs") or [""])[0]
    if err.startswith("Payment reason"): act = "held per the 9/15 rule (payment reason codes on an already-posted line; not a release candidate)"
    elif err.startswith("Bill Insurance"): act = "William's (visit 19375395 'MV' $75.68 line, Bill Insurance = No) - row on his turn since 9/17"
    elif err.startswith("Insurance order"): act = "new HCA chart, zero insplans (getdemographic re-read 03:15Z this run); cascade exhausted 9/18 05:xxZ; no facesheet, Pam email or drop since - held on William's turn"
    else: act = "held"
    add("Unbilled", "remaining", r.get("patientname", ""), "", r.get("carriercode") or "", err, act, visit=r.get("id", ""))
add("Unbilled", "count", action="%s -> %s ($%s); 0 released, 0 charts insured this run" % (ovb.get("unbillablecount"), ovb.get("unbillablecount"), ovb.get("unbillableamount")))
add("Exclusions", "count", carrier="AET12", action="0 -> 0 rows; no claim run newer than 1700202 (%s runs listed; no nightly claim run posted 9/17, 9/18 or so far 9/19 - ninth consecutive worked slot); 68 AET12 charges on 15 charts re-read: billdate 09/16/2026, $%.2f insurance balance open, no AET12 payment (Medicare paid $%.2f), none at $0 - held on the carrier-master fix, not re-sent" % (runs_n, aet_bal, aet_paid))
add("ERA", "count", action=ERA_TXT)
add("Sources", "acted", IDS["thorney_patient"], "09/18/2026", "FLO02 + BCBS", "Pam admit email (Center Pointe)", THORNEY_TXT, visit="pat25994")
add("Boards", "read", action="Working Denials queue 0 queued; Insurance Refresh Board: all 199 rows on Claude's turn read (4 pages), drops 0 new, no William note newer than 9/15; board inbox: the registry's applied map lists only 9/12-9/14 files (all already moved out of the inbox) - nothing trashed")
add("Boards", "finding", action="The Insurance Refresh Board's sync registry (meta/drive_sync) has not recorded a single applied inbox file since 9/15 (lastCheck 03:15Z 9/19, version 805) while ~60 board_updates/denials_updates files from 9/15-9/19 sit in the inbox - the page re-applies them on every open; the 9/18 0710Z-2310Z files carry pseudonymized row ids (conway-shelby, thurlow-nerys, gorman-davin, wexford-shelagh) and re-created those duplicate rows at 03:11Z 9/19. This run closes the duplicates in its update file and puts a row on William's turn (board-inbox-registry-0919); the standing rule forbids trashing files the registry never listed.")
add("Sources", "read", action="Facesheet folders (hca/tmh/PCC), Claimocity drop, Optum ERA folder, treasury folder, billing agent project files: nothing modified after 22:00Z 9/18 except the routine's own files; Pam Gmail: one new admit email 02:53Z 9/19 (Center Pointe, pat25994 - verified, above)")
add("Routine", "note", action="State bundle workspace_state_2026-09-18_1123UTC on Drive is older than GitHub main; registers restored from practices/ehpa/registers (109 files) + needs_facesheet_list rebuilt from 32 nightly/runs sections. Missing required helpers (not rewritten): columns_inspector2_0908.py, era_details_pull.py (era_step_b_0913.py fills the cache instead).")
add("Open on Claude's turn", "note", carrier="BCBS", action="Florida Blue patient-balance audit (row bcbs-patient-balance-audit-0918): 179 charges / 48 charts / $22,499.90 patient balance - not worked this run; hold Florida Blue patient statements")
with open("_run report 9-19 0310.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
ops = []
def app(id, ok, result, note=None, set_=None):
    o = {"op": "upsert", "collection": "items", "id": id, "append": {"checks": [{"ok": ok, "src": SRC, "result": result, "when": W}]}}
    if note: o["append"]["notes"] = [{"who": "Claude", "text": note, "at": NOW}]
    if set_: o["set"] = set_
    ops.append(o)
app("aet12-carrier-cpid", "no", "11pm ET 9/18: unchanged - Exclusions column 0 rows, no claim run newer than 1700202 (%s listed; no nightly claim run posted on 9/17, 9/18 or so far 9/19, ninth consecutive worked slot). 68 AET12 charges on the 15 charts: billdate 09/16/2026, $%.2f insurance balance open, no AET12 payment. Held, not rebilled, not completed - still waiting on the carrier record change (IDs dialog / Claim Fields / Box 33B REF*EI, or the AMD 837 case), then 'rebill'." % (runs_n, aet_bal))
app("era-manual-post-0912", "na", "ERA step 5 (%s, run %s): %s" % (SRC, S, ERA_TXT))
app("availity-remits-backlog", "na", "No Availity PDF or Check/EFT export newer than the registered set in 'bht Optum era downloads' / 'treasury payments' (nothing modified after 22:00Z 9/18 outside this routine's own files) - nothing to parse, post or reconcile; facesheet folders, board drops, Working Denials queue: nothing new; Pam Gmail: one new admit email 02:53Z 9/19 (Center Pointe, chart verified - row %s)." % IDS["thorney"])
for key, txt in (("hca1", "chart still has zero insurance plans (getdemographic 03:15Z 11pm ET 9/18); no facesheet in hca/tmh/PCC/Claimocity folders, Pam Gmail: only the 02:53Z Center Pointe admit (a different patient), no board drop; 3 visits stay in Unbilled 'Insurance order is missing'"),
                 ("hca2", "chart still has zero insurance plans (getdemographic 03:15Z 11pm ET 9/18); CMS names Capital Health Plan MA since 11/2016 - the CHP member id (facesheet / card) is still the missing piece; no facesheet, Pam email or drop since; 3 visits stay in Unbilled 'Insurance order is missing'"),
                 ("hca3", "chart still has zero insurance plans (getdemographic 03:15Z 11pm ET 9/18); no facesheet in hca/tmh/PCC/Claimocity folders, no Pam email, no board drop; 2 visits stay in Unbilled 'Insurance order is missing'")):
    app(IDS[key], "no", txt)
app(IDS["wexford"], "human", "11pm ET 9/18: visit 19375395 still on the Unbilled snapshot ('Bill Insurance = No at charge level and charge has insurance balance', the MV $75.68 line) - unchanged, still yours: delete the line, set Bill Insurance with the carrier, or move the $75.68 to the patient balance.")
app("bcbs-patient-balance-audit-0918", "na", "11pm ET 9/18: not worked this run (same blocker as 0710Z-0110Z: the CO-45 split needs the Availity CheckDetails rows re-parsed from the Check PDFs; the 80 full-charge $0-denial lines are denial decisions) - hold Florida Blue patient statements.")
for d in IDS["dups"]:
    ops.append({"op": "upsert", "collection": "items", "id": d, "set": {"status": "done", "need": "CLOSED 9/19 - duplicate row created from a pseudonymized run-script id (the board inbox re-applies the 9/18 files on every open). The real row is under the patient's name; nothing to do here."},
                "append": {"notes": [{"who": "Claude", "text": "Duplicate row closed by the 11pm ET 9/18 run; see the row under the real name.", "at": NOW}]}})
ops.append({"op": "upsert", "collection": "items", "id": IDS["thorney"],
            "set": {"patient": IDS["thorney_patient"], "dob": IDS["thorney_dob"], "facility": "CENTRE POINTE HEALTH & REHAB (SNF)", "amdid": "25994", "mbi": IDS["thorney_mbi"],
                    "inscarrier": "FLO02 Florida Medicare", "insid": IDS["thorney_mbi"], "insplans": "1st FLO02 Florida Medicare %s (since 7/22/2022) - 2nd BCBS Florida Blue %s (Medigap, since 7/22/2022)" % (IDS["thorney_mbi"], IDS["thorney_bcbs"]),
                    "lastfac": "Centre Pointe Health & Rehab", "lastdos": "", "amount": 0, "status": "claude",
                    "need": "None - chart verified against Pam's 9/18 Center Pointe admit sheet: Medicare primary (ACTIVE A/B) with Florida Blue Medigap second, both already on the chart with the sheet's numbers; home street filled into address line 1. The Center Pointe visits bill Medicare when they land.",
                    "why": "Pam admit email 9/19 02:53Z: 'New admit Center Pointe' (PCC profile photo, admitted 09/18/2026 from HCA Florida Capital Rehab)"},
            "append": {"checks": [{"ok": "ok", "src": SRC + " - Pam admit sheet vs AMD chart", "result": "Medicare A (MBI) + BCBS %s on the sheet = the chart's FLO02 seq 1 + BCBS seq 2; DOB matches; no open charges" % IDS["thorney_bcbs"], "when": W},
                                  {"ok": "ok", "src": "AMD eligibility (free 271) - Medicare + Florida Blue", "result": "Medicare ACTIVE Part A 2/1/2007, Part B 7/1/2014, Part D BCBS Association only, no Advantage entity, not deceased; Florida Blue ACTIVE 1/1/2025-open, STANDARD SECONDARY (Medigap), Medicare primary over 65", "when": W},
                                  {"ok": "ok", "src": "AMD address PATCH (addr_line1_fix)", "result": "line 1 blank -> 3438 SEDONA LOOP (sheet + CMS 271), zip 32308-6100; line 2 still holds the facility street [address] (cosmetic)", "when": W}],
                       "api": [{"src": "AMD 271 - Medicare + Florida Blue (pat25994)", "at": NOW, "text": "seq1 car6085 %s -> ACTIVE | plan 20070201,20140701 | A 20070201 B 20140701 | other: OT 18:S2135 N6:804 BLUE CROSS BLUE SHIELD ASSOCIATION (Part D) | death - | addr 3438 SEDONA LOOP TALLAHASSEE FL 32308-6100\\nseq2 car6062 %s -> ACTIVE | plan 20250101-99991231 | others MB/MA PRIMARY OVER 65 1L:%s; PR STANDARD SECONDARY" % (IDS["thorney_mbi"], IDS["thorney_bcbs"], IDS["thorney_mbi"])}],
                       "notes": [{"who": "Claude", "text": "Created by the 11pm ET 9/18 run from Pam's Center Pointe admit email. Chart already right - nothing for you.", "at": NOW}]}})
ops.append({"op": "upsert", "collection": "items", "id": "board-inbox-registry-0919",
            "set": {"patient": "BOARD INBOX - sync registry stopped recording (since 9/15)", "dob": "", "facility": "Insurance Refresh Board page", "amdid": "", "mbi": "", "amount": 0, "status": "william",
                    "need": "WILLIAM: the board's sync registry (meta/drive_sync) has recorded no applied inbox file since the 9/14 9:20 PM ET repair - its 'applied' map still lists only the 9/12-9/14 files, while about 60 board_updates / denials_updates files from 9/15-9/19 sit in 'board inbox' and the page re-applies all of them every time you open it (lastCheck 03:15Z 9/19). Effects: rows revert to older status/need after you change them, and the 9/18 0710Z-2310Z files (written with pseudonymized row ids) re-create duplicate rows (conway-shelby, thurlow-nerys, gorman-davin, wexford-shelagh) on every open - this run closed them again. The runs may only trash inbox files the registry lists, so nothing was trashed. Fix options: repair the page's registry write (a chat session with write_db can re-register the 9/15-9/19 files as applied, as was done 9/14), or move the 9/15-9/18 files into the 'ingested before 9-14' folder yourself.",
                    "why": "Seen by the 11pm ET 9/18 run: 5 pseudonymized duplicate rows re-created at 03:11Z 9/19 by the inbox re-apply; registry applied map unchanged since 9/15."},
            "append": {"notes": [{"who": "Claude", "text": "Created by the 11pm ET 9/18 run. Until the registry records applied files, every board_updates file in the inbox is re-applied on each open.", "at": NOW}]}})
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
nfl = """## %s columns run (ehpa cloud Code Routine, 03:08-%s UTC 9/19, run %s)
Bootstrap: repo ATTACHED (origin/main 31be959, session branch claude/pensive-einstein-ev7uol, layout 372 helpers + OCR tools), AMD_OK, STEDI_CRED_OK (no key file), ONE amd.login_cached success, no login lock. Drive 'workspace mirror' newest state bundle workspace_state_2026-09-18_1123UTC (26 parts) is older than GitHub main - registers restored from practices/ehpa/registers/ (109 files), needs_facesheet sections rebuilt from nightly/runs/ (32 sections); captured_calls.md = GitHub main docs/captured_calls.md (341 KB); pseudonyms.json 208 names. Missing required helpers (not rewritten): columns_inspector2_0908.py, era_details_pull.py (era_step_b_0913.py fills the cache instead). Cross-container guard: 0110 START (01:13Z) had its RUN COMPLETE digest (01:25Z) - proceeded.
Boards: Insurance Refresh Board - all 199 rows on Claude's turn read (4 pages), drops 0 new, no William note newer than 9/15; Working Denials queue 0. FINDING: the board's sync registry has recorded no applied inbox file since 9/15 while ~60 inbox files are re-applied on every open (pseudonymized duplicate rows re-created 03:11Z) - duplicates closed in this run's update file, row board-inbox-registry-0919 on William's turn. Facesheet folders, Claimocity drop, Optum ERA folder, treasury folder: nothing modified after 22:00Z 9/18 except the routine's own files. Pam Gmail: ONE new admit email 02:53Z 9/19 - Center Pointe, pat25994: %s
Columns: Charge Review 0 -> 0 | Claim Inspector 0 -> 0 | Unbilled 20 -> 20 ($4094.26): 11 'Payment reason codes' rows held per the 9/15 rule, pat17471007 'Bill Insurance = No' MV line still William's, 8 'Insurance order is missing' visits of the 3 new HCA charts pat17477775 / pat17477776 / pat17477779 (zero insplans re-read 03:15Z; the 9/18 0510Z cascade stands; no new facesheet, Pam email or drop) held on William's turn | Exclusions 0 -> 0 (no claim run newer than 1700202, %s runs listed - NO nightly claim run posted 9/17, 9/18 or so far 9/19, ninth consecutive worked slot; 68 AET12 charges $%.2f open, billdate 09/16/2026, no AET12 payment, not re-sent). Nothing released, rebilled or written off by this run.
ERA step 5: %s Availity 5(g): nothing new.
OPEN (Claude's turn, from the 9/18 0310Z run): Florida Blue patient-balance audit - 179 charges / 48 charts / $22,499.90 - not worked. Hold Florida Blue patient statements until then.
Calls learned: no new AMD call shapes (calls exercised: lookuppatient name wildcard, getdemographic, gettxhistory, checkEligibility x2, the addr_line1_fix PATCH). Vocabulary entries added: 0.
Mirror: %s
""" % (SLOT, datetime.datetime.utcnow().strftime("%H:%M"), S, THORNEY_TXT, runs_n, aet_bal, ERA_TXT, MIRROR)
open("needs_facesheet_list_section_%s.md" % S, "w").write(nfl)
if "--final" in sys.argv:
    open("needs_facesheet_list.md", "a").write("\n" + nfl)
    add_md = """# captured_calls additions - %s (backend billing run %s, ehpa cloud)

No new AMD or Stedi call shapes this run. Behaviours worth keeping:
- A Pam admit email whose subject names an existing patient: `lookuppatient class="api" name="LAST,FIRST%%"` found the chart in one call (DOB matched the PCC profile photo); getdemographic showed both plans already on the chart with the sheet's numbers, so the only write was the address line-1 fill (addr_line1_fix.py: PATCH 200, line 2 kept).
- The Insurance Refresh Board's sync registry (meta/drive_sync) has not recorded an applied inbox file since 9/15 (lastCheck keeps advancing, version 805): every board_updates_*.json in 'board inbox' is re-applied on each open, and files written with pseudonymized row ids re-create duplicate rows each time. Row ids must come from a local inbox/rowids_*.json; the duplicates are closed by this run's update file; the registry repair is William's / a chat session with write_db.
- getclaimrunstatus still lists 1700202 as the newest claim run at 03:13Z 9/19 (78 runs): ninth consecutive worked slot with no nightly claim run.
- ERA Center empty (0 checks) at 03:16Z 9/19 - era_post / fallback / era_clear all no-ops; the chain script is idempotent on an empty list.
""" % (S, SLOT)
    open("captured_calls_additions_2026-09-19_0310UTC-11pmET-ehpa-cloud.md", "w").write(add_md)
    digest = "# %s run digest - backend billing run, %s slot (ehpa cloud)\n\n%s\nRUN COMPLETE\n" % (S.replace("T", "_").replace("Z", "UTC"), SLOT, nfl)
    open("chat_history/%s run digest.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write(digest)
print("rows", len(rows), "board ops", len(ops), "ERA", nb, ab, "->", na, aa, "AET12 bal", aet_bal)
