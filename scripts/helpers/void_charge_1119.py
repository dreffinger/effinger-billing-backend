# PLAIN ENGLISH (Void named charges on William's word, 11/19/2026)
# Decides: Nothing. William on the Insurance Refresh Board 11/19/2026: the card of chart 17478228 "void this visit patient of a
#          different doctor" (both lines of the 10/20/2026 visit) and the duplicate-charge card of chart 17477375 "void second" (the
#          second 99306 entered for 8/7/2026; the first was paid). Voids exactly the charge ids given, the way Charge Entry's
#          Void does (void_tx.void_charge), after reading each one: refuses a charge that carries a posted payment or
#          write-off, or that is already void.
# Never touches: any other charge. Usage: python3 void_charge_1119.py <pid> <chargeid> [<chargeid> ...] [--live]
import amd, void_tx, sys, json, os
a = [x for x in sys.argv[1:] if not x.startswith("--")]; pid = a[0]; live = "--live" in sys.argv
amd.login_cached(); f = "registers/void_charge_1119.json"; reg = json.load(open(f)) if os.path.exists(f) else []
for cid in a[1:]:
    ch, wos, pays = void_tx.charge_state(cid)
    posted = [x for x in wos + pays if x.get("void") != "1"]
    print("pat%s chg%s %s %s fee %s void=%s postings=%d" % (pid, cid, ch.get("begindate"), ch.get("proccode"), ch.get("fee"), ch.get("void"), len(posted)))
    if ch.get("void") == "1": print("  already void"); continue
    if posted: print("  REFUSED - postings on the charge"); continue
    if not live: print("  DRY would void"); continue
    ok, msg = void_tx.void_charge(pid, cid); print("  void ->", ok, msg[-60:]); reg.append({"pid": pid, "charge": cid, "voided": ok})
if live: json.dump(reg, open(f, "w"), indent=1)
