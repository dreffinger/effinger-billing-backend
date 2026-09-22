# PLAIN ENGLISH (run outputs for the 9pm ET 9/21/2026 slot - ehpa cloud run 2026-09-22T0110Z)
# Decides: nothing. Reads this run's snapshots + the UHC rejected-claims register and writes: "_run report 9-21 0110.csv";
#   board_updates_2026-09-22T0110Z.json (checks appends on the standing watch rows + ONE new row on William's turn for the
#   UHC portal export); a needs_facesheet_list.md section; the chat-history digest (--final, after mirror_result.txt exists).
# Never touches: AMD, the board databases. Chart ids only in the section/digest - no patient names.
import csv, json, os, datetime, sys, collections
S = "2026-09-22T0110Z"; SRC = "9pm ET 9/21 columns run (ehpa cloud)"; W = "9/21"; SLOT = "9 PM ET 9/21"
NOW = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
MIRROR = open("mirror_result.txt").read().strip() if os.path.exists("mirror_result.txt") else "pending"
def load(p, d):
    try: return json.load(open(p))
    except Exception: return d
def f(x):
    try: return float(x or 0)
    except Exception: return 0.0
eb = load("era_checks_before_%s.json" % S, []); ea = load("era_checks_after_%s.json" % S, eb)
nb, ab = len(eb), round(sum(f(c.get("unpostedamount")) for c in eb), 2); na, aa = len(ea), round(sum(f(c.get("unpostedamount")) for c in ea), 2)
reg = load("registers/uhc_rejected_%s.json" % S, {"rows": [], "classes": {}})
R = reg["rows"]; C = reg["classes"]
def dol(cls): return sum(x["insbal"] for x in R if x["class"] == cls)
def pats(cls): return len({x["pid"] for x in R if x["class"] == cls and x.get("pid")})
UHC_TXT = ("UHC portal 'rejected claims' exports (6 CSVs William dropped into 'bht Optum era downloads' 00:00-00:05Z 9/22; the first is the full list, the other five are shrinking subsets of it): 436 distinct UHC claims on 101 charts, submitted 8/31-9/10/2026 (the 9/3-9/10 rebill runs), DOS 2/2024-9/2026, every row 'Action Required', portal deadlines 11/29-12/9/2026. The export carries NO rejection reason. Matched to AMD (massrebillsearch unpaid list + gettxhistory): %d closed in AMD (no open insurance balance - paid/adjusted/written off earlier; the re-sent claim duplicated an adjudicated one, nothing to do); %d open UNI20 visits with DOS before 5/1/2026 ($%.2f, %d charts) - held under your standing rule (never rebill UNI20/BCBS older than 5/1/2026, unposted-ERA backlog); %d open August-2026 UNI20 visits ($%.2f, %d charts, all billed 9/10/2026 - 99223/99232/99233 hospital stays and 99487/99489 CCM) that need the portal's rejection REASON before any correction; %d visits whose open balance already sits with another carrier (7 re-routed to UHCMA, 1 to Medicare); %d partly paid (pat21263, 9/4 payments). Nothing re-sent, nothing written off. Register registers/uhc_rejected_%s.json; PHI line list uhc_rejected_claims_%s.csv (SendUserFile)."
           % (C.get("closed-in-amd", 0), C.get("open-pre-0501-2026", 0), dol("open-pre-0501-2026"), pats("open-pre-0501-2026"), C.get("open-2026", 0), dol("open-2026"), pats("open-2026"), C.get("open-other-carrier", 0), C.get("open-partly-paid", 0), S, S))
