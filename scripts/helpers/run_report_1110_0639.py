#!/usr/bin/env python3
# PLAIN ENGLISH (report of the 2026-11-10T0639Z columns run, 1:39 AM ET Tue 11/10, ehpa cloud Code routine, six-hourly slot)
# Decides: nothing. Reads the engine report (reports/button/<stamp>-engine.json) and writes this run's needs_facesheet section
#   (appended to needs_facesheet_list.md + a per-run copy for Drive) and the run report CSV for SendUserFile. Names only in the
#   CSV (William's channel); chart ids elsewhere.
import json, csv, os
STAMP = "2026-11-10T0639Z"
IDS = json.load(open("secrets/run_0639_ids.json"))   # PHI identifiers live here, never in the script
def fill(x):
    if isinstance(x, str):
        for k, v in IDS.items(): x = x.replace("{{%s}}" % k, v)
        return x
    if isinstance(x, list): return [fill(i) for i in x]
    if isinstance(x, dict): return {k: fill(v) for k, v in x.items()}
    return x
rep = json.load(open("/home/claude/effinger-billing-backend/reports/button/%s-engine.json" % STAMP))
s = rep["summary"]; cb = s["columns"]["before"]; ca = s["columns"]["after"]; eb = s["era"]["before"]; ea = s["era"]["after"]
K = ("charge_review", "claim_inspector", "unbilled", "exclusions")
cols = "Columns %s -> %s" % ("/".join(str(cb.get(k, "?")) for k in K), "/".join(str(ca.get(k, "?")) for k in K))
era = "ERA %s checks $%.2f -> %s checks $%.2f" % (eb.get("checks", "?"), float(eb.get("unposted", 0) or 0), ea.get("checks", "?"), float(ea.get("unposted", 0) or 0))
posted = s.get("posted", {}); resent = s.get("resent", {}); wo = s.get("written_off", {})
steps = "; ".join("%s: %s - %s" % (st.get("title"), st.get("status"), (st.get("summary") or "")[:160]) for st in rep.get("steps", []))
wait = rep.get("waiting", []); errs = rep.get("errors", [])
sec = ["", "## %s - 1:39 AM ET Tue 11/10/2026 backend billing run (ehpa cloud, six-hourly slot)" % STAMP,
 "- %s (engine pass tools/button/run_all.py --mode live --profile columns --stedi-proxy from 06:48Z, report reports/button/%s-engine.json, status %s, errors %d). Charge Review 0. Claim Inspector 2 = chart 22322 Pattern 4531 x2 (v19460343 / v19460347, $603, coding call - William). Unbilled 0. Exclusions 2 = AET12 chart 24750 v19455937 PREF0288+PREF0264 ($315, carrier master) and CIG09 chart 17478318 v19460525 ($111, dental-only Cigna plan - HCA facesheet on William's turn since 11/9). Steps: %s" % (cols, STAMP, rep.get("status"), len(errs), steps),
 "- %s; auto-posted $%.2f (WOINS %.2f, WOCAID2ND %.2f, WOLATE %.2f); re-sent %s visits / $%.2f; written off %s / $%.2f; manual-posted 0 lines; residuals $0; orphans 0; takebacks 0; refused commands 0. Availity 5(g): no new PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' since 19:00Z 11/9; Treasury: nothing to reconcile." % (era, float(posted.get("pay", 0) or 0), float(posted.get("woins", 0) or 0), float(posted.get("wocaid2nd", 0) or 0), float(posted.get("wolate", 0) or 0), resent.get("visits", 0), float(resent.get("dollars", 0) or 0), wo.get("count", 0), float(wo.get("dollars", 0) or 0)),
 "- FEED: gcs 22 objects, 0 new (newest 20261109) - Claimocity feed: nothing new; retry-dx nothing to retry; feed_monitor refreshed (week 158 visits / $26,031; month 953 / $202,812; 39 holds) and committed. Practice database: this run's 3 docs (feed_checks 1, snapshots 2) written (ArtifactData batch, 926 docs on the page), Neon load-writes 3 new, register committed.",
 "- Sources: Working Denials queue 0; board drops 0; rows William changed after opening the board at 04:18Z 11/10: 0; facesheet folders (hca / tmh / PCC), Optum era, treasury, project files: nothing new since 19:00Z 11/9; Pam Gmail (2d): TWO new Centrepointe admit emails - 00:43Z ORCHARD, BETHAN C (new admit 11/09/2026 from TMH; chart 17469476 found by name + DOB; the chart's only plan = the sheet's CHP policy {{ORCHARD_POL}}, AMD 271 ACTIVE; blank address line 1 filled with {{ORCHARD_ADDR}} via addr_line1_fix) and 01:04Z THORNEY, MARCELLA H (readmit 11/07/2026 from TMH; chart 25994: Medicare {{THORNEY_MBI}} + BCBS Medigap {{THORNEY_POL}} = the sheet, both ACTIVE, nothing changed). Both emails arrived after the 00:39Z run began; that run posted a START but NO RUN COMPLETE digest - its evening extras (precheck, 'current face sheets needed' email, Drive CSV) did not run on 11/9 evening.",
 "- FACESHEET NEEDED: no new patient this run (standing: chart 17478318 HCA facesheet, chart 17478319, chart 17478345 duplicate-chart decision, chart 22322 coding call, AET12 carrier master).",
 "- Not an evening run (start 06:39Z) - no precheck / 'current face sheets needed' email / Drive CSV copy. Waiting (engine): %s" % ("; ".join(wait) or "none")]
