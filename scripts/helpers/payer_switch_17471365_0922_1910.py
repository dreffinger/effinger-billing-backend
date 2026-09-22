# PLAIN ENGLISH (payer switch, 3pm ET 9/22/2026 run 2026-09-22T1910Z): claim run 1700216 rejected two Medicare-secondary residuals on
#   pat17471365 (99349 10/15/2025 $20.86 and 99487 11/15/2025 $25.90, both GV) at UNITED HEALTHCARE (UNI20, CPID 3429): 'SUBSCRIBER AND
#   SUBSCRIBER ID NOT FOUND' + 'MEMBER PICK REJECT'. Lookup order applied: AMD 271 on the seq-2 plan names 'AARP SUPPLEMENTAL PLANS INS BY
#   UNITEDHEALTHCARE'; Stedi AARP Medigap (36273) with the same member id = ACTIVE 'AARP MEDICARE SUPPLEMENT PLAN F' at the DOS; UHC 87726
#   answers nothing. So the seq-2 plan is a Medigap entered under the wrong UHC carrier.
# Decides: (1) add AAR01 (car6600) with the same member id, begin date = the UNI20 plan's, coverage 2, NO group number; (2) end-date the
#   UNI20 plan 10/14/2025 (the day before the first rejected DOS); (3) each visit: deceased guard, full-visit resave with insorder
#   '1,<AARP seq>' (move_to_ins.move - balances stay on insurance) then freq1_visit.run on the AARP sequence; (4) complete the two
#   exclusion rows on run 1700216 (hideexclusions). Never touches: payments, write-offs, the Medicare plan, other visits.
"""Usage: python3 payer_switch_17471365_0922_1910.py [--dry]"""
import amd, add_ins, ins_update, move_to_ins, freq1_visit, deceased_guard, resave, re, time, json, sys
DRY = "--dry" in sys.argv
PID = "17471365"; UNI = "ins9510649"; MEMBER = "04988775211"; STAMP = "2026-09-22T1910Z"
VISITS = [("19422334", "23327672", "19422334C"), ("19423579", "23329181", "19423579C")]
amd.login_cached()
out = {"stamp": STAMP, "pid": PID, "steps": []}
def L(m): print(m, flush=True); out["steps"].append(m)
def plans():
    t = amd.post(amd.msg("getdemographic", "demographics", {"patientid": PID, "nocookie": "1"}), timeout=60)
    ps = []
    for ip in re.finditer(r'<insplan [^>]*>', t):
        b = dict(re.findall(r'(\w+)="([^"]*)"', ip.group(0))); ps.append({k: b.get(k) for k in ("id", "sequence", "carrier", "subscribernum", "begindate", "enddate", "coverage", "grpnum")})
    return ps
before = plans(); L("plans before: %s" % before)
aarp = [p for p in before if p["carrier"] == "car6600" and p["subscribernum"] == MEMBER]
if DRY: L("DRY: would add AAR01 car6600 %s begin 05/03/2023 coverage 2, end-date %s 10/14/2025, resave insorder 1,<seq> + freq1 rebill x2, hideexclusions 1700216" % (MEMBER, UNI)); sys.exit()
if not aarp:
    r = add_ins.add(PID, "car6600", MEMBER, "05/03/2023", coverage="2"); L("add_ins AAR01 -> %s" % str(r)[:300]); time.sleep(0.8)
    aarp = [p for p in plans() if p["carrier"] == "car6600" and p["subscribernum"] == MEMBER]
if not aarp: L("AAR01 plan not found after add - STOP"); json.dump(out, open("registers/payer_switch_%s_%s.json" % (PID, STAMP), "w"), indent=1); sys.exit(1)
seq = aarp[0]["sequence"]; L("AAR01 plan %s sequence %s grpnum=%r" % (aarp[0]["id"], seq, aarp[0]["grpnum"]))
r = ins_update.update(PID, UNI, enddate="10/14/2025"); L("end-date UNI20 %s 10/14/2025 -> %s" % (UNI, str(r)[:200]))
for vid, cid, claim in VISITS:
    vis, pat, allc = resave.visit_charges(cid); dos = vis.get("date")
    blocked, why = deceased_guard.check(PID, dos, "AAR01", None, allow_lookup=False)
    if blocked: L("v%s DECEASED GUARD BLOCK %s" % (vid, why)); continue
    r = move_to_ins.move(cid, seq="1,%s" % seq, rebill_seq=int(seq)); L("v%s move/insorder 1,%s -> %s" % (vid, seq, r))
    r = freq1_visit.run(vid, cid, int(seq)); L("v%s %s" % (vid, r)); time.sleep(0.5)
    x = resave.detail(cid); m = re.search(r'<charge [^>]*id="charge%s"[^>]*>' % cid, x); v2 = re.search(r'<visit [^>]*>', x).group(0)
    L("v%s readback insorder=%s insbilled=%s insbalance=%s patbalance=%s" % (vid, re.search(r'insorder="([^"]*)"', v2).group(1), re.search(r'insbilled="([^"]*)"', m.group(0)).group(1), re.search(r'insbalance="([^"]*)"', m.group(0)).group(1), re.search(r'patbalance="([^"]*)"', m.group(0)).group(1)))
lst = "".join('<visit id="%s" claimid="%s"/>' % (v, c) for v, _, c in VISITS)
r = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": "1700216", "hide": "-1", "nocookie": "1"}, "<visitlist>%s</visitlist>" % lst))
L("hideexclusions 1700216 x2 -> %s" % ("ok" if "Fault" not in r else re.sub(r"\s+", " ", r[:200])))
time.sleep(2)
t = amd.post(amd.msg("getclaimexclusioncharges", "claimsreports", {"claimrunid": "1700216", "clearinghouse": "1", "payer": "1", "nocookie": "1"}), timeout=120)
L("exclusion rows left on 1700216: %d" % len(re.findall(r'<visit ', t)))
L("plans after: %s" % plans())
json.dump(out, open("registers/payer_switch_%s_%s.json" % (PID, STAMP), "w"), indent=1)
