# PLAIN ENGLISH (ERA denial lines, UHC check 1052824 / W0299825, run 2026-09-24T0110Z). The Post button posted the 24 paid claims; the
#   17 $0 claims are worked here by the standing rules:
#   CO-B9 hospice (pat17473477 v19452587; pat17477227 v19449802 + v19450279): William 9/20 = GV + rebill to the MEDICARE sequence - both
#     charts carried only the UHC plan, so the Medicare plan is added first from Stedi's MBI lookup (MBI + Part A/B dates), GV (mcode713) on
#     every live charge (full-visit echo), visit insorder -> the new Medicare sequence, frequency 1 + chargerebill. Both patients are deceased
#     (9/15 and 8/1/2026 per CMS) but every DOS here is BEFORE the date of death - the deceased guard runs on each visit anyway.
#   PR-27 coverage terminated (wrong payer): pat17476042 + pat17470802 = straight Medicare ACTIVE on AMD's 271 (UHC INACTIVE) -> UHC plan
#     end-dated the day before the first denied DOS, visit insorder -> Medicare, freq-1 rebill; pat24853 = Humana MA ACTIVE (Medicare's 271
#     names Emphesys/Humana as primary) -> visit insorder 1,3 (the chart order), freq-1 rebill to Humana seq 1; pat17476094 / pat17473422 /
#     pat17471174 / pat17473065 already re-routed and paid by Medicare or Humana - nothing to rebill (recorded).
#   CO-29 untimely (pat12181899 v19420347, 10/14/2025 first billed 9/10/2026, UHC Group MA = the primary per both 271s): WOLATE through the
#     ERA-linked payreasons.post_line (reason codes kept); the chart's patient order is set to the MA plan (seq 3) - Medicare's 271 says the MA plan is primary.
# Never touches: paid claims, patient balances, any visit after a date of death. Register registers/uhc_1052824_<stamp>.json. --dry first.
import amd, resave, payreasons, add_ins, ins_update, move_to_ins, freq1_visit, gv_rebill, deceased_guard, elig_amd, json, re, sys, time
import xml.etree.ElementTree as ET
DRY = "--dry" in sys.argv; STAMP = "2026-09-24T0110Z"; CID = "1052824"
amd.login_cached()
chk = [c for c in json.load(open("era_checks_before_%s.json" % STAMP)) if str(c["id"]) == CID][0]
det = {str(v["visitid"]): v for v in json.load(open("era_details/%s.json" % CID))["eracheckdetails"]}
reg = {"stamp": STAMP, "checkid": CID, "actions": []}
def L(m): print(m, flush=True)
def R(**k): reg["actions"].append(k); L(json.dumps(k)[:400])
def live(vid, pid):
    import txh
    root = txh.fetch_visit(pid, vid); out = []
    for ch in root.iter("charge"):
        if ch.get("visit") != vid or ch.get("void") == "1" or (ch.get("fee") or "").startswith("-"): continue
        out.append({"cid": ch.get("id"), "cpt": ch.get("proccode"), "insbal": ch.get("insbal"), "patbal": ch.get("patbal"), "carrier": ch.get("carrier"), "dos": ch.get("dos") or ch.get("begindate"),
                    "pays": [(p.get("id"), p.get("amount"), p.get("checknumber")) for p in ch.iter("payment") if p.get("void") != "1" and float(p.get("amount") or 0) != 0]})
    return out
def guard(pid, vid, chs, carrier):
    for c in chs:
        dos = c["dos"] or ""; dos_iso = "%s-%s-%s" % (dos[6:10], dos[0:2], dos[3:5]) if "/" in dos else dos[:10]
        blocked, why = deceased_guard.check(pid, dos_iso, carrier, c["cpt"], allow_lookup=not DRY)
        if blocked: return True, why
    return False, "clear"
