# PLAIN ENGLISH (read-only scan, 2026-09-24T0110Z): for every $0 denial claim on ERA checks 1052824 (UNI20 PR-27 / CO-B9 / CO-29) read the chart's
# insurance plans (getdemographic), the visit's live charges/payments/insorder/billed carrier (gettxhistory), and AMD's free 271 on each open plan.
# Decides: nothing. Never touches: AMD writes.
import amd, txh, re, json, time, sys
amd.login_cached()
d = json.load(open("era_details/1052824.json"))["eracheckdetails"]
den = [c for c in d if float(c.get("paymentamount") or 0) == 0]
out = {}
seen = set()
for c in den:
    pid = str(c["patientid"]); vid = str(c["visitid"])
    cas = sorted({(r.get("payreasongroup","")+r.get("reasoncode","")) for k,v in c.items() if isinstance(v,list) for r in v if "reasoncode" in r})
    print("=== v%s pat%s %s dos %s cas %s insbal %s" % (vid, pid, c["patientname"], c["dos"][:10], cas, c["insurancebalance"]), flush=True)
    if pid not in seen:
        seen.add(pid)
        t = amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"}), timeout=120)
        plans = [dict(re.findall(r'(id|carrier|sequence|begindate|enddate|subscribernum|coverage)="([^"]*)"', p)) for p in re.findall(r'<insplan [^>]*/?>', t)]
        dec = re.search(r'deceased="([^"]*)"', t); dod = re.search(r'dod="([^"]*)"', t)
        insorder = re.search(r'<patient [^>]*insorder="([^"]*)"', t)
        print("  chart plans:", plans, "| deceased:", dec.group(1) if dec else None, dod.group(1) if dod else None, "| patient insorder:", insorder.group(1) if insorder else None, flush=True)
        out[pid] = {"plans": plans, "visits": {}}
        for p in plans:
            if p.get("enddate"): continue
            try:
                r = amd.check_eligibility(p["id"].replace("ins",""))
                st = re.search(r'eligibilitystatusid="([^"]*)"', r); act = "ACTIVE" if re.search(r'EB\*1\*', r) else ("INACTIVE" if re.search(r'EB\*6\*', r) else ("AAA" if "AAA*" in r else "?"))
                aaa = re.findall(r'AAA\*[^~]*', r)[:2]
                oth = re.findall(r'NM1\*PR\*2\*([^*~]*)', r)[:6]
                print("  271 %s %s: status %s %s aaa %s other payers %s" % (p.get("carrier"), p.get("sequence"), st.group(1) if st else "?", act, aaa, oth), flush=True)
                p["elig"] = act
                open("logs/elig_%s_%s.xml" % (pid, p["id"]), "w").write(r)
            except Exception as e:
                print("  271 error", p.get("carrier"), str(e)[:150], flush=True)
            time.sleep(0.5)
    try:
        root = txh.fetch_visit(pid, vid)
        vs = []
        for ch in root.iter("charge"):
            if ch.get("visit") != vid: continue
            pays = [(p.get("id"), p.get("amount"), p.get("checknumber"), p.get("carrier") or p.get("carrierfid"), p.get("void")) for p in ch.iter("payment")]
            vs.append({k: ch.get(k) for k in ("id","proccode","fee","insbal","patbal","carrier","billdate","void","insorder","modifiers")})
            vs[-1]["pays"] = pays
        print("  visit charges:", vs, flush=True)
        out[pid]["visits"][vid] = {"cas": cas, "charges": vs}
    except Exception as e:
        print("  txh error", str(e)[:150], flush=True)
    time.sleep(0.4)
json.dump(out, open("registers/scan_denials_2026-09-24T0110Z.json", "w"), indent=1)
