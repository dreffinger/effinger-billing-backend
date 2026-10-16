# PLAIN ENGLISH (Exclusions column, 7 AM ET 10/16/2026 run 2026-10-16T1110Z): claim run 1700302 (10/14 21:08) carries two
#   payer-level HUMANA rejections ('ACK, RETURNED AS UNPROCESSABLE CLAIM - ENTITY NOT FOUND: PATIENT' / 'POLICY CANCELED') on the
#   SECONDARY claims (letters B and D) that the 10/13 patient-balance execution sent. Live read this run
#   (registers/excl_reads_2026-10-16T1110Z.json): both visits already carry MEDICARE's (FLO02) primary payment and the open
#   insurance balance is exactly the Medicare coinsurance the secondary refused; no patient balance.
# Rules (William 10/13 'nothing stays on the patient balance', 10/14 rule A refinement 'a visit that carries the primary's payment is
#   NEVER rolled back or rebilled - it is settled and released', the 10/14 payment-reason settlement codes, and the same two charts'
#   sections B and G of excl_1015_1110.py applied on William's 'go' 10/15 23:15Z):
#   - section A, chart 23456 v19367114 (99497 10/10/2023, $15.16): Humana INACTIVE / 'entity not found', Humana already answered $0
#     NO-PAY on this line 12/02/2023 (check 119337146231103), no supplement in force -> WOCLTREQ (as card A-2026-10-15T1110Z-G);
#   - section B, chart 17475638 v19443047 (99232 05/24/2026, $14.38): Humana H65699623 = Medicaid managed care (271 'MC MEDICAID GATE
#     CAP DIR'); Humana answered POLICY CANCELED on the 2026 crossover claim -> WOCAID2ND (as card A-2026-10-15T1110Z-B).
#   - the Medicare PR-2 share test (paid x 0.2 / (0.8 x 0.98)) decides whether any never-adjusted contractual is WOINS first.
#   Then hideexclusions (claim run 1700302 + visit/claim id) for every settled row. One section per chart (--only <letter>); --dry default.
# Never touches: no chargerebill, no plan edit, no resave, no payment void; writes = manual_post (pay 0.0 + write-off) and hideexclusions.
# Register: registers/excl_2026-10-16T1110Z[_dry].json
import amd, manual_post, txh, json, sys, time, re
a = sys.argv; LIVE = "--live" in a; S = "2026-10-16T1110Z"
ONLY = a[a.index("--only") + 1].split(",") if "--only" in a else None
READ = {"visits": [
    {"pid": "23456", "vid": "19367114", "claim": "19367114B", "run": "1700302", "charges": [{"cid": "22433700", "insbal": 0.0}, {"cid": "22433701", "insbal": 15.16}]},
    {"pid": "17475638", "vid": "19443047", "claim": "19443047D", "run": "1700302", "charges": [{"cid": "23351322", "insbal": 14.38}]},
]}
SECTIONS = {  # letter: (pid, write-off code for the PR share, why)
    "A": ("23456", "WOCLTREQ", "Humana INACTIVE / entity not found; Medicare paid 12/2023 and Humana already answered $0 NO-PAY on this line 12/02/2023; no supplement in force"),
    "B": ("17475638", "WOCAID2ND", "Humana H65699623 = Medicaid managed care (271 'MC MEDICAID GATE CAP DIR'); Medicare paid 06/2026; Humana answered POLICY CANCELED on the 2026 crossover claim"),
}
def L(m): print(m, flush=True)
def live(pid, vid):
    root = txh.fetch_visit(pid, vid); res = {}
    for c in root.iter("charge"):
        if c.get("void") == "1" or c.get("visit") != str(vid): continue
        res[c.get("id").replace("charge", "")] = {"cpt": c.get("proccode"), "fee": float(c.get("fee") or 0), "paid": float(c.get("paid") or 0),
            "insbal": float(c.get("insbal") or 0), "patbal": float(c.get("patbal") or 0), "carrier": c.get("carrier"),
            "pays": [(float(p.get("amount") or 0), (p.get("checknumber") or "").strip(), p.get("carrier"), p.get("void")) for p in c.iter("payment") if p.get("void") != "1"]}
    return res
