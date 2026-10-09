# PLAIN ENGLISH (Medicare $0 remit 350045840 = ERA check 1053024, worked by the 9 AM ET 10/7/2026 run 2026-10-07T1310Z; the 7 AM run
#   classified the 34 denial claims and could not write - this helper does the writes its digest named for the next run)
# Decides: nothing new - applies William's standing rules to the hospice (CO-B9) claims of the check:
#   (1) CCM 99487+99489 under hospice (William 10/4/2026 "CCM charges billed to hospice patients don't pay"): the four CO-B9 CCM claims
#       (v19455831 pat17476032, v19455709 pat12183032, v19455668 pat17473245, v19455956 pat22603, $315 each) are written off WONCS
#       through the ERA-LINKED Payment Entry shape (payreasons.post_line, pay 0, wo = the remit's CO-B9 amount per line) so the remit's
#       reason codes ride the posting and the visit never lands in Unbilled 'payment reason codes'. Guard per charge: the live open
#       insurance balance must equal the remit adjustment and no non-void payment > 0 may sit on the charge; otherwise the line is
#       listed, not written.
#   (2) E&M 99308 under hospice (William 9/20/2026 "a hospice denial = add the GV modifier and rebill"): v19456187 pat12182946 (charge
#       23367811, Medicare seq 2) and v19456215 pat44987 (charge 23367839, Medicare seq 2) get GV (mcode713) on every live charge
#       through gv_rebill.add_gv (full-visit echo) and ONE frequency-1 rebill (freq1_visit.run) to the Medicare sequence. Guard: no
#       non-void payment > 0, no GV already present.
#   (3) RECORD ONLY (no write): v19456208 pat17477313 CO-B9 = the POYNOR standing flag (board row [name]-17477313, William's GV/GW
#       word); v19456837 pat17474493 CO-109 = Medicare's answer to the pre-re-route claim (UHC Dual Complete rebill already out 10/6);
#       the 26 CO-151 + CO-234 CCM claims = board rows on William's turn (appeal or WONCS) created by the 7 AM run.
# Reads first: era_details/1053024.json (the remit, cached by era_step_b), the chart's live tx history (payreasons.visit_state).
# Writes (only with --live): per CCM charge ONE ERA-linked addpayments (WONCS); per 99308 visit ONE updvisitwithcharges (GV) + ONE
#   freq-1 reset + chargerebill. Three consecutive addpayments faults stop the run. Register registers/era_1053024_2026-10-07T1310Z[_dry].json
# Never touches: the CO-151 cluster, the Poynor visit, the CO-109 visit, payments, plans, hospitalizationto, group numbers.
# Usage: cd /home/claude/unbilled && python3 era_1053024_1310.py [--live]
import amd, payreasons, gv_rebill, freq1_visit, json, sys, time, re
LIVE = "--live" in sys.argv
S = "2026-10-07T1310Z"; CHECK = "1053024"
amd.login_cached()
NOW = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
d = payreasons.details(CHECK)
claims = {str(v["visitid"]): v for v in d.get("eracheckdetails", [])}
out = {"stamp": S, "check": CHECK, "live": LIVE, "at": NOW, "ccm_woncs": [], "hospice_gv": [], "record_only": [], "errors": []}
def L(m): print(m, flush=True)

CCM = [("17476032", "19455831"), ("12183032", "19455709"), ("17473245", "19455668"), ("22603", "19455956")]
HOSP = [("12182946", "19456187", "23367811", "2"), ("44987", "19456215", "23367839", "2")]
faults = 0
# (1) CCM hospice -> WONCS ERA-linked, line by line
for pid, vid in CCM:
    v = claims.get(vid)
    if not v: out["errors"].append("v%s not on the remit" % vid); L("v%s not on remit" % vid); continue
    chk = payreasons.check_meta(CHECK, v)
    st = payreasons.visit_state(pid, vid)
    for ch in v["charges"]:
        cid = str(ch["chargedetailid"]); adj = round(float(ch.get("adjustmentamount") or 0), 2)
        codes = sorted(set(c.get("reasoncode") for c in (ch.get("carc") or [])))
        rec = {"pid": pid, "vid": vid, "cid": cid, "cpt": ch.get("chargecode"), "adj": adj, "carc": codes}
        live = [c for c in st if c["cid"] == cid]
        if not live: rec["result"] = "SKIP - charge not live on the chart"; out["ccm_woncs"].append(rec); L(rec); continue
        c = live[0]; paid = [p for p in c["pays"] if p["void"] != "1" and p["amount"] > 0]
        prior = [w for w in c["wos"] if w["void"] != "1" and w["code"].strip() == "WONCS"]
        rec["insbalance"] = c["insbalance"]; rec["patbalance"] = c["patbalance"]
        if prior: rec["result"] = "already written off WONCS %s" % [(w["id"], w["amount"]) for w in prior]; out["ccm_woncs"].append(rec); L(rec); continue
        if paid: rec["result"] = "SKIP - payment on the charge %s" % [(p["id"], p["amount"]) for p in paid]; out["ccm_woncs"].append(rec); L(rec); continue
        if codes != ["COB9"]: rec["result"] = "SKIP - not a pure CO-B9 line"; out["ccm_woncs"].append(rec); L(rec); continue
        if abs(c["insbalance"] - adj) > 0.011: rec["result"] = "SKIP - live insurance balance %.2f != remit adjustment %.2f" % (c["insbalance"], adj); out["ccm_woncs"].append(rec); L(rec); continue
        if not LIVE: rec["result"] = "DRY: post_line pay 0.00 wo %.2f WONCS (ERA-linked, check %s)" % (adj, chk.get("paymentnumber")); out["ccm_woncs"].append(rec); L(rec); continue
        if faults >= 3: rec["result"] = "STOPPED - 3 consecutive addpayments faults"; out["ccm_woncs"].append(rec); L(rec); continue
        try:
            ok, payid, resp = payreasons.post_line(pid, vid, chk, v, cid, ch, pay=0.0, wo=adj, wocode="WONCS")
            rec["result"] = "posted" if ok else "FAULT"; rec["paymentid"] = payid; rec["resp"] = resp[:160]
            faults = 0 if ok else faults + 1
        except Exception as e:
            rec["result"] = "ERROR %s" % e; faults += 1; out["errors"].append(rec["result"])
        out["ccm_woncs"].append(rec); L(rec); time.sleep(1.0)
    if LIVE:
        after = payreasons.visit_state(pid, vid)
        out["ccm_woncs"].append({"pid": pid, "vid": vid, "after": [(c["cid"], c["insbalance"], c["patbalance"], [(w["code"].strip(), w["amount"]) for w in c["wos"] if w["void"] != "1"]) for c in after],
                                 "balanced": payreasons.balanced(after)})
        L("   after v%s: %s balanced=%s" % (vid, out["ccm_woncs"][-1]["after"], out["ccm_woncs"][-1]["balanced"]))
