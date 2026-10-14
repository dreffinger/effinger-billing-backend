# PLAIN ENGLISH (cards A-2026-10-14T0510Z-A / -B of the 0510Z routine, applied by the 10/14 chat pass under the standing rules)
# Decides, per visit the 0510Z run listed: (A) the primary's contractual (CO45 + CO253 + CO144/PI144 on the payer's own payment
#   reasons) that the posting never wrote off -> WOINS, so the open balance is the cost-share only (the 9/21 'inflated fee-minus-paid'
#   lesson); (B) the Medicare / MA cost-share (PR1/PR2/PR3) with NO supplement in force on the DOS (the chart's secondary begins
#   after or ended before the DOS, or UHC answered PR26/PR27) -> WOCLTREQ (William 10/13/2026: nothing stays on the patient balance).
#   A visit at $0 afterwards is released from Unbilled if it is still listed. Also the correction for tonight: the chat's rule-A
#   rebills of these already-PAID visits were wrong (a visit with the primary's payment is a write-off, never a resubmit) - at $0
#   balance the queued claim drops at claim-run time.
# Never touches: unpaid visits (48008), payments, existing write-offs.
#   python3 cards_ab_1014.py [--live]
import amd, manual_post, payreasons, txh, json, sys, time, datetime
LIVE = "--live" in sys.argv
amd.login_cached()
stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H%MZ")
def f(x): return round(float(x or 0), 2)
VISITS = {"12233534": ["14016482", "19362928", "19362932"], "17471793": ["19386227", "19386718", "19387410"], "17472114": ["19404347", "19404388", "19404389", "19404395"],
          "23671": ["14025638"], "17474649": ["19425170", "19427052", "19423214"], "22603": ["19442384"], "23254": ["44745"], "17473032": ["19402284"],
          "17473197": ["19427174", "19430635", "19434034", "19434249", "19436818", "19436968"]}
REG = {"run": stamp, "live": LIVE, "lines": [], "released": [], "left": []}
unb = {r["visitid"] for r in payreasons.unbilled_rows(all_rows=True)}
for pid, vids in VISITS.items():
    for vid in vids:
        st = payreasons.visit_state(pid, vid, txh.fetch_visit(pid, vid)); ok_all = True
        for c in st:
            bal = f(c["insbalance"])
            if bal <= 0.005: continue
            primrose = [p for p in c["pays"] if p["void"] != "1" and p["reasons"] and f(p["amount"]) > 0]
            if not primrose: REG["left"].append({"pid": pid, "vid": vid, "cid": c["cid"], "why": "no reasoned primary payment - not a card A/B line"}); ok_all = False; continue
            co = sum(f(a) for p in primrose for code, a in p["reasons"] if str(code).upper().startswith(("CO", "OA", "PI")))
            pr = sum(f(a) for p in primrose for code, a in p["reasons"] if str(code).upper().startswith("PR"))
            wo_exist = sum(f(w["amount"]) for w in c["wos"] if w["void"] != "1")
            plan = []
            missing = round(co - wo_exist, 2); rem = bal
            if missing > 0.009: a1 = min(missing, rem); plan.append(("WOINS", a1, "contractual (CO45/CO253/CO144) on the primary's own payment reasons, never written off - card A, 9/21 lesson")); rem = round(rem - a1, 2)
            if rem > 0.009: plan.append(("WOCLTREQ", rem, "Medicare/MA cost-share with no supplement in force on the DOS - card B, William 10/13/2026"))
            for code, amt, note in plan:
                carrier = c["carrier"] if c["carrier"] in manual_post.CAR else primrose[0]["carrier"]
                ok, msg = manual_post.post(c["cid"], carrier, 0.0, amt, code, "CARDSAB1014", None, note + " - chat 10/14", dry=not LIVE)
                REG["lines"].append({"pid": pid, "vid": vid, "cid": c["cid"], "cpt": c["cpt"], "dos": c["dos"], "code": code, "amount": amt, "carrier": carrier, "ok": ok, "msg": msg[:90]})
                print(pid, vid, c["cpt"], c["dos"], code, amt, carrier, ok, flush=True)
                if not ok: ok_all = False
                time.sleep(0.3 if LIVE else 0)
        if LIVE and ok_all and vid in unb:
            st2 = payreasons.visit_state(pid, vid)
            if sum(f(x["insbalance"]) for x in st2) <= 0.005:
                rok, _ = payreasons.release_visit(vid); REG["released"].append((vid, rok))
json.dump(REG, open("registers/cards_ab_%s.json" % stamp, "w"), indent=1, default=str)
tot = {}
for l in REG["lines"]: tot[l["code"]] = round(tot.get(l["code"], 0) + l["amount"], 2)
print("SUMMARY lines %d %s released %d left %d live=%s" % (len(REG["lines"]), tot, len(REG["released"]), len(REG["left"]), LIVE))
