# PLAIN ENGLISH (run outputs for the 3 PM ET 10/20/2026 slot - ehpa cloud run 2026-10-20T1910Z)
# Decides: nothing. Reads this run's Billing Button engine report (reports/button/<engine stamp>.json), the ERA list
# registers, the sweep register and the pending-admit lookup register, then writes the run report CSV, the
# needs_facesheet_list.md section (+ a Drive copy), the board_updates inbox file (append-only checks on the standing rows),
# the captured_calls additions file, one SHARED_LESSONS line and the chat-history digest.
# Never touches: AMD, the board database. Usage: python3 run_outputs_1020_1910.py <engine stamp> <github slot run number>
import csv, json, datetime, collections, sys, glob
S = "2026-10-20T1910Z"; ES = sys.argv[1]; SLOT = sys.argv[2] if len(sys.argv) > 2 else "?"
SRC = "3pm ET 10/20 columns run (ehpa cloud) - run %s" % S; W = "10/20"
NOW = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
REPO = "/home/claude/effinger-billing-backend"
rep = json.load(open("%s/reports/button/%s.json" % (REPO, ES)))
sm = rep["summary"]; cb = sm["columns"]["before"]; ca = sm["columns"]["after"]
cols = "%d/%d/%d/%d -> %d/%d/%d/%d" % (cb["charge_review"], cb["claim_inspector"], cb["unbilled"], cb["exclusions"],
                                        ca["charge_review"], ca["claim_inspector"], ca["unbilled"], ca["exclusions"])
eb = (sm["era"]["before"]["checks"], float(sm["era"]["before"].get("unposted") or 0))
ea = (sm["era"]["after"]["checks"], float(sm["era"]["after"].get("unposted") or 0))
posted = sm.get("posted", {}); resent = sm.get("resent", {}); wo = sm.get("written_off", {}); pk = sm.get("packages", {})
steps = {s.get("id") or s.get("name"): s for s in rep.get("steps", [])}
sweep_sum = str(steps.get("sweep", {}).get("summary", ""))
errors = rep.get("errors", []) + [e for s in rep.get("steps", []) for e in s.get("errors", [])]
swf = sorted(glob.glob("registers/uni20_bcbs_pre0501_sweep_%s*.json" % ES[:13]))
sw = json.load(open(swf[-1])) if swf else []
sw = sw.get("rows", []) if isinstance(sw, dict) else sw
byact = collections.Counter(r["action"].split(" - ")[0] for r in sw); asked = len(sw); askamt = sum(float(r.get("balance") or 0) for r in sw)
bychart = collections.defaultdict(lambda: [0, 0.0])
for r in sw:
    k = (r["action"].split(" - ")[0], str(r["patientid"])); bychart[k][0] += 1; bychart[k][1] += float(r.get("balance") or 0)
swtxt = "; ".join("%d %s chart %s ($%.0f)" % (v[0], k[0], k[1], v[1]) for k, v in sorted(bychart.items())) or "nothing asked"
al = json.load(open("registers/admit_lookup_%s.json" % S)); nochart = sum(1 for x in al["lookups"] if not x["charts"])
rows = []
def add(col, state, patient="", dos="", carrier="", err="", action="", check="", visit="", amt=""):
    rows.append({"column": col, "state": state, "patient": patient, "dos": dos, "carrier": carrier, "error": err, "action": action, "check": check, "visit": visit, "amount": amt})
add("charge review", "clear" if ca["charge_review"] == 0 else "remaining", action="%d -> %d visits" % (cb["charge_review"], ca["charge_review"]))
add("claim inspector", "clear" if ca["claim_inspector"] == 0 else "remaining", action="%d -> %d visits" % (cb["claim_inspector"], ca["claim_inspector"]))
for pid, vids in (("17478059", "v19457778 / v19457794"), ("17478063", "v19457783 / v19457797"), ("17478064", "v19457784 / v19457791")):
    add("unbilled", "remaining", "chart %s" % pid, "99223 10/12 + 99232 10/13/2026", "(no plan on chart)", "Insurance order is missing on visit", "held - cascade exhausted 10/15, HCA Florida Capital facesheet (admit 10/12/2026) on William's turn", visit=vids, amt="421.00")
