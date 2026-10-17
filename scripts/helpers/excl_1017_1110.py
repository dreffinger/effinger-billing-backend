# PLAIN ENGLISH (Exclusions column, 7 AM ET 10/17/2026 run 2026-10-17T1110Z): claim run 1700305 (10/15) carries one payer-level
#   HUMANA rejection ('ACK, RETURNED AS UNPROCESSABLE CLAIM - ENTITY NOT FOUND: PATIENT') on the SECONDARY claim 19395738E
#   (chart 17472519, 99309 07/05/2024, charge 22468751). Live read this run: MEDICARE (FLO02) paid 71.01 on 09/09/2026 (check
#   816772687), WOINS 51.87 posted the same day, and the open insurance balance 18.12 is exactly Medicare's PR-2 share
#   (71.01 x 0.2 / (0.8 x 0.98)); no patient balance. The chart's Humana plan H60352730 answers INACTIVE on AMD's 271 (no plan text),
#   Humana itself says 'entity not found' - no supplement in force on that DOS.
# Rules (William 10/13 'nothing stays on the patient balance'; 10/14 rule A refinement 'a visit that carries the primary's payment is
#   NEVER rolled back or rebilled - it is settled and released'; the 10/14 settlement codes; the identical case excl_1016_1110.py
#   section A, chart 23456, applied 10/16): WOCLTREQ for the Medicare cost-share, then hideexclusions on run 1700305.
# Never touches: no chargerebill, no plan edit, no resave, no payment void; writes = manual_post (pay 0.0 + write-off) and hideexclusions.
# Register: registers/excl_2026-10-17T1110Z[_dry].json.   Usage: python3 excl_1017_1110.py [--live]
import amd, manual_post, txh, json, sys, time, re
a = sys.argv; LIVE = "--live" in a; S = "2026-10-17T1110Z"
READ = {"visits": [{"pid": "17472519", "vid": "19395738", "claim": "19395738E", "run": "1700305", "charges": [{"cid": "22468751", "insbal": 18.12}]}]}
SECTIONS = {"A": ("17472519", "WOCLTREQ", "Humana H60352730 INACTIVE on the 271 / 'entity not found: patient' on claim run 1700305; Medicare paid 09/09/2026; no supplement in force on the DOS")}
def L(m): print(m, flush=True)
def live(pid, vid):
    root = txh.fetch_visit(pid, vid); res = {}
    for c in root.iter("charge"):
        if c.get("void") == "1" or c.get("visit") != str(vid): continue
        res[c.get("id").replace("charge", "")] = {"cpt": c.get("proccode"), "fee": float(c.get("fee") or 0),
            "insbal": float(c.get("insbal") or 0), "patbal": float(c.get("patbal") or 0), "carrier": c.get("carrier"),
            "pays": [(float(p.get("amount") or 0), (p.get("checknumber") or "").strip(), p.get("carrier"), p.get("void")) for p in c.iter("payment") if p.get("void") != "1"]}
    return res
def plan(ch, code):
    bal = round(ch["insbal"], 2)
    if bal <= 0.005: return []
    medicare = [p for p in ch["pays"] if p[2] == "FLO02" and p[0] < 0]
    if medicare:
        paid = -sum(p[0] for p in medicare); pr = round(paid * 0.2 / (0.8 * 0.98), 2)
        if bal > pr + 0.02: return [("WOINS", round(bal - pr, 2), "Medicare contractual never adjusted at posting"), (code, pr, "Medicare PR-2 share")]
    return [(code, bal, "open cost-share")]
