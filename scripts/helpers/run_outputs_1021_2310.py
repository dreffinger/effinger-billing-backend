#!/usr/bin/env python3
# PLAIN ENGLISH (run outputs builder, 7 PM ET 10/21/2026 run 2026-10-21T2310Z): READ-ONLY on AMD (reads registers + reports only).
# Builds this run's report pieces: the run report CSV (delivered with SendUserFile and, on the 7 PM slot, copied to Drive 'bht hca
# facesheets'), the needs_facesheet_list.md section, the board_updates inbox file (append-only checks on the standing rows, REAL row
# ids as the previous inbox file on Drive carries them), the captured_calls additions file, the SHARED_LESSONS line, the text of the
# 'current face sheets needed' email (chart ids only in the file that reaches GitHub; the email itself is built by the run from the
# board rows) and the chat-history digest. Chart / visit / check ids only (no names, member ids or DOBs). Never touches AMD or the board.
# Usage: python3 run_outputs_1021_2310.py <engine stamp> <slot run number> <slot report stamp> <slot window text>
import csv, json, datetime, collections, sys, glob, os
S = "2026-10-21T2310Z"; ES = sys.argv[1]; SLOT = sys.argv[2]; SLOTS = sys.argv[3]; SLOTWIN = sys.argv[4] if len(sys.argv) > 4 else ""
SRC = "7pm ET 10/21 columns run (ehpa cloud) - run %s" % S; W = "10/21"
NOW = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"; REPO = "/home/claude/effinger-billing-backend"
rep = json.load(open("%s/reports/button/%s.json" % (REPO, ES))); srep = json.load(open("%s/reports/button/%s.json" % (REPO, SLOTS)))
sm = rep["summary"]; cb = sm["columns"]["before"]; ca = sm["columns"]["after"]
cols = "%d/%d/%d/%d -> %d/%d/%d/%d" % (cb["charge_review"], cb["claim_inspector"], cb["unbilled"], cb["exclusions"], ca["charge_review"], ca["claim_inspector"], ca["unbilled"], ca["exclusions"])
se = srep["summary"]["era"]; sp = srep["summary"]["posted"]; ee = sm["era"]; ep = sm["posted"]
errors = rep.get("errors", []) + [e for s in rep.get("steps", []) for e in s.get("errors", [])]
steps = {s.get("name"): s for s in rep.get("steps", [])}; sweep_sum = str(steps.get("sweep", {}).get("summary", ""))
def eralist(tag, st):
    try:
        d = json.load(open("registers/era_checks_%s_%s.json" % (tag, st))); return d.get("count", len(d.get("checks", []))), sum(float(c.get("unpostedamount") or 0) for c in d.get("checks", []))
    except Exception: return None, None
nb0, tb0 = eralist("before", S); na2, ta2 = eralist("after", S)
regs = sorted(glob.glob("registers/uni20_bcbs_pre0501_sweep_*.json")); npass = len(regs)
sw = json.load(open(regs[-1])); sw = sw.get("rows", sw) if isinstance(sw, dict) else sw
bychart = collections.defaultdict(lambda: [0, 0.0])
for r in sw:
    k = (r["action"].split(" - ")[0], str(r["patientid"])); bychart[k][0] += 1; bychart[k][1] += float(r.get("balance") or 0)