add("exclusions", "remaining", "chart 17470713 (AARP Medigap secondaries)", "4/2026-7/2026", "AAR01", "PA ACK,RETURND AS UNPRCESSBLE CLM - subscriber id not found (claim run 1700302, 25 rows)", "held - AARP Medicare Supplement member number needed (William's turn); not rebilled")
for vid, dos, cpt, fee in (("19431511", "02/03/2026", "99223", "310.00"), ("19435174", "03/08/2026", "99223", "310.00"), ("19435175", "03/09/2026", "99239", "163.00")):
    add("exclusions", "remaining", "chart 17471204", dos, "AET07", "PA ACK RETURND AS UNPRCESSBLE: ENTITY NOT ELIGIBLE FOR BENEFITS FOR SUBMITTED DOS: PATIENT (run 1700311)", "held for William - subscriber relationship (plan entered SELF, spouse is the subscriber per the 9/5 note); subscriber DOB/sex or the Feb 2026 HCA facesheet needed before a resend", visit=vid, amt=fee)
add("exclusions", "remaining", "chart 24750", "09/20/2026", "AET12", "CH FH PREF0288 INVALID PAYER ID/CPID 814723941 + PREF0264 (v19455937, run 1700294)", "held - carrier master (board row aet12-carrier-cpid); not rebilled", visit="19455937", amt="315.00")
add("era", "remaining", "chart 17474741", "09/20/2026", "FLO02", "check 1053220 Medicare 820007360: takeback pair on v19455454 (reversal -85.46 of check 819919368 + CO-236 $0 re-adjudication)", "era_clear HOLDS - takeback posting has no standing rule; William's decision (row [name]-17474741)", check="1053220", visit="19455454", amt="-85.46")
add("era", "summary", action="ERA Center %d checks $%.2f before -> %d checks $%.2f after; auto-posted pay $%.2f / WOINS $%.2f / WOCAID2ND $%.2f / WOLATE $%.2f; nothing uploaded (no new 835); Availity: no new PDF / Check-EFT export; Treasury: nothing new" % (eb + ea + (posted.get("pay", 0), posted.get("woins", 0), posted.get("wocaid2nd", 0), posted.get("wolate", 0))))
for r in sw:
    add("uni20/bcbs pre-5/1 sweep", "sweep", "chart %s" % r.get("patientid"), r.get("dos", ""), r.get("carrier", ""), r.get("action", ""), "277 answer recorded, nothing sent", visit=str(r.get("visitid")), amt=r.get("balance"))
add("pam admits", "waiting", "five pending Pam admits (Tapestry NA 10/15 + re-send 10/16; Brynwood NA 10/15 x2; Brynwood NA 10/19, re-sent 10/20; Center Pointe 10/17, emailed 10/20 17:15Z)", action="lookuppatient 19:2xZ by full name: no AMD chart for any of the five (%d of %d patterns = no chart; the Brynwood readmit chart 17474046 and the Aviata readmit chart 17472553 exist) - waiting on the Claimocity feed (a chart is never created from an email); the admits' insurance is parked on their board rows" % (nochart, len(al["lookups"])))
add("github button", "watch", action="GitHub slot #%s fired 19:24Z (absent at the 19:12 poll, present in-progress at 19:24Z); this run waited for it to complete (19:31Z, success, commit d2f8430) and ran its own engine pass 19:32-19:36Z afterwards - no overlap, no conflicting write" % SLOT)
for e in errors:
    add("engine", "error", action=str(e))
