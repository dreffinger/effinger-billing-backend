# PLAIN ENGLISH (Is the FEED's member number the right one? 11/20/2026) - READ ONLY in AdvancedMD, a few Stedi eligibility checks.
# Decides: Nothing. For the charts whose own plan AdvancedMD's free check did not confirm, asks the payer about the FEED's number
#          (Stedi, today's date) and lists the chart's open charges at that carrier and any payment that carrier already made
#          (a carrier that has paid on the chart's number proves the chart's number). Screen: chart ids, carriers, answers, dollars.
import amd, ins_update, stedi, txh, json, re, os
amd.login_cached()
PAYER = {"FLO02": "CMS", "UNI20": "87726", "HUM01": "61101", "SUN01": "68069", "AMB03": "68069", "CAP07": "95112", "BCBS": "BCBSF"}
rows = [r for r in json.load(open("in1_mismatch_review_1120.json")) if r["verdict"] == "CHART NOT CONFIRMED"]
out = []
for r in rows:
    pid = r["pid"]; raw, plans, order = ins_update._plans(pid)
    pa = dict(re.findall(r'(\w+)="([^"]*)"', re.search(r'<patient [^>]*>', raw).group(0)))
    last, first = (pa.get("name") or ",").split(",")[:2]; first = first.split()[0]; last = last.split()[0] if last.split()[-1:] and last.split()[-1] in ("JR", "SR", "II", "III", "IV") else last
    m, d, y = pa.get("dob").split("/"); dob = y + m + d
    code = "AMB03" if "AMBETTER" in r["feed_name"].upper() else r["code"]
    chs = [c.attrib for c in txh.fetch(pid).iter("charge") if c.attrib.get("void") != "1"]
    paid_by = sum(1 for c in txh.fetch(pid).iter("charge") for p in c.iter("payment") if p.get("void") != "1" and (p.get("carrier") or "") == r["code"] and abs(float(p.get("amount") or 0)) > 0.005)
    open_here = [c for c in chs if c.get("carrier") == r["code"] and float(c.get("insbal") or 0) > 0.005]
    ans = "no route"
    if code in PAYER:
        try:
            j = stedi.elig(PAYER[code], first, last, dob, re.sub(r"[^A-Za-z0-9]", "", r["feed"]), None, pid=pid) if False else stedi._post(stedi.API + "/change/medicalnetwork/eligibility/v3", {"tradingPartnerServiceId": PAYER[code], "provider": stedi.PROV, "subscriber": {"firstName": first, "lastName": last, "dateOfBirth": dob, "memberId": re.sub(r"[^A-Za-z0-9]", "", r["feed"])}, "encounter": {"serviceTypeCodes": ["30"]}})
            os.makedirs("patient_db/%s" % pid, exist_ok=True); json.dump(j, open("patient_db/%s/stedi_feednumber_%s_1120.json" % (pid, code), "w"))
            errs = [e.get("code") for e in j.get("errors") or []]; act = sorted({b.get("name") for b in j.get("benefitsInformation") or [] if b.get("code") in ("1", "6")})
            plan = sorted({(b.get("planCoverage") or "")[:40] for b in j.get("benefitsInformation") or [] if b.get("code") == "1" and b.get("planCoverage")})[:2]
            ans = "errors %s %s %s dates %s" % (errs, act, plan, json.dumps(j.get("planDateInformation") or {})[:90])
        except Exception as e: ans = "FAILED %s" % str(e)[:80]
    rec = dict(r, feed_code=code, feed_answer=ans, paid_by_carrier=paid_by, open=[(c.get("visit"), c.get("id"), c.get("dos"), c.get("proccode"), c.get("insbal"), c.get("billdate")) for c in open_here])
    out.append(rec)
    print("pat%s %s (feed says %s '%s') chart plan: %s %s | FEED number at the payer: %s | payments this carrier made on the chart: %d | open at this carrier: %d charges $%.2f" % (
        pid, r["code"], code, r["feed_name"], r.get("status"), r.get("aaa") or "", ans, paid_by, len(open_here), sum(float(c.get("insbal")) for c in open_here)))
json.dump(out, open("in1_mismatch_verify_1120.json", "w"))
