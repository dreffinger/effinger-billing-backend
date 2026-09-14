# PLAIN ENGLISH (Unbilled column pass, 11 PM ET 9/13/2026 slot - ehpa cloud run 9/14 0420UTC)
# Decides, per William's standing rules and the lookup cascade already run (patient_db, AMD 271, Stedi MBI/eligibility/discovery):
#   (a) 'Insurance order is missing' charts: add the plan found by the cascade (add_ins.add, NO group numbers), run the free AMD
#       271 on it, write the admission date (updextrainsinfo hospitalizationfrom ONLY, anchor = the stay's 99223), full-visit
#       resave with insorder + onhcfa=1 (charge echo, void trap), move a blank address line 1 up from line 2, then release.
#   (b) the 18 re-created Medicaid visits (prof13 re-render, never billed): freq-1 + chargerebill on the Medicaid car6113 sequence,
#       then release.  (c) 'prior payor' rows whose primary claim is days old and unanswered (9/8 rule): release.
#   (d) O'Brien 'charges have errors' rows: release once the inspector batches are clean.
# Never touches: the 11 'payment reason codes' rows (2024 FLO02 reversals - HELD, reported), Bull (no coverage found - board),
#   any UNI20/BCBS aged balance, group numbers, hospitalizationto.
"""Usage: python3 unbilled_0914_fix.py [--dry] [--only a,b,c,d]"""
import amd, resave, add_ins, elig_amd, addr_line1_fix, freq1_visit, json, re, sys, time, datetime
import xml.etree.ElementTree as ET
dry = "--dry" in sys.argv
only = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else ["a", "b", "c", "d"]
amd.login_cached()
LOG = open("unbilled_0914_fix.log", "a")
def L(m): print(m, flush=True); LOG.write(m + "\n"); LOG.flush()
S = json.load(open("scan_0912/summary_before.json")); D = json.load(open("scan_0912/unbilled_0914_detail.json"))
rows = {r["id"]: r for r in S["unbilled"]}
REL = []   # visit ids to release at the end
L("=== unbilled fix %s dry=%s only=%s ===" % (datetime.datetime.utcnow().isoformat(), dry, only))

def set_admit(vid, code, admit):
    ext = ('<extins txtChargeCode="%s" hospitalizationfrom="%s" patsignature="1" emergency="0" epsdt="0" payprov="1" '
           'employment="0" autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>' % (code, admit))
    r = amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": "vst%s" % vid, "nocookie": "1"}, ext))
    return "ok" if "Fault" not in r else "FAULT " + re.sub(r"\s+", " ", r[:160])

def resave_full(cid, insorder=None, onhcfa="1", preauth=None):
    vis, pat, allc = resave.visit_charges(cid); chg = ""
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f] = c.get(f)
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    va = dict(vis.attrib); va["force"] = "1"
    if onhcfa: va["onhcfa"] = onhcfa
    if insorder: va["insorder"] = str(insorder)
    if preauth: va["preauth"] = preauth
    if dry: return "DRY resave %d charges insorder %s->%s" % (len(allc), vis.get("insorder"), va.get("insorder"))
    r = amd.post(amd.msg("updvisitwithnewcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
                         "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, v) for k, v in va.items()), chg)))
    time.sleep(0.6)
    if "Fault" in r: return "FAULT " + re.sub(r"\s+", " ", r[:200])
    v2, p2, c2 = resave.visit_charges(cid)
    return "ok insorder=%s onhcfa=%s live %d (was %d)" % (v2.get("insorder"), v2.get("onhcfa"), len(c2), len(allc))

def plans(pid):
    x = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "pat%s" % pid, "nocookie": "1"}), timeout=60)
    return [dict(i.attrib) for i in ET.fromstring(x).iter("insplan")]

def seq_of(pid, carrier):
    for p in plans(pid):
        if p.get("carrier") == carrier and not p.get("enddate"): return p.get("sequence"), p.get("id")
    return None, None