with open("_run report 10-20 1510.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
errtxt = "; ".join(str(e) for e in errors) or "none"
sec = """## %s - backend billing run, 3 PM ET 10/20/2026 slot (ehpa cloud) - 19:10-19:5xZ

Bootstrap: repo ATTACHED (origin/main aa17ad8 at start; session branch claude/pensive-einstein-4cdigi; main checked out; symlinked as /home/claude/effinger-billing-backend; layout 1147 helper files); net AMD_OK / STEDI_CRED_OK / GitHub reachable; AMD password = the AMD_PSW environment credential (read by amd._stored_psw, no credential file written); ONE login 19:22Z (amd.login_cached by columns_scan.py, token reused by era_list.py, the admit lookup and the engine), no lock, no 429. Guard: 1710Z START has its RUN COMPLETE digest (17:42Z), no newer START; own START uploaded 19:21Z, lock written. State bundle: Drive 'workspace mirror' still lists no workspace_state bundle newer than 2026-09-18 - patient_db/ and era_details/ started empty (era_details rebuilt live for the one open check); registers, needs list, laterality log from main. pseudonyms.json: the Drive 10/19 copy (409) + pseudonyms_additions_2026-10-20.json (5) + pseudonyms_additions_2026-10-20_1710Z.json (2) = 415 names in both secrets/ copies, 0 new this run. deceased_cache.json: Drive 10/16 copy merged into the workspace cache before the engine (76 dated); the repo copy kept scrubbed. v12 precondition (seven repo helpers over the workspace, four greps, tf_writeoff_watch.json on main): all pass. Missing required helpers: none (optional absent: era_details_pull.py, columns_inspector2_0908.py, github_sync.py). GitHub Billing Button slot #%s fired 19:24Z (absent at the 19:12 poll) - this run WAITED for it (completed 19:31Z, success, commit d2f8430) and only then ran tools/button/run_all.py --mode live --steps columns,era,sweep,packages --stedi-proxy 19:32-19:36Z (report reports/button/%s.json): no overlap. Permission classifier: no refusal; no AdvancedMD write attempted (nothing to write).

Sources: Insurance Refresh Board (read_db only): rows on Claude's turn re-read (200 returned; no row updated since 14:00Z - no new William note), drops 0. Working Denials queue 0. Mandatory Approvals page 0 approved (A-2026-10-20T1310Z-A still waiting); engine packages step: no approved package in the register. Both drive_sync registries list no current inbox file - nothing trashed. Drive: nothing new in the HCA / TMH / PCC / Claimocity / 835 / treasury folders (no pdf / image / csv / 835 / hl7 modified after 12:00Z outside the routines' own files). Pam Gmail (7d): nine admit emails, all already worked (10/15 x3, 10/16-10/17 Tapestry re-send, 10/17 Aviata readmit chart 17472553, 10/19 + 10/20 Brynwood, 10/20 Brynwood readmit chart 17474046, 10/20 17:15Z Center Pointe); lookuppatient 19:2xZ by full name: still no AMD chart for the five pending admits (registers/admit_lookup_%s.json). SHARED_LESSONS.md: no line newer than this routine's last run from another routine.

Columns (engine columns_scan before -> after) %s:
- CHARGE REVIEW %d -> %d. CLAIM INSPECTOR %d -> %d.
- UNBILLED %d -> %d: the three zero-plan HCA charts 17478059 / 17478063 / 17478064 (99223 10/12 + 99232 10/13/2026, $421 each, $1,263) 'Insurance order is missing' - cascade exhausted 10/15; no facesheet, Pam email or board drop since; rows on William's turn unchanged.
- EXCLUSIONS %d -> %d (overview reads 30, the list calls 29): chart 17470713's 25 AARP Medigap rows on run 1700302 (member number), chart 17471204's three AET07 rows on run 1700311 ($783, subscriber relationship), the AET12 chart-24750 row on run 1700294 - all standing holds; no new claim run since 1700311. Nothing rebilled.
- Dollars re-sent $%.2f (%d visits). Write-offs %d / $%.2f. Packages applied %d / refused %d / skipped %d.

ERA (step 5): (a) nothing to upload (no new 835); (b) GET /api/era/checks = %d check / $%.2f before (19:23Z and 19:35Z: 1053220 Medicare 820007360, unposted -85.46, the takeback pair) and %d check / $%.2f after; (c) era_post --all-unposted: 0 postable (pay $%.2f, WOINS $%.2f, WOCAID2ND $%.2f, WOLATE $%.2f); (d) nothing refused or skipped; (e) 1053220 held by era_clear (takeback pair on chart 17474741 v19455454, William's decision). (g) Availity: no new PDF or Check/EFT export; Treasury nothing new.
UNI20/BCBS pre-5/1 (claim_status_sweep.py via the engine, --skip-answered): %d asked ($%.2f): %s - %s; engine summary: %s; 0 sent, 0 written off.

Waiting on William: takeback decision chart 17474741 v19455454 (ERA 1053220); chart 17471204's three Aetna rejections ($783 - subscriber relationship / Feb 2026 HCA facesheet, row tolland-tracen); HCA Florida Capital facesheets (admit 10/12/2026) for charts 17478059 / 17478063 / 17478064 (6 visits, $1,263); AARP Medicare Supplement member number for chart 17470713 (25 secondary claims); AET12 carrier master (chart 24750); approval A-2026-10-20T1310Z-A (restore the $0 VA CCN remit 1053221); five Pam admits without an AMD chart (10/15 x3, 10/19, 10/17 Center Pointe) - waiting on the Claimocity feed, nothing for William.
Calls used this run outside the engine (all in the registry): getclaimcenteroverview + the four list calls (columns_scan.py), GET /api/era/checks + GET /api/era/checkdetails (era_list.py), lookuppatient x9 (admit_lookup_1020_1910.py). Script errors: %s. Calls learned: 0 new shapes (0 vocabulary entries).
""" % (S, SLOT, ES, S, cols, cb["charge_review"], ca["charge_review"], cb["claim_inspector"], ca["claim_inspector"], cb["unbilled"], ca["unbilled"], cb["exclusions"], ca["exclusions"],
       float(resent.get("dollars", 0)), int(resent.get("visits", 0)), int(wo.get("count", 0)), float(wo.get("dollars", 0)), int(pk.get("applied", 0)), int(pk.get("refused", 0)), int(pk.get("skipped", 0)),
       eb[0], eb[1], ea[0], ea[1], posted.get("pay", 0), posted.get("woins", 0), posted.get("wocaid2nd", 0), posted.get("wolate", 0),
       asked, askamt, dict(byact), swtxt, sweep_sum, errtxt)
open("needs_facesheet_list.md", "a").write("\n" + sec); open("needs_facesheet_list_section_%s.md" % S, "w").write(sec)
chk = lambda txt, ok="na": {"checks": [{"ok": ok, "result": txt, "src": SRC, "when": W}]}
hold = "3 PM ET 10/20: chart %s still 0 insplans; both visits (99223 10/12 + 99232 10/13/2026, $421) still in Unbilled 'Insurance order is missing'; no HCA / TMH / PCC facesheet, Pam email or board drop since 10/15 - your turn unchanged (HCA Florida Capital facesheet, admit 10/12/2026)."
ops = [{"op": "upsert", "collection": "items", "id": "availity-remits-backlog", "append": chk("3 PM ET 10/20: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (no pdf / image / csv / 835 / hl7 modified after 12:00Z outside the routines' own files); no new facesheet or Claimocity file; Working Denials queue 0; board drops 0; approvals 0 approved / 1 waiting (A-2026-10-20T1310Z-A). ERA Center %d check $%.2f before and after (1053220 Medicare takeback pair held for your decision); nothing posted. Columns %s - every row a standing hold, no AMD write this slot. Pam Gmail: nothing newer than the 17:15Z Center Pointe admit (worked 1710Z); lookuppatient 19:2xZ: the five pending admits still have no AMD chart. UNI20/BCBS pre-5/1: %s, 0 sent. GitHub slot #%s ran 19:24-19:31Z; this run waited for it before its own engine pass." % (eb[0], eb[1], cols, swtxt, SLOT))},
       {"op": "upsert", "collection": "items", "id": "aet12-carrier-cpid", "append": chk("3 PM ET 10/20: HOLD - the one AET12 PREF0288 exclusion row (chart 24750, v19455937, run 1700294) stays on the list, not rebilled; carrier master still unchanged; no new claim run since 1700311.")},
       {"op": "upsert", "collection": "items", "id": "mabry-m-digby-delphia-17478059", "append": chk(hold % "17478059", "human")},
       {"op": "upsert", "collection": "items", "id": "gaskell-micah-17478063", "append": chk(hold % "17478063", "human")},
       {"op": "upsert", "collection": "items", "id": "edgerton-jocelyn-17478064", "append": chk(hold % "17478064", "human")},
       {"op": "upsert", "collection": "items", "id": "poulter-ellery-gwen-denials", "append": chk("3 PM ET 10/20: the 25 AARP Medigap rows on claim run 1700302 are still open (no new claim run since 1700311); waiting on the AARP Medicare Supplement member number - not re-sent.")},
       {"op": "upsert", "collection": "items", "id": "tolland-tracen", "append": chk("3 PM ET 10/20: the three AET07 rejections of run 1700311 (v19431511 / v19435174 / v19435175, $783) still on the exclusion list, not re-sent - waiting on the subscriber's DOB/sex (or the Feb 2026 HCA facesheet) to re-enter the Aetna plan as spouse.", "human")},
       {"op": "upsert", "collection": "items", "id": "[name]-17474741", "append": chk("3 PM ET 10/20: ERA check 1053220 (Medicare 820007360) still holds only the takeback pair on v19455454 (reversal -85.46 of check 819919368 + CO-236 $0 re-adjudication); era_clear holds it - takeback posting has no standing rule; your decision.")},
       {"op": "upsert", "collection": "items", "id": "dunwoody-laurel-admit-1016", "append": chk("3 PM ET 10/20: lookuppatient 19:2xZ by full name - still no AMD chart (nor for the three 10/15 admits); the insurance recorded on this row is applied the day the Claimocity feed delivers the chart.")},
       {"op": "upsert", "collection": "items", "id": "smith-baker-esme-admit-1017", "append": chk("3 PM ET 10/20: lookuppatient 19:2xZ under both name spellings - still no AMD chart (the different-DOB namesake pat25746 excluded); insurance stays parked on this row until the Claimocity feed delivers the chart.")}]
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
open("captured_calls_additions_2026-10-20_1910UTC-3pmET-ehpa-cloud.md", "w").write("""## 2026-10-20 19:10Z - backend billing run, 3 PM ET 10/20/2026 (ehpa cloud, repo attached)
No new call shapes this run. The columns, ERA, sweep and packages steps ran through the repository's Billing Button engine (tools/button/run_all.py --mode live --steps columns,era,sweep,packages --stedi-proxy) from the routine's own container AFTER the scheduled GitHub slot (run #%s, 19:24-19:31Z) had completed - one login (amd.login_cached 19:22Z by columns_scan.py, no lock, no 429). Calls used (all already in the registry): login, getclaimcenteroverview + getreviewcharges / getclaiminspectorbatches / getclaimunbillablecharges / getclaimexclusionclaimruns + getclaimexclusioncharges (columns_scan.py), GET /api/era/checks + GET /api/era/checkdetails (era_list.py), lookuppatient class=lookup x9 (admit_lookup_1020_1910.py), Stedi 276/277 (claim_status_sweep.py). Engine report reports/button/%s.json.
Lesson (GitHub button cadence, applied): the :17 cron slot was absent from the runs list at 19:12Z and present in-progress at 19:24Z; polling GET /repos/.../actions/runs/<id> every 20 s until status=completed (19:31:47Z) and running the engine afterwards avoided the overlap recorded at 17:26Z.
""" % (SLOT, ES))
lessons = ["- %s | backend billing run | WATCH | columns %s (standing holds: three zero-plan HCA charts 17478059/17478063/17478064, chart 17470713 AARP x25, chart 17471204 AET07 x3, AET12 chart 24750); ERA 1 check (-$85.46, the 1053220 takeback pair) held for William before and after; nothing posted, no AMD write; UNI20/BCBS pre-5/1: %s, 0 sent; the five Pam admits (10/15 x3, 10/19, 10/17 Center Pointe) still have no AMD chart; GitHub slot #%s (19:24-19:31Z) was waited for before this run's engine pass (19:32-19:36Z) - no overlap, which is the fix for the 17:26Z TRAP | reports/button/%s.json" % (NOW, cols, swtxt, SLOT, ES)]
open("%s/docs/SHARED_LESSONS.md" % REPO, "a").write("\n".join(lessons) + "\n")
dig = """# %s run digest - backend billing run, 3 PM ET 10/20/2026 (ehpa cloud, repo attached)

## Bootstrap
- Repo attached: main aa17ad8 at start (session branch claude/pensive-einstein-4cdigi; main checked out; /home/claude/effinger-billing-backend symlinked). Network: AMD OK, Stedi proxy credential OK (no key file), GitHub attached. AMD password: the AMD_PSW environment credential (read at login, no credential file written, never printed). One login 19:22Z (amd.login_cached by columns_scan.py; era_list.py, the admit lookup and the engine reused the token), no lock, no 429.
- State bundle: Drive 'workspace mirror' still lists nothing newer than workspace_state_2026-09-18 - superseded by main, not restored (patient_db/ and era_details/ started empty; era_details rebuilt live for the one open check). Workspace laid out from main: 1147 helper files; required helpers all present (optional absent: era_details_pull.py, columns_inspector2_0908.py, github_sync.py). pseudonyms.json: Drive 10/19 copy (409) + the two additions files (5 + 2) = 415 names in both secrets/ copies, nothing new this run. deceased_cache.json: Drive 10/16 copy merged into the workspace cache before the engine (76 dated); the repo copy kept PHI-scrubbed (reverted after dg_drive's merge).
- v12 precondition (seven repo helpers over the workspace, four greps, tf_writeoff_watch.json on main): all pass. Prompt fired as the v7 text; the v12 text + v13 insert on main (nightly/) applied as on every run since 10/6. Learned from others: git log 36h = this routine + the GitHub Billing Button slots only; SHARED_LESSONS lines newer than 17:38Z: none from another routine; 0 applied.
- Guard: 1710Z START has its RUN COMPLETE digest (17:42Z); START 1910Z uploaded 19:21Z, lock written, deleted at the end. The GitHub Billing Button slot #%s fired at 19:24Z (absent at the 19:12 poll, in progress at 19:24Z): this run polled the run until it completed (19:31:47Z, success, commit d2f8430) and only then ran tools/button/run_all.py --mode live --steps columns,era,sweep,packages --stedi-proxy (19:32-19:36Z, report reports/button/%s.json) - no overlap, no double write.
- Permission classifier: no refusal. No AdvancedMD write was attempted (nothing to write).

## Sources read
- Insurance Refresh Board (read_db only): rows on Claude's turn re-read (no row updated since 14:00Z, no new William note), drops 0. Working Denials queue 0. Mandatory Approvals page: 0 approved / 1 waiting (A-2026-10-20T1310Z-A, the $0 VA CCN remit 1053221 restore - not re-attempted, 0h rule); engine packages step: no approved package in the register. Both drive_sync registries: no current inbox file in the applied maps - nothing trashed.
- Drive: 'bht Optum era downloads', 'treasury payments', the facesheet folders, the Claimocity drop and 'github mirror' hold nothing new since the 1710Z run (no pdf / image / csv / 835 / hl7 modified after 12:00Z outside the routines' own files); the two GitHub PACKAGE manifests 2026-10-11 / 2026-10-12 still on 'github mirror' - not retried. Pam Gmail (7d): nine admit emails, all already worked; nothing newer than the 17:15Z Center Pointe admit. lookuppatient 19:2xZ by full name: the five pending admits (10/15 x3, 10/19 Brynwood, 10/17 Center Pointe) still have no AMD chart; the Brynwood readmit (chart 17474046) and the Aviata readmit (chart 17472553) exist (registers/admit_lookup_%s.json).

## Columns (list calls) %s
- Charge Review %d -> %d. Claim Inspector %d -> %d (no batch).
- Unbilled %d -> %d ($1,263): the three zero-plan HCA charts 17478059 / 17478063 / 17478064 on William's turn (HCA Florida Capital facesheets, admit 10/12/2026); live scan 19:22Z and 19:33Z: still 0 insplans on all three.
- Exclusions %d -> %d (overview reads 30, the list calls 29): the 25 AAR01 rows of chart 17470713 on run 1700302 (AARP supplement member number), chart 17471204's three AET07 rows on run 1700311 (subscriber relationship, $783) and the AET12 chart-24750 PREF0288 hold on run 1700294 - unchanged, nothing rebilled. No new claim run since 1700311.
- Dollars re-sent $%.2f (%d visits). Write-offs %d / $%.2f. Packages applied %d / refused %d / skipped %d.

## ERA Center - %d check $%.2f before -> %d check $%.2f after
- 1053220 Medicare 820007360 (unposted -85.46): only the takeback pair on chart 17474741 v19455454 (reversal -85.46 of check 819919368 + CO-236 $0 re-adjudication) - era_clear HOLDS it; takeback posting has no standing rule; William's decision on row [name]-17474741. Nothing to upload (no new 835 / Availity PDF / Check-EFT export); era_post --all-unposted: 0 postable (pay $%.2f, WOINS $%.2f, WOCAID2ND $%.2f, WOLATE $%.2f).
- Auto-posted $0; manual-posted 0 lines; residuals disregarded $0; checks cleared 0; still open 1 (1053220, held). Availity 5(g) and Treasury: nothing new. Calls learned: none (0 vocabulary entries).
- UNI20/BCBS pre-5/1 (engine sweep step, --min-age 172 --max 60 --carriers UNI20,BCBS --skip-answered): %d asked ($%.2f): %s; engine summary: %s; 0 candidates, 0 sent, 0 written off.

## Script errors
- %s

## Waiting on William
- Takeback decision: chart 17474741 v19455454 9/20/2026 99233 (row [name]-17474741); ERA check 1053220 held until then.
- Approval A-2026-10-20T1310Z-A - restore the dismissed $0 VA CCN remit 1053221 so its denial lines can be cached and worked ($0.00), or restore it yourself in the ERA Center (Dismissed > Restore).
- HCA Florida Capital facesheets (admit 10/12/2026) for charts 17478059 / 17478063 / 17478064 (6 visits, $1,263).
- Chart 17471204: three Aetna AET07 claims ($783) - subscriber relationship / Feb 2026 HCA facesheet. AARP Medicare Supplement member number for chart 17470713 (25 secondary claims on run 1700302). AET12 carrier master (chart 24750).
- GitHub packages 2026-10-11 / 2026-10-12 on Drive 'github mirror' - not retried.
- Five Pam admits without an AMD chart (10/15 x3, 10/19 Brynwood, 10/17 Center Pointe) - waiting on the Claimocity feed, nothing for William.

## Mirror
- MIRROR_PLACEHOLDER

## SHARED LESSONS
%s

RUN COMPLETE
""" % (S, SLOT, ES, S, cols, cb["charge_review"], ca["charge_review"], cb["claim_inspector"], ca["claim_inspector"], cb["unbilled"], ca["unbilled"], cb["exclusions"], ca["exclusions"],
       float(resent.get("dollars", 0)), int(resent.get("visits", 0)), int(wo.get("count", 0)), float(wo.get("dollars", 0)), int(pk.get("applied", 0)), int(pk.get("refused", 0)), int(pk.get("skipped", 0)),
       eb[0], eb[1], ea[0], ea[1], posted.get("pay", 0), posted.get("woins", 0), posted.get("wocaid2nd", 0), posted.get("wolate", 0),
       asked, askamt, swtxt, sweep_sum, errtxt, "\n".join(lessons))
import os; os.makedirs("chat_history", exist_ok=True)
open("chat_history/%s run digest.md" % S, "w").write(dig)
print("outputs written:", len(rows), "report rows;", len(ops), "board ops;", asked, "sweep rows;", nochart, "admits without chart")
