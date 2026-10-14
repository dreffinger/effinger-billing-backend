# PLAIN ENGLISH (ERA details summary, run 2026-10-14T1710Z - READ ONLY)
# Decides: nothing. Reads era_details/<checkid>.json (the GET /api/era/checkdetails cache: eracheckdetails[] = claims with
# patientid, visitid, checkclaimid, claimstatus, billedprimarysequence, charges[] with chargedetailid, chargecode, dos,
# paymentamount, claimamount, carc[], rarc[]) for the check ids on the command line and prints one line per charge so the
# run can sort the lines into money / denial-only / duplicate / reversal before a posting helper is written. No AMD call.
import json, sys, collections
for cid in sys.argv[1:]:
    det = json.load(open("era_details/%s.json" % cid))["eracheckdetails"]
    tot = 0.0; kinds = collections.Counter()
    print("## check %s claims=%d" % (cid, len(det)))
    for v in det:
        for ch in v.get("charges") or []:
            paid = float(ch.get("paymentamount") or 0); tot += paid
            carcs = ["%s%s=%.2f" % (x["payreasongroup"], x["reasoncode"], float(x["reasonamt"] or 0)) for x in ch.get("carc") or []]
            rarcs = [r["remarkcode"] for r in ch.get("rarc") or [] if r["remarkcode"] != "#AM"]
            kind = "MONEY" if paid > 0 else ("REVERSAL" if str(v.get("claimstatus")) == "3" or float(ch.get("claimamount") or 0) < 0 else "ZERO")
            kinds[kind] += 1
            print("  v%s pat%s clm%s st=%s primrose=%s c%s %s %s fee=%s paid=%.2f %s %s %s" % (
                v.get("visitid"), v.get("patientid"), v.get("checkclaimid"), v.get("claimstatus"), v.get("billedprimarysequence"),
                ch.get("chargedetailid"), ch.get("chargecode"), (ch.get("dos") or "")[:10], ch.get("claimamount"), paid, kind, "+".join(carcs), "+".join(rarcs)))
    print("  TOTAL paid %.2f  %s" % (tot, dict(kinds)))
