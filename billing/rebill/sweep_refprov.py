# PLAIN ENGLISH (referring-provider sweep, standing nightly step)
# Decides: Which charts still default to Garcia (rprov15) as referring provider while carrying open prof13 (Effinger) visits,
#          and fixes them on the back end: addreferralplan ismain=1 refprov=rprov13 (becomes the chart's main plan; the old one
#          is demoted), full-charge repoint of every open prof13 visit on the old plan, freq-1 rebill on the VISIT'S OWN sequence.
# Rules it uses: void-trap discipline on every resave (all active charges echoed, charge count verified); never touches
#          balances, other patients' visits, or visits already on an rprov13 plan. Population = every patient with an open
#          insurance balance (masswriteoffsearch isinsbalance:true, all carriers, 3-year bill window).
# Never: UI steps. --dry lists the charts it would fix.
import sys, re, json, time, datetime, argparse, requests
sys.path.insert(0, "/home/claude/effinger-billing-backend/core"); sys.path.insert(0, "/home/claude/effinger-billing-backend/billing/rebill")
import amd, resave
import fix_referring_provider as frp
STAMP = datetime.date.today().isoformat()
def all_open_pids():
    web, tok = amd.login_cached(); end = datetime.date.today(); start = end - datetime.timedelta(days=3 * 365)
    body = {"carrierids": None, "isinsbalance": True, "billstartdate": start.isoformat(), "billenddate": end.isoformat(), "patientids": None, "providerids": None, "facilityids": None, "financialclassids": None, "dateofservicestartdate": None, "dateofserviceenddate": None}
    r = requests.post("https://pm-api-103.advancedmd.com/api/masswriteoff/masswriteoffsearch", json=body, headers={"Authorization": "Bearer " + tok, "Accept": "application/json"}, timeout=180); r.raise_for_status()
    d = r.json(); rows = d.get("chargedetails", []) if isinstance(d, dict) else d
    return sorted(set(str(x["patientid"]) for x in rows if x.get("providerprofilecode") in (None, "", "EFFINGER") or str(x.get("profileid")) in ("13", "prof13")))
if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dry", action="store_true"); ap.add_argument("--max", type=int, default=10**9); a = ap.parse_args()
    amd.login_cached(); pids = all_open_pids(); hits = []
    for pid in pids:
        ref, ins = frp.plans(pid); main = [p for p in ref if p.get("ismain") == "1"]
        if main and main[0].get("refprov") == frp.GARCIA_RPROV: hits.append(pid)
        time.sleep(0.2)
    frp.L(f"sweep {STAMP}: {len(pids)} charts with open balances, {len(hits)} still default to rprov15: {hits[:40]}")
    if a.dry: sys.exit(0)
    for pid in hits[:a.max]:
        ref, ins = frp.plans(pid); mp = [p for p in ref if p.get("ismain") == "1"][0]
        vis = frp.open_visits_on_plan(pid, mp["id"])
        r = amd.post(amd.msg("addreferralplan", "chargeentry", {"nocookie": "1"}, f'<refplan id="" patient="pat{pid}" ismain="1" status="stat1" preauthreq="0" sequence="1" refprov="{frp.EFFINGER_RPROV}" type="I" reason="SELF-REFERRAL" preauth="" begindate="" enddate="" maxvisits="0" usedvisits="0" maxamount="" usedamount="0" proccode="" diagcodes="" facility="{mp.get("facility","")}"/>'))
        m = re.search(r'id="(rplan\d+)"', r); newplan = m.group(1) if m else None
        if not newplan or newplan == mp["id"]: frp.L(f"pat{pid}: no new main plan ({newplan}) - skip"); continue
        frp.L(f"pat{pid}: new main plan {newplan} (rprov13); repointing {len(vis)} open prof13 visits")
        for vid, cids in vis.items():
            v, pat, allc = resave.visit_charges(cids[0]); pre = len(allc); chg = ""
            for c in allc:
                at = {"id": c.get("id")}
                for fld in resave.CHG_FIELDS:
                    if c.get(fld) is not None: at[fld] = c.get(fld)
                chg += "<charge %s/>" % " ".join('%s="%s"' % (k, val) for k, val in at.items())
            va = f'id="{v.get("id")}" date="{v.get("date")}" profile="{v.get("profile")}" insorder="{v.get("insorder")}" refplan="{newplan}" facility="{v.get("facility")}" force="1"'
            rr = amd.post(amd.msg("updvisitwithnewcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": v.get("episode"), "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"}, f"<visit {va}><chargelist>{chg}</chargelist></visit>"))
            if "Fault" in rr: frp.L(f"  v{vid} FAULT {re.sub(chr(10),' ',rr)[:100]}"); continue
            time.sleep(0.6); _, _, post = resave.visit_charges(cids[0]); d = ET_detail = __import__("xml.etree.ElementTree", fromlist=["fromstring"]).fromstring(resave.detail(cids[0])); v2 = d.find(".//visit")
            ok = v2 is not None and v2.get("refplan") == newplan and len(post) == pre
            frp.L(f"  v{vid}: refplan -> {v2.get('refplan') if v2 is not None else '?'} charges {pre}->{len(post)} {'OK' if ok else '** CHECK **'}")
            if not ok: continue
            io = (v2.get("insorder") or "").split(","); mseq = frp.medicaid_seq(ins); vseq = mseq if mseq in io else (io[0] if io else None)
            for c in post:
                if float(c.get("insbalance") or 0) <= 0.005: continue
                amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": re.sub(r"\D", "", v.get("id")), "nocookie": "1"}, f'<extins txtChargeCode="{c.get("proccode")}" resubmissioncode="1" origrefnum="" patsignature="1" emergency="0" epsdt="0" payprov="1" employment="0" autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>'))
                code, _ = amd.rebill_charge(c.get("id"), vseq); frp.L(f"     rebill c{c.get('id')} seq {vseq} -> {code}"); time.sleep(0.3)
            time.sleep(0.4)
