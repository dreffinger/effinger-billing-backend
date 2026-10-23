# PLAIN ENGLISH (board update file builder, 11 PM ET 10/18/2026 slot - ehpa cloud run 2026-10-19T0310Z)
# Decides: nothing on AMD. Writes board_updates_2026-10-19T0310Z.json (Insurance Refresh Board inbox ops) - this slot's
#   check line on the standing rows: the three zero-plan HCA charts (17478059 / 17478063 / 17478064), the AET12 carrier
#   hold (chart 24750), chart 17470713's AARP secondaries, and the availity-remits-backlog run line. Appends only, never set.
# Never touches: the board directly (no write_db) - the board applies this file when William opens it.
import json, time
stamp = "2026-10-19T0310Z"; now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
src = "11pm ET 10/18 columns run (ehpa cloud) - run 2026-10-19T0310Z"; when = "10/18"
hca = "11 PM ET 10/18: getdemographic 03:2xZ - chart still has zero insurance plans; no new file in the hca/tmh/PCC/Claimocity folders after 20:00Z 10/18, Pam Gmail (6d) nothing for this chart, no board drop; the two visits (99223 10/12 + 99232 10/13/2026, $421) stay in Unbilled 'Insurance order is missing'. HCA facesheet (admit 10/12/2026) still needed."
ops = [
 {"op": "upsert", "collection": "items", "id": i, "append": {"checks": [{"ok": "no", "result": hca, "src": src, "when": when}]}}
 for i in ("maddern-digby-[first]-17478059", "[name]-17478063", "edgerton-jocelyn-17478064")]
ops += [
 {"op": "upsert", "collection": "items", "id": "aet12-carrier-cpid",
  "append": {"checks": [{"ok": "na", "result": "11 PM ET 10/18: HOLD - the one AET12 PREF0288 exclusion row (chart 24750, v19455937) stays on the list, not rebilled; chart plans unchanged (FLO02 seq 1, AET12 seq 2); carrier master still unchanged.", "src": src, "when": when}]}},
 {"op": "upsert", "collection": "items", "id": "poulter-ellery-gwen-denials",
  "append": {"checks": [{"ok": "na", "result": "11 PM ET 10/18: the 25 AARP (AAR01 seq 4) secondary rejections on claim run 1700302 ('returned as unprocessable') stay on the Exclusions list - chart plans unchanged (BCBS1 ended 3/31/2026, Medicare seq 3, AAR01 seq 4 with the rejected 9-digit id); nothing re-sent. Still waiting on the AARP Medicare Supplement member number.", "src": src, "when": when}]}},
 {"op": "upsert", "collection": "items", "id": "availity-remits-backlog",
  "append": {"checks": [{"ok": "na", "result": "11 PM ET 10/18: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (Drive: nothing modified in the seven watched folders after 20:00Z 10/18 outside the routine's own files); no new 835, facesheet or Claimocity file; Working Denials queue 0; board drops 0; approvals 0 approved / 0 waiting; Pam Gmail: nothing newer than the 10/17 Aviata readmit (worked). ERA Center 0 checks before and after. Columns 0/0/6/26 -> 0/0/6/26 - every row a standing hold (three zero-plan HCA charts 17478059 / 17478063 / 17478064, chart 17470713's 25 AARP secondaries on run 1700302, AET12 chart 24750), no AMD write this slot. The three 10/15 Pam admits still have no AMD chart.", "src": src, "when": when}]}},
]
doc = {"schema": "irb-board-updates/1", "source": "backend billing run %s" % stamp, "created": now, "ops": ops}
json.dump(doc, open("board_updates_%s.json" % stamp, "w"), indent=1)
print("wrote board_updates_%s.json with %d ops" % (stamp, len(ops)))
