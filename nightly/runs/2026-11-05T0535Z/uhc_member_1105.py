# PLAIN ENGLISH (one-night helper, 11/5/2026 nightly cascade)
# Decides: nothing. Runs ONE Stedi payer-eligibility call (UHC 87726) and prints the subscriber block (member id as the
#   payer carries it), plan dates and the plan/entity names, so an Advantage plan found on Medicare's record can be
#   added to the chart with the payer's own member number.
# Never touches: AMD, the chart, claims.
"""Usage: python3 uhc_member_1105.py <payer> <FIRST> <LAST> <yyyymmdd> <memberid-or-MBI> <dos>"""
import stedi, json, sys
a = sys.argv[1:]
j = stedi.elig(a[0], a[1], a[2], a[3], a[4], a[5])
out = {"subscriber": j.get("subscriber"), "planDateInformation": j.get("planDateInformation"), "planStatus": (j.get("planStatus") or [])[:2],
       "payer": j.get("payer"), "errors": j.get("errors"),
       "plans": sorted({(x.get("insuranceTypeCode") or "") + " " + (x.get("planCoverage") or "") for x in j.get("benefitsInformation") or [] if x.get("planCoverage")})[:6],
       "entities": [{"name": e.get("entityName"), "id": e.get("entityIdentificationValue"), "type": e.get("entityIdentifierValue")}
                    for x in j.get("benefitsInformation") or [] for e in x.get("benefitsRelatedEntities") or []][:6]}
print(json.dumps(out, indent=1))
