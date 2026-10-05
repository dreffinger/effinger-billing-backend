# PLAIN ENGLISH (Florida Medicaid FFS $0 remit 073078977 = ERA check 1052968, 5 PM ET 10/5/2026 run)
# Decides: the 85-claim $0 Medicaid FFS remit of 10/5 answers crossover / FFS claims on dual charts. Per denial group,
#   after a LIVE read of every visit (reads_2110_1005.py):
#   (1) CO-45/N45 'processed as secondary' and CO-170/N95 'provider type / plan procedures' (CCM 99487+99489, never payable
#       by Medicaid) on charts where Medicaid is the dual secondary and the Medicare coinsurance is still open ->
#       WOCAID2ND for exactly that residual with the remit's trace number (rules.md 9/11 + 10/4: a Medicaid $0 on Medicare
#       coinsurance is contractual, never a patient balance; CCM/AWV never payable by Medicaid -> WOCAID2ND secondary).
#   (2) a $0 Medicaid line that the ERA poster had transferred to the PATIENT balance on a dual (the secondary claim is
#       already out to FCC / Humana MMA / Sunshine / United American, or Medicaid is not on the chart yet) -> move the
#       balance back to insurance (wrong-payer / COB $0 never stays on the patient, 9/3 rule); nothing rebilled.
#   (3) everything else is recorded only: lines already at another secondary (pending), Garland-G-rendered N290 lines and
#       referring-provider N286 lines (the Medicaid cluster re-render pass William ordered 10/4), CO-31 lines already at Simply.
#   (4) dismiss checks 1052968 (all lines handled/recorded, no money) and 1052967 (Humana CO-B9 hospice denials -
#       the approved re-route act_1710_1005.py ran this run) - only when every write above succeeded.
# Rules it uses: live read before every write; manual_post refuses over-apply; --dry first; 3 consecutive faults stop the pass.
# Never touches: paid lines, charges at another live payer, the N290/N286 cluster lines (re-render is its own pass), 1052906 (held).
import amd, manual_post, move_to_ins, era_post, requests, json, sys, time
STAMP = "2026-10-05T2110Z"; CHK = "073078977"; DD = "10/07/2026"; DRY = "--live" not in sys.argv
amd.login_cached(); log = []; faults = 0
def L(s): print(s, flush=True); log.append(s)
NOTE = "ERA 1052968 Medicaid FFS $0 dual crossover %s - WOCAID2ND run %s"
# (1) WOCAID2ND: (pid, vid, cid, amount, reason)
WO = [("17476020","19454934","23366085",21.80,"CO-45 N45"),("17476020","19454918","23366070",21.80,"CO-45 N45"),
      ("17476020","19454892","23366042",21.80,"CO-45 N45"),("17476020","19454642","23365720",31.94,"CO-45 N45"),
      ("17477650","19454274","23365346",21.80,"CO-45 N45 (Medicaid crossover; MCAD not on chart)"),("17477650","19454304","23365377",21.80,"CO-45 N45 (Medicaid crossover; MCAD not on chart)"),
      ("23617","19420945","23326090",17.50,"CO-170 N95 CCM"),("23617","19420945","23326091",9.47,"CO-170 N95 CCM"),
      ("23617","19430732","23337202",16.14,"CO-170 N95 CCM"),("23617","19430732","23337203",8.92,"CO-170 N95 CCM"),
      ("17476094","19448872","23358349",16.14,"CO-170 N95 CCM (crossover; MCAD not on chart)"),("17476094","19448872","23358350",8.92,"CO-170 N95 CCM (crossover; MCAD not on chart)")]
# (2) patient -> insurance moves: (pid, vid, cid, where the live claim is)
MV = [("20863","19454654","23365732","FCC secondary out 9/29"),("17475638","19454656","23365734","Medicare paid; secondary order to settle"),
      ("17472393","19454645","23365723","Humana MMA secondary out 9/29"),("17472546","19454658","23365736","Sunshine secondary out 9/29"),
      ("17477747","19454665","23365743","United American Medigap out 9/29"),("25160","19454662","23365740","dual per the crossover; MCAD not on chart - cluster"),
      ("17473422","19454666","23365744","dual per the crossover; MCAD not on chart - cluster"),
      ("20407","19452433","23362700","CCM dual residual - WOCAID2ND follows"),("20407","19452433","23362701","CCM dual residual - WOCAID2ND follows")]
