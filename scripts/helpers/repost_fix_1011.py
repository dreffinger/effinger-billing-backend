# PLAIN ENGLISH (repair of the code-less 'per 277' hand posts the uploaded UHC 835s now cover - run 2026-10-11T0510Z)
# Decides: nothing new - William's 9/21/2026 REPAIR rule for a payment posted without reason codes: void the code-less payment
#   (void_tx.void_payment, Payment Entry's Void) and re-post the same ERA line through the ERA-linked Payment Entry shape
#   (payreasons.repost_visit = addpayments postingmethod=era with the remit's reasonlist). The three lines: chart 17469645
#   v19446193 99487 $64.57 + 99489 $35.66 (check 1053088 / 26259B1000319208) and v19453666 99309 $97.59 (check 1053096 /
#   26274B1000220792) - the 10/9 approved package A posted them from the 277 (claim total, no CARCs); AMD's auto-poster refused the
#   visits for that reason when the 835 arrived tonight.
# Never touches: payments that carry reason codes, write-offs, any other visit.
#   python3 repost_fix_1011.py          # dry
#   python3 repost_fix_1011.py --live   # register registers/repost_fix_2026-10-11T0510Z.json
import amd, void_tx, payreasons, txh, json, sys, time
LIVE = "--live" in sys.argv; S = "2026-10-11T0510Z"
ITEMS = [("17469645", "19446193", "1053088"), ("17469645", "19453666", "1053096")]
amd.login_cached()
reg = {"stamp": S, "live": LIVE, "items": []}
for pid, vid, checkid in ITEMS:
    st = payreasons.visit_state(pid, vid, root=txh.fetch_visit(pid, vid))
    hand = [(c["cid"], p["id"], p["amount"], p["checkno"]) for c in st for p in c["pays"] if p["void"] != "1" and p["amount"] > 0 and not p["reasons"]]
    rec = {"pid": pid, "vid": vid, "checkid": checkid, "hand_posts": hand}
    if not hand: rec["outcome"] = "no code-less payment left"; reg["items"].append(rec); print(json.dumps(rec)); continue
    if not LIVE: rec["outcome"] = "DRY: void %d code-less payment(s) then repost_visit" % len(hand); reg["items"].append(rec); print(json.dumps(rec)); continue
    rec["voids"] = []
    for cid, payid, amt, chk in hand:
        ok, msg = void_tx.void_payment(pid, cid, payid); rec["voids"].append((cid, payid, amt, ok, msg[:120])); time.sleep(0.6)
    if all(v[3] for v in rec["voids"]):
        try: rec["repost"] = payreasons.repost_visit(pid, vid, checkid, release=True)
        except Exception as e: rec["repost"] = {"outcome": "error", "error": str(e)[:300]}
    else: rec["outcome"] = "void failed - nothing re-posted"
    reg["items"].append(rec); print(json.dumps(rec, default=str)[:600]); time.sleep(0.8)
json.dump(reg, open("registers/repost_fix_%s.json" % S, "w"), indent=1, default=str)
print("saved registers/repost_fix_%s.json" % S)
