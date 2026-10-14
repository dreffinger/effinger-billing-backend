# PLAIN ENGLISH (1 PM ET 10/14/2026 run 2026-10-14T1710Z): the ERA Center Post button (pressed by the Billing Button engine between this
#   run's dry and live ERA passes) posted the five Florida Blue checks 1053163-1053167. On most lines it also wrote off the CO-45 contractual,
#   but on two paid lines it did not (the 9/23 Florida Blue defect) and on two $0 wrong-payer / COB answers it moved the whole charge to the
#   PATIENT balance. The audit register registers/era_audit_2026-10-14T1710Z.json is the evidence.
#   A (CO-45 landed on the patient): move_to_ins.move(cid) (balance back to insurance, no rebill) then manual_post pay 0 + WOINS = the open
#     balance, with the Florida Blue trace number and the check date - the era_co45_fix pattern of 9/23 - 9/25.
#       pat25994 v19455138 c23366298 99306 9/18/2026: paid 33.10 posted, remit CO-45 93.16 -> patient 93.16 (check 1053164, trace 620268423)
#       pat17474446 v19455133 c23366273 99349 9/17/2026: paid 22.60 posted, remit CO-45 182.36 -> patient 188.79 (check 1053165, trace 423823547)
#   B (a $0 answer pushed the charge to the patient - 'wrong-payer denials never stay on the patient balance'): move_to_ins.move(cid) only.
#       pat17475362 v19440504 c23348193 99349 4/29/2026: Florida Blue PR-276 $0 (the old plan's answer; the live claim is at Medicare, sent 9/23)
#       pat17473245 v19451554 c23361603 99309 8/10/2026: Florida Blue PR-22 / MA04 $0 (other payer primary - the COB data problem; live claim at BCBS)
#   Never touches: lines already $0 both sides, PR amounts (22.92 / 33.75 / 80.67 / 206.00 stay for William's call), plans, other charts.
#   --dry = read only. Register registers/era_co45_fix_2026-10-14T1710Z[_dry].json.
import amd, txh, move_to_ins, manual_post, json, sys, time, datetime
DRY = "--dry" in sys.argv; S = "2026-10-14T1710Z"
# --only A,B,C,D (10/14 1710Z: the live run was refused by the permission classifier and went to the Mandatory Approvals page as four cards,
#   one per chart - A = chart 25994, B = chart 17474446 (CO-45 corrections), C = chart 17475362, D = chart 17473245 (move-backs)); no --only = all four
ONLY = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else {"A", "B", "C", "D"}
amd.login_cached()
_c = json.load(open("registers/era_checks_before_%s.json" % S)); _c = _c.get("checks") if isinstance(_c, dict) else _c
CHK = {str(c["id"]): c for c in _c}
def dd(ck):
    c = CHK[str(ck)]
    for k in ("depositdate", "paymentdate", "checkdate", "receiveddate", "createddate"):
        v = c.get(k)
        if v and str(v)[:4].isdigit():
            y, m, d = str(v)[:10].split("-"); return "%s/%s/%s" % (m, d, y)
    return datetime.date.today().strftime("%m/%d/%Y")
def live(pid, vid):
    root = txh.fetch_visit(pid, vid); res = {}
    for c in root.iter("charge"):
        if c.get("void") == "1" or c.get("visit") != str(vid): continue
        res[c.get("id").replace("charge", "")] = {"fee": float(c.get("fee") or 0), "paid": float(c.get("paid") or 0), "patbal": float(c.get("patbal") or 0), "insbal": float(c.get("insbal") or 0), "carrier": c.get("carrier"), "cpt": c.get("proccode")}
    return res
