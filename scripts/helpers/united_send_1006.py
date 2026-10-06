# PLAIN ENGLISH (William 10/6/2026 04:0xZ: "Send all these United ones and then write them off if they return timely filing")
# Decides: nothing new - applies William's order to chart 12232248's six open 2025 visits ($1,656, balances moved back to insurance
#   at 0330Z on approval A-2026-10-06T0137Z-B). The Florida Blue plan (seq 1) is end-dated 06/21/2025, so every one of these DOS
#   belongs to the AARP Medicare Advantage plan on carrier UNI20 (ins9517757, seq 2, AMD 271 ACTIVE 10/6).
#   Per visit: visit insorder "2" by a no-rebill full-visit echo (skipped when already 2), then ONE frequency-1 reset + ONE
#   chargerebill to sequence 2 (freq1_visit.run). No UHC remit was ever posted on any of them, so frequency 1 (not 7).
# FOLLOW-UP (written into the routines + practices/ehpa/registers/tf_writeoff_watch.json): when UHC answers TIMELY FILING
#   (CO-29) on any of these visits, write the open insurance balance off WOLATE - William's order, no approval card needed.
# Never touches: visits with a non-zero payment, the 2025 visits already written off, any other chart.
# Usage: python3 united_send_1006.py [--live]        register: registers/united_send_1006_<dry|live>.json
import sys, re, json, time
sys.path.insert(0, "/home/claude/unbilled")
import amd, resave, freq1_visit, txh
LIVE = "--live" in sys.argv; PID = "12232248"; SEQ = 2; ORDER = "2"
VISITS = ["19417751", "19417390", "19420985", "19424313", "19424662", "19427156"]
REG = {"stamp": time.strftime("%Y-%m-%dT%H%MZ", time.gmtime()), "live": LIVE, "pid": PID, "order": "William 10/6/2026: send all these United ones; write off if they return timely filing", "steps": []}
def log(*a): s = " ".join(str(x) for x in a); print(s, flush=True); REG["steps"].append(s)
def set_insorder(cid, order):
    vis, pat, allc = resave.visit_charges(cid)
    if (vis.get("insorder") or "") == order: return True, "insorder already %s - resave skipped" % order
    chg = ""
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f] = c.get(f)
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    va = dict(vis.attrib); va["force"] = "1"; va["insorder"] = order
    if not LIVE: return True, "DRY resave %s insorder %s -> %s (%d live charges echoed)" % (vis.get("id"), vis.get("insorder"), order, len(allc))
    r = amd.post(amd.msg("updvisitwithcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
                 "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, v) for k, v in va.items()), chg)))
    time.sleep(0.8)
    if "Fault" in r: return False, "resave FAULT: " + re.sub(r"\s+", " ", r[:300])
    v2, p2, c2 = resave.visit_charges(cid)
    ok = (v2.get("insorder") or "") == order and len(c2) == len(allc)
    return ok, "resave %s insorder now %s, %d live (was %d)" % (vis.get("id"), v2.get("insorder"), len(c2), len(allc))
amd.login_cached()
el = txh.fetch(PID); plan = []
for vid in VISITS:
    chs = [c for c in el.iter("charge") if c.get("visit") == vid and c.get("void") != "1"]
    paid = [p for c in chs for p in c.iter("payment") if p.get("void") != "1" and abs(float(p.get("amount") or 0)) > 0]
    insbal = sum(float(c.get("insbal") or 0) for c in chs)
    log("v%s %s %s ins $%.2f carrier %s%s" % (vid, chs[0].get("dos") if chs else "?", "+".join(c.get("proccode") or "" for c in chs), insbal, chs[0].get("carrier") if chs else "?", " PAID - skipped" if paid else ""))
    if chs and not paid and insbal > 0: plan.append((vid, re.sub(r"\D", "", chs[0].get("id")), insbal))
for vid, cid, bal in plan:
    ok, m = set_insorder(cid, ORDER); log("  v%s c%s order: %s" % (vid, cid, m))
    if not ok: log("  v%s NOT rebilled - order step failed" % vid); continue
    if LIVE:
        time.sleep(0.5); log("  v%s c%s: %s" % (vid, cid, freq1_visit.run(vid, cid, SEQ)))
    else: log("  DRY v%s c%s: freq1_visit.run(%s, %s, %d) - ONE frequency-1 reset + ONE rebill to UNI20" % (vid, cid, vid, cid, SEQ))
log("total $%.2f on %d visits %s" % (sum(b for _, _, b in plan), len(plan), "SENT to UNI20" if LIVE else "(dry)"))
json.dump(REG, open("/home/claude/unbilled/registers/united_send_1006_%s.json" % ("live" if LIVE else "dry"), "w"), indent=1)
