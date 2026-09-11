# PLAIN ENGLISH (Clear the ERA Center unposted list the way William does by hand)
# Decides: For every check still on the ERA Center list: (1) post any line that still carries real money onto a visit with an open balance (era_post.post_check - the Post button); (2) post the leftover $0-payment / $0-adjustment lines (duplicates, info-only) the way 'Process Accepted ($0.00)' does; (3) if no postable money is left on the check, DISMISS it (POST /api/era/checks/dismiss with the check id as a JSON string - captured from William's own click on check 1050132, 9/7/2026). A check with money that still refuses to post is left on the list and reported.
# Rules it uses: never write off a denial line here ($0 pay with an adjustment is not posted - the cascade handles those visits; the check is dismissed because the remit is already read). Payments on visits already at $0 (money posted manually / by the reversal pipeline) are counted, not re-posted. Resumable: 'DISMISS <id>' and 'HOLD <id>' lines in era_clear.log are skipped on rerun.
# Never touches: visit balances beyond what the Post button itself would do. A check whose unvalidated lines ('Procedure codes do not match' etc.) carry money is HELD, never dismissed - lesson of 9/7 when 32 such checks ($7.4K) were dismissed and had to be restored.
# ---
"""Usage: python3 era_clear.py [--dry] [--max N] [--carrier UNI20,FFVA]"""
import era_post, txh, json, sys, time, os, collections, requests, datetime
from era_post import checks, details, batch, locks, build, H, XML, S, L, postable, post_check
dry = "--dry" in sys.argv; mx = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 10**9
carriers = set(sys.argv[sys.argv.index("--carrier") + 1].split(",")) if "--carrier" in sys.argv else None
API = "https://pm-api-103.advancedmd.com/api"
LOGF = "era_clear.log"; DONE = set(l.split()[1] for l in open(LOGF) if l.startswith(("DISMISS ", "HOLD "))) if os.path.exists(LOGF) else set(); CL = open(LOGF, "a")
def Z(m): L(m); CL.write(m + "\n"); CL.flush()
def adj(v): return sum(float(c.get("adjustmentamount") or 0) for c in v.get("charges") or [])
def zero_post(chk, det, zero):
    b = batch(); locks(chk["id"], ",".join(S(v["visitid"]) for v in zero)); body = build(chk, det, zero, b)
    for vis in body["ppmdmsg"]["visitlist"]["visit"]:
        for ch in vis["chargelist"]["charge"]: ch["@adjustmentamount"] = "0"; ch["@payreasonwoamount"] = "0"; ch["@paymentamount"] = "0"
    r = requests.post(XML, headers=H(), data=json.dumps(body), timeout=300)
    return r.status_code == 200 and "Fault" not in r.text and "faultstring" not in r.text, r.text[:200]
TX = {}; REV = []
def charges_of(pid):
    if pid not in TX:
        try: TX[pid] = [ch for ch in txh.fetch("pat%s" % pid).iter("charge") if ch.get("void") != "1"]
        except Exception: TX[pid] = []
    return TX[pid]
def recorded(v):
    """True when the visit already carries a non-void payment; else append a reversal-pipeline record when it only has write-offs."""
    chs = [ch for ch in charges_of(v["patientid"]) if ch.get("visit") == str(v["visitid"])]
    if not chs: return True
    if any(p.get("void") != "1" and float(p.get("amount") or 0) != 0 for ch in chs for p in ch.iter("payment")): return True
    wos = [(ch.get("id"), w.get("id"), w.get("wocode"), w.get("amount"), w.get("date")) for ch in chs for w in ch.iter("writeoff") if w.get("void") != "1"]
    if wos: REV.append({"checkid": None, "visitid": v["visitid"], "patientid": v["patientid"], "patient": v["patientname"], "dos": v["dos"][:10], "era_pay": v["paymentamount"], "writeoffs": wos, "fee": sum(float(ch.get("fee") or 0) for ch in chs)})
    return False
