# PLAIN ENGLISH (7am ET 9/20/2026 run 2026-09-20T1110Z): the new WellCare/Centene ERA check 1051721 (0917718629, $332.52) carried
#   4 paid lines (auto-posted by the Post button) and 7 $0 denial lines (1 CO109 wrong payer, 6 CO16/M56 'missing/invalid payer identifier').
# Decides: nothing. Reads each denied visit live via gettxhistory (carrier billed, last billed carrier, payer id, bill date, balances,
#   insorder, plans on the chart) so the denial handling can see whether the claim went to the right Centene product (SUN01 Sunshine vs
#   WEL04 WellCare) and whether any balance sits on the patient. Never touches: AMD writes.
import amd, txh, json, re, time
amd.login_cached()
d = json.load(open("era_details/1051721.json"))
den = [c for c in d["eracheckdetails"] if float(c.get("paymentamount") or 0) == 0]
out = []
for c in den:
    pid = str(c["patientid"]); root = txh.fetch("pat" + pid)
    t = amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"}), timeout=120)
    plans = [dict(re.findall(r'(id|carrier|sequence|enddate|subscribernum)="([^"]*)"', p)) for p in re.findall(r'<insplan [^>]*/?>', t)]
    for p in plans: p["subscribernum"] = (p.get("subscribernum") or "")[:3] + "..."
    chg = []
    for ch in root.iter("charge"):
        if ch.get("visit") == str(c["visitid"]) and ch.get("void") != "1":
            chg.append({k: ch.get(k) for k in ("id", "proccode", "dos", "carrier", "lastbilledcarrier", "datebilled", "billdate", "insbilled", "insbal", "patbal", "paid", "insorder", "payerinfo", "amount")})
    rec = {"checkclaimid": c["checkclaimid"], "vid": c["visitid"], "pid": pid, "dos": c["dos"][:10], "era_carrierid": c["carrierid"], "carc": sorted({x["reasoncode"] for x in c.get("carc", [])}), "rarc": sorted({x["remarkcode"] for x in c.get("rarc", [])}), "era_insbal": c["insurancebalance"], "claimstatus": c["claimstatus"], "plans": plans, "charges": chg}
    out.append(rec); print(json.dumps(rec)); time.sleep(0.3)
json.dump(out, open("registers/era_denials_1051721_2026-09-20T1110Z.json", "w"), indent=1)
