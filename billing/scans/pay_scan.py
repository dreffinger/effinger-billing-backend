# PLAIN ENGLISH (Posted-payment scan for the Money Ledger)
# Decides: Nothing. Reads every known patient's transaction history and totals what each carrier has actually PAID (posted payments, by month) and what was written off, so the ledger can show "paid last 12 months / paid all time" per payer next to the outstanding number (William 9/7: "CHP pays a lot - add a column that says how much they paid and posted").
# Rules it uses: txh.fetch per patient (payments carry carrier, date, amount, check number); voided transactions ignored; amounts are stored as credits (negative) - reported as positive. Patient universe = every patient seen on an unpaid list, claim-status sweep or ERA detail (patient_universe_0907.json, 1,103 patients); resumable/cached in pay_scan_cache.json.
# Never touches: AMD writes.
# ---
"""Usage: python3 pay_scan.py [--max N]   -> payments_by_carrier.json"""
import amd, txh, json, sys, os, time, collections, datetime
amd.login_cached(); mx = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 10**9
pids = json.load(open("patient_universe_0907.json")); CF = "pay_scan_cache.json"
cache = json.load(open(CF)) if os.path.exists(CF) else {}
n = 0
for pid in pids:
    if pid in cache or n >= mx: continue
    try: root = txh.fetch(pid)
    except Exception as e: print("ERR", pid, str(e)[:60]); continue
    rec = {"pays": [], "wos": [], "charges": 0, "fees": 0.0}
    for c in root.iter("charge"):
        if c.get("void") == "1": continue
        rec["charges"] += 1; rec["fees"] += float(c.get("fee") or 0)
        for p in c.iter("payment"):
            if p.get("void") != "1": rec["pays"].append([p.get("date"), p.get("carrier") or "PAT", abs(float(p.get("amount") or 0)), (p.get("checknumber") or "")[:20], c.get("dos")])
        for w in c.iter("writeoff"):
            if w.get("void") != "1": rec["wos"].append([w.get("date"), w.get("wocode"), abs(float(w.get("amount") or 0)), c.get("carrier") or "", c.get("dos")])
    cache[pid] = rec; n += 1
    if n % 25 == 0: json.dump(cache, open(CF, "w")); print(n, "patients scanned", flush=True)
    time.sleep(0.15)
json.dump(cache, open(CF, "w"))
# aggregate
today = datetime.date(2026, 9, 7); d12 = today - datetime.timedelta(days=365); d24 = today - datetime.timedelta(days=730)
def pd(s):
    try: return datetime.datetime.strptime(s, "%m/%d/%Y").date()
    except Exception: return None
agg = collections.defaultdict(lambda: {"paid_12": 0.0, "paid_24": 0.0, "paid_all": 0.0, "n_12": 0, "last_paid": "", "wo_12": 0.0, "months": collections.defaultdict(float)})
for pid, rec in cache.items():
    for dt, car, amt, chk, dos in rec["pays"]:
        d = pd(dt); a = agg[car]; a["paid_all"] += amt
        if d:
            if d >= d12: a["paid_12"] += amt; a["n_12"] += 1
            if d >= d24: a["paid_24"] += amt
            a["months"][d.strftime("%Y-%m")] += amt
            if d.isoformat() > a["last_paid"]: a["last_paid"] = d.isoformat()
    for dt, code, amt, car, dos in rec["wos"]:
        d = pd(dt)
        if d and d >= d12: agg[car or "OTHER"]["wo_12"] += amt
out = {k: dict(v, months=dict(sorted(v["months"].items()))) for k, v in agg.items()}
json.dump({"asof": today.isoformat(), "patients": len(cache), "carriers": out}, open("payments_by_carrier.json", "w"), indent=1)
for k, v in sorted(out.items(), key=lambda kv: -kv[1]["paid_12"])[:25]: print("%-8s paid 12mo $%9.0f  24mo $%9.0f  all $%9.0f  last %s" % (k, v["paid_12"], v["paid_24"], v["paid_all"], v["last_paid"]))
