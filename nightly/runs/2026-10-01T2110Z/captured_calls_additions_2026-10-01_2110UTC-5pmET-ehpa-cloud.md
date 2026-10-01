## 2026-10-01 21:10 UTC (5 PM ET 10/1) backend billing run - ehpa cloud

No new call shapes. One named read-only helper added: `era_dismissed_read.py <YYYY-MM-DD>` wraps the captured
`GET /api/era/checks/dismiss?DismissedDateBegin=<date>` (9/7/2026 capture) so a run can say where a check that left the
unposted list went (10/1: only 1052922 dismissed since 10/1; 1052906 + 1052921 still on GET /api/era/checks).
Lesson: `era_post.py --all-unposted --dry` iterates only checks with unposted money > 0, so its "1 checks" header is not the
ERA Center count - read `era_checks_before_<stamp>.json` (reads_pass.py) for the before/after count and dollars.