swtxt = "; ".join("%d %s chart %s ($%.0f)" % (v[0], k[0], k[1], v[1]) for k, v in sorted(bychart.items())) or "nothing asked"
asked = len(sw); askamt = sum(float(r.get("balance") or 0) for r in sw)
al = json.load(open("registers/admit_lookup_%s.json" % S)); nochart = sum(1 for x in al["lookups"] if not x["charts"])
plans = json.load(open("registers/plan_check_%s.json" % S))["charts"]; zero = [p for p in ("17478059", "17478063", "17478064") if not plans.get(p)]
rl = json.load(open("registers/era_co45_relink_1053251_2026-10-21T2345Z.json")); rll = rl["lines"]
aud = json.load(open("registers/era_audit_%s.json" % S))["rows"]; b9 = json.load(open("registers/era_b9_%s.json" % S))["lines"]
nb3, tb3 = eralist("after", "2026-10-21T2355Z")
woins_tot = sum(float(w[0].lstrip("-")) for r in aud for w in r["wos"] if w[1] == "WOINS"); pr_left = [(r["vid"], r["cid"], r["patbal"]) for r in aud if float(r["patbal"] or 0) > 0.004]
ERATXT = ("this run's pre-slot read (era_list.py 23:22Z): %s checks / $%.2f unposted; GitHub slot #%s (%s) read %d checks / $%.2f -> %d / $%.2f, Post button $%.2f; this run's engine pass (%s): %d checks / $%.2f before -> %d / $%.2f after, era_post $%.2f; "
          "a NEW UnitedHealthcare remit W1539499 (check 1053251, UNI20, $3,697.67, 35 claims / 42 charge lines, received 23:39Z - after the engine pass) was read by this run's after-pass list (%s checks / $%.2f) and settled by this run: all 42 lines cached BEFORE any post (era_details_prepost/1053251.json); era_post.py --all-unposted (--dry, then live 23:42Z) Post-buttoned the 34 money claims / 41 lines ($3,697.67, HTTP 200) and skipped the one $0 line; the live audit (era_audit_1021_2310.py) found the CO-45-on-the-balance defect on every money line (AMD put CO45/CO253 on the payment with payreasonwoamount 0: 37 lines' contractual on the PATIENT balance, 4 lines' on insurance where the chart carries a secondary) - corrected by era_co45_relink.py 1053251 --live 23:45-23:52Z: 41 voids + 41 ERA-linked re-posts (pay $3,697.67 + WOINS $%.2f; PR-2 stays), the $0 CO-B9 hospice line (chart 17475312 v19455651 99487 $206) written off WONCS ERA-linked by era_b9_1021_2310.py --live (the CCM-hospice rule), era_clear.py found the check already off the list, after read 23:52Z: %s checks / $%.2f; final audit: 42 of 42 charges carry the W1539499 payment with CO45/CO253 reasons + WOINS, 40 at $0 both sides, 2 lines of chart 17477848 keep PR-2 patient coinsurance %s (UNI20 is the chart's only plan - patient responsibility, never written off); 1053220 takeback pair (chart 17474741 v19455454) stays dismissed outside the routine, lines still unposted - William's decision"
          % (nb0, tb0 or 0, SLOT, SLOTWIN, se["before"]["checks"], se["before"]["unposted"], se["after"]["checks"], se["after"]["unposted"], sp["pay"], ES, ee["before"]["checks"], ee["before"]["unposted"], ee["after"]["checks"], ee["after"]["unposted"], ep["pay"], na2, ta2 or 0, woins_tot, nb3, tb3 or 0, ", ".join("v%s $%s" % (v, p) for v, c, p in pr_left)))
rows = []
def add(col, state, patient="", dos="", carrier="", err="", action="", check="", visit="", amt=""):
    rows.append({"column": col, "state": state, "patient": patient, "dos": dos, "carrier": carrier, "error": err, "action": action, "check": check, "visit": visit, "amount": amt})
add("charge review", "clear", action="%d -> %d charges" % (cb["charge_review"], ca["charge_review"])); add("claim inspector", "clear", action="%d -> %d batches" % (cb["claim_inspector"], ca["claim_inspector"]))
for pid, vids in (("17478059", "v19457778 / v19457794"), ("17478063", "v19457783 / v19457797"), ("17478064", "v19457784 / v19457791")):
    add("unbilled", "remaining", "chart %s" % pid, "99223 10/12 + 99232 10/13/2026", "(no plan on chart - live getdemographic 23:22Z: %d insplans)" % len(plans.get(pid, [])), "Insurance order is missing on visit", "held - HCA Florida Capital facesheet (admit 10/12/2026) on William's turn; in tonight's face sheets email", visit=vids, amt="421.00")
add("exclusions", "remaining", "chart 17470713 (AARP Medigap secondaries)", "4/2026-7/2026", "AAR01", "PA ACK,RETURND AS UNPRCESSBLE CLM - subscriber id not found (claim run 1700302, 25 rows)", "held - AARP member number on William's turn (live plans 23:22Z unchanged: BCBS ended 12/31/2022, MA plan ended 3/31/2026, Medicare seq 3, AAR01 seq 4)")
for vid, dos, fee in (("19431511", "02/03/2026", "310.00"), ("19435174", "03/08/2026", "310.00"), ("19435175", "03/09/2026", "163.00")):
    add("exclusions", "remaining", "chart 17471204", dos, "AET07", "PA ACK RETURND AS UNPRCESSBLE: ENTITY NOT ELIGIBLE FOR BENEFITS FOR SUBMITTED DOS: PATIENT (run 1700311)", "held for William - subscriber relationship / Feb 2026 HCA facesheet", visit=vid, amt=fee)
