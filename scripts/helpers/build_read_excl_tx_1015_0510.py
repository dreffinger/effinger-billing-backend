# Rebuilds work/read_excl_tx.json for excl_1015_0510.py from the 1 AM run's dry register (row list) + a LIVE gettxhistory per visit. Read-only.
import sys; sys.path.insert(0, "/home/claude/unbilled")
import json, time, txh
reg = json.load(open("registers/excl_1015_0510_dry.json"))
ERRS = {"BCBS": ["CH FH PREF0283 MISSING PAYER DOC CONTROL NUM"], "AET07": ["ACK RETURNED AS UNPROCESSABLE CLAIM"], "AET12": ["PREF0288"]}
recs = []
for sec in ("A", "B", "C", "held"):
    for r in reg.get(sec, []): recs.append(r)
seen = set(); ex = []; tx = {}
for r in recs:
    key = (r["pid"], r["vid"])
    if key in seen: continue
    seen.add(key)
    root = txh.fetch_visit(r["pid"], r["vid"]); rows = []
    for c in root.iter("charge"):
        if c.get("visit") != str(r["vid"]): continue
        row = dict(c.attrib); row["payments"] = [dict(p.attrib) for p in c.iter("payment")]
        rows.append(row)
    tx["%s:%s" % (r["pid"], r["vid"])] = rows
    ex.append({"vid": r["vid"], "pid": r["pid"], "claimid": r["claimid"], "run": r["run"], "carrier": r["carrier"], "errs": ERRS.get(r["carrier"], ["unclassified"]), "charges": [{"dos": r["dos"]}]})
    time.sleep(0.25)
json.dump({"built": "2026-10-15T2316Z go rebuild from registers/excl_1015_0510_dry.json + live txh", "exclusions": ex, "tx": tx}, open("work/read_excl_tx.json", "w"), indent=1)
print("exclusions", len(ex), "tx visits", len(tx), "by section in dry register:", {s: len(reg.get(s, [])) for s in ("A", "B", "C", "held")})
openA = sum(float(c.get("insbal") or 0) for e in ex if e["run"] == "1700302" and e["carrier"] == "BCBS" for c in tx["%s:%s" % (e["pid"], e["vid"])] if c.get("void") != "1")
print("live open insurance balance on the BCBS run-1700302 rows now: %.2f" % openA)
