## 2026-10-01 23:10 UTC (7 PM ET 10/1) backend billing run - ehpa cloud

No new call shapes, no new helpers. Reads only: getclaimcenteroverview + the four list calls (columns_scan.py), GET /api/era/checks
+ checkdetails (reads_pass.py), lookuppatient x5 (the four 9/30 admits still have no chart; the 10/1 Brynwood admit resolves to
pat17477953), era_post.py --all-unposted --dry (0 postable / 14 skipped), precheck.py --days 3 --max 120 (1 pair, 0 flagged).
Nothing written to AdvancedMD. Columns 0/21/33/0 unchanged; ERA 2 checks $149.48 unchanged; approvals A-2026-10-01T1110Z-A1/A2/A3
still unanswered (Gmail thread 1a0f741c8df8f617 has no reply; Working Denials queue empty).
