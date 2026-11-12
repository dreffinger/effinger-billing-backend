# PLAIN ENGLISH (board inbox file for the 7:40 PM ET 11/10 evening columns run, fired 00:40Z 11/11): writes ONE
#   board_updates_<stamp>.json for William's Drive 'board inbox' (the page applies it; no write_db, no approval). Decides nothing
#   in AMD. Ops: append-only checks on the standing watch rows (availity-remits-backlog, aet12-carrier-cpid) with this run's
#   column / ERA numbers read from reports/button/<stamp>-engine.json, and a checks/notes append on grantham-carlotta-17478318 (the
#   'current face sheets needed' email of this run names that chart). No new cards: the ERA posts and the two wrong-payer
#   coinsurance write-offs needed no decision from William (chart ids in the run report). Built through board_ops.clean_file:
#   no `updated`, no status/need/why on rows William owns. Never touches: AMD, the board DB, Drive (the upload is the connector's).
# Usage: cd /home/claude/unbilled && python3 board_file_1111_0040.py -> outbox/board_updates_2026-11-11T0040Z.json
import json, os, datetime
from board_ops import clean_file
STAMP = "2026-11-11T0040Z"; NOW = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"); WHEN = "11/10"
SRC = "7:40pm ET 11/10 columns run (ehpa cloud, evening slot) - run %s" % STAMP
rep = {}
p = "/home/claude/effinger-billing-backend/reports/button/%s-engine.json" % STAMP
if os.path.exists(p): rep = json.load(open(p))
s = rep.get("summary", {}); cb = s.get("columns", {}).get("before", {}); ca = s.get("columns", {}).get("after", {}); eb = s.get("era", {}).get("before", {}); ea = s.get("era", {}).get("after", {})
K = ("charge_review", "claim_inspector", "unbilled", "exclusions")
cols = "Columns %s -> %s" % ("/".join(str(cb.get(k, "?")) for k in K), "/".join(str(ca.get(k, "?")) for k in K))
era = "ERA Center %s check(s) $%.2f -> %s checks $%.2f" % (eb.get("checks", "?"), float(eb.get("unposted", 0) or 0), ea.get("checks", "?"), float(ea.get("unposted", 0) or 0))
wait = "; ".join(rep.get("waiting", [])[:4]) or "none listed"
ops = []
ops.append({"op": "upsert", "collection": "items", "id": "availity-remits-backlog", "set": {}, "append": {"checks": [{"ok": "na", "src": SRC, "when": WHEN,
    "result": "7:40 PM ET 11/10 (evening slot): no new Availity PDF or Check/EFT export in 'bht Optum era downloads' / 'treasury payments' (nothing new there since the 11/10 01:39 AM run); no new facesheet in hca / tmh / PCC; Claimocity feed 23 objects, 1 new (20261110, 60 messages - all 60 already in AMD, entered by the day's button slots); Working Denials queue 0; board drops 0; Claude-turn rows William changed since 07:00Z 11/10: 0; Pam Gmail: the six 11/9-11/10 admit emails all worked by earlier runs, nothing newer. %s: UHC W2439062 (1053487, $363.80, 9 claims) - 4 money lines posted by the Post button on charts 17476042 / 17477772 / 17478058 x2 ($363.80) and their CO-45 contractual corrected off the patient balances (WOINS $361.20); its 5 $0 lines were UHC's wrong-payer answers on Medicare-paid coinsurance (PR26 x4 on chart 17475777 May-2026 visits - the AARP MA plan began 7/1/2026; PR27 x1 on chart 17473661 9/28/2026 - the MA plan ended 9/17/2026, Medicare + Part D now) - the zero-post had put $115.33 of coinsurance on the two patients: moved back to insurance and written off WOCLTREQ (no live secondary, William 10/13), $0/$0 everywhere; check dismissed. %s (engine pass 00:58-01:08Z, 0 errors). Evening extras: 'current face sheets needed' email sent (chart 17478318 only); run report CSV to 'bht hca facesheets'. NOTE: the 11/10 12:39Z run posted a START and no RUN COMPLETE digest and the 18:39Z slot never started - the GitHub Actions button engine covered both (columns 0/2/0/2 all day, ERA emptied 3 times). Waiting: %s" % (era, cols, wait)}]}})
ops.append({"op": "upsert", "collection": "items", "id": "aet12-carrier-cpid", "set": {}, "append": {"checks": [{"ok": "na", "src": SRC, "when": WHEN,
    "result": "7:40 PM ET 11/10: HOLD - the one AET12 PREF0288 + PREF0264 exclusion row (chart 24750, v19455937, run 1700294, $206 CCM line / $315 claim) stays on the list, not rebilled; carrier master still unchanged."}]}})
ops.append({"op": "upsert", "collection": "items", "id": "grantham-carlotta-17478318", "set": {}, "append": {
    "checks": [{"ok": "human", "src": SRC, "when": WHEN, "result": "Exclusion row still open on run 1700365 (v19460525 99232 11/07/2026 $111, CIG09 'entity not eligible'); chart still carries only the Cigna Dental HMO plan; no facesheet in hca / tmh / PCC, no Pam email, no board drop for this chart since 11/9. Listed as the only facesheet needed in tonight's 'current face sheets needed' email."}],
    "notes": [{"who": "Claude", "at": NOW, "text": "Still the one facesheet needed - the HCA admission sheet or card for the ~11/03/2026 stay (five visits, $754). Tonight's facesheets email names only this chart."}]}})
doc = clean_file({"schema": "irb-board-updates/1", "source": "backend billing run %s" % STAMP, "created": NOW, "ops": ops})
os.makedirs("outbox", exist_ok=True); out = "outbox/board_updates_%s.json" % STAMP
json.dump(doc, open(out, "w"), indent=1); print("wrote", out, len(ops), "ops;", "engine report" if rep else "NO engine report")
