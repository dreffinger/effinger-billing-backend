# PLAIN ENGLISH (Exact-date claim status - one 277 per visit, raw answer kept)
# Decides: nothing. Asks the payer (Stedi 276/277) for the status of ONE visit with the exact date of service - the weekly sweep
#   asks with a +/-3-day window, so a daily-visit chart's answer carries its neighbours' payments too (10/9/2026: four $48.34 lines
#   across three checks on a $111 visit). Keeps the raw JSON under claimstatus_raw/<vid>.json and writes a deduplicated summary:
#   payments counted once per (check number, paid date, amount), with the payer's claim number and the patient account number
#   the payer echoes, so a posting can carry the right check.
# Never touches: AMD writes.
"""Usage: python3 claim_status_exact.py --vids <vid,vid,...> | --from-disposition <stamp> [--tiers POST-277,WO-PAID-NOREMIT] [--out claimstatus_exact_<stamp>.json] [--max N]"""
import amd, stedi, precheck, requests, json, sys, os, re, time, datetime, collections
a = sys.argv[1:]
def opt(n, d=None): return a[a.index(n) + 1] if n in a else d
STAMP = opt("--from-disposition", opt("--stamp", "1009")); OUT = opt("--out", "claimstatus_exact_%s.json" % STAMP); MX = int(opt("--max", 10**9))
TIERS = set(opt("--tiers", "POST-277,WO-PAID-NOREMIT").split(","))
STEDI_CS = "https://healthcare.us.stedi.com/2024-04-01/change/medicalnetwork/claimstatus/v2"
os.makedirs("claimstatus_raw", exist_ok=True)
unp = {str(v["visitid"]): v for v in json.load(open("unpaid_%s.json" % datetime.date.today().strftime("%Y%m%d")))}
if "--vids" in a: vids = opt("--vids").split(",")
else:
    D = json.load(open("old_claims_disposition_%s.json" % STAMP)); vids = [r["vid"] for r in D["visits"] if r["tier"] in TIERS]
have = json.load(open(OUT)) if os.path.exists(OUT) else {}
vids = [v for v in vids if v not in have][:MX]
print("exact-date 277 for %d visits (%d already in %s)" % (len(vids), len(have), OUT))
amd.login_cached(); cache = {}
def ask(payer, first, last, dob, member, dos, amount):
    body = {"tradingPartnerServiceId": payer, "providers": [{"npi": "1629515325", "organizationName": "EFFINGER HEALTH PA", "providerType": "BillingProvider"}],
            "subscriber": {"firstName": first, "lastName": last, "dateOfBirth": dob, "memberId": member},
            "encounter": {"beginningDateOfService": dos, "endDateOfService": dos, "submittedAmount": "%.2f" % amount}}
    r = requests.post(STEDI_CS, headers=stedi.H, json=body, timeout=120); return r.status_code, r.json()
def walk(j):
    """Every claimStatus object in the answer, with the claim-level fields beside it."""
    out = []
    for c in j.get("claims") or []:
        cs = c.get("claimStatus") or c; cs = cs if isinstance(cs, list) else [cs]
        lines = [{"cpt": (d.get("service") or {}).get("procedureId"), "paid": (d.get("service") or {}).get("amountPaid"), "charge": (d.get("service") or {}).get("submittedAmount"),
                  "cat": ((d.get("status") or [{}])[0]).get("statusCategoryCode")} for d in (c.get("serviceDetails") or [])]
        for s in cs:
            acct = s.get("patientAccountNumber") or c.get("patientAccountNumber") or ""
            out.append({"cat": s.get("statusCategoryCode"), "catv": (s.get("statusCategoryCodeValue") or "")[:70], "code": s.get("statusCode"), "codev": (s.get("statusCodeValue") or "")[:90],
                        "paid": s.get("amountPaid"), "check": s.get("checkNumber"), "paidDate": s.get("paidDate") or s.get("checkIssueDate") or s.get("effectiveDate"), "checkDate": s.get("checkIssueDate"), "finalized": s.get("adjudicationFinalizedDate"),
                        "payerClaim": s.get("tradingPartnerClaimNumber"), "acct": acct, "svcDate": s.get("claimServiceDate") or s.get("serviceDate"), "charge": s.get("submittedAmount") or s.get("totalClaimChargeAmount"), "lines": lines})
    if not out:
        for s in j.get("claimStatus") or []:
            out.append({"cat": s.get("statusCategoryCode"), "catv": (s.get("statusCategoryCodeValue") or "")[:70], "code": s.get("statusCode"), "codev": (s.get("statusCodeValue") or "")[:90], "paid": s.get("amountPaid"), "check": s.get("checkNumber"),
                        "paidDate": s.get("paidDate") or s.get("checkIssueDate") or s.get("effectiveDate"), "finalized": s.get("adjudicationFinalizedDate"), "payerClaim": s.get("tradingPartnerClaimNumber"), "acct": "", "svcDate": None, "charge": None})
    return out
