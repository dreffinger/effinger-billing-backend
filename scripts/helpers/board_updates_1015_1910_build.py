# PLAIN ENGLISH (board update file builder, 3 PM ET 10/15/2026 slot - ehpa cloud run 2026-10-15T1910Z)
# Decides: nothing on AMD. Writes board_updates_2026-10-15T1910Z.json (Insurance Refresh Board inbox ops) with ONE check line
#   on the availity-remits-backlog row (this slot's sources / ERA / columns read - idempotent by src+when).
# Never touches: the board directly (no write_db) - the board applies this file when William opens it.
import json, time
stamp = "2026-10-15T1910Z"; now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
src = "3pm ET 10/15 columns run (ehpa cloud) - run %s" % stamp
ops = [
 {"op": "upsert", "collection": "items", "id": "availity-remits-backlog",
  "append": {"checks": [{"ok": "na", "result": "3 PM ET 10/15: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (the seven watched folders hold nothing after 10/14 except the routine's own files); no new 835, facesheet or Claimocity file; Working Denials queue 0; board drops 0; 0 rows changed since 15:00Z; approvals 0 approved / 29 waiting; Pam Gmail: the two 17:0xZ Brynwood admits still have no AMD chart (lookuppatient at 19:19Z). ERA Center 1 check $71.00 before and after (1053116 UHC W0020208 held for your takeback decision; era_post --dry 0 postable / 3 skipped, era_clear --dry HELD). Columns 0/5/28/141 -> 0/5/28/141 - every row on a waiting card (A-2026-10-15T0510Z-A..P, A-2026-10-15T1110Z-A..M) or a standing hold; the seven zero-plan HCA charts re-read live at 19:19Z still carry no plan; no AMD write this slot. UNI20/BCBS pre-5/1 pass 107: 16 PENDING (chart 17472874 $2,563) + 1 UNKNOWN, 0 sent.", "src": src, "when": "10/15"}]}},
]
doc = {"schema": "irb-board-updates/1", "source": "backend billing run %s" % stamp, "created": now, "ops": ops}
json.dump(doc, open("board_updates_%s.json" % stamp, "w"), indent=1)
print("wrote board_updates_%s.json with %d ops" % (stamp, len(ops)))
