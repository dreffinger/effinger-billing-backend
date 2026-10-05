# captured_calls additions - 2026-10-05T2310Z (7 PM ET 10/5 backend billing run, ehpa cloud)
No new AMD or Stedi call shapes this run (reads only: getclaimcenteroverview, getreviewcharges, getclaiminspectorbatches/charges, getclaimunbillablecharges, getclaimrunstatus, getclaimexclusioncharges, GET /api/era/checks, GET /api/era/checkdetails; era_post --dry).

## Lesson (helper, not a call): precheck.py carrier map shape
- bootstrap_workspace.sh layout derives carriers.json in the SIMPLE form (code -> carN) from practices/ehpa/carriers.json, while precheck.py built its code->carN map with `{v[0]: k ...}` from the RICH form (carN -> [code, name]). On the simple form v[0] is the letter 'c', so no carrier ever matched and every pair flagged 'no <carrier> plan on chart' (12 of 13 flags on 10/5 2310Z; the 9/18 '7 precheck plan-match misses' were the same defect). precheck.py now accepts both shapes. Re-run: 2 informational flags only.
- Still open in CAR2STEDI: FIR07 (no Stedi payer id mapped); FLO99 (FCC) has no Stedi eligibility - both report-only.
