# PLAIN ENGLISH (Exclusions column, 3 AM ET 10/16/2026 run 2026-10-16T0710Z): 17 rows on claim runs 1700302 / 1700305 / 1700294.
# Decides, from the live chart read of this run (registers/visit_read_2026-10-16T0710Z.json, live_read_, elig_amd):
#  A. chart 17478013 (8 VA CCN claims, run 1700305, CH RH PNM10902 INVALID SUBSCRIBER MEMBER ID): the approved card
#     A-2026-10-15T0510Z-H was applied 10/15 23:06Z from the PHI-scrubbed repo copy of its helper, so the Optum VA CCN plan
#     ins9520862 carries the literal placeholder text as its member id (5 characters) and all 8 claims rejected at the
#     clearinghouse. The ICN on the HCA facesheet William pasted on the board row 10/15 03:41Z (Policy #) is written as the
#     member id (ins_update, wrapped updateinsurance shape, patient order 1 verified), the readback must be ICN-shaped
#     (10 digits + V + 6 digits), then each of the 8 visits gets ONE frequency-1 rebill to seq 1 (the auth VA0048867957 and the
#     admission 10/05/2026 are already on the visits - verified read-only this run), then hideexclusions run 1700305.
#  B. chart 17475064 (6 AET07 claims, run 1700302, payer 'SUBSCRIBER AND SUBSCRIBER ID NOT FOUND'): Medicare paid every visit
#     06/09/2026 (check 819190894, CO45/CO253 written off at posting); the open insurance balance is the PR2 coinsurance; Aetna
#     (seq 1) answers INACTIVE on AMD's 271 and 'subscriber not found' on the claim; the Stedi Medicare lookup at the DOS shows
#     Part A/B only (no Advantage entity, only a Part D plan) and a date of death [DOB]. No supplement in force -> the
#     cost-share is written off WOCLTREQ (William 10/13 'nothing stays on the patient balance'; 10/14 rule A: a visit that carries
#     the primary's payment is settled, never rebilled; the 10/15 1110Z precedent for a dead secondary), then hideexclusions.
#  C/D. charts 46253 (v13965945, 99349 01/30/2023) and 20804 (v14003195, 99350 04/27/2023), run 1700302, the same Aetna
#     'subscriber not found': Medicare paid 05/2023 and 07/2023, the open balance is the 2023 PR2 coinsurance, Aetna INACTIVE on
#     the 271. The 10/14 rule for a 2022-23 Medigap balance whose Medicare remit is older than 12 months: WOINS untimely with a
#     dated note, exclusion completed (the secondary window is closed).
#  The AET12 PREF0288 row (chart 24750) is the carrier record - left on its board row.
# Never touches: no plan add, no end-date, no resave, no payment void; writes = updateinsurance (A), chargerebill via
#   freq1_visit.run (A, one per visit, amd.rebill_charge guard + deceased guard), manual_post pay 0.0 + write-off (B, C, D),
#   hideexclusions. --dry default; --live acts; --only <letters>. Register: registers/excl_2026-10-16T0710Z[_dry].json
import amd, manual_post, freq1_visit, ins_update, txh, payreasons, json, sys, time, re
a = sys.argv; LIVE = "--live" in a; S = "2026-10-16T0710Z"
ONLY = a[a.index("--only") + 1].split(",") if "--only" in a else None
SCAN = json.load(open("scan_%s/summary_before.json" % S))
VA_ICN = open("patient_db/17478013/va_icn.txt").read().strip()   # the ICN from the board row note William pasted 10/15 03:41Z - kept in patient_db/ (never in the repo), pid-only file name
ROWS = {}   # pid -> [(run, vid, claim, [(cid, cpt, fee)])]
for run, rows in SCAN["exclusions"].items():
    for r in rows:
        ROWS.setdefault(r["patientid"], []).append((run, r["id"], r["claimid"], [(c["id"], c["chgcode"], float(c["totalfee"])) for c in r["_chgs"]]))
