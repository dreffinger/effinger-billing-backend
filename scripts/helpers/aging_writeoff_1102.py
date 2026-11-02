# PLAIN ENGLISH (Old-claims write-off pass, William 11/2/2026 in chat: "old claims over a year likely need to be written off ... cleaned up,
#   logged and removed from the outstanding claims if there isn't really waiting on insurance for them")
# Decides: which open insurance balances the AR aging engine (aging_refresh.py -> aging_latest.json, the standing 10/13-10/15 rules)
#   already marked WRITE OFF AND whose date of service is more than 365 days old get written off tonight, and with which code:
#     'primary unpaid > 12 months from DOS, no adjudication'            -> WOINS   (untimely, dated note)
#     'primary paid, no secondary on the chart -> WOCLTREQ cost-share'  -> WOCLTREQ
#     'secondary balance, primary remit > 12 months old'                -> WOCLTREQ
#     "primary paid > 12 months ago, the secondary's window is closed"  -> WOCLTREQ
#     'WOCAID2ND cost-share'                                            -> WOCAID2ND
#     'CO-29 timely filing'                                             -> WOLATE
#     'CCM ... WONCS'                                                   -> WONCS
#   Every charge is RE-READ LIVE (gettxhistory) and only its live open insurance balance is written off (manual_post never over-applies).
# Never touches: FLO99 / FCC balances (paper-check reconciliation hold), charts worked by today's board answers, visits in
#   tf_writeoff_watch.json, visits with a DOS inside 365 days, patient balances, payments, claims. Resumable: registers/aging_writeoff_<stamp>.json.
# Usage: python3 aging_writeoff_1102.py [--live] [--max N] [--include-recent]
import sys, json, os, time, datetime, re
sys.path.insert(0, "/home/claude/unbilled")
import amd, txh, manual_post
LIVE = "--live" in sys.argv; MX = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 10**9
STAMP = "2026-11-02T0855Z"; REG = "registers/aging_writeoff_%s%s.json" % (STAMP, "" if LIVE else "_dry")
AGING = "/home/user/effinger-billing-backend/reports/button/aging_latest.json"
SKIP_PIDS = {"25558", "17475837", "17472519", "17477039", "47979", "17478213", "17471204", "17475392", "17478229", "12183299", "21593", "17469446", "45011", "17472874", "17471793", "17477533"}
watch = json.load(open("/home/user/effinger-billing-backend/practices/ehpa/registers/tf_writeoff_watch.json"))
WATCH_VIDS = set(str(v.get("visitid") or v.get("visit") or v.get("vid")) for it in (watch if isinstance(watch, list) else watch.get("items", [])) for v in it.get("visits", []))
def code_for(rule):
    r = rule.lower()
    if "wocaid2nd" in r: return "WOCAID2ND"
    if "wolate" in r or "co-29" in r: return "WOLATE"
    if "woncs" in r: return "WONCS"
    if "wocltreq" in r: return "WOCLTREQ"
    if "woins" in r: return "WOINS"
    return None
rows = [r for r in json.load(open(AGING))["rows"] if r.get("rec") == "WRITE OFF"]
rows = [r for r in rows if (r.get("days_dos") or 0) > 365 or "--include-recent" in sys.argv]
rows = [r for r in rows if r.get("payer") != "FLO99" and str(r.get("pid")) not in SKIP_PIDS and str(r.get("visitid")) not in WATCH_VIDS and code_for(r.get("rule") or "")]
print("candidates", len(rows), "$%.2f" % sum(r["bal"] for r in rows), "(dry)" if not LIVE else "(LIVE)")
reg = json.load(open(REG)) if os.path.exists(REG) else {"stamp": STAMP, "live": LIVE, "posted": [], "skipped": [], "failed": []}
done = set((p["cid"]) for p in reg["posted"])
def save(): json.dump(reg, open(REG, "w"), indent=1)
NOTE = "11/2/2026 William in chat: old claims over a year written off and cleaned up - aging rule: %s"
n = 0; tot = 0.0; charts = {}
for r in sorted(rows, key=lambda x: (x["pid"], x["visitid"])):
    if n >= MX: break
    pid, vid, code = str(r["pid"]), str(r["visitid"]), code_for(r["rule"])
    if pid not in charts:
        try: charts[pid] = txh.fetch(pid)
        except Exception as e:
            reg["failed"].append({"pid": pid, "vid": vid, "why": "txh %s" % str(e)[:100]}); save(); continue
    root = charts[pid]
    for c in root.iter("charge"):
        a = c.attrib
        if str(a.get("visit")) != vid or a.get("void") == "1" or (a.get("fee") or "").startswith("-"): continue
        cid = a.get("id"); ins = float(a.get("insbal") or 0)
        if cid in done: continue
        if ins <= 0.004:
            reg["skipped"].append({"pid": pid, "vid": vid, "cid": cid, "why": "insbal 0"}); continue
        car = (a.get("carrier") or r.get("payer") or "").strip()
        if car not in manual_post.CAR: car = r.get("payer")
        if car not in manual_post.CAR:
            reg["skipped"].append({"pid": pid, "vid": vid, "cid": cid, "why": "no carrier code %s" % car}); continue
        if car == "FLO99":
            reg["skipped"].append({"pid": pid, "vid": vid, "cid": cid, "why": "FLO99 hold"}); continue
        entry = {"pid": pid, "vid": vid, "cid": cid, "cpt": a.get("proccode"), "dos": a.get("dos"), "carrier": car, "code": code, "amt": ins, "rule": r["rule"][:90]}
        if not LIVE:
            reg["posted"].append(dict(entry, dry=True)); n += 1; tot += ins; continue
        ok, msg = manual_post.post(cid, car, 0.0, ins, code, "AGING1102", None, NOTE % r["rule"][:120])
        entry["ok"] = ok; entry["msg"] = str(msg)[:160]
        if ok: reg["posted"].append(entry); n += 1; tot += ins
        else: reg["failed"].append(entry)
        save(); time.sleep(0.4)
        if len([f for f in reg["failed"] if not f.get("why")]) >= 5 and n == 0: print("5 faults, stopping"); break
save()
print("posted %d charges $%.2f; skipped %d; failed %d; register %s" % (n, tot, len(reg["skipped"]), len(reg["failed"]), REG))
