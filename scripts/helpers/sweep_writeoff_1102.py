# PLAIN ENGLISH (Claim-status sweep write-offs, William 11/2/2026 in chat: "claims paid but not posted can just be written off as paid
#   not posted in AMD ... these old UNI20 and BCBS claims ... cleaned up, logged and removed from the outstanding claims if there isn't
#   really waiting on insurance for them")
# Decides: for every row of today's claim-status sweep (claimstatus_20261102.json - Stedi 276/277 per visit), which open balances are
#   settled by the payer's answer and with which write-off code (the 10/25 map William approved then, now standing):
#     PAID (F0/F1 with money, no remit posted)                        -> WOINSBANK  'paid not posted' (payer, check, paid date in the note)
#     UNI20 / UHCMA / SIM01 '585 denied or non-covered'               -> WONCS
#     HUM01 '107 processed according to contract'                      -> WOINS      (contractual)
#     'claim/line has been paid' (65)                                  -> WOINSBANK
#     SUN01 '1 see remittance advice'                                  -> WOCLTREQ
#     AET07 '20 accepted for processing' older than 6 months           -> WOCLTREQ   (accepted for months, never adjudicated)
#     CARC 29 / 'timely filing' in the status text                     -> WOLATE
#   HELD on the books (genuinely pending): PENDING, BCBS '38 awaiting next periodic adjudication cycle', AET07 20 inside 6 months,
#   NOT ON FILE (today's cleanup does not re-send; the aging pass / William decide), ERROR / UNKNOWN.
#   Every charge is re-read live (gettxhistory) and only its live open insurance balance is written off, under the carrier the sweep
#   answered for; FLO99 and today's board charts are skipped. Resumable: registers/sweep_writeoff_<stamp>.json.
# Never touches: plans, claims, payments, the ERA Center, visits with a $0 balance. --live writes; default is a dry plan.
# Usage: python3 sweep_writeoff_1102.py [--live] [--max N]
import sys, json, os, time, datetime, re
sys.path.insert(0, "/home/claude/unbilled")
import amd, txh, manual_post
LIVE = "--live" in sys.argv; MX = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 10**9
STAMP = "2026-11-02T0855Z"; SRC = "claimstatus_20261102.json"; REG = "registers/sweep_writeoff_%s%s.json" % (STAMP, "" if LIVE else "_dry")
SKIP_PIDS = {"25558", "17475837", "17472519", "17477039", "47979", "17478213", "17471204", "17475392", "17478229", "12183299", "21593", "17469446", "45011", "17471793", "17477533"}
rows = json.load(open(SRC)); today = datetime.date(2026, 11, 2)
def decide(r):
    act = (r.get("action") or ""); car = r.get("carrier") or ""; st = r.get("status") or []
    txt = " ".join(((s.get("codev") or "") + " " + (s.get("catv") or "")).lower() for s in st)
    codes = [str(s.get("code") or "") for s in st]
    if act.startswith("PAID"):
        chk = ";".join(sorted(set(str(s.get("check") or "") for s in st if s.get("check")))); pd = ";".join(sorted(set(str(s.get("paidDate") or "") for s in st if s.get("paidDate"))))
        paid = ";".join(sorted(set(str(s.get("paid") or "") for s in st if s.get("paid"))))
        return "WOINSBANK", "paid not posted - payer %s reports paid %s on %s chk %s" % (car, paid, pd, chk)
    if act.startswith("PENDING") or act.startswith("NOT ON FILE") or act.startswith(("ERROR", "UNKNOWN")): return None, act
    if "29" in codes or "timely" in txt or "time limit" in txt: return "WOLATE", "payer timely-filing answer: " + txt[:80]
    if "585" in codes or "non-covered" in txt: return "WONCS", "payer finalized 585 denied/non-covered: " + txt[:80]
    if "107" in codes or "according to contract" in txt: return "WOINS", "payer 107 processed per contract: " + txt[:80]
    if "65" in codes or "has been paid" in txt: return "WOINSBANK", "payer says claim/line already paid, no remit posted: " + txt[:80]
    if car == "SUN01" and ("1" in codes or "remittance" in txt): return "WOCLTREQ", "Sunshine 'see remittance advice', nothing collectible: " + txt[:80]
    if "20" in codes or "accepted for processing" in txt:
        try: d = datetime.datetime.strptime(r["dos"][:10], "%Y-%m-%d").date()
        except Exception: d = today
        if (today - d).days > 180: return "WOCLTREQ", "accepted for processing > 6 months, never adjudicated: " + txt[:80]
        return None, "AET 20 inside 6 months - hold"
    if "38" in codes or "awaiting" in txt: return None, "BCBS 38 awaiting adjudication - hold"
    return None, "no rule for: " + txt[:100]
reg = json.load(open(REG)) if os.path.exists(REG) else {"stamp": STAMP, "live": LIVE, "posted": [], "held": [], "skipped": [], "failed": []}
done = set(p["cid"] for p in reg["posted"]); save = lambda: json.dump(reg, open(REG, "w"), indent=1)
n = 0; tot = 0.0; charts = {}
for r in rows:
    if n >= MX: break
    pid, vid, car = str(r.get("patientid")), str(r.get("visitid")), r.get("carrier")
    code, why = decide(r)
    if not code:
        reg["held"].append({"pid": pid, "vid": vid, "carrier": car, "bal": r.get("balance"), "why": why}); continue
    if pid in SKIP_PIDS or car == "FLO99":
        reg["skipped"].append({"pid": pid, "vid": vid, "why": "board chart / FLO99"}); continue
    if pid not in charts:
        try: charts[pid] = txh.fetch(pid)
        except Exception as e: reg["failed"].append({"pid": pid, "vid": vid, "why": str(e)[:100]}); save(); continue
    for c in charts[pid].iter("charge"):
        a = c.attrib
        if str(a.get("visit")) != vid or a.get("void") == "1" or (a.get("fee") or "").startswith("-"): continue
        cid = a.get("id"); ins = float(a.get("insbal") or 0)
        if cid in done: continue
        if ins <= 0.004: reg["skipped"].append({"pid": pid, "vid": vid, "cid": cid, "why": "insbal 0"}); continue
        carc = (a.get("carrier") or car or "").strip()
        if carc not in manual_post.CAR: carc = car
        if carc not in manual_post.CAR: reg["skipped"].append({"pid": pid, "vid": vid, "cid": cid, "why": "no carrier %s" % carc}); continue
        e = {"pid": pid, "vid": vid, "cid": cid, "cpt": a.get("proccode"), "dos": a.get("dos"), "carrier": carc, "code": code, "amt": ins, "why": why}
        if not LIVE: reg["posted"].append(dict(e, dry=True)); n += 1; tot += ins; continue
        ok, msg = manual_post.post(cid, carc, 0.0, ins, code, "SWEEP1102", None, "Sweep 11/2/2026 - William: write off, " + why[:150])
        e["ok"] = ok; e["msg"] = str(msg)[:160]
        (reg["posted"] if ok else reg["failed"]).append(e)
        if ok: n += 1; tot += ins
        save(); time.sleep(0.4)
save()
import collections
print("posted %d charges $%.2f | held %d | skipped %d | failed %d -> %s" % (n, tot, len(reg["held"]), len(reg["skipped"]), len(reg["failed"]), REG))
print("by code:", collections.Counter((p["carrier"], p["code"]) for p in reg["posted"]).most_common(12))
print("held why:", collections.Counter(h["why"][:40] for h in reg["held"]).most_common(10))
