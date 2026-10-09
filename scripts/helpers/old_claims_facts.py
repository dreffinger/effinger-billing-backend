# PLAIN ENGLISH (Old-claims facts pull - READ ONLY)
# Decides: nothing. For every visit on the unpaid list with a date of service over 90 days old, reads the live chart facts a
#   disposition needs: every charge with its payments (reason codes included), write-offs, last-billed carrier and bill date;
#   the visit's insurance order and claim-send history (getchargedetail); the chart's plan list (sequence, begin/end) and the
#   AMD 'deceased' flag. Writes old_claims_facts_<stamp>.json (resumable - a rerun skips visits already pulled).
# Rules it uses: read-only calls only (gettxhistory visitid=, getchargedetaildataicd10, getdemographic). The claim detail is read
#   only for visits that could still be acted on (no non-void payment yet, or a Stedi-mapped carrier); adjudicated Medicare
#   residuals only need the history. 4 worker threads, one cached token, retry with backoff on a transport error.
# Never touches: AMD writes, balances, claims. Chart names stay in the workspace copy only.
"""Usage: python3 old_claims_facts.py [--stamp 1009] [--threads 4] [--max N] [--only-carriers A,B] [--min-age 90]"""
import amd, txh, resave, precheck, json, sys, datetime, time, os, re, threading, queue, collections
import xml.etree.ElementTree as ET

a = sys.argv[1:]
def opt(n, d=None): return a[a.index(n) + 1] if n in a else d
STAMP = opt("--stamp", datetime.date.today().strftime("%m%d")); NT = int(opt("--threads", 4)); MX = int(opt("--max", 10**9)); MINAGE = int(opt("--min-age", 90))
ONLY = set(opt("--only-carriers", "").split(",")) - {""}
OUT = "old_claims_facts_%s.json" % STAMP; LOGF = "old_claims_facts_%s.log" % STAMP
TODAY = datetime.date(2026, 10, 9)
MAPPED = {k for k, v in precheck.CAR2STEDI.items() if v and k not in ("FLO02", "RET01")}
CODE_OF = {v: k for k, v in precheck.CARRIERS.items()}          # carNNNN -> code
amd.login_cached()
lock = threading.Lock(); LOG = open(LOGF, "a")
def L(m):
    with lock: print(m, flush=True); LOG.write(m + "\n"); LOG.flush()
def f(x):
    try: return float(x or 0)
    except Exception: return 0.0
def retry(fn, *args, tries=4):
    for i in range(tries):
        try: return fn(*args)
        except Exception as e:
            if i == tries - 1: raise
            time.sleep(1.5 * (i + 1))

unp = json.load(open("unpaid_%s.json" % TODAY.strftime("%Y%m%d")))
sel = []
for v in unp:
    car = (v.get("carriercode") or "").strip(); d = datetime.datetime.fromisoformat(v["dateofservice"]).date(); age = (TODAY - d).days
    if f(v.get("insbalance")) <= 0 or age <= MINAGE: continue
    if ONLY and car not in ONLY: continue
    v["_age"] = age; v["_car"] = car or "OTHER"; sel.append(v)
sel.sort(key=lambda v: (v["_car"], v["dateofservice"]))
done = {}
if os.path.exists(OUT):
    try: done = {r["vid"]: r for r in json.load(open(OUT))["visits"]}
    except Exception: done = {}
todo = [v for v in sel if str(v["visitid"]) not in done][:MX]
L("=== facts pull %s: %d visits over %d days on the unpaid list, %d already pulled, %d to do, %d threads ===" % (STAMP, len(sel), MINAGE, len(done), len(todo), NT))

plans_cache = {}; plans_lock = threading.Lock()
def chart(pid):
    pid = str(pid)
    with plans_lock:
        if pid in plans_cache: return plans_cache[pid]
    pa, pl = retry(precheck.plans, pid)
    rec = {"deceased": pa.get("deceased", ""), "inactive": pa.get("inactive", ""), "name": pa.get("name", ""), "dob": pa.get("dob", ""),
           "plans": [{"ins": p[0], "car": p[1], "code": CODE_OF.get(p[1], p[1]), "begin": p[2], "end": p[3], "seq": p[5]} for p in pl]}
    with plans_lock: plans_cache[pid] = rec
    return rec

