# PLAIN ENGLISH (board update file, columns run 2026-11-19T0640Z). Writes outbox/board_updates_<stamp>.json via board_ops.clean_file. No AMD call.
import json, os, sys
sys.path.insert(0, "/home/user/effinger-billing-backend/scripts/helpers")
from board_ops import clean_file
STAMP = "2026-11-19T0640Z"; NOW = "2026-11-19T07:05:00Z"; WHEN = "11/19"
SRC = "1:39 AM ET 11/19 columns run (ehpa cloud, six-hourly slot) - run %s" % STAMP
def app(i, checks=None, notes=None, api=None, set_=None):
    a = {}
    if checks: a["checks"] = checks
    if notes: a["notes"] = notes
    if api: a["api"] = api
    op = {"op": "upsert", "collection": "items", "id": i, "append": a}
    if set_: op["set"] = set_
    return op
ops = [
 app("[name]-17478395",
   checks=[{"ok": "ok", "src": "Pam Gmail 11/19 03:27Z (Centre Pointe admit, PointClickCare face sheet photo)", "result": "Primary payer Capital Health Plan, policy [member id] (DOB matches chart F261113-02); admitted to Centre Pointe 11/13/2026 from TMH", "when": WHEN},
           {"ok": "ok", "src": "AMD action: add_ins 17478395 car41826 (CAP07) CIO50063618 -> ins9521322 seq 2; AMD eligibility (free 271)", "result": "CAP07 CIO50063618 ACTIVE; FLO02 ACTIVE naming H5938 CAPITAL HEALTH PLAN as the plan", "when": WHEN},
           {"ok": "ok", "src": "AMD action: ins_update sequence=2 + freq1_visit reroute <visit> <charge> 2", "result": "chart order 2 (CHP alone); v19461089 11/09 99223 310, v19461018 11/10, v19461017 11/11, v19461123 11/12, v19461266 11/13 (99232 111 each) -> insorder 2, frequency 1, chargerebill seq 2 -> 204 x5 (754 dollars)", "when": WHEN}],
   notes=[{"who": "Claude", "at": NOW, "text": "11/19 1:39 AM run: Pam's Centre Pointe admit photo (11/19) carried her Capital Health Plan number - CHP added (AMD 271 ACTIVE), chart set CHP first, and the five HCA visits 11/09-11/13 (754 dollars, already sent to Medicare) re-sent to CHP as original claims. Nothing left for you here unless CHP denies."}],
   api=[{"src": "AMD 271 (elig_amd --all) after add", "at": NOW, "text": "seq1 car6085 FLO02 <MBI> ACTIVE | HN 18:H5938 CAPITAL HEALTH PLAN\nseq2 car41826 CAP07 CIO50063618 ACTIVE"}],
   set_={"status": "claude", "need": "None - fixed 11/19: CHP member number from Pam's 11/19 face sheet photo (CIO50063618) added as CAP07, AMD 271 ACTIVE; chart order CHP first; the five HCA visits 11/09-11/13 (754 dollars) re-sent to CHP as original claims (204 x5). Watch for CHP's answer.", "inscarrier": "CAP07 Capital Health Plan (MA) seq 2 - chart order 2; FLO02 Medicare seq 1 (not billed)"}),
 app("aet12-carrier-cpid", checks=[{"ok": "na", "src": SRC, "when": WHEN,
   "result": "1:39 AM ET 11/19: HOLD - the one AET12 PREF0288 + PREF0264 exclusion row (chart 24750, v19455937, run 1700294, $315) stays on the list, not rebilled; carrier master still unchanged (getclaimexclusionclaimruns: 1 run, 1 row)."}]),
 app("availity-remits-backlog", checks=[{"ok": "na", "src": SRC, "when": WHEN,
   "result": "1:39 AM ET 11/19: no new Availity PDF / Check-EFT export / 835 / facesheet (Drive watched folders: nothing new after 00:55Z except the nightly cascade's own files); Claimocity feed 31 objects, 0 new (newest 20261118); retry-dx: 1 visit still waits on S82.843D; feed order sweep 0 saved, 51 not saved (standing checks); Working Denials queue 0; board drops 0; Pam Gmail: one new Centre Pointe admit 03:27Z (chart 17478395 - CHP number found, insured and re-sent, see its card). ERA Center 0 checks $0.00 -> 0 checks $0.00. Columns 0/1/28/1 -> 0/1/0/1 (28 Unbilled rows released by the engine, 26 of them 'prior payor'; inspector chart 17478413 O24.419 hold; AET12 hold)."}]),
]
doc = clean_file({"schema": "irb-board-updates/1", "source": "backend billing run %s" % STAMP, "created": NOW, "ops": ops})
os.makedirs("outbox", exist_ok=True)
json.dump(doc, open("outbox/board_updates_%s.json" % STAMP, "w"), indent=1)
print("ops", len(doc["ops"]), [o["id"] for o in doc["ops"]])
