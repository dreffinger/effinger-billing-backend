# PLAIN ENGLISH (approved-card verification, 3 AM ET 10/14/2026 run 2026-10-14T0710Z) - READ ONLY
# Decides: nothing. For every visit named on the five approved old-claims cards (A-2026-10-14T0155Z-C / J / J-dec / K / K-dec)
#   it reads the visit's LIVE transaction history (gettxhistory visitid=) and prints each charge's open insurance / patient
#   balance and every payment / write-off line with its date, so the run can tell whether the card was ALREADY APPLIED
#   (the 0310Z run's additions file says old_claims_apply.py --live ran C/J/J-dec/K/K-dec) and record it done without
#   running the package again (step 0h: "if the change is already in place ... record it done and do NOT run it").
# Never touches: anything - no AMD write of any kind.
import txh, json, sys
CARDS = {
    "A-2026-10-14T0155Z-C": [("17474496", "19422188"), ("17474496", "19425226"), ("17472859", "19438897"), ("17472859", "19438896")],
    "A-2026-10-14T0155Z-J": [("17472067", "19389115")],
    "A-2026-10-14T0155Z-J-dec": [("44984", "19418039"), ("44984", "19419573"), ("44984", "19432957"), ("44984", "19435816")],
    "A-2026-10-14T0155Z-K": [("20670", "19420291"), ("12232001", "19433032"), ("17472124", "19445180"), ("12232001", "19401825")],
    "A-2026-10-14T0155Z-K-dec": [("44984", "19389068"), ("44984", "19423860")],
}
out = {}
for card, visits in CARDS.items():
    print("==", card)
    rows = []
    for pid, vid in visits:
        root = txh.fetch_visit(pid, vid)
        for ch in root.iter("charge"):
            a = ch.attrib
            if a.get("void") == "1":
                continue
            line = {"pid": pid, "vid": vid, "cid": a.get("id"), "dos": a.get("dos"), "cpt": a.get("proccode"), "fee": a.get("fee"),
                    "insbal": a.get("insbal"), "patbal": a.get("patbal"), "paid": a.get("paid"), "carrier": a.get("carrier"), "billdate": a.get("billdate"), "tx": []}
            for t in list(ch.iter("payment")) + list(ch.iter("writeoff")):
                ta = t.attrib
                line["tx"].append({"tag": t.tag, "amount": ta.get("amount"), "date": ta.get("date"), "code": ta.get("wocode") or ta.get("paycode"),
                                   "carrier": ta.get("carrier"), "check": ta.get("checknumber"), "void": ta.get("void"), "created": (ta.get("createtime") or "")[:16]})
            rows.append(line)
            print("  v%s chg%s %s %s fee %s paid %s insbal %s patbal %s carrier %s billed %s" % (vid, line["cid"], line["dos"], line["cpt"], line["fee"], line["paid"], line["insbal"], line["patbal"], line["carrier"], line["billdate"]))
            for tx in line["tx"]:
                if tx["void"] == "1":
                    continue
                print("      %s %s %s %s %s chk %s created %s" % (tx["tag"], tx["amount"], tx["date"], tx["code"], tx["carrier"], tx["check"], tx["created"]))
    out[card] = rows
json.dump(out, open("registers/approvals_verify_2026-10-14T0710Z.json", "w"), indent=1)
print("saved registers/approvals_verify_2026-10-14T0710Z.json")
