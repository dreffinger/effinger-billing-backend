# PLAIN ENGLISH (void specific visits the Claimocity feed ingest created by mistake - William 10/28/2026: "accept duplicates and void them").
# Decides: nothing. You name the visits (pid:vid pairs, e.g. pat17477204:vst19459522); for each one it re-reads the chart's
#   transaction history, refuses any visit that carries a payment, and in --live mode voids every live charge on that visit with the
#   proven charge void (void_tx.void_charge, action=void class=void). --dry (default) only lists what it would void.
# Why it exists (10/30/2026): the 10/29 daily feed run re-read September files that were already in AdvancedMD through the old
#   integration; two 9/2 home visits had been entered as 99349 (the Claim Inspector's new->established swap), the feed said 99344, so the
#   CPT+DOS dedupe missed them and entered a second visit for the same encounter. claimocity_import now treats the same E/M family on
#   the same DOS as the same encounter; this helper cleans up the two that slipped through.
# Register: registers/feed_void_visits.json (appends one record per visit: pid, vid, charges voided, billdate seen, when, mode).
# Usage: python3 claimocity_void_visits.py pat...:vst... [pat...:vst... ...] [--live] [--why "<text>"]
import amd, txh, void_tx, sys, re, json, os, datetime
live = "--live" in sys.argv
why = sys.argv[sys.argv.index("--why") + 1] if "--why" in sys.argv else "duplicate of an encounter already in AdvancedMD"
# 11/09/2026 fix: the --why VALUE must not be read as a pid:vid pair as well (it used to crash the run after the voids).
_skip = {sys.argv.index("--why") + 1} if "--why" in sys.argv else set()
args = [a for i, a in enumerate(sys.argv) if i >= 1 and not a.startswith("--") and i not in _skip]
REG = "registers/feed_void_visits.json"
reg = json.load(open(REG)) if os.path.exists(REG) else []
amd.login_cached()
for pair in args:
    pid, vid = pair.split(":"); vnum = re.sub(r"\D", "", vid)
    root = txh.fetch_visit(pid, vid)
    charges = [c.attrib for c in root.iter("charge") if re.sub(r"\D", "", c.attrib.get("visitid") or c.attrib.get("visit") or "") == vnum and c.attrib.get("void") != "1"]
    pays = [p.attrib for p in root.iter("payment") if float(p.attrib.get("amount") or 0) != 0]
    print("%s %s: %d live charge(s) %s, billdate %s, payments %d" % (pid, vid, len(charges), [c.get("proccode") for c in charges], (charges[0].get("billdate") if charges else "-"), len(pays)))
    if pays:
        print("   SKIP - a payment is posted on this visit; never void a paid visit"); continue
    if not charges:
        print("   nothing live to void"); continue
    rec = {"pid": pid, "vid": vid, "charges": [], "billdate": charges[0].get("billdate"), "why": why, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "mode": "live" if live else "dry"}
    for c in charges:
        if live:
            ok, msg = void_tx.void_charge(pid, c.get("id"))
            print("   void charge %s %s -> %s %s" % (c.get("id"), c.get("proccode"), "OK" if ok else "FAILED", "" if ok else msg))
            rec["charges"].append({"id": c.get("id"), "cpt": c.get("proccode"), "ok": ok})
        else:
            print("   DRY would void charge %s %s" % (c.get("id"), c.get("proccode")))
            rec["charges"].append({"id": c.get("id"), "cpt": c.get("proccode"), "ok": None})
    if live:
        back = txh.fetch_visit(pid, vid)
        left = [c.attrib for c in back.iter("charge") if re.sub(r"\D", "", c.attrib.get("visitid") or c.attrib.get("visit") or "") == vnum and c.attrib.get("void") != "1"]
        print("   re-read: %d live charge(s) left on the visit" % len(left)); rec["left_live"] = len(left)
    reg.append(rec)
os.makedirs("registers", exist_ok=True); json.dump(reg, open(REG, "w"), indent=1)
print("register ->", REG, "(%s)" % ("live" if live else "dry"))
