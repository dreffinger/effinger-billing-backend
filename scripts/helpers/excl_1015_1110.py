# PLAIN ENGLISH (Exclusions column, 7 AM ET 10/15/2026 run 2026-10-15T1110Z): claim runs 1700295 / 1700296 carry 100 payer-level
#   rejections ('ACK, RETURNED AS UNPROCESSABLE CLAIM - POLICY CANCELED / ENTITY NOT FOUND / RETURNED TO ENTITY') from HUMANA (89) and
#   VA CCN (11) on the SECONDARY claims the 10/13 patient-balance execution sent (claim letters B-F). Live read this run
#   (registers/excl_read_2026-10-15T1110Z.json): EVERY one of the 100 visits already carries the PRIMARY's payment - Medicare (FLO02)
#   or UHC (UNI20, chart 17468961) paid 2022-2026 - and the open insurance balance is the cost-share the secondary refused.
# Rules (William 10/13 'nothing stays on the patient balance', 10/14 rule A refinement 'a visit that carries the primary's payment is
#   NEVER rolled back or rebilled - it is settled and released', the 10/14 payment-reason settlement codes, card A-2026-10-15T0310Z-A
#   applied on William's 'go' 10/15 03:47Z):
#   - the secondary that answered is a Medicaid-family plan (Humana whose own 271 reads 'MC MEDICAID GATE CAP DIR' - charts 23847,
#     17475638, 24214) -> the coinsurance is written off WOCAID2ND;
#   - the secondary is a dead Humana MA plan (INACTIVE on AMD's 271; charts 22182, 17468961, 23456, 20347, 24205, 17470785, 17470977,
#     17471428, 17477190) or VA CCN 'returned to entity' (chart 17471834, Medicare paid, VA is not a supplement) -> no supplement in
#     force on the DOS -> WOCLTREQ;
#   - where the open balance still holds Medicare's never-adjusted contractual (balance > the PR-2 share of a Medicare-paid line:
#     PR = paid x 0.2 / (0.8 x 0.98) with the 2% sequestration; charts 17477190 x4 lines, 17471834 x2 lines), that part is WOINS and only
#     the PR share takes the chart's code; a UHC-paid residual (chart 17468961) cannot be split without the 2023 remit -> WOCLTREQ whole.
#   - a visit already at $0 (chart 17476855 v19455617 - Medicare + Florida Blue secondary paid 10/14; chart 20347 c20961003, chart
#     24205 c21327694) gets no posting, only its exclusion completed.
#   Then hideexclusions (claim run + visit/claim id) for every settled row. One section per chart (--only <letter>); --dry default.
# Never touches: no chargerebill, no plan edit, no resave, no payment void; writes = manual_post (pay 0.0 + write-off) and hideexclusions.
# Register: registers/excl_2026-10-15T1110Z[_dry].json
import amd, manual_post, txh, json, sys, time, re
a = sys.argv; LIVE = "--live" in a; S = "2026-10-15T1110Z"
ONLY = a[a.index("--only") + 1].split(",") if "--only" in a else None
READ = json.load(open("registers/excl_read_%s.json" % S))
SECTIONS = {  # letter: (pid, write-off code for the PR share, why)
    "A": ("23847", "WOCAID2ND", "Humana H54675873 = Medicaid managed care (271 'MC MEDICAID GATE CAP DIR'); Medicare paid 03/2024; Humana answered POLICY CANCELED on the 2023 crossover claims"),
    "B": ("17475638", "WOCAID2ND", "Humana H65699623 = Medicaid managed care (271 'MC MEDICAID GATE CAP DIR'); Medicare paid 05-06/2026; Humana answered POLICY CANCELED on the 2026 crossover claims"),
    "C": ("24214", "WOCAID2ND", "Humana H06414087 = Medicaid managed care (271 'MC MEDICAID GATE CAP DIR'); Medicare paid 03/2024; Humana answered POLICY CANCELED"),
    "D": ("17476855", "WOCAID2ND", "visit already at $0 (Medicare 819928855 + Florida Blue 190596986 paid) - exclusion completed only"),
    "E": ("22182", "WOCLTREQ", "Humana H71485535 INACTIVE (MA plan dead), Medicare MBI answers AAA 73; Medicare paid 2022-2023; no supplement in force"),
    "F": ("17468961", "WOCLTREQ", "Humana H53803808 INACTIVE and UHC 981508988 INACTIVE; UHC (MA) paid 2023-2024; MA cost-share, no supplement in force"),
    "G": ("23456", "WOCLTREQ", "deceased [DOB]; Humana INACTIVE; Medicare paid 2023-2024 and Humana already answered $0 NO-PAY; no supplement in force"),
    "H": ("20347", "WOCLTREQ", "deceased [DOB]; Humana INACTIVE; Medicare + Humana paid the 99305, the 99497 residual has no payer left"),
    "I": ("24205", "WOCLTREQ", "deceased [DOB]; Humana INACTIVE; Medicare + Humana paid the 99310, the 99497 residual has no payer left"),
    "J": ("17470785", "WOCLTREQ", "Humana H50198160 INACTIVE; Medicare paid 03/2024; no supplement in force"),
    "K": ("17470977", "WOCLTREQ", "Humana H67602920 INACTIVE and already answered $0 NO-PAY twice; Medicare paid 03/2024; no supplement in force"),
    "L": ("17471428", "WOCLTREQ", "deceased [DOB]; Humana INACTIVE; Medicare paid 09/2026; no supplement in force"),
    "M": ("17477190", "WOCLTREQ", "Humana H54884335 INACTIVE; Medicare paid 09-10/2026; the never-adjusted Medicare contractual is WOINS, the PR-2 share WOCLTREQ"),
    "N": ("17471834", "WOCLTREQ", "VA CCN 'returned to entity' on Medicare-paid 2024 SNF visits (deceased [DOB]); VA CCN is not a Medicare supplement - cost-share written off"),
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
            carrier = "VACCN" if letter == "N" else "HUM01"
            for wcode, amt, what in steps:
                note = "%s - %s; secondary rejected on claim run %s (%s); William 10/13-10/14 rules; run %s" % (what, why[:90], run, claim, S)
                if LIVE:
                    ok, msg = manual_post.post(cid, carrier, 0.0, amt, wcode, checknumber="EXCL1015B", depositdate=None, note=note)
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
