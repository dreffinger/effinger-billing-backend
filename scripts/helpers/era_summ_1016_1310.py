# PLAIN ENGLISH (ERA check-details summary, 9 AM ET 10/16/2026 run 2026-10-16T1310Z) - READ ONLY.
# Decides: nothing. For each check id given it GETs /api/era/checkdetails (era_post.details caches it in era_details/)
#   and prints one line per claim and per charge line: visit, chart id, claim status, insurance balance stored at remit load,
#   processok/errors, CPT, DOS, paid, adjustment, patient amount, CARC codes with amounts and RARCs. No AMD write.
import era_post, json, sys
for cid in sys.argv[1:]:
    d = era_post.details(cid)
    vs = d.get("eracheckdetails") or []
    print("== check", cid, "claims", len(vs), "keys", [k for k in d.keys() if k != "eracheckdetails"][:12])
    for v in vs:
        print(" claim %s visit %s pid %s status %s pay %s calc %s insbal %s chargecount %s ok %s err %s rev %s" % (
            v.get("checkclaimid"), v.get("visitid"), v.get("patientid"), v.get("claimstatus"), v.get("paymentamount"),
            v.get("calculatedamount"), v.get("insurancebalance"), v.get("chargecount"), v.get("processok"), v.get("errors"), v.get("hasreversals")))
        for ch in v.get("charges", []):
            carc = ["%s%s=%s" % (c.get("payreasongroup"), c.get("reasoncode"), c.get("reasonamt")) for c in ch.get("carc", [])]
            rarc = [r.get("remarkcode") for r in ch.get("rarc", []) if r.get("remarkcode") != "#AM"]
            print("    cd %s %s %s claim %s paid %s adj %s pt %s allowed %s wo %s/%s next %s carc %s rarc %s" % (
                ch.get("chargedetailid"), ch.get("chargecode"), (ch.get("dos") or "")[:10], ch.get("claimamount"), ch.get("paymentamount"),
                ch.get("adjustmentamount"), ch.get("patientamount"), ch.get("allowedamount"), ch.get("payreasonwocode"), ch.get("payreasonwoamount"), ch.get("nextaction"), carc, rarc))
