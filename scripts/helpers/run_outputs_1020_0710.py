# PLAIN ENGLISH (run outputs for the 3 AM ET 10/20/2026 slot - ehpa cloud run 2026-10-20T0710Z)
# Decides: nothing. Reads this run's Billing Button engine report (reports/button/<engine stamp>.json: column counts before/after,
# ERA Center counts, posted / resent / written-off dollars, the sweep summary), the sweep register and the pending-admit
# lookup register, then writes the run report CSV, the needs_facesheet_list.md section (+ a copy for Drive), the board_updates
# inbox file (append-only checks on the standing rows), the captured_calls additions file and the chat-history digest.
# Never touches: AMD, the board database. Usage: python3 run_outputs_1020_0710.py <engine stamp> [<slot run number>]
import csv, json, datetime, collections, os, sys, glob
S = "2026-10-20T0710Z"; ES = sys.argv[1]; SLOT = sys.argv[2] if len(sys.argv) > 2 else "?"
SRC = "3am ET 10/20 columns run (ehpa cloud) - run %s" % S; W = "10/20"
NOW = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
REPO = "/home/claude/effinger-billing-backend"
rep = json.load(open("%s/reports/button/%s.json" % (REPO, ES)))
sm = rep["summary"]; cb = sm["columns"]["before"]; ca = sm["columns"]["after"]
cols = "%d/%d/%d/%d -> %d/%d/%d/%d" % (cb["charge_review"], cb["claim_inspector"], cb["unbilled"], cb["exclusions"],
                                        ca["charge_review"], ca["claim_inspector"], ca["unbilled"], ca["exclusions"])
eb = (sm["era"]["before"]["checks"], float(sm["era"]["before"].get("unposted") or 0)); ea = (sm["era"]["after"]["checks"], float(sm["era"]["after"].get("unposted") or 0))
posted = sm.get("posted", {}); resent = sm.get("resent", {}); wo = sm.get("written_off", {}); pk = sm.get("packages", {})
steps = {s.get("id") or s.get("name"): s for s in rep.get("steps", [])}
sweep_sum = str(steps.get("sweep", {}).get("summary", ""))
errors = rep.get("errors", []); waiting = rep.get("waiting", [])
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
    add("exclusions", "remaining", "chart 17471204", dos, "AET07", "PA ACK RETURND AS UNPRCESSBLE: ENTITY NOT ELIGIBLE FOR BENEFITS FOR SUBMITTED DOS: PATIENT (run 1700311)", "held for William since the 0510Z run - every eligibility source says Aetna ACTIVE from 1/1/2026 under this member id; the plan is entered relationship SELF while the spouse is the subscriber - subscriber DOB/sex (or the Feb 2026 HCA facesheet) needed before a resend", visit=vid, amt=fee)
add("exclusions", "remaining", "chart 24750", "09/20/2026", "AET12", "CH FH PREF0288 INVALID PAYER ID/CPID 814723941 + PREF0264 (v19455937, run 1700294)", "held - carrier master (board row aet12-carrier-cpid); not rebilled", visit="19455937", amt="315.00")
add("era", "clear" if ea[0] == 0 else "remaining", action="ERA Center %d checks $%.2f before -> %d checks $%.2f after; auto-posted pay $%.2f / WOINS $%.2f / WOCAID2ND $%.2f / WOLATE $%.2f; nothing uploaded (no new 835); Availity: no new PDF / Check-EFT export; Treasury: nothing new" % (eb + ea + (posted.get("pay", 0), posted.get("woins", 0), posted.get("wocaid2nd", 0), posted.get("wolate", 0))))
for r in sw:
    add("uni20/bcbs pre-5/1 sweep", "sweep", "chart %s" % r.get("patientid"), r.get("dos", ""), r.get("carrier", ""), r.get("action", ""), "277 answer recorded, nothing sent", visit=str(r.get("visitid")), amt=r.get("balance"))