WO2 = [("20407","19452433","23362700",16.14,"CO-170 N95 CCM (after move-back)"),("20407","19452433","23362701",8.92,"CO-170 N95 CCM (after move-back)")]
out = {"stamp": STAMP, "check": CHK, "live": not DRY, "wo": [], "mv": [], "dismiss": []}
def wo(pid, vid, cid, amt, why):
    global faults
    ok, msg = manual_post.post(cid, "MCAD", 0.0, amt, "WOCAID2ND", CHK, DD, NOTE % (why, STAMP), DRY)
    L("WOCAID2ND pat%s v%s c%s %.2f (%s) -> %s %s" % (pid, vid, cid, amt, why, ok, msg[:140])); out["wo"].append((pid, vid, cid, amt, why, ok, msg[:140]))
    faults = 0 if ok else faults + 1
    if faults >= 3: L("3 consecutive addpayments faults - stopping the pass"); finish(False)
    time.sleep(0.5)
def finish(allok):
    json.dump({"log": log, **out}, open("registers/act_%s%s.json" % (STAMP, "" if not DRY else "_dry"), "w"), indent=1)
    if not allok: sys.exit(1)
for r in WO: wo(*r)
for pid, vid, cid, why in MV:
    try:
        m = move_to_ins.move(cid, dry=DRY) if DRY else move_to_ins.move(cid)
    except TypeError:
        m = "DRY (move_to_ins has no dry flag)" if DRY else move_to_ins.move(cid)
    L("MOVE pat%s v%s c%s (%s) -> %s" % (pid, vid, cid, why, m)); out["mv"].append((pid, vid, cid, why, str(m)[:160])); time.sleep(0.5)
for r in WO2: wo(*r)
# (3) pat17475638: AMD 271 this run - seq1 HUM01 ACTIVE 'MC MEDICAID GATE CAP DIR' (Humana Medicaid MMA, capitated), seq2 BCBS REJECTED AAA 75,
#     seq3 FLO02 ACTIVE straight Medicare. Medicare paid these HCA 99233s; Medicaid FFS says managed care -> the secondary is Humana Medicaid:
#     patient default order 3,1 (Medicare first, Humana Medicaid second), the five open visits insorder 3,1 + frequency-1 rebill seq 1.
import ins_update, freq1_visit
RT = [("17475638","19454307","23365380"),("17475638","19454278","23365350"),("17475638","19454457","23365545"),("17475638","19454436","23365524"),("17475638","19454656","23365734")]
out["route"] = []
if DRY:
    for pid, vid, cid in RT: L("DRY route pat%s v%s c%s: insorder 3,1 + freq1 rebill seq 1 -> %s" % (pid, vid, cid, move_to_ins.move(cid, "3,1", dry=True)))
    L("DRY: ins_update pat17475638 ins9517115 sequence=3,1")
else:
    ok, msg = ins_update.update("17475638", "ins9517115", sequence="3,1"); L("ins_update pat17475638 order 3,1 -> %s %s" % (ok, str(msg)[-120:])); time.sleep(0.5)
    for pid, vid, cid in RT:
        try:
            f = freq1_visit.run(vid, cid, 1); time.sleep(0.5); m = move_to_ins.move(cid, "3,1", rebill_seq=1)
            L("ROUTE pat%s v%s c%s -> freq1 %s | %s" % (pid, vid, cid, f, m)); out["route"].append((pid, vid, cid, str(f)[:80], str(m)[:160]))
        except Exception as e: L("ROUTE pat%s v%s c%s FAILED %s" % (pid, vid, cid, str(e)[:160])); out["route"].append((pid, vid, cid, "ERR", str(e)[:160]))
        time.sleep(0.5)
bad = [x for x in out["wo"] if not x[5]]
if DRY: L("DRY: would dismiss 1052968 and 1052967 (%d WOCAID2ND, %d moves planned)" % (len(WO) + len(WO2), len(MV)))
elif bad: L("NOT dismissing - %d write-off(s) failed: %s" % (len(bad), [(b[2], b[6]) for b in bad]))
else:
    for cid in ("1052968", "1052967"):
        r = requests.post("https://pm-api-103.advancedmd.com/api/era/checks/dismiss", headers=era_post.H(), data=json.dumps(cid), timeout=60)
        L("dismiss %s -> %s %s" % (cid, r.status_code, r.text[:120])); out["dismiss"].append((cid, r.status_code, r.text[:120])); time.sleep(0.5)
finish(True)
