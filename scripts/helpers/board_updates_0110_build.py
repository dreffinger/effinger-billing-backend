# PLAIN ENGLISH (board update file builder, 9 PM ET 9/14/2026 slot - ehpa cloud run 2026-09-15T0110Z)
# Decides: nothing on AMD. Writes board_updates_2026-09-15T0110Z.json (Insurance Refresh Board inbox ops):
#   - aet12-carrier-cpid: still no claim run after 1700188 (9/12 21:09 UTC) at 01:12 UTC 9/15; exclusions 0; Standard Professional test undecided.
#   - [name]-17477723: this slot's check line (chart still 0 plans, no facesheet / email / drop).
#   - era-manual-post-0912: this slot's ERA line (idempotent by src+when).
# Never touches: the board directly (no write_db) - the board applies this file when William opens it.
import json, sys, time
stamp = "2026-09-15T0110Z"; now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
era_line = sys.argv[1] if len(sys.argv) > 1 else "ERA step ran - see run report"
src = "9pm ET 9/14 columns run (ehpa cloud)"
ops = [
 {"op": "upsert", "collection": "items", "id": "aet12-carrier-cpid",
  "append": {"checks": [{"ok": "na", "result": "Exclusions column 0 rows. getclaimrunstatus at 01:12 UTC 9/15 still lists 1700188 (9/12 21:09 UTC) as the newest claim run (88 runs) - the 59 AET12 claims re-sent 04:20 UTC 9/14 on the Standard Professional profile have not left yet; PREF0288 answer is read by the first run after the next claim run posts.", "src": src, "when": "9/14"}]}},
 {"op": "upsert", "collection": "items", "id": "[name]-17477723",
  "append": {"checks": [{"ok": "no", "result": "chart still has zero insurance plans; no new file in the hca/tmh/PCC/Claimocity facesheet folders since 9/14 22:30 UTC, Pam Gmail sweep newer_than:2d = 0, no board drop; visits 19454443/19454465 ($421) stay in Unbilled. Still on the 'current face sheets needed' list.", "src": src, "when": "9/14"}]}},
 {"op": "upsert", "collection": "items", "id": "era-manual-post-0912",
  "append": {"checks": [{"ok": "na", "result": era_line, "src": src + " - ERA step 5", "when": "9/14"}]}},
]
doc = {"schema": "irb-board-updates/1", "source": "backend billing run %s" % stamp, "created": now, "ops": ops}
json.dump(doc, open("board_updates_%s.json" % stamp, "w"), indent=1)
print("wrote board_updates_%s.json with %d ops" % (stamp, len(ops)))
