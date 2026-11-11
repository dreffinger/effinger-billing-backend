#!/usr/bin/env python3
# PLAIN ENGLISH (Exclusions column by hand, 1:39 PM ET 11/11 columns run, fired 18:39Z)
# Decides: nothing new - the standing exclusion rules on the nine rows getclaimexclusionclaimruns lists (William's own EFFINGER-user
#   claim runs 1700332/333/347/363/372 - the engine's scan reads getclaimrunstatus and never saw them; AET12 1700294 stays held):
#   A. chart 17477498 run 1700332 (Florida Blue, ALF CCM 10/22/2026 POS 13): 'ACUTE ISCHEMIC STROKE ... OUTPATIENT' -> I63.9 -> I69.30
#      (recode.swap_dx: full echo, both charges) + frequency-1 rebill seq 1, complete.
#   B. chart 12232512 run 1700333 (Humana 'ENTITY NOT FOUND: PATIENT' x2): the Medicare 271 names the D-SNP CARE IMPROVEMENT PLUS SOUTH
#      CENTRAL (UHC Dual Complete = the chart's UNI20 seq 4, ACTIVE) and the Medicaid 271 says Humana is the SMMC LONG-TERM CARE plan (custodial,
#      not the physician payer); the chart default order is already 4,3 - the two visits went out insorder 3. freq1_visit.reroute to 4,3 seq 4, complete.
#   C. chart 17478213 run 1700347 (Sunshine 'INVALID MBR DOB' x3): every visit is since PAID by Sunshine (11/07 + 11/11 checks, insurance balance $0)
#      -> complete (the $0-balance rule), no rebill.
#   D. chart 17470950 run 1700363 (AARP PSBR0130 'INVALID PAYER RESP SEQ NUM CODE P'): the 11/07 run sent the Medigap as primary; the visit was
#      re-sent to Medicare (seq 1, FLO02, 11/08, frequency 1) the day after -> complete, no rebill (AARP gets the crossover).
#   E. chart 17469028 run 1700372 (Florida Blue PREF0283 on claim B, the Medigap secondary after Medicare paid 11/10): the crossover-wait rule
#      (10/25, 11/9 precedent) -> complete, no rebill.
# Rules it uses: one AMD login; re-list each run right before acting (rule 6, 10/14); one rebill per visit; never rebill a visit with a
#   payment; hideexclusions hide=-1 with visit id + claimid; register registers/excl_hand_2026-11-11T1839Z_actions[_dry].json.
# Usage: python3 excl_1111_1839.py [--live]
import sys, re, json, time, amd, recode, freq1_visit, txh
LIVE = "--live" in sys.argv; STAMP = "2026-11-11T1839Z"
out = {"stamp": STAMP, "live": LIVE, "steps": []}
def step(k, v): out["steps"].append({k: v}); print(k, "->", str(v)[:300])
amd.login_cached()
def listed(rid):
    x = amd.post(amd.msg("getclaimexclusioncharges", "claimsreports", {"claimrunid": rid, "clearinghouse": "1", "payer": "1", "nocookie": "1"}))
    return {m.group(1): m.group(2) for m in re.finditer(r'<visit [^>]*\bid="(\d+)" claimid="([^"]+)"', x)}
def complete(rid, pairs):
    if not pairs: return "nothing listed"
    if not LIVE: return "DRY complete %s" % pairs
    r = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": rid, "hide": "-1", "nocookie": "1"},
        "<visitlist>%s</visitlist>" % "".join('<visit id="%s" claimid="%s"/>' % (v, c) for v, c in pairs)))
    time.sleep(0.4); return "ok" if "Fault" not in r else "FAULT " + re.sub(r"\s+", " ", r[:200])
def paid(pid, vid):
    for c in txh.fetch(pid).iter("charge"):
        if c.attrib.get("visit") == vid and [p for p in c.iter("payment") if p.get("void") not in ("1","true")]: return True
    return False
# A
l = listed("1700332"); step("A_listed", l)
if "19458935" in l:
    if paid("17477498", "19458935"): step("A", "SKIP payment on the visit")
    elif LIVE:
        step("A_swap", recode.swap_dx("23371199", "dcode1034545006", "dcode1034545425", 1)); time.sleep(0.5)
        step("A_complete", complete("1700332", [("19458935", l["19458935"])]))
    else: step("A", "DRY swap_dx 23371199 I63.9->I69.30 + freq1 seq 1; complete")
# B
l = listed("1700333"); step("B_listed", l)
for vid, cid in (("19458851", "23371076"), ("19459007", "23371341")):
    if vid not in l: continue
    if paid("12232512", vid): step("B_%s" % vid, "SKIP payment on the visit"); continue
    r = freq1_visit.reroute(vid, cid, "4,3", seq=4, dry=not LIVE); step("B_%s" % vid, r)
    if LIVE and "NOT rebilled" not in r and "FAULT" not in r: step("B_complete_%s" % vid, complete("1700333", [(vid, l[vid])]))
    time.sleep(0.5)
# C
l = listed("1700347"); step("C_listed", l)
zero = []
for c in txh.fetch("17478213").iter("charge"):
    a = c.attrib
    if a.get("visit") in l and float(a.get("insbal") or 0) == 0 and float(a.get("paid") or 0) > 0: zero.append(a.get("visit"))
pairs = [(v, l[v]) for v in sorted(set(zero))]; step("C_zero_balance_paid", pairs)
step("C_complete", complete("1700347", pairs))
# D
l = listed("1700363"); step("D_listed", l)
at_medicare = any(c.attrib.get("visit") == "19460408" and c.attrib.get("carrier") == "FLO02" and c.attrib.get("billdate") for c in txh.fetch("17470950").iter("charge"))
step("D_at_medicare", at_medicare)
if "19460408" in l and at_medicare: step("D_complete", complete("1700363", [("19460408", l["19460408"])]))
# E
l = listed("1700372"); step("E_listed", l)
medicare_paid = any(c.attrib.get("visit") == "19459142" and any(p.get("carrier") == "FLO02" for p in c.iter("payment")) for c in txh.fetch("17469028").iter("charge"))
step("E_medicare_paid", medicare_paid)
if "19459142" in l and medicare_paid: step("E_complete", complete("1700372", [("19459142", l["19459142"])]))
# after
r = amd.post(amd.msg("getclaimexclusionclaimruns", "claimsreports", {"nocookie": "1"}))
m = re.search(r'<Results[^>]*>', r); step("after_runs", (m.group(0) if m else "") + " " + str(re.findall(r'<claimrun [^>]*\bid="(\d+)"[^>]*claimcount="(\d+)"', r)))
o = amd.post(amd.msg("getclaimcenteroverview", "claimsreports", {"nocookie": "1"})); step("overview", re.sub(r"\s+", " ", o)[:300])
json.dump(out, open("registers/excl_hand_%s_actions%s.json" % (STAMP, "" if LIVE else "_dry"), "w"), indent=1); print("register written")
