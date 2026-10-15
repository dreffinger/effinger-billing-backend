# PLAIN ENGLISH (board update file builder, 5 PM ET 10/15/2026 slot - ehpa cloud run 2026-10-15T2110Z)
# Decides: nothing on AMD. Writes board_updates_2026-10-15T2110Z.json (Insurance Refresh Board inbox ops) with ONE check line
#   on the availity-remits-backlog row (this slot's sources / ERA / columns read - idempotent by src+when).
# Never touches: the board directly (no write_db) - the board applies this file when William opens it.
import json, time
stamp = "2026-10-15T2110Z"; now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
src = "5pm ET 10/15 columns run (ehpa cloud) - run %s" % stamp
ops = [
 {"op": "upsert", "collection": "items", "id": "availity-remits-backlog",
  "append": {"checks": [{"ok": "na", "result": "5 PM ET 10/15: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (the seven watched folders hold nothing after 17:00Z except the routine's own board_updates files; Drive-wide no pdf/csv/image/835/hl7 after 19:30Z); no new 835, facesheet or Claimocity file; Working Denials queue 0; board drops 0; 0 rows changed since 19:00Z; approvals 0 approved / 29 waiting (A-2026-10-15T0510Z-A..P, A-2026-10-15T1110Z-A..M); Pam Gmail: a THIRD admit email 19:19Z (NA Tapestry, photo facesheet) joins the two 17:0xZ Brynwood admits - lookuppatient at 21:22Z finds no AMD chart for any of the three (listed, not turned into charts). ERA Center 1 check $71.00 before and after (1053116 UHC W0020208 held for your takeback decision; era_post --dry 0 postable / 3 skipped, era_clear --dry HELD). Columns 0/5/28/141 -> 0/5/28/141 - every row on a waiting card or a standing hold; the seven zero-plan HCA charts re-read live at 21:22Z still carry no plan; no AMD write this slot. UNI20/BCBS pre-5/1 pass 108: 16 PENDING (chart 17472874 $2,563) + 1 UNKNOWN (chart 17475632), 0 sent.", "src": src, "when": "10/15"}]}},
]
doc = {"schema": "irb-board-updates/1", "source": "backend billing run %s" % stamp, "created": now, "ops": ops}
json.dump(doc, open("board_updates_%s.json" % stamp, "w"), indent=1)
print("wrote board_updates_%s.json with %d ops" % (stamp, len(ops)))
