#!/usr/bin/env python3
# PLAIN ENGLISH (run outputs builder, 3 PM ET 10/21/2026 run 2026-10-21T1910Z): READ-ONLY on AMD (reads registers + reports only).
# Builds this run's report pieces: the run report CSV (delivered with SendUserFile), the needs_facesheet_list.md section, the
# board_updates inbox file (checks on the standing rows only - the real row ids are read from the previous inbox file kept in the
# workspace, never written into this script), the captured_calls additions file, the SHARED_LESSONS line and the chat-history digest.
# Chart / visit / check ids only in everything that reaches GitHub. No AMD call of any kind.
# Usage: python3 run_outputs_1021_1910.py
import csv, json, datetime, collections, glob, os
S = "2026-10-21T1910Z"; E = "2026-10-21T1929Z"; SRC = "3pm ET 10/21 columns run (ehpa cloud) - run %s" % S; W = "10/21"
NOW = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"; REPO = "/home/claude/effinger-billing-backend"
slot = json.load(open(REPO + "/reports/button/2026-10-21T1923Z.json")); eng = json.load(open(REPO + "/reports/button/%s.json" % E))
ss, es = slot["summary"], eng["summary"]; cb = es["columns"]["before"]; ca = es["columns"]["after"]
cols = "%d/%d/%d/%d -> %d/%d/%d/%d" % (cb["charge_review"], cb["claim_inspector"], cb["unbilled"], cb["exclusions"], ca["charge_review"], ca["claim_inspector"], ca["unbilled"], ca["exclusions"])
def eralist(tag, st):
    d = json.load(open("registers/era_checks_%s_%s.json" % (tag, st))); return d.get("count", len(d.get("checks", []))), sum(float(c.get("unpostedamount") or 0) for c in d.get("checks", []))
nb0, tb0 = eralist("before", S); nb, tb = eralist("before", E); na, ta = eralist("after", E)
regs = sorted(glob.glob("registers/uni20_bcbs_pre0501_sweep_*.json")); npass = len(regs)
sw = json.load(open(regs[-1])); sw = sw.get("rows", sw) if isinstance(sw, dict) else sw
bychart = collections.defaultdict(lambda: [0, 0.0])
for r in sw:
    k = (r["action"].split(" - ")[0], str(r["patientid"])); bychart[k][0] += 1; bychart[k][1] += float(r.get("balance") or 0)
swtxt = "; ".join("%d %s chart %s ($%.0f)" % (v[0], k[0], k[1], v[1]) for k, v in sorted(bychart.items())) or "nothing asked"
al = json.load(open("registers/admit_lookup_%s.json" % S)); nochart = sum(1 for x in al["lookups"] if not x["charts"])
plans = json.load(open("registers/plan_check_%s.json" % S))["charts"]; zero = [p for p in ("17478059", "17478063", "17478064") if not plans.get(p)]
errors = eng.get("errors", []) + [e for s in eng.get("steps", []) for e in s.get("errors", [])]
ERATXT = ("GitHub slot #129 (19:23:00-19:28:57Z, 6 minutes late) read %d checks / $%.2f unposted -> %d / $%.2f, posted $%.2f; this run's pre-slot read (era_list.py 19:25Z): %d checks / $%.2f; this run's engine pass (19:29:57-19:33:46Z, after the slot): %d checks / $%.2f before -> %d / $%.2f after, era_post $%.2f, era_clear 0 dismissed / 0 held; no new remit arrived since the 1710Z run; nothing posted, nothing cleared; 1053220 takeback pair (chart 17474741 v19455454) stays dismissed outside the routine, lines still unposted - William's decision"
          % (ss["era"]["before"]["checks"], ss["era"]["before"]["unposted"], ss["era"]["after"]["checks"], ss["era"]["after"]["unposted"], ss["posted"]["pay"], nb0, tb0, nb, tb, na, ta, es["posted"]["pay"]))
rows = []
def add(col, state, patient="", dos="", carrier="", err="", action="", check="", visit="", amt=""):
    rows.append({"column": col, "state": state, "patient": patient, "dos": dos, "carrier": carrier, "error": err, "action": action, "check": check, "visit": visit, "amount": amt})