# (2) 99308 hospice -> GV + frequency-1 rebill to Medicare
for pid, vid, cid, seq in HOSP:
    rec = {"pid": pid, "vid": vid, "cid": cid, "seq": seq}
    st = payreasons.visit_state(pid, vid)
    paid = [(c["cid"], p["id"], p["amount"]) for c in st for p in c["pays"] if p["void"] != "1" and p["amount"] > 0]
    if paid: rec["result"] = "SKIP - payment posted %s" % paid; out["hospice_gv"].append(rec); L(rec); continue
    det = amd.post(amd.msg("getchargedetaildataicd10", "chargeentry", {"chargeid": "charge" + cid, "nocookie": "1"}), timeout=120) if hasattr(amd, "msg") else ""
    mods = re.findall(r'<modcode [^>]*code="([^"]*)"', det)
    if "GV" in mods: rec["result"] = "SKIP - GV already on the charge"; out["hospice_gv"].append(rec); L(rec); continue
    rec["live"] = [(c["cid"], c["cpt"], c["insbalance"]) for c in st]
    if not LIVE: rec["result"] = "DRY: gv_rebill.add_gv(%s) then freq1_visit.run(%s, %s, %s)" % (cid, vid, cid, seq); out["hospice_gv"].append(rec); L(rec); continue
    try:
        r1 = gv_rebill.add_gv(cid); time.sleep(0.8)
        det2 = amd.post(amd.msg("getchargedetaildataicd10", "chargeentry", {"chargeid": "charge" + cid, "nocookie": "1"}), timeout=120)
        mods2 = re.findall(r'<modcode [^>]*code="([^"]*)"', det2)
        if "GV" not in mods2: raise RuntimeError("GV not on the charge after add_gv: %s" % mods2)
        r2 = freq1_visit.run(vid, cid, seq)
        rec["result"] = "GV added %s; rebill %s" % (str(r1)[:120], str(r2)[:160])
    except Exception as e:
        rec["result"] = "ERROR %s" % e; out["errors"].append(rec["result"])
    out["hospice_gv"].append(rec); L(rec); time.sleep(0.8)
# (3) record only
out["record_only"] = [
    {"pid": "17477313", "vid": "19456208", "cpt": "99308", "dos": "09/21/2026", "amount": 107.0, "carc": "COB9", "result": "POYNOR standing flag - board row [name]-17477313 on William's turn (GV or GW); nothing written"},
    {"pid": "17474493", "vid": "19456837", "cpt": "99223", "dos": "09/30/2026", "amount": 310.0, "carc": "CO109", "result": "Medicare's answer to the pre-re-route claim; UHC Dual Complete rebill out 10/6 - nothing written"},
    {"cluster": "CO151+CO234 CCM", "claims": sorted(k for k, v in claims.items() if any(c.get("reasoncode") == "CO151" for ch in v["charges"] for c in (ch.get("carc") or []))),
     "result": "board rows on William's turn (7 AM ET 10/7 run) - appeal or WONCS; nothing written"}]
fn = "registers/era_1053024_%s%s.json" % (S, "" if LIVE else "_dry")
json.dump(out, open(fn, "w"), indent=1)
L("DONE %s errors=%d -> %s" % ("LIVE" if LIVE else "DRY", len(out["errors"]), fn))
