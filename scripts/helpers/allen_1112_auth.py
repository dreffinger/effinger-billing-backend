# PLAIN ENGLISH (Lowry Fenwick 9/4 stay auth, 9/12 7am ET run): William posted the 12-byte auth in secrets/run_1112_ids.json on the board (09:05 UTC) and dropped
# 'herman allen new auth.pdf' (HCA facesheet, admit 09/04/26, Auth the 12-byte auth in secrets/run_1112_ids.json, 12 bytes). Write it on the 9/4-9/6 stay only:
# check which referral plan each of the 3 visits points to, resave each visit with that same refplan + preauth (full echo,
# hospitalizationfrom 09/04/2026, onhcfa=1), verify the plan carries the 12-byte auth, freq-1 rebill seq 1, then complete the
# 3 exclusions on run 1700158. The 8/10 stay (visit 19451315) keeps its hold - no 12-byte auth exists for it yet.
# Never touches: other stays' plans, balances.
import amd, resave, era_post, freq1_visit, re, time, json
LOG = open("allen_1112_auth.log", "a")
def L(m): print(m, flush=True); LOG.write(m + "\n"); LOG.flush()
AUTH = json.load(open("secrets/run_1112_ids.json"))["lowry_auth"]; HOSP = "09/04/2026"
VIS = [("19453862", "23364781", "19453862B"), ("19453861", "23364780", "19453861B"), ("19453860", "23364779", "19453860B")]
amd.login_cached(); batch = era_post.batch()
plans = {}
for vid, cid, _ in VIS:
    v, p, ch = resave.visit_charges(cid); plans[vid] = v.get("refplan"); L("v%s refplan=%s preauth=%s charges=%d" % (vid, v.get("refplan"), v.get("preauth"), len(ch)))
if len(set(plans.values())) != 1:
    L("STOP: the 3 visits are on different plans %s - not writing (would cross-write)" % plans); raise SystemExit
plan = list(plans.values())[0]
# is the 8/10 stay visit on the same plan? (then writing the auth would overwrite ITS auth too)
v8, p8, c8 = resave.visit_charges("23361358"); L("8/10 visit 19451315 refplan=%s" % v8.get("refplan"))
if v8.get("refplan") == plan:
    L("STOP: the 8/10 stay shares plan %s - needs its own plan first; not writing" % plan); raise SystemExit
done = []
for vid, cid, claim in VIS:
    v, p, allc = resave.visit_charges(cid)
    chg = ""
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f] = c.get(f)
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, val) for k, val in a.items())
    va = dict(v.attrib); va.update({"force": "1", "refplan": plan, "preauth": AUTH, "onhcfa": "1"})
    vs = " ".join('%s="%s"' % (k, val) for k, val in va.items())
    r = amd.post(amd.msg("updvisitwithnewcharges", "chargeentry",
        {"patientid": p.get("id"), "episodeid": v.get("episode"), "approval": "1", "inspectorenabled": "1", "batchid": str(batch),
         "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
        "<visit %s><chargelist>%s</chargelist>%s</visit>" % (vs, chg, resave._extins_xml(v, HOSP))))
    if "Fault" in r: L("  v%s FAULT %s" % (vid, re.sub(r"\s+", " ", r[:200]))); continue
    time.sleep(0.8)
    v2, p2, c2 = resave.visit_charges(cid); ex = v2.find("extins")
    L("  v%s saved live=%d/%d refplan=%s preauth=%s hospfrom=%s" % (vid, len(c2), len(allc), v2.get("refplan"), v2.get("preauth"), ex.get("hospitalizationfrom") if ex is not None else None))
    if len(c2) != len(allc) or v2.get("preauth") != AUTH: L("  v%s VERIFY FAILED - not rebilling" % vid); continue
    L("  " + freq1_visit.run(vid, cid, 1)); time.sleep(0.5); done.append((vid, claim))
# plan readback
d = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "17475970", "nocookie": "1"}))
for rp in re.findall(r'<refplan [^>]*>', d):
    a = dict(re.findall(r'(\w+)="([^"]*)"', rp)); L("  refplan %s preauth=%s" % (a.get("id"), a.get("preauth")))
if done:
    r = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": "1700158", "hide": "-1", "nocookie": "1"},
        "<visitlist>%s</visitlist>" % "".join('<visit id="%s" claimid="%s"/>' % (v, c) for v, c in done)))
    L("hideexclusions 1700158 %s -> %s" % (done, "ok" if "Fault" not in r else re.sub(r"\s+", " ", r[:200])))
json.dump({"done": done, "plan": plan}, open("allen_1112_results.json", "w"))
