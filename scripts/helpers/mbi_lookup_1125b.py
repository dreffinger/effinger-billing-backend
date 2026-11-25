#!/usr/bin/env python3
# PLAIN ENGLISH (two Medicare-number cards where William's facesheet carries the SAME number the chart already has - 11/25/2026)
# Decides: nothing. Charts 17476021 and 48458: Medicare rejects the chart's number (AAA 72) and the facesheet William pasted shows that
#   same number, so the number itself is not what Medicare objects to. ONE Medicare look-up each through Stedi (the look-up price):
#   chart 17476021 with the chart's SSN (MBILU - the exact match Medicare keeps), chart 48458 under the spelling the hospital's
#   guarantor block uses (DANIELS) since Medicare matches the name letter for letter. A number that comes back different from the
#   chart's is a candidate for medicare_number_fix (written only when AdvancedMD's free check answers ACTIVE). Answers to
#   patient_db/<pid>/. Never prints an SSN or a full Medicare number. Usage: python3 mbi_lookup_1125b.py
import amd, ins_update, stedi, json, re, os, datetime
import medicare_number_fix as mnf
today = datetime.date.today().strftime("%Y%m%d")
amd.login_cached()
out = {}
for pid, first, last in (("17476021", "JULES", "COPELAND"), ("48458", "CARLOTTA", "DANIELS")):
    raw, plans, order = ins_update._plans(pid)
    pa = dict(re.findall(r'(\w+)="([^"]*)"', re.search(r'<patient [^>]*>', raw).group(0)))
    m, d, y = (pa.get("dob") or "0/0/0").split("/"); ssn = re.sub(r"\D", "", pa.get("ssn") or "")
    cur = [mnf.norm(p.get("subscribernum")) for p in plans.values() if p.get("carrier") == "car6085" and not p.get("enddate")]
    try:
        j = stedi.mbi(first, last, y + m.zfill(2) + d.zfill(2), "FL", today, ssn if len(ssn) == 9 else None, pid=pid)
        os.makedirs("patient_db/%s" % pid, exist_ok=True); json.dump(j, open("patient_db/%s/stedi_mbi_lookup_%s_b.json" % (pid, today), "w"))
        n = mnf.norm((j.get("subscriber") or {}).get("memberId")); errs = [(str(e.get("code")), str(e.get("description"))[:60]) for e in j.get("errors") or []]
        sub = j.get("subscriber") or {}
        res = {"with_ssn": len(ssn) == 9, "name_asked": "%s %s" % (first, last), "found": bool(re.fullmatch(mnf.MBI, n)), "same_as_chart": n in cur, "errors": errs,
               "name_on_record": "%s %s" % (sub.get("firstName", ""), sub.get("lastName", "")), "dod": j.get("subscriber", {}).get("dateOfDeath") or (j.get("planDateInformation") or {}).get("dateOfDeath")}
        if res["found"] and not res["same_as_chart"]: res["candidate_last4"] = n[-4:]
        out[pid] = res; print(pid, res)
    except Exception as e:
        out[pid] = {"error": "%s: %s" % (type(e).__name__, str(e)[:120])}; print(pid, out[pid])
json.dump(out, open("registers/mbi_lookup_2026-11-25T0557Z.json", "w"), indent=1)
