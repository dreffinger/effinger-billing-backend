# PLAIN ENGLISH (Nightly pre-claim eligibility check)
# Decides: For every recent unpaid visit, whether the plan it is billed to was really active on that date of service (Stedi), and proposes the right payer when it was not.
# Rules it uses: Medicare visits use ONE Medicare answer (also shows Advantage plan / hospice / death); everything else uses the payer's own eligibility. One check per patient+payer+month is cached so nights are cheap. Only reports - never changes a chart or a claim.
#   11/10/2026 (look-ups part A): the Medicare answer is asked through stedi.medicare() - a PLAIN Medicare check with the number of the
#   chart's OPEN Medicare plan, the MBI lookup when the chart has no usable number, when Medicare does not know it, or when Medicare
#   refuses the plain check for another reason (41, 61, an answer with no Part A or Part B; after a refusal of OUR provider number the
#   rest of the run skips the plain check) - and is shared with the deceased-patient guard through medicare_store.py for the visit's
#   calendar month (an answer read back from the store is not a new lookup). A Medicare call that failed - this run's own, or another
#   helper's earlier the same day - is never kept in precheck_cache.json for the month: the next night asks again. The result words are
#   the same as before; 'MBI MISMATCH' is raised only on an answer that came from a lookup (in a plain
#   answer the number is only the echo of what was sent), and the Medicare number is not written into precheck_cache.json or
#   precheck_<date>.json when the answer was a plain one. A real argument reader: --help prints and exits; an unknown option is an error
#   and nothing is asked (11/5: a probe started it with a word it did not know and it bought 40 lookups over its 14-day default window).
#   A shared answer is taken only when it was asked about the visit's own calendar month (rule (a) adds an Advantage plan and rebills on
#   what this check says). When the shared answer is a lookup that found the chart's number differs from Medicare's, ONE lookup is bought
#   to read Medicare's number for rule (d) - the store keeps no Medicare number; when Medicare cannot answer that lookup (42, 79, 80) the
#   row says so in the same words and is not kept for the month either (11/10/2026 re-check fix).
# Never touches: AMD writes, claims, balances. Output = precheck_<date>.json + board rows for the exceptions.
# ---
"""Usage: python3 precheck.py [--days 14] [--max 150] [--dry]
Reads the unpaid list (POST /claim/massrebillsearch), keeps visits with DOS in the last --days, and for each patient+carrier
asks Stedi whether that plan was active on the DOS.  Inactive -> MBI lookup / discovery to find the real payer.  Writes
precheck_YYYYMMDD.json and prints a summary.  Cache: precheck_cache.json keyed patient|payer|yyyymm."""
import amd, era_post, stedi, requests, json, re, sys, datetime, time, os, argparse
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
def _open_on(enddate, dos):
    """11/10/2026: a chart plan is open on the date of service when it has no end date or ends on/after it (AMD writes MM/DD/YYYY)."""
    m = re.match(r"(\d\d)/(\d\d)/(\d{4})", enddate or "")
    return not m or m.group(3) + m.group(1) + m.group(2) >= dos
def _month_age(dos):
    """11/10/2026: days back to the first of the visit's month - a Medicare answer asked since then about this month (or later) is reused."""
    return (datetime.date.today() - datetime.date(int(dos[:4]), int(dos[4:6]), 1)).days
def _about_other_month(stored, dos):
    """11/10/2026: True when an answer read back from the store was asked about another calendar month than the visit's (the store also
    serves a later month - right for a date of death, not for which plan pays on this visit's date)."""
    if not isinstance(stored, dict): return False
    about = re.sub(r"\D", "", str(stored.get("dos") or stored.get("asked") or ""))[:6]   # no date of service asked = the day it was asked
    return bool(about) and about != dos[:6]