# ---------------- (a) no-insurance charts ----------------
# cfg per pid: add [[carrier, member, begindate]], bill = carrier to set as insorder, admit {vid: mm/dd/yyyy}, addr [a1, city, st, zip] or null
A = json.load(open("registers/unbilled_0914_fix_cfg.json"))   # per-chart plan/admission/address config (member numbers) - lives in registers/, never in the repo
if "a" in only:
    for pid, cfg in A.items():
        L("--- %s pat%s ---" % (cfg["name"], pid))
        for car, num, bd in cfg["add"]:
            s, insid = seq_of(pid, car)
            if s: L("  plan %s already on file seq %s (%s)" % (car, s, insid)); continue
            if dry: L("  DRY add %s %s begin %s" % (car, num, bd)); continue
            insid, s = add_ins.add(pid, car, num, bd); L("  add %s %s -> %s seq %s" % (car, num, insid, s)); time.sleep(0.5)
            if insid and str(insid).startswith("ins"):
                try:
                    e = elig_amd.run_plan(pid, insid.replace("ins", ""), True); L("  AMD 271: %s" % elig_amd.one_line(e)[:300])
                except Exception as ex: L("  AMD 271 ERR %s" % str(ex)[:120])
        seq, insid = seq_of(pid, cfg["bill"])
        if not seq: L("  NO open %s plan on chart -> HOLD" % cfg["bill"]); continue
        L("  bill seq %s (%s %s)" % (seq, cfg["bill"], insid))
        if cfg["addr"]:
            try:
                msg, det = addr_line1_fix.fix(pid, *cfg["addr"], dry=dry); L("  addr: %s %s" % (msg, json.dumps(det)[:200]))
            except Exception as ex: L("  addr ERR %s" % str(ex)[:150])
        vids = [r["id"] for r in S["unbilled"] if r["patientid"] == pid and "Insurance order" in r["_errs"][0]]
        for vid in vids:
            r = rows[vid]; cid = r["_chgs"][0]["id"]; codes = sorted({c["chgcode"] for c in r["_chgs"]})
            adm = cfg["admit"].get(vid)
            if adm and not dry:
                for code in codes: L("  v%s admit %s %s -> %s" % (vid, code, adm, set_admit(vid, code, adm))); time.sleep(0.3)
            elif adm: L("  DRY v%s admit %s" % (vid, adm))
            L("  v%s resave -> %s" % (vid, resave_full(cid, insorder=seq)))
            REL.append(vid); time.sleep(0.4)

# ---------------- (b) re-created Medicaid visits ----------------
RECREATED = ["19454223", "19454224", "19454226", "19454227", "19454228", "19454229", "19454230", "19454231", "19454232", "19454233", "19454234", "19454235", "19454236", "19454246", "19454247", "19454248", "19454250", "19454251"]
if "b" in only:
    L("--- (b) recreated Medicaid visits ---")
    for vid in RECREATED:
        d = D["txh"].get(vid); pid = d["pid"]; cid = [c for c in d["charges"] if c["void"] != "1"][0]["chargeid"]
        seq, insid = seq_of(pid, "car6113")
        if not seq: L("  v%s pat%s NO Medicaid plan -> HOLD" % (vid, pid)); continue
        if dry: L("  DRY v%s pat%s chg %s freq1 rebill MCAD seq %s" % (vid, pid, cid, seq)); REL.append(vid); continue
        try: L("  v%s pat%s chg %s -> %s" % (vid, pid, cid, freq1_visit.run(vid, cid, seq))); REL.append(vid)
        except Exception as ex: L("  v%s REBILL ERR %s" % (vid, str(ex)[:150]))
        time.sleep(0.4)

# ---------------- (c) prior-payor rows ----------------
if "c" in only:
    pp = [r["id"] for r in S["unbilled"] if r["_errs"][0].startswith("A payment from the prior payor") and r["id"] not in RECREATED]
    L("--- (c) prior-payor rows to release: %d ---" % len(pp)); REL += pp

# ---------------- (d) O'Brien rows ----------------
if "d" in only:
    b = amd.call('action="getclaiminspectorbatches" class="chargeentry" nocookie="1"'); bl = re.findall(r'<batch id="([^"]+)"', b)
    ob = [r["id"] for r in S["unbilled"] if r["patientid"] == "44953"]
    if bl: L("--- (d) inspector batches still open %s -> O'Brien rows %s NOT released" % (bl, ob))
    else: L("--- (d) inspector clean -> release O'Brien rows %s" % ob); REL += ob

# ---------------- release ----------------
REL = list(dict.fromkeys(REL))
L("release %d visits: %s" % (len(REL), REL))
if REL and not dry:
    for i in range(0, len(REL), 40):
        chunk = REL[i:i + 40]
        r = amd.post(amd.msg("hideunbillablevisits", "claimsreports", {"hide": "-1", "nocookie": "1"}, "<visitlist>%s</visitlist>" % "".join('<visit id="%s"/>' % v for v in chunk)), timeout=120)
        L("  hideunbillablevisits %d -> %s" % (len(chunk), "ok" if "Fault" not in r else "FAULT " + re.sub(r"\s+", " ", r[:200]))); time.sleep(0.5)
    t = amd.post(amd.msg("getclaimunbillablecharges", "claimsreports", {"lowdate": "", "highdate": "", "carrier": "", "provider": "", "nocookie": "1"}), timeout=180)
    L("Unbilled after: totalcount=%s" % (re.search(r'totalcount="([^"]*)"', t).group(1) if re.search(r'totalcount="([^"]*)"', t) else "?"))
json.dump(REL, open("registers/unbilled_release_2026-09-14_0420UTC.json", "w"))
