# PLAIN ENGLISH (1am ET 9/22/2026 run, 2026-09-22T0510Z): the first AMD claim run since 9/16 (1700216, 9/19 21:02 AMD clock, 54 claims) rejected
#   3 Florida Blue SECONDARY claims 'CH FH PREF0283: MISSING PAYER DOC CONTROL NUM'. Cause read from the charges: none of them carries an
#   extins frequency code, so AMD sent them as resubmissions (frequency 7) without a payer claim number.
# Decides, per William's 9/3 + 9/14 rules: a visit Florida Blue already adjudicated (a non-void Florida Blue payment with the payer claim
#   number in <payment origrefnum>) is re-sent as frequency 7 WITH that ICN (freq7_visit); a visit Florida Blue never adjudicated goes out as
#   an original, frequency 1 (freq1_visit); both to the chart's Florida Blue sequence (the secondary here - Medicare paid 9/19). Then the 11
#   exclusion rows are completed (hideexclusions run 1700216) and the run re-listed. Register: registers/excl_1700216_2026-09-22T0510Z.json
# Never touches: balances, payments, any other claim run.
import amd, resave, freq1_visit, freq7_visit, json, re, time, sys
import xml.etree.ElementTree as ET
DRY = "--dry" in sys.argv
amd.login_cached()
S_ = json.load(open("scan_0912/summary_before.json")); rows = S_["exclusions"]["1700216"]
reg = []; seqcache = {}
def L(m): print(m, flush=True)
def bcbs_seq(pid):
    if pid not in seqcache:
        t = amd.post(amd.msg("getdemographic", "demographics", {"patientid": str(pid), "nocookie": "1"}), timeout=120)
        plans = [dict(re.findall(r'(carrier|sequence|enddate)="([^"]*)"', p)) for p in re.findall(r'<insplan [^>]*/?>', t)]
        b = [p for p in plans if p.get("carrier") == "car6062" and not p.get("enddate")]
        seqcache[pid] = (b[0]["sequence"] if b else None, plans)
    return seqcache[pid]
for v in rows:
    vid, pid, claimid = v["id"], v["patientid"], v["claimid"]; cid = v["_chgs"][0]["id"]
    rec = {"vid": vid, "claimid": claimid, "pid": pid, "cid": cid, "cpts": [c["chgcode"] for c in v["_chgs"]], "dos": v["_chgs"][0]["dos"].strip(), "steps": []}
    def S(m): rec["steps"].append(m); L("v%s pat%s %s" % (vid, pid, m))
    seq, plans = bcbs_seq(pid)
    icn = None
    for c in v["_chgs"]:
        rt = ET.fromstring(resave.detail(c["id"])); ch = [x for x in rt.iter("charge") if x.get("id") == "charge" + c["id"]][0]
        for p in ch.iter("payment"):
            if p.get("void") != "1" and p.get("carrierfid") == "6062" and p.get("origrefnum"): icn = p.get("origrefnum")
    S("Florida Blue seq %s; prior Florida Blue ICN %s" % (seq, icn))
    if not seq: S("no live Florida Blue plan - HOLD"); rec["outcome"] = "hold"; reg.append(rec); continue
    if DRY: rec["outcome"] = "DRY"; reg.append(rec); continue
    r = freq7_visit.run(vid, cid, seq, icn) if icn else freq1_visit.run(vid, cid, seq)
    S("rebill -> %s" % r); rec["outcome"] = ("freq7" if icn else "freq1") + (" 204" if "204" in r else " " + r[:60])
    reg.append(rec); time.sleep(0.6)
done = [r for r in reg if "204" in r.get("outcome", "")]
if done and not DRY:
    xml = amd.call('action="hideexclusions" class="claimsreports" claimrunid="1700216" hide="-1" nocookie="1"', "<visitlist>%s</visitlist>" % "".join('<visit id="%s" claimid="%s"/>' % (r["vid"], r["claimid"]) for r in done))
    L("hideexclusions x%d -> %s" % (len(done), re.sub(r"\s+", " ", xml)[:200]))
    time.sleep(1)
    t = amd.post(amd.msg("getclaimexclusioncharges", "claimsreports", {"claimrunid": "1700216", "clearinghouse": "1", "payer": "1", "nocookie": "1"}), timeout=120)
    L("run 1700216 re-listed: %d visit rows" % len(re.findall(r"<visit ", t)))
json.dump(reg, open("registers/excl_1700216_2026-09-22T0510Z.json", "w"), indent=1)
L("=== exclusions done: %s" % [(r["vid"], r.get("outcome")) for r in reg])
