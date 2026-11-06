# PLAIN ENGLISH (Nightly pre-claim eligibility check)
# Decides: For every recent unpaid visit, whether the plan it is billed to was really active on that date of service (Stedi), and proposes the right payer when it was not.
# Rules it uses: Medicare visits use the CMS MBI lookup (also shows Advantage plan / hospice / death); everything else uses the payer's own eligibility. One check per patient+payer+month is cached so nights are cheap. Only reports - never changes a chart or a claim.
# Never touches: AMD writes, claims, balances. Output = precheck_<date>.json + board rows for the exceptions.
# ---
"""Usage: python3 precheck.py [--days 14] [--max 150] [--dry]
Reads the unpaid list (POST /claim/massrebillsearch), keeps visits with DOS in the last --days, and for each patient+carrier
asks Stedi whether that plan was active on the DOS.  Inactive -> MBI lookup / discovery to find the real payer.  Writes
precheck_YYYYMMDD.json and prints a summary.  Cache: precheck_cache.json keyed patient|payer|yyyymm."""
import amd, era_post, stedi, requests, json, re, sys, datetime, time, os
CAR2STEDI = {"FLO02": "MEDICARE", "RET01": "MEDICARE", "UNI20": "87726", "UHCMA": "87726", "AAR01": "87726", "UMR": "87726", "CIPSC": "87726", "HUM01": "61101", "AET07": "60054",
             "CIG09": "62308", "CIG13": "63092", "BCBS": "BCBSF", "SUN01": "68069", "WEL04": "14163", "AMB03": "68069", "SIM01": "SMPLY",
             "CAP07": "95112", "MCAD": "77027", "TRI00": "99727", "TRI05": "99727", "VACCN": "VACCN", "FLO99": None, "PHI01": None}
_cj = json.load(open("carriers.json"))
# code -> carNNNN; accepts BOTH shapes (10/5/2026 fix): rich {carN: [code, name]} and simple {code: carN} - the simple form made every pair flag 'no plan on chart'
CARRIERS = {(v[0] if isinstance(v, (list, tuple)) else k): (k if isinstance(v, (list, tuple)) else v) for k, v in _cj.items()}
def plans(pid):
    r = amd.post('<ppmdmsg action="getdemographic" class="demographics" msgtime="%s" patientid="pat%s" nocookie="1"/>' % (amd._msgtime(), pid))
    p = re.search(r'<patient [^>]*>', r); a = dict(re.findall(r'(\w+)="([^"]*)"', p.group(0))) if p else {}
    pl = re.findall(r'<insplan id="(ins\d+)" carrier="(car\d+)" begindate="([^"]*)" enddate="([^"]*)"[^>]*subscribernum="([^"]*)"[^>]*sequence="(\d+)"', r)
    return a, pl
