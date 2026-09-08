# PLAIN ENGLISH (Find voided charges)
# Decides: Nothing - lists charges voided on given dates and whether the void looked intended.
# Rules it uses: Read-only.
# Never touches: AMD writes.
# ---
"""Find charges voided on given dates: in gettxhistory a void shows as a sibling charge entry with negative fee and
dos = void date.  Reports (patient, visit, original charge, cpt, fee, void date) + whether the void was intended.
Usage: python3 void_scan.py 09/02/2026 09/03/2026"""
import txh, json, sys, time, collections
dates = set(sys.argv[1:]) or {"09/03/2026"}
pids = json.load(open("audit_pids.json"))
out = []; t0 = time.time()
for i, pid in enumerate(pids):
    try: root = txh.fetch(pid)
    except Exception as e: print(pid, "ERR", e, flush=True); time.sleep(5); continue
    byvisit = collections.defaultdict(list)
    for c in root.iter("charge"): byvisit[c.get("visit")].append(c)
    for v, chs in byvisit.items():
        negs = [c for c in chs if (c.get("fee") or "").startswith("-") and c.get("dos") in dates]
        for n in negs:
            orig = [c for c in chs if c.get("void") == "1" and c.get("proccode") == n.get("proccode") and c.get("id") != n.get("id")]
            live = [c for c in chs if c.get("void") != "1"]
            pays = sum(float(p.get("amount") or 0) for c in orig for p in c.iter("payment") if p.get("void") != "1")
            out.append({"patientid": pid, "patient": next((p.get("patient") for c in chs for p in c.iter("payment")), ""), "visit": v, "voiddate": n.get("dos"),
                        "cpt": n.get("proccode"), "fee": n.get("fee"), "orig_charges": [(c.get("id"), c.get("dos")) for c in orig], "live_charges_on_visit": [(c.get("id"), c.get("proccode")) for c in live], "orig_payments": pays})
    if i % 50 == 0: print("progress", i, len(out), "%.0fs" % (time.time() - t0), flush=True); json.dump(out, open("void_scan.json", "w"), indent=1)
    time.sleep(0.3)
json.dump(out, open("void_scan.json", "w"), indent=1); print("DONE", len(out))
