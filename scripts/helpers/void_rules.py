# PLAIN ENGLISH (Void-on-arrival rules)
# Decides: Whether any charge that has landed in AMD matches a rule William gave in advance ("that 9/5 visit is an error - void it when it comes through"), and voids it.
# Rules it uses: void_rules.json - one row per rule: patient id, date of service, optional CPT, note, and who asked. A charge is voided only when patient AND date (AND CPT if given) all match and the charge is not already voided. Matched rules are marked done with the charge id.
# Never touches: Any other charge, payments, write-offs, or the rule file's other rows.
# ---
"""Usage: python3 void_rules.py [--dry]   (runs inside the nightly cascade)"""
import amd, txh, void_tx, json, sys, datetime
amd.login_cached(); dry = "--dry" in sys.argv
rules = json.load(open("void_rules.json")); changed = False
for r in rules:
    if r.get("done"): continue
    root = txh.fetch(r["pid"])
    for c in root.iter("charge"):
        a = c.attrib
        if a.get("void") == "1" or a.get("dos") != r["dos"] or (r.get("cpt") and a.get("proccode") != r["cpt"]): continue
        if any(float(p.get("amount") or 0) != 0 for p in c.iter("payment")): print("SKIP paid charge", r["pid"], r["dos"], a.get("id")); continue
        print("VOID %s %s %s chg %s (%s)" % (r["pid"], r["dos"], a.get("proccode"), a.get("id"), r.get("note", "")), flush=True)
        if not dry:
            ok, msg = void_tx.void_charge(r["pid"], a.get("id")); print("  ->", ok, msg[:80])
            if ok: r["done"] = datetime.date.today().isoformat(); r["charge"] = a.get("id"); changed = True
if changed and not dry: json.dump(rules, open("void_rules.json", "w"), indent=1)
print("void_rules: %d open" % sum(1 for r in rules if not r.get("done")))
