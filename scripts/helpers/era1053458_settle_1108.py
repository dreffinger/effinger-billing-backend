# PLAIN ENGLISH (ERA check 1053458 UHC W2348427 - settle the repeat $0 PR26/PR27 cluster, 7:39 PM ET 11/7 slot run 2026-11-08T0039Z)
# Decides: nothing new. Medicare already paid every one of these lines; the chart's UHC plan answered PR27 'coverage terminated' /
#   PR26 'prior to coverage' (= UHC is not the payer for those dates), and the ERA poster had left the Medicare coinsurance on the
#   PATIENT balance. AMD 271 on every plan of the five charts: no live secondary for those dates (UHC Medigap dead on 17472910 /
#   17473571 / 17471174; 17475777 and 17476042 joined UHC Medicare Advantage AFTER the denied dates). Standing rules applied:
#   wrong-payer denials never stay on the patient (William 9/3) -> move_to_ins.move(cid, rebill=False);
#   cost-share with no supplement in force on the DOS -> WOCLTREQ (William 10/13 'nothing stays on the patient balance');
#   a Medicare payment whose CO-45 was never adjusted -> WOINS for the contractual first (payreasons repair, 10/14 rule).
#   Every charge is re-read live before each write; amounts come from the live balances, never from the remit.
# Never touches: claims, plans, the ERA Center. --live writes; default is a dry plan. Register registers/era1053458_settle_<stamp>[_dry].json
import sys, json, os, time
sys.path.insert(0, "/home/claude/unbilled")
import txh, payreasons, move_to_ins, manual_post
LIVE = "--live" in sys.argv; STAMP = "2026-11-08T0039Z"
REG = "registers/era1053458_settle_%s%s.json" % (STAMP, "" if LIVE else "_dry")
# cid -> (pid, contractual WOINS to post first or 0)
LINES = {
 "17472910": ["22482619","22483325","23316776","23319639","22484480","22484503","22482808","22483940","22482966","23318263"],
 "17475777": ["23353778","23353038","23355203","23355204"],
 "17473571": ["23345947","23338639","23338924","23342195","23321905","23320684","23320326","23326855","23323521","23329572",
              "23320703","23324186","23327002","23324509","23327003","23334397","23333177","23325353"],
 "17471174": ["23350731"],
 "17476042": ["23361594"],
}
WOINS_FIRST = {"23350731": 65.31, "23361594": 57.71}
reg = json.load(open(REG)) if os.path.exists(REG) else {}
def save(): json.dump(reg, open(REG, "w"), indent=1)
note = "ERA 1053458 UHC W2348427 PR26/PR27 repeat - Medicare cost-share, no supplement in force on DOS - run %s" % STAMP
tot = {"moved": 0.0, "woins": 0.0, "wocltreq": 0.0, "lines": 0}; faults = 0
for pid, cids in LINES.items():
    root = txh.fetch(pid)
    for cid in cids:
        if reg.get(cid, {}).get("done"): continue
        ch = next((c for v in {payreasons.num(c.get("visit")) for c in root.iter("charge")} for c in payreasons.visit_state(pid, v, root) if c["cid"] == cid), None)
        if not ch: reg[cid] = {"pid": pid, "outcome": "charge not found live"}; save(); continue
        r = {"pid": pid, "visit": None, "cpt": ch["cpt"], "dos": ch["dos"], "pat_before": ch["patbalance"], "ins_before": ch["insbalance"], "steps": []}
        pat, ins = ch["patbalance"], ch["insbalance"]
        if pat > 0.005:
            if LIVE:
                m = move_to_ins.move(cid, rebill=False); r["steps"].append(["move_to_ins", str(m)[:120]]); time.sleep(0.4)
            else: r["steps"].append(["move_to_ins", "DRY %.2f patient -> insurance" % pat])
            tot["moved"] += pat
        total = round(pat + ins, 2)
        woins = WOINS_FIRST.get(cid, 0.0)
        if woins > 0:
            if LIVE:
                ok, msg = manual_post.post(cid, "FLO02", 0.0, woins, "WOINS", "PAYREASON1108", None, "Medicare contractual never adjusted - " + note); r["steps"].append(["WOINS %.2f" % woins, ok, str(msg)[:120]]); faults += 0 if ok else 1; time.sleep(0.4)
            else: r["steps"].append(["WOINS", "DRY %.2f" % woins])
            tot["woins"] += woins
        cost = round(total - woins, 2)
        if cost > 0.005:
            if LIVE:
                ok, msg = manual_post.post(cid, "FLO02", 0.0, cost, "WOCLTREQ", "ERA1053458", None, note); r["steps"].append(["WOCLTREQ %.2f" % cost, ok, str(msg)[:120]]); faults += 0 if ok else 1; time.sleep(0.4)
            else: r["steps"].append(["WOCLTREQ", "DRY %.2f" % cost])
            tot["wocltreq"] += cost
        if LIVE:
            root = txh.fetch(pid); after = next((c for v in {payreasons.num(c.get("visit")) for c in root.iter("charge")} for c in payreasons.visit_state(pid, v, root) if c["cid"] == cid), {})
            r["pat_after"] = after.get("patbalance"); r["ins_after"] = after.get("insbalance")
            r["done"] = all(s[1] is True for s in r["steps"] if s[0].startswith("WO")) and (after.get("patbalance", 1) or 0) < 0.005 and (after.get("insbalance", 1) or 0) < 0.005
        else: r["done"] = False
        tot["lines"] += 1; reg[cid] = r; save()
        print(cid, pid, ch["cpt"], ch["dos"], "pat %.2f ins %.2f ->" % (pat, ins), r["steps"], "after pat %s ins %s" % (r.get("pat_after"), r.get("ins_after")) if LIVE else "")
        if faults >= 3: print("STOP: 3 consecutive addpayments faults"); break
    if faults >= 3: break
print("TOTALS", json.dumps(tot), "live" if LIVE else "DRY")
