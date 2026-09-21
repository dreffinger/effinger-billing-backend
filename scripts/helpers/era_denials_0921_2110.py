# PLAIN ENGLISH (5pm ET 9/21/2026 run 2026-09-21T2110Z): the new Florida Medicaid ERA check 1051726 (073041757, $0.00) carries
#   44 $0 denial lines (CO16/N290 rendering-provider id, CO208/N286 NPI/referring id, CO256/N130 managed-care contract, CO170/N95,
#   COB7/N570, CO22/N598 other payer primary, CO29 timely). Decides: nothing. Reads each denied visit live via gettxhistory (charges,
#   balances, non-void payments by carrier, carrier billed) and getdemographic (plans + sequences) so the denial handling can classify
#   each line: secondary residual after a primary payment / never-paid primary / already $0. Never touches: AMD writes.
import amd, txh, json, re, time, resave
amd.login_cached()
CK = "1051726"
d = json.load(open("era_details/%s.json" % CK))
out = []; PL = {}; TX = {}
for c in d["eracheckdetails"]:
    pid = str(c["patientid"]); vid = str(c["visitid"])
    if pid not in TX:
        TX[pid] = txh.fetch("pat" + pid); time.sleep(0.3)
        t = amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"}), timeout=120)
        PL[pid] = [dict(re.findall(r'(id|carrier|sequence|enddate|begindate)="([^"]*)"', p)) for p in re.findall(r'<insplan [^>]*/?>', t)]
        m = re.search(r'<patient [^>]*insorder="([^"]*)"', t); PL[pid + "_order"] = m.group(1) if m else ""
        time.sleep(0.3)
    root = TX[pid]; chg = []; prof = None
    for ch in root.iter("charge"):
        if ch.get("visit") == vid and ch.get("void") != "1":
            pays = [{"carrier": p.get("carrier"), "amount": p.get("amount"), "void": p.get("void"), "date": p.get("date"), "check": p.get("checknumber"), "code": p.get("paymentcode")} for p in ch.iter("payment")]
            wos = [{"code": w.get("wocode"), "amount": w.get("amount"), "void": w.get("void"), "date": w.get("date")} for w in ch.iter("writeoff")]
            chg.append({k: ch.get(k) for k in ("id", "proccode", "dos", "fee", "carrier", "lastbilledcarrier", "datebilled", "billdate", "insbilled", "insbal", "patbal", "paid", "insorder", "payerinfo", "profile")} | {"payments": pays, "writeoffs": wos})
    if chg:
        try:
            v, p, allc = resave.visit_charges(chg[0]["id"].replace("charge", "")); prof = v.get("profile"); time.sleep(0.2)
        except Exception as e: prof = "ERR %s" % str(e)[:60]
    rec = {"checkclaimid": c["checkclaimid"], "vid": vid, "pid": pid, "dos": c["dos"][:10], "era_carrierid": c["carrierid"], "profilecode": c.get("profilecode"),
           "carc": sorted({(x["reasoncode"], x["reasonamt"]) for x in c.get("carc", [])}), "rarc": sorted({x["remarkcode"] for x in c.get("rarc", [])}),
           "era_insbal": c["insurancebalance"], "era_lines": [(x["chargecode"], x["claimamount"], x["allowedamount"]) for x in c["charges"]], "billedprimary": c.get("billedprimarysequence"),
           "visit_profile": prof, "plans": PL[pid], "patient_insorder": PL[pid + "_order"], "charges": chg}
    out.append(rec)
    print(json.dumps({k: rec[k] for k in ("checkclaimid", "vid", "pid", "dos", "carc", "rarc", "era_insbal", "visit_profile", "patient_insorder")}), "| plans", [(p.get("carrier"), p.get("sequence"), p.get("enddate")) for p in PL[pid]], "| charges", [(x["id"], x["proccode"], x["fee"], x["insbal"], x["patbal"], x["paid"], x["carrier"], x["insorder"], [(q["carrier"], q["amount"], q["void"]) for q in x["payments"] if q["void"] != "1"], [(w["code"], w["amount"]) for w in x["writeoffs"] if w["void"] != "1"]) for x in chg], flush=True)
json.dump(out, open("registers/era_denials_%s_2026-09-21T2110Z.json" % CK, "w"), indent=1)
print("done", len(out))
