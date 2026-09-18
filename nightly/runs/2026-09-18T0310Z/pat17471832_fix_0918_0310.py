# PLAIN ENGLISH (contractual correction on pat17471832, 11pm ET 9/17/2026 run - 2026-09-18T0310Z)
# The Florida Blue lines posted 9/14 from the Availity remits carry patient balance = charge - payment: the remit's CO-45
# contractual was never written off, so the patient holds CO-45 + PR-2. For every paid line whose remit row (parsed from the
# Availity CheckDetails PDFs into inbox/availity/checkdetails_rows_<stamp>.csv) shows a CO-45 amount:
#   1. move_to_ins.move(cid)  - patient balance back to insurance, NO rebill (seq None)
#   2. manual_post.post(cid, "BCBS", 0, CO-45, "WOINS", checknumber=<trace>, depositdate=<check date>, note=...)
#   3. readback: AMD posts the write-off and auto-transfers the remainder (= the remit's PR) to the patient.
# Skips: lines with paid 0 (PR-39 / $0 denials stay for William's 'same'), lines already carrying a WOINS, lines whose
# live patient balance != charge - paid (something else already adjusted them), lines whose remit row is missing.
# Stops after 3 consecutive faults. Register: registers/pat17471832_correction_<stamp>.json. --dry prints the plan only.
import amd, move_to_ins, manual_post, resave, re, json, csv, sys, time
S = "2026-09-18T0310Z"; DRY = "--dry" in sys.argv
amd.login_cached()
pays = json.load(open("registers/pat17471832_payments_%s.json" % S))
rows = list(csv.DictReader(open("inbox/availity/checkdetails_rows_%s.csv" % S)))
byvisit = {}
for r in rows:
    byvisit.setdefault(str(r.get("visit") or "").strip(), []).append(r)
def cas_amount(cas, code):
    m = re.search(r'(?<![A-Z0-9-])%s:([0-9.]+)' % re.escape(code), cas or "")
    return float(m.group(1)) if m else 0.0
def bal(cid):
    x = resave.detail(cid); m = re.search(r'<charge [^>]*id="charge%s"[^>]*>' % cid, x)
    d = dict(re.findall(r'(insbalance|patbalance)="([^"]*)"', m.group(0)))
    wo = [w for w in re.findall(r'<writeoff [^>]*/?>', x) if 'void="0"' in w or 'void=' not in w]
    return d, wo
