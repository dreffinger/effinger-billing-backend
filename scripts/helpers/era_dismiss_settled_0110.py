# PLAIN ENGLISH (Dismiss an ERA check whose every line this run settled by hand - the ERA Center 'Dismiss' click after the ERA-linked posts
#   of era_new_1010_0110.py; 9 PM ET 10/9/2026 slot, run 2026-10-10T0110Z)
# Decides: whether ONE check on the ERA Center unposted list has nothing left to post: every MONEY line of the remit (paymentamount > 0) now
#   carries a non-void payment with this check's payment number on the LIVE charge (gettxhistory visitid=) or sits on a charge at $0
#   insurance balance (residual, William's rule: post the maximum AMD accepts, disregard the rest), and every $0 line was READ by this run -
#   it is in registers/era_new_2026-10-10T0110Z.json as a reversal, a skip (balance already 0), a duplicate or a HOLD whose decision is on the
#   Insurance Refresh Board (board_updates_2026-10-10T0110Z.json). Only then it dismisses the check (POST /api/era/checks/dismiss with the
#   check id as a JSON string - the shape captured from William's own click on 9/7/2026, the same call era_clear.dismiss and
#   era_dismiss_zero.py make) and confirms the check is gone from GET /api/era/checks. era_details/<checkid>.json stays cached;
#   POST /api/era/checks/reversedismiss restores a check if it is ever needed again.
# Why not era_clear.py: era_clear HOLDS a check whose $0 lines carry CAS adjustments ('denial with write-off (cascade handles)') and would
#   'Process Accepted $0' the reversal lines; the denials here are already on the board, so the check only clutters the unposted list.
# Rules it uses: ERA step 5(e) - a check leaves the unposted list only when every line is settled. Any money line without its payment on the
#   charge and with an open insurance balance, any line this run did not record, or a check that still shows unpostedamount > 0 with an
#   unsettled money line = HOLD, nothing written.
# Writes (only with --live): ONE POST /api/era/checks/dismiss per check. Register registers/era_dismiss_settled_<stamp>[_dry].json.
# Never touches: payments, write-offs, balances, plans, claims; never the held Florida Blue check 1052906.
# Usage: cd /home/claude/unbilled && python3 era_dismiss_settled_0110.py <checkid> [<checkid> ...] [--live]
import amd, era_post, txh, json, sys, time, requests
a = sys.argv[1:]; LIVE = "--live" in a; S = "2026-10-10T0110Z"
CIDS = [x for x in a if not x.startswith("--")]
if not CIDS: print("usage: python3 era_dismiss_settled_0110.py <checkid> [...] [--live]"); sys.exit(2)
NEVER = {"1052906"}
RUN = json.load(open("registers/era_new_%s.json" % S))["lines"]
REG = "registers/era_dismiss_settled_%s%s.json" % (S, "" if LIVE else "_dry")
try: out = json.load(open(REG))
except Exception: out = []
def L(m): print(m, flush=True)
def live_pays(pid, vid):
    root = txh.fetch_visit(pid, vid); res = {}
    for c in root.iter("charge"):
        if c.get("void") == "1" or c.get("visit") != str(vid): continue
        res[c.get("id").replace("charge", "")] = {"insbal": float(c.get("insbal") or 0), "checks": [(p.get("checknumber") or "").strip() for p in c.iter("payment") if p.get("void") != "1"]}
    return res
amd.login_cached()
checks = {str(c["id"]): c for c in json.loads(amd.rest_get("/api/era/checks"))}
rc = 0
for CID in CIDS:
    rec = {"checkid": CID, "stamp": S, "live": LIVE, "lines": {"money-posted": 0, "money-residual": 0, "zero-recorded": 0}, "unsettled": []}
    if CID in NEVER: rec["outcome"] = "never - standing hold"; out.append(rec); L("check %s: standing hold, not touched" % CID); rc = 1; continue
    chk = checks.get(CID)
    if not chk: rec["outcome"] = "not on the unposted list"; out.append(rec); L("check %s: not on the list" % CID); continue
    rec.update(carrier=chk.get("systemcarriercode"), eracarrier=chk.get("eracarriername"), paymentnumber=chk.get("paymentnumber"), paymentamount=chk.get("paymentamount"), unposted=chk.get("unpostedamount"))
    det = json.load(open("era_details/%s.json" % CID))["eracheckdetails"]; cache = {}
    for v in det:
        pid = str(v["patientid"]); vid = str(v["visitid"])
        for ch in v.get("charges") or []:
            cid = str(ch["chargedetailid"]); paid = float(ch.get("paymentamount") or 0)
            if paid > 0:
                if vid not in cache: cache[vid] = live_pays(pid, vid); time.sleep(0.25)
                s = cache[vid].get(cid)
                if s and str(chk.get("paymentnumber")) in s["checks"]: rec["lines"]["money-posted"] += 1
                elif s and s["insbal"] <= 0: rec["lines"]["money-residual"] += 1
                else: rec["unsettled"].append((vid, cid, paid, "money line without its payment, insurance balance %s" % (s and s["insbal"])))
            else:
                hit = [r for r in RUN if r["checkid"] == CID and str(r["visitid"]) == vid and str(r["chargedetailid"]) == cid]
                if hit: rec["lines"]["zero-recorded"] += 1
                else: rec["unsettled"].append((vid, cid, 0.0, "$0 line not recorded by this run"))
    if rec["unsettled"]:
        rec["outcome"] = "HOLD - %d unsettled line(s)" % len(rec["unsettled"]); out.append(rec); L("HOLD check %s: %s" % (CID, rec["unsettled"][:5])); rc = 1; continue
    if not LIVE:
        rec["outcome"] = "dry - would dismiss"; out.append(rec); L("DRY check %s %s %s $%s: %s - every line settled; --live dismisses it" % (CID, rec["carrier"], rec["paymentnumber"], rec["paymentamount"], rec["lines"])); continue
    r = requests.post(era_post.API + "/era/checks/dismiss", headers=era_post.H(), data=json.dumps(str(CID)), timeout=60)
    time.sleep(1.5); still = CID in {str(c["id"]) for c in json.loads(amd.rest_get("/api/era/checks"))}
    ok = r.status_code == 200 and ("true" in r.text.lower() or r.text.strip() in ("", "null"))
    rec.update(dismiss_http=r.status_code, dismiss_text=r.text[:160], outcome="dismissed" if ok and not still else ("dismiss answered ok but check still listed" if ok else "dismiss refused"))
    out.append(rec); L("%s: check %s -> %s (HTTP %s) %s" % ("DISMISSED" if rec["outcome"] == "dismissed" else "NOT DISMISSED", CID, rec["outcome"], r.status_code, r.text[:120]))
    if rec["outcome"] != "dismissed": rc = 1
json.dump(out, open(REG, "w"), indent=1)
sys.exit(rc)
