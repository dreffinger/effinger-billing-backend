# PLAIN ENGLISH (Unbilled 'prior payor' triage, 5am ET 9/20/2026 run 2026-09-20T0910Z)
# Decides: nothing. For every Unbilled row whose error is 'A payment from the prior payor is required',
#   reads the patient's gettxhistory and prints that visit's live charges: carrier billed, bill date, paid,
#   insurance balance, insorder - so the run can tell 'primary out and unanswered' (release) from
#   'primary paid, secondary waiting' (bill the secondary) from 'window passed' (write off). Never touches: AMD writes.
import amd, re, json, time, sys, collections
s = json.load(open("scan_0912/summary_before.json"))
rows = [r for r in s["unbilled"] if any(e.startswith("A payment from the prior") for e in (r.get("_errs") or []))]
pids = sorted({r["patientid"] for r in rows})
byv = {r["id"]: r for r in rows}
amd.login_cached()
out = []
for pid in pids:
    t = amd.post(amd.msg("gettxhistory", "demographics", {"patientid": pid, "filterhistory": "0", "pagenumber": "1", "typefilter": "1", "sortbypayment": "false", "groupbyvisit": "0", "sortdescending": "1", "visitid": "0", "getmemo": "false", "nocookie": "1"}), timeout=120)
    chg = [dict(re.findall(r'(\w+)="([^"]*)"', m.group(0))) for m in re.finditer(r'<charge [^>]*/?>', t)]
    for c in chg:
        if c.get("visit") in byv and c.get("void", "0") in ("0", ""):
            o = {k: c.get(k) for k in ("id", "visit", "proccode", "dos", "carrier", "lastbilledcarrier", "datebilled", "billdate", "insbilled", "insbal", "patbal", "paid", "insorder", "payerinfo", "lastpaymentdate", "amount", "fee")}
            o["patientid"] = pid
            # payments on the charge
            o["pays"] = re.findall(r'<payment [^>]*carrier="([^"]*)"[^>]*amount="([^"]*)"[^>]*date="([^"]*)"', t[t.find('<charge id="%s"' % c["id"]):][:6000])
            out.append(o)
    time.sleep(0.3)
json.dump(out, open("registers/unbilled_prior_2026-09-20T0910Z.json", "w"), indent=1)
for o in out:
    print(o["visit"], "pat%s" % o["patientid"], o["proccode"], o["dos"], "car=%s last=%s bill=%s insbilled=%s paid=%s insbal=%s patbal=%s order=%s" % (o["carrier"], o["lastbilledcarrier"], o["datebilled"] or o["billdate"], o["insbilled"], o["paid"], o["insbal"], o["patbal"], o["insorder"]))
print(len(out), "charges on", len({o['visit'] for o in out}), "visits of", len(byv))
