# PLAIN ENGLISH (board update file builder, 7 PM ET 10/15/2026 slot - ehpa cloud run 2026-10-15T2310Z)
# Decides: nothing on AMD. Writes board_updates_2026-10-15T2310Z.json (Insurance Refresh Board inbox ops): ONE check line on the
#   availity-remits-backlog row (this slot's sources / ERA / columns read - idempotent by src+when) and ONE check line on the
#   hesketh-[first]-17472553 row (the 10/12/2026 visit billed to FCC alone - fix on approval card B).
# Never touches: the board directly (no write_db) - the board applies this file when William opens it.
import json, time
stamp = "2026-10-15T2310Z"; now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
src = "7pm ET 10/15 columns run (ehpa cloud) - run %s" % stamp
ops = [
 {"op": "upsert", "collection": "items", "id": "availity-remits-backlog",
  "append": {"checks": [{"ok": "na", "result": "7 PM ET 10/15: no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (Drive recent-files list: nothing after the 2110Z run's own files); no new 835, facesheet or Claimocity file; Working Denials queue 0; board drops 0; Pam Gmail: the three 10/15 admits (Tapestry x1, Brynwood x2) still have no AMD chart. ERA Center 2 checks -> 1: NEW UHC W1223786 (1053188, $567.32, 11 claims) - 6 money lines posted by the Billing Button before this run's pass, the last 2 by its 23:22Z pass (this run's live post was refused by the environment), check gone from the Center; the 4 CO-29 timely-filing answers on chart 23967 ($886, UNI20 pre-5/1 primary claims) are on approval card A-2026-10-15T2310Z-A (WOLATE); 1053116 ($71 takeback pair) held for your decision. Columns 0/5/28/141 -> 0/5/12/6: the cascade session applied 28 of the 29 cards you approved at 21:38Z ($10,508.02); card K (chart 17478062) not applied - Stedi MBILU AAA 72 - your turn. Precheck --days 3: 1 flag -> card A-2026-10-15T2310Z-B (chart 17472553 Medicare first). 'current face sheets needed' email sent (Gaskins 17478063 facesheet; Madison-Digby 17478059 and Edgerton 17478064 CHP ids).", "src": src, "when": "10/15"}]}},
 {"op": "upsert", "collection": "items", "id": "hesketh-[first]-17472553",
  "append": {"checks": [{"ok": "no", "result": "7 PM ET 10/15 precheck: the 10/12/2026 99233 (v19457645, $160) went out 10/13 to Florida Community Care ALONE - the 10/10 re-route set the eleven visits' order but the chart's default order still reads FCC only (3). Fix = patient order Medicare, FCC (2,3) + one re-route of the visit to Medicare; the environment refused the write -> approval card A-2026-10-15T2310Z-B (tap Approve on the Mandatory Approvals page).", "src": src, "when": "10/15"}],
             "notes": [{"who": "Claude", "text": "10/12 visit went to FCC alone (chart default order never changed) - fix is on approval card A-2026-10-15T2310Z-B; after it applies, every later Claimocity visit bills Medicare first on its own.", "at": now}]}},
]
doc = {"schema": "irb-board-updates/1", "source": "backend billing run %s" % stamp, "created": now, "ops": ops}
json.dump(doc, open("board_updates_%s.json" % stamp, "w"), indent=1)
print("board_updates_%s.json" % stamp, len(ops), "ops")
