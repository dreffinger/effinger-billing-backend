# PLAIN ENGLISH (read the lines of an ERA check that was dismissed before its details were cached - written 10/1/2026 run
#   2026-10-01T0510Z; the 9/19 recipe from captured_calls.md: GET /api/era/checks/dismiss?DismissedDateBegin= lists the dismissed
#   checks with their dismissedat stamp, POST /api/era/checks/reversedismiss brings ONE check back to the unposted list so
#   GET /api/era/checkdetails answers again, the details are cached to era_details/<checkid>.json, and POST /api/era/checks/dismiss
#   puts the check back where it was). Needed because era_clear dismisses a denial-only check the moment it sees it, and a check
#   that lands between the run's list read and the clear pass has no cached lines for the denial handling.
# Decides: nothing about the lines - it only reads them. Refuses to re-dismiss when the check still carries unposted money
#   (unpostedamount > 0 after the restore) and says so.
# Never touches: payments, write-offs, visits, any other check.
#   python3 era_read_dismissed.py <checkid> [--since YYYY-MM-DD]          # dry: shows whether the check is in the dismissed list
#   python3 era_read_dismissed.py <checkid> [--since YYYY-MM-DD] --live   # restore -> cache details -> dismiss again; register registers/era_read_dismissed_<stamp>.json
import amd, era_post, payreasons, json, sys, os, time, datetime, requests
a = sys.argv[1:]; cid = a[0]; LIVE = "--live" in a
since = a[a.index("--since") + 1] if "--since" in a else (datetime.date.today() - datetime.timedelta(days=3)).isoformat()
stamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H%MZ"); os.makedirs("registers", exist_ok=True); os.makedirs("era_details", exist_ok=True)
amd.login_cached()
r = requests.get(era_post.API + "/era/checks/dismiss", params={"DismissedDateBegin": since}, headers=era_post.H(), timeout=60)
idx = {str(x["id"]): x for x in (r.json() if r.status_code == 200 else [])}
x = idx.get(str(cid))
rec = {"stamp": stamp, "live": LIVE, "checkid": cid, "since": since, "in_dismissed_list": bool(x), "dismissedat": (x or {}).get("dismissedat"), "paymentnumber": (x or {}).get("paymentnumber")}
if not x:
    rec["result"] = "not in the dismissed list since %s - nothing done" % since; print(json.dumps(rec)); sys.exit(1)
if not LIVE:
    rec["result"] = "dry: would reversedismiss, cache era_details/%s.json, then dismiss again" % cid; print(json.dumps(rec)); sys.exit(0)
r2 = requests.post(era_post.API + "/era/checks/reversedismiss", headers=era_post.H(), data=json.dumps([{"id": int(cid), "dismissedat": x["dismissedat"]}]), timeout=60)
rec["reversedismiss"] = "HTTP %s %s" % (r2.status_code, r2.text[:120])
if r2.status_code != 200: print(json.dumps(rec)); sys.exit(2)
time.sleep(1.5)
det = era_post.details(cid); n = len(det.get("eracheckdetails") or [])
json.dump(det, open("era_details/%s.json" % cid, "w"), indent=1); rec["claims_cached"] = n
live = {str(c["id"]): c for c in era_post.checks()}; c = live.get(str(cid)) or {}
rec["unpostedamount_after_restore"] = c.get("unpostedamount")
if float(c.get("unpostedamount") or 0) > 0:
    rec["result"] = "RESTORED and cached, NOT re-dismissed: the check carries unposted money - era_post / era_fallback handle it"
else:
    ok, txt = era_post.dismiss(cid) if hasattr(era_post, "dismiss") else payreasons.redismiss(cid) or (True, "redismiss")
    rec["dismiss_again"] = txt if isinstance(txt, str) else str(txt); rec["result"] = "restored, %d claim(s) cached, dismissed again (%s)" % (n, "ok" if ok else "DISMISS FAILED - check is back on the unposted list")
print(json.dumps(rec)); open("registers/era_read_dismissed_%s.json" % stamp, "a").write(json.dumps(rec) + "\n")
