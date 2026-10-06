# PLAIN ENGLISH (AMD write for the 5 PM ET 10/6 run, 2026-10-06T2110Z, second check) - ERA check 1053019 (Humana NO-PAY-202610050005590, $0, 3 claims):
#   1 line posted ERA-linked by era_new_1006_2110.py (pat46051 v19454875 99309: CO-185/N767 Medicaid-secondary crossover $0 on the Medicare-paid
#   line -> WOINS 16.93, 9/20 rule); 4 OA-23 $0 lines on pat17473383's two CCM visits (12/28/2025, 1/27/2026, $630) have NO prior payment on the
#   charges (UHC $0 denials, then billed to Humana 9/27) - denial-only, handed to William on board row dunstan-josiah through the board update
#   file - so the remit is fully read and the check is DISMISSED (POST /api/era/checks/dismiss, the id as a JSON string); GET /api/era/checks
#   confirms. --dry prints the plan and posts nothing. Never touches: the held Florida Blue check 1052906, balances, plans. Register: registers/act_2026-10-06T2110Z_b.json
import amd, era_post, requests, json, sys, time
DRY = "--dry" in sys.argv; amd.login_cached(); STAMP = "2026-10-06T2110Z"; log = []
def L(s): print(s, flush=True); log.append(s)
reg = json.load(open("registers/era_new_%s.json" % STAMP))
mine = [r for r in reg["lines"] if str(r["checkid"]) == "1053019"]
bad = [r for r in mine if r["outcome"] == "FAULT"]
if not mine: L("NOT dismissing 1053019 - no posting register lines for it")
elif bad: L("NOT dismissing 1053019 - faults in the posting register: %s" % bad)
elif DRY: L("DRY dismiss 1053019 (register outcomes: %s)" % sorted(set(r["outcome"][:24] for r in mine)))
else:
    r = requests.post("https://pm-api-103.advancedmd.com/api/era/checks/dismiss", headers=era_post.H(), data=json.dumps("1053019"), timeout=60)
    L("dismiss 1053019 -> %s %s" % (r.status_code, r.text[:120]))
    time.sleep(1); L("checks after: %s" % [c["id"] for c in era_post.checks()])
json.dump({"stamp": STAMP, "dry": DRY, "log": log}, open("registers/act_%s_b%s.json" % (STAMP, "_dry" if DRY else ""), "w"), indent=1)
