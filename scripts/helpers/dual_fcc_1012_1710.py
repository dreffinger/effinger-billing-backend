# PLAIN ENGLISH (dual chart 17472124, follow-up of dual_fcc_1011.py - run 2026-10-12T1710Z, ehpa cloud copy)
# William's PCC admission record (board note 10/11/2026 03:34Z): Florida Community Care (Medicaid MMA) carries the Medicare B coinsurance.
# The 10/11 0510Z run added FCC (FLO99 car42008, seq 4), end-dated the guessed AARP supplement (ins9520542) and re-routed the four
# June-July visits. Two later visits still sit at AAR01 with their Medicare coinsurance open: the 9/20/2026 CCM (v19455794 c23367244,
# 16.14 after Medicare paid 63.28 + WOINS 126.58 on 10/7) and the 9/24/2026 99309 (v19456179 c23367803, 16.93 after Medicare paid
# 66.36 + WOINS 57.71 on 10/9) - AARP rejected the latter on claim run 1700286 ('SUBSCRIBER AND SUBSCRIBER ID NOT FOUND', claim 19456179B).
# Decides: a coinsurance sitting on the PATIENT balance (v19455794) is moved back first (move_to_ins.move, no rebill - never bill a dual); then for each of the two visits ONE re-route (freq1_visit.reroute vid cid "2,4" 4 = visit order Medicare / FCC + one frequency-1
#   secondary claim to FCC, William's 10/6 one-rebill rule), then the exclusion row 19456179B on run 1700286 is completed (hideexclusions)
#   because the visit was re-sent this run. Dry mode reads the live charge (carrier, balances) and prints the plan.
# Never touches: payments, write-offs, plans, the patient order (already 2,4), any other chart or visit.
#   python3 dual_fcc_1012_1710.py          # dry
#   python3 dual_fcc_1012_1710.py --live   # register registers/dual_fcc_2026-10-12T1710Z.json
import amd, freq1_visit, move_to_ins, txh, json, sys, time, re
LIVE = "--live" in sys.argv; S = "2026-10-12T1710Z"; PID = "17472124"; ORDER = "2,4"; SEQ = 4
VISITS = [("19455794", "23367244"), ("19456179", "23367803")]
EXCL = [("1700286", "19456179", "19456179B")]
amd.login_cached()
reg = {"stamp": S, "live": LIVE, "pid": PID, "steps": []}
def L(m): print(m, flush=True); reg["steps"].append(m)
def live(vid, cid):
    root = txh.fetch_visit(PID, vid)
    for c in root.iter("charge"):
        if (c.get("id") or "").replace("charge", "") == cid and c.get("void") != "1":
            return {"cpt": c.get("proccode"), "dos": c.get("dos"), "carrier": c.get("carrier"), "billdate": c.get("billdate"), "insbal": c.get("insbal"), "patbal": c.get("patbal")}
    return None
for vid, cid in VISITS:
    s = live(vid, cid); L("v%s c%s live: %s" % (vid, cid, s))
    if not s: L("  skip - charge not live"); continue
    if float(s["insbal"] or 0) <= 0 and float(s["patbal"] or 0) <= 0: L("  skip - nothing open"); continue
    if s["carrier"] == "FLO99": L("  skip - already at FCC"); continue
    if float(s["patbal"] or 0) > 0:   # a dual's coinsurance on the PATIENT balance (never bill a dual): move it back first, no rebill
        if LIVE: mv = move_to_ins.move(cid, rebill=False); L("  move back v%s c%s: %s" % (vid, cid, mv)); time.sleep(0.6)
        else: L("  DRY would move %s patient balance back to insurance first (no rebill)" % s["patbal"])
    L("reroute v%s c%s -> %s seq %s: %s" % (vid, cid, ORDER, SEQ, freq1_visit.reroute(vid, cid, ORDER, SEQ, dry=not LIVE)))
    time.sleep(0.5)
for run, vid, claim in EXCL:
    if LIVE:
        r = amd.post(amd.msg("hideexclusions", "claimsreports", {"nocookie": "1", "claimrunid": run, "hide": "-1"}, '<visitlist><visit id="%s" claimid="%s"/></visitlist>' % (vid, claim)))
        L("complete exclusion run %s %s: ok=%s %s" % (run, claim, "Fault" not in r, re.sub(r"\s+", " ", r[:160])))
    else: L("DRY complete exclusion run %s visit %s claim %s" % (run, vid, claim))
json.dump(reg, open("registers/dual_fcc_%s%s.json" % (S, "" if LIVE else "_dry"), "w"), indent=1)
