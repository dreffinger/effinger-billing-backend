# captured_calls additions - run 2026-10-03T0710Z (3 AM ET 10/3, ehpa cloud)

No new AMD call shapes this run (read-only verification pass: columns_scan.py before, getclaimcenteroverview after, GET /api/era/checks + checkdetails via era_post, era_post.py --all-unposted --dry, getdemographic on the 11 Unbilled 'insurance order' charts, lookuppatient x6 for the 9/30 admits). Lessons recorded:

- lookuppatient BOYDSTON,OPA% (the admit email names her Opal) returns no chart either - the four 9/30 Pam admits without a chart (JONES / LAWHON / BOYDSTON / WILBOURNE) are still waiting on the Claimocity feed or William's chart creation; a chart created by the feed shows up with the NEXT run's lookup, so the six-name lookup set stays in the read-only pass.
- When two consecutive runs find identical columns, identical chart plans and the same held ERA check, the right output is a run with zero AMD writes: the standing holds are documented on the board and in needs_facesheet_list.md, and re-running bypasses or resaves on them would change nothing.
