# PLAIN ENGLISH (run outputs for the 7am ET 9/25/2026 slot - ehpa cloud run 2026-09-25T1110Z)
# Decides: nothing. Reads this run's registers (scan_0912 before snapshot, ERA snapshots) and writes:
#   "_run report 9-25 0710.csv" (names allowed - SendUserFile only), board_updates_2026-09-25T1110Z.json (appends on the
#   standing watch rows only - no new rows this run), a needs_facesheet_list.md section (pat ids only),
#   captured_calls_additions_*.md and the chat-history digest (--final adds the mirror result).
# Never touches: AMD, the board databases.
import csv, json, os, datetime, sys
S = "2026-09-25T1110Z"; SRC = "7am ET 9/25 columns run (ehpa cloud)"; W = "9/25"; SLOT = "7 AM ET 9/25"
NOW = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
def rd(p, d): return open(p).read().strip() if os.path.exists(p) else d
def load(p, d):
    try: return json.load(open(p))
    except Exception: return d
def f(x):
    try: return float(x or 0)
    except Exception: return 0.0
MIRROR = rd("mirror_result.txt", "pending")
sb = load("scan_0912/summary_before.json", {}); sa = sb
eb = load("era_checks_before_%s.json" % S, []); ea = load("era_checks_after_%s.json" % S, [])
insp_b = sum(len(v) for v in (sb.get("inspector") or {}).values()); insp_a = insp_b
ub_b = sb.get("unbilled_totalcount"); ub_a = ub_b; ex_b = sum(len(r) for r in (sb.get("exclusions") or {}).values()); ex_a = ex_b
eb_amt = sum(f(x.get("unpostedamount")) for x in eb); ea_amt = sum(f(x.get("unpostedamount")) for x in ea)
ov = sb.get("overview") or {}
def pat(pid): return "pat%s" % pid
rows = []
def add(col, status, **k):
    r = {"column": col, "status": status, "patient": "", "dos": "", "carrier": "", "error": "", "action": "", "amount": "", "checkid": "", "visit": ""}; r.update(k); rows.append(r)
add("Charge Review", "0 -> 0", action="nothing to review (getreviewcharges empty)")
add("Claim Inspector", "%d -> %d" % (insp_b, insp_a), action="no new rows since the 0910Z run; 20 standing holds unchanged (batches 126125-127783), nothing edited")
for h in [("17472874", "15 April-2026 hospital visits", "Hospitalization From Date empty", "HELD - HCA admission date (row thackeray-kendrew-17472874)", "2403.00"), ("17473477", "19455625", "Pattern 35790 + deceased guard", "HELD for William", ""), ("45668", "19455691", "Pattern 20389 F02.80 + deceased guard", "HELD for William: void", ""), ("20863", "19455936", "Pattern 24078 CCI", "HELD for William", ""), ("17477208", "19455940", "duplicate 99487+99489 lines", "HELD for William", ""), ("17474541", "19430630", "Pattern 15775 + 4426", "HELD for William", "109.00")]:
    add("Claim Inspector", "held", patient=pat(h[0]), visit=h[1], error=h[2], action=h[3], amount=h[4])
add("Unbilled", "%s -> %s" % (ub_b, ub_a), action="no new rows since the 0910Z run (no claim run newer than 1700236); 26 standing holds unchanged, nothing released")
for r in sb.get("unbilled", []):
    add("Unbilled", "held", patient="%s %s" % (pat(r["patientid"]), r.get("patientname", "")), visit=r["id"], dos=", ".join(sorted({x.get("dos", "").strip() for x in r["_chgs"]})), carrier=r.get("carriercode", ""), error="; ".join(r.get("_errs") or [])[:120], action="standing hold (see needs list)", amount="%.2f" % sum(f(x.get("fee")) for x in r["_chgs"]))
