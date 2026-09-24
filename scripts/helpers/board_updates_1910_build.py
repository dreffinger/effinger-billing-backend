# PLAIN ENGLISH (board update file builder, 3 PM ET 9/14/2026 slot - ehpa cloud run 2026-09-14T1910Z)
# Decides: nothing on AMD. Writes board_updates_2026-09-14T1910Z.json (Insurance Refresh Board inbox ops):
#   - jasper-jethro-open: records the WellCare duplicate-claim rejection on run 1700190 (9/18/2025 visit) completed, no rebill.
#   - aet12-carrier-cpid: claim run 1700190 (9/13 21:07 UTC, 4 claims) predates the 04:20 UTC AET12 re-send - still waiting.
#   - bull-thurlow-17477723: this slot's check line (chart still 0 plans, no facesheet anywhere).
#   - era-manual-post-0912: this slot's ERA line (idempotent by src+when).
# Never touches: the board directly (no write_db) - the board applies this file when William opens it.
import json, sys, time
stamp = "2026-09-14T1910Z"; now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
era_line = sys.argv[1] if len(sys.argv) > 1 else "ERA step ran - see run report"
src = "3pm ET 9/14 columns run (ehpa cloud)"
ops = [
 {"op": "upsert", "collection": "items", "id": "jasper-jethro-open",
  "append": {"checks": [{"ok": "ok", "result": "Exclusion run 1700190 (9/13 21:07 UTC) visit 19417241 claim 19417241G (99223+99497 9/18/2025, $443, WEL04): WellCare answered 'THIS SEEMS TO BE A DUPLICATE OF A CLAIM SUBMITTED 09/05/2026' - the 9/5 claim is already in play, so the exclusion was completed with no rebill (William's duplicate rule). Nothing else on this row changed.", "src": src, "when": "9/14"}],
             "notes": [{"who": "Claude", "at": now, "text": "3pm ET 9/14 run: WellCare bounced the 9/18/2025 hospital claim as a duplicate of the 9/5/2026 submission - completed off the exclusion list, original claim stays out. Watching."}]}},
 {"op": "upsert", "collection": "items", "id": "aet12-carrier-cpid",
  "append": {"checks": [{"ok": "na", "result": "Exclusions column 2 -> 0 (both rows were WEL04 duplicate rejections on run 1700190, not AET12). Run 1700190 (9/13 21:07 UTC, 4 claims, user EFFINGER) predates the 04:20 UTC 9/14 AET12 re-send, so the Standard Professional profile test is still decided by the next MCKGRP claim run.", "src": src, "when": "9/14"}]}},
 {"op": "upsert", "collection": "items", "id": "bull-thurlow-17477723",
  "append": {"checks": [{"ok": "no", "result": "chart still has zero insurance plans (getdemographic 19:19 UTC); no facesheet in hca/tmh/PCC/Claimocity folders since 9/14 13:00 UTC, Pam Gmail sweep newer_than:2d = 0, no board drop; visits 19454443/19454465 ($421) stay in Unbilled", "src": src, "when": "9/14"}]}},
 {"op": "upsert", "collection": "items", "id": "era-manual-post-0912",
  "append": {"checks": [{"ok": "na", "result": era_line, "src": src + " - ERA step 5", "when": "9/14"}]}},
]
doc = {"schema": "irb-board-updates/1", "source": "backend billing run %s" % stamp, "created": now, "ops": ops}
json.dump(doc, open("board_updates_%s.json" % stamp, "w"), indent=1)
print("wrote board_updates_%s.json with %d ops" % (stamp, len(ops)))
