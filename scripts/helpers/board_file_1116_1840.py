# PLAIN ENGLISH (board inbox file for the 1:39 PM ET 11/16 six-hourly columns run, fired 18:39Z): ONE board_updates_<stamp>.json for
#   William's Drive 'board inbox' (the page applies it; no write_db). Decides nothing in AMD. Ops (append-only, built through
#   board_ops.clean_file - no `updated`, no status change): the chart-17472874 card (the two 12/2025 visits William had re-sent Medicare
#   first on 11/2: Medicare paid 11/14, Sunshine's secondary claims rejected 'invalid member' - cost-share written off WOCLTREQ under the
#   10/13 rule, exclusions completed); the standing watch rows aet12-carrier-cpid and availity-remits-backlog with this run's numbers.
# Usage: cd /home/claude/unbilled && python3 board_file_1116_1840.py -> outbox/board_updates_2026-11-16T1840Z.json
import json, datetime
from board_ops import clean_file
STAMP = "2026-11-16T1840Z"; NOW = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"); WHEN = "11/16"
SRC = "1:39 PM ET 11/16 columns run (ehpa cloud, six-hourly slot) - run %s" % STAMP
ops = [
 {"op": "upsert", "collection": "items", "id": "thackeray-kendrew-17472874", "set": {}, "append": {
   "checks": [{"ok": "ok", "src": SRC + " - Exclusions run 1700382", "when": WHEN,
     "result": "Sunshine (SUN01) rejected the two secondary claims 19455319D / 19455320D (99308 12/05 + 12/15/2025) '02 - INVALID MBR'. Live read: Medicare paid 55.97 + 36.75 contractual on each (check 820183876, 11/14/2026), 14.28 cost-share left on each. The chart's Sunshine plan carries 30722106 = the WellCare member id; AMD 271 on it AAA 78; CMS 271 names no Medicaid/QMB (WellCare Part D only); Stedi discovery at DOS 12/05/2025 finds Medicare only. No supplement in force on the DOS -> WOCLTREQ 14.28 x2 ($28.56, 10/13 rule), both visits $0, exclusions completed."}],
   "notes": [{"who": "Claude", "at": NOW, "text": "Medicare paid both December 2025 visits on 11/14; the small coinsurance went to Sunshine, which does not know him (the Sunshine plan on his chart carries his old WellCare number, and Medicare's record shows no Medicaid). Written off as cost-share with no secondary ($28.56); both visits are at $0. Nothing for you here - if he does have a Medicaid number, the Sunshine plan on the chart needs it."}]}},
 {"op": "upsert", "collection": "items", "id": "aet12-carrier-cpid", "set": {}, "append": {"checks": [{"ok": "na", "src": SRC, "when": WHEN,
   "result": "1:39 PM ET 11/16: HOLD - the one AET12 PREF0288 + PREF0264 exclusion row (chart 24750, v19455937, run 1700294, $315) stays on the list, not rebilled; carrier master still unchanged."}]}},
 {"op": "upsert", "collection": "items", "id": "availity-remits-backlog", "set": {}, "append": {"checks": [{"ok": "na", "src": SRC, "when": WHEN,
   "result": "1:39 PM ET 11/16: no new Availity PDF / Check-EFT export / 835 / facesheet (Drive-wide nothing new after 13:01Z except this run's START); Claimocity feed 29 objects, 0 new (newest 20261116); Working Denials queue 0; board drops 0; 0 rows changed since 17:00Z; Pam Gmail: the 11/14 Stout thread only (carded). ERA Center 0 checks $0.00 -> 0 checks $0.00 (engine pass 18:43-18:52Z, 0 errors). Columns 0/1/0/3 -> 0/1/0/1 (Exclusions: chart 17472874 two Sunshine 'invalid member' secondaries settled WOCLTREQ $28.56 + completed; inspector chart 17478413 O24.419 hold; AET12 hold)."}]}},
]
doc = {"schema": "irb-board-updates/1", "source": "backend billing run %s" % STAMP, "created": NOW, "ops": ops}
doc = clean_file(doc)
json.dump(doc, open("outbox/board_updates_%s.json" % STAMP, "w"), indent=1)
print("ops", len(doc["ops"]))
