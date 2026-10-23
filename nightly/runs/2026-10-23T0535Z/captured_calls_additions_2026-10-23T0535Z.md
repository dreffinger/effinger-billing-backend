# captured_calls additions - nightly cascade 2026-10-23T0535Z (1:30 AM ET 10/23/2026)

No new AMD or Stedi call shapes captured this run. Calls used, all already in the registry: AMD login (one attempt, POI0712, 05:43Z), `POST /claim/massrebillsearch` with `{}` (unpaid list, via precheck.py and the read-only unpaid_peek_1023.py), `GET /api/era/checks` (via era_post.py / era_clear.py), Stedi `GET /payers/search` (credential self-check only). 0 vocabulary entries added.

Operational notes for the registry:
- The unpaid list's newest date of service is 10/13/2026 on 10/23 (60 visits 8-14 days old, none under 8): the Claimocity charge feed runs ~10 days behind, so precheck.py `--days 3` has found 0 pairs on every nightly since 10/18. A `--days 14` window would have covered ~60 pairs tonight (cached after the first night).
- Fresh container: pip/pip3 belong to python3.13 while /usr/local/bin/python3 is 3.11 - `python3 -m pip install requests openpyxl` is the install that the helpers see (nightly_bootstrap.sh's `pip install -q openpyxl` lands in the wrong interpreter).
- void_rules.py was refused by the permission classifier ([Modify Shared Resources]) and not retried; listed for William in the run report.
- cred_check.py: NPPES answered (3 records, 0 changes); data.cms.gov (revalidation list) and oig.hhs.gov (LEIE) still refuse from this container ('Max retries exceeded').