def main():
    ap = argparse.ArgumentParser(prog="precheck.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    ap.add_argument("--days", type=int, default=14, help="keep visits with a date of service in the last N days (default 14)")
    ap.add_argument("--max", type=int, default=150, help="at most N new checks this run (default 150)")
    ap.add_argument("--dry", action="store_true", help="read the unpaid list and the charts, ask Stedi nothing")
    o = ap.parse_args(); days, mx, dry = o.days, o.max, o.dry          # --help prints and exits; an unknown option is an error - before any call
    stedi.WHO = "pre-claim check"
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
                # 11/10/2026: ONE Medicare answer with the number of the chart's OPEN Medicare plan, shared for the visit's month (see the header)
                mine = sorted(mine, key=lambda p: 0 if _open_on(p[3], dos) else 1); member = mine[0][4] if mine else ""; rec["member"] = member
                ask = {"member_id": member or None, "dos": dos, "state": pa.get("state") or "FL", "pid": pid, "who": "pre-claim check"}
                j, how = stedi.medicare(first, last, dobc, max_age_days=_month_age(dos), **ask)
                if how != "failed" and _about_other_month(j.get("stored"), dos):                 # a shared answer about a LATER month: asked again for this visit's month
                    j, how = stedi.medicare(first, last, dobc, **ask)
                if j.get("stored") and how in stedi.LOOKUP_KINDS and j.get("number_differs"):    # the store keeps no number and rule (d) needs Medicare's: ONE lookup (the store keeps its answer)
                    j, how = stedi.mbi(first, last, dobc, ask["state"], dos, pid=pid), "lookup after plain"
                    if {str(e.get("code")) for e in (j.get("errors") or []) if isinstance(e, dict)} & stedi.MEDICARE_DOWN: how = "failed"   # 42 / 79 / 80: not kept for the month (re-check fix)
                if j.get("stored"): n -= 1                                                        # read back from the store: no new paid call
                if how == "failed" and not j.get("errors"): raise RuntimeError("Medicare check failed (%s)" % j.get("failed"))   # as a failed lookup before: ERROR, nothing cached
                m = stedi.med_summ(j); lookup = how in stedi.LOOKUP_KINDS
                if lookup: rec["mbi"] = m["mbi"] if m["mbi"] or j.get("number_differs") is not False else member
                else: rec.pop("member", None)                                                     # a plain answer: the number was only an echo - written nowhere
                rec["death"] = m["death"]; rec["partA"] = m["partA"]; rec["partB"] = m["partB"]
                ma = [o for o in m["other"] if o["code"] in ("U", "R") and (o["type"] or "") in ("HN", "HM", "PR", "PS", "IN", "MC", "MD")]
                hosp = [o for o in m["other"] if "45" in json.dumps(o)]
                if m["errors"]: rec["result"] = "not found on Medicare: " + "; ".join(m["errors"])
                elif ma: rec["result"] = "ADVANTAGE PLAN on DOS: " + "; ".join("%s %s" % (e[0], e[1] or "") for o in ma for e in o["entity"]) + " (dates %s)" % json.dumps(ma[0]["dates"])
                elif m["death"]: rec["result"] = "DATE OF DEATH " + m["death"]
                elif lookup and member and m["mbi"] and member != m["mbi"]: rec["result"] = "MBI MISMATCH chart %s vs CMS %s" % (member, m["mbi"])
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
            if not (payer == "MEDICARE" and how == "failed"):          # a failed Medicare call (own, or another helper's today) is not kept for the month
                cache[key] = {k: rec[k] for k in rec if k in ("result", "mbi", "death", "partA", "partB", "discovery")}
        except Exception as e:
            rec["result"] = "ERROR " + str(e)[:120]
        out.append(rec); time.sleep(0.3)
    json.dump(cache, open("precheck_cache.json", "w")); json.dump(out, open("precheck_%s.json" % stamp, "w"), indent=1)
    flags = [r for r in out if not str(r.get("result", "")).startswith("OK")]
    print("checked %d patient/payer pairs (%d new lookups); %d flagged" % (len(out), n, len(flags)))
    for r in flags: print("  %-28s %-6s %s  $%-8.2f %s" % (r["patient"][:28], r["carrier"], r["dos"], r["balance"], r.get("result")), ("| " + json.dumps(r["discovery"])[:160]) if r.get("discovery") else "")
if __name__ == "__main__": main()
