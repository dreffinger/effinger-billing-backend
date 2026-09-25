# PLAIN ENGLISH (11am ET 9/25/2026 run 2026-09-25T1510Z): the ERA Center Post button posted the CAP07 check 4123813 and the UHC check W0384723
#   with the CO-45 / CO-253 reason on each payment but payreasonwoamount 0, so every posted charge shows patient balance = fee - paid (the
#   9/23 Florida Blue / VA CCN / 9/25 WellCare defect). PR amounts on these lines are all 0, so the whole patient balance is contractual.
#   For each line: move_to_ins.move(cid) (balance back to insurance, no rebill) then manual_post pay 0 + WOINS = the open balance, with the
#   check number and deposit date. Also: the UHC PR-27 $0 lines era_clear zero-posted on pat17476042 (already re-routed to Medicare 9/23)
#   pushed the charges to the patient balance - move them back (move only; the claims are at Medicare, billed 9/23).
# Never touches: paid lines already at $0 both sides, plans, other charts. --dry = read only. Register registers/era_co45_fix_2026-09-25T1510Z.json
import amd, txh, move_to_ins, manual_post, json, sys, time
DRY = "--dry" in sys.argv; S = "2026-09-25T1510Z"
amd.login_cached()
CHK = {c["id"]: c for c in json.load(open("era_checks_before_%s.json" % S))}
def dd(cid): y, m, d = CHK[cid]["depositdate"][:10].split("-"); return "%s/%s/%s" % (m, d, y)
def live(pid, vid):
    root = txh.fetch_visit(pid, vid); res = {}
    for c in root.iter("charge"):
        if c.get("void") == "1": continue
        res[c.get("id")] = {"fee": float(c.get("fee") or 0), "paid": float(c.get("paid") or 0), "patbal": float(c.get("patbal") or 0), "insbal": float(c.get("insbal") or 0), "carrier": c.get("carrier"), "cpt": c.get("proccode"),
                            "wos": [(w.get("amount"), w.get("wocode"), w.get("void"), w.get("date")) for w in c.iter("writeoff")]}
    return res
# (pid, vid, cid, carrier, checkid)
A = [("17477776","19454904","23366055","CAP07",1052843),("17477776","19454910","23366062","CAP07",1052843),("17477776","19454936","23366087","CAP07",1052843),("17477776","19455052","23366204","CAP07",1052843),
     ("17477798","19455030","23366180","CAP07",1052843),("17477798","19455057","23366210","CAP07",1052843),("17477471","19451896","23361986","CAP07",1052843),
     ("17477349","19450732","23360691","UNI20",1052844),("17477349","19450768","23360728","UNI20",1052844),("17477349","19450839","23360841","UNI20",1052844),
     ("17477402","19451377","23361421","UNI20",1052844),("17477402","19451394","23361438","UNI20",1052844),("17477402","19451472","23361520","UNI20",1052844),
     ("17477203","19449614","23359383","UNI20",1052844),("17477203","19449615","23359384","UNI20",1052844),("17477203","19449625","23359400","UNI20",1052844),("17477203","19450072","23359935","UNI20",1052844),("17477203","19450073","23359936","UNI20",1052844),
     ("17473342","19453118","23363618","UNI20",1052844),("17473342","19453119","23363619","UNI20",1052844)]
B = [("17476042","19453092","23363592"),("17476042","19453101","23363601"),("17476042","19453127","23363629")]
out = {"stamp": S, "dry": DRY, "A": [], "B": []}; faults = 0
def L(m): print(m, flush=True)
for pid, vid, cid, car, ck in A:
    st = live(pid, vid).get(cid)
    if not st: L("A pat%s v%s c%s not live" % (pid, vid, cid)); continue
    if st["patbal"] <= 0.005 and st["insbal"] <= 0.005: out["A"].append({"pid": pid, "vid": vid, "cid": cid, "result": "already $0"}); L("A pat%s v%s c%s %s already $0" % (pid, vid, cid, st["cpt"])); continue
    wo = round(st["patbal"] + st["insbal"], 2); chkno = CHK[ck]["paymentnumber"]
    L("A pat%s v%s c%s %s fee %.2f paid %.2f patbal %.2f insbal %.2f -> move back + WOINS %.2f (check %s %s)" % (pid, vid, cid, st["cpt"], st["fee"], st["paid"], st["patbal"], st["insbal"], wo, chkno, dd(ck)))
    rec = {"pid": pid, "vid": vid, "cid": cid, "cpt": st["cpt"], "patbal_before": st["patbal"], "wo": wo, "check": chkno}
    if DRY: rec["result"] = "DRY"; out["A"].append(rec); continue
    if st["patbal"] > 0.005:
        m = move_to_ins.move(cid); rec["move"] = str(m)[:120]; L("   move_to_ins -> %s" % str(m)[:120]); time.sleep(0.6)
    ok, msg = manual_post.post(cid, car, 0.0, wo, "WOINS", checknumber=chkno, depositdate=dd(ck), note="ERA %s contractual correction run %s" % (ck, S)); rec["post"] = (ok, str(msg)[:160]); L("   manual_post WOINS %.2f -> %s %s" % (wo, ok, str(msg)[:120]))
    faults = 0 if ok else faults + 1
    time.sleep(0.8); after = live(pid, vid).get(cid, {}); rec["after"] = {k: after.get(k) for k in ("patbal", "insbal", "paid")}; L("   after patbal %.2f insbal %.2f" % (after.get("patbal", -1), after.get("insbal", -1)))
    out["A"].append(rec)
    if faults >= 3: L("3 consecutive addpayments faults - stopping"); break
for pid, vid, cid in B:
    st = live(pid, vid).get(cid)
    L("B pat%s v%s c%s %s carrier %s patbal %.2f insbal %.2f" % (pid, vid, cid, st["cpt"], st["carrier"], st["patbal"], st["insbal"]))
    rec = {"pid": pid, "vid": vid, "cid": cid, "patbal_before": st["patbal"]}
    if st["patbal"] <= 0.005: rec["result"] = "patbal 0 - nothing"; out["B"].append(rec); continue
    if DRY: rec["result"] = "DRY"; out["B"].append(rec); continue
    m = move_to_ins.move(cid); rec["move"] = str(m)[:120]; L("   move_to_ins -> %s" % str(m)[:120]); time.sleep(0.8)
    after = live(pid, vid).get(cid, {}); rec["after"] = {k: after.get(k) for k in ("patbal", "insbal", "carrier")}; L("   after %s" % rec["after"]); out["B"].append(rec)
json.dump(out, open("registers/era_co45_fix_%s%s.json" % (S, "_dry" if DRY else ""), "w"), indent=1)
L("DONE A %d B %d faults %d" % (len(out["A"]), len(out["B"]), faults))
