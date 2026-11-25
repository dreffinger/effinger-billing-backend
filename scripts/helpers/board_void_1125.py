# PLAIN ENGLISH (void the after-death CCM charge William answered 'void' on 11/25/2026)
# Decides: nothing. Card card-17477258: Medicare's record gives a date of death of [DOB]; the 09/20/2026
#   99487 (v19455614, charge 23366962, $206) was written off WOINS (reference DOD1120) with a $0 payment line on 11/20/2026 and the
#   card asked 'void or write off'. William wrote "void" (04:38 UTC). So: void the WOINS write-off, void the $0 DOD1120 payment, then
#   void the charge itself (Charge Entry's Void, void_tx.void_charge), and read the charge back as void.
# Never touches: the 07/28 and 08/23 visits (dated before the death, paid / written off by Medicare's own answers), any other chart.
# Usage: python3 board_void_1125.py [--live]
import amd, void_tx, re, json, sys
LIVE = "--live" in sys.argv; S = "2026-11-25T0435Z"
PID, VID, CID = "17477258", "19455614", "23366962"
amd.login_cached()
ch, wos, pays = void_tx.charge_state(CID)
print("charge", CID, ch.get("begindate"), ch.get("proccode"), "fee", ch.get("fee"), "void", ch.get("void"), "insbal", ch.get("insbalance"), "patbal", ch.get("patbalance"))
live_wos = [w for w in wos if w.get("void") != "1"]; live_pays = [p for p in pays if p.get("void") != "1"]
for w in live_wos: print("  WO", w.get("id"), w.get("amount"), w.get("code"), w.get("checknumber"), w.get("memo", "")[:40])
for p in live_pays: print("  PAY", p.get("id"), p.get("amount"), p.get("checknumber"))
out = {"stamp": S, "live": LIVE, "pid": PID, "visit": VID, "charge": CID, "steps": []}
if ch.get("void") == "1":
    print("already void"); out["steps"].append("already void")
elif not LIVE:
    print("DRY - would void %d write-off(s), %d payment(s), then the charge" % (len(live_wos), len(live_pays)))
else:
    for w in live_wos:
        ok, msg = void_tx.void_writeoff(PID, CID, w.get("id")); out["steps"].append(["void writeoff", w.get("id"), ok, msg[:120]]); print("  void WO", w.get("id"), ok, msg[:100])
    for p in live_pays:
        ok, msg = void_tx.void_payment(PID, CID, p.get("id")); out["steps"].append(["void payment", p.get("id"), ok, msg[:120]]); print("  void PAY", p.get("id"), ok, msg[:100])
    ok, msg = void_tx.void_charge(PID, CID); out["steps"].append(["void charge", CID, ok, msg[:120]]); print("  void CHARGE", ok, msg[:100])
    ch2, _, _ = void_tx.charge_state(CID); out["after"] = {"void": ch2.get("void"), "insbalance": ch2.get("insbalance"), "patbalance": ch2.get("patbalance")}
    print("after: void=%s insbal=%s patbal=%s" % (ch2.get("void"), ch2.get("insbalance"), ch2.get("patbalance")))
json.dump(out, open("registers/board_void_%s%s.json" % (S, "" if LIVE else "_dry"), "w"), indent=1)
