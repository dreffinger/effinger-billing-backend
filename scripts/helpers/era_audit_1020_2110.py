# PLAIN ENGLISH (post-Post-button audit of the three checks the 5 PM ET 10/20/2026 run 2026-10-20T2110Z posted - READ ONLY)
# Decides: nothing. era_post.py --all-unposted (the ERA Center Post button) posted UnitedHealthcare 1053227 (two paid 99233s on chart 17477638, three $0 PR-27 secondary answers on charts 17473661 / 17470802)
#   by the GitHub slot / this run's engine pass. The Post button is known to leave the CO-45 contractual on the PATIENT balance for some
#   carriers (Florida Blue, VA CCN, CAP07/UHC, Ambetter, Humana, Medicaid FFS - the 9/23 and 9/25 lessons). This helper reads every
#   posted line's live charge (txh.fetch_visit) and prints, beside the remit's paid / CO / PR amounts, what is on the charge now:
#   insurance balance, patient balance, the payments carrying this check's trace number and their reason codes. Output:
#   registers/era_audit_2026-10-20T1510Z.json + one line per charge (chart / visit / charge ids and dollars only). No AMD write.
import json, sys, time, txh, amd
S = "2026-10-20T2110Z"; CHECKS = [1053227]
amd.login_cached(); out = []
def live(pid, vid):
    root = txh.fetch_visit(pid, vid); res = {}
    for c in root.iter("charge"):
        if c.get("void") == "1" or c.get("visit") != str(vid): continue
        res[c.get("id").replace("charge", "")] = {"cpt": c.get("proccode"), "fee": float(c.get("fee") or 0), "paid": float(c.get("paid") or 0),
            "patbal": float(c.get("patbal") or 0), "insbal": float(c.get("insbal") or 0), "carrier": c.get("carrier"),
            "pays": [{"amt": float(p.get("amount") or 0), "chk": (p.get("checknumber") or "").strip(), "car": p.get("carrier"), "void": p.get("void"),
                      "reasons": [(r.get("code") or r.get("reasoncode"), r.get("amount")) for r in p.iter() if r.tag.lower().startswith("reason") and r is not p]} for p in c.iter("payment")],
            "wos": [(float(w.get("amount") or 0), (w.get("code") or w.get("wocode") or "").strip(), w.get("void")) for w in c.iter("writeoff")]}
    return res
first = True
for ck in CHECKS:
    d = json.load(open("era_details/%d.json" % ck))
    claims = d if isinstance(d, list) else d.get("eracheckdetails") or d.get("claims") or []
    for cl in claims:
        pid, vid = cl.get("patientid"), cl.get("visitid")
        try: lv = live(pid, vid)
        except Exception as e: lv = {"error": str(e)[:120]}
        for ch in cl.get("charges") or []:
            if first: print("line keys:", sorted(ch.keys())); first = False
            cid = str(ch.get("chargedetailid"))
            adj = ch.get("adjustments") or ch.get("adjustmentlist") or ch.get("reasons") or []
            row = {"check": ck, "pid": pid, "vid": vid, "cid": cid, "cpt": ch.get("cpt") or ch.get("proccode"), "dos": str(ch.get("dos"))[:10],
                   "remit_charge": ch.get("chargeamount") or ch.get("billedamount"), "remit_allowed": ch.get("allowedamount"), "remit_paid": ch.get("paidamount") or ch.get("paymentamount"),
                   "remit_adj": adj if isinstance(adj, (list, dict)) else str(adj)[:200], "live": lv.get(cid) or lv.get("error") or "charge not on visit"}
            out.append(row)
            l = row["live"] if isinstance(row["live"], dict) else {}
            print("%d v%s c%s %s %s | remit paid %s allowed %s | live ins %.2f pat %.2f paid %.2f | pays %s | wos %s" % (ck, vid, cid, row["cpt"], row["dos"], row["remit_paid"], row["remit_allowed"],
                  l.get("insbal", 0), l.get("patbal", 0), l.get("paid", 0), [(p["amt"], p["chk"], p["void"], p["reasons"][:4]) for p in l.get("pays", [])][-3:], l.get("wos", [])[-3:]), flush=True)
        time.sleep(0.2)
json.dump({"stamp": S, "rows": out}, open("registers/era_audit_%s.json" % S, "w"), indent=1, default=str)
print("rows", len(out))
