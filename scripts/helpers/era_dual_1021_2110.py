#!/usr/bin/env python3
# PLAIN ENGLISH (5 PM ET 10/21/2026 run 2026-10-21T2110Z - ehpa cloud copy; adapted from era_dual_1019_2110.py / era_dual_1018_1110.py)
# Sunshine State Health Plan check 0917962882 (ERA check 1053247, $14.29, 12 claims) arrived between this run's 21:21Z Center read and
#   GitHub slot #130 (21:25Z). The slot Post-buttoned its ONE money line (chart 20729 v19456669 99306: 14.29) and era_clear dismissed the
#   check; its 11 other claims are $0 answers on Medicare-paid charges (the Sunshine Medicaid-MMA secondary) and were cached by this run
#   (era_details/1053247.json) before the dismiss. The standing rules decide them, as on 10/18 (era_dual_1018_1110.py, lesson
#   2026-10-18T11:30Z) and 10/19:
#     CO96 + N448  (CCM 99487/99489 and ACP 99497 'not covered' by the Medicaid plan) -> WOCAID2ND: a Medicaid-family plan answered the
#                  Medicare cost-share short of the PR total (William 10/13-10/14; 10/4, 10/6, 10/11, 10/18 precedents).
#     CO16 + M56   (missing/invalid payer identifier) -> NO write-off here: recorded for the centene-m56 cluster row (10/16, 10/18 precedent).
#   Each write-off is ERA-LINKED to this check (payreasons.post_line = addpayments postingmethod=era with eraclaimid / erareportid and the
#   remit's reasonlist, pay 0.00 + the write-off; the check's metadata comes from the dismissed list through payreasons.check_meta),
#   never a bare manual_post (the 9/21 reason-code trap).
# Guards (per charge, read LIVE with gettxhistory first): the charge must carry a non-void PAYMENT from the primary (Medicare / the MA plan) -
#   a charge the primary never paid is HELD; the live open balance must not exceed the remit's stored insurancebalance by more than a cent
#   (something else happened - HOLD); a patient-side balance is moved back to insurance first (move_to_ins, no rebill); a charge already
#   carrying a non-void payment with this check number is 'already-posted'; a $0 charge is 'nothing open' (record only); the money line
#   the slot posted is skipped (the audit helper covers it).
# --dry (default) prints the plan; --live writes. Stops after 3 consecutive addpayments faults.
# Register: registers/era_dual_2026-10-21T2110Z[_dry].json + registers/era_manual_register.json (live).
# Never touches: plans, insurance order, claims, rebills, the Humana checks of this slot (1053248 / 1053249 / 1053250), any charge not on the remit.
import amd, payreasons, move_to_ins, txh, json, sys, time, os, collections
a = sys.argv; DRY = "--live" not in a; S = "2026-10-21T2110Z"; CID = "1053247"
ONLY = a[a.index("--only") + 1].split(",") if "--only" in a else None      # visit ids to limit a re-run to
def L(m): print(m, flush=True)
amd.login_cached()
det = json.load(open("era_details/%s.json" % CID))["eracheckdetails"]      # cached at 21:3xZ, before the dismiss
chk = payreasons.check_meta(CID, det[0])
L("check meta: id %s paymentnumber %s depositdate %s paymentcode %s carrier %s" % (chk.get("id"), chk.get("paymentnumber"), chk.get("depositdate"), chk.get("paymentcode"), chk.get("systemcarrierid") or det[0].get("carrierid")))
if not str(chk.get("paymentnumber") or ""): L("HOLD - no check metadata (not on the unposted or dismissed list) - nothing written"); sys.exit(2)

def rule(v):
    carcs = {x["reasoncode"] for x in v["carc"]}; rarcs = {x["remarkcode"] for x in v["rarc"]}
    if "CO96" in carcs and "N448" in rarcs: return "WOCAID2ND", "CO96/N448"
    if "CO16" in carcs and "M56" in rarcs: return None, "CO16/M56 - centene-m56 cluster, no write-off"
    return None, "+".join(sorted(carcs)) + "/" + "+".join(sorted(rarcs - {"#AM"}))

