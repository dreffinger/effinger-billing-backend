# PLAIN ENGLISH (Charges dated after a patient's date of death - [DOB]) - READ ONLY.
# Decides: Nothing. For each chart the Medicare scan found with a date of death on Medicare's record it lists every live charge
#          dated AFTER that date that still carries a balance (insurance or patient) - the standing rule (cascade rule e) writes those
#          off and puts the chart on the board for William to confirm or void. Output post_death_1120.json (ids, dates, dollars).
import amd, elig_amd, txh, json
amd.login_cached(); o = [x for x in json.load(open("medicare_number_scan_1120.json")) if x["status"] == "INACTIVE"]; out = []
for x in o:
    s = elig_amd.run_plan(x["pid"], x["ins"].replace("ins", ""), False); dod = str(s.get("date_of_death") or "")
    if len(dod) != 8: continue
    for c in txh.fetch(x["pid"]).iter("charge"):
        a = c.attrib
        if a.get("void") == "1": continue
        d8 = a.get("dos")[6:] + a.get("dos")[:2] + a.get("dos")[3:5]
        if d8 > dod:
            pays = [p.get("amount") for p in c.iter("payment") if p.get("void") != "1" and abs(float(p.get("amount") or 0)) > 0.005]
            rec = {"pid": x["pid"], "dod": dod, "charge": a.get("id"), "visit": a.get("visit"), "dos": a.get("dos"), "cpt": a.get("proccode"), "fee": a.get("fee"), "insbal": a.get("insbal"), "patbal": a.get("patbal"), "carrier": a.get("carrier"), "paid": pays}
            out.append(rec); print("pat%s died %s | chg%s v%s %s %s fee %s insbal %s patbal %s at %s paid %s" % (x["pid"], dod, a.get("id"), a.get("visit"), a.get("dos"), a.get("proccode"), a.get("fee"), a.get("insbal"), a.get("patbal"), a.get("carrier"), pays))
json.dump(out, open("post_death_1120.json", "w"))
print("charges dated after death: %d on %d charts; open insurance $%.2f, open patient $%.2f, already paid lines %d" % (len(out), len({r["pid"] for r in out}), sum(float(r["insbal"] or 0) for r in out), sum(float(r["patbal"] or 0) for r in out), sum(1 for r in out if r["paid"])))
