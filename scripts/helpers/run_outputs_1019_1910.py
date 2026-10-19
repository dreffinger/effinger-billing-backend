# PLAIN ENGLISH (run outputs for the 3 PM ET 10/19/2026 slot - ehpa cloud run 2026-10-19T1910Z)
# Decides: nothing. Reads this run's Billing Button engine report (reports/button/<engine stamp>.json: column counts before/after,
# ERA Center counts, posted / resent / written-off dollars, the sweep summary), the sweep register and the pending-admit
# lookup register, then writes the run report CSV, the needs_facesheet_list.md section (+ a copy for Drive), the board_updates
# inbox file (append-only checks on standing rows + one new row for today's Brynwood admit), the captured_calls additions
# file and the chat-history digest. Never touches: AMD, the board database. Usage: python3 run_outputs_1019_1910.py <engine stamp>
import csv, json, datetime, collections, os, sys, glob
S = "2026-10-19T1910Z"; ES = sys.argv[1]; SRC = "3pm ET 10/19 columns run (ehpa cloud) - run %s" % S; W = "10/19"
NOW = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
PA = json.load(open("patient_db/pending_admits_1019.json"))["dunwoody-laurel-admit-1016"]  # PHI stays in the workspace
PN, PD, PM, PX, PP = PA["patient"], PA["dob"], PA["medicaid"], PA["auth"], PA["pattern"]
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
NAMES = {"17478059": "chart 17478059", "17478063": "chart 17478063", "17478064": "chart 17478064", "17470713": "chart 17470713 (AARP Medigap secondaries)", "24750": "chart 24750"}
rows = []
def add(col, state, patient="", dos="", carrier="", err="", action="", check="", visit="", amt=""):
    rows.append({"column": col, "state": state, "patient": patient, "dos": dos, "carrier": carrier, "error": err, "action": action, "check": check, "visit": visit, "amount": amt})
add("charge review", "clear" if ca["charge_review"] == 0 else "remaining", action="%d -> %d visits" % (cb["charge_review"], ca["charge_review"]))
add("claim inspector", "clear" if ca["claim_inspector"] == 0 else "remaining", action="%d -> %d visits" % (cb["claim_inspector"], ca["claim_inspector"]))
for pid, vids in (("17478059", "v19457778 / v19457794"), ("17478063", "v19457783 / v19457797"), ("17478064", "v19457784 / v19457791")):
    add("unbilled", "remaining", NAMES[pid], "99223 10/12 + 99232 10/13/2026", "(no plan on chart)", "Insurance order is missing on visit", "held - cascade exhausted 10/15, HCA Florida Capital facesheet (admit 10/12/2026) on William's turn", visit=vids, amt="421.00")
add("exclusions", "remaining", NAMES["17470713"], "4/2026-7/2026", "AAR01", "PA ACK,RETURND AS UNPRCESSBLE CLM - subscriber id not found (claim run 1700302, 25 rows)", "held - AARP Medicare Supplement member number needed (William's turn); not rebilled")
add("exclusions", "remaining", NAMES["24750"], "09/20/2026", "AET12", "CH FH PREF0288 INVALID PAYER ID/CPID 814723941 + PREF0264 (v19455937)", "held - carrier master (board row aet12-carrier-cpid); not rebilled", visit="19455937", amt="315.00")
add("era", "clear" if ea[0] == 0 else "remaining", action="ERA Center %d checks $%.2f before -> %d checks $%.2f after; auto-posted pay $%.2f / WOINS $%.2f / WOCAID2ND $%.2f / WOLATE $%.2f; nothing uploaded (no new 835); Availity: no new PDF / Check-EFT export; Treasury: nothing new" % (eb + ea + (posted.get("pay", 0), posted.get("woins", 0), posted.get("wocaid2nd", 0), posted.get("wolate", 0))))
for r in sw:
    add("uni20/bcbs pre-5/1 sweep", "sweep", "chart %s" % r.get("patientid"), r.get("dos", ""), r.get("carrier", ""), r.get("action", ""), "277 answer recorded, nothing sent", visit=str(r.get("visitid")), amt=r.get("balance"))
