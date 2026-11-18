# PLAIN ENGLISH (board inbox file for the 7:39 PM ET 11/17 evening columns run, fired 00:40Z 11/18): ONE board_updates_<stamp>.json for
#   William's Drive 'board inbox' (the page applies it; no write_db). Decides nothing in AMD. Append-only ops (no set of status/need/updated):
#   - orwell-padraig-denials (chart 44953, same work item): Humana NO-PAY 202611160007235 (ERA 1053558) CO-16/M76 on three 99233s -> the
#     F01.50-primary cascade deleted F01.50 on 12 open visits and re-sent them as originals.
#   - chp-pr242-check-4131654: the engine's inspector pass bypassed two advisories on v19442338 / v19423586 (two of the card's PR-242 visits).
#   - standing watch rows aet12-carrier-cpid and availity-remits-backlog.
# Usage: cd /home/claude/unbilled && python3 board_file_1118_0040.py -> outbox/board_updates_2026-11-18T0040Z.json
import json, datetime, os
from board_ops import clean_file
STAMP = "2026-11-18T0040Z"; NOW = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"); WHEN = "11/17"
SRC = "7:39 PM ET 11/17 columns run (ehpa cloud, evening slot) - run %s" % STAMP
def app(i, checks=None, notes=None):
    a = {}
    if checks: a["checks"] = checks
    if notes: a["notes"] = notes
    return {"op": "upsert", "collection": "items", "id": i, "set": {}, "append": a}
ops = [
 app("orwell-padraig-denials",
     checks=[{"ok": "ok", "src": "ERA 1053558 Humana NO-PAY 202611160007235 + dx_primary_fix.py 44953 --bad F01.50 - " + SRC, "when": WHEN,
              "result": "Humana CO-16/M76 on v19461026 / v19461052 / v19461072 (99233 11/9-11/11, $480): F01.50 (code-first vascular dementia) was the primary dx. Cascade = DELETE F01.50 (J06.9 now leads); the same fix on every other open visit of the chart whose primary was F01.50 (9 more: v19457092, v19460190, v19460529, v19460677, v19461125, v19461227, v19461250, v19461280, v19461434). 12 visits (~$2,343) resaved, frequency 1 + rebill -> 204."}],
     notes=[{"who": "Claude", "at": NOW, "text": "Humana denied three November hospital visits for the diagnosis order again (F01.50 first - the 9/14 ZY3 problem). F01.50 removed on all 12 open visits that led with it and re-sent; the Claimocity feed is still sending F01.50 first on this chart."}]),
 app("chp-pr242-check-4131654",
     checks=[{"ok": "na", "src": SRC + " - engine inspector pass", "when": WHEN,
              "result": "v19442338 (chart 46678 5/17/2026 CCM) and v19423586 (chart 48008 11/15/2025 CCM) re-entered the Claim Inspector after the 11/17 move-back; the engine bypassed their advisories, so they may go out to CHP again on the next claim run. Your decision on the card stands."}]),
 app("aet12-carrier-cpid", checks=[{"ok": "na", "src": SRC, "when": WHEN,
   "result": "7:39 PM ET 11/17: HOLD - the one AET12 PREF0288 + PREF0264 exclusion row (chart 24750, v19455937, run 1700294, $315) stays on the list, not rebilled; carrier master still unchanged (getclaimexclusionclaimruns: 1 run, 1 row)."}]),
 app("availity-remits-backlog", checks=[{"ok": "na", "src": SRC, "when": WHEN,
   "result": "7:39 PM ET 11/17: no new Availity PDF / Check-EFT export / 835 / facesheet (Drive watched folders: nothing new after 18:30Z except the 18:40Z run's own files); Claimocity feed 30 objects, 0 new (newest 20261117); retry-dx: 1 visit still waits on S82.843D; feed order sweep 51 visits / 27 charts unchanged, 0 checks bought, 0 saved; Working Denials queue 0; board drops 0; Pam Gmail nothing in 2 days. ERA Center 5 checks $932.19 -> 0 (engine Post button; 18 Sunshine dual residuals 9.71 settled WOCAID2ND $174.78). Columns 0/3/0/1 -> 0/1/0/1. 'current face sheets needed' email sent (20 charts, $9,227)."}]),
]
doc = clean_file({"schema": "irb-board-updates/1", "source": "backend billing run %s" % STAMP, "created": NOW, "ops": ops})
os.makedirs("outbox", exist_ok=True)
json.dump(doc, open("outbox/board_updates_%s.json" % STAMP, "w"), indent=1)
print("ops", len(doc["ops"]), [o["id"] for o in doc["ops"]])
