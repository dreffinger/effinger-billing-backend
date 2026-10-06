# PLAIN ENGLISH (AMD write for the 5 PM ET 10/6 run, 2026-10-06T2110Z, third check) - ERA check 1053020 (Humana 202336236261006, $106.82, 1 claim):
#   its one 99233 money line (pat17477640 v19455115 9/18/2026: paid 106.82, CO-45 51.00 + CO-253 2.18 -> WOINS 53.18) was posted ERA-linked by
#   era_new_1006_2110.py, so the check is DISMISSED (POST /api/era/checks/dismiss, the id as a JSON string); GET /api/era/checks confirms.
#   --dry prints the plan and posts nothing. Never touches: the held Florida Blue check 1052906, balances, plans. Register: registers/act_2026-10-06T2110Z_c.json
import amd, era_post, requests, json, sys, time
DRY = "--dry" in sys.argv; amd.login_cached(); STAMP = "2026-10-06T2110Z"; log = []
def L(s): print(s, flush=True); log.append(s)
reg = json.load(open("registers/era_new_%s.json" % STAMP))
mine = [r for r in reg["lines"] if str(r["checkid"]) == "1053020"]
bad = [r for r in mine if r["outcome"] == "FAULT"]
if not mine: L("NOT dismissing 1053020 - no posting register lines for it")
elif bad: L("NOT dismissing 1053020 - faults in the posting register: %s" % bad)
elif DRY: L("DRY dismiss 1053020 (register outcomes: %s)" % sorted(set(r["outcome"][:24] for r in mine)))
else:
    r = requests.post("https://pm-api-103.advancedmd.com/api/era/checks/dismiss", headers=era_post.H(), data=json.dumps("1053020"), timeout=60)
    L("dismiss 1053020 -> %s %s" % (r.status_code, r.text[:120]))
    time.sleep(1); L("checks after: %s" % [c["id"] for c in era_post.checks()])
json.dump({"stamp": STAMP, "dry": DRY, "log": log}, open("registers/act_%s_c%s.json" % (STAMP, "_dry" if DRY else ""), "w"), indent=1)
