#!/usr/bin/env python3
# PLAIN ENGLISH (chart 48458 / 17469674 / 17472573 - one Medicare look-up WITH the Social Security number, 11/25/2026 press 09:03Z)
# Decides: nothing. William's 3:26 AM paste of the facility's payer history shows hospice from 6/4/2025 and a 'STOP BILLING' line on
#   12/24/2025; the chart's Medicare number answers 72 on AdvancedMD's free check (11/20, 11/25 x2) and the look-up by name + birth
#   date answered 75 twice. The standing cascade's step 2 is the look-up WITH the chart SSN (MBILU, $1.00) - chart 17469674 (same
#   person, same birth date) holds the SSN; this asks Medicare ONCE that way, dated to the open visit (11/03/2025), and prints the
#   picture: Medicare number (masked), Part A/B, date of death, hospice / other payers. The deceased guard records a date of death
#   for chart 48458 by itself (stedi's hook). Nothing on any chart changes here.
# Never touches: AMD writes. The SSN is read from the chart and never printed or stored. Usage: python3 danvers_medicare_1018.py
import amd, stedi, re, json
import xml.etree.ElementTree as ET
amd.login_cached()
d = ET.fromstring(amd.post(amd.msg("getdemographic", "demographics", {"patientid": "17469674", "nocookie": "1"})))
p = d.find(".//patient"); ssn = re.sub(r"\D", "", p.get("ssn") or ""); dob = p.get("dob") or ""
name = (p.get("name") or "").split(",")
last = name[0].strip(); first = name[1].strip().split()[0] if len(name) > 1 else ""
m = re.match(r"(\d{2})/(\d{2})/(\d{4})", dob); dob8 = m.group(3) + m.group(1) + m.group(2) if m else dob.replace("-", "")
print("asking Medicare (MBILU, with the SSN) for %s***, %s*** dob [DOB] ssn %s digits, dos 20251103" % (last[:3], first[:2], len(ssn)))
stedi.WHO = "danvers_medicare_1018"
j = stedi.mbi(first, last, dob8, dos="20251103", ssn=ssn, pid="48458")
s = stedi.med_summ(j)
mbi = s.get("mbi"); s["mbi"] = (mbi[:2] + "*******" + mbi[-2:]) if mbi else None
s["name"] = None; s["dob"] = None; s["address"] = None
print(json.dumps(s, indent=1)[:3000])
errs = j.get("errors") or []
print("errors:", [(e.get("code"), (e.get("description") or "")[:60]) for e in errs][:5])
# the plan-level picture: benefits with hospice / MA entity / other payers
for b in (j.get("benefitsInformation") or [])[:60]:
    txt = " ".join(str(x) for x in [b.get("code"), b.get("name"), b.get("insuranceTypeCode"), b.get("insuranceType"), b.get("planCoverage"), b.get("benefitsDateInformation")])
    ents = [(e.get("entityName"), e.get("entityIdentifier")) for e in (b.get("benefitsRelatedEntities") or [])]
    if any(k in txt.upper() for k in ("HOSPICE", "ACTIVE", "INACTIVE", "DEATH", "ADVANTAGE", "HN", "PART A", "PART B", "QM")) or ents:
        print("  benefit:", txt[:200], ents)