ERA_TXT = ("%d unposted checks / $%.2f before -> %d / $%.2f after - the ERA Center is empty. Locks release-expired sent; era_post --all-unposted: nothing to post; fallback (payreasons.post_line, ERA-linked) 0 lines; era_clear 0 looked at, 0 dismissed; 0 addpayments faults; no new 835 in 'bht Optum era downloads'; no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (the only new files anywhere in Drive after 23:00Z 9/21 are the six UHC rejected_claims CSVs, worked - see the UHC row); no MA63/M76/M64 work; payreasons.py --list: 0 Unbilled reason-code rows." % (nb, ab, na, aa))
BOOT = "Bootstrap: repo ATTACHED (origin/main 8683fdf, session branch claude/pensive-einstein-s0o3x0), AMD_OK, STEDI_CRED_OK (no key file), AMD password from Gmail thread 1866ce7e2233e4c0, ONE amd.login_cached success, no login lock. Cross-container guard: the 2310Z run's START has its RUN COMPLETE digest (23:28Z); proceeded 01:12Z. Registers from practices/ehpa/registers (225 files); needs_facesheet_list.md rebuilt from the 9/20-9/21 run sections on main; precheck_cache.json / laterality_flag_log.md / pseudonyms.json (223 names) from Drive 'workspace mirror'; missing required helpers columns_inspector2_0908.py, era_details_pull.py (not rewritten; era_step_b_0913.py fills the cache). Newest Drive state bundle still 2026-09-18_1123UTC (stale - not unpacked). Prompt v7 fired; v8 (Drive 9/21 06:30Z, on main) not yet pasted - its rules followed."
rows = []
def add(col, status, patient="", dos="", carrier="", error="", action="", check="", payer="", visit="", amount=""):
    rows.append(dict(column=col, status=status, patient=patient, dos=dos, carrier=carrier, error=error, action=action, checkid=check, payer=payer, visit=visit, amount=amount))
add("Charge Review", "count", action="0 -> 0 (getreviewcharges empty before and after)")
add("Claim Inspector", "count", action="0 -> 0 (getclaiminspectorbatches empty before and after; no new HCA feed batch this slot)")
add("Unbilled", "count", action="0 -> 0 (getclaimunbillablecharges totalcount 0 before and after; payreasons rows 0)")
add("Exclusions", "count", action="0 -> 0 rows on the per-run list calls (81 claim runs; overview 1/$198.00 lagging; no claim run newer than 1700211 at 9/20 02:04 AMD clock - no nightly claim run has posted for 9/20 evening, 9/21 or so far 9/22). AET12: HOLD per William 9/21 - not rebilled, not re-verified this slot.")
add("ERA", "count", action=ERA_TXT)
add("UHC rejected claims", "read", action=UHC_TXT)
for x in sorted(R, key=lambda x: (x["class"], x.get("pid", ""), x["dos"])):
    if x["class"] in ("open-2026", "open-other-carrier", "open-partly-paid", "open-pre-0501-2026"):
        add("UHC rejected claims", x["class"], patient="pat%s" % x.get("pid", ""), dos=x["dos"], carrier=x.get("carrier", ""), error="UHC portal 'Action Required' (no reason in the export); expires " + x["expires"], action=x["detail"], visit=x["visitid"] + x["letter"], amount="%.2f" % x["insbal"], payer="UHC")
