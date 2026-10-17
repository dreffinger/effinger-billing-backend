# PLAIN ENGLISH (99344 -> 99349 recode + resend, 7 AM ET 10/17/2026 run 2026-10-17T1110Z, five charts)
# Decides: nothing new - the standing rule "a new-patient home/ALF code on an established patient -> 99349 (pcode65142)".
#   Medicare's $0 remit 350087718 (ERA 1053200, 10/17) denied each 10/01/2026 99344 CO-96 / M13 ('only one initial visit is covered
#   per specialty per medical group') - Medicare itself says each patient is established with the practice. Same action as
#   recode_99349_1011.py (William's 'go' 10/11 on the identical CO-97 pattern): for each visit verify the charge still carries
#   pcode601053 (99344), carries NO payment and the chart holds an EARLIER paid charge (the proof Medicare's M13 rests on);
#   recode.swap_proc swaps the procedure on a full-visit echo (every live charge echoed) and sends ONE frequency-1 claim to the
#   Medicare sequence (Medicare Part B takes no frequency-7 professional claims; a fully denied claim is re-sent as an original).
# Never touches: payments, write-offs, diagnosis codes, any other charge of the visit, any other visit.
#   python3 recode_99349_1017.py          # dry
#   python3 recode_99349_1017.py --live   # register registers/recode_99349_2026-10-17T1110Z.json
import amd, resave, recode, txh, json, sys, re, time
LIVE = "--live" in sys.argv; S = "2026-10-17T1110Z"
ITEMS = [("25592", "19457088", "23368910"), ("24537", "19457093", "23368915"), ("12179688", "19457096", "23368918"), ("17476438", "19457098", "23368920"), ("17476855", "19457099", "23368921")]
amd.login_cached()
reg = {"stamp": S, "live": LIVE, "items": []}
for pid, vid, cid in ITEMS:
    vis, pat, allc = resave.visit_charges(cid)
    codes = {re.sub(r"\D", "", c.get("id") or ""): c.get("proccode") for c in allc}
    rec = {"pid": pid, "vid": vid, "cid": cid, "codes": codes, "visit_insorder": vis.get("insorder")}
    root = txh.fetch("pat%s" % pid); time.sleep(0.3)
    mine = [c for c in root.iter("charge") if c.get("id") == cid or c.get("id") == "charge" + cid]
    pays = [p for c in mine for p in c.iter("payment") if p.get("void") != "1" and float(p.get("amount") or 0) != 0]
    earlier_paid = [c.get("id") for c in root.iter("charge") if c.get("void") != "1" and c.get("id") not in (cid, "charge" + cid) and any(p.get("void") != "1" and float(p.get("amount") or 0) < 0 for p in c.iter("payment"))]
    rec["earlier_paid_charges"] = len(earlier_paid); rec["payments_on_charge"] = len(pays)
    seq = (vis.get("insorder") or "1").split(",")[0]
    if codes.get(cid) != "pcode601053":
        rec["action"] = "SKIP - charge no longer carries 99344 (pcode601053)"
    elif pays:
        rec["action"] = "SKIP - charge carries a payment"
    elif not earlier_paid:
        rec["action"] = "HOLD - no earlier paid charge on the chart (not provably established) - report"
    elif not LIVE:
        rec["action"] = "DRY swap pcode601053 -> pcode65142 on c%s (full-visit echo of %d charges) + freq-1 to seq %s" % (cid, len(allc), seq)
    else:
        rec["result"] = recode.swap_proc(cid, {"pcode601053": "pcode65142"}, seq); rec["action"] = "done"
        time.sleep(0.8)
        v2, p2, c2 = resave.visit_charges(cid)
        rec["after"] = {re.sub(r"\D", "", c.get("id") or ""): c.get("proccode") for c in c2}
    reg["items"].append(rec); print(json.dumps(rec, default=str))
    json.dump(reg, open("registers/recode_99349_%s%s.json" % (S, "" if LIVE else "_dry"), "w"), indent=1, default=str)
print("saved registers/recode_99349_%s%s.json" % (S, "" if LIVE else "_dry"))
