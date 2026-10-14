# PLAIN ENGLISH (Patient-balance review - one Stedi insurance discovery per Medicare patient with cost-sharing and no supplement)
# Decides: nothing. For every patient in the STATEMENT-MEDICARE bucket (Medicare paid, coinsurance on the patient, no supplement
#   on the chart), asks Stedi insurance discovery ($1.50) with the chart name + DOB and the most recent open DOS whether any
#   other coverage exists (a Medigap, a secondary, Medicaid). Writes patbal_discovery_1013.json; nothing is added to a chart here.
# Never touches: AMD writes.
import json, re, time, sys, collections
import amd, precheck, stedi
D = json.load(open("patbal_review_1013.json"))["rows"]
rows = [r for r in D if r["bucket"] == "STATEMENT-MEDICARE"]
bypid = collections.defaultdict(list)
for r in rows: bypid[r["pid"]].append(r)
MX = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 10**9
out = {}
try: out = json.load(open("patbal_discovery_1013.json"))
except Exception: pass
amd.login_cached(); n = 0
for pid, rs in bypid.items():
    if pid in out: continue
    if n >= MX: break
    try:
        pa, pl = precheck.plans(pid)
        nm = pa.get("name") or rs[0]["patient"]; last, first = nm.split(",")[0].strip(), nm.split(",")[-1].strip().split(" ")[0]
        dob = pa.get("dob", ""); dobc = dob[6:] + dob[:2] + dob[3:5] if dob else ""
        dos = max(r["dos"] for r in rs).replace("-", "")
        j = stedi.disc(first, last, dobc, "FL", dos); s = stedi.disc_summ(j)
        out[pid] = {"dos": dos, "bal": round(sum(r["patbal"] for r in rs), 2), "charges": len(rs), "found": s["found"], "items": s["items"], "errors": s["errors"]}
        print(pid, "$%.2f" % out[pid]["bal"], "found", s["found"], [(i["payer"], i["status"], i["plan"]) for i in s["items"]][:3], (s["errors"] or [""])[:1], flush=True)
    except Exception as e:
        out[pid] = {"error": str(e)[:120]}; print(pid, "ERR", str(e)[:100], flush=True)
    n += 1; json.dump(out, open("patbal_discovery_1013.json", "w"), indent=0); time.sleep(0.4)
hits = {k: v for k, v in out.items() if v.get("found")}
print("done: %d patients asked, %d with coverage found ($%.2f of cost-sharing on those charts)" % (len(out), len(hits), sum(v["bal"] for v in hits.values())))
