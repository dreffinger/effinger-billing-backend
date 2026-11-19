# PLAIN ENGLISH (Stedi coordination-of-benefits check - does this member have ANOTHER health plan, and which one pays first?)
# Decides: Nothing. Asks Stedi's coordination-of-benefits service (POST /coordination-of-benefits, the same account as the eligibility
#   checks) about one member of one payer the patient is known to have, and reads back: the other plans on file, each one's payer name,
#   member number where the answer carries it, and which is primary when the service can tell. Built 11/19/2026 on William's word
#   ("tmh sometimes has had secondaries ... if stedi has that it might be worth looking for that on all of them").
# Rules it uses: it needs a payer the patient HAS and that payer's member number (or the SSN): it finds a SECOND plan, never a first.
#   A paid call - about 1.00 dollar on the 9/2026 statement - so the intake asks it once per chart and keeps the answer in
#   patient_db/<chart>/cob_<day>.json; every call leaves one line in patient_db/stedi_usage.log (kind 'coordination of benefits').
# First use 11/19/2026: a Florida Blue member who also has Medicare answered 'MemberFoundNoCob' - the service does not know Medicare,
#   so it finds a second COMMERCIAL plan, not a Medicare / Medigap pairing (Medicare's own 271 lists those).
# Never touches: AdvancedMD. Not yet in stedi.py or the price table (tools/selftest pins their texts); this helper stands alone.
# Usage: python3 stedi_cob.py <payer id> FIRST LAST YYYYMMDD <member number or -> [YYYYMMDD date of service] [--pid <chart>]
import stedi, requests, json, sys, os, re, datetime
URL = stedi.API + "/coordination-of-benefits"
def _log(payer, pid, code):
    try:
        p = os.environ.get("STEDI_USAGE_LOG") or os.path.join(stedi.HERE, "patient_db", "stedi_usage.log"); os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
        open(p, "a").write("\t".join([datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), os.path.basename(sys.argv[0] or "stedi_cob.py"), "coordination of benefits", str(payer), re.sub(r"\D", "", str(pid or "")) or "-", code, "1.00"]) + "\n")
    except Exception: pass
def cob(payer, first, last, dob, member_id=None, ssn=None, dos=None, pid=None):
    iso = lambda x: ("%s-%s-%s" % (x[:4], x[4:6], x[6:8])) if x and re.fullmatch(r"\d{8}", x) else x      # this endpoint wants YYYY-MM-DD (11/19/2026: YYYYMMDD answers HTTP 400)
    dob = iso(dob); dos = iso(dos)
    sub = {"firstName": first, "lastName": last, "dateOfBirth": dob}
    if member_id: sub["memberId"] = member_id
    if ssn: sub["ssn"] = re.sub(r"\D", "", ssn)
    body = {"tradingPartnerServiceId": payer, "provider": stedi.PROV, "subscriber": sub, "encounter": {"serviceTypeCodes": ["30"]}}
    if dos: body["encounter"]["dateOfService"] = dos
    try:
        r = requests.post(URL, headers=stedi.H, json=body, timeout=130); j = r.json() if r.content else {}
        if r.status_code >= 400 and "errors" not in j: j = {"errors": [{"code": "http %s" % r.status_code, "description": json.dumps(j)[:200]}]}
    except Exception as e:
        _log(payer, pid, "error %s" % type(e).__name__); raise
    errs = j.get("errors") or []; _log(payer, pid, str(errs[0].get("code")) if errs and isinstance(errs[0], dict) else "ok"); return j
def summ(j):
    """Other plans of the answer: [{role, payer, member, begin, end}] + the service's own flags."""
    out = []
    for b in j.get("benefitsInformation") or []:
        for e in b.get("benefitsRelatedEntities") or []:
            d = b.get("benefitsDateInformation") or {}
            out.append({"role": e.get("entityIdentifier"), "payer": e.get("entityName"), "member": e.get("entityIdentificationValue") or (b.get("benefitsAdditionalInformation") or {}).get("memberId") or "",
                        "payer_id": e.get("entityIdentificationValue") if (e.get("entityIdentification") or "").upper() in ("PI", "XV") else "", "dates": d.get("coordinationOfBenefits") or d.get("benefit") or ""})
    seen = []; [seen.append(x) for x in out if x not in seen]
    return {"flags": j.get("coordinationOfBenefits"), "others": seen, "errors": [(e.get("code"), (e.get("description") or "")[:80]) for e in j.get("errors") or []]}
if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    pid = sys.argv[sys.argv.index("--pid") + 1] if "--pid" in sys.argv else None
    j = cob(a[0], a[1], a[2], a[3], None if a[4] == "-" else a[4], dos=a[5] if len(a) > 5 else None, pid=pid)
    if pid:
        d = os.path.join(stedi.HERE, "patient_db", str(pid)); os.makedirs(d, exist_ok=True); json.dump(j, open(os.path.join(d, "cob_%s.json" % datetime.date.today().strftime("%Y%m%d")), "w"))
    print(json.dumps(summ(j), indent=1)[:2500])
