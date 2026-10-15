# PLAIN ENGLISH (run report, 11 AM ET 10/15/2026 slot, run 2026-10-15T1510Z) - READ ONLY.
# Decides: nothing. Builds "_run report 10-15 1510.csv" (per column: remaining rows with chart id, visit, DOS/CPT where the
# scan carries them, carrier, error text and the standing action) from scan_2026-10-15/summary_before.json, the ERA list
# registers/era_checks_before_<stamp>.json, the sweep register and the approvals register. Never touches AMD.
import json, csv, re, collections
S = "2026-10-15T1510Z"
s = json.load(open("scan_2026-10-15/summary_before.json"))
appr = json.load(open("/home/claude/effinger-billing-backend/practices/ehpa/registers/approvals_pending.json"))
items = appr.get("items") if isinstance(appr, dict) else appr
card_by_chart = collections.defaultdict(list)
for it in items:
    if it.get("status") != "waiting": continue
    for pid in set(re.findall(r"chart (\d+)", it.get("what") or "")): card_by_chart[pid].append(it["id"])
rows = []
HOLD = {"23177": "CCI 24078 / 15775 hold (99309 + 99489) - standing hold", "44983": "duplicate 99239 2023 - standing hold", "22845": "TRI05 carrier file - standing hold (Olson/TRI05)", "17472519": "standing inspector hold"}
for b, vs in s["inspector"].items():
    for v in vs:
        rows.append(["Claim Inspector", "remaining", "pat%s" % v["pid"], v["vid"], "", "", "; ".join(e[1][:90] for e in v["errs"]), HOLD.get(v["pid"], "standing hold")])
for r in s["unbilled"]:
    pid = r["patientid"]; cards = ",".join(card_by_chart.get(pid, []))
    act = ("approval card %s waiting" % cards) if cards else ("inspector hold visit" if pid in HOLD else "on William's turn (board row: CHP id / facesheet)")
    rows.append(["Unbilled", "remaining", "pat%s" % pid, r["id"], "", r.get("carriercode") or "", "; ".join(r["_errs"])[:120], act])
ex = collections.Counter()
for run, vs in s["exclusions"].items():
    for v in vs:
        e = v.get("_errs") or [""]; e = e[0] if isinstance(e, list) else str(e)
        ex[(run, v.get("patientid"), v.get("carriercodeshort") or v.get("carriercode"), str(e)[:60])] += 1
for (run, pid, car, err), n in sorted(ex.items()):
    cards = ",".join(card_by_chart.get(str(pid), []))
    act = ("approval card %s waiting" % cards) if cards else ("AET12 carrier CPID - board row aet12-carrier-cpid, held" if car == "AET12" else "held (chart 17472859: Medicaid 271 unreadable at DOS)" if str(pid) == "17472859" else "standing hold")
    rows.append(["Exclusions", "remaining x%d" % n, "pat%s" % pid, "run %s" % run, "", car, err, act])
rows.append(["ERA", "remaining", "", "check 1053116", "", "UHC W0020208", "$71.00 unposted - OA-18 pair settled, CO-29 reversal AMD cannot match", "held for William's takeback decision (no takeback posting rule)"])
sw = json.load(open("registers/uni20_bcbs_pre0501_eval_%s.json" % S))
rows.append(["UNI20/BCBS pre-5/1 sweep", "pass 105", "", "", "", "UNI20,BCBS", "asked %s: %s" % (sw["asked"], sw["by_action"]), "0 candidates, 0 sent"])
with open("_run report 10-15 1510.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["column", "status", "chart", "visit/run", "dos/cpt", "carrier", "error", "action"]); w.writerows(rows)
print(len(rows), "rows")
