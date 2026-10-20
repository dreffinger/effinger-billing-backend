# PLAIN ENGLISH (settle the three $0 PR-27 'coverage terminated' secondary answers on UHC remit 1053227 - run 2026-10-20T2110Z)
# Decides: by William's standing rules only. (1) chart 17473661 v19455470 99309 9/18/2026 charge 23366761: Medicare paid 66.36,
#   the 16.93 coinsurance went to UHC (chart seq 1, plan ins9514351) which answered PR-27 - UHC 87726 at the DOS = INACTIVE,
#   Stedi discovery finds no Medigap / Medicaid (only a Part D plan) -> no supplement in force on the DOS: a wrong-payer
#   $0 never stays on the patient (move it back to insurance with no rebill if the Post button moved it) and the Medicare
#   cost-share is written off WOCLTREQ (William 10/13: nothing stays on the patient balance); the dead UHC plan is end-dated
#   the day before the first rejected DOS (09/17/2026) and the patient order re-asserted Medicare-only ('2').
#   (2) chart 17470802 v19452694 99497 charge 23363074 (13.35 open at FLO02, Medicaid FFS crossover cluster held for William):
#   UHC's PR-27 is the dead plan's stale answer - only a patient-balance move-back (no rebill) if the Post button moved it.
#   (3) chart 17470802 v19452372: already $0 (WOCLTREQ 10/13) - read only.
# Rules it uses: --dry (default) reads and prints the plan; --live writes through move_to_ins.move (no seq, no rebill),
#   manual_post.post (pay 0.0 + WOCLTREQ, note), ins_update.update (enddate=, then sequence=). Register
#   registers/uhc_pr27_1053227_2026-10-20T2110Z.json. Never touches: payments, rebills, any other chart.
import sys, json, re, time, resave, move_to_ins, manual_post, ins_update
import xml.etree.ElementTree as ET
LIVE = "--live" in sys.argv; S = "2026-10-20T2110Z"; REG = {"stamp": S, "live": LIVE, "steps": []}
def log(*a):
    print(*a, flush=True); REG["steps"].append(" ".join(str(x) for x in a))
def bal(cid):
    rt = ET.fromstring(resave.detail(cid)); c = [x for x in rt.iter("charge") if x.get("id") == "charge" + cid][0]
    return float(c.get("insbalance") or 0), float(c.get("patbalance") or 0), c.get("carrier") or c.get("carriercode")
for pid, vid, cid, cpt, settle in (("17473661", "19455470", "23366761", "99309", True), ("17470802", "19452694", "23363074", "99497", False), ("17470802", "19452372", "23362582", "99487", False)):
    ins, pat, car = bal(cid); log("chart", pid, "v" + vid, "c" + cid, cpt, "live ins %.2f pat %.2f carrier %s" % (ins, pat, car))
    if pat > 0:
        log("  patient balance %.2f -> move back to insurance, no rebill:" % pat, move_to_ins.move(cid, None, dry=not LIVE, rebill=False))
        if LIVE: ins, pat, car = bal(cid); log("  after move: ins %.2f pat %.2f" % (ins, pat))
    if settle and ins > 0:
        ok, msg = manual_post.post(cid, "FLO02", 0.0, ins, "WOCLTREQ", "PAYREASON" + S, None, "UHC 1053227 PR-27 coverage terminated; UHC 87726 inactive at DOS, discovery no supplement - Medicare cost-share WOCLTREQ (William 10/13) run " + S, dry=not LIVE)
        log("  WOCLTREQ %.2f ->" % ins, ok, msg)
        if LIVE: ins, pat, car = bal(cid); log("  after write-off: ins %.2f pat %.2f" % (ins, pat))
# dead UHC plan on chart 17473661
raw, plans, order = ins_update._plans("17473661"); p = plans.get("ins9514351", {})
log("chart 17473661 patient insorder", order, "UHC plan ins9514351 begin", p.get("begindate"), "end", repr(p.get("enddate")))
if p and not (p.get("enddate") or "").strip():
    if LIVE:
        log("  end-date UHC 09/17/2026:", ins_update.update("17473661", "ins9514351", enddate="09/17/2026"))
        log("  patient order -> '2' (Medicare only):", ins_update.update("17473661", "ins9520551", sequence="2"))
        raw, plans, order = ins_update._plans("17473661"); log("  readback: insorder", order, "UHC enddate", plans.get("ins9514351", {}).get("enddate"))
    else: log("  DRY: would end-date ins9514351 09/17/2026 and set the patient order to '2'")
json.dump(REG, open("registers/uhc_pr27_1053227_%s%s.json" % (S, "" if LIVE else "_dry"), "w"), indent=1)
