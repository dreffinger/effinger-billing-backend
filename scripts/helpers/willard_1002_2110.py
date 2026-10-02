# PLAIN ENGLISH (5pm ET 10/2/2026 run 2026-10-02T2110Z): the Claimocity feed created the chart for Pam's 9/30 Sodalis admit
# (board row wilbourne-jocelyn-admit-0930, pat17477966) with NO insurance plan and one 9/30/2026 home visit (99344 + 99497-25, $433,
# first dx I10). The 11 PM ET 9/23 run already verified the insurance from Pam's card photos: Stedi CMS 271 = Medicare A/B with the
# MA entity BCBS of Florida; Stedi BCBSF = BLUEMEDICARE VALUE (PPO) ACTIVE 1/1-12/31/2026 (eligibility begin 2/1/2025) - the MA plan is
# the ONLY plan to bill (never add FLO02 behind an MA). This helper: (1) add_ins.add BCBS car6062, the member id from the board row,
# begin 02/01/2025, no group number; (2) AMD's own 271 on the new plan; (3) if ACTIVE: patient default order = that plan, full-visit
# resave of v19456752 with insorder = the plan sequence + onhcfa=1 (both charges echoed - the void trap); (4) address: the feed put the
# room number '9' in line 1 and the Sodalis street in line 2 -> line 1 = 1891 CAPITAL CIRCLE NE, line 2 = APT 9 (patient_patch PATCH;
# a 500 is reported, never retried). --dry = read only. Never touches: payments, other charts, other visits.
import amd, add_ins, elig_amd, ins_update, resave, patient_patch, json, sys, time
amd.login_cached(); DRY = "--dry" in sys.argv; S = "2026-10-02T2110Z"; pid = "17477966"; out = {"stamp": S, "dry": DRY, "log": []}
def L(m): print(m, flush=True); out["log"].append(m)
MEMBER = json.load(open("secrets/wilbourne_member.json"))["member"]
vis, pat, allc = resave.visit_charges("23368442")
L("visit %s date %s insorder '%s' charges %s" % (vis.get("id"), vis.get("date"), vis.get("insorder"), [(c.get("proccode"), c.get("modcodes"), c.get("fee")) for c in allc]))
if DRY: L("DRY: would add BCBS car6062 member %s.. begin 02/01/2025, 271, order, resave v19456752, address fix" % MEMBER[:4]); json.dump(out, open("registers/wilbourne_%s_dry.json" % S, "w"), indent=1); sys.exit()
insid, seq = add_ins.add(pid, "car6062", MEMBER, "02/01/2025", "1", "CC"); L("add_ins BCBS -> %s seq %s" % (insid, seq))
if insid:
    s = elig_amd.run_plan(pid, insid.replace("ins", ""), force=True); line = elig_amd.one_line(s); L("AMD 271 BCBS -> %s" % line[:300])
    out["elig"] = line[:400]
    if "ACTIVE" in line.upper() and "INACTIVE" not in line.upper():
        ok, r = ins_update.update(pid, insid, sequence=str(seq)); L("patient order %s -> %s" % (seq, ok))
        chg = ""
        for c in allc:
            a = {"id": c.get("id")}
            for f in resave.CHG_FIELDS:
                if c.get(f) is not None: a[f] = c.get(f)
            chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
        va = dict(vis.attrib); va["force"] = "1"; va["insorder"] = str(seq); va["onhcfa"] = "1"
        r = amd.post(amd.msg("updvisitwithcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
                             "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, v) for k, v in va.items() if v is not None), chg)))
        time.sleep(0.6); v2, p2, c2 = resave.visit_charges("23368442"); L("v19456752 resave insorder %s -> %s live=%d/%d insorder=%s onhcfa=%s" % (seq, "Fault" not in r, len(c2), len(allc), v2.get("insorder"), v2.get("onhcfa")))
        if "Fault" in r: L("resave response: " + r[:300])
    else: L("BCBS not ACTIVE on the 271 - plan left at seq %s, visit order unchanged; for the board" % seq)
try:
    r = patient_patch.family_address(pid, "1891 CAPITAL CIRCLE NE", "APT 9", "32308-5555", "TALLAHASSEE", "FL"); L("address PATCH -> %s" % str(r)[:200])
except Exception as e: L("address PATCH failed: %s" % str(e)[:200])
json.dump(out, open("registers/wilbourne_%s.json" % S, "w"), indent=1)
