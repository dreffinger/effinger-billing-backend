# PLAIN ENGLISH (Fix the 21 checks left in ERA Center, 9/7/2026 late)
# Decides: On 9/6 the manual-post pass took the $0 DENIAL line of several 2024 UHC checks instead of the PAYMENT line, so McHome, Fierro, Neill and White Judith show a $0 payment and a full write-off where UHC actually paid ($1,850). Jones Pearl's 2024 repayment ($231.84) was never posted (bulk-written-off 5/30). Wallace Diane's Humana payment ($114.76, 8/2026) never posted ('procedure codes do not match'). This script voids the wrong write-offs, posts the real payments with the remainder written off, fixes two reversal mistakes (Posey: $88.84 over-posted on the 99239 the payer did not repay; Docter: a $97.39 takeback recorded as a payment), then dismisses every check that is now fully accounted for (denial-only checks belong to the cascade / tonight's over-12-month write-off).
# Rules it uses: void_tx.void_writeoff / void_payment, manual_post.post (pay + WOINS, check number and deposit date from the ERA), era_post dismiss endpoint. Resumable via era_fix_0907.log.
# Never touches: Visits not listed here.
# ---
"""Usage: python3 era_fix_0907.py [--dry]"""
import amd, txh, resave, manual_post, void_tx, era_post, requests, json, sys, time, os, re
amd.login_cached(); dry = "--dry" in sys.argv
LOGF = "era_fix_0907.log"; done = set(l.split()[1] for l in open(LOGF) if l.startswith(("POST ", "VOIDWO ", "VOIDPAY ", "WO ", "DISMISS "))) if os.path.exists(LOGF) else set(); LOG = open(LOGF, "a")
def L(m): print(m, flush=True); LOG.write(m + "\n"); LOG.flush()
CHECKS = {c["id"]: c for c in json.load(open("era_checks_left_0907.json"))}
def dd(cid): d = CHECKS[cid]["depositdate"][:10]; return "%s/%s/%s" % (d[5:7], d[8:10], d[:4])
def carrier(cid): k = CHECKS[cid]["systemcarriercode"]; return k if k in manual_post.CAR else "UNI20"
# (checkid, patientid, visitid, {proccode: payment}, void_wo_dates)
FIX = [
 (1050814, "12231743", "19391567", {"99306": 177.01, "99497": 58.67}, ["09/06/2026"]),
 (1050814, "12231743", "19391623", {"99223": 135.14, "99497": 58.67}, ["09/06/2026"]),
 (1050814, "12231743", "19391710", {"99232": 61.54}, ["09/06/2026"]),
 (1050814, "12231743", "19391724", {"99232": 61.54}, ["09/06/2026"]),
 (1050814, "12231743", "19391790", {"99232": 61.54}, ["09/06/2026"]),
 (1050814, "12231743", "19391862", {"99232": 61.54}, ["09/06/2026"]),
 (1050820, "17471916", "19392363", {"99233": 116.16}, ["09/06/2026"]),
 (1050820, "17471916", "19392383", {"99233": 116.16}, ["09/06/2026"]),
 (1050836, "17471916", "19392443", {"99233": 116.16}, ["09/06/2026"]),
 (1050822, "17471916", "19392523", {"99232": 61.54}, ["09/06/2026"]),
 (1050822, "17471916", "19392571", {"99233": 116.16}, ["09/06/2026"]),
 (1050875, "17471793", "19392531", {"99223": 168.93, "99497": 73.34}, ["09/06/2026"]),
 (1050875, "17471793", "19392576", {"99232": 76.93}, ["09/06/2026"]),
 (1050849, "17471216", "19385396", {"99349": 97.39}, ["09/06/2026"]),
 (1051243, "25150", "19376052", {"99306": 174.12, "99497": 57.72}, ["05/30/2026"]),
 (1051025, "17477353", "19450772", {"99344": 114.76}, []),
]
tot = 0.0
for chk, pid, vid, pays, wodates in FIX:
    root = txh.fetch(pid); chs = [c for c in root.iter("charge") if c.get("visit") == vid and c.get("void") != "1"]
    for c in chs:
        cid = c.get("id"); code = c.get("proccode")
        if code not in pays: continue
        for w in c.iter("writeoff"):
            if w.get("void") != "1" and w.get("date") in wodates and ("VOIDWO %s" % w.get("id")) not in ("VOIDWO " + x for x in done) and w.get("id") not in done:
                if dry: L("DRY VOIDWO %s %s %s %s $%s" % (w.get("id"), c.get("patient"), code, w.get("wocode"), w.get("amount"))); continue
                ok, msg = void_tx.void_writeoff(pid, cid, w.get("id")); L("%s %s %s %s %s $%s %s" % ("VOIDWO" if ok else "VOIDWOFAIL", w.get("id"), c.get("patient"), code, w.get("wocode"), w.get("amount"), "" if ok else msg[:80])); time.sleep(0.3)
        if cid in done: continue
        pay = pays[code]
        x = resave.detail(cid); m = re.search(r'<charge [^>]*id="charge%s"[^>]*>' % cid, x).group(0); bal = float(re.search(r'insbalance="([^"]*)"', m).group(1) or 0); pb = float(re.search(r'patbalance="([^"]*)"', m).group(1) or 0)
        if not dry and bal < pay and pb > 0:
            import move_to_ins; L("MOVE %s %s %s patient balance %.2f -> insurance: %s" % (cid, c.get("patient"), code, pb, move_to_ins.move(cid))); time.sleep(0.5)
            x = resave.detail(cid); m = re.search(r'<charge [^>]*id="charge%s"[^>]*>' % cid, x).group(0); bal = float(re.search(r'insbalance="([^"]*)"', m).group(1) or 0)
        if bal <= 0.005: L("SKIP %s %s %s balance already 0" % (cid, c.get("patient"), code)); continue
        wo = round(bal - pay, 2)
        if wo < 0: L("SKIP %s %s %s pay %.2f > balance %.2f" % (cid, c.get("patient"), code, pay, bal)); continue
        if dry: L("DRY POST %s %s %s pay %.2f wo %.2f (bal %.2f) check %s" % (cid, c.get("patient"), code, pay, wo, bal, CHECKS[chk]["paymentnumber"])); tot += pay; continue
        ok, msg = manual_post.post(cid, carrier(chk), pay, wo, "WOINS", CHECKS[chk]["paymentnumber"], dd(chk), note="ERA line re-posted 9/7 (9/6 pass posted the $0 denial line instead of the payment)")
        L("%s %s %s %s pay %.2f wo %.2f %s" % ("POST" if ok else "POSTFAIL", cid, c.get("patient"), code, pay, wo, "" if ok else msg[:100])); tot += pay if ok else 0; time.sleep(0.3)
