# PLAIN ENGLISH (Dismiss a $0 ERA check whose lines are already settled - the ERA Center 'Dismiss' click for a remit nothing can post)
# Decides: whether ONE check on the ERA Center unposted list carries nothing to post - the check's paymentamount and unpostedamount are
#   both 0, every claim line's paymentamount is 0, every claim is validated (processok, no errors), and every charge the remit names is
#   already at $0 insurance balance on the LIVE chart (gettxhistory visitid=) - and, only then, dismisses it
#   (POST /api/era/checks/dismiss with the check id as a JSON string - the shape captured from William's own click on 9/7/2026,
#   the same call era_clear.dismiss makes). The remit stays readable afterwards: era_details/<checkid>.json is cached first and
#   POST /api/era/checks/reversedismiss restores it to the list if it is ever needed again.
# Why not era_clear.py: era_clear HOLDS a check whose $0 lines carry CAS adjustments ('denial with write-off (cascade handles)') so the
#   cascade can read the denial. Once the cascade is done with it (10/7 1310Z finding on 1053025: Medicaid-MMA secondary $0 CO-23/OA-23
#   on Medicare-paid lines already at $0) the check only clutters the unposted list; this helper is that last click, one check at a time.
# Rules it uses: ERA step 5(e) - a check leaves the unposted list only when every line is settled; a $0 open insurance balance on every
#   named charge = already adjudicated, record only, post nothing. Any money on the check, any charge with an open insurance balance,
#   any claim not validated, or a charge the live chart does not carry = HOLD, nothing written.
# Writes (only with --live): ONE POST /api/era/checks/dismiss. Register registers/era_dismiss_<stamp>[_dry].json (one entry per run).
# Never touches: payments, write-offs, balances, plans, claims; never dismisses a check with money or an open balance.
# Usage: cd /home/claude/unbilled && python3 era_dismiss_zero.py <checkid> [--live] [--stamp <UTC stamp>]
import amd, era_post, txh, requests, json, sys, os, re, datetime

a = sys.argv[1:]
LIVE = "--live" in a
STAMP = a[a.index("--stamp") + 1] if "--stamp" in a else datetime.datetime.utcnow().strftime("%Y-%m-%dT%H%MZ")
cids = [x for x in a if x.isdigit()]
if len(cids) != 1:
    print("usage: python3 era_dismiss_zero.py <checkid> [--live] [--stamp <UTC stamp>]"); sys.exit(2)
CID = cids[0]
REG = "registers/era_dismiss_%s%s.json" % (STAMP, "" if LIVE else "_dry")
num = lambda s: re.sub(r"\D", "", str(s or ""))
money = lambda v: abs(float(v or 0)) > 0.005

def L(m): print(m, flush=True)

def save(rec):
    os.makedirs("registers", exist_ok=True)
    old = json.load(open(REG)) if os.path.exists(REG) else []
    old.append(rec); json.dump(old, open(REG, "w"), indent=1)

def main():
    amd.login_cached()
    rec = {"checkid": CID, "stamp": STAMP, "live": LIVE, "holds": [], "lines": [], "outcome": ""}
    chk = [c for c in era_post.checks() if str(c.get("id")) == CID]
    if not chk:
        rec["holds"].append("check %s is not on the unposted list" % CID); rec["outcome"] = "hold"; save(rec); L("HOLD: " + rec["holds"][0]); return 1
    chk = chk[0]
    rec["carrier"] = chk.get("systemcarriercode"); rec["paymentnumber"] = chk.get("paymentnumber")
    pay, unp = float(chk.get("paymentamount") or 0), float(chk.get("unpostedamount") or 0)
    if money(pay) or money(unp):
        rec["holds"].append("check carries money: paymentamount %.2f unpostedamount %.2f" % (pay, unp))
    det = era_post.details(CID)                     # caches era_details/<checkid>.json before anything changes
    claims = det.get("eracheckdetails") or []
    if not claims: rec["holds"].append("checkdetails returned no claim lines")
    for v in claims:
        vid, pid = str(v.get("visitid")), str(v.get("patientid"))
        if v.get("errors") or not v.get("processok"): rec["holds"].append("visit %s not validated (errors / processok false)" % vid)
        if money(v.get("paymentamount")): rec["holds"].append("visit %s claim paymentamount %.2f" % (vid, float(v.get("paymentamount"))))
        try:
            root = txh.fetch_visit(pid, vid)
            live = {num(c.get("id")): c for c in root.iter("charge") if c.get("void") != "1"}
        except Exception as e:
            rec["holds"].append("visit %s live read failed: %s" % (vid, str(e)[:80])); continue
        for ch in v.get("charges") or []:
            cdid = num(ch.get("chargedetailid")); lc = live.get(cdid)
            line = {"visitid": vid, "chargedetailid": cdid, "cpt": ch.get("chargecode"), "dos": (ch.get("dos") or "")[:10],
                    "remit_paid": ch.get("paymentamount"), "remit_adj": ch.get("adjustmentamount"),
                    "carc": [(c.get("payreasongroup"), c.get("reasoncode"), c.get("reasonamt")) for c in ch.get("carc") or []]}
            if lc is None:
                rec["holds"].append("visit %s charge %s not on the live chart" % (vid, cdid))
            else:
                line["live_insbal"] = float(lc.get("insbal") or 0); line["live_patbal"] = float(lc.get("patbal") or 0)
                line["live_carrier"] = lc.get("carrier", "")
                if money(line["live_insbal"]): rec["holds"].append("visit %s charge %s open insurance balance %.2f" % (vid, cdid, line["live_insbal"]))
            if money(ch.get("paymentamount")): rec["holds"].append("visit %s charge %s remit paymentamount %s" % (vid, cdid, ch.get("paymentamount")))
            rec["lines"].append(line)
    for ln in rec["lines"]: L("  line v%s chg %s %s %s remit paid %s adj %s live insbal %s patbal %s carrier %s" % (ln["visitid"], ln["chargedetailid"], ln["cpt"], ln["dos"], ln["remit_paid"], ln["remit_adj"], ln.get("live_insbal"), ln.get("live_patbal"), ln.get("live_carrier")))
    if rec["holds"]:
        rec["outcome"] = "hold"; save(rec)
        for h in rec["holds"]: L("HOLD: " + h)
        return 1
    if not LIVE:
        rec["outcome"] = "dry - would dismiss"; save(rec); L("DRY: check %s %s %s - nothing to post, every charge at $0 insurance balance; --live dismisses it" % (CID, rec["carrier"], rec["paymentnumber"])); return 0
    r = requests.post(era_post.API + "/era/checks/dismiss", headers=era_post.H(), data=json.dumps(str(CID)), timeout=60)
    ok = r.status_code == 200 and '"issuccess":true' in r.text
    rec["dismiss_http"] = r.status_code; rec["dismiss_text"] = r.text[:160]
    still = [c for c in era_post.checks() if str(c.get("id")) == CID]
    rec["outcome"] = "dismissed" if ok and not still else ("dismiss answered ok but check still listed" if ok else "dismiss refused")
    save(rec); L("%s: check %s -> %s (HTTP %s) %s" % ("DISMISSED" if rec["outcome"] == "dismissed" else "NOT DISMISSED", CID, rec["outcome"], r.status_code, r.text[:120]))
    return 0 if rec["outcome"] == "dismissed" else 1

if __name__ == "__main__":
    sys.exit(main())