def live(pid, vid):
    root = txh.fetch_visit(pid, vid); res = {}
    for c in root.iter("charge"):
        if c.get("void") == "1" or c.get("visit") != str(vid): continue
        pays = [((p.get("checknumber") or "").strip(), p.get("void"), abs(float(p.get("amount") or 0)), p.get("carrier")) for p in c.iter("payment")]   # txh amounts are negative
        res[c.get("id").replace("charge", "")] = {"insbal": float(c.get("insbal") or 0), "patbal": float(c.get("patbal") or 0), "carrier": c.get("carrier"),
            "cpt": c.get("proccode"), "dos": c.get("dos"), "fee": c.get("fee"), "pays": pays,
            "primary_paid": sum(p[2] for p in pays if p[1] != "1" and p[2] > 0)}
    return res

out = {"stamp": S, "dry": DRY, "checkid": CID, "paymentnumber": chk.get("paymentnumber"), "lines": []}; faults = 0; seen = set()
REGF = "registers/era_manual_register.json"; reg = json.load(open(REGF)) if os.path.exists(REGF) else []
cache = {}
for v in det:
    pid, vid = str(v["patientid"]), str(v["visitid"])
    if ONLY and vid not in ONLY: continue
    if vid not in cache: cache[vid] = live(pid, vid); time.sleep(0.25)
    st = cache[vid]
    for ch in v["charges"]:
        cid = str(ch["chargedetailid"])
        key = (vid, cid)
        if key in seen: continue
        seen.add(key)
        # per-charge rule: the remit's CARC/RARC are repeated on the charge rows
        carcs = {x["reasoncode"] for x in (ch.get("carc") or v["carc"])}; rarcs = {x["remarkcode"] for x in (ch.get("rarc") or v["rarc"])}
        if "CO96" in carcs and "N448" in rarcs: wocode, why = "WOCAID2ND", "CO96/N448"
        elif "CO16" in carcs and "M56" in rarcs: wocode, why = None, "CO16/M56 - centene-m56 cluster, no write-off"
        else: wocode, why = None, "+".join(sorted(carcs)) + "/" + "+".join(sorted(rarcs - {"#AM"}))
        r = {"checkid": CID, "checkclaimid": v["checkclaimid"], "pid": pid, "visitid": vid, "chargedetailid": cid, "cpt": ch.get("chargecode"), "dos": str(v["dos"])[:10],
             "rule": why, "wocode": wocode, "remit_insbal": v["insurancebalance"], "remit_paid": float(ch.get("paymentamount") or 0)}
        s = st.get(cid)
        r["before"] = s and {k: s[k] for k in ("insbal", "patbal", "carrier", "cpt", "dos", "fee", "primary_paid")}
        if float(ch.get("paymentamount") or 0) > 0: r["outcome"] = "money line - Post-buttoned by slot #130 (audit helper covers it)"; out["lines"].append(r); L("v%s c%s %s" % (vid, cid, r["outcome"])); continue
        if not s: r["outcome"] = "HOLD - no live charge matches"; out["lines"].append(r); L("v%s %s %s: no live charge" % (vid, ch.get("chargecode"), why)); continue
        if not wocode: r["outcome"] = "recorded - " + why + " (ins %.2f pat %.2f)" % (s["insbal"], s["patbal"]); out["lines"].append(r); L("v%s c%s %s" % (vid, cid, r["outcome"])); continue
        if any(p[0] == str(chk.get("paymentnumber")) and p[1] != "1" for p in s["pays"]): r["outcome"] = "already-posted"; out["lines"].append(r); L("v%s c%s already posted" % (vid, cid)); continue
        if s["patbal"] <= 0.005 and s["insbal"] <= 0.005: r["outcome"] = "nothing open (already settled)"; out["lines"].append(r); L("v%s c%s nothing open" % (vid, cid)); continue
        if s["primary_paid"] <= 0: r["outcome"] = "HOLD - primary never paid this charge (ins %.2f pat %.2f)" % (s["insbal"], s["patbal"]); out["lines"].append(r); L("v%s c%s %s" % (vid, cid, r["outcome"])); continue
        if s["insbal"] + s["patbal"] > float(v["insurancebalance"] or 0) + 0.011 and float(v["insurancebalance"] or 0) > 0:
            r["outcome"] = "HOLD - live balance %.2f exceeds the remit's %.2f" % (s["insbal"] + s["patbal"], float(v["insurancebalance"])); out["lines"].append(r); L("v%s c%s %s" % (vid, cid, r["outcome"])); continue
        if s["patbal"] > 0:
            if DRY: r["move"] = "DRY would move %.2f patient balance back to insurance (no rebill)" % s["patbal"]
            else:
                mv = move_to_ins.move(cid, rebill=False); r["move"] = mv; L("v%s c%s move back: %s" % (vid, cid, mv))
                if not str(mv).startswith("moved"): r["outcome"] = "HOLD - move back failed"; out["lines"].append(r); continue
                time.sleep(0.6); cache[vid] = live(pid, vid); st = cache[vid]; s = st.get(cid); r["after_move"] = {"insbal": s["insbal"], "patbal": s["patbal"]}
        bal = s["insbal"] if not DRY else (s["insbal"] + s["patbal"]); wo = round(bal, 2)
        if DRY: r["outcome"] = "DRY would post pay 0.00 + %s %.2f (ERA-linked, check %s)" % (wocode, wo, chk.get("paymentnumber")); out["lines"].append(r); L("v%s c%s %s %s (%s %s live ins %.2f pat %.2f primary paid %.2f)" % (vid, cid, r["outcome"], why, s["cpt"], s["dos"], s["insbal"], s["patbal"], s["primary_paid"])); continue
        if faults >= 3: r["outcome"] = "not attempted - 3 faults"; out["lines"].append(r); continue
        ok, payid, resp = payreasons.post_line(pid, vid, chk, v, cid, ch, pay=0.0, wo=wo, wocode=wocode)
        time.sleep(0.7); s2 = live(pid, vid).get(cid) or {}
        r.update(outcome="posted" if ok else "FAULT", pay=0.0, wo=wo, paymentid=payid, resp=resp[:160], after={"insbal": s2.get("insbal"), "patbal": s2.get("patbal")})
        faults = 0 if ok else faults + 1
        L("v%s c%s %s %.2f ok=%s after ins %s pat %s" % (vid, cid, wocode, wo, ok, s2.get("insbal"), s2.get("patbal")))
        out["lines"].append(r); time.sleep(0.4)
json.dump(out, open("registers/era_dual_%s%s.json" % (S, "_dry" if DRY else ""), "w"), indent=1)
if not DRY:
    for r in out["lines"]:
        if r.get("outcome", "").startswith(("posted", "already")):
            reg.append({"checkid": r["checkid"], "checkclaimid": r["checkclaimid"], "visitid": r["visitid"], "chargedetailid": r["chargedetailid"], "outcome": r["outcome"].split()[0], "pay": r.get("pay"), "wo": r.get("wo"), "wocode": r.get("wocode"), "when": S})
    json.dump(reg, open(REGF, "w"), indent=1)
L("SUMMARY " + json.dumps(collections.Counter(r["outcome"].split(" (")[0][:34] for r in out["lines"])))
L("TOTAL WOCAID2ND %.2f on %d charges" % (sum(float(r["before"]["insbal"] + r["before"]["patbal"]) for r in out["lines"] if r.get("wocode") == "WOCAID2ND" and r["outcome"].startswith(("DRY", "posted"))), sum(1 for r in out["lines"] if r.get("wocode") == "WOCAID2ND" and r["outcome"].startswith(("DRY", "posted")))))