A = [x for L_, x in (("A", ("25994", "19455138", "23366298", "BCBS", "1053164", 93.16)), ("B", ("17474446", "19455133", "23366273", "BCBS", "1053165", 188.79))) if L_ in ONLY]
B = [x for L_, x in (("C", ("17475362", "19440504", "23348193")), ("D", ("17473245", "19451554", "23361603"))) if L_ in ONLY]
out = {"stamp": S, "dry": DRY, "A": [], "B": []}; faults = 0
def L(m): print(m, flush=True)
for pid, vid, cid, car, ck, expect in A:
    st = live(pid, vid).get(cid)
    if not st: L("A pat%s v%s c%s not live" % (pid, vid, cid)); continue
    rec = {"pid": pid, "vid": vid, "cid": cid, "cpt": st["cpt"], "before": dict(st), "check": CHK[ck]["paymentnumber"], "depositdate": dd(ck)}
    if st["patbal"] <= 0.005 and st["insbal"] <= 0.005: rec["result"] = "already $0"; out["A"].append(rec); L("A pat%s v%s c%s already $0" % (pid, vid, cid)); continue
    if abs(st["patbal"] - expect) > 0.011 and abs(st["insbal"] - expect) > 0.011:
        rec["result"] = "HOLD - balance %.2f/%.2f is not the expected contractual %.2f (someone else moved it)" % (st["patbal"], st["insbal"], expect); out["A"].append(rec); L("A pat%s v%s c%s %s" % (pid, vid, cid, rec["result"])); continue
    wo = round(st["patbal"] + st["insbal"], 2)
    L("A pat%s v%s c%s %s fee %.2f paid %.2f patbal %.2f insbal %.2f -> move back + WOINS %.2f (check %s %s)" % (pid, vid, cid, st["cpt"], st["fee"], st["paid"], st["patbal"], st["insbal"], wo, rec["check"], rec["depositdate"]))
    rec["wo"] = wo
    if DRY: rec["result"] = "DRY"; out["A"].append(rec); continue
    if st["patbal"] > 0.005:
        m = move_to_ins.move(cid); rec["move"] = str(m)[:120]; L("   move_to_ins -> %s" % str(m)[:120]); time.sleep(0.8)
        st2 = live(pid, vid).get(cid) or {}
        if st2.get("insbal", 0) < wo - 0.011: rec["result"] = "HOLD - after the move insbal %.2f < %.2f" % (st2.get("insbal", 0), wo); out["A"].append(rec); L("   %s" % rec["result"]); continue
    ok, msg = manual_post.post(cid, car, 0.0, wo, "WOINS", checknumber=rec["check"], depositdate=rec["depositdate"], note="ERA %s contractual correction run %s" % (ck, S))
    rec["post"] = (ok, str(msg)[:160]); L("   manual_post WOINS %.2f -> %s %s" % (wo, ok, str(msg)[:120]))
    faults = 0 if ok else faults + 1
    time.sleep(0.8); after = live(pid, vid).get(cid, {}); rec["after"] = {k: after.get(k) for k in ("patbal", "insbal", "paid")}; L("   after patbal %s insbal %s" % (after.get("patbal"), after.get("insbal")))
    rec["result"] = "posted" if ok else "FAULT"; out["A"].append(rec)
    if faults >= 3: L("3 consecutive addpayments faults - stopping"); break
for pid, vid, cid in B:
    st = live(pid, vid).get(cid)
    if not st: L("B pat%s v%s c%s not live" % (pid, vid, cid)); continue
    L("B pat%s v%s c%s %s carrier %s patbal %.2f insbal %.2f" % (pid, vid, cid, st["cpt"], st["carrier"], st["patbal"], st["insbal"]))
    rec = {"pid": pid, "vid": vid, "cid": cid, "cpt": st["cpt"], "before": dict(st)}
    if st["patbal"] <= 0.005: rec["result"] = "patbal 0 - nothing"; out["B"].append(rec); continue
    if DRY: rec["result"] = "DRY - would move %.2f back to insurance" % st["patbal"]; out["B"].append(rec); continue
    m = move_to_ins.move(cid); rec["move"] = str(m)[:120]; L("   move_to_ins -> %s" % str(m)[:120]); time.sleep(0.8)
    after = live(pid, vid).get(cid, {}); rec["after"] = {k: after.get(k) for k in ("patbal", "insbal", "carrier")}; rec["result"] = "moved" if str(m).startswith("moved") else "move answered %s" % str(m)[:60]; L("   after %s" % rec["after"]); out["B"].append(rec)
json.dump(out, open("registers/era_co45_fix_%s%s.json" % (S, "_dry" if DRY else ""), "w"), indent=1)
L("DONE A %d B %d faults %d" % (len(out["A"]), len(out["B"]), faults))
