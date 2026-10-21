#!/usr/bin/env python3
# PLAIN ENGLISH (dismissed $0 remit read-back, 9 AM ET 10/21/2026 run 2026-10-21T1310Z): the GitHub Billing Button slot #126 dismissed
#   the new $0 Optum VA CCN remit (ERA check 1053239, trace 3680200143) at 13:29:45Z before any run cached its claim lines, and
#   GET /api/era/checkdetails answers 0 rows for a dismissed check. This helper RESTORES the check (POST /api/era/checks/reversedismiss,
#   body [{"id": <checkid>, "dismissedat": <value from GET /api/era/checks/dismiss>}] - the captured 9/4-9/7 shape), reads its claim lines
#   (GET /api/era/checkdetails?checkid=), caches them to era_details/<checkid>.json AND era_details_prepost/<checkid>.json, and - because
#   the remit carries no money (every line $0) - DISMISSES it again (POST /api/era/checks/dismiss, the id as a JSON string) so the unposted
#   list is left as the slot left it. The $0 lines are then worked under the denial rules by the run (never written off here).
# Decides: nothing about the claims. Writes: reversedismiss + dismiss on this ONE check. --dry (default) = reads only and prints the plan.
# Usage: python3 era_restore_1021_1310.py [--live]
import amd, era_post, json, sys, os, time, requests
CHECK = "1053239"; LIVE = "--live" in sys.argv; STAMP = "2026-10-21T1310Z"
amd.login_cached()
dis = amd.rest_get("/api/era/checks/dismiss?DismissedDateBegin=2026-10-21"); dis = json.loads(dis) if isinstance(dis, str) else dis
rows = dis if isinstance(dis, list) else (dis.get("items") or dis.get("checks") or [])
row = next((x for x in rows if str(x.get("id") or x.get("checkid")) == CHECK), None)
print("dismissed row:", json.dumps(row)[:400] if row else None)
if not row: print("check not on the dismissed list - nothing to do"); sys.exit(0)
dat = row.get("dismissedat") or row.get("dismisseddate") or row.get("dismissedAt")
print("plan: reversedismiss", CHECK, "dismissedat", dat, "-> checkdetails -> cache -> dismiss again")
if not LIVE: print("DRY - no write"); sys.exit(0)
r = requests.post(era_post.API + "/era/checks/reversedismiss", headers=era_post.H(), data=json.dumps([{"id": int(CHECK), "dismissedat": dat}]), timeout=60)
print("reversedismiss HTTP", r.status_code, r.text[:200]); time.sleep(2)
d = era_post.details(int(CHECK)); n = len(d.get("eracheckdetails") or []) if isinstance(d, dict) else 0
print("checkdetails rows:", n)
os.makedirs("era_details_prepost", exist_ok=True)
json.dump(d, open("era_details/%s.json" % CHECK, "w"), indent=1); json.dump(d, open("era_details_prepost/%s.json" % CHECK, "w"), indent=1)
money = sum(float(c.get("paidamount") or c.get("paid") or 0) for c in (d.get("eracheckdetails") or []) for c in [c]) if isinstance(d, dict) else 0
print("money on the lines:", money)
if n and money == 0:
    r2 = requests.post(era_post.API + "/era/checks/dismiss", headers=era_post.H(), data=json.dumps(CHECK), timeout=60)
    print("dismiss again HTTP", r2.status_code, r2.text[:200])
else:
    print("NOT re-dismissed (no rows read, or money present) - left on the unposted list for the ERA step")
lst = era_post.checks(); print("unposted now:", len(lst) if hasattr(lst, "__len__") else lst)
json.dump({"stamp": STAMP, "check": CHECK, "rows": n, "money": money, "redismissed": bool(n and money == 0)}, open("registers/era_restore_%s.json" % STAMP, "w"), indent=1)
