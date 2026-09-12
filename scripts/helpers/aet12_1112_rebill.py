# PLAIN ENGLISH (AET12 rebill, 9/12 7am ET run): William 09:16 UTC on board row aet12-carrier-cpid: "i fixed this again try to
# rebill them all the aet12". For every AET12 row on today's exclusion lists: find the patient's Aetna Senior Supplemental
# (car42009) plan sequence, freq-1 reset + chargerebill that sequence, then complete the exclusion rows per claim run.
# Rules it uses: every rebill is frequency 1; a secondary is rebilled at its own sequence (no insorder change).
# Never touches: balances, plans, other carriers.
import amd, freq1_visit, re, time, json, collections
LOG = open("aet12_1112_rebill.log", "a")
def L(m): print(m, flush=True); LOG.write(m + "\n"); LOG.flush()
s = json.load(open("scan_0912/summary_before.json"))
rows = [(rid, r) for rid, rs in s["exclusions"].items() for r in rs if r["carriercode"].startswith("AET12")]
L("AET12 rows: %d" % len(rows))
amd.login_cached()
seqs = {}
for pid in sorted({r["patientid"] for _, r in rows}):
    d = amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"}))
    for ip in re.findall(r'<insplan [^>]*>', d):
        a = dict(re.findall(r'(\w+)="([^"]*)"', ip))
        if a.get("carrier") == "car42009" and not a.get("enddate"): seqs[pid] = a.get("sequence")
    L("pat%s AET12 seq %s" % (pid, seqs.get(pid))); time.sleep(0.3)
done = collections.defaultdict(list); fail = []
for rid, r in rows:
    pid = r["patientid"]; vid = r["id"]; cid = r["_chgs"][0].get("id") if r["_chgs"] else None
    if not seqs.get(pid) or not cid: fail.append((vid, "no seq/charge")); L("SKIP v%s no AET12 seq or charge" % vid); continue
    try:
        res = freq1_visit.run(vid, cid, seqs[pid])
    except Exception as e:
        res = "ERROR " + str(e)[:120]
    L("run %s v%s pat%s seq %s -> %s" % (rid, vid, pid, seqs[pid], res))
    if "204" in res: done[rid].append((vid, r["claimid"]))
    else: fail.append((vid, res))
    time.sleep(0.4)
for rid, lst in done.items():
    r = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": rid, "hide": "-1", "nocookie": "1"},
        "<visitlist>%s</visitlist>" % "".join('<visit id="%s" claimid="%s"/>' % (v, c) for v, c in lst)))
    L("hideexclusions run %s x%d -> %s" % (rid, len(lst), "ok" if "Fault" not in r else re.sub(r"\s+", " ", r[:200]))); time.sleep(0.4)
json.dump({"done": {k: v for k, v in done.items()}, "fail": fail, "seqs": seqs}, open("aet12_1112_results.json", "w"), indent=1)
L("DONE rebilled %d, failed %d" % (sum(len(v) for v in done.values()), len(fail)))
