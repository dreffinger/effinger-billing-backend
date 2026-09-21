# PLAIN ENGLISH (5pm ET 9/21/2026 run 2026-09-21T2110Z, RECOVERY): this run's attempt to move seven SLMB-only coinsurance lines on
#   pat17477184 to the patient balance (full-visit echo with insportion=0) made AMD UNAPPLY the seven 9/17 hand-posted Medicare payments
#   (check 819803392 = ERA check 1051693) and void their WOINS. Repair per the v8 reason-code rule: void the seven unapplied credits
#   (voidpayment on the actvpaymentid), move each charge's balance back to insurance (move_to_ins), restore check 1051693 from the
#   dismissed list, re-post each visit's Medicare line through the ERA-linked shape (payreasons.repost_visit - keeps CO45/PR2),
#   then dismiss the check again. Also moves the coinsurance that AMD auto-transferred to the patient on three contractual write-offs
#   (Sunshine / United American secondaries in play) back to insurance. Never touches: other charts, other checks.
import amd, void_tx, move_to_ins, payreasons, json, time
amd.login_cached(); S = "2026-09-21T2110Z"; PID = "17477184"; CK = "1051693"
CREDITS = ["10158263", "10158355", "10158356", "10158357", "10158358", "10158359", "10158360"]
VIS = [("19451189", "23361189"), ("19453359", "23363903"), ("19452834", "23363209"), ("19452073", "23362189"), ("19451568", "23361620"), ("19451541", "23361590"), ("19452413", "23362661")]
OTHER = [("17473346", "19453034", "23363449"), ("17477607", "19453346", "23363891"), ("17477023", "19452626", "23362974")]
rec = {"stamp": S, "voids": [], "moves": [], "reposts": [], "other_moves": []}
print("== 1. void the 7 unapplied Medicare credits")
for a in CREDITS:
    ok, msg = void_tx.void_unapplied(a); print("  voidpayment %s -> %s %s" % (a, ok, msg[:100])); rec["voids"].append((a, ok, msg[:120])); time.sleep(0.5)
print("== 2. move balances back to insurance")
for vid, cid in VIS:
    r = move_to_ins.move(cid); print("  move c%s: %s" % (cid, str(r)[:120])); rec["moves"].append((cid, str(r)[:120])); time.sleep(0.5)
for pid, vid, cid in OTHER:
    r = move_to_ins.move(cid); print("  move c%s (pat%s): %s" % (cid, pid, str(r)[:120])); rec["other_moves"].append((pid, cid, str(r)[:120])); time.sleep(0.5)
print("== 3. restore check %s and re-post the 7 Medicare lines (ERA-linked, with reasons)" % CK)
ok, msg = payreasons.restore(CK); print("  restore -> %s %s" % (ok, msg[:100]))
d = payreasons.details(CK, fresh=True); print("  details: %d claims" % len(d.get("eracheckdetails", [])))
for vid, cid in VIS:
    try:
        r = payreasons.repost_visit(PID, vid, CK, release=False); print("  repost v%s -> %s" % (vid, r.get("outcome")))
        rec["reposts"].append({k: r.get(k) for k in ("visitid", "outcome", "steps", "after")})
    except Exception as e:
        print("  repost v%s EXC %s" % (vid, str(e)[:200])); rec["reposts"].append({"visitid": vid, "outcome": "exception", "err": str(e)[:200]})
    time.sleep(0.8)
ok2, msg2 = payreasons.redismiss(CK); print("  redismiss -> %s %s" % (ok2, msg2[:100])); rec["redismiss"] = (ok2, msg2[:120])
print("== 4. verify")
st = payreasons.visit_state(PID, None) if False else None
for vid, cid in VIS:
    s = payreasons.visit_state(PID, vid); print("  v%s" % vid, [(c["cid"], c["fee"], "ins", c["insbalance"], "pat", c["patbalance"], [(p["id"], p["amount"], p["reasons"]) for p in c["pays"] if p["void"] != "1"], [(w["code"], w["amount"]) for w in c["wos"] if w["void"] != "1"]) for c in s], "balanced", payreasons.balanced(s))
json.dump(rec, open("registers/era_recover_17477184_%s.json" % S, "w"), indent=1, default=str)