amd.login_cached()
REG = "registers/excl_%s%s.json" % (S, "" if LIVE else "_dry"); rec = {"stamp": S, "live": LIVE, "sections": {}}; faults = 0
for letter, (pid, code, why) in SECTIONS.items():
    visits = [v for v in READ["visits"] if v["pid"] == pid]; sec = {"pid": pid, "code": code, "why": why, "visits": [], "hide": {}}
    L("=== section %s chart %s (%d visits) %s" % (letter, pid, len(visits), code)); settled_claims = {}
    for v in visits:
        vid, claim, run = v["vid"], v["claim"], v["run"]; st = live(pid, vid); time.sleep(0.25)
        vrec = {"vid": vid, "claim": claim, "run": run, "charges": []}; ok_all = True
        for ch0 in v["charges"]:
            cid = ch0["cid"]; ch = st.get(cid)
            if not ch: vrec["charges"].append({"cid": cid, "result": "HOLD - charge not live"}); ok_all = False; continue
            if abs(ch["insbal"] - ch0["insbal"]) > 0.005 or ch["patbal"] > 0.005:
                vrec["charges"].append({"cid": cid, "result": "HOLD - live state changed since the read (insbal %.2f patbal %.2f)" % (ch["insbal"], ch["patbal"])}); ok_all = False; continue
            if not any(p[0] < 0 for p in ch["pays"]):
                vrec["charges"].append({"cid": cid, "result": "HOLD - no primary payment on the charge"}); ok_all = False; continue
            steps = plan(ch, code); crec = {"cid": cid, "cpt": ch["cpt"], "insbal": ch["insbal"], "steps": []}
            if not steps: crec["result"] = "already $0 - nothing to post"; vrec["charges"].append(crec); continue
            if faults >= 3: crec["result"] = "not attempted - 3 consecutive addpayments faults"; vrec["charges"].append(crec); ok_all = False; continue
            for wcode, amt, what in steps:
                note = "%s - %s; secondary rejected on claim run %s (%s); William 10/13-10/14 rules; run %s" % (what, why[:90], run, claim, S)
                if LIVE:
                    ok, msg = manual_post.post(cid, "HUM01", 0.0, amt, wcode, checknumber="EXCL1017A", depositdate=None, note=note)
                    crec["steps"].append({"code": wcode, "amt": amt, "ok": ok, "msg": str(msg)[:160]}); time.sleep(0.5)
                    L("   %s %s %.2f on c%s -> %s %s" % (vid, wcode, amt, cid, ok, str(msg)[:100]))
                    if not ok: faults += 1; ok_all = False; break
                    faults = 0
                else:
                    crec["steps"].append({"code": wcode, "amt": amt, "dry": True}); L("   %s DRY %s %.2f on c%s %s (%s)" % (vid, wcode, amt, cid, ch["cpt"], what))
            crec["result"] = "settled" if ok_all else "FAULT"; vrec["charges"].append(crec)
        if ok_all:
            vrec["after"] = live(pid, vid) if LIVE else None
            if LIVE and any(x["insbal"] > 0.005 or x["patbal"] > 0.005 for x in vrec["after"].values()):
                vrec["result"] = "HOLD - balance still open after the write-offs: %s" % json.dumps(vrec["after"], default=str)[:200]
            else:
                vrec["result"] = "settled"; settled_claims.setdefault(run, []).append((vid, claim))
        else: vrec["result"] = "HOLD"
        sec["visits"].append(vrec)
    for run, lst in settled_claims.items():
        if LIVE:
            child = "<visitlist>%s</visitlist>" % "".join('<visit id="%s" claimid="%s"/>' % (vid, claim) for vid, claim in lst)
            r = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": run, "hide": "-1", "nocookie": "1"}, child))
            ok = "Fault" not in r; sec["hide"][run] = {"n": len(lst), "ok": ok, "resp": re.sub(r"\s+", " ", r[:160])}
            L("hideexclusions run %s (%d rows) -> %s" % (run, len(lst), "OK" if ok else re.sub(r"\s+", " ", r[:200])))
        else:
            sec["hide"][run] = {"n": len(lst), "dry": True}; L("DRY hideexclusions run %s: %d rows" % (run, len(lst)))
    rec["sections"][letter] = sec; json.dump(rec, open(REG, "w"), indent=1)
L("rows settled: %d / %d" % (sum(1 for s in rec["sections"].values() for v in s["visits"] if v["result"] == "settled"), sum(len(s["visits"]) for s in rec["sections"].values())))
