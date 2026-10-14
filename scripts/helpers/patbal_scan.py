# PLAIN ENGLISH (Patient-balance review scan - READ ONLY; William 10/13/2026: "of all the money put on patient balance, categorize
#   it: can any be retrieved by sending it correctly to an insurance - if not it should all be written off")
# Decides: nothing. For every chart carrying a patient balance (masswriteoffsearch isinsbalance:false), reads the chart's plans
#   (getdemographic: carrier, begin/end, sequence, deceased flag) and the transaction history (gettxhistory: every charge's
#   payments with CARC reasons, write-offs, last-billed carrier and bill date). Writes patbal_scan_<stamp>.json (resumable).
# Never touches: AMD writes.
import amd, txh, precheck, json, sys, os, time, threading, queue, re, datetime
STAMP = "1013"; OUT = "patbal_scan_%s.json" % STAMP; NT = int(sys.argv[sys.argv.index("--threads") + 1]) if "--threads" in sys.argv else 3
CODE_OF = {v: k for k, v in precheck.CARRIERS.items()}
rows = json.load(open("mwo_pat_all_20261013.json"))
for x in json.load(open("[name]_[DOB].json"))["chargedetails"]:
    if not any(r["chargedetailid"] == x["chargedetailid"] for r in rows[:0]): pass
pids = sorted({str(r["patientid"]) for r in rows}, key=int)
done = {}
if os.path.exists(OUT):
    try: done = json.load(open(OUT))["charts"]
    except Exception: done = {}
todo = [p for p in pids if p not in done]
print("patient-balance charts: %d (%d already read, %d to do)" % (len(pids), len(done), len(todo)), flush=True)
amd.login_cached(); lock = threading.Lock(); n = [0]; errs = []
def f(x):
    try: return float(x or 0)
    except Exception: return 0.0
def retry(fn, *a):
    for i in range(3):
        try: return fn(*a)
        except Exception as e:
            if i == 2: raise
            time.sleep(1.5 * (i + 1))
def read(pid):
    pa, pl = retry(precheck.plans, pid)
    plans = [{"ins": p[0], "car": p[1], "code": CODE_OF.get(p[1], p[1]), "begin": p[2], "end": p[3], "seq": p[5]} for p in pl]
    root = retry(txh.fetch, pid)
    charges = []
    for c in root.iter("charge"):
        if c.get("void") == "1": continue
        pays = [{"amount": abs(f(p.get("amount"))), "carrier": p.get("carrier", ""), "date": p.get("date", ""), "check": p.get("checknumber", ""),
                 "reasons": [[r.get("code", ""), f(r.get("amount"))] for r in p.iter("payreason")]} for p in c.iter("payment") if p.get("void") != "1"]
        wos = [{"amount": abs(f(w.get("amount"))), "code": w.get("wocode", ""), "date": w.get("date", "")} for w in c.iter("writeoff") if w.get("void") != "1"]
        charges.append({"cid": c.get("id"), "visit": c.get("visit"), "cpt": (c.get("proccode") or "").strip(), "dos": c.get("dos", ""), "fee": f(c.get("fee")),
                        "insbal": f(c.get("insbal")), "patbal": f(c.get("patbal")), "carrier": c.get("carrier", ""), "billdate": c.get("billdate", ""),
                        "prov": c.get("provcode", ""), "pays": pays, "wos": wos})
    return {"deceased": pa.get("deceased", ""), "inactive": pa.get("inactive", ""), "dob": "", "plans": plans, "charges": charges}
q = queue.Queue(); [q.put(p) for p in todo]
def worker():
    while True:
        try: pid = q.get_nowait()
        except queue.Empty: return
        try:
            r = read(pid)
            with lock: done[pid] = r; n[0] += 1
        except Exception as e:
            with lock: errs.append("pat%s %s" % (pid, str(e)[:80]))
        if n[0] % 50 == 0:
            with lock:
                json.dump({"stamp": STAMP, "charts": done, "errors": errs}, open(OUT, "w")); print("  %d charts read, %d errors" % (n[0], len(errs)), flush=True)
        time.sleep(0.2)
ts = [threading.Thread(target=worker, daemon=True) for _ in range(NT)]; [t.start() for t in ts]; [t.join() for t in ts]
json.dump({"stamp": STAMP, "charts": done, "errors": errs}, open(OUT, "w"))
print("done: %d charts, %d errors -> %s" % (len(done), len(errs), OUT), flush=True)
