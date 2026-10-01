# PLAIN ENGLISH (read-only, first used run 2026-10-01T2110Z): lists the ERA Center checks DISMISSED on/after a date
# (GET /api/era/checks/dismiss?DismissedDateBegin=YYYY-MM-DD, captured 9/7/2026) so a run can say where a check that left
# the unposted list went. Decides: nothing. Never touches: AMD writes. Reuses the cached token.
#   python3 era_dismissed_read.py 2026-10-01
import era_post, requests, sys, json
day = sys.argv[1] if len(sys.argv) > 1 else "2026-10-01"
r = requests.get(era_post.API + "/era/checks/dismiss", headers=era_post.H(), params={"DismissedDateBegin": day}, timeout=60)
print("HTTP", r.status_code)
try:
    rows = r.json()
    rows = rows if isinstance(rows, list) else rows.get("items", rows)
    for c in rows:
        print({k: c.get(k) for k in ("id", "checknumber", "payername", "checkamount", "unpostedamount", "dismissedat", "dismissedby", "checkdate") if k in c} or c)
    print(len(rows), "dismissed since", day)
except Exception as e:
    print("parse:", e, r.text[:500])
