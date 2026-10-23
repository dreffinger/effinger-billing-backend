# PLAIN ENGLISH (2:40 PM ET 10/23 slot, run 2026-10-23T1842Z): chart 17478064's two HCA visits (v19457791 99223 10/12/2026, v19457784
#   99232 10/13/2026, $421) were rejected on claim run 1700319 by Capital Health Plan: "SUBSCRIBER ID IS EIGHT NUMERIC CHARACTERS WITH THE
#   FIRST CHARACTER STARTING WITH 0, 1, 2, 5 OR 6, OR A MAXIMUM OF ELEVEN CHARACTERS WITH A PREFIX OF CHP, CHI, OR CIO". The chart's CAP07
#   plan (ins9520948) carries CIO001011016 - 12 characters, one too many. CHP's own 271 on that plan (AMD free eligibility, 19:0xZ)
#   echoes the member as NM109 = 01011016 (8 digits, first digit 0 = the allowed form), so that is the id the payer recognizes.
# Decides: nothing new - the 10/14 exclusion rule ('wrong member id' -> fix the id, frequency-1 original, hideexclusions).
# Does (live): ins_update.update(pid, ins, subscribernum="01011016") [wrapped updateinsurance; re-reads insorder], freq1_visit.run per
#   visit on seq 1 (one rebill per visit), hideexclusions run 1700319 for 19457784A + 19457791A, re-list the run.
# --dry = read only. Register registers/cap07_id_fix_2026-10-23T1842Z[_dry].json. Chart/visit ids only - no names.
import amd, re, json, sys, time
DRY = "--dry" in sys.argv; S = "2026-10-23T1842Z"
PID = "17478064"; INS = "ins9520948"; NEW = "01011016"; RUN = "1700319"
VIS = [("19457791", "23369837", "19457791A"), ("19457784", "23369828", "19457784A")]
amd.login_cached(); out = {"stamp": S, "dry": DRY, "pid": PID, "ins": INS, "new_id": NEW, "steps": []}
def plans():
    r = amd.post(amd.msg("getdemographic", "demographics", {"patientid": PID, "nocookie": "1"}))
    p = {d.get("id"): d for d in [dict(re.findall(r'(\w+)="([^"]*)"', x)) for x in re.findall(r'<insplan [^>]*/?>', r)]}
    m = re.search(r'<patient [^>]*?insorder="([^"]*)"', r)
    return p, (m.group(1) if m else None)
p, order = plans(); cur = p.get(INS, {}).get("subscribernum")
print("before: subscribernum", cur, "insorder", order); out["before"] = {"subscribernum": cur, "insorder": order}
if cur == NEW: print("id already corrected"); out["steps"].append("id already " + NEW)
elif DRY: print("DRY - would updateinsurance subscribernum %s -> %s, then freq1 + rebill seq 1 on %s, then hideexclusions run %s" % (cur, NEW, [v[0] for v in VIS], RUN))
else:
    import ins_update
    ok, msg = ins_update.update(PID, INS, subscribernum=NEW); print("updateinsurance ->", ok, msg[:200]); out["steps"].append({"updateinsurance": [ok, msg[:200]]})
    if not ok: json.dump(out, open("registers/cap07_id_fix_%s.json" % S, "w"), indent=1); sys.exit("STOP - id not written")
    time.sleep(0.8); p, order = plans(); print("after: subscribernum", p.get(INS, {}).get("subscribernum"), "insorder", order)
    out["after_plan"] = {"subscribernum": p.get(INS, {}).get("subscribernum"), "insorder": order}
    if p.get(INS, {}).get("subscribernum") != NEW: json.dump(out, open("registers/cap07_id_fix_%s.json" % S, "w"), indent=1); sys.exit("STOP - re-read does not show the new id")
if not DRY:
    import freq1_visit
    for vid, cid, claimid in VIS:
        r = freq1_visit.run(vid, cid, 1); print("v%s c%s:" % (vid, cid), r); out["steps"].append({"visit": vid, "rebill": str(r)[:160]}); time.sleep(0.8)
    lst = "".join('<visit id="%s" claimid="%s"/>' % (vid, claimid) for vid, cid, claimid in VIS)
    x = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": RUN, "hide": "-1", "nocookie": "1"}, "<visitlist>%s</visitlist>" % lst), timeout=120)
    print("hideexclusions ->", re.sub(r"\s+", " ", x[:200])); out["steps"].append({"hideexclusions": re.sub(r"\s+", " ", x[:200])}); time.sleep(1)
    y = amd.post(amd.msg("getclaimexclusioncharges", "claimsreports", {"claimrunid": RUN, "clearinghouse": "1", "payer": "1", "nocookie": "1"}), timeout=120)
    left = re.findall(r'<visit [^>]*?id="(\d+)"', y); print("run %s exclusion visits left:" % RUN, left); out["left"] = left
json.dump(out, open("registers/cap07_id_fix_%s%s.json" % (S, "_dry" if DRY else ""), "w"), indent=1); print("DONE")
