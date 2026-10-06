# captured_calls additions - 2026-10-06 2310 UTC (7 PM ET backend billing run, ehpa cloud)

No new call shapes this run (ONE login 23:17Z; reads only: getclaimcenteroverview + the four list calls via columns_scan.py, GET /api/era/checks, GET /api/era/checkdetails?checkid=1052906, massrebillsearch + 21 Stedi 277 claim-status checks via claim_status_sweep.py, precheck.py eligibility reads).

Lesson (TRAP, operational): `python3 era_post.py --help` is not a help flag - era_post.py parses sys.argv for --dry / --carrier / --visits / --all-unposted only, so any other flag runs a LIVE Post pass over the unposted list ("0 checks, dry=False" this run, nothing posted). Learn its options from the header or `grep sys.argv era_post.py`; never probe it with an unknown flag.