add("charge review", "clear", action="%d -> %d charges" % (cb["charge_review"], ca["charge_review"])); add("claim inspector", "clear", action="%d -> %d batches" % (cb["claim_inspector"], ca["claim_inspector"]))
for pid, vids in (("17478059", "v19457778 / v19457794"), ("17478063", "v19457783 / v19457797"), ("17478064", "v19457784 / v19457791")):
    add("unbilled", "remaining", "chart %s" % pid, "99223 10/12 + 99232 10/13/2026", "(no plan on chart - live getdemographic 19:24Z: %d insplans)" % len(plans.get(pid, [])), "Insurance order is missing on visit", "held - HCA Florida Capital facesheet (admit 10/12/2026) on William's turn", visit=vids, amt="421.00")
add("exclusions", "remaining", "chart 17470713 (AARP Medigap secondaries)", "4/2026-7/2026", "AAR01", "PA ACK,RETURND AS UNPRCESSBLE CLM - subscriber id not found (claim run 1700302, 25 rows)", "held - AARP member number on William's turn (live plans 19:24Z unchanged: BCBS ended 12/31/2022, MA plan ended 3/31/2026, Medicare seq 3, AAR01 seq 4)")
for vid, dos, fee in (("19431511", "02/03/2026", "310.00"), ("19435174", "03/08/2026", "310.00"), ("19435175", "03/09/2026", "163.00")):
    add("exclusions", "remaining", "chart 17471204", dos, "AET07", "PA ACK RETURND AS UNPRCESSBLE: ENTITY NOT ELIGIBLE FOR BENEFITS FOR SUBMITTED DOS: PATIENT (run 1700311)", "held for William - subscriber relationship / Feb 2026 HCA facesheet", visit=vid, amt=fee)
