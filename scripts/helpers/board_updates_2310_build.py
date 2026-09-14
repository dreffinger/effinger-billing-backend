# PLAIN ENGLISH (board update file builder, 7 PM ET 9/14/2026 slot - ehpa cloud run 2026-09-14T2310Z)
# Decides: nothing on AMD. Writes board_updates_2026-09-14T2310Z.json (Insurance Refresh Board inbox ops):
#   - aet12-carrier-cpid: still no claim run after 1700188 (9/12 21:09 UTC) at 23:16 UTC; exclusions 0; the Standard Professional test is undecided.
#   - bull-thurlow-17477723: this slot's check line (chart still 0 plans, no facesheet / email / drop).
#   - era-manual-post-0912: this slot's ERA line (idempotent by src+when).
#   - lee-muriel-a-denials: the row still reads status 'william' / 'MBI needed' although the 11pm ET 9/13 run added
#     Medicare and re-sent both visits - need rewritten and the row moved back to Claude's watch.
#   - precheck rows (optional argv[2] = JSON list of extra ops) appended as-is.
# Never touches: the board directly (no write_db) - the board applies this file when William opens it.
import json, sys, time
stamp = "2026-09-14T2310Z"; now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
era_line = sys.argv[1] if len(sys.argv) > 1 else "ERA step ran - see run report"
extra = json.load(open(sys.argv[2])) if len(sys.argv) > 2 else []
src = "7pm ET 9/14 columns run (ehpa cloud)"
ops = [
 {"op": "upsert", "collection": "items", "id": "aet12-carrier-cpid",
  "append": {"checks": [{"ok": "na", "result": "Exclusions column 0 rows. getclaimrunstatus at 23:16 UTC still lists 1700188 (9/12 21:09 UTC) as the newest claim run - the 59 AET12 claims re-sent 04:20 UTC on the Standard Professional profile have not left yet; PREF0288 answer is read by the first run after the next claim run posts.", "src": src, "when": "9/14"}]}},
 {"op": "upsert", "collection": "items", "id": "bull-thurlow-17477723",
  "append": {"checks": [{"ok": "no", "result": "chart still has zero insurance plans; no facesheet in hca/tmh/PCC/Claimocity folders since 9/14 17:00 UTC, Pam Gmail sweep newer_than:2d = 0, no board drop; visits 19454443/19454465 ($421) stay in Unbilled. Listed in tonight's 'current face sheets needed' email.", "src": src, "when": "9/14"}]}},
 {"op": "upsert", "collection": "items", "id": "era-manual-post-0912",
  "append": {"checks": [{"ok": "na", "result": era_line, "src": src + " - ERA step 5", "when": "9/14"}]}},
 {"op": "update", "collection": "items", "id": "lee-muriel-a-denials",
  "set": {"status": "claude",
          "need": "DONE 9/14 (11pm ET 9/13 run): Medicare (the MBI from your facesheet paste) added seq 2 and verified ACTIVE on AMD's free 271 (A/B since 6/1/2005, QMB); patient order 2,1; visits 19448262 (7/14, $310) and 19448577 (7/15, $111) reset to freq 1 and re-sent to Medicare (204/204). Florida Blue Medigap F stays second for the crossover. Watching for the Medicare remit - nothing needed from you."},
  "append": {"notes": [{"who": "Claude", "at": now, "text": "7pm ET 9/14 run: this row still showed 'MBI needed' on your turn after the 11pm 9/13 run had already added Medicare and re-sent both July visits - need rewritten, moved back to my watch."}]}},
] + extra
doc = {"schema": "irb-board-updates/1", "source": "backend billing run %s" % stamp, "created": now, "ops": ops}
json.dump(doc, open("board_updates_%s.json" % stamp, "w"), indent=1)
print("wrote board_updates_%s.json with %d ops" % (stamp, len(ops)))
