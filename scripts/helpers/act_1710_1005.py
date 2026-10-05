# PLAIN ENGLISH (Humana CO-B9 hospice denials -> straight Medicare + GV, 1 PM ET 10/5/2026 run)
# Decides: Humana check 1052967 answered CO-B9 'patient is enrolled in a hospice' on three visits of one chart whose
#   May-July 2026 claims had been re-routed to the Humana MA plan on 10/2 because the chart's Medicare plan was end-dated
#   04/30/2026. William's standing rule (9/20/2026): a hospice denial = GV modifier + frequency-1 rebill to straight
#   Medicare, never written off, never held. AMD's own 271 today: Medicare A/B ACTIVE since 2/1/2014 (Humana is the MA plan).
#   So: re-open the Medicare plan (clear the end date), set the patient order Medicare first, and for every hospice-period
#   visit the 10/2 re-route sent to Humana (the three denied ones + the two May visits that will draw the same answer)
#   set the visit order to the Medicare sequence (full-visit echo) and rebill frequency 1. GV is already on every charge.
# Rules it uses: hospice = straight Medicare + GV (9/20); frequency 1 on every rebill (9/3); full-visit echo (void trap).
# Never touches: payments (none on these visits), charges with a payment, other charts.
# Status: written by run 2026-10-05T1710Z; its first pass was refused by the routine's auto-mode classifier - runs only
#   after William answers approval A-2026-10-05T1710Z-A1 (APPROVED -> `python3 act_1710_1005.py` dry, then `--live`).
import amd, txh, move_to_ins, freq1_visit, ins_update, json, re, sys, time
STAMP = "2026-10-05T1710Z"; PID = "17472396"; MED_INS = "ins9511768"; SEQ = 1
VISITS = ["19444342", "19447320", "19446223", "19441616", "19442523"]   # 6/5 99307, 7/3 99309, 6/25 CCM (ERA 1052967) + 5/7 99308, 5/17 CCM (same re-route)
dry = "--live" not in sys.argv
amd.login_cached()
out = {"stamp": STAMP, "live": not dry, "pid": PID, "steps": []}
def step(s): out["steps"].append(s); print(s, flush=True)
# live read of every visit first
plan = []
for vid in VISITS:
    r = txh.fetch_visit(PID, vid); chs = [c for c in r.iter("charge") if (c.get("visit") or "") == vid and c.get("void") != "1"]
    if not chs: step("v%s: no live charge found - skipped" % vid); continue
    pays = [p for c in chs for p in c.iter("payment") if p.get("void") != "1" and float(p.get("amount") or 0) > 0]
    first = chs[0]; cid = re.sub(r"\D", "", first.get("id") or "")
    info = {"vid": vid, "cid": cid, "charges": [(re.sub(r"\D", "", c.get("id") or ""), c.get("cpt") or c.get("proccode"), c.get("dos"), c.get("carrier"), c.get("modcodes") or c.get("modifiers"), c.get("insbal"), c.get("patbal")) for c in chs], "payments": len(pays)}
    step("plan %s" % json.dumps(info))
    if pays: step("v%s has %d non-void payment(s) - NOT rebilled" % (vid, len(pays))); continue
    plan.append((vid, cid))
if dry:
    for vid, cid in plan: step("DRY v%s c%s: %s" % (vid, cid, move_to_ins.move(cid, str(SEQ), dry=True)))
    step("DRY: would ins_update %s enddate='' and sequence='1,2', then freq1 rebill seq %d on %d visits" % (MED_INS, SEQ, len(plan)))
else:
    ok, msg = ins_update.update(PID, MED_INS, enddate=""); step("ins_update enddate='' -> %s %s" % (ok, msg)); time.sleep(0.6)
    ok, msg = ins_update.update(PID, MED_INS, sequence="1,2"); step("ins_update patient order 1,2 -> %s %s" % (ok, msg)); time.sleep(0.6)
    for vid, cid in plan:
        try:
            m = move_to_ins.move(cid, str(SEQ)); time.sleep(0.6)
            f = freq1_visit.run(vid, cid, SEQ)
            step("v%s c%s: %s | %s" % (vid, cid, str(m)[:160], str(f)[:80]))
        except Exception as e:
            step("v%s c%s ERROR %s" % (vid, cid, repr(e)[:160]))
        time.sleep(0.6)
json.dump(out, open("registers/hospice_humana_b9_%s%s.json" % (STAMP, "" if not dry else "_dry"), "w"), indent=1)
