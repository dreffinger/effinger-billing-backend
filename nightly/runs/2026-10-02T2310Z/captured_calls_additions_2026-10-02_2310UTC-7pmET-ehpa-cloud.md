# captured_calls additions - run 2026-10-02T2310Z (7 PM ET 10/2, ehpa cloud)

No new AMD call shapes this run (read-only verification pass: columns_scan.py, GET /api/era/checks, GET /api/era/checkdetails?checkid=1052906, precheck.py). Lesson recorded:

- era_post.locks(checkid, claimids="") needs a numeric check id - calling it with a blank id raises `invalid literal for int()`; POST /api/era/locks/release-expired is per check, so with only the held check 1052906 on the list there is nothing to release.