n = 0
for vid in vids:
    v = unp.get(vid)
    if not v: have[vid] = {"error": "not on tonight's unpaid list"}; continue
    pid = str(v["patientid"]); car = v["carriercode"].strip(); payer = precheck.CAR2STEDI.get(car)
    if pid not in cache: cache[pid] = precheck.plans(pid)
    pa, pl = cache[pid]; nm = pa.get("name") or v["patientname"]; last, first = nm.split(",")[0].strip(), nm.split(",")[-1].strip().split(" ")[0]
    dob = pa.get("dob", ""); dobc = dob[6:] + dob[:2] + dob[3:5] if dob else ""
    mine = [p for p in pl if p[1] == precheck.CARRIERS.get(car)]; member = mine[0][4] if mine else ""
    dos = v["dateofservice"][:10].replace("-", "")
    rec = {"vid": vid, "pid": pid, "carrier": car, "payer": payer, "dos": v["dateofservice"][:10], "balance": v["insbalance"], "amount": v["totalvisitamount"], "icn": v.get("icn")}
    if not payer or not member: rec["error"] = "no payer map / member id"; have[vid] = rec; continue
    try:
        code, j = ask(payer, first, last, dobc, member, dos, v["totalvisitamount"] or v["insbalance"])
        json.dump(j, open("claimstatus_raw/%s.json" % vid, "w"))
        rows = walk(j); rec["http"] = code; rec["rows"] = rows; rec["errors"] = [e.get("code", "") + " " + e.get("description", "") for e in j.get("errors") or []]
        pays = collections.OrderedDict()
        for s in rows:
            amt = float(s.get("paid") or 0)
            if s.get("cat") in ("F0", "F1") and amt > 0:
                k = (s.get("check") or "", s.get("paidDate") or "", "%.2f" % amt); pays.setdefault(k, s)
        rec["payments"] = [{"check": k[0], "date": k[1], "checkDate": s.get("checkDate"), "amount": float(k[2]), "payerClaim": s.get("payerClaim"), "acct": s.get("acct"), "svcDate": s.get("svcDate"), "charge": s.get("charge"), "lines": s.get("lines")} for k, s in pays.items()]
        rec["paid_unique"] = round(sum(p["amount"] for p in rec["payments"]), 2)
        rec["cats"] = sorted({s.get("cat") or "" for s in rows})
        rec["accts"] = sorted({s.get("acct") for s in rows if s.get("acct")})
    except Exception as e: rec["error"] = str(e)[:160]
    have[vid] = rec; n += 1
    json.dump(have, open(OUT, "w"), indent=1)
    print("  v%s %s %s bal %.2f -> cats %s payments %s%s" % (vid, car, rec["dos"], rec["balance"], rec.get("cats"), [(p["amount"], p["check"], p["date"]) for p in rec.get("payments", [])], (" accts " + ",".join(rec["accts"])) if rec.get("accts") else ""))
    time.sleep(0.3)
print("done: %d asked, %d in %s" % (n, len(have), OUT))
