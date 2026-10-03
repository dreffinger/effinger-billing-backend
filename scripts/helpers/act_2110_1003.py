# PLAIN ENGLISH (5 PM ET 10/3 slot, run 2026-10-03T2110Z): CLEAR the ERA checks whose every line is settled, adapted from act_1710_1003.py.
#   For each check named on the command line: re-read the LIVE charges of every claim on it - a money line must carry a non-void payment with the
#   check's payment number (posted ERA-linked by era_new_1003_2110.py); a $0 line is settled when the charge's insurance balance is already 0
#   (adjudicated earlier - the TRICARE CO-29 lines were written off before this 835 arrived) or when it is a denial-only line handed to the
#   board (PI-252 documentation denials on CCM, CO-147 on a 99497 beside a paid 99223 - never zero-posted). Any other open line HOLDS the check.
#   A settled check is DISMISSED (POST /api/era/checks/dismiss, the captured shape). Then GET /api/era/checks is re-read and saved.
#   --dry = read + plan only, no dismiss. Never touches: the Florida Blue takeback check 1052906 (William's decision), any chart, any plan.
import amd, txh, era_post, json, sys, time, requests
DRY = "--dry" in sys.argv; STAMP = "2026-10-03T2110Z"
CIDS = [a for a in sys.argv[1:] if not a.startswith("--")]
DENIAL_TO_BOARD = ("PI252", "CO147")
amd.login_cached()
chks = {str(c["id"]): c for c in json.load(open("registers/era_checks_before_%s.json" % STAMP))}
rec = {"stamp": STAMP, "dry": DRY, "checks": {}}
for CID in CIDS:
    chk = chks[CID]; TRN = chk["paymentnumber"]; det = json.load(open("era_details/%s.json" % CID))["eracheckdetails"]
    lines = []; open_lines = 0
    for v in det:
        pid, vid = str(v["patientid"]), str(v["visitid"])
        root = txh.fetch_visit(pid, vid); time.sleep(0.3)
        live = {c.get("id").replace("charge", ""): c for c in root.iter("charge") if c.get("void") != "1" and c.get("visit") == vid}
        for ch in v["charges"]:
            cid = str(ch["chargedetailid"]); c = live.get(cid); paid = float(ch.get("paymentamount") or 0)
            carcs = [a["reasoncode"] for a in ch.get("carc") or []]
            if c is None: st = "OPEN - charge not live"; open_lines += 1
            else:
                pays = [(p.get("checknumber") or "").strip() for p in c.iter("payment") if p.get("void") != "1"]
                insbal = float(c.get("insbal") or 0)
                if paid > 0:
                    if TRN in pays: st = "posted (%s on the charge), insbal %.2f" % (TRN, insbal)
                    else: st = "OPEN - money line without this check's payment"; open_lines += 1
                elif insbal == 0: st = "settled - insurance balance already 0 (%s)" % "+".join(carcs)
                elif any(x in carcs for x in DENIAL_TO_BOARD): st = "denial-only %s $%.2f open on %s - handed to the board" % ("+".join(carcs), insbal, c.get("carrier"))
                else: st = "OPEN - unhandled $0 line %s insbal %.2f" % (carcs, insbal); open_lines += 1
            lines.append({"visitid": vid, "pid": pid, "chargedetailid": cid, "cpt": ch["chargecode"], "dos": ch["dos"][:10], "paid": paid, "claimamount": ch.get("claimamount"), "carcs": carcs, "state": st})
            print("chk %s v%s pat%s c%s %s %s paid %.2f -> %s" % (CID, vid, pid, cid, ch["chargecode"], ch["dos"][:10], paid, st), flush=True)
    r = {"trn": TRN, "carrier": chk["systemcarriercode"], "amount": chk["paymentamount"], "open_lines": open_lines, "lines": lines}
    if open_lines == 0 and not DRY:
        rr = requests.post(era_post.API + "/era/checks/dismiss", headers=era_post.H(), data=json.dumps(str(CID)), timeout=60)
        print("dismiss %s -> HTTP %s %s" % (CID, rr.status_code, rr.text[:120])); r["dismiss"] = rr.status_code; time.sleep(1.0)
    elif open_lines: print("NOT dismissed %s - %d open line(s)" % (CID, open_lines)); r["dismiss"] = "held - open lines"
    else: print("DRY - would dismiss %s" % CID); r["dismiss"] = "dry"
    rec["checks"][CID] = r
after = era_post.checks(); print("ERA unposted after:", [(c.get("id"), c.get("systemcarriercode"), c.get("unpostedamount")) for c in after])
json.dump({"after": after}, open("registers/era_checks_after_%s%s.json" % (STAMP, ".dry" if DRY else ""), "w"), indent=1, default=str)
json.dump(rec, open("registers/act_%s%s.json" % (STAMP, ".dry" if DRY else ""), "w"), indent=1)
