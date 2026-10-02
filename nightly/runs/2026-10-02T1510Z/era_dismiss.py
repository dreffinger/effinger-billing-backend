# PLAIN ENGLISH (Dismiss ONE ERA Center check by id - the Dismiss button - for a check whose every line is already settled)
# Decides: nothing on its own. Use it for a check that carries NO postable money and whose $0 lines are already handled by the
#   denial cascade (the visit was re-routed / rebilled / written off on an earlier run), so the remit is read and the check
#   only clutters the unposted list. It never zero-posts the lines (a $0 PR-group posting can push a wrong-payer denial onto
#   the patient statement and re-queue the next plan - the Brinson 9/3 lesson), it just removes the check from the list.
# Rules it uses: refuses a check whose unpostedamount is not 0 unless --force-money is given (money is era_post / manual_post work);
#   --dry (default) only reads the list and says what it would do; --live POSTs /api/era/checks/dismiss (body = the check id as a
#   JSON string, captured from William's own click 9/7/2026) and re-reads GET /api/era/checks to confirm the check is gone.
# Register: registers/era_dismiss_register.json (checkid, carrier, check number, amount, reason, result, when, run).
# Never touches: visits, payments, write-offs, insurance plans.
"""Usage: python3 era_dismiss.py <checkid> --reason "<why every line is settled>" [--stamp <run stamp>] [--live] [--force-money]"""
import era_post, requests, json, sys, os, time, datetime
API = "https://pm-api-103.advancedmd.com/api"
REG = "registers/era_dismiss_register.json"
def main():
    a = sys.argv[1:]
    cid = next((x for x in a if x.isdigit()), None)
    if not cid: print(__doc__); sys.exit(2)
    live = "--live" in a; force = "--force-money" in a
    reason = a[a.index("--reason") + 1] if "--reason" in a else ""
    stamp = a[a.index("--stamp") + 1] if "--stamp" in a else "manual"
    cks = era_post.checks(); chk = next((c for c in cks if str(c["id"]) == cid), None)
    if not chk: print("check %s is not on the unposted list (%d checks) - nothing to do" % (cid, len(cks))); return
    unposted = float(chk.get("unpostedamount") or 0)
    print("check %s %s %s amount %s unposted %s received %s" % (cid, chk.get("systemcarriercode"), chk.get("paymentnumber"), chk.get("paymentamount"), unposted, chk.get("receiveddate")))
    if unposted != 0 and not force:
        print("REFUSED: unposted amount %.2f is not zero - post the money first (era_post / manual_post) or pass --force-money" % unposted); sys.exit(3)
    if not live:
        print("DRY: would POST /api/era/checks/dismiss %s (reason: %s)" % (cid, reason)); return
    r = requests.post(API + "/era/checks/dismiss", headers=era_post.H(), data=json.dumps(str(cid)), timeout=60)
    ok = r.status_code == 200 and '"issuccess":true' in r.text
    time.sleep(2); after = era_post.checks(); gone = not any(str(c["id"]) == cid for c in after)
    rec = {"checkid": cid, "carrier": chk.get("systemcarriercode"), "checknumber": chk.get("paymentnumber"), "amount": chk.get("paymentamount"),
           "reason": reason, "result": "dismissed" if ok else "FAILED %s %s" % (r.status_code, r.text[:120]), "gone_from_list": gone,
           "when": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), "run": stamp}
    reg = json.load(open(REG)) if os.path.exists(REG) else []; reg.append(rec); os.makedirs("registers", exist_ok=True); json.dump(reg, open(REG, "w"), indent=1)
    print("LIVE: HTTP %s ok=%s gone_from_list=%s; list now %d checks" % (r.status_code, ok, gone, len(after)))
    if not ok: print(r.text[:300]); sys.exit(1)
if __name__ == "__main__":
    main()