add("exclusions", "remaining", "chart 24750", "09/20/2026", "AET12", "CH FH PREF0288 INVALID PAYER ID/CPID 814723941 + PREF0264 (v19455937, run 1700294)", "held - carrier master (board row aet12-carrier-cpid)")
add("era", "summary", action=ERATXT)
add("era", "remaining", "chart 17474741", "09/20/2026", "FLO02", "check 1053220 Medicare 820007360: takeback pair on v19455454 - dismissed outside the routine 05:37Z 10/21, both lines unposted", "William's decision stands", check="1053220", visit="v19455454", amt="-85.46")
for r in sw: add("uni20/bcbs pre-5/1 sweep (pass %d)" % npass, "sweep", "chart %s" % r.get("patientid"), r.get("dos", ""), r.get("carrier", ""), r.get("action", ""), "277 answer recorded, nothing sent", visit="v%s" % r.get("visitid", ""), amt=r.get("balance", ""))
add("pam admits", "waiting", "pending Pam admits (Tapestry NA 10/15 + 10/17 re-send; Brynwood NA 10/15 x2; Brynwood NA 10/19 + 10/20 re-send; Center Pointe 10/20)", action="lookuppatient 19:24Z by full name pattern: %d of %d patterns still have no AMD chart (hits: namesake chart 25746 - different DOB; readmit charts 17474046 and 17472553 + duplicate 21086); waiting on the Claimocity feed" % (nochart, len(al["lookups"])))
add("github button", "watch", action="GitHub slot #129 ran 19:23:00-19:28:57Z (6 minutes late); this run polled the workflow until it completed and ran its own engine pass 19:29:57-19:33:46Z afterwards - no overlap")
for e in errors: add("engine", "error", action=str(e))
csvname = "_run report 10-21 1910.csv"
with open(csvname, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
errtxt = "; ".join(str(e) for e in errors) or "none"
sec = """## %s - backend billing run, 3 PM ET 10/21/2026 slot (ehpa cloud) - 19:10-%sZ 10/21

Bootstrap: repo ATTACHED (origin/main feddbd0 at start, 8d685c5 after slot #129; session branch claude/pensive-einstein-5i1oc0; main checked out; symlinked as /home/claude/effinger-billing-backend; layout 1191 helper files, required helpers all present - optional era_details_pull.py / columns_inspector2_0908.py / github_sync.py absent as usual); network AMD OK / Stedi proxy credential OK / GitHub attached; AMD_PSW environment credential (no credential file); ONE login (plan_check_%s.py 19:24Z, token reused by every later helper and the engine pass), no lock, no 429. State bundle: Drive 'workspace mirror' still lists nothing newer than workspace_state_2026-09-18 - superseded by main, not restored; pseudonyms.json (Drive 10/21 17:55Z, 410 names) in both secrets/ copies; deceased_cache.json (Drive 10/16) merged into the workspace cache (76 dated, 0 scrubbed after the engine pass), repo copy kept scrubbed. v12 precondition: all pass. Learned from others: git log 36h = this routine + the GitHub Billing Button slots; SHARED_LESSONS lines newer than 17:50Z: none; 0 applied. Guard: 1710Z START has its RUN COMPLETE digest (17:57Z); START 1910Z uploaded 19:13Z, lock written, deleted at the end.
Sources: Insurance Refresh Board (read_db): Claude's-turn rows re-read (first 200, standing rows unchanged), drops 0; Working Denials queue 0; Mandatory Approvals page 0 approved (register 93 done, 0 waiting). Drive: nothing new in 'bht Optum era downloads', 'treasury payments', the facesheet folders or the Claimocity drop since 10/20 (only the 2310Z 10/20 run report CSV); Pam Gmail (7d): the same nine admit threads of 10/15-10/20, all already worked; admit lookup: %d of %d name patterns without an AMD chart. Neither board registry lists a current inbox file in its applied map - no inbox file trashed.
Columns (engine columns_scan) %s: CHARGE REVIEW 0; CLAIM INSPECTOR 0; UNBILLED the three zero-plan HCA charts %s (live getdemographic 19:24Z: 0 insplans on all three, $1,263, William's turn); EXCLUSIONS: chart 17470713's 25 AARP secondaries (run 1700302), chart 17471204's three AET07 rows (run 1700311, $783), the AET12 chart-24750 row (run 1700294) - standing holds, no new claim run row.
ERA (step 5): %s. Availity step 5(g): no new Availity PDF or Check/EFT export - nothing to parse, post or reconcile.
UNI20/BCBS pre-5/1 pass %d (engine sweep): %d asked ($%.2f): %s; engine summary: %s; 0 sent, 0 written off.
Writes this run (AdvancedMD): none - the engine pass ran its columns/era/sweep steps and found nothing to write (see reports/button/%s.json). Dollars re-sent $0. Write-offs: none. Permission classifier: nothing refused. Script errors: %s.
Waiting on William: takeback decision chart 17474741 v19455454 (ERA 1053220); VA referral for chart 17478013; HCA Florida Capital facesheets (admit 10/12/2026) for charts 17478059 / 17478063 / 17478064 ($1,263); chart 17471204 AET07 x3; AARP member number chart 17470713; AET12 carrier master (chart 24750); chart 17474290 appeal-or-write-off (CO-97, $310); chart 17473501 payer for $122.29 coinsurance. Six Pam admit name patterns without an AMD chart - waiting on the Claimocity feed.
Helpers this run: plan_check_%s.py, admit_lookup_%s.py, poll_slot_1910.sh, run_outputs_%s.py (all read-only). Calls captured: 0 new shapes; 0 vocabulary entries added.
""" % (S, NOW[11:16].replace(":", ""), "1021_1910", nochart, len(al["lookups"]), cols, " / ".join(zero) if zero else "(none - plans entered)", ERATXT, npass, len(sw), sum(float(r.get("balance") or 0) for r in sw), swtxt, str({s.get("name"): s for s in eng.get("steps", [])}.get("sweep", {}).get("summary", "")), E, errtxt, "1021_1910", "1021_1910", "1021_1910")
open("needs_facesheet_list.md", "a").write("\n" + sec); open("needs_facesheet_list_section_%s.md" % S, "w").write(sec)
chk = lambda txt, ok="na": {"checks": [{"ok": ok, "result": txt, "src": SRC, "when": W}]}
prev = {op["id"]: op for op in json.load(open("inbox/board_updates_1510_prev.json"))["ops"]}   # real row ids, workspace only
byamd = {pid: next(i for i in prev if i.endswith("-" + pid)) for pid in ("17478059", "17478063", "17478064", "17474741", "17478013")}
hold = "3 PM ET 10/21: chart %s still has zero insurance plans (live getdemographic 19:24Z 10/21; Unbilled list unchanged); no new HCA / TMH / PCC facesheet, Pam email or board note - the two visits (%s, $421) stay in Unbilled on your turn."
ops = [{"op": "upsert", "collection": "items", "id": "availity-remits-backlog", "append": chk("3 PM ET 10/21: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (nothing new there since 10/20); no new facesheet or Claimocity file; Working Denials queue 0; board drops 0; approvals 0 approved / 0 waiting; Pam Gmail: the nine 10/15-10/20 admit threads, all worked. ERA Center: " + ERATXT + ". Columns " + cols + " - every row a standing hold; UNI20/BCBS pre-5/1 pass %d: %s, 0 sent." % (npass, swtxt))},
       {"op": "upsert", "collection": "items", "id": "aet12-carrier-cpid", "append": chk("3 PM ET 10/21: HOLD - the one AET12 PREF0288 exclusion row (chart 24750, v19455937, run 1700294) stays on the list, not rebilled; carrier master still unchanged.")},
       {"op": "upsert", "collection": "items", "id": byamd["17478059"], "append": chk(hold % ("17478059", "v19457778 / v19457794"), "human")},
       {"op": "upsert", "collection": "items", "id": byamd["17478063"], "append": chk(hold % ("17478063", "v19457783 / v19457797"), "human")},
       {"op": "upsert", "collection": "items", "id": byamd["17478064"], "append": chk(hold % ("17478064", "v19457784 / v19457791"), "human")},
       {"op": "upsert", "collection": "items", "id": "poulter-ellery-gwen-denials", "append": chk("3 PM ET 10/21: the 25 AARP Medigap secondary rejections of claim run 1700302 stay on the exclusion list (live plans 19:24Z unchanged: BCBS ended 12/31/2022, MA plan ended 3/31/2026, Medicare seq 3, AAR01 seq 4) - AARP member number still needed.", "human")},
       {"op": "upsert", "collection": "items", "id": "tully-tracy", "append": chk("3 PM ET 10/21: the three Aetna AET07 rejections of claim run 1700311 (v19431511 / v19435174 / v19435175, $783) stay on the exclusion list, held for your subscriber-relationship answer / the Feb 2026 HCA facesheet.", "human")},
       {"op": "upsert", "collection": "items", "id": byamd["17478013"], "append": chk("3 PM ET 10/21: VACCN plan unchanged (seq 1, begin 10/15/2025, live 19:24Z); ERA 1053239 (8 x CO-288 'referral absent', $1,430) stays dismissed; the 2026 VA referral / authorization number for the 10/5/2026 HCA admission is still needed before the 8 visits are re-sent.", "human")},
       {"op": "upsert", "collection": "items", "id": byamd["17474741"], "append": chk("3 PM ET 10/21: ERA check 1053220 (Medicare 820007360, the takeback pair on v19455454: reversal -85.46 of check 819919368 + CO-236 $0) still dismissed outside the routine (05:37Z 10/21), both lines unposted on the visit - your decision stands.", "human")}]
json.dump({"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}, open("board_updates_%s.json" % S, "w"), indent=1)
add_md = """## 2026-10-21 19:10Z - backend billing run, 3 PM ET 10/21/2026 (ehpa cloud, repo attached)
No new call shapes this run. Calls used (all in the registry): login (one, plan_check_1021_1910.py 19:24Z), getdemographic x7 (plan_check), lookuppatient x9 (admit_lookup), GET /api/era/checks (era_list.py 19:25Z pre-slot and the engine's before/after), getclaimcenteroverview + the four list calls (columns_scan before 19:25Z and the engine's before/after), the engine's inspector / unbilled / exclusion helpers (nothing to act on), era_post.py --all-unposted + era_clear.py on an empty Center, Stedi 276/277 (engine sweep, 17 visits). GitHub slot #129 19:23:00-19:28:57Z (report reports/button/2026-10-21T1923Z.json); engine pass 19:29:57-19:33:46Z (report reports/button/2026-10-21T1929Z.json). No AMD write.
"""
open("captured_calls_additions_2026-10-21_1910UTC-3pmET-ehpa-cloud.md", "w").write(add_md)
lessons = ["- %s | backend billing run | WATCH | columns %s (standing holds: three zero-plan HCA charts 17478059/17478063/17478064, chart 17470713 AARP x25, chart 17471204 AET07 x3, AET12 chart 24750); ERA: %s; UNI20/BCBS pre-5/1 pass %d: %s, 0 sent; %d Pam admit name patterns still without a chart; no AMD write by this container; GitHub slot #129 19:23:00-19:28:57Z waited for before the engine pass 19:29:57-19:33:46Z | reports/button/%s.json" % (NOW, cols, ERATXT, npass, swtxt, nochart, E)]
open("shared_lessons_%s.txt" % S, "w").write("\n".join(lessons) + "\n")
digest = """# %s run digest - backend billing run, 3 PM ET 10/21/2026 (ehpa cloud, repo attached)

%s
## Mirror
- (filled by the run after the mirror step)

## SHARED LESSONS
%s
""" % (S, sec, "\n".join(lessons))
os.makedirs("chat_history", exist_ok=True); open("chat_history/%s run digest.md" % S, "w").write(digest)
print("wrote", csvname, "rows", len(rows), "| ops", len(ops), [o["id"][-9:] for o in ops], "| needs section", len(sec), "chars")
