# PLAIN ENGLISH (Claim Inspector advisory sweep, first written 10/5/2026 5 AM ET slot - ehpa cloud copy)
# Decides: which Claim Inspector holds are ADVISORY-ONLY by William's standing rules and clears them with
# bypassclaimedits - timely-filing 20657 (bypass + submit, the denial documents any write-off; a secondary is
# timely from the primary's remit anyway), unspecified-laterality 11256 (bypass + log to laterality_flag_log.md),
# Medicare MUE 33799, CCM add-on / frequency advisories 35790 7011 3429 35777, mod-25 4426, provider-history 4310,
# AWV 27261. A visit is touched only when EVERY error on it is one of those patterns.
# Reads the fresh scan summary (python3 columns_scan.py <tag> <dir> run moments before - error ids change on every
# re-inspection) given as the first argument; --dry (default) prints the plan, --live sends the bypass calls.
# Never touches: missing-data holds (hospitalization date 117065068, CCI 24078, sequela-first 20389, anything not
# in the list), paid visits are irrelevant here (bypass changes no money). Register: registers/insp_bypass_<stamp>.json
import amd, json, re, sys, time, datetime, os
ADVISORY = {"20657", "11256", "33799", "35790", "7011", "3429", "35777", "4426", "4310", "4311", "27261"}   # 4311 added 10/14 (new-patient-in-history advisory, as insp_1013_1910.py)
summary_path = [a for a in sys.argv[1:] if not a.startswith("--")]
if not summary_path:
    print("usage: python3 insp_bypass_advisories.py <scan_dir>/summary_<tag>.json [--live]"); sys.exit(2)
live = "--live" in sys.argv
stamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H%MZ")
S = json.load(open(summary_path[0]))
insp = S.get("inspector") or {}
plan, held = [], []
for batch, visits in insp.items():
    for v in visits:
        errs = v.get("errs") or []
        pats = [(e[0], (re.search(r"Pattern (\d+)", e[1] or "") or [None, None])[1], e[1] or "") for e in errs]
        if errs and all(p in ADVISORY for _, p, _ in pats):
            plan.append({"batch": batch, "vid": v["vid"], "pid": v.get("pid"), "errids": [i for i, _, _ in pats],
                         "patterns": [p for _, p, _ in pats],
                         "lat": [(re.search(r"code\(s\) (\w+)", t) or [None, None])[1] for _, p, t in pats if p == "11256"]})
        else:
            held.append({"batch": batch, "vid": v["vid"], "pid": v.get("pid"), "patterns": [p for _, p, _ in pats]})
print("plan: %d visits to bypass, %d held" % (len(plan), len(held)), flush=True)
for h in held: print("  HOLD", h["vid"], "pat" + str(h["pid"]), h["patterns"])
from collections import Counter
print("  patterns in plan:", Counter(p for x in plan for p in x["patterns"]))
reg = {"stamp": stamp, "live": live, "source": summary_path[0], "held": held, "done": [], "failed": []}
if live:
    amd.login_cached()
    for x in plan:
        body = '<visitlist><visit id="%s"><claimeditlist>%s</claimeditlist></visit></visitlist>' % (
            x["vid"], "".join('<claimedit id="%s"/>' % e for e in x["errids"]))
        r = amd.post(amd.msg("bypassclaimedits", "chargeentry", {"nocookie": "1"}, body))
        ok = "Fault" not in r
        (reg["done"] if ok else reg["failed"]).append({**x, "resp": re.sub(r"\s+", " ", r)[:160]})
        print("  bypass", x["vid"], "pat" + str(x["pid"]), x["patterns"], "OK" if ok else "FAULT " + r[:120], flush=True)
        for code in x["lat"]:
            if code:
                with open("laterality_flag_log.md", "a") as f:
                    f.write("- %s run %s: pat%s visit %s - Pattern 11256 unspecified laterality %s bypassed (billing hold only); William to confirm the laterality\n" % (
                        datetime.date.today().strftime("%m/%d/%Y"), stamp, x["pid"], x["vid"], code))
        time.sleep(0.4)
else:
    for x in plan: print("  DRY bypass", x["vid"], "pat" + str(x["pid"]), x["patterns"], "lat=" + str(x["lat"]) if x["lat"] else "")
    reg["planned"] = plan
os.makedirs("registers", exist_ok=True)
out = "registers/insp_bypass_%s%s.json" % (stamp, "" if live else "_dry")
json.dump(reg, open(out, "w"), indent=1)
print("register", out, "done=%d failed=%d" % (len(reg["done"]), len(reg["failed"])))