REVF = "era_clear_reversal_%s.json" % datetime.date.today().strftime("%Y%m%d")
def save_rev():
    if not REV: return
    old = json.load(open(REVF)) if os.path.exists(REVF) else []; seen = {(r["checkid"], r["visitid"]) for r in old}
    json.dump(old + [r for r in REV if (r["checkid"], r["visitid"]) not in seen], open(REVF, "w"), indent=1); REV.clear()
def dismiss(cid):
    r = requests.post(API + "/era/checks/dismiss", headers=H(), data=json.dumps(str(cid)), timeout=60)
    return r.status_code == 200 and '"issuccess":true' in r.text, r.text[:120]
allc = checks(); todo = [c for c in allc if str(c["id"]) not in DONE and (not carriers or c["systemcarriercode"] in carriers)]
Z("=== ERA CLEAR %s: %d on the list, %d to do, dry=%s ===" % (time.ctime(), len(allc), len(todo), dry))
cat = collections.Counter(); money = collections.Counter(); n = 0; nd = 0; nz = 0; np_ = 0.0
for chk in sorted(todo, key=lambda x: x["depositdate"]):
    if n >= mx: break
    n += 1
    try: det = details(chk["id"])
    except Exception as e: Z("ERR details %s: %s" % (chk["id"], str(e)[:80])); continue
    vs = det["eracheckdetails"]; pay_lines = [v for v in vs if postable(v)]
    if pay_lines and not dry:
        k, t = post_check(chk); np_ += t; cat["money posted"] += k
        det = details(chk["id"]); vs = det["eracheckdetails"]; pay_lines = [v for v in vs if postable(v)]
    zero = []; held = collections.Counter()
    for v in vs:
        pay = float(v.get("paymentamount") or 0); a = adj(v); bal = float(v.get("insurancebalance") or 0)
        if v.get("errors") or not v.get("processok"):
            if pay > 0: held["not validated with money (manual post: era_manual_post.py)"] += 1; money["unvalidated"] += pay
            else: held["not validated $0"] += 1
        elif pay == 0 and a == 0: zero.append(v)
        elif pay == 0: held["denial with write-off (cascade handles)"] += 1; money["denial writeoff"] += a
        elif bal <= 0:
            if recorded(v): held["money already on the visit"] += 1; money["already posted"] += pay
            else: held["unrecorded payment (reversal pipeline)"] += 1; money["unrecorded"] += pay; REV[-1].update(checkid=chk["id"], check=chk["paymentnumber"], carrier=chk["systemcarriercode"]) if REV and REV[-1]["checkid"] is None else None
        else: held["postable money"] += 1; money["postable"] += pay
    for k, v in held.items(): cat[k] += v
    if dry: Z("DRY %s %s %s: zero %d held %s" % (chk["id"], chk["systemcarriercode"], chk["paymentnumber"], len(zero), dict(held))); continue
    if zero:
        ok, t = zero_post(chk, det, zero); nz += len(zero) if ok else 0
        if not ok: Z("   zero-post failed on %s: %s" % (chk["id"], t.replace("\n", " ")))
    if held.get("postable money") or held.get("unrecorded payment (reversal pipeline)") or held.get("not validated with money (manual post: era_manual_post.py)"):
        save_rev(); Z("HOLD %s %s %s $%s: %d postable / %d unrecorded lines - left on the list" % (chk["id"], chk["systemcarriercode"], chk["paymentnumber"], chk["paymentamount"], held.get("postable money", 0), held.get("unrecorded payment (reversal pipeline)", 0))); continue
    ok, t = dismiss(chk["id"])
    Z("%s %s %s %s $%s: zero-posted %d, held %s -> %s" % ("DISMISS" if ok else "FAILD", chk["id"], chk["systemcarriercode"], chk["paymentnumber"], chk["paymentamount"], len(zero), dict(held) or "-", "ok" if ok else t)); nd += 1 if ok else 0
    time.sleep(0.4)
save_rev()
Z("=== done: %d looked at, money posted $%.2f, %d $0 lines posted, %d checks dismissed; lines %s; $ %s ===" % (n, np_, nz, nd, dict(cat), {k: round(v) for k, v in money.items()}))
