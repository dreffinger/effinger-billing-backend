# PLAIN ENGLISH (coinsurance back to the secondary after the CO-45 correction, 7 AM ET 10/17/2026 run 2026-10-17T1110Z)
# Decides: nothing new. era_co45_relink.py voided the Post-button payments of Medicare check 1053199 (819996619) and re-posted
#   each line ERA-linked with its WOINS contractual; the ERA-linked re-post left every PR-2 coinsurance on the PATIENT balance,
#   also on charts whose chart carries a LIVE secondary plan (Florida Blue, United American, Humana) that the Post button had
#   already queued a secondary claim to (charge carrier/billdate 10/17/2026). Rule (prompt step 5d): PR amounts are never written
#   off - they stay for the SECONDARY when the chart has one in the order, and as the patient balance only when there is none.
# Does (--live): for every corrected line in registers/era_co45_relink_1053199_<stamp>.json whose chart has an ACTIVE non-Medicare
#   plan (no end date, or end date on/after the DOS): move_to_ins.move(cid, "<medicare seq>,<secondary seq>", rebill=False) = the
#   patient balance back to insurance and the visit order Medicare, secondary - NO rebill (the secondary claim the Post button queued
#   stays the one claim; a second send would draw OA-18). Charts with Medicare only: the PR stays on the patient (correct).
# Never touches: payments, write-offs, plans, claims (no chargerebill), charges not in the relink register.
#   python3 pr_moveback_1110.py           # dry      python3 pr_moveback_1110.py --live   # register registers/pr_moveback_2026-10-17T1110Z.json
import amd, move_to_ins, txh, json, sys, re, time, glob, datetime
LIVE = "--live" in sys.argv; S = "2026-10-17T1110Z"
REL = sorted(f for f in glob.glob("registers/era_co45_relink_1053199_*.json") if not f.endswith("_dry.json"))[-1]
lines = json.load(open(REL))["lines"]
FB = "registers/era_manual_register.json"
amd.login_cached()
PL = {}
def plans(pid):
    if pid not in PL:
        d = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "pat" + pid, "nocookie": "1"}), timeout=60)
        PL[pid] = ([dict(re.findall(r'(\w+)="([^"]*)"', p)) for p in re.findall(r'<insplan [^>]*>', d)], (re.search(r'insorder="([^"]*)"', d) or [None, None])[1] if re.search(r'insorder="([^"]*)"', d) else None)
        time.sleep(0.3)
    return PL[pid]
def mdy(s):
    try: m, d, y = s.split("/"); return datetime.date(int(y), int(m), int(d))
    except Exception: return None
reg = {"stamp": S, "live": LIVE, "source": REL, "items": []}
# the fallback-posted line (v19442523 99489, chart 17472396) is corrected the same way
extra = [{"pid": "17472396", "vid": "19442523", "cid": "23350698", "cpt": "99489", "pr": 8.92, "dos": "05/17/2026", "after": {}}]
for ln in lines + extra:
    if ln.get("after") is None and ln not in extra: continue
    pid, vid, cid = ln["pid"], ln["vid"], ln["cid"]
    ps, order = plans(pid)
    root = txh.fetch_visit(pid, vid); time.sleep(0.3)
    ch = next((c for c in root.iter("charge") if c.get("id") == cid or c.get("id") == "charge" + cid), None)
    if ch is None: reg["items"].append({"pid": pid, "vid": vid, "cid": cid, "action": "SKIP - charge not found live"}); continue
    pat = float(ch.get("patbal") or 0); ins = float(ch.get("insbal") or 0); dos = mdy(ch.get("begindate") or ln.get("dos") or "") or datetime.date.today()
    med = [p for p in ps if p.get("carrier") == "car6085"]
    sec = [p for p in ps if p.get("carrier") != "car6085" and (not p.get("enddate") or (mdy(p.get("enddate")) or dos) >= dos)]
    rec = {"pid": pid, "vid": vid, "cid": cid, "cpt": ch.get("proccode"), "patbal": pat, "insbal": ins, "carrier": ch.get("carrier"), "billdate": ch.get("billdate"), "chart_order": order,
           "secondary": [(p.get("carrier"), p.get("sequence"), p.get("enddate")) for p in sec]}
    if pat <= 0.005: rec["action"] = "nothing on the patient - leave"
    elif not med or not sec: rec["action"] = "Medicare only on the chart - PR %.2f stays on the patient (correct)" % pat
    else:
        order_new = "%s,%s" % (med[0]["sequence"], sec[0]["sequence"])
        if not LIVE: rec["action"] = "DRY move_to_ins %.2f -> insurance, visit order %s, no rebill" % (pat, order_new)
        else:
            r = move_to_ins.move(cid, order_new, rebill=False); time.sleep(0.6)
            rec["result"] = str(r)[:200]; rec["action"] = "moved"
            root2 = txh.fetch_visit(pid, vid); ch2 = next((c for c in root2.iter("charge") if c.get("id") in (cid, "charge" + cid)), None)
            rec["after"] = {"patbal": ch2.get("patbal"), "insbal": ch2.get("insbal"), "carrier": ch2.get("carrier"), "billdate": ch2.get("billdate")} if ch2 is not None else None
    print(json.dumps(rec, default=str)); reg["items"].append(rec)
    json.dump(reg, open("registers/pr_moveback_%s%s.json" % (S, "" if LIVE else "_dry"), "w"), indent=1, default=str)
n = sum(1 for i in reg["items"] if i.get("action", "").startswith(("DRY move", "moved"))); tot = sum(i.get("patbal", 0) for i in reg["items"] if i.get("action", "").startswith(("DRY move", "moved")))
print("lines to move: %d, $%.2f; saved registers/pr_moveback_%s%s.json" % (n, tot, S, "" if LIVE else "_dry"))
