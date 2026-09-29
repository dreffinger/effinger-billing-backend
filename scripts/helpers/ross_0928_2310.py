# PLAIN ENGLISH (7pm ET 9/28/2026 run 2026-09-28T2310Z): Pam's Brynwood readmit record for pat20729 (Medicare A primary, Medicaid # on the sheet,
# secondary 'Medicare A coinsurance from Medicaid - SUNSHINE STATE') - the chart carries Medicare alone (QMB on AMD's 271). Adds the Sunshine
# SMMC plan (SUN01, the Medicaid number from the sheet, no group), reads AMD's 271 on it; if ACTIVE sets the patient order 1,2 and the two
# 9/23-9/24 HCA visits resaved this run to insorder 1,2 (full-visit echo). Never touches: payments, other charts.
import amd, add_ins, elig_amd, ins_update, resave, json, re, sys, time
amd.login_cached(); DRY = "--dry" in sys.argv; pid = "20729"; out = []
def L(m): print(m, flush=True); out.append(m)
num = open("secrets/rossiter_medicaid_num.txt").read().strip()
if DRY: L("DRY: would add SUN01 car6194 %s.. begin 09/25/2026" % num[:3]); sys.exit()
insid, seq = add_ins.add(pid, "car6194", num, "01/01/2026", "1", "MC"); L("add_ins SUN01 -> %s seq %s" % (insid, seq))
if insid:
    s = elig_amd.run_plan(pid, insid.replace("ins", ""), force=True); line = elig_amd.one_line(s); L("AMD 271 SUN01 -> %s" % line[:300])
    if "ACTIVE" in line.upper() and "INACTIVE" not in line.upper():
        ok, r = ins_update.update(pid, insid, sequence="1,%s" % seq); L("patient order 1,%s -> %s" % (seq, ok))
        for vid, cid in (("19456249", "23367873"), ("19456269", "23367893")):
            vis, pat, allc = resave.visit_charges(cid); chg = ""
            for c in allc:
                a = {"id": c.get("id")}
                for f in resave.CHG_FIELDS:
                    if c.get(f) is not None: a[f] = c.get(f)
                chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
            va = dict(vis.attrib); va["force"] = "1"; va["insorder"] = "1,%s" % seq; va["onhcfa"] = "1"
            r = amd.post(amd.msg("updvisitwithcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"}, "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, v) for k, v in va.items()), chg)))
            time.sleep(0.6); v2, p2, c2 = resave.visit_charges(cid); L("v%s resave insorder 1,%s -> %s live=%d/%d insorder=%s" % (vid, seq, "Fault" not in r, len(c2), len(allc), v2.get("insorder")))
    else: L("SUN01 not ACTIVE on the 271 - plan left at seq %s, visit order unchanged (Medicare alone); note for the board" % seq)
json.dump(out, open("registers/rossiter_%s.json" % "2026-09-28T2310Z", "w"), indent=1)
