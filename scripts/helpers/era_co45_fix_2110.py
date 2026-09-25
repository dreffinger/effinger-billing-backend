# PLAIN ENGLISH (5pm ET 9/25/2026 run 2026-09-25T2110Z): the ERA Center Post button posted the Ambetter (AMB03) check 0934734717 (ERA 1052847)
#   with the CO-45 reason on each payment but payreasonwoamount 0, so both posted charges show patient balance = fee - paid (the 9/23 CO-45 defect).
#   The chart carries one plan (AMB03 seq 1), so the PR-2 coinsurance IS the patient's; only the CO-45 contractual is corrected:
#   move_to_ins.move(cid) (balance back to insurance, no rebill) then manual_post pay 0 + WOINS = patbal minus the line's PR-2, with the trace
#   number and the check date - AMD transfers the PR-2 remainder back to the patient on its own (captured 9/18 'Contractual correction').
# Never touches: the Sunshine lines (posted with WOMCAD, $0 both sides), plans, other charts. --dry = read only.
import amd, txh, move_to_ins, manual_post, json, sys, time
DRY = "--dry" in sys.argv; S = "2026-09-25T2110Z"
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
# (pid, vid, cid, carrier, checkid, PR amount on the line, expected CO-45)
A = [("17477799", "19455058", "23366211", "AMB03", 1052847, 79.85, 150.30), ("17477799", "19455032", "23366182", "AMB03", 1052847, 35.95, 39.10)]
out = {"stamp": S, "dry": DRY, "A": []}
def L(m): print(m, flush=True)
faults = 0
for pid, vid, cid, car, ck, pr, co45 in A:
    st = live(pid, vid).get("charge" + cid) or live(pid, vid).get(cid)
    if not st: L("pat%s v%s c%s: not live" % (pid, vid, cid)); continue
    chkno = CHK[ck]["paymentnumber"]
    rec = {"pid": pid, "vid": vid, "cid": cid, "cpt": st["cpt"], "check": chkno, "before": {k: st[k] for k in ("fee", "paid", "patbal", "insbal")}}
    if any(w[1] and w[1].strip() == "WOINS" and w[2] != "1" for w in st["wos"]) or st["patbal"] <= pr + 0.005:
        rec["result"] = "already corrected (patbal %.2f, PR %.2f)" % (st["patbal"], pr); L("pat%s v%s c%s %s" % (pid, vid, cid, rec["result"])); out["A"].append(rec); continue
    wo = round(st["patbal"] - pr, 2)
    if abs(wo - co45) > 0.01: rec["result"] = "patbal-PR %.2f != remit CO-45 %.2f - left for review" % (wo, co45); L("pat%s v%s c%s %s" % (pid, vid, cid, rec["result"])); out["A"].append(rec); continue
    L("pat%s v%s c%s %s fee %.2f paid %.2f patbal %.2f insbal %.2f PR %.2f -> move back + WOINS %.2f (check %s %s)" % (pid, vid, cid, st["cpt"], st["fee"], st["paid"], st["patbal"], st["insbal"], pr, wo, chkno, dd(ck)))
    rec["wo"] = wo
    if DRY: rec["result"] = "DRY"; out["A"].append(rec); continue
    m = move_to_ins.move(cid); rec["move"] = str(m)[:120]; L("   move_to_ins -> %s" % str(m)[:120]); time.sleep(0.8)
    ok, msg = manual_post.post(cid, car, 0.0, wo, "WOINS", checknumber=chkno, depositdate=dd(ck), note="ERA %s contractual correction run %s" % (ck, S)); rec["post"] = (ok, str(msg)[:160]); L("   manual_post WOINS %.2f -> %s %s" % (wo, ok, str(msg)[:120]))
    faults = 0 if ok else faults + 1
    time.sleep(0.8); after = live(pid, vid).get("charge" + cid) or live(pid, vid).get(cid) or {}; rec["after"] = {k: after.get(k) for k in ("patbal", "insbal", "paid")}; L("   after patbal %s insbal %s" % (after.get("patbal"), after.get("insbal")))
    rec["result"] = "posted" if ok else "FAULT"; out["A"].append(rec)
    if faults >= 3: L("3 consecutive addpayments faults - stopping"); break
json.dump(out, open("registers/era_co45_fix_%s%s.json" % (S, "_dry" if DRY else ""), "w"), indent=1)