def pull(v):
    pid = str(v["patientid"]); vid = str(v["visitid"])
    root = retry(txh.fetch_visit, pid, vid)
    charges = []
    for c in root.iter("charge"):
        if str(c.get("visit")) != vid: continue
        pays = [{"id": p.get("id"), "amount": abs(f(p.get("amount"))), "carrier": p.get("carrier", ""), "date": p.get("date", ""), "checkno": p.get("checknumber", ""),
                 "paycode": p.get("paycode", ""), "void": p.get("void", ""), "reasons": [[r.get("code", ""), f(r.get("amount"))] for r in p.iter("payreason")]} for p in c.iter("payment")]
        wos = [{"id": w.get("id"), "amount": abs(f(w.get("amount"))), "code": w.get("wocode", ""), "date": w.get("date", ""), "void": w.get("void", "")} for w in c.iter("writeoff")]
        charges.append({"cid": c.get("id"), "cpt": c.get("proccode", ""), "mods": c.get("modifiers", ""), "dos": c.get("dos", ""), "fee": f(c.get("fee")), "paid": abs(f(c.get("paid"))),
                        "insbal": f(c.get("insbal")), "patbal": f(c.get("patbal")), "carrier": c.get("carrier", ""), "billdate": c.get("billdate", ""), "void": c.get("void", ""),
                        "prov": c.get("provcode", ""), "fac": c.get("faccode", ""), "payerinfo": c.get("payerinfo", ""), "pays": pays, "wos": wos})
    live = [c for c in charges if c["void"] != "1"]
    livepays = [p for c in live for p in c["pays"] if p["void"] != "1"]
    rec = {"vid": vid, "pid": pid, "patient": v.get("patientname", ""), "carrier": v["_car"], "carriername": v.get("carriername", ""), "dos": v["dateofservice"][:10], "age": v["_age"],
           "insbalance": f(v.get("insbalance")), "visitamount": f(v.get("totalvisitamount")), "icn": v.get("icn"), "provider": v.get("providerprofilecode", "").strip(),
           "charges": charges, "live_charges": len(live), "live_insbal": round(sum(c["insbal"] for c in live), 2), "live_patbal": round(sum(c["patbal"] for c in live), 2),
           "adjudicated": bool(livepays), "paid_total": round(sum(p["amount"] for p in livepays), 2),
           "pay_carriers": sorted({p["carrier"] for p in livepays}), "last_pay_date": max([p["date"] for p in livepays] or [""]),
           "pay_reasons": sorted({r[0] for p in livepays for r in p["reasons"]}), "wo_codes": sorted({w["code"] for c in live for w in c["wos"] if w["void"] != "1"})}
    if live and (not livepays or v["_car"] in MAPPED):
        try:
            rt = ET.fromstring(retry(resave.detail, re.sub(r"\D", "", live[0]["cid"]))); vis = rt.find(".//visit")
            rec["insorder"] = vis.get("insorder", "") if vis is not None else ""
            rec["insbills"] = [{"carriername": b.get("carriername", ""), "billeddate": b.get("billeddate", ""), "claimid": b.get("claimid", ""), "paperedi": b.get("paperedi", ""), "claimrun": b.get("claimrun", "")} for b in rt.iter("insbill")]
        except Exception as e: rec["detail_error"] = str(e)[:120]
    ch = chart(pid); rec["chart"] = {"deceased": ch["deceased"], "inactive": ch["inactive"], "plans": ch["plans"]}
    return rec

q = queue.Queue(); [q.put(v) for v in todo]
results = dict(done); n = [0]; errs = [0]
def worker():
    while True:
        try: v = q.get_nowait()
        except queue.Empty: return
        try:
            r = pull(v)
            with lock: results[r["vid"]] = r; n[0] += 1
        except Exception as e:
            with lock: errs[0] += 1
            L("ERR v%s pat%s %s" % (v["visitid"], v["patientid"], str(e)[:120]))
        if n[0] % 100 == 0 and n[0]:
            with lock:
                json.dump({"stamp": STAMP, "about": "live chart facts for the over-%d-day unpaid book (read-only pull)" % MINAGE, "visits": list(results.values())}, open(OUT, "w"))
            L("  ... %d pulled, %d errors, %d left" % (n[0], errs[0], q.qsize()))
        time.sleep(0.15)
ts = [threading.Thread(target=worker, daemon=True) for _ in range(NT)]; [t.start() for t in ts]; [t.join() for t in ts]
json.dump({"stamp": STAMP, "about": "live chart facts for the over-%d-day unpaid book (read-only pull)" % MINAGE, "visits": list(results.values())}, open(OUT, "w"))
by = collections.Counter(r["carrier"] for r in results.values())
L("=== done: %d visits in %s (%d new, %d errors); by carrier %s ===" % (len(results), OUT, n[0], errs[0], dict(by.most_common())))
