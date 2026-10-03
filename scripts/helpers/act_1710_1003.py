# PLAIN ENGLISH (1 PM ET 10/3 slot, run 2026-10-03T1710Z): CLEAR the new UHC ERA check 1052947 (W0739587, $690.31) once every line is settled.
#   (1) Re-reads the LIVE charges of every claim on the check: the 8 money lines must each carry a non-void payment with this check number
#       (posted ERA-linked by era_new_1003_1710.py earlier this run); the 2 PR-27 'coverage terminated' $0 lines (pat17476042 v19453848 9/5 and
#       v19453833 9/6, HCA 99233) must be on a carrier other than UNI20 - that chart was re-routed to Medicare 9/9 + 9/23 (UHC MA ended 8/19/2026):
#       v19453833 is already PAID by Medicare 9/22 (coinsurance 21.80 on the patient, no secondary), v19453848 is at Medicare since 9/23 (pending).
#       A PR-27 line is NEVER zero-posted (the $0 post transfers the charge to the patient balance - the 9/24 pr27_fix lesson), so era_clear.py's
#       zero-post is not used on this check; the check is DISMISSED (POST /api/era/checks/dismiss, the captured shape) when no line is open.
#   (2) Re-reads GET /api/era/checks and writes registers/era_checks_after_<stamp>.json + registers/act_<stamp>.json.
#   --dry = read + plan only, no dismiss. Never touches: the Florida Blue takeback check 1052906 (William's decision), any chart, any plan.
import amd, txh, era_post, json, sys, time, requests
DRY = "--dry" in sys.argv; STAMP = "2026-10-03T1710Z"; CID = 1052947; TRN = "W0739587"
amd.login_cached()
det = json.load(open("era_details/%s.json" % CID))["eracheckdetails"]
rec = {"stamp": STAMP, "checkid": CID, "dry": DRY, "lines": []}; open_lines = 0
for v in det:
    pid, vid = str(v["patientid"]), str(v["visitid"])
    root = txh.fetch_visit(pid, vid); time.sleep(0.3)
    live = {c.get("id").replace("charge", ""): c for c in root.iter("charge") if c.get("void") != "1" and c.get("visit") == vid}
    for ch in v["charges"]:
        cid = str(ch["chargedetailid"]); c = live.get(cid); paid = float(ch.get("paymentamount") or 0)
        carcs = [a["reasoncode"] for a in ch.get("carc") or []]
        if c is None: st = "NOT LIVE"; open_lines += 1
        else:
            pays = [(p.get("checknumber") or "").strip() for p in c.iter("payment") if p.get("void") != "1"]
            insbal = float(c.get("insbal") or 0)
            if paid > 0: st = "posted (W0739587 on the charge)" if TRN in pays else "OPEN - money line without this check's payment"; open_lines += 0 if TRN in pays else 1
            elif "PR27" in carcs: st = ("PR-27 wrong payer - visit already at %s (billdate %s, insbal %.2f, paid %s) - nothing to post" % (c.get("carrier"), c.get("billdate"), insbal, c.get("paid"))) if c.get("carrier") != "UNI20" else "OPEN - PR-27 visit still at UNI20 (cascade needed)"; open_lines += 1 if c.get("carrier") == "UNI20" else 0
            else: st = "OPEN - unhandled $0 line %s" % carcs; open_lines += 1
        rec["lines"].append({"visitid": vid, "pid": pid, "chargedetailid": cid, "cpt": ch["chargecode"], "dos": ch["dos"][:10], "paid": paid, "carcs": carcs, "state": st})
        print("v%s pat%s c%s %s %s paid %.2f -> %s" % (vid, pid, cid, ch["chargecode"], ch["dos"][:10], paid, st), flush=True)
print("open lines:", open_lines)
if open_lines == 0 and not DRY:
    r = requests.post(era_post.API + "/era/checks/dismiss", headers=era_post.H(), data=json.dumps(str(CID)), timeout=60)
    print("dismiss %s -> HTTP %s %s" % (CID, r.status_code, r.text[:120])); rec["dismiss"] = r.status_code
    time.sleep(1.0)
elif open_lines:
    print("NOT dismissed - %d open line(s)" % open_lines); rec["dismiss"] = "held - open lines"
else: print("DRY - would dismiss %s" % CID); rec["dismiss"] = "dry"
after = era_post.checks(); print("ERA unposted after:", [(c.get("id"), c.get("unpostedamount")) for c in after])
json.dump({"after": after}, open("registers/era_checks_after_%s%s.json" % (STAMP, ".dry" if DRY else ""), "w"), indent=1, default=str)
json.dump(rec, open("registers/act_%s%s.json" % (STAMP, ".dry" if DRY else ""), "w"), indent=1)