lines = []; faults = 0
done_already = {"23344347": {"cid": "23344347", "visit": "19437268", "dos": "04/03/2026", "cpt": "99233", "check": "213047694", "wo": 52.74, "cas": "CO-45:52.74;PR-2:53.63", "ok": True, "msg": "corrected first (test line): move 106.37 -> WOINS 52.74 -> patient 53.63"}}
for p in pays:
    cid = p["cid"]
    if cid in done_already:
        lines.append(done_already[cid]); continue
    if float(p["paid"] or 0) <= 0:
        lines.append({"cid": cid, "visit": p["visit"], "dos": p["dos"], "cpt": p["proc"], "check": p["check"], "wo": 0, "cas": "", "ok": False, "msg": "skipped: $0 payment (denial) - William's decision"}); continue
    rr = [r for r in byvisit.get(p["visit"], []) if str(r.get("chargeid") or "").strip() == cid or str(r.get("cpt") or "").strip().endswith(p["proc"])]
    if not rr:
        lines.append({"cid": cid, "visit": p["visit"], "dos": p["dos"], "cpt": p["proc"], "check": p["check"], "wo": 0, "cas": "", "ok": False, "msg": "skipped: no remit row parsed for this visit"}); continue
    r = rr[0]; co = cas_amount(r.get("cas"), "CO-45"); pr = sum(cas_amount(r.get("cas"), c) for c in ("PR-1", "PR-2", "PR-3"))
    if co <= 0:
        lines.append({"cid": cid, "visit": p["visit"], "dos": p["dos"], "cpt": p["proc"], "check": p["check"], "wo": 0, "cas": r.get("cas"), "ok": False, "msg": "skipped: remit shows no CO-45"}); continue
    d, wos = bal(cid)
    exp_pat = round(float(p["fee"]) - float(p["paid"]), 2)
    if wos or abs(float(d.get("patbalance") or 0) - exp_pat) > 0.01 or float(d.get("insbalance") or 0) > 0.005:
        lines.append({"cid": cid, "visit": p["visit"], "dos": p["dos"], "cpt": p["proc"], "check": p["check"], "wo": 0, "cas": r.get("cas"), "ok": False, "msg": "skipped: live state not the plain 'charge - payment on patient' pattern: %s writeoffs=%d" % (d, len(wos))}); continue
    if abs(co + pr + float(p["paid"]) - float(p["fee"])) > 0.02:
        lines.append({"cid": cid, "visit": p["visit"], "dos": p["dos"], "cpt": p["proc"], "check": p["check"], "wo": 0, "cas": r.get("cas"), "ok": False, "msg": "skipped: remit CO %.2f + PR %.2f + paid %s != charge %s" % (co, pr, p["paid"], p["fee"])}); continue
    chk = str(r.get("check") or p["check"]).strip(); cdate = str(r.get("checkdate") or "").strip() or None
    note = "Availity remit %s CO-45 contractual write-off missed on the 9/14 post; patient share PR %.2f - run %s" % (chk, pr, S)
    if DRY:
        lines.append({"cid": cid, "visit": p["visit"], "dos": p["dos"], "cpt": p["proc"], "check": chk, "wo": co, "cas": r.get("cas"), "ok": False, "msg": "DRY: would move %.2f then WOINS %.2f (patient keeps %.2f)" % (exp_pat, co, pr)}); continue
    mv = move_to_ins.move(cid)
    d2, _ = bal(cid)
    if not str(mv).startswith("moved") or float(d2.get("insbalance") or 0) < co - 0.005:
        faults += 1; lines.append({"cid": cid, "visit": p["visit"], "dos": p["dos"], "cpt": p["proc"], "check": chk, "wo": 0, "cas": r.get("cas"), "ok": False, "msg": "FAULT move: %s -> %s" % (mv, d2)})
        if faults >= 3: break
        continue
    ok, msg = manual_post.post(cid, "BCBS", 0.0, co, "WOINS", chk, cdate, note)
    time.sleep(0.8); d3, _ = bal(cid)
    if ok and float(d3.get("insbalance") or 0) < 0.005:
        faults = 0; lines.append({"cid": cid, "visit": p["visit"], "dos": p["dos"], "cpt": p["proc"], "check": chk, "wo": co, "cas": r.get("cas"), "ok": True, "msg": "moved %.2f -> WOINS %.2f -> patient %s" % (exp_pat, co, d3.get("patbalance"))})
    else:
        faults += 1; lines.append({"cid": cid, "visit": p["visit"], "dos": p["dos"], "cpt": p["proc"], "check": chk, "wo": co if ok else 0, "cas": r.get("cas"), "ok": bool(ok), "msg": "post %s %s -> %s" % (ok, msg[:120], d3)})
        if faults >= 3: break
    open("era_manual_post.log", "a").write("pat17471832_fix %s %s wo %.2f -> %s %s\n" % (time.ctime(), cid, co, ok, msg[:100]))
    time.sleep(0.5)
reg = {"stamp": S, "patient": "pat17471832", "lines": lines, "note": "faults stop rule 3; $0-paid denial lines left for William" if faults < 3 else "STOPPED after 3 consecutive faults"}
json.dump(reg, open("registers/pat17471832_correction_%s.json" % S, "w"), indent=1)
ok_l = [l for l in lines if l["ok"]]
print("lines", len(lines), "corrected", len(ok_l), "WOINS %.2f" % sum(l["wo"] for l in ok_l))
for l in lines: print(" ", l["cid"], l["dos"], l["cpt"], l["check"], l["wo"], l["ok"], l["msg"][:110])
