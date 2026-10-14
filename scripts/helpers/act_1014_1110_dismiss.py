# PLAIN ENGLISH (AMD write for the 7 AM ET 10/14/2026 run, 2026-10-14T1110Z) - ERA check 1053153 (Medicare Part B 819970542, $4,210.92, 43 claims):
#   its 57 money lines were posted ERA-linked (pay $4,107.33 + WOINS $4,650.12, 0 faults) by era_new_1014_1110.py; the two remaining lines
#   (chart 22603 v19420337 / v19422862, 99308, paid 55.97 + 47.57) sit on charges Medicare had already denied $0 on 9/10/2026 (check 349929519)
#   and that were written off WOINS the same day - live open balance 0, recorded as residual $103.54 (William's 9/13 rule: post the maximum AMD
#   accepts, the residual goes in the report). Every line is settled, so the check is DISMISSED (POST /api/era/checks/dismiss, the id as a JSON
#   string); GET /api/era/checks confirms. --dry prints the plan and posts nothing. Never touches: the held UHC takeback check 1053116, balances,
#   plans. Register: registers/act_2026-10-14T1110Z_dismiss.json
import amd, era_post, requests, json, sys, time
DRY = "--live" not in sys.argv; amd.login_cached(); STAMP = "2026-10-14T1110Z"; CHECK = "1053153"; log = []
def L(s): print(s, flush=True); log.append(s)
reg = json.load(open("registers/era_new_%s.json" % STAMP))
mine = [r for r in reg["lines"] if str(r["checkid"]) == CHECK]
bad = [r for r in mine if r["outcome"] == "FAULT" or r["outcome"].startswith(("HOLD", "DRY", "not attempted"))]
unsettled = [r for r in mine if not r["outcome"].startswith(("posted", "already", "residual", "skip - insurance balance already 0", "duplicate"))]
if not mine: L("NOT dismissing %s - no posting register lines for it" % CHECK)
elif bad or unsettled: L("NOT dismissing %s - unsettled lines in the posting register: %s" % (CHECK, [(r["visitid"], r["outcome"][:40]) for r in (bad + unsettled)]))
elif DRY: L("DRY dismiss %s (%d lines; outcomes: %s)" % (CHECK, len(mine), sorted(set(r["outcome"][:24] for r in mine))))
else:
    r = requests.post("https://pm-api-103.advancedmd.com/api/era/checks/dismiss", headers=era_post.H(), data=json.dumps(CHECK), timeout=60)
    L("dismiss %s -> %s %s" % (CHECK, r.status_code, r.text[:120]))
    time.sleep(1); L("checks after: %s" % [c["id"] for c in era_post.checks()])
json.dump({"stamp": STAMP, "dry": DRY, "check": CHECK, "lines": len(mine), "log": log}, open("registers/act_%s_dismiss%s.json" % (STAMP, "_dry" if DRY else ""), "w"), indent=1)
