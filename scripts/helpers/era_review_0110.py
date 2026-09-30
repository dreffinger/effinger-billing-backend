# PLAIN ENGLISH (ERA review, 0110Z 9/30/2026 run). Decides nothing. For each unposted check named on the command line, prints every
# remit line (claim, visit, CPT, DOS, paid, allowed, CAS group/code/amount, RARCs) next to the LIVE charge (fee, paid, insurance/patient
# balance, last-billed carrier, payments already carrying this check number). Read-only: gettxhistory per visit.
import amd, txh, json, sys, time
amd.login_cached()
chks = {str(c["id"]): c for c in json.load(open("scan_0930_0110/era_checks_before.json"))}
def live(pid, vid):
    root = txh.fetch_visit(pid, vid); res = {}
    for c in root.iter("charge"):
        if c.get("void") == "1" or c.get("visit") != str(vid): continue
        res[c.get("id").replace("charge", "")] = {"fee": float(c.get("fee") or 0), "paid": float(c.get("paid") or 0), "patbal": float(c.get("patbal") or 0), "insbal": float(c.get("insbal") or 0), "carrier": c.get("carrier"), "cpt": c.get("proccode"), "dos": c.get("dos"),
            "pays": [(float(p.get("amount") or 0), (p.get("checknumber") or "").strip(), p.get("carrier"), p.get("void"), p.get("date")) for p in c.iter("payment")],
            "wos": [(float(w.get("amount") or 0), (w.get("wocode") or "").strip(), w.get("void")) for w in c.iter("writeoff")]}
    return res
for cid in sys.argv[1:]:
    chk = chks[cid]; det = json.load(open("era_details/%s.json" % cid))["eracheckdetails"]
    print("=== check %s %s %s $%s deposit %s" % (cid, chk["systemcarriercode"], chk["paymentnumber"], chk["paymentamount"], chk.get("depositdate")))
    for v in det:
        pid = str(v["patientid"]); vid = str(v["visitid"])
        st = live(pid, vid); time.sleep(0.3)
        print(" claim %s v%s pat%s status=%s errors=%s" % (v.get("checkclaimid"), vid, pid, v.get("claimstatus") or v.get("status"), [e.get("id") for e in v.get("errors") or []]))
        for ch in v.get("charges") or []:
            c = str(ch["chargedetailid"]); cas = ["%s%s:%s" % (a["payreasongroup"], a["reasoncode"], a["reasonamt"]) for a in ch.get("carc") or []]
            rar = [r["remarkcode"] for r in ch.get("rarc") or [] if r["remarkcode"] != "#AM"]
            s = st.get(c)
            print("   c%s %s %s billed=%s allowed=%s paid=%s patresp=%s %s %s" % (c, ch["chargecode"], ch["dos"][:10], ch.get("chargeamount"), ch.get("allowedamount"), ch.get("paymentamount"), ch.get("patientresponsibility") or ch.get("patresp"), cas, rar))
            if s: print("      LIVE fee=%.2f paid=%.2f insbal=%.2f patbal=%.2f carrier=%s pays=%s wos=%s" % (s["fee"], s["paid"], s["insbal"], s["patbal"], s["carrier"], [(p[0], p[1], p[2], p[3]) for p in s["pays"] if p[3] != "1"], [w for w in s["wos"] if w[2] != "1"]))
            else: print("      LIVE: charge not on visit (live charges: %s)" % [(k, x["cpt"], x["dos"]) for k, x in st.items()])