def reroute(pid, vid, insorder, seq, label):
    chs = live(vid, pid)
    if not chs: R(visit=vid, pid=pid, step=label, outcome="no live charge"); return
    if any(c["pays"] for c in chs): R(visit=vid, pid=pid, step=label, outcome="payment already posted - not rebilled", charges=chs); return
    b, why = guard(pid, vid, chs, "FLO02" if str(seq) != "1" or pid != "24853" else "HUM01")
    if b: R(visit=vid, pid=pid, step=label, outcome="DECEASED GUARD BLOCK", why=why); return
    cid = chs[0]["cid"]
    if DRY: R(visit=vid, pid=pid, step=label, outcome="DRY would set insorder %s + freq1 seq %s" % (insorder, seq), charges=chs); return
    f = freq1_visit.run(vid, cid, seq); time.sleep(0.6)
    if str(f).startswith("FAULT"): R(visit=vid, pid=pid, step=label, outcome="FAULT freq1", resp=str(f)[:200]); return
    m = move_to_ins.move(cid, seq=insorder); time.sleep(0.5)
    if str(m).startswith("FAULT"): R(visit=vid, pid=pid, step=label, outcome="FAULT insorder", resp=str(m)[:200], freq1=str(f)[:120]); return
    R(visit=vid, pid=pid, step=label, outcome="freq1 %s; insorder %s set (%s)" % (f, insorder, str(m)[:100]), charges=chs)
def gv_and_bill(pid, vid, seq, label):
    chs = live(vid, pid)
    if not chs: R(visit=vid, pid=pid, step=label, outcome="no live charge"); return
    if any(c["pays"] for c in chs): R(visit=vid, pid=pid, step=label, outcome="payment posted - not rebilled", charges=chs); return
    b, why = guard(pid, vid, chs, "FLO02")
    if b: R(visit=vid, pid=pid, step=label, outcome="DECEASED GUARD BLOCK", why=why); return
    cid = chs[0]["cid"]
    if DRY: R(visit=vid, pid=pid, step=label, outcome="DRY would add GV, insorder %s, freq1 seq %s" % (seq, seq), charges=chs); return
    g = gv_rebill.add_gv(cid); time.sleep(0.6)
    if str(g).startswith("FAULT"): R(visit=vid, pid=pid, step=label, outcome="FAULT GV", resp=str(g)[:200]); return
    f = freq1_visit.run(vid, cid, seq); time.sleep(0.6)
    if str(f).startswith("FAULT"): R(visit=vid, pid=pid, step=label, outcome="FAULT freq1", resp=str(f)[:200], gv=str(g)[:120]); return
    m = move_to_ins.move(cid, seq=str(seq)); time.sleep(0.5)
    if str(m).startswith("FAULT"): R(visit=vid, pid=pid, step=label, outcome="FAULT insorder", resp=str(m)[:200], gv=str(g)[:120]); return
    R(visit=vid, pid=pid, step=label, outcome="GV added; freq1 %s; insorder %s set (%s)" % (f, seq, str(m)[:100]), gv=str(g)[:120], charges=chs)
def plan_ids(pid):
    a, pl = elig_amd.plans(pid); return {p.get("carrier") + "#" + p.get("sequence", ""): p for p in pl}, pl
def add_medicare(pid, mbi, begin):
    a, pl = elig_amd.plans(pid)
    med = [p for p in pl if p.get("carrier") == "car6085" and not p.get("enddate")]
    if med: R(pid=pid, step="add Medicare", outcome="already on chart seq %s" % med[0]["sequence"]); return med[0]["sequence"]
    if DRY: R(pid=pid, step="add Medicare", outcome="DRY would add FLO02 car6085 %s begin %s" % (mbi, begin)); return "9"
    insid, seq = add_ins.add(pid, "car6085", mbi, begin, "1")
    R(pid=pid, step="add Medicare", outcome="added %s seq %s" % (insid, seq), mbi=mbi, begin=begin)
    return seq if insid else None
# 1. CO-29 untimely -> WOLATE via the ERA-linked line (pat12181899 v19420347)
v = det["19420347"]; ch = v["charges"][0]; cid = str(ch["chargedetailid"])
rt = ET.fromstring(resave.detail(cid)); c = [x for x in rt.iter("charge") if x.get("id") == "charge" + cid][0]; bal = float(c.get("insbalance") or 0)
if bal <= 0: R(visit="19420347", pid="12181899", step="CO-29", outcome="balance already 0")
elif DRY: R(visit="19420347", pid="12181899", step="CO-29", outcome="DRY would post $0 + WOLATE %.2f (ERA-linked, reason CO-29)" % bal)
else:
    ok, payid, head = payreasons.post_line("12181899", "19420347", chk, v, cid, ch, pay=0.0, wo=bal, wocode="WOLATE"); time.sleep(0.6)
    rt2 = ET.fromstring(resave.detail(cid)); c2 = [x for x in rt2.iter("charge") if x.get("id") == "charge" + cid][0]
    R(visit="19420347", pid="12181899", step="CO-29", outcome=("posted $0 + WOLATE %.2f" % bal) if ok else "FAULT", paymentid=payid, insbalance_after=c2.get("insbalance"), patbalance_after=c2.get("patbalance"), resp=head[:120])