SECTIONS = {
    "A": ("17478013", "rebill", None, "VA CCN member id was the scrubbed placeholder; ICN from William's pasted HCA facesheet written, 8 claims re-sent frequency 1"),
    "B": ("17475064", "writeoff", "WOCLTREQ", "Medicare paid 06/09/2026; Aetna seq 1 INACTIVE on the 271 and 'subscriber not found' on the claim; Stedi at DOS: Part A/B only, deceased [DOB]; no supplement in force"),
    "C": ("46253", "writeoff", "WOINS", "2023 Medigap coinsurance after Medicare's 05/04/2023 remit; secondary window closed (12 months from the primary's remit); Aetna INACTIVE on the 271 and 'subscriber not found'"),
    "D": ("20804", "writeoff", "WOINS", "2023 Medigap coinsurance after Medicare's 07/13/2023 remit; secondary window closed (12 months from the primary's remit); Aetna INACTIVE on the 271 and 'subscriber not found'"),
}
def L(m): print(m, flush=True)
def live(pid, vid):
    return {c["cid"]: c for c in payreasons.visit_state(pid, vid)}
def icn_shaped(s): return bool(re.fullmatch(r"\d{10}V\d{6}", s or ""))
amd.login_cached()
REG = "registers/excl_%s%s.json" % (S, "" if LIVE else "_dry")
rec = {"stamp": S, "live": LIVE, "sections": {}}; faults = 0
for letter, (pid, kind, code, why) in SECTIONS.items():
    if ONLY and letter not in ONLY: continue
    rows = ROWS.get(pid, []); sec = {"pid": pid, "kind": kind, "code": code, "why": why, "visits": [], "hide": {}}
    L("=== section %s chart %s (%d rows) %s" % (letter, pid, len(rows), kind))
    settled = {}
    if kind == "rebill":
        r = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "pat" + pid, "nocookie": "1"}))
        plans = [dict(re.findall(r'(\w+)="([^"]*)"', p)) for p in re.findall(r'<insplan [^>]*>', r)]
        va = [p for p in plans if p.get("carrier") == "car42025"]
        if len(va) != 1: sec["result"] = "HOLD - expected one VA CCN plan, found %d" % len(va); rec["sections"][letter] = sec; continue
        cur = va[0].get("subscribernum") or ""; insid = va[0]["id"]
        sec["plan"] = {"ins": insid, "cur_shape": ("ICN" if icn_shaped(cur) else "placeholder len %d" % len(cur))}
        if icn_shaped(cur) and cur == VA_ICN:
            L("   member id already the ICN - no plan write"); sec["plan"]["written"] = "already in place"
        elif LIVE:
            ok, msg = ins_update.update(pid, insid, subscribernum=VA_ICN)
            sec["plan"]["written"] = {"ok": ok, "msg": str(msg)[:200]}; L("   ins_update subscribernum -> %s %s" % (ok, str(msg)[:160]))
            r2 = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "pat" + pid, "nocookie": "1"}))
            p2 = [dict(re.findall(r'(\w+)="([^"]*)"', p)) for p in re.findall(r'<insplan [^>]*>', r2) if insid in p]
            io = re.search(r'<patient [^>]*insorder="([^"]*)"', r2)
            back = p2[0].get("subscribernum") if p2 else ""
            sec["plan"]["readback"] = {"icn_shaped": icn_shaped(back), "matches": back == VA_ICN, "insorder": io.group(1) if io else None}
            L("   readback: ICN-shaped %s matches %s insorder %r" % (icn_shaped(back), back == VA_ICN, io.group(1) if io else None))
            if not (back == VA_ICN): sec["result"] = "HOLD - member id did not land"; rec["sections"][letter] = sec; json.dump(rec, open(REG, "w"), indent=1); continue
            if not (io and io.group(1).strip()):
                ok3, m3 = ins_update.update(pid, insid, sequence="1"); sec["plan"]["order_fix"] = {"ok": ok3, "msg": str(m3)[:160]}; L("   insorder restore -> %s %s" % (ok3, str(m3)[:120]))
        else:
            L("   DRY: would write subscribernum = ICN (shape %s) on %s (current: %s)" % ("ok" if icn_shaped(VA_ICN) else "BAD", insid, sec["plan"]["cur_shape"]))
        for run, vid, claim, chgs in rows:
            vrec = {"vid": vid, "claim": claim, "run": run, "cid": chgs[0][0], "cpt": chgs[0][1]}
            st = live(pid, vid)
            if any(c["paid"] > 0 for c in st.values()): vrec["result"] = "HOLD - a payment is on the visit"; sec["visits"].append(vrec); continue
            if LIVE:
                res = freq1_visit.run(vid, chgs[0][0], 1); vrec["rebill"] = str(res)[:160]; L("   %s freq1 seq 1 -> %s" % (vid, str(res)[:120]))
                okr = ("204" in str(res)) or ("SKIPPED" in str(res)) or (res is True)
                if okr: vrec["result"] = "re-sent"; settled.setdefault(run, []).append((vid, claim))
                else: vrec["result"] = "HOLD - rebill not accepted"
            else:
                vrec["result"] = "DRY re-send"; settled.setdefault(run, []).append((vid, claim)); L("   DRY %s freq1 seq 1 c%s %s" % (vid, chgs[0][0], chgs[0][1]))
            sec["visits"].append(vrec); time.sleep(0.3)
    else:
        carrier = "AET07"
        for run, vid, claim, chgs in rows:
            st = live(pid, vid); vrec = {"vid": vid, "claim": claim, "run": run, "charges": []}; ok_all = True
            for cid, cpt, fee in chgs:
                ch = st.get(cid)
                if not ch: vrec["charges"].append({"cid": cid, "result": "HOLD - charge not live"}); ok_all = False; continue
                if not any(p["void"] != "1" and p["carrier"] == "FLO02" and p["amount"] > 0 for p in ch["pays"]):
                    vrec["charges"].append({"cid": cid, "result": "HOLD - no Medicare payment on the charge"}); ok_all = False; continue
                if ch["patbalance"] > 0.005: vrec["charges"].append({"cid": cid, "result": "HOLD - patient balance %.2f" % ch["patbalance"]}); ok_all = False; continue
                pr2 = sum(amt for p in ch["pays"] if p["void"] != "1" for cd, amt in p["reasons"] if cd == "PR2")
                bal = round(ch["insbalance"], 2)
                crec = {"cid": cid, "cpt": cpt, "insbal": bal, "pr2": pr2}
                if bal <= 0.005: crec["result"] = "already $0"; vrec["charges"].append(crec); continue
                if abs(bal - pr2) > 0.02: crec["result"] = "HOLD - open balance %.2f is not the PR2 share %.2f" % (bal, pr2); vrec["charges"].append(crec); ok_all = False; continue
                if faults >= 3: crec["result"] = "not attempted - 3 consecutive addpayments faults"; vrec["charges"].append(crec); ok_all = False; continue
                note = "%s %.2f - %s; rejected on claim run %s (%s); run %s" % (code, bal, why[:110], run, claim, S)
                if LIVE:
                    ok, msg = manual_post.post(cid, carrier, 0.0, bal, code, checknumber="EXCL1016", depositdate=None, note=note)
                    crec.update({"ok": ok, "msg": str(msg)[:160]}); L("   %s %s %.2f on c%s -> %s %s" % (vid, code, bal, cid, ok, str(msg)[:100])); time.sleep(0.5)
                    if not ok: faults += 1; ok_all = False
                    else: faults = 0
                else:
                    crec["dry"] = True; L("   %s DRY %s %.2f on c%s %s" % (vid, code, bal, cid, cpt))
                vrec["charges"].append(crec)
            if ok_all:
                if LIVE:
                    after = live(pid, vid); vrec["after"] = {k: (v["insbalance"], v["patbalance"]) for k, v in after.items()}
                    if any(v["insbalance"] > 0.005 or v["patbalance"] > 0.005 for v in after.values()): vrec["result"] = "HOLD - balance still open after the write-off"
                    else: vrec["result"] = "settled"; settled.setdefault(run, []).append((vid, claim))
                else: vrec["result"] = "DRY settled"; settled.setdefault(run, []).append((vid, claim))
            else: vrec["result"] = "HOLD"
            sec["visits"].append(vrec); time.sleep(0.3)
    for run, lst in settled.items():
        if LIVE:
            child = "<visitlist>%s</visitlist>" % "".join('<visit id="%s" claimid="%s"/>' % (vid, claim) for vid, claim in lst)
            r = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": run, "hide": "-1", "nocookie": "1"}, child))
            ok = "Fault" not in r; sec["hide"][run] = {"n": len(lst), "ok": ok, "resp": re.sub(r"\s+", " ", r[:160])}
            L("hideexclusions run %s (%d rows) -> %s" % (run, len(lst), "OK" if ok else re.sub(r"\s+", " ", r[:200])))
        else:
            sec["hide"][run] = {"n": len(lst), "dry": True}; L("DRY hideexclusions run %s: %d rows" % (run, len(lst)))
    rec["sections"][letter] = sec
    json.dump(rec, open(REG, "w"), indent=1)
L("register " + REG)
