#!/usr/bin/env python3
# PLAIN ENGLISH (5 PM ET 10/21/2026 run 2026-10-21T2110Z): the one money line of Sunshine check 0917962882 (ERA 1053247) that GitHub slot
#   #130 Post-buttoned at 21:27Z - chart 20729 visit 19456669 (99305 + 99497, 9/28/2026; Medicare primary, Sunshine Medicaid-MMA secondary) -
#   left the visit the way the Post button leaves dual crossovers (the 9/25 / 10/18 lesson): on the 99305 (charge 23368375) Sunshine's
#   14.29 posted WITHOUT its CO-45 / OA-23 reasons and 10.03 landed on the PATIENT balance; on the 99497 (charge 23368376) Sunshine's $0
#   CO-96/N448 answer posted and 13.35 Medicare coinsurance stays open on insurance. A dual's cost-share is never the patient's and a
#   Medicaid-family plan has answered it short of the PR total -> move the 10.03 back to insurance (move_to_ins, no rebill) and write both
#   residuals off WOCAID2ND, ERA-LINKED to this check (payreasons.post_line, pay 0.00 + the write-off, the remit's reasonlist) - the
#   10/14 rule, 10/4 / 10/6 / 10/11 / 10/18 precedents.
# Guards: live read first; each charge must carry Medicare's payment; the write-off never exceeds the live open balance; nothing else on
#   the chart is touched. --dry (default) prints the plan; --live writes. Register registers/era_fix_20729_2026-10-21T2110Z[_dry].json
#   + registers/era_manual_register.json (live). Never touches: plans, order, claims, rebills, other visits.
import amd, payreasons, move_to_ins, txh, json, sys, time, os
DRY = "--live" not in sys.argv; S = "2026-10-21T2110Z"; CID = "1053247"; PID = "20729"; VID = "19456669"
def L(m): print(m, flush=True)
amd.login_cached()
det = json.load(open("era_details/%s.json" % CID))["eracheckdetails"]
v = next(x for x in det if str(x["visitid"]) == VID); chk = payreasons.check_meta(CID, v)
L("check meta: paymentnumber %s depositdate %s" % (chk.get("paymentnumber"), chk.get("depositdate")))
if not str(chk.get("paymentnumber") or ""): L("HOLD - no check metadata"); sys.exit(2)
def live():
    root = txh.fetch_visit(PID, VID); res = {}
    for c in root.iter("charge"):
        if c.get("void") == "1" or c.get("visit") != VID: continue
        pays = [((p.get("checknumber") or "").strip(), p.get("void"), abs(float(p.get("amount") or 0)), p.get("carrier")) for p in c.iter("payment")]
        res[c.get("id").replace("charge", "")] = {"insbal": float(c.get("insbal") or 0), "patbal": float(c.get("patbal") or 0), "cpt": c.get("proccode"), "pays": pays,
                                                  "medicare_paid": sum(p[2] for p in pays if p[1] != "1" and p[2] > 0 and p[3] == "FLO02")}
    return res
st = live(); out = {"stamp": S, "dry": DRY, "checkid": CID, "visit": VID, "lines": []}
REGF = "registers/era_manual_register.json"; reg = json.load(open(REGF)) if os.path.exists(REGF) else []
for ch in v["charges"]:
    cid = str(ch["chargedetailid"]); s = st.get(cid); r = {"chargedetailid": cid, "cpt": ch.get("chargecode"), "before": s}
    if not s: r["outcome"] = "HOLD - no live charge"; out["lines"].append(r); L("c%s no live charge" % cid); continue
    if s["medicare_paid"] <= 0: r["outcome"] = "HOLD - Medicare never paid"; out["lines"].append(r); L("c%s Medicare never paid" % cid); continue
    if any(w for w in []): pass
    if s["patbal"] > 0.005:
        if DRY: r["move"] = "DRY would move %.2f back to insurance (no rebill)" % s["patbal"]
        else:
            mv = move_to_ins.move(cid, rebill=False); r["move"] = str(mv); L("c%s move back: %s" % (cid, mv))
            if not str(mv).startswith("moved"): r["outcome"] = "HOLD - move back failed"; out["lines"].append(r); continue
            time.sleep(0.6); st = live(); s = st.get(cid); r["after_move"] = {"insbal": s["insbal"], "patbal": s["patbal"]}
    wo = round(s["insbal"] + (s["patbal"] if DRY else 0), 2)
    if wo <= 0.005: r["outcome"] = "nothing open"; out["lines"].append(r); L("c%s nothing open" % cid); continue
    if DRY: r["outcome"] = "DRY would post pay 0.00 + WOCAID2ND %.2f ERA-linked" % wo; out["lines"].append(r); L("c%s %s %s (ins %.2f pat %.2f)" % (cid, s["cpt"], r["outcome"], s["insbal"], s["patbal"])); continue
    ok, payid, resp = payreasons.post_line(PID, VID, chk, v, cid, ch, pay=0.0, wo=wo, wocode="WOCAID2ND")
    time.sleep(0.7); s2 = live().get(cid) or {}
    r.update(outcome="posted" if ok else "FAULT", wo=wo, paymentid=payid, resp=resp[:160], after={"insbal": s2.get("insbal"), "patbal": s2.get("patbal")})
    L("c%s WOCAID2ND %.2f ok=%s after ins %s pat %s" % (cid, wo, ok, s2.get("insbal"), s2.get("patbal")))
    if ok: reg.append({"checkid": CID, "checkclaimid": v["checkclaimid"], "visitid": VID, "chargedetailid": cid, "outcome": "posted", "pay": 0.0, "wo": wo, "wocode": "WOCAID2ND", "when": S})
    out["lines"].append(r)
json.dump(out, open("registers/era_fix_20729_%s%s.json" % (S, "_dry" if DRY else ""), "w"), indent=1)
if not DRY: json.dump(reg, open(REGF, "w"), indent=1)
L("SUMMARY " + json.dumps([(x["chargedetailid"], x["outcome"]) for x in out["lines"]]))
