# PLAIN ENGLISH (AMD write for the 5 PM ET 10/6 run, 2026-10-06T2110Z) - ERA check 1053018 (Centene / WellCare 0917844205, $166.26, 8 claims):
#   every line is settled - 3 posted ERA-linked by era_new_1006_2110.py (2 x 99233 pay 83.13 + WOINS 76.87 on pat17472703; WOCAID2ND 21.80
#   dual residual on pat17472546), 2 CO-242 $0 WellCare lines on charges WellCare already paid (balance 0), 3 CO-16/M56 $0 lines (the SUN01
#   payer-id cluster, board row centene-m56-denials-0920; the pat17472834 16.93 coinsurance moved back to insurance with move_to_ins.py) -
#   so the check is DISMISSED (POST /api/era/checks/dismiss, the id as a JSON string), then GET /api/era/checks confirms it is gone.
#   --dry prints the plan and posts nothing. Never touches: the held Florida Blue check 1052906, balances, plans.  Register: registers/act_2026-10-06T2110Z.json
import amd, era_post, requests, json, sys, time
DRY = "--dry" in sys.argv; amd.login_cached(); STAMP = "2026-10-06T2110Z"; log = []
def L(s): print(s, flush=True); log.append(s)
reg = json.load(open("registers/era_new_%s.json" % STAMP))
bad = [r for r in reg["lines"] if r["outcome"] == "FAULT"]
if bad: L("NOT dismissing 1053018 - faults in the posting register: %s" % bad)
elif DRY: L("DRY dismiss 1053018 (posting register: %s)" % sorted(set(r["outcome"][:20] for r in reg["lines"])))
else:
    r = requests.post("https://pm-api-103.advancedmd.com/api/era/checks/dismiss", headers=era_post.H(), data=json.dumps("1053018"), timeout=60)
    L("dismiss 1053018 -> %s %s" % (r.status_code, r.text[:120]))
    time.sleep(1); L("checks after: %s" % [c["id"] for c in era_post.checks()])
json.dump({"stamp": STAMP, "dry": DRY, "log": log}, open("registers/act_%s%s.json" % (STAMP, "_dry" if DRY else ""), "w"), indent=1)