add("pam admits", "waiting", "" + PN + " (Brynwood NA 10/16, Pam 10/19 18:00Z) - Sunshine MMA Skilled " + PM + ", auth " + PX + ", DOB " + PD + "; FLINTHAM (Tapestry NA 10/15); JENNER (Brynwood NA 10/15); BEARDSLEY (Brynwood NA 10/15)", action="lookuppatient 19:2xZ: no AMD chart for any of the four - nothing to attach to; waiting on the Claimocity feed (never create a chart from an email); insurance recorded on the board row for the day the chart arrives")
with open("_run report 10-19 1510.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
errtxt = "; ".join(str(e) for e in errors) or "none"
sec = """## %s - backend billing run, 3 PM ET 10/19/2026 slot (ehpa cloud) - 19:10-19:5xZ

Bootstrap: repo ATTACHED (origin/main 70c9261 at start; session branch claude/pensive-einstein-xdmgdx; main checked out; symlinked as /home/claude/effinger-billing-backend; layout 1123 helper files); net AMD_OK / STEDI_CRED_OK / GitHub reachable; AMD password = the AMD_PSW environment credential (no credential file); ONE login 19:20Z (amd.login_cached, token reused by the engine), no lock, no 429. Guard: 1710Z START has its RUN COMPLETE digest (17:40Z), no newer START; own START uploaded 19:12Z, lock written. State bundle: Drive 'workspace mirror' still lists no workspace_state bundle newer than 2026-09-18 - patient_db/ and era_details/ started empty; registers, needs list, laterality log from main. pseudonyms.json (406 names, Drive 10/8) in both secrets/; deceased_cache.json (Drive 10/16) merged (76 dated entries) before and again after the engine. Missing required helpers: none; v12 precondition markers all present. The GitHub Billing Button slot #103 (19:22Z) was allowed to finish first; this run's engine pass (tools/button/run_all.py --mode live --steps columns,era,sweep,packages --stedi-proxy) followed - report reports/button/%s.json.

Sources: Insurance Refresh Board (read_db only): 200 rows on Claude's turn re-read, 0 rows updated after 15:00Z, drops 0; William's two 10/15 answers verified applied live (chart 17477498 v19455608 WONCS 206.00 posted 10/15; chart 17471326 v19457089 recoded to the established-patient code and billed 10/15). Working Denials queue 0. Mandatory Approvals page 0 approved / 0 waiting. Both drive_sync registries list no current inbox file - nothing trashed. Drive: nothing new in the HCA / TMH / PCC / Claimocity / 835 / treasury folders (nothing modified anywhere after 17:45Z outside the routines' own files). Pam Gmail (2 days): ONE new admit email 18:00Z 10/19 - 'NA BW' (Brynwood) PCC facesheet: admitted 10/16/2026 from Capital Regional, age 40, Primary Payer MCD MGD - MMA Skilled (Sunshine State Health Plan), Medicaid # " + PM + ", auth " + PX + ", no Medicare; lookuppatient 19:2xZ: NO AMD chart yet (never created from an email) - board row dunwoody-laurel-admit-1016 holds the insurance for the day the Claimocity feed delivers the chart. The three 10/15 admits (FLINTHAM Tapestry, JENNER / BEARDSLEY Brynwood) still have no AMD chart (registers/admit_lookup_%s.json).

Columns (engine columns_scan before -> after) %s:
- CHARGE REVIEW %d -> %d. CLAIM INSPECTOR %d -> %d.
- UNBILLED %d -> %d: the three zero-plan HCA charts 17478059 / 17478063 / 17478064 (99223 10/12 + 99232 10/13/2026, $421 each, $1,263) 'Insurance order is missing' - cascade exhausted 10/15; no HCA / TMH / PCC facesheet, Pam email or board drop since; rows on William's turn unchanged.
- EXCLUSIONS %d -> %d: 25 AARP Medigap secondary rows of chart 17470713 on claim run 1700302 (subscriber id not found - supplement member number, William's turn) + 1 AET12 PREF0288 chart 24750 v19455937 (carrier master hold). Nothing rebilled, nothing completed.
- Dollars re-sent $%.2f (%d visits). Write-offs %d / $%.2f. Packages applied %d / refused %d / skipped %d.

ERA (step 5): (a) nothing to upload (no new 835); (b) GET /api/era/checks = %d checks / $%.2f before and %d checks / $%.2f after; (c) era_post --all-unposted: pay $%.2f, WOINS $%.2f, WOCAID2ND $%.2f, WOLATE $%.2f; (d)-(e) see the engine report. (g) Availity: no new PDF or Check/EFT export; Treasury nothing new.
UNI20/BCBS pre-5/1 (claim_status_sweep.py via the engine, --skip-answered with the earlier registers): %d asked ($%.2f): %s - %s; engine summary: %s; 0 sent, 0 written off.

Waiting on William: HCA Florida Capital facesheets (admit 10/12/2026) for charts 17478059 / 17478063 / 17478064 (6 visits, $1,263); AARP Medicare Supplement member number for chart 17470713 (25 secondary claims); AET12 carrier master (chart 24750); four Pam admits (10/15 x3, 10/16 x1) without an AMD chart; the standing items of earlier digests unchanged.
Script errors: %s. Calls learned: 0 new shapes (0 vocabulary entries).
""" % (S, ES, S, cols, cb["charge_review"], ca["charge_review"], cb["claim_inspector"], ca["claim_inspector"], cb["unbilled"], ca["unbilled"], cb["exclusions"], ca["exclusions"],
       float(resent.get("dollars", 0)), int(resent.get("visits", 0)), int(wo.get("count", 0)), float(wo.get("dollars", 0)), int(pk.get("applied", 0)), int(pk.get("refused", 0)), int(pk.get("skipped", 0)),
       eb[0], eb[1], ea[0], ea[1], posted.get("pay", 0), posted.get("woins", 0), posted.get("wocaid2nd", 0), posted.get("wolate", 0),
       asked, askamt, dict(byact), swtxt, sweep_sum, errtxt)
sec = sec.replace('" + PM + "', PM).replace('" + PX + "', PX).replace('" + PD + "', PD).replace('" + PN + "', PN)
open("needs_facesheet_list.md", "a").write("\n" + sec); open("needs_facesheet_list_section_%s.md" % S, "w").write(sec)
chk = lambda txt, ok="na": {"checks": [{"ok": ok, "result": txt, "src": SRC, "when": W}]}
hold = "3 PM ET 10/19: chart %s still has zero insurance plans (Unbilled list unchanged); no new HCA facesheet in Drive, no Pam email, no board note - the two visits (%s) stay in Unbilled 'Insurance order is missing'; your turn unchanged (HCA Florida Capital facesheet, admit 10/12/2026)."
ops = [{"op": "upsert", "collection": "items", "id": "madison-digby-[first]-17478059", "append": chk(hold % ("17478059", "v19457778 / v19457794"), "no")},
       {"op": "upsert", "collection": "items", "id": "[name]-17478063", "append": chk(hold % ("17478063", "v19457783 / v19457797"), "no")},
       {"op": "upsert", "collection": "items", "id": "edgerton-jocelyn-17478064", "append": chk(hold % ("17478064", "v19457784 / v19457791"), "no")}]
ops.append({"op": "upsert", "collection": "items", "id": "aet12-carrier-cpid", "append": chk("3 PM ET 10/19: HOLD - the one AET12 PREF0288 exclusion row (chart 24750, v19455937) stays on the list, not rebilled; carrier master still unchanged.")})
ops.append({"op": "upsert", "collection": "items", "id": "availity-remits-backlog", "append": chk("3 PM ET 10/19: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (nothing modified anywhere in Drive after 17:45Z outside the routines' own files); no new 835, facesheet or Claimocity file; Working Denials queue 0; board drops 0; approvals 0 approved / 0 waiting; Pam Gmail: one new Brynwood admit 18:00Z (row dunwoody-laurel-admit-1016 - no AMD chart yet). ERA Center %d checks $%.2f -> %d checks $%.2f. Columns %s. UNI20/BCBS pre-5/1: %s, 0 sent. Engine report reports/button/%s.json." % (eb[0], eb[1], ea[0], ea[1], cols, swtxt, ES))})
ops.append({"op": "upsert", "collection": "items", "id": "dunwoody-laurel-admit-1016",
            "set": {"patient": PN, "dob": PD, "facility": "BRYNWOOD (Monticello) - admitted 10/16/2026 from Capital Regional Medical Center", "amdid": "", "mbi": "",
                    "inscarrier": "SUN01 Sunshine State Health Plan (MCD MGD - MMA Skilled)", "insid": "" + PM + "", "insplans": "1st SUN01 Sunshine State Health Plan " + PM + " (MMA Skilled; auth " + PX + ") - second payer 'Managed Care coinsurance from Medicaid' " + PM + "; no Medicare (age 40)",
                    "need": "None yet (Claude watching): Pam's PCC facesheet 10/19 18:00Z - Brynwood new admit 10/16/2026, Primary Payer MCD MGD - MMA Skilled = Sunshine State Health Plan, Medicaid # " + PM + ", authorization " + PX + ", no Medicare. lookuppatient 10/19 19:2xZ: no AMD chart yet (a chart is never created from an email). When the Claimocity feed delivers the chart: add SUN01 " + PM + " (no group), AMD 271, put the auth on the visit/referral plan, order the visits, release.",
                    "why": "Pam new-admit email 10/19/2026 (NA BW) - chart not yet in AMD", "amount": 0, "status": "claude", "created": NOW, "updated": NOW,
                    "notes": [{"who": "Claude", "text": "Created by the 3 PM ET 10/19 run from Pam's admit email. Nothing needed from you - the run adds the Sunshine plan and auth the moment the chart exists.", "at": NOW}]},
            "append": {"checks": [{"ok": "na", "result": "PCC facesheet read (image): Sunshine MMA Skilled " + PM + ", auth " + PX + ", DOB " + PD + ", admit 10/16/2026 from Capital Regional; lookuppatient " + PP.replace("%","%%") + " = no chart", "src": SRC, "when": W}]}})
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
open("captured_calls_additions_2026-10-19_1910UTC-3pmET-ehpa-cloud.md", "w").write("""## 2026-10-19 19:10Z - backend billing run, 3 PM ET 10/19/2026 (ehpa cloud, repo attached)
No new call shapes this run. The columns, ERA, sweep and packages steps ran through the repository's Billing Button engine (tools/button/run_all.py --mode live --steps columns,era,sweep,packages --stedi-proxy) from the routine's own container after the scheduled GitHub slot (run #103, 19:22Z) had finished - one login (amd.login_cached 19:20Z, no lock, no 429). Calls used (all already in the registry): login, lookuppatient (four pending Pam admits, no chart), gettxhistory (two board-answer verifications), getclaimcenteroverview, getreviewcharges, getclaiminspectorbatches, getclaimunbillablecharges, getclaimexclusionclaimruns / getclaimexclusioncharges (columns_scan.py before/after), GET /api/era/checks x2, Stedi 276/277 (claim_status_sweep.py). Engine report reports/button/%s.json.
""" % ES)
dig = """# %s run digest - backend billing run, 3 PM ET 10/19/2026 (ehpa cloud, repo attached)

## Bootstrap
- Repo attached: main 70c9261 at start (session branch claude/pensive-einstein-xdmgdx; main checked out; /home/claude/effinger-billing-backend symlinked). Network: AMD OK, Stedi proxy credential OK (no key file), GitHub attached. AMD password: the AMD_PSW environment credential (no credential file). One login 19:20Z (amd.login_cached; the engine reused the token), no lock, no 429.
- State bundle: Drive 'workspace mirror' still lists nothing newer than workspace_state_2026-09-18 - superseded by main, not restored (patient_db/ and era_details/ start empty). Workspace laid out from main: 1123 helper files; missing required helpers none (optional absent: era_details_pull.py, columns_inspector2_0908.py). pseudonyms.json (406 names, Drive 10/8) in both secrets/; deceased_cache.json (Drive 10/16, 76 dated entries) merged before the engine and re-merged after it (the engine bootstrap re-lays the scrubbed repo copy - 10/19 1742Z TRAP); v12 precondition OK.
- Prompt fired as the v7 text; the v12 text + v13 insert on main (nightly/) applied as on every run since 10/6.
- Guard: 1710Z START has its RUN COMPLETE digest (17:40Z); START 1910Z uploaded 19:12Z, lock written, deleted at the end. The scheduled GitHub Billing Button slot (run #103, started 19:22Z) was allowed to finish FIRST; this run's engine pass (tools/button/run_all.py --mode live --steps columns,era,sweep,packages --stedi-proxy) followed in this container; report reports/button/%s.json. Permission classifier: no refusal.

## Sources read
- Insurance Refresh Board (read_db only): 200 rows on Claude's turn re-read, 0 rows updated after 15:00Z, drops 0; William's two 10/15 answers (chart 17477498 WONCS; chart 17471326 'resend as original') verified applied live on 10/15 - nothing to do. Working Denials queue 0. Mandatory Approvals page 0 approved / 0 waiting. Both drive_sync registries: no current inbox file in the applied maps - nothing trashed.
- Drive: nothing modified anywhere after 17:45Z outside the routines' own files; no 835, Availity PDF, Check/EFT export, facesheet or Claimocity file. Pam Gmail (2d): one new admit 18:00Z 10/19 (Brynwood NA 10/16, Sunshine MMA Skilled + auth on the PCC sheet) - no AMD chart yet (lookuppatient), board row dunwoody-laurel-admit-1016 created through the inbox; the three 10/15 admits still have no chart (registers/admit_lookup_%s.json).

## Columns (list calls) %s
- Charge Review %d -> %d. Claim Inspector %d -> %d.
- Unbilled %d -> %d: the three zero-plan HCA charts 17478059 / 17478063 / 17478064 on William's turn (HCA Florida Capital facesheets admit 10/12/2026, 6 visits $1,263).
- Exclusions %d -> %d: the 25 AAR01 rows of chart 17470713 on run 1700302 (AARP supplement member number) and the AET12 chart-24750 PREF0288 hold - unchanged, nothing rebilled.
- Dollars re-sent $%.2f (%d visits). Write-offs %d / $%.2f. Packages applied %d / refused %d / skipped %d.

## ERA Center - %d checks $%.2f before -> %d checks $%.2f after
- Nothing to upload (no new 835 / Availity PDF / Check-EFT export); era_post --all-unposted: pay $%.2f, WOINS $%.2f, WOCAID2ND $%.2f, WOLATE $%.2f; era_clear per the engine report. Availity 5(g) and Treasury: nothing new. Calls learned: none (0 vocabulary entries).

## UNI20/BCBS pre-5/1
- claim_status_sweep.py (engine sweep step, --skip-answered with the earlier registers): %d asked ($%.2f): %s; engine summary: %s; 0 candidates, 0 sent, written off 0.

## Script errors
- %s

## Waiting on William
- HCA Florida Capital facesheets (admit 10/12/2026) for charts 17478059 / 17478063 / 17478064 (6 visits, $1,263).
- AARP Medicare Supplement member number for chart 17470713 (25 secondary claims on run 1700302).
- AET12 carrier master (chart 24750).
- Four Pam admits without an AMD chart (10/15 x3, 10/16 x1) - waiting on the Claimocity feed, nothing for William.
- The Billing Button schedule still runs live at :17 past the odd hours in the same hours as this routine; this run sequenced after it (no overlap), but docs/BILLING_BUTTON.md still says one of the two should be paused - William's call.

## Mirror
- GitHub: MIRROR_GITHUB
- Postman: unchanged (no new call shapes; docs/postman_effinger_amd.json and api_vocabulary.json unchanged, not re-uploaded). The Drive registry copy is carried by captured_calls_additions_2026-10-19_1910UTC-3pmET-ehpa-cloud.md -> 'billing agent project files'.
- Drive: needs_facesheet_list_section_%s.md -> 'workspace mirror'; board_updates_%s.json (%d ops) -> 'board inbox'; no denials_updates (queue empty); this digest -> 'chat history'; run report CSV (_run report 10-19 1510.csv) delivered with SendUserFile (not a 7 PM slot - no Drive copy). deceased_cache.json on Drive unchanged - not re-uploaded.
- State bundle: skipped with the standing justification (Drive bundle 2026-09-18 superseded by main; the registers that changed are on main; patient_db/ and era_details/ empty this run; the connector's typed-text transport cannot carry the parts byte-exact).

## SHARED LESSONS
- %s | backend billing run | WATCH | columns %s (three zero-plan HCA charts 17478059 / 17478063 / 17478064 on William's turn, chart 17470713's 25 AARP secondaries on run 1700302, AET12 chart 24750 carrier hold); ERA Center %d checks $%.2f -> %d checks $%.2f; UNI20/BCBS pre-5/1: %s, 0 sent; Pam's 10/19 Brynwood admit (Sunshine MMA Skilled + auth on the PCC sheet) has no AMD chart yet - insurance parked on its board row; the GitHub button slot #103 (19:22Z) ran first and this engine pass followed - no overlap | reports/button/%s.json

RUN COMPLETE
""" % (S, ES, S, cols, cb["charge_review"], ca["charge_review"], cb["claim_inspector"], ca["claim_inspector"], cb["unbilled"], ca["unbilled"], cb["exclusions"], ca["exclusions"],
       float(resent.get("dollars", 0)), int(resent.get("visits", 0)), int(wo.get("count", 0)), float(wo.get("dollars", 0)), int(pk.get("applied", 0)), int(pk.get("refused", 0)), int(pk.get("skipped", 0)),
       eb[0], eb[1], ea[0], ea[1], posted.get("pay", 0), posted.get("woins", 0), posted.get("wocaid2nd", 0), posted.get("wolate", 0),
       asked, askamt, swtxt, sweep_sum, errtxt, S, S, len(ops), NOW, cols, eb[0], eb[1], ea[0], ea[1], swtxt, ES)
os.makedirs("chat_history", exist_ok=True); open("chat_history/%s run digest.md" % S, "w").write(dig)
print(cols, "| ERA", eb, ea, "| posted", posted, "| resent", resent, "| wo", wo, "| sweep", asked, dict(byact), "|", swtxt, "| errors", errtxt)