def plan(ch, code):
    """Split one charge's open balance into (WOINS contractual, chart-code share)."""
    bal = round(ch["insbal"], 2)
    if bal <= 0.005: return []
    medicare = [p for p in ch["pays"] if p[2] == "FLO02" and p[0] < 0]
    if medicare:
        paid = -sum(p[0] for p in medicare)
        pr = round(paid * 0.2 / (0.8 * 0.98), 2)
        if bal > pr + 0.02:
            return [("WOINS", round(bal - pr, 2), "Medicare contractual never adjusted at posting"), (code, pr, "Medicare PR-2 share")]
    return [(code, bal, "open cost-share")]
amd.login_cached()
REG = "registers/excl_%s%s.json" % (S, "" if LIVE else "_dry")
rec = {"stamp": S, "live": LIVE, "sections": {}}
faults = 0
for letter, (pid, code, why) in SECTIONS.items():
    if ONLY and letter not in ONLY: continue
    visits = [v for v in READ["visits"] if v["pid"] == pid]
    sec = {"pid": pid, "code": code, "why": why, "visits": [], "hide": {}}
    L("=== section %s chart %s (%d visits) %s" % (letter, pid, len(visits), code))
    settled_claims = {}   # run -> [(vid, claim)]
    for v in visits:
        vid, claim, run = v["vid"], v["claim"], v["run"]
        st = live(pid, vid); time.sleep(0.25)
        vrec = {"vid": vid, "claim": claim, "run": run, "charges": []}; ok_all = True
        for ch0 in v["charges"]:
            cid = ch0["cid"]; ch = st.get(cid)
            if not ch: vrec["charges"].append({"cid": cid, "result": "HOLD - charge not live"}); ok_all = False; continue
            if abs(ch["insbal"] - ch0["insbal"]) > 0.005 or ch["patbal"] > 0.005:
                vrec["charges"].append({"cid": cid, "result": "HOLD - live state changed since the read (insbal %.2f patbal %.2f)" % (ch["insbal"], ch["patbal"])}); ok_all = False; continue
            if not any(p[0] < 0 for p in ch["pays"]):
                vrec["charges"].append({"cid": cid, "result": "HOLD - no primary payment on the charge"}); ok_all = False; continue
            steps = plan(ch, code)
            crec = {"cid": cid, "cpt": ch["cpt"], "insbal": ch["insbal"], "steps": []}
            if not steps: crec["result"] = "already $0 - nothing to post"; vrec["charges"].append(crec); continue
            if faults >= 3: crec["result"] = "not attempted - 3 consecutive addpayments faults"; vrec["charges"].append(crec); ok_all = False; continue
            carrier = "HUM01"
            for wcode, amt, what in steps:
                note = "%s - %s; secondary rejected on claim run %s (%s); William 10/13-10/14 rules; run %s" % (what, why[:90], run, claim, S)
                if LIVE:
                    ok, msg = manual_post.post(cid, carrier, 0.0, amt, wcode, checknumber="EXCL1016A", depositdate=None, note=note)
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
    rec["sections"][letter] = sec
    json.dump(rec, open(REG, "w"), indent=1)
tot = {}
for letter, sec in rec["sections"].items():
    for v in sec["visits"]:
        for c in v["charges"]:
            for s in c.get("steps", []): tot[s["code"]] = round(tot.get(s["code"], 0) + s["amt"], 2)
L("TOTAL by code: %s   rows settled: %d / %d" % (tot, sum(1 for s in rec["sections"].values() for v in s["visits"] if v["result"] == "settled"), sum(len(s["visits"]) for s in rec["sections"].values())))
