# PLAIN ENGLISH (7am ET 9/22/2026 run 2026-09-22T1110Z): the new $0 Medicare ERA check 1051728 (349980199, dismissed by
#   era_clear this run) carries 8 denial claims. Decides, per the standing rules:
#   (1) HOSPICE CO-B9 (William 9/20 rule: add the GV modifier and rebill) - pat17472784 v19420555 99307 10/7/2025 ($68) and
#       pat22603 v19454390 99308 9/2/2026 ($107): gv_rebill.add_gv (full-visit echo) + freq1_visit.run to the chart's Medicare seq 1.
#   (2) RAILROAD MEDICARE CO-109 + N105 ("misdirected claim - RRB beneficiary") on pat12182505's four CCM visits (99487+99489,
#       $315 each; every one already denied the same way on an earlier check): wrong Medicare contractor -> add the RET01 plan
#       (car6080 RETIRED RAILROAD MEDICARE, same MBI, no group), end-date FLO02 the day before the first denied DOS (09/20/2025),
#       patient order RET01 first / AARP Medigap second, then the three visits inside 12 months (4/22, 7/13, 8/23/2026, $945) get
#       visit insorder = the RET01 sequence and a frequency-1 rebill (amd.rebill_charge carries the deceased guard - it fails
#       closed). The 9/21/2025 visit ($315) is past the 12-month window as of 9/22/2026 -> WOLATE with a dated note (William 9/7
#       + 9/21: primary claims over 12 months from DOS and unpaid are written off, not chased).
#   (3) AWV PR-119 / N130 (benefit maximum) on pat23617 and pat21885 G0439 7/13/2026 ($204 each): our own history shows the
#       previous G0439 on 7/17/2025 = 11 full months passed, so the denial is not explained by our records - NO write, balances
#       stay on insurance; one board row on William's turn (appeal with the 11-month calculation, or WONCS).
# Never touches: visits with a non-void payment > 0, any other chart, hospitalizationto, group numbers.
"""Usage: python3 era_denials_1051728_0922_1110.py [--dry]"""
import amd, gv_rebill, freq1_visit, add_ins, ins_update, move_to_ins, manual_post, txh, json, re, time, sys, os
DRY = "--dry" in sys.argv
STAMP = "2026-09-22T1110Z"; CHECK = "349980199"; CID = "1051728"
amd.login_cached()
NOW = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
out = {"stamp": STAMP, "check": CID, "dry": DRY, "hospice": [], "rrb": [], "awv": [], "errors": []}
def L(m): print(m, flush=True)
def paid(pid, vid):
    root = txh.fetch("pat" + pid)
    return [(c.get("id"), p.get("carrier"), p.get("amount")) for c in root.iter("charge") if c.get("visit") == vid and c.get("void") != "1"
            for p in c.iter("payment") if p.get("void") != "1" and float(p.get("amount") or 0) != 0]
# (1) hospice GV + rebill
for pid, vid, cid, seq in (("17472784", "19420555", "23325534", "1"), ("22603", "19454390", "23365478", "1")):
    rec = {"pid": pid, "vid": vid, "cid": cid, "seq": seq}
    p = paid(pid, vid)
    if p: rec["result"] = "SKIP - payment posted %s" % p; out["hospice"].append(rec); L(rec); continue
    if DRY: rec["result"] = "DRY: add_gv + freq1 rebill seq %s" % seq; out["hospice"].append(rec); L(rec); continue
    try:
        r1 = gv_rebill.add_gv(cid); time.sleep(0.5); r2 = freq1_visit.run(vid, cid, seq)
        rec["result"] = "%s; %s" % (r1, r2)
    except Exception as e: rec["result"] = "ERROR %s" % e; out["errors"].append(rec["result"])
    out["hospice"].append(rec); L(rec); time.sleep(0.5)
# (2) railroad Medicare re-route
PID = "12182505"; FLO02_INS = "ins6028495"
_t = amd.post(amd.msg("getdemographic", "demographics", {"patientid": PID, "nocookie": "1"}), timeout=120)
MBI = re.search(r'<insplan id="%s"[^>]*subscribernum="([^"]*)"' % FLO02_INS, _t).group(1)   # the chart MBI, never a literal
rrb = {"pid": PID, "steps": []}
def S(m): rrb["steps"].append(m); L("pat%s %s" % (PID, m))
if DRY:
    S("DRY: add_ins RET01 car6080 %s begin 02/01/2022; FLO02 %s enddate 09/20/2025; patient order <newseq>,2; visits 19439508/19448729/19452655 insorder <newseq> + freq1; WOLATE 23321115 $206 + 23321116 $109 (9/21/2025)" % (MBI[:4] + "...", FLO02_INS))
else:
    try:
        insid, seq = add_ins.add(PID, "car6080", MBI, "02/01/2022")
        S("add_ins RET01 -> %s seq %s" % (insid, seq))
        if not insid or not str(seq).isdigit(): raise RuntimeError("add_ins failed: %s %s" % (insid, seq))
        newseq = str(seq); time.sleep(0.5)
        ok, msg = ins_update.update(PID, FLO02_INS, enddate="09/20/2025"); S("FLO02 %s enddate 09/20/2025 -> %s %s" % (FLO02_INS, ok, msg[:120])); time.sleep(0.5)
        ok, msg = ins_update.update(PID, insid, sequence="%s,2" % newseq); S("patient order %s,2 -> %s %s" % (newseq, ok, msg[:120])); time.sleep(0.5)
        for vid, cid in (("19439508", "23346974"), ("19448729", "23358048"), ("19452655", "23363029")):
            if paid(PID, vid): S("v%s SKIP - payment posted" % vid); continue
            r1 = move_to_ins.move(cid, seq=newseq); time.sleep(0.5); r2 = freq1_visit.run(vid, cid, newseq)
            S("v%s move -> %s; %s" % (vid, r1, r2)); time.sleep(0.5)
        for cid, amt in (("23321115", 206.0), ("23321116", 109.0)):
            ok, msg = manual_post.post(cid, "FLO02", 0.0, amt, "WOLATE", checknumber=CHECK, note="untimely: Medicare CO109/N105 (RRB beneficiary) on ERA %s 9/22/2026, DOS 9/21/2025 past the 12-month window - William 9/7 rule; run %s" % (CHECK, STAMP), dry=False)
            S("WOLATE %s $%.2f -> %s %s" % (cid, amt, ok, str(msg)[:160])); time.sleep(0.5)
        t = amd.post(amd.msg("getdemographic", "demographics", {"patientid": PID, "nocookie": "1"}), timeout=120)
        S("readback plans %s insorder %s" % ([dict(re.findall(r'(carrier|sequence|enddate)="([^"]*)"', p)) for p in re.findall(r'<insplan [^>]*/?>', t)], (re.search(r'<patient [^>]*insorder="([^"]*)"', t) or [None, "?"])[1]))
    except Exception as e:
        S("ERROR %s" % e); out["errors"].append(str(e))
out["rrb"].append(rrb)
# (3) AWV PR119 - no write
for pid, vid, cid in (("23617", "19448516", "23357819"), ("21885", "19448510", "23357813")):
    out["awv"].append({"pid": pid, "vid": vid, "cid": cid, "amount": 204.0, "result": "PR119/N130 benefit maximum; previous G0439 7/17/2025 (11 full months passed) - balance left on insurance, board row for William (appeal vs WONCS)"})
json.dump(out, open("registers/era_denials_%s_%s%s.json" % (CID, STAMP, "_dry" if DRY else ""), "w"), indent=1)
L("DONE errors=%d" % len(out["errors"]))
