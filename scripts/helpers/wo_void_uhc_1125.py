# PLAIN ENGLISH (UHC paid two CCM visits whose charges had been written off on Medicare's denial - void those write-offs, 11/25/2026)
# Decides: nothing new - the standing reversal rule (a remit paying a visit whose charges were written off -> void the write-off, then
#   post the payer's line ERA-linked). UHC check W3040204 (ERA 1053638) pays $172.85 on each of v19458938 (chart 17471216, 10/22/2026
#   99487+99489) and v19459138 (chart 12179690, 10/25/2026 99487+99489); both visits were written off in full on 11/04/2026 beside
#   Medicare's $0 answer (check 350165188 - the patients are UHC Medicare Advantage members). era_clear holds the check
#   ('unrecorded payment') and its rows are not safe for the Post button (the check carries other unposted lines - SWEEP RULE), so this
#   helper only voids the write-offs; era_fallback_0913b.py then posts each UHC line by itself (payreasons.post_line, never sweeps).
# Never touches: payments, other write-offs, other visits. Usage: python3 wo_void_uhc_1125.py [--live]
import amd, void_tx, json, sys
LIVE = "--live" in sys.argv
CH = [("17471216", "23371205"), ("17471216", "23371206"), ("12179690", "23371535"), ("12179690", "23371536")]
amd.login_cached(); out = []
for pid, cid in CH:
    ch, wos, pays = void_tx.charge_state(cid)
    live = [w for w in wos if w.get("void") != "1"]
    for w in live:
        line = {"pid": pid, "charge": cid, "wo": w.get("id"), "amount": w.get("amount"), "date": w.get("date") or w.get("postdate")}
        if not LIVE: line["result"] = "DRY would void"
        else:
            ok, msg = void_tx.void_writeoff(pid, cid, w.get("id")); line["result"] = "voided" if ok else "VOID FAIL " + msg[:100]
        print(line); out.append(line)
    if LIVE:
        ch2, _, _ = void_tx.charge_state(cid); print("  after: insbal %s patbal %s" % (ch2.get("insbalance"), ch2.get("patbalance")))
json.dump(out, open("registers/wo_void_uhc_2026-11-25T0435Z%s.json" % ("" if LIVE else "_dry"), "w"), indent=1)