# Posey: the 99239 (9/5/2024) got $88.84 posted on 9/5 but the payer's repayment left it out -> void that payment, write the 88.84 off (untimely).
# Docter: the -97.39 line was a takeback of a never-posted payment; it was recorded as a payment -> void it, write 97.39 off (untimely).
for pid, vid, code, amt, note in [("17472047", "19389121", "99239", 88.84, "payer reversal 9/5/2024 - repayment excluded this line; untimely"), ("12232591", "19380365", "99349", 97.39, "takeback of a payment that was never posted; untimely")]:
    root = txh.fetch(pid)
    for c in root.iter("charge"):
        if c.get("visit") != vid or c.get("proccode") != code or c.get("void") == "1": continue
        cid = c.get("id")
        for p in c.iter("payment"):
            if p.get("void") != "1" and abs(abs(float(p.get("amount") or 0)) - amt) < 0.01 and p.get("id") not in done:
                if dry: L("DRY VOIDPAY %s %s %s $%s" % (p.get("id"), c.get("patient"), code, p.get("amount"))); continue
                ok, msg = void_tx.void_payment(pid, cid, p.get("id")); L("%s %s %s %s $%s %s" % ("VOIDPAY" if ok else "VOIDPAYFAIL", p.get("id"), c.get("patient"), code, p.get("amount"), "" if ok else msg[:80])); time.sleep(0.5)
                if ok:
                    ok2, msg2 = manual_post.post(cid, "UNI20", 0.0, amt, "WOINS", note=note); L("%s %s %s %s $%.2f %s" % ("WO" if ok2 else "WOFAIL", cid, c.get("patient"), code, amt, "" if ok2 else msg2[:80]))
# dismiss everything that is now accounted for
DISMISS = [1051367, 1051562, 1051243, 1051517, 1050814, 1050849, 1050820, 1050822, 1050875, 1050836, 1050727, 1050270, 1050229, 1050213, 1051090, 1051025, 1051568, 1051569, 1051573, 1051575]
for cid in DISMISS:
    if str(cid) in done: continue
    if dry: L("DRY DISMISS %s" % cid); continue
    r = requests.post(era_post.API + "/era/checks/dismiss", headers=era_post.H(), data=json.dumps(str(cid)), timeout=60); ok = r.status_code == 200 and '"issuccess":true' in r.text
    L("%s %s %s %s" % ("DISMISS" if ok else "DISMISSFAIL", cid, CHECKS[cid]["paymentnumber"], "" if ok else r.text[:100])); time.sleep(0.3)
L("=== done: re-posted $%.2f ===" % tot)
