# PLAIN ENGLISH (board inbox file for the 1:39 PM ET 11/17 six-hourly columns run, fired 18:40Z 11/17): ONE board_updates_<stamp>.json for
#   William's Drive 'board inbox' (the page applies it; no write_db). Decides nothing in AMD.
#   - NEW card chp-pr242-check-4131654 (William's turn): Capital Health Plan check 4131654 (ERA 1053550) answered 6 visits PR-242
#     'not a network provider' and 1 visit CO-243 at $0; the ERA zero-post had moved the PR-242 amounts to the patients - moved back
#     to insurance this run (no rebill). Twinned with the cards on charts 46678 / 48008 (board_ops).
#   - append-only checks on the standing watch rows aet12-carrier-cpid and availity-remits-backlog.
# Usage: cd /home/claude/unbilled && python3 board_file_1117_1840.py -> outbox/board_updates_2026-11-17T1840Z.json
import json, datetime, os
from board_ops import clean_file, plan_new_row
STAMP = "2026-11-17T1840Z"; NOW = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"); WHEN = "11/17"
SRC = "1:39 PM ET 11/17 columns run (ehpa cloud, six-hourly slot) - run %s" % STAMP
items = [{"id": "gillespie-janis-46678", "amdid": "46678", "status": "claude"},
         {"id": "[name]-48008", "amdid": "48008", "status": "done"}]   # inline board read: the only cards on these charts
row = {"id": "chp-pr242-check-4131654", "patient": "CAPITAL HEALTH PLAN PR-242 (check 4131654)", "facility": "ALF / home (CCM, AWV)",
       "amdid": "46678, 21491, 48008, 17474083, 17476942", "mbi": "", "amount": 1658, "status": "william",
       "need": ("YOUR CALL - appeal, write off (WONCS) or credentialing: Capital Health Plan check 4131654 (ACH 11/17, ERA 1053550) paid 11 visits "
                "and answered 7 at $0 with 'services not provided by network/primary care providers': PR-242 on chart 46678 v19442338 5/17/2026 CCM "
                "$315, v19448386 7/10/2026 G0439 $204, v19452574 8/23/2026 CCM $206; chart 21491 v19459620 10/27/2026 CCM $206; chart 48008 v19423586 "
                "11/15/2025 CCM $315 (the claim on the hamrick card - died [DOB]); chart 17474083 v19434037 2/26/2026 CCM $206 = $1,452; and CO-243 "
                "(not authorized by the network/PCP) on chart 17476942 v19459617 10/27/2026 CCM $206. AMD's zero-post had moved the $1,452 PR-242 "
                "amounts onto the six patients' statements - moved back to insurance this run (no rebill, $0 patient balance on all 8 charges). "
                "The Working Denials table files 242 as a credentialing gap (CHP network). Nothing re-sent and nothing written off - tell me which."),
       "why": "ERA Center 11/17: CHP check 4131654 (ERA 1053550, $1,262.12) - Post button posted 11 visits; era_clear zero-posted 6 PR-242 $0 lines (moved to patient) and recorded 1 CO-243 denial",
       "notes": [{"who": "Claude", "at": NOW, "text": "Created by the 1:39 PM ET 11/17 run. CHP is denying CCM / AWV as out-of-network; the patient balances the ERA created are back on insurance. Your decision on the $1,658."}],
       "checks": [{"ok": "no", "src": "ERA 1053550 CAP07 4131654 (era_details)", "result": "6 visits PR-242 $1,452 + 1 visit CO-243/#AM $206 at $0; 11 visits paid $1,262.12 (CO-45 already correct)", "when": WHEN},
                  {"ok": "ok", "src": "move_to_ins.move x6 (rebill=False) - registers/chp_pr242_moveback_2026-11-17T1840Z.json", "result": "8 charges patbal -> 0, insbal restored ($1,452)", "when": WHEN}]}
ops = plan_new_row(items, row, now=NOW)
ops += [
 {"op": "upsert", "collection": "items", "id": "aet12-carrier-cpid", "set": {}, "append": {"checks": [{"ok": "na", "src": SRC, "when": WHEN,
   "result": "1:39 PM ET 11/17: HOLD - the one AET12 PREF0288 + PREF0264 exclusion row (chart 24750, v19455937, run 1700294, $315) stays on the list, not rebilled; carrier master still unchanged (getclaimexclusionclaimruns: 1 run, 1 row)."}]}},
 {"op": "upsert", "collection": "items", "id": "availity-remits-backlog", "set": {}, "append": {"checks": [{"ok": "na", "src": SRC, "when": WHEN,
   "result": "1:39 PM ET 11/17: no new Availity PDF / Check-EFT export / 835 / facesheet (Drive watched folders: nothing new after 12:30Z except the 12:39Z run's own files); Claimocity feed 30 objects, 0 new (newest 20261117); retry-dx nothing to retry (G0439 not in the import tables); feed order sweep 51 visits / 27 charts empty order unchanged, 0 checks bought, 0 saved; Working Denials queue 0; board drops 0; no William note since the last run; Pam Gmail: nothing in 2 days. ERA Center 3 checks $1,829.41 -> 0: WellCare/Sunshine 1008879805 ($459.35, 4 visits), Optum VA CCN 3009764794 ($107.94, 1 visit), Capital Health Plan 4131654 ($1,262.12, 11 visits) all posted by the Post button with CO-45 already right; CHP's 7 $0 lines -> card chp-pr242-check-4131654 (PR-242 patient balances $1,452 moved back to insurance). Columns 0/1/0/1 -> 0/1/0/1 (inspector chart 17478413 O24.419 hold; AET12 hold)."}]}},
]
doc = clean_file({"schema": "irb-board-updates/1", "source": "backend billing run %s" % STAMP, "created": NOW, "ops": ops})
os.makedirs("outbox", exist_ok=True)
json.dump(doc, open("outbox/board_updates_%s.json" % STAMP, "w"), indent=1)
print("ops", len(doc["ops"]), [o["id"] for o in doc["ops"]])
