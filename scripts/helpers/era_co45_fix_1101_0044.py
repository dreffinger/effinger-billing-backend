# PLAIN ENGLISH (9pm ET 10/31/2026 run 2026-11-01T0044Z): the ERA Center Post button posted Humana check 204982853261031 (ERA 1053359,
#   $70.46 on v19457780 99232 10/13/2026, chart 17478061) with CO-45 39.10 + CO-253 1.44 as reasons but payreasonwoamount 0, so the
#   contractual ($40.54) lands on the PATIENT balance (the 9/23 CO-45 defect). PR on the line is 0, so the whole remainder is contractual:
#   move_to_ins.move(cid) then manual_post pay 0 + WOINS 40.54 with the trace number and the check date. --dry = read only.
import amd, txh, move_to_ins, manual_post, json, sys, time
DRY = "--dry" in sys.argv; S = "2026-11-01T0044Z"
amd.login_cached()
CHK = {str(c["id"]): c for c in json.load(open("registers/era_checks_before_%s.json" % S))["checks"]}
def dd(cid): y, m, d = CHK[cid]["depositdate"][:10].split("-"); return "%s/%s/%s" % (m, d, y)
def live(pid, vid):
    root = txh.fetch_visit(pid, vid); res = {}
    for c in root.iter("charge"):
        if c.get("void") == "1": continue
        res[c.get("id").replace("charge","")] = {"fee": float(c.get("fee") or 0), "paid": float(c.get("paid") or 0), "patbal": float(c.get("patbal") or 0), "insbal": float(c.get("insbal") or 0), "carrier": c.get("carrier"), "cpt": c.get("proccode"),
                            "pays": [(p.get("amount"), p.get("checknumber") or p.get("checknum"), p.get("void")) for p in c.iter("payment")],
                            "wos": [(w.get("amount"), w.get("wocode"), w.get("void"), w.get("date")) for w in c.iter("writeoff")]}
    return res
A = [("17478061", "19457780", "23369824", "HUM01", "1053359", 0.0, 40.54)]
out = {"stamp": S, "dry": DRY, "A": []}
def L(m): print(m, flush=True)
for pid, vid, cid, car, ck, pr, co in A:
    st = live(pid, vid).get(cid)
    if not st: L("pat%s v%s c%s: not live" % (pid, vid, cid)); continue
    chkno = CHK[ck]["paymentnumber"]
    rec = {"pid": pid, "vid": vid, "cid": cid, "cpt": st["cpt"], "check": chkno, "before": {k: st[k] for k in ("fee", "paid", "patbal", "insbal")}, "pays": st["pays"], "wos": st["wos"]}
    L("pat%s v%s c%s %s live: %s" % (pid, vid, cid, st["cpt"], json.dumps(rec["before"])) + " pays=%s wos=%s" % (st["pays"], st["wos"]))
    if any(w[1] and w[1].strip() == "WOINS" and w[2] != "1" for w in st["wos"]) or (st["patbal"] <= pr + 0.005 and st["insbal"] <= 0.005):
        rec["result"] = "already corrected / settled (patbal %.2f insbal %.2f)" % (st["patbal"], st["insbal"]); L("   " + rec["result"]); out["A"].append(rec); continue
    wo = round(st["patbal"] + st["insbal"] - pr, 2)
    if abs(wo - co) > 0.01: rec["result"] = "open %.2f != remit contractual %.2f - left for review" % (wo, co); L("   " + rec["result"]); out["A"].append(rec); continue
    L("   -> move back + WOINS %.2f (check %s %s)" % (wo, chkno, dd(ck))); rec["wo"] = wo
    if DRY: rec["result"] = "DRY"; out["A"].append(rec); continue
    if st["patbal"] > 0.005:
        m = move_to_ins.move(cid); rec["move"] = str(m)[:160]; L("   move_to_ins -> %s" % str(m)[:160]); time.sleep(0.8)
    ok, msg = manual_post.post(cid, car, 0.0, wo, "WOINS", checknumber=chkno, depositdate=dd(ck), note="ERA %s contractual correction run %s" % (ck, S)); rec["post"] = (ok, str(msg)[:200]); L("   manual_post WOINS %.2f -> %s %s" % (wo, ok, str(msg)[:160]))
    time.sleep(0.8); after = live(pid, vid).get(cid) or {}; rec["after"] = {k: after.get(k) for k in ("patbal", "insbal", "paid")}; L("   after %s" % rec["after"])
    rec["result"] = "posted" if ok else "FAULT"; out["A"].append(rec)
json.dump(out, open("registers/era_co45_fix_%s%s.json" % (S, "_dry" if DRY else ""), "w"), indent=1)
