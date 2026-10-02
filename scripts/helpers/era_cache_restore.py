# PLAIN ENGLISH (cache the line detail of an ERA check that was posted + dismissed before its details were saved - 5 AM ET 10/2/2026 run 2026-10-02T0910Z)
# Decides: nothing new. era_clear.py's live pass posted a Medicare 835 that arrived mid-run (check 1052929, 40 visits, $3,826.73)
#   through the Post button and dismissed it before this run had cached GET /api/era/checkdetails for it; AMD answers an empty
#   claim list for a processed/dismissed check, and every later repair (payreasons.py re-posts, the 9/21 audit, the Unbilled
#   'Payment reason codes' rule) reads the remit lines from era_details/<checkid>.json. This helper applies the 9/19 recipe already
#   inside payreasons.py: reversedismiss (the check comes back to the unposted list) -> checkdetails (saved to the cache) ->
#   dismiss again. Then, read-only, it audits every remit line against the live chart: the payment carrying the check number must
#   equal the remit's paid amount and carry reason codes; it prints the mismatches. --dry (default) only says whether the check is
#   on the dismissed list and whether the cache already holds it; --live does the restore/cache/redismiss and the audit.
# Never touches: payments, write-offs, charges, any other check. Register: registers/era_cache_restore_<checkid>_<stamp>.json
import sys, os, json, time, datetime
import amd, payreasons, txh
a = sys.argv[1:]; LIVE = "--live" in a
cid = [x for x in a if x.isdigit()][0]
stamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H%MZ")
reg = {"stamp": stamp, "checkid": cid, "live": LIVE, "steps": [], "audit": []}
amd.login_cached()
fn = os.path.join(payreasons.CACHE, "%s.json" % cid)
have = os.path.exists(fn) and bool(json.load(open(fn)).get("eracheckdetails"))
dis = payreasons.dismissed_index().get(cid)
reg["steps"].append("cache %s; dismissed-list entry %s" % ("present" if have else "absent", "yes (%s)" % dis.get("dismissedat") if dis else "no"))
print(reg["steps"][-1])
d = None
if have:
    d = json.load(open(fn))
elif LIVE and dis:
    ok, t = payreasons.restore(cid); reg["steps"].append("reversedismiss -> %s %s" % (ok, t)); print(reg["steps"][-1])
    if ok:
        d = payreasons.details(cid, fresh=True)
        n = len(d.get("eracheckdetails") or [])
        reg["steps"].append("checkdetails -> %d claim lines %s" % (n, "cached" if n else "EMPTY (not cached)")); print(reg["steps"][-1])
        ok2, t2 = payreasons.redismiss(cid); reg["steps"].append("dismiss again -> %s %s" % (ok2, t2)); print(reg["steps"][-1])
        if not n: d = None
else:
    print("dry: would reversedismiss %s, cache its checkdetails, dismiss it again, then audit the posted lines" % cid)
if d:
    vs = d["eracheckdetails"]; chk = payreasons.check_meta(cid, vs[0] if vs else None) or {}
    paynum = next((x[8:] for x in a if x.startswith("--check=")), None) or str(chk.get("paymentnumber") or "")
    tot = 0.0; bad = 0
    for v in vs:
        pid, vid = str(v["patientid"]), str(v["visitid"])
        try: root = txh.fetch_visit(pid, vid)
        except Exception as e: reg["audit"].append({"pid": pid, "visit": vid, "verdict": "txh error %s" % str(e)[:120]}); bad += 1; continue
        live = {c.get("id"): c for c in root.iter("charge") if c.get("void") != "1"}
        for ch in v.get("charges") or []:
            paid = float(ch.get("paymentamount") or 0); cidc = str(ch.get("chargedetailid")); tot += paid
            cas = ch.get("carc") or []
            pr = sum(float(x["reasonamt"]) for x in cas if x["payreasongroup"] == "PR"); co = sum(float(x["reasonamt"]) for x in cas if x["payreasongroup"] == "CO")
            c = live.get(cidc)
            if c is None:
                reg["audit"].append({"pid": pid, "visit": vid, "cid": cidc, "paid": paid, "verdict": "charge not live"}); bad += 1; continue
            pays = [p for p in c.iter("payment") if p.get("void") != "1" and (paynum and str(p.get("checknumber") or "") == paynum)]
            amt = sum(abs(float(p.get("amount") or 0)) for p in pays)
            reasons = [(r.get("code"), r.get("amount")) for p in pays for r in p.iter("payreason")]
            rec = {"pid": pid, "visit": vid, "cid": cidc, "dos": (ch.get("dos") or "")[:10], "remit_paid": paid, "remit_co": co, "remit_pr": pr,
                   "posted": amt, "payments": len(pays), "reasons": reasons, "insbalance": c.get("insbalance"), "patbalance": c.get("patbalance")}
            if paid > 0 and not pays: rec["verdict"] = "NOT POSTED"
            elif abs(amt - paid) > 0.011: rec["verdict"] = "MISMATCH"
            elif paid > 0 and not reasons: rec["verdict"] = "no reason codes"
            else: rec["verdict"] = "ok"
            if rec["verdict"] != "ok": bad += 1
            reg["audit"].append(rec)
        time.sleep(0.2)
    from collections import Counter
    reg["summary"] = {"lines": len(reg["audit"]), "remit_paid_total": round(tot, 2), "verdicts": dict(Counter(x["verdict"] for x in reg["audit"]))}
    print("AUDIT", json.dumps(reg["summary"]))
    for x in reg["audit"]:
        if x["verdict"] != "ok": print("   ", json.dumps(x, default=str))
os.makedirs("registers", exist_ok=True)
json.dump(reg, open("registers/era_cache_restore_%s_%s%s.json" % (cid, stamp, "" if LIVE else "_dry"), "w"), indent=1, default=str)
print("register written")