def main():
    a = sys.argv[1:]; days = int(a[a.index("--days") + 1]) if "--days" in a else 14; mx = int(a[a.index("--max") + 1]) if "--max" in a else 150; dry = "--dry" in a
    amd.login_cached()
    unp = requests.post(era_post.API + "/claim/massrebillsearch", headers=era_post.H(), json={}, timeout=120).json()
    today = datetime.date.today(); stamp = today.strftime("%Y%m%d")
    cache = json.load(open("precheck_cache.json")) if os.path.exists("precheck_cache.json") else {}
    keep = [v for v in unp if (today - datetime.datetime.fromisoformat(v["dateofservice"]).date()).days <= days]
    byp = {}
    for v in keep: byp.setdefault((v["patientid"], v["carriercode"].strip()), []).append(v)
    out = []; n = 0
    for (pid, car), vs in sorted(byp.items(), key=lambda kv: -sum(x["insbalance"] for x in kv[1])):
        if n >= mx: break
        dos = max(v["dateofservice"][:10] for v in vs).replace("-", ""); key = "%s|%s|%s" % (pid, car, dos[:6])
        rec = {"patientid": pid, "patient": vs[0]["patientname"], "carrier": car, "visits": len(vs), "balance": round(sum(x["insbalance"] for x in vs), 2), "dos": dos}
        if key in cache: rec.update(cache[key]); rec["cached"] = True; out.append(rec); continue
        payer = CAR2STEDI.get(car, "UNKNOWN")
        if payer is None: rec["result"] = "no eligibility on Stedi for this payer"; out.append(rec); continue
        if payer == "UNKNOWN": rec["result"] = "carrier not mapped - add to CAR2STEDI"; out.append(rec); continue
        try:
            pa, pl = plans(pid); last, first = (pa.get("name") or vs[0]["patientname"]).split(",")[0].strip(), (pa.get("name") or vs[0]["patientname"]).split(",")[-1].strip().split(" ")[0]
            dob = pa.get("dob", ""); dobc = dob[6:] + dob[:2] + dob[3:5] if dob else ""
            mine = [p for p in pl if p[1] == CARRIERS.get(car)]; member = mine[0][4] if mine else ""
            rec.update({"dob": dob, "member": member})
            if dry: rec["result"] = "DRY"; out.append(rec); continue
            n += 1
            if payer == "MEDICARE":
                j = stedi.mbi(first, last, dobc, pa.get("state") or "FL", dos); m = stedi.med_summ(j)
                rec["mbi"] = m["mbi"]; rec["death"] = m["death"]; rec["partA"] = m["partA"]; rec["partB"] = m["partB"]
                ma = [o for o in m["other"] if o["code"] in ("U", "R") and (o["type"] or "") in ("HN", "HM", "PR", "PS", "IN", "MC", "MD")]
                hosp = [o for o in m["other"] if "45" in json.dumps(o)]
                if m["errors"]: rec["result"] = "not found on Medicare: " + "; ".join(m["errors"])
                elif ma: rec["result"] = "ADVANTAGE PLAN on DOS: " + "; ".join("%s %s" % (e[0], e[1] or "") for o in ma for e in o["entity"]) + " (dates %s)" % json.dumps(ma[0]["dates"])
                elif m["death"]: rec["result"] = "DATE OF DEATH " + m["death"]
                elif member and m["mbi"] and member != m["mbi"]: rec["result"] = "MBI MISMATCH chart %s vs CMS %s" % (member, m["mbi"])
                else: rec["result"] = "OK straight Medicare" + (" (hospice benefit present)" if hosp else "")
            else:
                if not member: rec["result"] = "no %s plan on chart" % car; out.append(rec); continue
                j = stedi.elig(payer, first, last, dobc, member, dos)
                st = (j.get("planStatus") or [{}])[0]; errs = j.get("errors") or []
                if errs: rec["result"] = "payer error: " + "; ".join("%s %s" % (e.get("code"), e.get("description")) for e in errs[:2])
                elif st.get("statusCode") in ("1", "2", "3", "4", "5"): rec["result"] = "OK active - " + (st.get("planDetails") or "") + " " + json.dumps(j.get("planDateInformation") or {})  # X12 EB01 1-5 are all ACTIVE (5 = Active - Pending Investigation; 11/6/2026 fix)
                else:
                    rec["result"] = "INACTIVE on DOS (%s)" % (st.get("status") or "?")
                    try:
                        d = stedi.disc_summ(stedi.disc(first, last, dobc, pa.get("state") or "FL", dos))
                        act = [i for i in d["items"] if (i["status"] or "").startswith("Active")]
                        rec["discovery"] = [(i["payer"], i["member"], i["plan"], i["dates"]) for i in act][:4] or "nothing active found"
                    except Exception as e: rec["discovery"] = "discovery error %s" % str(e)[:80]
            cache[key] = {k: rec[k] for k in rec if k in ("result", "mbi", "death", "partA", "partB", "discovery")}
        except Exception as e:
            rec["result"] = "ERROR " + str(e)[:120]
        out.append(rec); time.sleep(0.3)
    json.dump(cache, open("precheck_cache.json", "w")); json.dump(out, open("precheck_%s.json" % stamp, "w"), indent=1)
    flags = [r for r in out if not str(r.get("result", "")).startswith("OK")]
    print("checked %d patient/payer pairs (%d new lookups); %d flagged" % (len(out), n, len(flags)))
    for r in flags: print("  %-28s %-6s %s  $%-8.2f %s" % (r["patient"][:28], r["carrier"], r["dos"], r["balance"], r.get("result")), ("| " + json.dumps(r["discovery"])[:160]) if r.get("discovery") else "")
if __name__ == "__main__": main()