sec = fill(sec)
open("needs_facesheet_list.md", "a").write("\n".join(sec) + "\n")
open("needs_facesheet_list_%s.md" % STAMP, "w").write("\n".join(sec) + "\n")
rows = [["column", "status", "patient", "chart", "dos", "carrier", "error / item", "action"]]
rows.append(["claim inspector", "remaining", "(chart 22322)", "22322", "11/07/2026", "FLO02", "Pattern 4531 hospital E&M at non-hospital location x2 (v19460343, v19460347) $603", "coding call - William"])
rows.append(["exclusions", "remaining", "(chart 24750)", "24750", "", "AET12", "run 1700294 v19455937 PREF0288 INVALID PAYER ID/CPID + PREF0264 $315", "standing hold - carrier master (William)"])
rows.append(["exclusions", "remaining - held", "(chart 17478318)", "17478318", "11/07/2026", "CIG09", "run 1700365 v19460525 99232 $111 ENTITY NOT ELIGIBLE - chart plan is Cigna DENTAL", "HCA facesheet / card - William (row since 11/9)"])
rows.append(["pam admit", "verified - address fixed", "ORCHARD, BETHAN C", "17469476", "11/09/2026 admit (TMH)", "CAP07", "Centrepointe admission record: CHP policy {{ORCHARD_POL}} = chart plan (271 ACTIVE), MBI {{ORCHARD_MBI}} printed; address line 1 was blank -> {{ORCHARD_ADDR}}", "new board row orchard-bethan-17469476 (claude)"])
rows.append(["pam admit", "verified - no change", "THORNEY, MARCELLA H", "25994", "11/07/2026 readmit (TMH)", "FLO02", "Centrepointe admission record: Medicare A {{THORNEY_MBI}} + BCBS {{THORNEY_POL}} = chart plans, both ACTIVE", "append on thorney-marcella-25994"])
rows.append(["feed", "nothing new", "", "", "", "", "gcs 22 objects, 0 new, newest 20261109", "one line; retry-dx nothing"])
rows.append(["era", "none", "", "", "", "", era, "nothing to post"])
rows.append(["routine", "gap", "", "", "", "", "00:39Z 11/9 evening run: START posted, no RUN COMPLETE digest, no commit", "evening extras (precheck, facesheets email, Drive CSV) did not run - William"])
rows = fill(rows)
csv.writer(open("_run report 11-10 0139.csv", "w", newline="")).writerows(rows)
print(cols, "|", era, "| waiting:", wait, "| errors:", errs, "| csv rows", len(rows) - 1)
