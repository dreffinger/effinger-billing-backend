# PLAIN ENGLISH (Weekly metrics verification + run extras)
# Decides: Nothing. Cross-checks the massrebillsearch unpaid total against the gettxhistory open insurance balances
# of the same patients (the step-5 verification of the weekly practice metrics run), and totals a few run extras
# the report quotes: rebills in the last 7 days (registers/rebill_log.jsonl), the timely-filing watch
# (tf_writeoff_watch.json), the week's Mandatory Approvals packages (approvals_pending.json) - ids and dollars only.
# Rules it uses: read-only; RUN_DATE env var (YYYY-MM-DD) picks unpaid_<stamp>.json / metrics_txh_cache_<stamp>.json.
# Never touches: AMD.
# ---
import json, os, datetime, collections
WS = "/home/claude/unbilled"; os.chdir(WS)
RUN = os.environ.get("RUN_DATE") or datetime.date.today().isoformat(); STAMP = RUN.replace("-", "")
REG = os.environ.get("REGISTERS", "/home/claude/effinger-billing-backend/practices/ehpa/registers")
D7 = (datetime.date.fromisoformat(RUN) - datetime.timedelta(days=7)).isoformat()

def money(s):
    try: return float(s or 0)
    except Exception: return 0.0

unp = json.load(open("unpaid_%s.json" % STAMP))
cache = json.load(open("metrics_txh_cache_%s.json" % STAMP))
out = {"run_date": RUN}

# ---- verification: unpaid list (by last-billed carrier) vs live open insurance balances on the same patients ----
pids = sorted({str(v["patientid"]) for v in unp})
unp_total = sum(money(v.get("insbalance")) for v in unp)
unp_by_car = collections.defaultdict(float)
for v in unp: unp_by_car[(v.get("carriercode") or "").strip() or "NONE"] += money(v.get("insbalance"))
txh_total = 0.0; txh_by_car = collections.defaultdict(float); missing = 0
for pid in pids:
    rec = cache.get(pid)
    if not rec or rec.get("error"): missing += 1; continue
    seen = set()
    for ch in rec["charges"]:
        if ch.get("void") == "1" or ch["id"] in seen: continue
        seen.add(ch["id"])
        b = money(ch.get("insbal"))
        if b > 0:
            txh_total += b; txh_by_car[(ch.get("carrier") or "").strip() or "NONE"] += b
out["verification"] = {"unpaid_patients": len(pids), "patients_missing_in_scan": missing,
                       "massrebillsearch_total": round(unp_total, 2), "txh_open_ins_balance_same_patients": round(txh_total, 2),
                       "gap_pct": round((txh_total - unp_total) / unp_total * 100, 1) if unp_total else None,
                       "by_carrier": {c: {"unpaid_list": round(unp_by_car.get(c, 0.0), 2), "txh_open": round(txh_by_car.get(c, 0.0), 2)}
                                      for c in sorted(set(unp_by_car) | set(txh_by_car), key=lambda c: -max(unp_by_car.get(c, 0), txh_by_car.get(c, 0)))[:14]}}

# ---- rebills last 7 days ----
n = 0; vis = set(); by = collections.Counter()
try:
    for line in open(os.path.join(REG, "rebill_log.jsonl")):
        try: r = json.loads(line)
        except Exception: continue
        if (r.get("at") or "")[:10] >= D7: n += 1; vis.add(r.get("visit")); by[r.get("by")] += 1
except FileNotFoundError: pass
out["rebills_7d"] = {"entries": n, "visits": len(vis), "by_helper": dict(by)}

# ---- timely-filing watch ----
try:
    tf = json.load(open(os.path.join(REG, "tf_writeoff_watch.json")))
    items = tf.get("items", [])
    op = [i for i in items if i.get("status") == "open"]
    out["tf_writeoff_watch"] = {"items": len(items), "open_items": len(op), "open_visits": sum(len(i.get("visits") or []) for i in op),
                               "open_total": round(sum(money(i.get("total")) for i in op), 2),
                               "closed_items": sum(1 for i in items if i.get("status") == "closed"),
                               "open_by_carrier": dict(collections.Counter(i.get("carrier") for i in op))}
except Exception as e:
    out["tf_writeoff_watch"] = {"error": str(e)}

# ---- approvals packages this week ----
try:
    ap = json.load(open(os.path.join(REG, "approvals_pending.json"))).get("items", [])
    wk = [p for p in ap if (p.get("stamp") or p.get("at") or "")[:10] >= D7]
    st = collections.Counter(p.get("status") for p in wk)
    def dol(p):
        try: return float(str(p.get("dollars") or "0").replace("$", "").replace(",", "").split()[0])
        except Exception: return 0.0
    out["approvals_7d"] = {"packages": len(wk), "by_status": dict(st), "dollars_as_written": round(sum(dol(p) for p in wk), 2),
                           "ids": [p.get("id") for p in wk]}
except Exception as e:
    out["approvals_7d"] = {"error": str(e)}

json.dump(out, open("metrics_verify_%s.json" % STAMP, "w"), indent=1)
v = out["verification"]
print("VERIFY massrebillsearch $%.2f vs tx-history open insurance balances on the same %d patients $%.2f (%+.1f%%; %d patients missing in scan)" % (
    v["massrebillsearch_total"], v["unpaid_patients"], v["txh_open_ins_balance_same_patients"], v["gap_pct"] or 0, v["patients_missing_in_scan"]))
for c, d in v["by_carrier"].items(): print("   %-6s unpaid-list %12.2f  txh-open %12.2f" % (c, d["unpaid_list"], d["txh_open"]))
print("REBILLS 7d:", out["rebills_7d"]); print("TF WATCH:", out["tf_writeoff_watch"]); print("APPROVALS 7d:", {k: v for k, v in out["approvals_7d"].items() if k != "ids"})
