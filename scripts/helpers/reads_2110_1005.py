# PLAIN ENGLISH (live read of every visit on the Florida Medicaid FFS $0 remit 073078977 = ERA check 1052968, 5 PM ET 10/5/2026 run)
# Decides: nothing. For each claim line of the remit it reads the visit's LIVE charges (gettxhistory visitid=) - CPT, DOS,
#   last-billed carrier, bill date, insurance/patient balance, payments and write-offs - and the chart's insurance plans
#   (getdemographic), so the run can decide per denial group (WOCAID2ND dual residuals, SMMC re-routes, cascade, cluster).
# Never touches: AMD writes.
import amd, txh, amdw, json, re, time, collections
amd.login_cached()
rows = json.load(open("scan_1005_2110/era_1052968_rows.json"))
visits = collections.OrderedDict()
for r in rows: visits.setdefault((str(r[0]), str(r[1])), []).append(r)
plans = {}; out = {}
for (pid, vid), rs in visits.items():
    if pid not in plans:
        try:
            pl, resp, dob, name, _ = amdw.plans(pid); plans[pid] = pl
        except Exception as e: plans[pid] = [{"error": str(e)[:100]}]
        time.sleep(0.2)
    try:
        root = txh.fetch_visit(pid, vid)
        chs = []
        for c in root.iter("charge"):
            if (c.get("visit") or "") != vid or c.get("void") == "1": continue
            chs.append({"cid": re.sub(r"\D", "", c.get("id") or ""), "cpt": c.get("proccode"), "dos": c.get("begindate") or c.get("dos"),
                        "carrier": c.get("carrier"), "billdate": c.get("billdate"), "fee": c.get("fee"), "insbal": c.get("insbal"), "patbal": c.get("patbal"), "paid": c.get("paid"),
                        "prov": c.get("provcode") or c.get("profile"),
                        "pays": [(p.get("carrier") or p.get("carriercode"), p.get("amount"), p.get("checknumber") or p.get("check"), p.get("date"), p.get("void")) for p in c.iter("payment")],
                        "wos": [(w.get("wocode") or w.get("code"), w.get("amount"), w.get("date"), w.get("void")) for w in c.iter("writeoff")]})
    except Exception as e: chs = [{"error": str(e)[:100]}]
    out[pid + "/" + vid] = {"era": [{"cpt": r[4], "dos": r[3][:10], "chg": r[5], "carc": r[9], "rarc": r[10], "stored_insbal": r[11], "status": r[13]} for r in rs], "live": chs}
    time.sleep(0.2)
json.dump({"plans": plans, "visits": out}, open("scan_1005_2110/reads_1052968.json", "w"), indent=1)
for pid, pl in plans.items():
    print("PLANS pat%s:" % pid, [(p["id"], p["carriercode"], p["seq"], p["begin"], p["end"]) for p in pl if "id" in p])
for k, v in out.items():
    e = v["era"][0]
    print("V", k, e["carc"], e["rarc"], "stored", e["stored_insbal"], "status", e["status"])
    for c in v["live"]:
        print("    ", c)
