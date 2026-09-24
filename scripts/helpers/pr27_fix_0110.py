# PLAIN ENGLISH (run 2026-09-24T0110Z, correction after era_clear): era_clear's 'Process Accepted $0.00' post of the UHC PR-27 lines (check W0299825)
#   moved the denied charges to the PATIENT balance on the visits this run had just re-routed to Medicare (pat17476042 x2, pat17470802 x2) and on two
#   Medicare-paid CCM visits (pat17476094 v19452631, pat17473422 v19452628). William's rule: wrong-payer denials never stay on the patient balance.
# Decides: (1) move every such patient balance back to insurance (move_to_ins.move, full-visit echo); on the four re-routed visits re-assert insorder 2 and
#   rebill Medicare seq 2 in the same call; (2) on the two Medicare-paid visits the balance back on FLO02 is Medicare's contractual never adjusted - read
#   Medicare's own remit lines for 819814877 (dismissed ERA checks, restore -> checkdetails -> re-dismiss) and post the $0 + WOINS line ERA-linked with
#   Medicare's CO-45/CO-253/PR-2 reasons (payreasons.post_line) so AMD moves only the PR share to the patient; (3) hospice visits: re-check the rebill.
# Never touches: paid lines, any other chart. Register registers/pr27_fix_2026-09-24T0110Z.json. --dry = read only.
import amd, resave, move_to_ins, freq1_visit, payreasons, txh, json, re, sys, time
import xml.etree.ElementTree as ET
DRY = "--dry" in sys.argv; STAMP = "2026-09-24T0110Z"
amd.login_cached()
reg = {"stamp": STAMP, "actions": []}
def L(m): print(m, flush=True)
def R(**k): reg["actions"].append(k); L(json.dumps(k, default=str)[:420])
def state(pid, vid):
    root = txh.fetch_visit(pid, vid); out = []
    for ch in root.iter("charge"):
        if ch.get("visit") != vid or ch.get("void") == "1" or (ch.get("fee") or "").startswith("-"): continue
        out.append((ch.get("id"), ch.get("proccode"), ch.get("insbal"), ch.get("patbal")))
    return out
# (1) re-routed visits: move back + insorder 2 + rebill seq 2
for pid, vids in (("17476042", ["19452859", "19452616"]), ("17470802", ["19452694", "19452832"])):
    for vid in vids:
        st = state(pid, vid); cid = st[0][0]
        if DRY: R(visit=vid, pid=pid, step="move back + rebill Medicare", outcome="DRY", before=st); continue
        m = move_to_ins.move(cid, seq="2", rebill_seq=2); time.sleep(0.8)
        R(visit=vid, pid=pid, step="move back + insorder 2 + rebill seq 2", outcome=str(m)[:200], before=st, after=state(pid, vid))
# (2) Medicare-paid CCM visits: move back, then the contractual from Medicare's remit
med = {"17476094": "19452631", "17473422": "19452628"}
for pid, vid in med.items():
    st = state(pid, vid)
    for cid, cpt, ib, pb in st:
        if float(pb or 0) > 0 and not DRY:
            m = move_to_ins.move(cid); time.sleep(0.6); R(visit=vid, pid=pid, step="move back to insurance", charge=cid, outcome=str(m)[:160])
    R(visit=vid, pid=pid, step="state after move-back", outcome=state(pid, vid))
# Medicare remit lines (dismissed checks for 819814877)
di = payreasons.dismissed_index(since="2026-09-15")
cands = [c for c, m in di.items() if str(m.get("paymentnumber", "")).startswith("819814877")]
R(step="dismissed Medicare checks 819814877", outcome=cands)
lines = {}
for c in cands:
    try:
        d = payreasons.details(c)
        if not d.get("eracheckdetails"):
            if DRY: R(step="restore", check=c, outcome="DRY - would restore to read"); continue
            ok, _ = payreasons.restore(c); time.sleep(1); d = payreasons.details(c, fresh=True); R(step="restore", check=c, outcome=ok, lines=len(d.get("eracheckdetails", [])))
        for v in d.get("eracheckdetails", []):
            if str(v["visitid"]) in med.values(): lines[str(v["visitid"])] = (c, payreasons.check_meta(c, v), v)
    finally:
        if c in payreasons.RESTORED: payreasons.redismiss(c); R(step="redismiss", check=c, outcome="ok")
for pid, vid in med.items():
    if vid not in lines: R(visit=vid, pid=pid, step="Medicare remit line", outcome="not found in the 819814877 checks - left for the next run"); continue
    c, chk, v = lines[vid]
    for ch in v.get("charges", []):
        cid = str(ch["chargedetailid"]); carcs = [(r["payreasongroup"] + r["reasoncode"], r["reasonamt"]) for r in ch.get("carc", [])]
        rt = ET.fromstring(resave.detail(cid)); cx = [x for x in rt.iter("charge") if x.get("id") == "charge" + cid][0]; bal = float(cx.get("insbalance") or 0)
        co = round(sum(float(r["reasonamt"]) for r in ch.get("carc", []) if r["payreasongroup"] in ("CO", "OA", "PI")), 2); wo = round(min(co, bal), 2)
        if bal <= 0 or wo <= 0: R(visit=vid, pid=pid, charge=cid, step="Medicare contractual", outcome="nothing to adjust", bal=bal, carcs=carcs); continue
        if DRY: R(visit=vid, pid=pid, charge=cid, step="Medicare contractual", outcome="DRY would post $0 + WOINS %.2f (ERA-linked, reasons %s) on balance %.2f" % (wo, carcs, bal)); continue
        ok, payid, head = payreasons.post_line(pid, vid, chk, v, cid, ch, pay=0.0, wo=wo, wocode="WOINS"); time.sleep(0.8)
        rt2 = ET.fromstring(resave.detail(cid)); c2 = [x for x in rt2.iter("charge") if x.get("id") == "charge" + cid][0]
        R(visit=vid, pid=pid, charge=cid, step="Medicare contractual WOINS", outcome="posted %.2f ok=%s" % (wo, ok), carcs=carcs, paymentid=payid, ins_after=c2.get("insbalance"), pat_after=c2.get("patbalance"), resp=head[:100])
# (3) hospice visits: state + rebill re-check
for pid, vids in (("17473477", ["19452587"]), ("17477227", ["19449802", "19450279"])):
    for vid in vids:
        st = state(pid, vid); cid = st[0][0]
        if DRY: R(visit=vid, pid=pid, step="hospice re-check", outcome="DRY", state=st); continue
        f = freq1_visit.run(vid, cid, "2"); time.sleep(0.5)
        R(visit=vid, pid=pid, step="hospice rebill re-check", outcome=f, state=st)
json.dump(reg, open("registers/pr27_fix_%s%s.json" % (STAMP, "_dry" if DRY else ""), "w"), indent=1, default=str)
L("=== %s done" % ("DRY" if DRY else "LIVE"))