add("Exclusions", "%d -> %d" % (ex_b, ex_a), action="2 standing PDTP0303 holds unchanged; no claim run newer than 1700236 (overview 8/$1268 lags the list calls)")
add("Exclusions", "held", patient="pat17472517", visit="19423193", carrier="HUM01", error="PDTP0303 missing admission date", action="HELD - no 99223 anchor within 45 days (standing)", amount="70.17")
add("Exclusions", "held", patient="pat20863", visit="19445850", carrier="FLO99", error="PDTP0303 missing admission date", action="HELD - no 99223 anchor within 45 days (standing)", amount="14.38")
add("ERA", "%d checks / $%.2f -> %d / $%.2f" % (len(eb), eb_amt, len(ea), ea_amt), action="ERA Center empty before and after (locks released, no new 835 in 'bht Optum era downloads', nothing to post, nothing to clear); payreasons --list 0 rows")
add("ERA", "Availity 5(g)", action="no new Remittance Viewer PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (nothing modified there after 12:00Z 9/24); no ScanSnap batch; nothing to parse, post or reconcile")
csvname = "_run report 9-25 0710.csv"
with open(csvname, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); [w.writerow(r) for r in rows]
# ---------------- board updates (appends on the standing watch rows only)
ops = []
def chk(rid, result, ok="ok"):
    ops.append({"op": "upsert", "collection": "items", "id": rid, "set": {}, "append": {"checks": [{"ok": ok, "src": SRC, "result": result, "when": W}]}})