add("pam admits", "waiting", "four Pam admits (Tapestry NA 10/15; Brynwood NA 10/15 x2; Brynwood NA 10/16)", action="lookuppatient 07:22Z by full name: no AMD chart for any of the four (%d of %d patterns = no chart) - waiting on the Claimocity feed (a chart is never created from an email); the 10/16 admit's insurance is parked on its board row" % (nochart, len(al["lookups"])))
add("github button", "note", action="scheduled cascade slot #109 (05:43-05:52Z, live) ran its engine but its 'Commit the report to main' step failed on a rebase conflict in reports/button/latest.json (the 0510Z routine push landed first); the aging report of that slot was not committed - the next cascade slot (05:35Z 10/21) rewrites it; columns slot #110 (07:32-07:38Z) committed normally")
for e in errors:
    add("engine", "error", action=str(e))
with open("_run report 10-20 0310.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
errtxt = "; ".join(str(e) for e in errors) or "none"
sec = """## %s - backend billing run, 3 AM ET 10/20/2026 slot (ehpa cloud) - 07:10-07:5xZ

Bootstrap: repo ATTACHED (origin/main 1c96fff at start, 6f03cef after the button slot; session branch claude/pensive-einstein-psgl0t; main checked out; symlinked as /home/claude/effinger-billing-backend; layout 1136 helper files); net AMD_OK / STEDI_CRED_OK / GitHub reachable; AMD password = the AMD_PSW environment credential (no credential file); ONE login 07:22Z (amd.login_cached by admit_lookup_1020_0710.py, token reused by the engine), no lock, no 429. Guard: 0510Z START has its RUN COMPLETE digest (05:52Z), no newer START; own START uploaded 07:12Z, lock written. State bundle: Drive 'workspace mirror' still lists no workspace_state bundle newer than 2026-09-18 - patient_db/ and era_details/ started empty; registers, needs list, laterality log from main. pseudonyms.json: the Drive copy (409 names, 10/19 19:37Z) landed COMPLETE this run and the 10/20 additions (4 new names) were merged -> 413 names in both secrets/ copies; re-uploaded to 'workspace mirror'. deceased_cache.json: Drive copy (10/16, 38 dated + 253 no-death) merged into the WORKSPACE cache (76 dated entries); the repo copy stays scrubbed (the engine bootstrap re-lays it over the workspace copy - re-unpacked after the engine as the 10/19 TRAP says). Missing required helpers: none (optional absent: era_details_pull.py, columns_inspector2_0908.py, github_sync.py). The GitHub Billing Button slot #%s (07:32-07:38Z) was allowed to finish first; this run's engine pass (tools/button/run_all.py --mode live --steps columns,era,sweep,packages --stedi-proxy) followed 07:38-07:42Z - report reports/button/%s.json. NOTE: the scheduled cascade slot #109 (05:43-05:52Z) ran its engine but failed at 'Commit the report to main' (rebase conflict in reports/button/latest.json with the 0510Z routine push) - its aging report was not committed; nothing in AMD affected.

Sources: Insurance Refresh Board (read_db only): rows changed since 05:00Z 0 (no new William note), drops 0. Working Denials queue 0. Mandatory Approvals page 0 approved; register 92 items all done. Both drive_sync registries list no current inbox file - nothing trashed. Drive: nothing new in the HCA / TMH / PCC / Claimocity / 835 / treasury folders (only the routine's own 2310Z report CSV since 10/19). Pam Gmail (7 days): Flintham (Tapestry 10/15), Jenner + Beardsley (Brynwood 10/15), Dunwoody (Brynwood 10/16, re-sent 10/19) and the Hesketh 10/17 readmit (worked earlier); lookuppatient 07:22Z by full name: the four pending admits still have no AMD chart (registers/admit_lookup_%s.json). SHARED_LESSONS.md: no line newer than this routine's last run from another routine (learned from others: 0 applied).

Columns (engine columns_scan before -> after) %s:
- CHARGE REVIEW %d -> %d. CLAIM INSPECTOR %d -> %d.
- UNBILLED %d -> %d: the three zero-plan HCA charts 17478059 / 17478063 / 17478064 (99223 10/12 + 99232 10/13/2026, $421 each, $1,263) 'Insurance order is missing' - cascade exhausted 10/15; no HCA / TMH / PCC facesheet, Pam email or board drop since; rows on William's turn unchanged.
- EXCLUSIONS %d -> %d (list rows, re-listed before acting): chart 17470713's 25 AARP Medigap rows on run 1700302 (member number - William), chart 17471204's three AET07 'entity not eligible for DOS: patient' rows on run 1700311 ($783 - subscriber relationship, William's turn since 0510Z), the AET12 chart-24750 row on run 1700294 (carrier master). No new claim run since 1700311. Nothing rebilled, nothing completed.
- Dollars re-sent $%.2f (%d visits). Write-offs %d / $%.2f. Packages applied %d / refused %d / skipped %d.

ERA (step 5): (a) nothing to upload (no new 835); (b) GET /api/era/checks = %d checks / $%.2f before and %d checks / $%.2f after; (c) era_post --all-unposted: pay $%.2f, WOINS $%.2f, WOCAID2ND $%.2f, WOLATE $%.2f; (d)-(e) nothing to post or clear. (g) Availity: no new PDF or Check/EFT export; Treasury nothing new.
UNI20/BCBS pre-5/1 (claim_status_sweep.py via the engine, --min-age 172 --skip-answered): %d asked ($%.2f): %s - %s; engine summary: %s; 0 sent, 0 written off.

Waiting on William: chart 17471204's three Aetna rejections ($783 - subscriber relationship / HCA facesheet); HCA Florida Capital facesheets (admit 10/12/2026) for charts 17478059 / 17478063 / 17478064 (6 visits, $1,263); AARP Medicare Supplement member number for chart 17470713 (25 secondary claims); AET12 carrier master (chart 24750); four Pam admits (10/15 x3, 10/16 x1) without an AMD chart (nothing for William - waiting on the Claimocity feed); the standing items of earlier digests unchanged.
Writes in AdvancedMD: none outside the engine (engine: 0 writes - every column row a standing hold). Calls used (all in the registry): login, lookuppatient, getclaimcenteroverview, getreviewcharges, getclaiminspectorbatches, getclaimunbillablecharges, getclaimexclusionclaimruns / getclaimexclusioncharges, GET /api/era/checks, Stedi 276/277. Script errors: %s. Calls learned: 0 new shapes (0 vocabulary entries).
""" % (S, SLOT, ES, S, cols, cb["charge_review"], ca["charge_review"], cb["claim_inspector"], ca["claim_inspector"], cb["unbilled"], ca["unbilled"], cb["exclusions"], ca["exclusions"],
       float(resent.get("dollars", 0)), int(resent.get("visits", 0)), int(wo.get("count", 0)), float(wo.get("dollars", 0)), int(pk.get("applied", 0)), int(pk.get("refused", 0)), int(pk.get("skipped", 0)),
       eb[0], eb[1], ea[0], ea[1], posted.get("pay", 0), posted.get("woins", 0), posted.get("wocaid2nd", 0), posted.get("wolate", 0),
       asked, askamt, dict(byact), swtxt, sweep_sum, errtxt)
open("needs_facesheet_list.md", "a").write("\n" + sec); open("needs_facesheet_list_section_%s.md" % S, "w").write(sec)
chk = lambda txt, ok="na": {"checks": [{"ok": ok, "result": txt, "src": SRC, "when": W}]}
hold = "3 AM ET 10/20: chart %s still 0 insplans; both visits (99223 10/12 + 99232 10/13/2026, $421) still in Unbilled 'Insurance order is missing'; no HCA / TMH / PCC facesheet, Pam email or board drop since 10/15 - your turn unchanged (HCA Florida Capital facesheet, admit 10/12/2026)."
ops = [{"op": "update", "collection": "items", "id": "availity-remits-backlog", "append": chk("3 AM ET 10/20: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (nothing new in the watched folders since 10/19 outside the routine's own files); no new 835, facesheet or Claimocity file; Working Denials queue 0; board drops 0; approvals 0 approved / 0 waiting; Pam Gmail: nothing newer than the 10/19 18:00Z Brynwood admit (recorded 1910Z). ERA Center %d checks $%.2f -> %d checks $%.2f. Columns %s - every row a standing hold (charts 17478059 / 17478063 / 17478064 zero plans; chart 17470713's 25 AARP secondaries on run 1700302; chart 17471204's 3 Aetna rows on run 1700311; AET12 chart 24750). UNI20/BCBS pre-5/1: %s, 0 sent." % (eb[0], eb[1], ea[0], ea[1], cols, swtxt))},
       {"op": "update", "collection": "items", "id": "aet12-carrier-cpid", "append": chk("3 AM ET 10/20: HOLD - the one AET12 PREF0288 exclusion row (chart 24750, v19455937, run 1700294) stays on the list, not rebilled; carrier master still unchanged.")},
       {"op": "update", "collection": "items", "id": "mabry-m-digby-delphia-17478059", "append": chk(hold % "17478059")},
       {"op": "update", "collection": "items", "id": "gaskell-micah-17478063", "append": chk(hold % "17478063")},
       {"op": "update", "collection": "items", "id": "edgerton-jocelyn-17478064", "append": chk(hold % "17478064")}]
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
open("captured_calls_additions_2026-10-20_0710UTC-3amET-ehpa-cloud.md", "w").write("""## 2026-10-20 07:10Z - backend billing run, 3 AM ET 10/20/2026 (ehpa cloud, repo attached)
No new call shapes this run. The columns, ERA, sweep and packages steps ran through the repository's Billing Button engine (tools/button/run_all.py --mode live --steps columns,era,sweep,packages --stedi-proxy) from the routine's own container after the scheduled GitHub slot (run #%s, 07:32-07:38Z) had finished - one login (amd.login_cached 07:22Z by admit_lookup_1020_0710.py, no lock, no 429). Calls used (all already in the registry): login, lookuppatient (four pending Pam admits), getclaimcenteroverview, getreviewcharges, getclaiminspectorbatches, getclaimunbillablecharges, getclaimexclusionclaimruns / getclaimexclusioncharges (columns_scan.py), GET /api/era/checks (era_list.py), Stedi 276/277 (claim_status_sweep.py). No AdvancedMD write this run. Engine report reports/button/%s.json.
""" % (SLOT, ES))
dig = """# %s run digest - backend billing run, 3 AM ET 10/20/2026 (ehpa cloud, repo attached)

## Bootstrap
- Repo attached: main 1c96fff at start, 6f03cef after the button slot (session branch claude/pensive-einstein-psgl0t; main checked out; /home/claude/effinger-billing-backend symlinked). Network: AMD OK, Stedi proxy credential OK (no key file), GitHub attached. AMD password: the AMD_PSW environment credential (no credential file). One login 07:22Z (amd.login_cached by admit_lookup_1020_0710.py; the engine reused the token), no lock, no 429.
- State bundle: Drive 'workspace mirror' still lists nothing newer than workspace_state_2026-09-18 - superseded by main, not restored (patient_db/ and era_details/ started empty). Workspace laid out from main: 1136 helper files; required helpers all present (optional absent: era_details_pull.py, columns_inspector2_0908.py, github_sync.py). pseudonyms.json landed COMPLETE this run (409 names from Drive + the 4 new names of pseudonyms_additions_2026-10-20.json = 413) and was re-uploaded to 'workspace mirror'. deceased_cache.json: Drive 10/16 copy merged into the workspace cache (76 dated entries); the repo copy stays scrubbed; re-unpacked after the engine bootstrap (10/19 TRAP).
- Prompt fired as the v7 text; the v12 text + v13 insert on main (nightly/) applied as on every run since 10/6.
- Guard: 0510Z START has its RUN COMPLETE digest (05:52Z); START 0710Z uploaded 07:12Z, lock written, deleted at the end. The scheduled GitHub Billing Button slot (run #%s, columns profile live, 07:32-07:38Z, columns 0/0/6/29 unchanged) was allowed to finish FIRST; this run's engine pass (tools/button/run_all.py --mode live --steps columns,era,sweep,packages --stedi-proxy) ran in this container 07:38-07:42Z; report reports/button/%s.json. No permission refusal. No AdvancedMD write by this run (every column row a standing hold).
- GitHub button slot #109 (scheduled CASCADE profile, live, 05:43-05:52Z): engine step succeeded, 'Commit the report to main' FAILED - rebase conflict in reports/button/latest.json against the 0510Z routine push (05:47Z); its aging report was lost (not committed). Nothing in AMD affected; the 05:35Z 10/21 cascade slot rewrites it. WATCH: the cascade slot and this routine's 1 AM slot both push to main within the same ten minutes.

## Sources read
- Insurance Refresh Board (read_db only): rows changed since 05:00Z 0 (no new William note), drops 0. Working Denials queue 0. Mandatory Approvals page 0 approved; register 92 items all done. Both drive_sync registries: no current inbox file in the applied maps - nothing trashed.
- Drive: 'bht Optum era downloads', 'treasury payments', the three facesheet folders and the Claimocity drop hold nothing new since 10/19 (only the routine's own 2310Z report CSV); no 835, Availity PDF, Check/EFT export, facesheet or Claimocity file. Pam Gmail (7d): Flintham 10/15 (Tapestry), Jenner + Beardsley 10/15 (Brynwood), Dunwoody 10/16 (Brynwood, email 10/19 18:00Z), Hesketh 10/17 readmit (worked 10/17); lookuppatient 07:22Z by full name - the four pending admits still have no AMD chart (registers/admit_lookup_%s.json). SHARED_LESSONS.md: no line newer than this routine's last run from another routine (learned from others: 0 applied; shared: 1).

## Columns (list calls) %s
- Charge Review %d -> %d. Claim Inspector %d -> %d.
- Unbilled %d -> %d: the three zero-plan HCA charts 17478059 / 17478063 / 17478064 on William's turn (HCA Florida Capital facesheets admit 10/12/2026, 6 visits $1,263).
- Exclusions %d -> %d: chart 17470713's 25 AARP Medigap rows (run 1700302, member number), chart 17471204's three AET07 rows (run 1700311, $783, subscriber relationship - William's turn since 0510Z), the AET12 chart-24750 row (run 1700294, carrier master). No new claim run since 1700311. Nothing rebilled or completed.
- Dollars re-sent $%.2f (%d visits). Write-offs %d / $%.2f. Packages applied %d / refused %d / skipped %d.

## ERA Center - %d checks $%.2f before -> %d checks $%.2f after
- Nothing to upload (no new 835 / Availity PDF / Check-EFT export); era_post --all-unposted: pay $%.2f, WOINS $%.2f, WOCAID2ND $%.2f, WOLATE $%.2f; nothing to clear; manual-posted lines 0; residual disregarded $0; checks cleared 0. Availity 5(g) and Treasury: nothing new. Calls learned: none (0 vocabulary entries).
- UNI20/BCBS pre-5/1 (engine sweep step, --min-age 172 --skip-answered with the earlier registers): %d asked ($%.2f): %s; engine summary: %s; 0 candidates, 0 sent, 0 written off.

## Script errors
- %s

## Waiting on William
- HCA Florida Capital facesheets (admit 10/12/2026) for charts 17478059 / 17478063 / 17478064 (6 visits, $1,263).
- Chart 17471204: three Aetna AET07 claims (2/3, 3/8, 3/9/2026, $783) rejected 'entity not eligible for benefits for submitted DOS: patient' on run 1700311 although Stedi 60054 + AMD 271 show Aetna ACTIVE from 1/1/2026 under this member id - the plan is entered relationship SELF while the spouse is the subscriber: the subscriber's DOB/sex (or the Feb 2026 HCA facesheet) to re-enter it as spouse, then resend.
- AARP Medicare Supplement member number for chart 17470713 (25 secondary claims on run 1700302).
- AET12 carrier master (chart 24750).
- GitHub packages 2026-10-11 / 2026-10-12 on Drive 'github mirror' (push from your machine or a byte-exact re-upload) - not retried.
- Four Pam admits without an AMD chart (10/15 x3, 10/16 x1) - waiting on the Claimocity feed, nothing for William.

## Mirror
- GitHub: MIRROR_GITHUB
- Postman: unchanged (no new call shapes; docs/postman_effinger_amd.json and api_vocabulary.json unchanged, not re-uploaded). The Drive registry copy is carried by captured_calls_additions_2026-10-20_0710UTC-3amET-ehpa-cloud.md -> 'billing agent project files'.
- Drive: needs_facesheet_list_section_%s.md + admit_lookup_1020_0710.py + run_outputs_1020_0710.py + pseudonyms.json (413 names, previous copy trashed) -> 'workspace mirror'; docs/SHARED_LESSONS.md -> 'billing agent project files' (previous copy trashed); board_updates_%s.json (%d append ops) -> 'board inbox'; no denials_updates (queue empty); this digest -> 'chat history'; run report CSV (_run report 10-20 0310.csv) delivered with SendUserFile (not a 7 PM slot - no Drive copy, no facesheet email). deceased_cache.json unchanged on Drive (nothing re-learned) - not re-uploaded.
- State bundle: skipped with the standing justification (Drive bundle 2026-09-18 superseded by main; every register that changed is on main; patient_db/ and era_details/ empty this run; the connector's typed-text transport cannot carry the parts byte-exact).

## SHARED LESSONS
- %s | backend billing run | WATCH | columns %s (three zero-plan HCA charts 17478059 / 17478063 / 17478064 on William's turn, chart 17471204's 3 Aetna rows on run 1700311, chart 17470713's 25 AARP secondaries on run 1700302, AET12 chart 24750 carrier hold); ERA Center %d checks $%.2f -> %d checks $%.2f; UNI20/BCBS pre-5/1: %s, 0 sent; four Pam admits (10/15 x3, 10/16 x1) still without an AMD chart; no AMD write; GitHub button slot #%s ran first, this engine pass followed - no overlap | reports/button/%s.json
- %s | backend billing run | TRAP | GitHub button cascade slot #109 (05:43Z live) lost its aging report: 'Commit the report to main' rebased onto the 0510Z routine push (05:47Z) and conflicted in reports/button/latest.json, four pull retries failed on the unresolved rebase; the 05:35Z cascade cron and this routine's 1 AM mirror push land in the same minutes - the workflow's commit step needs a rebase --abort + retry (or latest.json regenerated from the stamped report) instead of 'git pull' on an unmerged tree | .github/workflows/billing-button.yml

RUN COMPLETE
""" % (S, SLOT, ES, S, cols, cb["charge_review"], ca["charge_review"], cb["claim_inspector"], ca["claim_inspector"], cb["unbilled"], ca["unbilled"], cb["exclusions"], ca["exclusions"],
       float(resent.get("dollars", 0)), int(resent.get("visits", 0)), int(wo.get("count", 0)), float(wo.get("dollars", 0)), int(pk.get("applied", 0)), int(pk.get("refused", 0)), int(pk.get("skipped", 0)),
       eb[0], eb[1], ea[0], ea[1], posted.get("pay", 0), posted.get("woins", 0), posted.get("wocaid2nd", 0), posted.get("wolate", 0),
       asked, askamt, swtxt, sweep_sum, errtxt, S, S, len(ops), NOW, cols, eb[0], eb[1], ea[0], ea[1], swtxt, SLOT, ES, NOW)
os.makedirs("chat_history", exist_ok=True); open("chat_history/%s run digest.md" % S, "w").write(dig)
print(cols, "| ERA", eb, ea, "| posted", posted, "| resent", resent, "| wo", wo, "| sweep", asked, dict(byact), "|", swtxt, "| errors", errtxt, "| waiting", len(waiting))