add("exclusions", "remaining", "chart 24750", "09/20/2026", "AET12", "CH FH PREF0288 INVALID PAYER ID/CPID 814723941 + PREF0264 (v19455937, run 1700294)", "held - carrier master (board row aet12-carrier-cpid)", visit="19455937", amt="315.00")
add("era", "summary", action=ERATXT)
for r in aud:
    pay = r["pays"][-1] if r["pays"] else {}
    wo = next((w for w in r["wos"] if w[1] in ("WOINS", "WONCS")), None)
    state = "posted + corrected" if r["remit_paid"] > 0 else "denial written off"
    add("era", state, "chart %s" % r["pid"], r["dos"], "UNI20", "UHC W1539499 %s: remit paid %.2f, %s" % (r["cpt"], r["remit_paid"], ", ".join(r["remit_carc"])),
        "Post button, then void + ERA-linked re-post pay %s + %s %s (era_co45_relink.py); ins %s / pat %s%s" % (pay.get("amt", "0").lstrip("-"), wo[1] if wo else "-", wo[0].lstrip("-") if wo else "0", r["insbal"], r["patbal"], " (PR-2 patient coinsurance - no secondary on the chart)" if float(r["patbal"] or 0) > 0 else "") if r["remit_paid"] > 0 else "CO-B9 hospice CCM denial: WONCS %s ERA-linked (era_b9_1021_2310.py), balance $0, no rebill" % (wo[0].lstrip("-") if wo else "206.00"),
        check="1053251", visit="v%s" % r["vid"], amt="%.2f" % r["remit_paid"])
