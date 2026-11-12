# captured_calls additions - nightly cascade 2026-11-12T0329Z

No new AMD or Stedi call shapes were learned tonight (vocabulary +0). Calls used: massrebillsearch (unpaid list, via precheck.py), getdemographic (precheck --dry chart reads), ERA Center GET /api/era/checks (empty), NPPES registry API (cred_check). Postman: unchanged.

Lesson (no call shape): the nightly cascade fired at 03:29Z instead of its 05:35Z slot; the unpaid list's newest date of service was 11/8, so `precheck.py --days 3` had nothing to ask. No nightly cascade digest exists for 11/11 (nightly/runs newest = 2026-11-10T0535Z).