add("Sources", "read", action="Pam Gmail: no admit email newer than the three 16:46Z 9/21 readmit records (worked by the 1910Z run). Drive-wide: the only files modified after 23:00Z 9/21 outside the routine's own are the six rejected_claims CSVs (worked). Facesheet folders, Claimocity drop, 835 / Availity / treasury folders otherwise quiet. Board drops 0; Working Denials queue 0; Insurance Refresh Board: no row updated after 15:38Z 9/21 (no new William note).")
add("Boards", "read", action="Board inbox: 23 files present (9/20 0345Z - 9/21 2310Z), none in the board's applied map (registry lastCheck 06:36Z 9/21) - nothing trashed. Denials board registry: only the two 9/12 synctest files - nothing to trash.")
add("Routine", "note", action=BOOT)
add("Open on William's turn", "note", patient="UHC rejected claims", action="41 August-2026 UHC claims ($8,206, 17 charts) rejected 'Action Required' on the UHC portal - the export has no reason column: export the rejection detail (or paste one claim's reason) and the run corrects + re-sends; 69 pre-5/1/2026 claims ($10,872.90) stay held under the no-rebill rule unless you say otherwise")
add("Open on William's turn", "note", patient="routine", action="paste columns_task_prompt_ehpa_cloud_v8.txt into the routine - v7 still fires")
add("Open on William's turn", "note", patient="medicaid-n286 cluster (pat17472419 x2, pat17472518 x7)", action="9 Medicaid-primary 99309s re-created under Effinger 9/13 ($1,269) deny CO208/N286 - referring provider on those visits' referral plan in the UI, then 'rebill'")
add("Open on William's turn", "note", patient="AET12 carrier", action="HOLD (your 9/21 word): carrier master; 59 visits $2,052.25")
add("Open on William's turn", "note", patient="centene-m56-denials-0920", action="SUN01 carrier payer id / CPID check, or 'rebill' - $772.92 on 5 visits")
add("Open on William's turn", "note", patient="FCC (car42008)", action="Medicaid FFS answers every FCC-dual crossover CO256 - 8 coinsurance lines $180.07 held (pat24039, pat20863) - FCC contracting / payer id")
add("Open on William's turn", "note", patient="Automation Center", action="no nightly claim run since 1700211 (9/20 02:04) - the EOD close looks stopped again; the 9/21 rebills wait on it")
add("Open on William's turn", "note", patient="pat17477777", action="clear the Pre-Auth # on main referral plan rplan18462071 in the UI")
add("Open on William's turn", "note", patient="Optum Pay", action="6 Optum Pay remits still to download into 'bht Optum era downloads'")
with open("_run report 9-21 0110.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
ops = []
def app(id, ok, result):
    ops.append({"op": "upsert", "collection": "items", "id": id, "append": {"checks": [{"ok": ok, "src": SRC, "result": result, "when": W}]}})
app("era-manual-post-0912", "na", "ERA step 5 (%s, run %s): %s" % (SLOT, S, ERA_TXT))
app("aet12-carrier-cpid", "na", "%s: HOLD per your 9/21 word - not rebilled, not re-verified this slot; Exclusions 0 rows; no claim run newer than 1700211 (9/20 02:04) - no nightly claim run has posted for 9/20 evening, 9/21 or so far 9/22." % SLOT)
app("availity-remits-backlog", "na", "%s: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' - the six new files there are UHC portal rejected_claims CSVs, worked on their own row (uhc-rejected-claims-0922); Working Denials queue 0; board drops 0; Pam Gmail: nothing newer than the three 16:46Z 9/21 readmit records already worked." % SLOT)
app("bcbs-patient-balance-audit-0918", "na", "%s: not worked this run (same blocker: the CO-45 split needs the Availity CheckDetails rows re-parsed from the Check PDFs; the 80 full-charge $0 denials are denial decisions) - hold Florida Blue patient statements." % SLOT)
open2026 = sorted([x for x in R if x["class"] == "open-2026"], key=lambda x: (x["pid"], x["dos"]))
pre = sorted([x for x in R if x["class"] == "open-pre-0501-2026"], key=lambda x: (x["pid"], x["dos"]))
bypat = collections.defaultdict(list)
for x in open2026: bypat[x["pid"]].append(x)
lines = "; ".join("pat%s %s (%s)" % (p, ", ".join(x["visitid"] + x["letter"] + " " + x["dos"][:5] for x in v), "$%.2f" % sum(x["insbal"] for x in v)) for p, v in bypat.items())
ops.append({"op": "upsert", "collection": "items", "id": "uhc-rejected-claims-0922",
    "set": {"patient": "UHC PORTAL REJECTED CLAIMS (6 CSV exports 9/21)", "dob": "", "facility": "", "amdid": "multiple", "mbi": "", "status": "william",
            "amount": round(sum(x["insbal"] for x in open2026) + sum(x["insbal"] for x in pre), 2),
            "why": "William dropped six rejected_claims*.csv exports from the UnitedHealthcare provider portal into 'bht Optum era downloads' (00:00-00:05Z 9/22): 436 UHC claims on 101 charts submitted 8/31-9/10/2026, every row 'Action Required' with a portal deadline 11/29-12/9/2026. The export has NO rejection-reason column, so the run cannot tell what UHC wants corrected.",
            "need": ("WILLIAM: (1) for the 41 open AUGUST-2026 UHC claims ($%.2f, 17 charts: %s) export the portal's rejection DETAIL (reason / edit text) as a CSV into the same folder, or paste one claim's reason here - the run then corrects and re-sends them all; (2) the 69 open UHC claims with DOS before 5/1/2026 ($%.2f, 15 charts, mostly Sept-Dec 2025) are HELD under your standing rule (never rebill UNI20/BCBS older than 5/1/2026 - unposted-ERA backlog) - say 'rebill' with the reason if you want them worked, or 'writeoff-aged' for a documented untimely write-off; (3) 315 of the 436 are already closed in AMD (paid/adjusted earlier - the 9/4-9/10 re-sends duplicated adjudicated claims) - nothing to do, they fall off the portal list at expiry; 8 visits already sit with UHCMA/Medicare, 3 on pat21263 are partly paid (9/4 payments). Line list: uhc_rejected_claims_%s.csv (sent to you)." % (sum(x["insbal"] for x in open2026), lines, sum(x["insbal"] for x in pre), S)),
            "inscarrier": "UNI20 United Healthcare", "created": NOW, "updated": NOW},
    "append": {"notes": [{"who": "Claude", "text": "Created by the 9pm ET 9/21 run from your six rejected_claims CSV drops. Nothing re-sent or written off - the export has no rejection reason. Give me the reason (portal detail export or a paste) and the August claims go back out corrected the same run.", "at": NOW}],
               "checks": [{"ok": "human", "src": SRC + " - UHC portal export vs AMD", "result": UHC_TXT, "when": W}]}})
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
SEC = """
## %s columns run (ehpa cloud Code Routine, 01:09-%s UTC 9/22, run %s)
%s
Boards: Working Denials queue 0. Insurance Refresh Board: 0 new drops, no row updated after 15:38Z 9/21; 3 rows on William's turn (denial decisions, unchanged). Sources: the only Drive files modified after 23:00Z 9/21 outside the routine's own are six UHC portal rejected_claims CSVs (worked below); Claimocity drop: nothing; Pam Gmail: nothing newer than the three 16:46Z 9/21 readmit records (worked 1910Z).
Claim runs: none newer than 1700211 (9/20 02:04 AMD clock; 81 runs) - no nightly claim run posted for 9/20 evening, 9/21 or so far 9/22.
Columns: Charge Review 0 -> 0 | Claim Inspector 0 -> 0 | Unbilled 0 -> 0 | Exclusions 0 -> 0 rows (overview 1/$198 lagging). AET12: HOLD.
ERA step 5: %s
UHC rejected claims: %s
Write-offs: none. Rebilled: none. Insurance entered: none.
NEEDS WILLIAM: (1) NEW board row uhc-rejected-claims-0922 - the rejection reason for the 41 August-2026 UHC claims ($8,206) and a word on the 69 pre-5/1/2026 ones ($10,872.90); (2) paste prompt v8; (3) board row medicaid-n286-referring-provider-0921 ($1,269, 9 visits); (4) AET12 carrier master (HOLD); (5) centene-m56-denials-0920 ($772.92); (6) FCC contracting (8 lines $180.07 held); (7) nightly claim run stopped again after 1700211; (8) pat17477777 rplan18462071 Pre-Auth # (UI); (9) 6 Optum Pay remits; (10) BCBS patient-balance audit parked.
Calls learned: no new call shapes (massrebillsearch {} + gettxhistory are captured). Vocabulary unchanged (54).
""" % (SLOT, datetime.datetime.utcnow().strftime("%H:%M"), S, BOOT, ERA_TXT, UHC_TXT)
open("needs_facesheet_list_section_%s.md" % S, "w").write(SEC)
if "--final" in sys.argv:
    dig = """# 2026-09-22_0110UTC run digest - backend billing run, 9 PM ET 9/21 slot (ehpa cloud)
%s
Board inbox: board_updates_%s.json (%d ops: checks appends on era-manual-post-0912, aet12-carrier-cpid, availity-remits-backlog, bcbs-patient-balance-audit-0918 + new row uhc-rejected-claims-0922 on William's turn) uploaded; nothing trashed (none of the 23 inbox files is in the board's applied map). Denials file skipped (queue 0).
Vocabulary entries added: 0 (54 calls). Postman: unchanged.
Mirror: %s

RUN COMPLETE
""" % (SEC.strip(), S, len(ops), MIRROR)
    os.makedirs("chat_history", exist_ok=True)
    open("chat_history/%s run digest.md" % S.replace("T", "_").replace("Z", "UTC"), "w").write(dig)
    print("digest written")
print("csv rows", len(rows), "| board ops", len(ops))