# patient order -> the UHC Group Medicare Advantage plan (seq 3) - both 271s name it primary
pm, pl = plan_ids("12181899"); p3 = pm.get("car6404#3")
if p3 and not DRY:
    ok, msg = ins_update.update("12181899", p3["id"], sequence="3"); R(pid="12181899", step="patient insorder -> 3 (UHC MA primary)", outcome="ok" if ok else "FAIL", resp=msg[:120])
else: R(pid="12181899", step="patient insorder -> 3", outcome="DRY" if DRY else "seq-3 plan not found")
# 2. PR-27 -> straight Medicare (pat17476042 HOLLIS, pat17470802 PEMBROKE)
for pid, first_dos, visits in (("17476042", "08/19/2026", ["19452859", "19452616"]), ("17470802", "08/19/2026", ["19452694", "19452832"])):
    pm, pl = plan_ids(pid); uhc = [p for p in pl if p.get("carrier") == "car6404"]; med = [p for p in pl if p.get("carrier") == "car6085" and not p.get("enddate")]
    if not med: R(pid=pid, step="PR-27", outcome="no live Medicare plan - HOLD"); continue
    mseq = med[0]["sequence"]
    for u in uhc:
        if u.get("enddate") == first_dos: continue
        if DRY: R(pid=pid, step="end-date UHC", outcome="DRY would set enddate %s (was %s)" % (first_dos, u.get("enddate"))); continue
        ok, msg = ins_update.update(pid, u["id"], enddate=first_dos); R(pid=pid, step="end-date UHC %s" % u["id"], outcome="ok" if ok else "FAIL", enddate=first_dos, was=u.get("enddate"), resp=msg[:120])
    if pid == "17470802" and not DRY:
        ok, msg = ins_update.update(pid, med[0]["id"], sequence=mseq); R(pid=pid, step="patient insorder -> %s (Medicare only)" % mseq, outcome="ok" if ok else "FAIL", resp=msg[:120])
    for vid in visits: reroute(pid, vid, mseq, mseq, "PR-27 -> Medicare")
# 3. PR-27 -> Humana MA primary (pat24853 MARCHBANK, 5 hospital 99233s)
for vid in ("19452240", "19452244", "19452954", "19452815", "19452802"): reroute("24853", vid, "1,3", "1", "PR-27 -> Humana MA seq 1")
# 4. already settled PR-27 lines (recorded only)
for vid, pid, why in (("19452631", "17476094", "already re-routed to Medicare and paid (819814877)"), ("19452628", "17473422", "already re-routed to Medicare and paid (819814877)"), ("19452607", "17471174", "Medicare paid; 99489 voided"), ("19452664", "17473065", "Humana paid 199572529260909, balance 0")):
    R(visit=vid, pid=pid, step="PR-27", outcome="nothing to rebill - " + why)
# 5. CO-B9 hospice -> GV + Medicare (pat17473477 SMYTHE, pat17477227 CANTRELL)
_MBI = json.load(open("inbox/mbi_0110.json"))  # MBIs live in the workspace inbox only (PHI), never in the mirrored helper
for pid, visits in (("17473477", ["19452587"]), ("17477227", ["19449802", "19450279"])):
    mbi, begin = _MBI[pid]
    seq = add_medicare(pid, mbi, begin)
    if not seq: R(pid=pid, step="CO-B9", outcome="Medicare plan add failed - HOLD"); continue
    for vid in visits: gv_and_bill(pid, vid, seq, "CO-B9 hospice -> GV + Medicare")
json.dump(reg, open("registers/uhc_1052824_%s%s.json" % (STAMP, "_dry" if DRY else ""), "w"), indent=1)
L("=== %s done: %d actions" % ("DRY" if DRY else "LIVE", len(reg["actions"])))
