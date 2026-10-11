# PLAIN ENGLISH (99344 -> 99349 recode + resend on William's 'go' 10/11/2026 03:35Z / 03:37Z, charts 17470940 and 17477516)
# Decides: nothing new - the standing rule "a new-patient home/ALF code on an established patient -> 99349 (pcode65142)".
#   Medicare's $0 remit 350041718 (10/6) denied each 9/25/2026 99344 CO-97 (N211/MA15/N666); both patients are established.
#   For each visit: verify the charge still carries pcode601053 (99344) and no payment; recode.swap_proc swaps the procedure on a
#   full-visit echo (updvisitwithcharges, every live charge echoed - the 99497 on the same visit keeps its Medicare payment) and
#   sends ONE frequency-1 claim to the Medicare sequence (1) - Medicare Part B takes no frequency-7 professional claims.
# Never touches: payments, write-offs, diagnosis codes, the 99497 charge, any other visit.
#   python3 recode_99349_1011.py          # dry
#   python3 recode_99349_1011.py --live   # register registers/recode_99349_2026-10-11T0510Z.json
import amd, resave, recode, json, sys, re, time
LIVE = "--live" in sys.argv; S = "2026-10-11T0510Z"
ITEMS = [("17470940", "19456320", "23367956"), ("17477516", "19456319", "23367954")]
amd.login_cached()
reg = {"stamp": S, "live": LIVE, "items": []}
for pid, vid, cid in ITEMS:
    vis, pat, allc = resave.visit_charges(cid)
    codes = {re.sub(r"\D", "", c.get("id") or ""): c.get("proccode") for c in allc}
    rec = {"pid": pid, "vid": vid, "cid": cid, "codes": codes, "visit_insorder": vis.get("insorder")}
    if codes.get(cid) != "pcode601053":
        rec["action"] = "SKIP - charge no longer carries 99344 (pcode601053)"
    elif not LIVE:
        rec["action"] = "DRY swap pcode601053 -> pcode65142 on c%s (full-visit echo of %d charges) + freq-1 to seq 1" % (cid, len(allc))
    else:
        rec["result"] = recode.swap_proc(cid, {"pcode601053": "pcode65142"}, "1"); rec["action"] = "done"
        time.sleep(0.8)
        v2, p2, c2 = resave.visit_charges(cid)
        rec["after"] = {re.sub(r"\D", "", c.get("id") or ""): c.get("proccode") for c in c2}
    reg["items"].append(rec); print(json.dumps(rec))
json.dump(reg, open("registers/recode_99349_%s.json" % S, "w"), indent=1)
print("saved registers/recode_99349_%s.json" % S)