chk("aet12-carrier-cpid", "7 AM ET 9/25: HOLD per your 9/21 word - not rebilled, not re-verified this slot; Exclusions 2 -> 2 (both PDTP0303 holds, none AET12); no claim run newer than 1700236.", "na")
chk("availity-remits-backlog", "7 AM ET 9/25: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (nothing modified in any watched folder after 12:00Z 9/24 except the routine's own files); no ScanSnap batch; ERA Center empty (0 checks before and after); Working Denials queue 0; board drops 0; 0 rows changed since 06:30Z; Pam Gmail: nothing newer than the 02:41Z 9/24 Sodalis admit (worked); facesheet folders and Claimocity drop: nothing new. Columns unchanged (0/20/26/2, all standing holds).", "na")
chk("bcbs-patient-balance-audit-0918", "7 AM ET 9/25: not worked this run (same blocker: the CO-45 split needs the Availity CheckDetails rows re-parsed from the Check PDFs; the 80 full-charge $0 denials are denial decisions) - hold Florida Blue patient statements.", "na")
board = {"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}
json.dump(board, open("board_updates_%s.json" % S, "w"), indent=1)
# ---------------- needs section (pat ids only)
sec = """
## %s columns run (ehpa cloud Code Routine, run %s) - %s
- Bootstrap: repo ATTACHED (origin/main b4b4cf3 = the 0910Z run finalize commit; session branch claude/pensive-einstein-rd4de3, main checked out in the session clone, symlinked as /home/claude/effinger-billing-backend); net AMD_OK, STEDI_CRED_OK, GitHub reachable; AMD password from Gregg's thread; ONE amd.login_cached success 11:2xZ; no login lock; START marker uploaded 11:12Z. Layout from main (645 helpers; needs list rebuilt from the 70 run sections in nightly/runs; 365 registers from practices/ehpa/registers); pseudonyms (314 names), precheck cache, laterality log from 'workspace mirror'. bootstrap check: era_details_pull.py and columns_inspector2_0908.py MISSING from main (not rewritten; era_step_b_0913.py fills the era_details cache, insp_*.py scripts are the inspector template). Newest Drive state bundle still 2026-09-18_1123UTC (older than main - not unpacked). GITHUB INBOX: no unapplied PACKAGE_* manifest (both 9/23 packages APPLIED). Boards: Working Denials queue 0; Insurance board 0 new drops, 0 rows changed since 06:30Z (query on updated), inbox registry lists none of the current inbox files - nothing trashed. Pam Gmail: nothing newer than the 02:41Z 9/24 Sodalis admit (worked 0510Z 9/24). Drive: 'bht Optum era downloads' / 'treasury payments' / the three facesheet folders / Claimocity drop / project-files root: nothing modified after 12:00Z 9/24 except the routine's own files; no ScanSnap batch.
- Columns: Charge Review 0 -> 0 | Claim Inspector %d -> %d ($%s) | Unbilled %s -> %s ($%s) | Exclusions %d -> %d (list; overview %s/$%s lagging). NOTHING NEW in the four columns since the 0910Z run - no claim run newer than 1700236, no new Claimocity visit, every row a standing hold; no column write this run.
- Claim Inspector holds (20, unchanged): pat17472874 x15 April-2026 HCA 'Hospitalization From Date empty' (admission date from William); pat17474541 v19430630 Pattern 15775 + 4426; pat17473477 v19455625 + pat45668 v19455691 deceased guard; pat20863 v19455936 CCI 24078; pat17477208 v19455940 duplicate CCM lines.
- Unbilled holds (26, unchanged): 16 pat17472874 + pat17474541 behind the inspector holds; pat17470743 v19441047 MCAD crossover 'prior payor'; pat17477183 v19455471 + v19455759 (facesheet - William); pat17473232 v19455597 and pat17471681 v19455606 (CCM after DOD - William); pat17477639 v19455621 (no plan - William); pat17477842 v19455665 (duplicate chart - William: merge); pat17477850 v19455868 + v19455898 (CHP member id - William); pat17477870 v19456058 (duplicate chart - William: merge).
- EXCLUSIONS: 2 standing PDTP0303 holds unchanged (pat17472517 v19423193 HUM01 $70.17, pat20863 v19445850 FLO99 $14.38 - no 99223 anchor within 45 days); every other run lists 0.
- ERA step 5: %d unposted checks / $%.2f -> %d / $%.2f. ERA Center empty (locks released; no new 835 to upload; nothing to post, clear or hand-post). Auto-posted $0, manual-posted 0, write-offs $0, residual disregarded $0, checks cleared 0. Availity 5(g): no new PDF / Check-EFT export; no ScanSnap batch. payreasons --list: 0 rows.
- Dollars re-sent: $0. Insurance entered: none. Write-offs: none.
- Calls learned: no new call shape (captured_calls_additions_2026-09-25_1110UTC-7amET-ehpa-cloud.md, behaviours only).
- Mirror: %s
""" % (SLOT, S, datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"), insp_b, insp_a, ov.get("claiminspectoramount", "?"), ub_b, ub_a, sb.get("unbilled_totalamount", "?"), ex_b, ex_a, ov.get("exclusioncount", "?"), ov.get("exclusionamount", "?"), len(eb), eb_amt, len(ea), ea_amt, MIRROR)
open("needs_facesheet_list_section_%s.md" % S, "w").write(sec.strip() + "\n")
if "--final" in sys.argv:
    txt = open("needs_facesheet_list.md").read()
    marker = "## %s columns run (ehpa cloud Code Routine, run %s)" % (SLOT, S)
    if marker in txt:
        txt = txt[:txt.index(marker)].rstrip() + "\n\n" + sec.strip() + "\n"
    else:
        txt = txt.rstrip() + "\n\n" + sec.strip() + "\n"
    open("needs_facesheet_list.md", "w").write(txt)
# ---------------- additions file (behaviours only)
adds = """# captured_calls additions - run %s (7am ET 9/25/2026, ehpa cloud Code Routine)
No new call shape this run. Behaviours confirmed:
- getclaimcenteroverview at 11:2xZ: chargereview 0 / inspector 20 ($3,846) / unbilled 26 ($5,252) / exclusions 8 ($1,268 - the overview count lags; getclaimexclusioncharges per run lists 2) / claimrunstatus 83 runs; newest claim run still 1700236 - the four list calls returned exactly the 0910Z rows.
- GET /api/era/checks answered an empty list before and after (ERA Center empty since the 0910Z run cleared 1052840/1052841); POST /api/era/locks/release-expired accepted on an empty Center.
- payreasons.py --list on an Unbilled list with no 'Payment reason codes' rows prints 0 rows / SUMMARY {} and makes no write.
""" % S
open("captured_calls_additions_2026-09-25_1110UTC-7amET-ehpa-cloud.md", "w").write(adds)
# ---------------- digest
dig = """# %s run digest - backend billing run, 7 AM ET 9/25 slot (ehpa cloud)

- Bootstrap: repo ATTACHED (origin/main b4b4cf3; session branch claude/pensive-einstein-rd4de3; main checked out in the session clone, symlinked as /home/claude/effinger-billing-backend); net AMD_OK, STEDI_CRED_OK, GitHub reachable; AMD password from Gregg's thread 1866ce7e2233e4c0; ONE amd.login_cached success; no login lock; START marker 11:12Z. Layout from main (645 helpers, 365 registers); pseudonyms (314 names), precheck cache, laterality log from 'workspace mirror'; needs list rebuilt from the 70 run sections in nightly/runs. Missing helpers: era_details_pull.py, columns_inspector2_0908.py (not rewritten). State bundle restored: none (newest Drive bundle 2026-09-18_1123UTC is older than main). GITHUB INBOX: no unapplied PACKAGE_* manifest.
- Sources: Working Denials queue 0; Insurance board 0 new drops, 0 rows changed since 06:30Z, inbox registry lists none of the current inbox files - nothing trashed; Pam Gmail: nothing newer than the 02:41Z 9/24 Sodalis admit (worked); Drive: era downloads / treasury / facesheet folders / Claimocity drop unchanged (nothing after 12:00Z 9/24 but the routine's own files); no ScanSnap batch.
- Columns: Charge Review 0 -> 0 | Claim Inspector %d -> %d | Unbilled %s -> %s ($%s) | Exclusions %d -> %d. NOTHING NEW in the four columns since the 0910Z run: no claim run newer than 1700236, every row a standing hold - no column write this run. $0 re-sent.
- ERA: %d unposted checks / $%.2f -> %d / $%.2f - Center empty before and after; locks released; no new 835; auto-posted $0, manual-posted 0, write-offs $0, residual disregarded $0, checks cleared 0. Availity 5(g): no new files. payreasons --list 0 rows.
- Board: board_updates_%s.json (appends only, on aet12-carrier-cpid, availity-remits-backlog, bcbs-patient-balance-audit-0918; no new rows) -> board inbox; inbox registry lists none of the current inbox files - nothing trashed; denials inbox: nothing queued, no file.
- Waiting on William (unchanged from 0910Z 9/25): copeland-jules-17476021 (current Medicare MBI), osgood-maryann-17477870 (merge the duplicate chart), whitlow-shay-17477639 facesheet, jarvis-marisa-17477842 duplicate chart, griffith-jace-17477850 CHP member id, whitfield-rowan-17473232 + penhale-rupert-17471681 CCM after death, alcott-alfie-17477183 facesheet, thackeray-kendrew-17472874 HCA admission date, AET12 carrier master, Florida Blue / VA CCN ERA setup, deistchle 8/22 CCM CO-151, centene-m56-denials-0920, Optum Pay remits to download, prompt v8 + v9 insert not yet pasted into the routine (this run still fired with the v7 text; v8's payreasons rules were applied where they arose - none did).
- Calls learned: no new call shape (captured_calls_additions_2026-09-25_1110UTC-7amET-ehpa-cloud.md, behaviours only). Vocabulary entries added: 0.
- Mirror: %s
- Script errors: none.

RUN COMPLETE
""" % (S, insp_b, insp_a, ub_b, ub_a, sb.get("unbilled_totalamount", "?"), ex_b, ex_a, len(eb), eb_amt, len(ea), ea_amt, S, MIRROR)
os.makedirs("chat_history", exist_ok=True)
open("chat_history/%s run digest.md" % S, "w").write(dig)
print("wrote", csvname, "board ops", len(ops), "digest", "chat_history/%s run digest.md" % S)
