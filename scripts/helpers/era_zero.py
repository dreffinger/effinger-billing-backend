# PLAIN ENGLISH (Clear the ERA Center list - post the $0 lines the way the 'Process Accepted' button does)
# Decides: For every check still on the ERA Center unposted list, posts the remaining validated lines that carry $0 payment AND $0 adjustment (denial / duplicate / info-only lines) - exactly what William's 'Process Accepted ($0.00)' click did on check 1050115 (V5791585) on 9/7. Those postings change no balance; they just record the remit so the check leaves the list.
# Rules it uses: era_post.build/locks (same posterapayments message as the Post button). Lines with $0 pay but a NON-zero adjustment (a write-off) are NOT posted - they are listed for review. Lines with a payment on a visit already at $0 (money posted manually / by the reversal pipeline) cannot be re-posted through the ERA - listed.
# Never touches: balances, write-offs, checks with unposted money that era_post can still post normally (run era_post first).
# ---
"""Usage: python3 era_zero.py [--dry] [--max N] [--carrier UNI20,FFVA]"""
import era_post, json, sys, time, os, collections, requests
from era_post import checks, details, batch, locks, build, H, XML, S, L
dry = "--dry" in sys.argv; mx = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 10**9
carriers = set(sys.argv[sys.argv.index("--carrier") + 1].split(",")) if "--carrier" in sys.argv else None
DONE = set(l.split()[1] for l in open("era_zero.log") if l.startswith("ZERO ")) if os.path.exists("era_zero.log") else set()
ZL = open("era_zero.log", "a")
def Z(m): L(m); ZL.write(m + "\n"); ZL.flush()
def adj(v): return sum(float(c.get("adjustmentamount") or 0) for c in v.get("charges") or [])
allc = checks(); todo = [c for c in allc if str(c["id"]) not in DONE and (not carriers or c["systemcarriercode"] in carriers)]
Z("=== ERA ZERO %s: %d checks on the list, %d to look at, dry=%s ===" % (time.ctime(), len(allc), len(todo), dry))
cat = collections.Counter(); money = collections.Counter(); n = 0; posted = 0; cleared = 0
for chk in sorted(todo, key=lambda x: x["depositdate"]):
    if n >= mx: break
    n += 1
    try: det = details(chk["id"])
    except Exception as e: Z("ERR details %s: %s" % (chk["id"], str(e)[:80])); continue
    vs = det["eracheckdetails"]; zero = []; hold = []
    for v in vs:
        pay = float(v.get("paymentamount") or 0); a = adj(v); bal = float(v.get("insurancebalance") or 0)
        if v.get("errors") or not v.get("processok"): cat["error/not validated"] += 1; hold.append(("ERR", v)); continue
        if pay == 0 and a == 0: zero.append(v); cat["$0 pay $0 adj -> post"] += 1
        elif pay == 0: cat["$0 pay with write-off %.2f -> review" % 0] += 1; money["writeoff"] += a; hold.append(("WO", v))
        elif bal <= 0: cat["payment on $0-balance visit -> already posted elsewhere"] += 1; money["dup"] += pay; hold.append(("DUP", v))
        else: cat["postable money (run era_post)"] += 1; money["postable"] += pay; hold.append(("PAY", v))
    if not zero:
        Z("check %s %s %s: nothing to zero-post (%d lines held)" % (chk["id"], chk["systemcarriercode"], chk["paymentnumber"], len(hold))); continue
    if dry: Z("DRY check %s %s %s: would zero-post %d lines, hold %d" % (chk["id"], chk["systemcarriercode"], chk["paymentnumber"], len(zero), len(hold))); continue
    b = batch(); locks(chk["id"], ",".join(S(v["visitid"]) for v in zero))
    body = build(chk, det, zero, b)
    for vis in body["ppmdmsg"]["visitlist"]["visit"]:            # belt and braces: nothing but $0 goes out
        for ch in vis["chargelist"]["charge"]: ch["@adjustmentamount"] = "0"; ch["@payreasonwoamount"] = "0"; ch["@paymentamount"] = "0"
    r = requests.post(XML, headers=H(), data=json.dumps(body), timeout=300)
    ok = r.status_code == 200 and "Fault" not in r.text and "faultstring" not in r.text
    Z("%s %s %s %s: zero-posted %d lines -> HTTP %s ok=%s%s" % ("ZERO" if ok else "FAILZ", chk["id"], chk["systemcarriercode"], chk["paymentnumber"], len(zero), r.status_code, ok, "" if ok else " " + r.text[:300].replace("\n", " ")))
    if ok: posted += len(zero); cleared += 1 if not hold else 0
    time.sleep(0.6)
Z("=== done: %d checks looked at, %d $0 lines posted, %d checks should now be off the list; line categories %s; $ %s ===" % (n, posted, cleared, dict(cat), {k: round(v) for k, v in money.items()}))
