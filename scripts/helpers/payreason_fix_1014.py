# PLAIN ENGLISH (Unbilled 'Payment reason codes are missing or do not balance' - the no-ERA-line rows; William 10/14/2026:
#   "payment reasons are missing or do not balance - just figure out how to fix this")
# What the hold means: AMD will not build the NEXT payer's claim unless every posted payment carries reason codes that balance to
#   the fee. payreasons.py repairs the rows whose 835 is in the ERA Center (ERA-linked re-post keeps the reasons). The rows left are
#   hand-posted money with no 835 anywhere (277-posted MA primaries of 10/9, Humana/Medicaid coinsurance payments, 2022-23 Medigap
#   leftovers). For those there is nothing to re-post from, so the fix is to settle the balance the standing rules already settle:
#   (1) the primary's CONTRACTUAL (CO45 + CO253 + CO144) that was never written off -> WOINS (the 9/21 'inflated fee-minus-paid' lesson);
#   (2) coinsurance a Medicaid-family plan answered ($0.04 / $0 Sunshine, Medicaid, Humana-as-Medicaid) -> WOCAID2ND (dual rule 10/5);
#   (3) coinsurance left after a supplement paid its part, or after a Medicaid $0, with no insurance left to bill -> WOCLTREQ (William 10/13);
#   (4) a 277-posted MA/commercial PRIMARY with no remit (10/9 old-claims cards): the remainder is contractual (the 10/9 disposition
#       note) -> WOINS; (5) 2022-23 Medigap leftovers of a few dollars -> WOSMBAL.
#   When the balance reaches $0 there is no next claim to build, and the visit is released from the column.
# Never touches: payments, write-offs already posted, visits whose balance would not reach $0 (left with a reason).
#   python3 payreason_fix_1014.py            # dry
#   python3 payreason_fix_1014.py --live
import amd, manual_post, payreasons, json, re, sys, time, datetime
LIVE = "--live" in sys.argv
amd.login_cached()
stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H%MZ")
REG = {"run": stamp, "live": LIVE, "visits": [], "left": []}
MEDICAID_FAMILY = {"MCAD", "SUN01", "FLO99", "SIM01", "HUM01", "WEL04", "FCC", "UHCMA"}
def f(x): return round(float(x or 0), 2)
def log(*a):
    print(*a, flush=True); open("payreason_fix_1014.log", "a").write(time.strftime("%Y-%m-%dT%H:%M:%SZ ", time.gmtime()) + " ".join(str(x) for x in a) + "\n")

state = json.load(open("payreason_state_1014.json"))
for v in state:
    pid, vid, nxt = v["pid"], v["vid"], v["next"]
    rec = {"pid": pid, "vid": vid, "next": nxt, "charges": [], "released": None}
    all_ok = True
    for c in v["charges"]:
        cid, fee, bal = c["cid"], f(c["fee"]), f(c["insbalance"])
        pays = [p for p in c["pays"] if p["void"] != "1"]; wos = [w for w in c["wos"] if w["void"] != "1"]
        cr = {"cid": cid, "cpt": c["cpt"], "dos": c["dos"], "fee": fee, "insbal": bal, "plan": []}
        if bal <= 0.005: cr["plan"].append(("nothing", "balance already 0")); rec["charges"].append(cr); continue
        reasoned = [p for p in pays if p["reasons"] and f(p["amount"]) > 0]   # a $0 Medicaid/MA denial line (CO256 etc.) is not the primary's contractual
        codeless = [p for p in pays if not p["reasons"]]
        existing_wo = sum(f(w["amount"]) for w in wos)
        co_total = sum(f(a) for p in reasoned for code, a in p["reasons"] if str(code).upper().startswith(("CO", "OA", "PI")))
        pr_total = sum(f(a) for p in reasoned for code, a in p["reasons"] if str(code).upper().startswith("PR"))
        remaining = bal
        if reasoned:
            missing_wo = round(co_total - existing_wo, 2)
            if missing_wo > 0.009:
                amt = min(missing_wo, remaining)
                cr["plan"].append(("WOINS", amt, "contractual from the primary's CO45/CO253/CO144 never written off (payreasons 9/21 lesson)")); remaining = round(remaining - amt, 2)
            if remaining > 0.009:
                sec_paid = sum(f(p["amount"]) for p in codeless)
                fam = {p["carrier"] for p in codeless}
                if fam & MEDICAID_FAMILY and sec_paid < pr_total:
                    cr["plan"].append(("WOCAID2ND", remaining, "coinsurance answered by the Medicaid-family plan (%s paid $%.2f of $%.2f PR2) - dual rule 10/5" % ("/".join(sorted(fam)), sec_paid, pr_total)))
                elif (fee <= 110 and remaining < 7) or (remaining < 7 and c["dos"].endswith(("2022", "2023"))):
                    cr["plan"].append(("WOSMBAL", remaining, "2022-23 Medigap leftover under $7 - small balance"))
                else:
                    cr["plan"].append(("WOCLTREQ", remaining, "patient cost-share left after the supplement's answer, no insurance left to bill (William 10/13)"))
                remaining = 0.0
        else:
            # no payment carries reasons: a 277-posted MA / commercial PRIMARY (10/9 old-claims cards) - remainder is contractual
            cr["plan"].append(("WOINS", remaining, "277-posted %s primary with no remit; remainder contractual per the 10/9 disposition note - no secondary cost share" % "/".join(sorted({p["carrier"] for p in codeless})))); remaining = 0.0
        # act
        for code, amt, note in [x for x in cr["plan"] if x[0] != "nothing"]:
            carrier = c["carrier"] if c["carrier"] in manual_post.CAR else "FLO02"
            ok, msg = manual_post.post(cid, carrier, 0.0, round(amt, 2), code, "PAYREASON1014", None, "%s - chat 10/14 payreason fix" % note, dry=not LIVE)
            cr.setdefault("posted", []).append((code, round(amt, 2), carrier, ok, msg[:100]))
            if not ok: all_ok = False
            time.sleep(0.3 if LIVE else 0)
        rec["charges"].append(cr)
    if LIVE and all_ok:
        st = payreasons.visit_state(pid, vid); left = sum(f(c["insbalance"]) for c in st)
        if left <= 0.005:
            ok, msg = payreasons.release_visit(vid); rec["released"] = ok
        else:
            rec["released"] = False; rec["left_balance"] = left; REG["left"].append({"pid": pid, "vid": vid, "why": "balance %.2f after posting" % left})
    elif not all_ok: REG["left"].append({"pid": pid, "vid": vid, "why": "a write-off failed"})
    REG["visits"].append(rec); log(json.dumps(rec, default=str)); time.sleep(0.3 if LIVE else 0)
json.dump(REG, open("registers/payreason_fix_%s.json" % stamp, "w"), indent=1, default=str)
tot = {}
for r in REG["visits"]:
    for c in r["charges"]:
        for code, amt, note in [x for x in c["plan"] if x[0] != "nothing"]: tot[code] = round(tot.get(code, 0) + amt, 2)
log("SUMMARY visits %d, write-offs by code %s, released %d, left %d, live=%s" % (len(REG["visits"]), tot, sum(1 for r in REG["visits"] if r["released"]), len(REG["left"]), LIVE))
