# PLAIN ENGLISH (fix referring provider on re-rendered visits)
# Decides: Which visits still print Garcia (rprov15) as referring provider after the 9/11 re-render to Effinger (prof13),
#          and repoints them at a new referral plan whose referring provider is Effinger (rprov13).
# Rules it uses: the referring provider lives on the visit's referral plan (refplan); plans cannot be updated via the gateway
#          (9/20 probes), so: addreferralplan (ismain=0, refprov=rprov13) -> repoint the visit with a FULL-charge resave (void-trap:
#          every active charge echoed, no preauth attr) -> verify refplan + charge count -> freq-1 + rebill on Medicaid's own sequence.
# Never touches: the chart's main plan, charges on other visits, balances. --rebill only for visits already denied N286.
"""Usage: python3 fix_referring_provider.py --pids 17472419,... [--rebill-vids 19454237,...] [--dry]"""
import sys, re, time, json, argparse, datetime
sys.path.insert(0, "/home/claude/effinger-billing-backend/core")
import amd, resave
import xml.etree.ElementTree as ET
EFFINGER_RPROV = "rprov13"; GARCIA_RPROV = "rprov15"; MCAD = "car6113"
STAMP = datetime.date.today().isoformat(); LOGF = open(f"/home/claude/unbilled/fix_refprov_{STAMP}.log", "a")
def L(m): print(m, flush=True); LOGF.write(m + "\n"); LOGF.flush()

def plans(pid):
    t = amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"}), timeout=120)
    ref = [dict(re.findall(r'(\w+)="([^"]*)"', x)) for x in re.findall(r'<refplan [^>]*>', t)]
    ins = [dict(re.findall(r'(\w+)="([^"]*)"', x)) for x in re.findall(r'<insplan [^>]*>', t)]
    return ref, ins
def medicaid_seq(ins):
    for p in ins:
        if p.get("carrier") == MCAD and not p.get("enddate"): return p.get("sequence")
    for p in ins:
        if p.get("carrier") == MCAD: return p.get("sequence")
def open_visits_on_plan(pid, planid):
    """visits on this chart (recent history pages) that point at planid and are prof13 with live charges"""
    out = {}
    for page in range(1, 6):
        th = ET.fromstring(amd.post(amd.msg('gettxhistory', 'demographics', {'patientid': pid, 'filterhistory': '0', 'pagenumber': str(page), 'typefilter': '0', 'sortbypayment': 'false', 'groupbyvisit': '0', 'sortdescending': '1', 'visitid': '0', 'profileid': '', 'getmemo': 'false', 'nocookie': '1'}), timeout=120))
        chs = list(th.iter("charge"))
        for c in chs:
            if c.get("void") == "1" or (c.get("fee") or "").startswith("-"): continue
            if float(c.get("insbal") or 0) <= 0.005: continue
            out.setdefault(c.get("visit"), []).append(re.sub(r"\D", "", c.get("id")))
        if len(chs) < 100: break
    keep = {}
    for vid, cids in out.items():
        d = ET.fromstring(resave.detail(cids[0])); vis = d.find(".//visit")
        if vis is not None and vis.get("refplan") == planid and vis.get("profile") == "prof13": keep[vid] = cids
        time.sleep(0.15)
    return keep

def fix_chart(pid, rebill_vids, dry):
    ref, ins = plans(pid); main = [p for p in ref if p.get("ismain") == "1"]
    if not main: L(f"pat{pid}: no main plan - skip"); return
    mp = main[0]
    if mp.get("refprov") != GARCIA_RPROV: L(f"pat{pid}: main plan refprov={mp.get('refprov')} (not Garcia) - skip"); return
    already = [p for p in ref if p.get("refprov") == EFFINGER_RPROV and p.get("ismain") != "1"]
    vis_on_main = open_visits_on_plan(pid, mp["id"])
    L(f"pat{pid}: main plan {mp['id']} refprov=rprov15; prof13 open visits on it: {list(vis_on_main)}; existing Effinger plan: {[p['id'] for p in already]}")
    if not vis_on_main: return
    if dry: L("  DRY - stop"); return
    if already: newplan = already[0]["id"]
    else:
        r = amd.post(amd.msg("addreferralplan", "chargeentry", {"nocookie": "1"},
            f'<refplan id="" patient="pat{pid}" ismain="0" status="stat1" preauthreq="0" sequence="2" refprov="{EFFINGER_RPROV}" type="I" reason="SELF-REFERRAL" preauth="" begindate="" enddate="" maxvisits="0" usedvisits="0" maxamount="" usedamount="0" proccode="" diagcodes="" facility="{mp.get("facility","")}"/>'))
        m = re.search(r'id="(rplan\d+)"', r); newplan = m.group(1) if m else None
        if not newplan or newplan == mp["id"]:
            L(f"  addreferralplan returned {newplan} (main plan or none) - the get-or-return quirk; UI fix needed for this chart"); return
        L(f"  new referral plan {newplan} refprov={EFFINGER_RPROV}")
    seq = medicaid_seq(ins)
    for vid, cids in vis_on_main.items():
        vis, pat, allc = resave.visit_charges(cids[0]); pre = len(allc)
        chg = ""
        for c in allc:
            a = {"id": c.get("id")}
            for fld in resave.CHG_FIELDS:
                if c.get(fld) is not None: a[fld] = c.get(fld)
            chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
        va = f'id="{vis.get("id")}" date="{vis.get("date")}" profile="{vis.get("profile")}" insorder="{vis.get("insorder")}" refplan="{newplan}" facility="{vis.get("facility")}" force="1"'
        r = amd.post(amd.msg("updvisitwithnewcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
                             f"<visit {va}><chargelist>{chg}</chargelist></visit>"))
        if "Fault" in r: L(f"  v{vid} resave FAULT: {re.sub(chr(10),' ',r)[:120]}"); continue
        time.sleep(0.6)
        d = ET.fromstring(resave.detail(cids[0])); v2 = d.find(".//visit"); _, _, post = resave.visit_charges(cids[0])
        ok = v2 is not None and v2.get("refplan") == newplan and len(post) == pre
        L(f"  v{vid}: refplan {vis.get('refplan')} -> {v2.get('refplan') if v2 is not None else '?'}  charges {pre}->{len(post)}  {'OK' if ok else '** CHECK **'}")
        if ok and vid in rebill_vids and seq:
            for c in post:
                pc = c.get("proccode")
                amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": re.sub(r"\D", "", vis.get("id")), "nocookie": "1"},
                    f'<extins txtChargeCode="{pc}" resubmissioncode="1" origrefnum="" patsignature="1" emergency="0" epsdt="0" payprov="1" employment="0" autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>'))
                code, _ = amd.rebill_charge(c.get("id"), seq); L(f"     rebill c{c.get('id')} seq {seq} -> http {code}")
                time.sleep(0.3)
        time.sleep(0.5)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--pids", required=True); ap.add_argument("--rebill-vids", default=""); ap.add_argument("--dry", action="store_true")
    a = ap.parse_args(); amd.login_cached()
    rv = set(x.strip() for x in a.rebill_vids.split(",") if x.strip())
    for pid in a.pids.split(","): fix_chart(pid.strip(), rv, a.dry)