add("era", "remaining", "chart 17474741", "09/20/2026", "FLO02", "check 1053220 Medicare 820007360: takeback pair on v19455454 - dismissed outside the routine 05:37Z 10/21, both lines unposted", "William's decision stands", check="1053220", visit="v19455454", amt="-85.46")
add("unpaid (7pm precheck)", "clear", action="precheck --days 3 --max 120: checked 0 patient/payer pairs (0 new lookups), 0 flagged")
for r in sw: add("uni20/bcbs pre-5/1 sweep (pass %d)" % npass, "sweep", "chart %s" % r.get("patientid"), r.get("dos", ""), r.get("carrier", ""), r.get("action", ""), "277 answer recorded, nothing sent", visit="v%s" % r.get("visitid", ""), amt=r.get("balance", ""))
add("pam admits", "waiting", "pending Pam admits (Tapestry NA 10/15 + 10/17 re-send; Brynwood NA 10/15 x2; Brynwood NA 10/19 + 10/20 re-send; Center Pointe 10/20)", action="lookuppatient 23:22Z by full name pattern: %d of %d patterns still have no AMD chart (hits: namesake chart 25746 - different DOB; readmit charts 17474046 and 17472553 + duplicate 21086); waiting on the Claimocity feed" % (nochart, len(al["lookups"])))
add("github button", "watch", action="GitHub slot #%s ran %s (cron :17); this run polled the workflow until it completed and ran its own engine pass (%s) afterwards, then the 7 PM extras - no overlap" % (SLOT, SLOTWIN, ES))
for e in errors: add("engine", "error", action=str(e))
csvname = "_run report 10-21 2310.csv"
with open(csvname, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
errtxt = "; ".join(str(e) for e in errors) or "none"
sec = """## %s - backend billing run, 7 PM ET 10/21/2026 slot (ehpa cloud) - 23:10-%sZ 10/21

Bootstrap: repo ATTACHED (origin/main b8929ce at start; session branch claude/pensive-einstein-p7i02e; main checked out; symlinked as /home/claude/effinger-billing-backend; layout 1209 helper files + OCR tools, required helpers all present - optional era_details_pull.py / columns_inspector2_0908.py / github_sync.py absent as usual); network AMD OK / Stedi proxy credential OK / GitHub attached; AMD_PSW environment credential (no credential file); ONE login (plan_check_1021_2310.py 23:22Z, token reused by every later helper, the engine pass and the sweep step), no lock, no 429. State bundle: Drive 'workspace mirror' still lists nothing newer than workspace_state_2026-09-18 - superseded by main, not restored; pseudonyms.json (Drive 10/21 17:55Z, 410 names) in both secrets/ copies; deceased_cache.json (Drive 10/21 21:56Z, 76 dated) merged into the workspace cache, repo copy kept scrubbed. v12 precondition: all pass. Routine text: this routine still carries the v7 prompt - the v12 text + v13 insert on main were applied as the current standing rules. Learned from others: git log 36h = this routine + the GitHub Billing Button slots; SHARED_LESSONS lines newer than 21:50Z: none; 0 applied. Guard: 2110Z START has its RUN COMPLETE digest (21:58Z); START 2310Z uploaded 23:15Z, lock written, deleted at the end.
Sources: Insurance Refresh Board (read_db): 0 rows updated after 19:00Z, drops 0; Working Denials queue 0; Mandatory Approvals page 0 approved / 0 waiting (register: 93 items, none open). Drive: nothing new in 'bht Optum era downloads', 'treasury payments', the three facesheet folders, the Claimocity drop or 'board inbox' since the 2110Z run's own files; Pam Gmail (8d): the same nine admit threads of 10/15-10/20, all already worked; admit lookup: %d of %d name patterns without an AMD chart. Neither board registry lists a current inbox file in its applied map - no inbox file trashed.
Columns (engine columns_scan) %s: CHARGE REVIEW 0; CLAIM INSPECTOR 0; UNBILLED the three zero-plan HCA charts %s (live getdemographic 23:22Z: 0 insplans on all three, $1,263, William's turn); EXCLUSIONS: chart 17470713's 25 AARP secondaries (run 1700302), chart 17471204's three AET07 rows (run 1700311, $783), the AET12 chart-24750 row (run 1700294) - standing holds, no new claim run row.
ERA (step 5): %s. Availity step 5(g): no new Availity PDF or Check/EFT export - nothing to parse, post or reconcile.
UNI20/BCBS pre-5/1 pass %d (engine sweep step, after the engine pass): %d asked ($%.2f): %s; engine summary: %s; 0 sent, 0 written off.
7 PM extras: (a) precheck.py --days 3 --max 120 -> checked 0 patient/payer pairs (0 new lookups), 0 flagged. (c) 'current face sheets needed' email sent to dreffinger@gmail.com (charts 17478059 / 17478063 / 17478064 HCA facesheets; chart 17478013 VA referral; chart 17470713 AARP member number; chart 17471204 Aetna subscriber relationship; the six Pam admit name patterns without a chart for information). (d) run report CSV also in Drive 'bht hca facesheets'.
Writes this run (AdvancedMD): era_post.py --all-unposted (Post button on UHC 1053251: 34 claims / 41 lines $3,697.67), era_co45_relink.py 1053251 --live (41 x void_payment + 41 x addpayments postingmethod=era pay + WOINS $%.2f; 30 move_to_ins no-rebill move-backs of the patient-side remainders first), era_b9_1021_2310.py --live (1 x addpayments postingmethod=era pay 0.00 + WONCS 206.00); the engine pass wrote nothing (engine posted $%.2f, resent %d visits, written off %d). Dollars re-sent $%.2f. Write-offs: WOINS $%.2f on 41 charges (UHC contractual, ERA-linked) + WONCS $206.00 on 1 charge (CCM hospice CO-B9). Approvals applied 0 / submitted 0 / waiting 0. Permission classifier: nothing refused. Script errors: %s.
Waiting on William: takeback decision chart 17474741 v19455454 (ERA 1053220); VA referral for chart 17478013 (the 10/5/2026 admission; the note of 10/15 carries the 2025 auth); HCA Florida Capital facesheets (admit 10/12/2026) for charts 17478059 / 17478063 / 17478064 ($1,263); chart 17471204 AET07 x3; AARP member number chart 17470713; AET12 carrier master (chart 24750); chart 17474290 appeal-or-write-off (CO-97, $310); chart 17473501 payer for $122.29 coinsurance. Six Pam admit name patterns without an AMD chart - waiting on the Claimocity feed.
Helpers this run: plan_check_1021_2310.py, admit_lookup_1021_2310.py, poll_slot_2310.sh, era_audit_1021_2310.py, run_outputs_1021_2310.py (read-only); era_b9_1021_2310.py (write, --dry then --live), era_chain_2310.sh (the nohup chain: era_co45_relink.py --live, era_b9 --live, era_clear.py, era_list.py, era_audit). Calls captured: 0 new shapes; 0 vocabulary entries added.
""" % (S, NOW[11:16].replace(":", ""), nochart, len(al["lookups"]), cols, " / ".join(zero) if zero else "(none - plans entered)", ERATXT, npass, asked, askamt, swtxt, sweep_sum, woins_tot, ep["pay"], sm["resent"]["visits"], sm["written_off"]["count"], sm["resent"]["dollars"], woins_tot, errtxt)
open("needs_facesheet_list.md", "a").write("\n" + sec); open("needs_facesheet_list_section_%s.md" % S, "w").write(sec)
chk = lambda txt, ok="na": {"checks": [{"ok": ok, "result": txt, "src": SRC, "when": W}]}
prev = {op["id"]: op for op in json.load(open("inbox/board_updates_2110_prev.json"))["ops"]}   # real row ids, workspace only
byamd = {pid: next(i for i in prev if i.endswith("-" + pid)) for pid in ("17478059", "17478063", "17478064", "17474741", "17478013")}
denrow = next(i for i in prev if i.endswith("-denials") and "poulter" in i or i.endswith("-gwen-denials"))
hold = "7 PM ET 10/21: chart %s still has zero insurance plans (live getdemographic 23:22Z 10/21; Unbilled list unchanged); no new HCA / TMH / PCC facesheet, Pam email or board note - the two visits (%s, $421) stay in Unbilled on your turn; in tonight's face sheets email."
ops = [{"op": "upsert", "collection": "items", "id": "availity-remits-backlog", "append": chk("7 PM ET 10/21: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (nothing new there since 10/20); no new facesheet or Claimocity file; Working Denials queue 0; board drops 0; approvals 0 approved / 0 waiting; Pam Gmail: the nine 10/15-10/20 admit threads, all worked. ERA Center: " + ERATXT + ". Columns " + cols + " - every row a standing hold; precheck --days 3: 0 pairs; UNI20/BCBS pre-5/1 pass %d: %s, 0 sent. 'current face sheets needed' email sent." % (npass, swtxt))},
       {"op": "upsert", "collection": "items", "id": "aet12-carrier-cpid", "append": chk("7 PM ET 10/21: HOLD - the one AET12 PREF0288 exclusion row (chart 24750, v19455937, run 1700294) stays on the list, not rebilled; carrier master still unchanged.")},
       {"op": "upsert", "collection": "items", "id": byamd["17478059"], "append": chk(hold % ("17478059", "v19457778 / v19457794"), "human")},
       {"op": "upsert", "collection": "items", "id": byamd["17478063"], "append": chk(hold % ("17478063", "v19457783 / v19457797"), "human")},
       {"op": "upsert", "collection": "items", "id": byamd["17478064"], "append": chk(hold % ("17478064", "v19457784 / v19457791"), "human")},
       {"op": "upsert", "collection": "items", "id": denrow, "append": chk("7 PM ET 10/21: the 25 AARP Medigap secondary rejections of claim run 1700302 stay on the exclusion list (live plans 23:22Z unchanged: BCBS ended 12/31/2022, MA plan ended 3/31/2026, Medicare seq 3, AAR01 seq 4) - AARP member number still needed; in tonight's face sheets email.", "human")},
       {"op": "upsert", "collection": "items", "id": "tully-tracy", "append": chk("7 PM ET 10/21: the three Aetna AET07 rejections of claim run 1700311 (v19431511 / v19435174 / v19435175, $783) stay on the exclusion list, held for your subscriber-relationship answer / the Feb 2026 HCA facesheet; in tonight's face sheets email.", "human")},
       {"op": "upsert", "collection": "items", "id": byamd["17478013"], "append": chk("7 PM ET 10/21: VACCN plan unchanged (seq 1, begin 10/15/2025, live 23:22Z); ERA 1053239 (8 x CO-288 'referral absent', $1,430) stays dismissed; your 10/15 note carries the 2025 admission's auth - the 2026 VA referral / authorization number for the 10/5/2026 HCA admission is still needed before the 8 visits are re-sent; in tonight's face sheets email.", "human")},
       {"op": "upsert", "collection": "items", "id": byamd["17474741"], "append": chk("7 PM ET 10/21: ERA check 1053220 (Medicare 820007360, the takeback pair on v19455454: reversal -85.46 of check 819919368 + CO-236 $0) still dismissed outside the routine (05:37Z 10/21), both lines unposted on the visit - your decision stands.", "human")}]
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
add_md = """## 2026-10-21 23:10Z - backend billing run, 7 PM ET 10/21/2026 (ehpa cloud, repo attached)
No new call shapes this run. The columns, ERA, sweep and packages steps ran through the repository's Billing Button engine (tools/button/run_all.py --mode live --steps columns,era,sweep,packages --stedi-proxy) from the routine's own container AFTER the scheduled GitHub slot (run #%s, %s) had completed - one login (plan_check_1021_2310.py 23:22Z; every later helper, the engine pass and the sweep reused the token; no lock, no 429). Calls used (all already in the registry): login, getdemographic x5 (plan_check_1021_2310.py), lookuppatient x9 (admit_lookup_1021_2310.py), GET /api/era/checks (era_list.py 23:22Z pre-slot and the after read; the slot's and the engine's before/after), getclaimcenteroverview + getreviewcharges / getclaiminspectorbatches / getclaimunbillablecharges / getclaimexclusionclaimruns + getclaimexclusioncharges (columns_scan.py before/after), the engine's inspector / unbilled / exclusion helpers, era_post.py --all-unposted + era_clear.py, Stedi 276/277 (sweep step, %d visits), precheck.py --days 3 (0 pairs). Engine report reports/button/%s.json; slot report reports/button/%s.json.
""" % (SLOT, SLOTWIN, asked, ES, SLOTS)
open("captured_calls_additions_2026-10-21_2310UTC-7pmET-ehpa-cloud.md", "w").write(add_md)
lessons = ["- %s | backend billing run | WATCH | columns %s (standing holds: three zero-plan HCA charts 17478059/17478063/17478064, chart 17470713 AARP x25, chart 17471204 AET07 x3, AET12 chart 24750); ERA: %s; UNI20/BCBS pre-5/1 pass %d: %s, 0 sent; precheck --days 3: 0 pairs; %d Pam admit name patterns still without a chart; GitHub slot #%s %s waited for before the engine pass %s and the sweep step; 'current face sheets needed' email sent | reports/button/%s.json" % (NOW, cols, ERATXT, npass, swtxt, nochart, SLOT, SLOTWIN, ES, ES),
           "- %s | backend billing run | TRAP | the ERA Center Post button on a UNITEDHEALTHCARE (UNI20) PRIMARY remit put CO45/CO253 on every payment with payreasonwoamount 0 again (check 1053251 W1539499, 41 money lines: 37 contractual remainders on the PATIENT balance, 4 on insurance where a secondary exists) - the 10/20 'did not recur on UNI20' observation was one check, not the carrier; after ANY Post on UNI20 run era_co45_relink.py <checkid> --meta <list-form era_checks json> --live (void + ERA-linked re-post with WOINS, PR stays) and audit; a remit that lands AFTER the engine pass is still this run's to settle (list again before the report) | scripts/helpers/era_co45_relink.py, registers/era_co45_relink_1053251_2026-10-21T2345Z.json" % NOW,
           "- %s | backend billing run | FIX | a $0 CO-B9 (hospice) CCM line on a money remit: WONCS ERA-linked through payreasons.post_line pay 0.00 (era_dual pattern with the primary-paid guard relaxed for WONCS) - chart 17475312 v19455651 99487 $206 on UHC 1053251; era_post.py skips the $0 line and era_clear needs nothing once the money lines are posted | scripts/helpers/era_b9_1021_2310.py" % NOW]
open("shared_lessons_%s.txt" % S, "w").write("\n".join(lessons) + "\n")
digest = """# %s run digest - backend billing run, 7 PM ET 10/21/2026 (ehpa cloud, repo attached)

%s
## Mirror
- MIRROR_PLACEHOLDER

## SHARED LESSONS
%s

RUN COMPLETE
""" % (S, sec, "\n".join(lessons))
os.makedirs("chat_history", exist_ok=True); open("chat_history/%s run digest.md" % S, "w").write(digest)
print("wrote", csvname, "rows", len(rows), "| ops", len(ops), [o["id"][-12:] for o in ops], "| needs section", len(sec), "chars | zero-plan", zero, "| no chart", nochart, "of", len(al["lookups"]))
