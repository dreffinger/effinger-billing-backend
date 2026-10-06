# PLAIN ENGLISH (Weekly claim-status sweep)
# Decides: For unpaid claims older than N days, what the payer says happened to them (paid / denied / pending / never received) via a Stedi 276/277 check, and sorts them into actions.
# Rules it uses: One check per visit; the payer's answer is recorded, not acted on. Paid-but-unposted = find the ERA; denied = route to the denial cascade; not found = resend as an original claim.
# Never touches: AMD writes, balances, claims. Output = claimstatus_<date>.json + a printed summary by action.
# ---
"""Usage: python3 claim_status_sweep.py [--min-age 45] [--max 100] [--carriers UNI20,BCBS,...]
Reads the unpaid list (massrebillsearch), keeps visits with DOS older than --min-age days on the chosen carriers,
asks the payer for status with the patient's chart member id, and writes claimstatus_YYYYMMDD.json."""
import amd, era_post, stedi, requests, json, re, sys, datetime, time, os
from precheck import CAR2STEDI, CARRIERS, plans
STEDI_CS = "https://healthcare.us.stedi.com/2024-04-01/change/medicalnetwork/claimstatus/v2"
def status(payer, first, last, dob, member, dos, amount):
    d = datetime.datetime.strptime(dos, "%Y%m%d").date()
    body = {"tradingPartnerServiceId": payer, "providers": [{"npi": "1629515325", "organizationName": "EFFINGER HEALTH PA", "providerType": "BillingProvider"}],
            "subscriber": {"firstName": first, "lastName": last, "dateOfBirth": dob, "memberId": member},
            "encounter": {"beginningDateOfService": (d - datetime.timedelta(days=3)).strftime("%Y%m%d"), "endDateOfService": (d + datetime.timedelta(days=3)).strftime("%Y%m%d"), "submittedAmount": "%.2f" % amount}}
    r = requests.post(STEDI_CS, headers=stedi.H, json=body, timeout=120); return r.status_code, r.json()
def summarize(j):
    out = []
    for c in j.get("claims") or []:
        cs = c.get("claimStatus") or c; cs = cs if isinstance(cs, list) else [cs]
        for s in cs:
            out.append({"cat": s.get("statusCategoryCode"), "catv": s.get("statusCategoryCodeValue"), "code": s.get("statusCode"), "codev": s.get("statusCodeValue"),
                        "paid": s.get("amountPaid"), "check": s.get("checkNumber"), "paidDate": s.get("paidDate") or s.get("effectiveDate"), "payerClaim": s.get("tradingPartnerClaimNumber")})
    if not out:
        for s in j.get("claimStatus") or []: out.append({"cat": s.get("statusCategoryCode"), "catv": s.get("statusCategoryCodeValue"), "code": s.get("statusCode"), "codev": s.get("statusCodeValue"), "paid": s.get("amountPaid"), "check": s.get("checkNumber"), "paidDate": s.get("paidDate") or s.get("effectiveDate"), "payerClaim": s.get("tradingPartnerClaimNumber")})
    return out, [e.get("code", "") + " " + e.get("description", "") for e in j.get("errors") or []]
def action(rows, errs):
    cats = {r["cat"] for r in rows}
    if errs and not rows: return "ERROR"
    if cats & {"F0", "F1"}:
        paid = sum(float(r["paid"] or 0) for r in rows if r["cat"] in ("F0", "F1"))
        return ("PAID $%.2f - find/post the ERA (check %s)" % (paid, ",".join(sorted({r["check"] for r in rows if r["check"]})[:3]))) if paid > 0 else "FINALIZED $0 - denial, run the cascade"
    if cats & {"F2", "F3", "F4"}: return "DENIED/REVISED - run the denial cascade"
    if cats & {"A0", "A1", "A2", "A5", "P0", "P1", "P2", "P3", "P4", "P5"}: return "PENDING at payer - wait"
    if cats & {"A3", "A4", "A6", "A7", "A8", "E0", "E1", "E2", "E3", "E4", "D0"}: return "NOT ON FILE / rejected - resend as original"
    return "UNKNOWN - review"
def main():
    a = sys.argv[1:]; minage = int(a[a.index("--min-age") + 1]) if "--min-age" in a else 45; mx = int(a[a.index("--max") + 1]) if "--max" in a else 100
    cars = a[a.index("--carriers") + 1].split(",") if "--carriers" in a else ["UNI20", "BCBS", "HUM01", "AET07", "SUN01", "WEL04", "CAP07", "SIM01", "CIG09", "CIG13"]
    # --skip-answered <claimstatus json>[,<json>...] (10/6/2026): visits an earlier sweep already answered with a FINAL status (PAID / FINALIZED /
    # DENIED / NOT ON FILE) are not asked again - only PENDING / ERROR / UNKNOWN rows and never-asked visits cost a new 277.
    skip = set()
    if "--skip-answered" in a:
        for fn in a[a.index("--skip-answered") + 1].split(","):
            for r in json.load(open(fn)):
                act = r.get("action") or ""
                if act.startswith(("PAID", "FINALIZED", "DENIED", "NOT ON FILE")): skip.add(str(r.get("visitid")))
        print("skipping %d visits already answered" % len(skip))
    amd.login_cached(); today = datetime.date.today(); stamp = today.strftime("%Y%m%d")
    unp = requests.post(era_post.API + "/claim/massrebillsearch", headers=era_post.H(), json={}, timeout=120).json()
    keep = [v for v in unp if v["carriercode"].strip() in cars and (today - datetime.datetime.fromisoformat(v["dateofservice"]).date()).days >= minage and str(v["visitid"]) not in skip]
    keep.sort(key=lambda v: -v["insbalance"]); out = []; cache = {}
    for v in keep[:mx]:
        pid = v["patientid"]; car = v["carriercode"].strip(); payer = CAR2STEDI.get(car)
        if pid not in cache: cache[pid] = plans(pid)
        pa, pl = cache[pid]; nm = pa.get("name") or v["patientname"]; last, first = nm.split(",")[0].strip(), nm.split(",")[-1].strip().split(" ")[0]
        dob = pa.get("dob", ""); dobc = dob[6:] + dob[:2] + dob[3:5] if dob else ""
        mine = [p for p in pl if p[1] == CARRIERS.get(car)]; member = mine[0][4] if mine else ""
        rec = {"visitid": v["visitid"], "patientid": pid, "patient": v["patientname"], "carrier": car, "dos": v["dateofservice"][:10], "balance": v["insbalance"], "member": member, "icn": v.get("icn")}
        if not payer or not member: rec["action"] = "SKIP - no payer map / member id"; out.append(rec); continue
        try:
            code, j = status(payer, first, last, dobc, member, v["dateofservice"][:10].replace("-", ""), v["totalvisitamount"] or v["insbalance"])
            rows, errs = summarize(j); rec["status"] = rows; rec["errors"] = errs; rec["action"] = action(rows, errs)
        except Exception as e: rec["action"] = "ERROR " + str(e)[:100]
        out.append(rec); time.sleep(0.3)
    json.dump(out, open("claimstatus_%s.json" % stamp, "w"), indent=1)
    from collections import Counter
    print("checked %d claims; by action:" % len(out))
    for k, n in Counter(r["action"] for r in out).most_common(): print("  %3d  %s" % (n, k))
    for r in out[:40]: print("   ", r["patient"][:24], r["carrier"], r["dos"], "$%.2f" % r["balance"], "->", r["action"], "|", (r.get("status") or [{}])[0].get("codev", "") if r.get("status") else (r.get("errors") or [""])[0][:80])
if __name__ == "__main__": main()
