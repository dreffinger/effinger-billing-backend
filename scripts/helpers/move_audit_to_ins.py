# PLAIN ENGLISH (9/3 balances back to insurance)
# Decides: Every audit charge sitting on a patient balance after a wrong-payer denial goes back to insurance; flags it for rebill once the new plan is on file.
# Rules it uses: Wrong-payer denials never stay on the patient.
# Never touches: Rebilling - that came later.
# ---
"""William 9/3 11:55 PM: put every audit charge's patient balance back on insurance now; flag for rebill under the
new insurance once it's on file (pending_new_insurance.json).  No rebill here."""
import move_to_ins, json, time, re
hits = json.load(open("audit_pr_transfer.json"))
rows = [x for x in hits if float(x["patbalance"] or 0) > 0]
log = open("move_audit_to_ins.log", "a")
done = {m.group(1) for line in open("move_audit_to_ins.log") for m in [re.search(r"OK (\d+)", line)] if m}
pend = json.load(open("pending_new_insurance.json")) if __import__("os").path.exists("pending_new_insurance.json") else {}
n = 0; tot = 0.0
for x in rows:
    cid = x["chargeid"]
    key = "%s|%s" % (x["patient"], x["patientid"])
    p = pend.setdefault(key, {"patient": x["patient"], "patientid": x["patientid"], "old_carrier": set(), "charges": []})
    if isinstance(p["old_carrier"], list): p["old_carrier"] = set(p["old_carrier"])
    p["old_carrier"].add(x["reasons"][0][2])
    if not any(c["chargeid"] == cid for c in p["charges"]):
        p["charges"].append({"chargeid": cid, "visit": x["visit"], "dos": x["dos"], "cpt": x["cpt"], "amount": float(x["patbalance"]), "codes": sorted({r[0] for r in x["reasons"]}), "status": "moved to insurance 9/3 - rebill when new plan on file"})
    if cid in done: continue
    try:
        res = move_to_ins.move(cid)
    except Exception as e:
        res = "EXC " + str(e)[:100]
    ok = res.startswith("moved")
    msg = "%s %s %s %s %s -> %s" % ("OK" if ok else "ERR", cid, x["patient"], x["dos"], x["patbalance"], res)
    print(msg, flush=True); log.write(msg + "\n"); log.flush()
    if ok: n += 1; tot += float(x["patbalance"])
    time.sleep(0.5)
for p in pend.values(): p["old_carrier"] = sorted(p["old_carrier"])
json.dump(pend, open("pending_new_insurance.json", "w"), indent=1)
print("moved %d charges $%.2f; pending list %d patients" % (n, tot, len(pend)))
