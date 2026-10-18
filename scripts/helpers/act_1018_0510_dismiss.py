# PLAIN ENGLISH (AMD write for the 1 AM ET 10/18/2026 run, 2026-10-18T0510Z) - ERA check 1053206 (Humana ACH 203498031261017, received 10/17,
#   check amount $16.93, 8 claim lines, every line $0 payment): 7 lines are Humana's OA-23 $0 answers (as the Medicaid MMA secondary) on the
#   CCM 99487/99489 visits of chart 17472784 and 1 line is a CO-185/N767 $0 answer on chart 20379 v19456477 (99309 9/24/2026, Garland-G profile).
#   Live read 05:2xZ: EVERY charge on the check is already at $0 insurance / $0 patient and already carries Humana's earlier answer from check
#   203180143261014 (10/14: WOCAID2ND on the 17472784 lines, a $16.93 payment on 20379) - this remit repeats answers AMD already holds, so there is
#   nothing postable (William 9/13: a $0 open balance = already adjudicated, record only; denial-only lines never go to a manual post). The check
#   is DISMISSED (POST /api/era/checks/dismiss, the id as a JSON string) only when that live gate holds for all 8 lines; GET /api/era/checks confirms.
# --dry prints the plan and posts nothing. Never touches: balances, plans, claims, rebills. Register: registers/act_2026-10-18T0510Z_dismiss.json
#   + registers/era_manual_register.json (live: one 'already-posted' row per line).
import amd, era_post, payreasons, requests, json, sys, time
DRY = "--live" not in sys.argv; amd.login_cached(); STAMP = "2026-10-18T0510Z"; CHECK = "1053206"; log = []
def L(s): print(s, flush=True); log.append(s)
det = json.load(open("era_details/%s.json" % CHECK))["eracheckdetails"]
lines = []; ok_all = True
for v in det:
    pid, vid = str(v["patientid"]), str(v["visitid"])
    st = {c["cid"]: c for c in payreasons.visit_state(pid, vid)}
    for ch in v["charges"]:
        cid = str(ch["chargedetailid"]); c = st.get(cid)
        row = {"checkid": CHECK, "checkclaimid": v["checkclaimid"], "pid": pid, "visitid": vid, "chargedetailid": cid, "cpt": ch["chargecode"],
               "era_paid": ch["paymentamount"], "era_adj": ch["adjustmentamount"], "carc": [x["reasoncode"] for x in ch.get("carc", [])]}
        if not c: row["outcome"] = "HOLD - charge not live"; ok_all = False
        else:
            hum = [p for p in c["pays"] if p.get("void") != "1" and p.get("carrier") == "HUM01"]
            row.update(insbal=c["insbalance"], patbal=c["patbalance"], humana_pays=[(p["checkno"], p["amount"]) for p in hum])
            if c["insbalance"] == 0 and c["patbalance"] == 0 and hum: row["outcome"] = "already-posted - $0 balances, Humana answer on the charge from check %s" % hum[0]["checkno"]
            elif c["insbalance"] == 0 and c["patbalance"] == 0: row["outcome"] = "already adjudicated - $0 balances, no Humana line (record only)"
            else: row["outcome"] = "HOLD - open balance ins %.2f pat %.2f" % (c["insbalance"], c["patbalance"]); ok_all = False
        L("v%s c%s %s %s" % (vid, cid, row["cpt"], row["outcome"])); lines.append(row)
    time.sleep(0.3)
if not ok_all: L("NOT dismissing %s - a line is not settled" % CHECK)
elif DRY: L("DRY dismiss %s (%d lines all settled)" % (CHECK, len(lines)))
else:
    r = requests.post("https://pm-api-103.advancedmd.com/api/era/checks/dismiss", headers=era_post.H(), data=json.dumps(CHECK), timeout=60)
    L("dismiss %s -> %s %s" % (CHECK, r.status_code, r.text[:120])); time.sleep(1); L("checks after: %s" % [c["id"] for c in era_post.checks()])
    REGF = "registers/era_manual_register.json"; reg = json.load(open(REGF))
    for x in lines: reg.append({"checkid": CHECK, "checkclaimid": x["checkclaimid"], "visitid": x["visitid"], "chargedetailid": x["chargedetailid"], "outcome": "already-posted", "when": STAMP})
    json.dump(reg, open(REGF, "w"), indent=1)
json.dump({"stamp": STAMP, "dry": DRY, "check": CHECK, "lines": lines, "log": log}, open("registers/act_%s_dismiss%s.json" % (STAMP, "_dry" if DRY else ""), "w"), indent=1)
