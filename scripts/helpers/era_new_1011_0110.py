# PLAIN ENGLISH (new ERA checks of the 9 PM ET 10/10/2026 slot, run 2026-10-11T0110Z - copy of era_new_1010_0110.py with this run's
#   check ids, stamp and three rule additions for Humana NO-PAY answers that AMD filed under another carrier):
#   1053084 Humana (HUM01) NO-PAY-202610090008699 - 1 PRIMARY claim (claimstatus 1) on chart 20379 (99487 9/7/2025, v19416099, $206
#     open at HUM01): CO-16 + M76 (invalid diagnosis) on an ADJUDICATED claim (277: F0/107 $0, payer claim number in
#     claimstatus_exact_2026-10-11T0110Z.json) - HELD: nothing written; a board row on William's turn carries the planned correction
#     (the v12 step 5(d) rule: never frequency 1 into an adjudicated claim).
#   1053085 Humana INC. NO-PAY-202610090008700 - AMD filed it under FLORIDA MEDICARE (systemcarriercode FLO02) because the claims it
#     matched sit at Medicare; the payer is Humana, so the check is treated as HUM01 (car6285) here:
#     chart 17471238 x3 (CCM 3/20, 4/20, 5/17/2026, claimstatus 1, OA-23 $206): balances already $0 (Humana's 10/6 NO-PAY settled them) - skip.
#     chart 20379 x3 (HCA 9/16-9/18/2026, claimstatus 2 = SECONDARY, OA-23): Medicare paid 9/19-9/20 and the residual (Medicare's
#       contractual + coinsurance, no write-off posted) sits on the insurance balance at FLO02; the chart's seq-4 Humana plan is the
#       Medicaid MMA ('MEDICAID GATE CAP DIR' on AMD's 271, board row fenner-[first]-20379) -> dual-crossover residual WOCAID2ND, ERA-linked,
#       posted under HUM01 (9/20 William: 'write these off the humana secondary amounts'; 10/4 / 10/6 / 10/10 rule).
#     chart 23969 x5 (7 lines, HCA 9/16-9/20/2026, claimstatus 2, OA-23): the chart carries NO Humana plan (Medicare seq 1 + Cigna
#       seq 2 only; AMD 271 names no Medicaid) and the live claims are at CIG09 (billed 10/2-10/6, pending) -> HOLD, nothing written.
#     chart 17472784 v19420555 (99307 10/7/2025, claimstatus 1, CO-185 + N767 'rendering provider not enrolled in Medicaid'): Medicare
#       paid 25.47 + WOINS; the 6.50 coinsurance sits on the PATIENT balance; the chart's seq-2 Humana plan is the Medicaid MMA (AMD 271
#       'MEDICAID GATE CAP DIR'; patient deceased [DOB], DOS before) -> move the 6.50 back to insurance (no rebill) and write it off
#       WOINS ERA-linked (William 9/20/2026: CO-185/N767 crossover residuals from the Humana Medicaid plan are written off).
#   1052906 (Florida Blue takeback pair) is NOT touched: William's decision.
# Decides, per line, through the ERA-linked Payment Entry shape (payreasons.post_line = addpayments postingmethod="era" with the remit's
#   reasonlist, so the CARCs stay on the payment and no 'Payment reason codes' Unbilled row is born):
#   MONEY line: pay = min(remit paid, open insurance balance), WOINS = the CO/OA contractual capped so pay + wo <= that balance; PR never
#     written off; a paid amount above the open balance is a residual (William 9/13: post the maximum AMD accepts, disregard the rest).
#     Coinsurance sitting on the PATIENT balance when the payer pays is moved back first (move_to_ins.move, no rebill).
#   $0 lines: OA-18 = duplicate, nothing posted; CO-29 on a watch / UNI20-BCBS pre-5/1 primary = WOLATE; OA-23 from a Medicaid-type
#   secondary that is ON THE CHART = WOCAID2ND; CO-185/N767 from that plan = WOINS; a coinsurance residual such a plan answers $0 on
#   while it sits on the patient balance is moved back to insurance first (no rebill) - a dual never owes it; a $0 answer from a payer
#   the chart does not carry, or on a claim now at another payer, is HELD and listed; PR-only deductible answer = WOINS the contractual;
#   every other $0 line is HELD and listed for the board / report.
# --dry = read only (default is dry unless --live). 3 consecutive addpayments faults stop the run. --only <checkid,...>, --first-only.
# Register: registers/era_new_2026-10-11T0110Z[_dry].json; settled lines appended to registers/era_manual_register.json.
# Never touches: the ERA Center Post button, the held check 1052906, plans, claims, rebills.
import amd, txh, payreasons, move_to_ins, amdw, json, sys, time, datetime
a = sys.argv; DRY = "--live" not in a; FIRST = "--first-only" in a; S = "2026-10-11T0110Z"
ONLY = a[a.index("--only") + 1].split(",") if "--only" in a else ["1053084", "1053085"]
NEVER = {"1052906"}
RECORD_ONLY = {}
MEDICAID_CARS = {"SUN01", "MCAD", "FLO99", "WEL04", "HUM01", "SIM01", "AMB03"}
# Carrier override is for the SAME payer filed under another AMD carrier record (UHC family; Florida Blue 835s AMD files under FLORIDA
# MEDICARE; a Humana NO-PAY AMD files under the carrier the matched claims sit at) - never for a genuinely different payer.
ALIAS = {"UNI20": {"UHCMA", "AAR01"}, "UHCMA": {"UNI20", "AAR01"}, "AAR01": {"UNI20", "UHCMA"}}
def alias_ok(chk, lc):
    if lc in ALIAS.get(chk["systemcarriercode"], set()): return True
    return lc == "BCBS" and str(chk.get("eracarriername", "")).upper().startswith("FLORIDA BLUE")
CARRIERS = json.load(open("carriers.json")); CAR2CODE = {v: k for k, v in CARRIERS.items()}
WATCH = json.load(open("/home/claude/effinger-billing-backend/practices/ehpa/registers/tf_writeoff_watch.json"))
WATCH_VIDS = {str(v.get("vid")): it["id"] for it in WATCH.get("items", []) for v in it.get("visits", [])}
amd.login_cached()
_l = json.load(open("registers/era_checks_before_2026-10-11T0110Z.json")); _l = _l.get("checks") if isinstance(_l, dict) else _l
chks = {str(c["id"]): c for c in _l}
def L(m): print(m, flush=True)
PLANS = {}
def chart_plans(pid):
    """Carrier codes of the chart's insurance plans that are not end-dated (read-only getdemographic)."""
    if pid not in PLANS:
        try:
            pl = amdw.plans(pid)[0]
            PLANS[pid] = {CAR2CODE.get(x.get("carrier") or "", x.get("carriercode") or "") for x in pl if not (x.get("end") or "").strip()}
        except Exception as e:
            PLANS[pid] = set(); L("pat%s plans read failed: %s" % (pid, repr(e)[:120]))
    return PLANS[pid]
def live(pid, vid):
    root = txh.fetch_visit(pid, vid); res = {}
    for c in root.iter("charge"):
        if c.get("void") == "1" or c.get("visit") != str(vid): continue
        d = (c.get("dos") or "")
        iso = ("%s-%s-%s" % (d[6:10], d[0:2], d[3:5])) if "/" in d else d[:10]
        res[c.get("id").replace("charge", "")] = {"fee": float(c.get("fee") or 0), "paid": float(c.get("paid") or 0), "patbal": float(c.get("patbal") or 0), "insbal": float(c.get("insbal") or 0), "carrier": c.get("carrier"), "billdate": c.get("billdate"), "cpt": c.get("proccode"), "dos": iso,
            "pays": [(float(p.get("amount") or 0), (p.get("checknumber") or "").strip(), p.get("carrier"), p.get("void")) for p in c.iter("payment")]}
    return res
REGF = "registers/era_manual_register.json"; reg = json.load(open(REGF))
out = {"stamp": S, "dry": DRY, "lines": [], "wolate": []}; faults = 0; posted_once = False
for CID in ONLY:
    if CID in NEVER: L("check %s: standing hold - not touched" % CID); continue
    chk = dict(chks[CID]); det = json.load(open("era_details/%s.json" % CID))["eracheckdetails"]; done = set()
    if str(chk.get("eracarriername", "")).upper().startswith("HUMANA") and chk["systemcarriercode"] != "HUM01":
        L("check %s: Humana NO-PAY filed by AMD under %s - treated as HUM01 (car6285)" % (CID, chk["systemcarriercode"]))
        chk["filed_under"] = chk["systemcarriercode"]; chk["systemcarriercode"] = "HUM01"; chk["systemcarrierid"] = 6285
    L("=== check %s %s %s $%s unposted $%s" % (CID, chk["systemcarriercode"], chk["paymentnumber"], chk["paymentamount"], chk.get("unpostedamount")))
    for v in det:
        pid = str(v["patientid"]); vid = str(v["visitid"]); st = None
        for ch in v.get("charges") or []:
            cid = str(ch["chargedetailid"]); paid = float(ch.get("paymentamount") or 0)
            carcs = ["%s" % x["reasoncode"] for x in ch.get("carc") or []]; rarcs = [r["remarkcode"] for r in ch.get("rarc") or [] if r["remarkcode"] != "#AM"]
            co = sum(float(x["reasonamt"] or 0) for x in ch.get("carc") or [] if x["payreasongroup"] in ("CO", "OA", "PI"))
            co29 = sum(float(x["reasonamt"] or 0) for x in ch.get("carc") or [] if x["reasoncode"] in ("CO29", "29", "PI29", "OA29"))
            pr = sum(float(x["reasonamt"] or 0) for x in ch.get("carc") or [] if x["payreasongroup"] == "PR")
            r = {"checkid": CID, "checkclaimid": v["checkclaimid"], "visitid": vid, "pid": pid, "chargedetailid": cid, "cpt": ch["chargecode"], "dos": ch["dos"][:10], "paid": paid, "carcs": carcs, "rarcs": rarcs, "claimstatus": v.get("claimstatus"), "primary": v.get("billedprimarysequence")}
            if CID in RECORD_ONLY:
                if paid > 0: r["outcome"] = "HOLD - money line on a record-only check"; L("v%s c%s MONEY on record-only check %s" % (vid, cid, CID))
                else: r["outcome"] = "recorded - $0 %s %s: %s" % ("+".join(carcs), "+".join(rarcs), RECORD_ONLY[CID])
                out["lines"].append(r); continue
            if faults >= 3: r["outcome"] = "not attempted - 3 consecutive addpayments faults"; out["lines"].append(r); continue
            if FIRST and posted_once: r["outcome"] = "not attempted - --first-only"; out["lines"].append(r); continue
            if str(v.get("claimstatus")) == "3" or float(ch.get("claimamount") or 0) < 0:
                r["outcome"] = "reversal of an earlier $0 denial (%s) - recorded, nothing posted" % "+".join(carcs); out["lines"].append(r); L("v%s c%s reversal %s" % (vid, cid, carcs)); continue
            if st is None: st = live(pid, vid); time.sleep(0.3)
            if int(ch.get("chargedetailid") or -1) <= 0:
                cands = [k for k, s0 in st.items() if s0["cpt"] == ch["chargecode"] and s0["dos"] == ch["dos"][:10]] or [k for k, s0 in st.items() if s0["cpt"] == ch["chargecode"]]
                cands = [k for k in cands if (k, paid) not in done]
                if len(cands) == 1: cid = cands[0]; r["chargedetailid"] = cid; r["matched_by"] = "cpt+dos (era line had chargedetailid -1)"; L("v%s line %s %s matched to live charge %s" % (vid, ch["chargecode"], ch["dos"][:10], cid))
                else: r["outcome"] = "orphan - no AMD charge on the line (%d live candidates)" % len(cands); out["lines"].append(r); L("v%s ORPHAN %s" % (vid, ch["chargecode"])); continue
            if (cid, paid) in done: r["outcome"] = "skip - charge already handled on this check (repeated claim)"; out["lines"].append(r); continue
            done.add((cid, paid))
            s = st.get(cid)
            if not s: r["outcome"] = "skip - charge not live"; out["lines"].append(r); L("v%s c%s not live" % (vid, cid)); continue
            r["before"] = {k: s[k] for k in ("fee", "paid", "insbal", "patbal", "carrier", "billdate")}
            if any(p[1] == chk["paymentnumber"] and p[3] != "1" for p in s["pays"]): r["outcome"] = "already-posted"; out["lines"].append(r); L("v%s c%s already posted" % (vid, cid)); continue
            bal = s["insbal"]
            prior = [p for p in s["pays"] if p[3] != "1" and p[0] < 0]
            plans = chart_plans(pid); on_chart = chk["systemcarriercode"] in plans
            dual_zero = (paid == 0 and chk["systemcarriercode"] in MEDICAID_CARS and on_chart and prior
                         and (any(c in ("OA23", "23") for c in carcs) or any(c in ("CO185", "185") for c in carcs)))
            if paid > 0 and bal <= 0 and s["patbal"] >= paid - 0.011:
                if DRY: r["note"] = "would move %.2f patient balance back to insurance first" % s["patbal"]; bal = s["patbal"]
                else:
                    mv = move_to_ins.move(cid, rebill=False); r["moved"] = mv; L("v%s c%s move back: %s" % (vid, cid, mv))
                    if not str(mv).startswith("moved"): r["outcome"] = "HOLD - move back failed: %s" % mv; out["lines"].append(r); continue
                    time.sleep(0.6); st = live(pid, vid); s = st.get(cid); bal = s["insbal"]; r["before_after_move"] = {"insbal": bal, "patbal": s["patbal"]}
            elif dual_zero and bal <= 0 and s["patbal"] > 0:
                # NEW E (10/11): the Medicaid-type secondary on the chart answered $0 on a coinsurance residual that sits on the PATIENT balance - a dual never owes it
                if DRY: r["note"] = "would move %.2f patient balance (dual coinsurance residual) back to insurance first, no rebill" % s["patbal"]; bal = s["patbal"]
                else:
                    mv = move_to_ins.move(cid, rebill=False); r["moved"] = mv; L("v%s c%s move back (dual residual): %s" % (vid, cid, mv))
                    if not str(mv).startswith("moved"): r["outcome"] = "HOLD - move back failed: %s" % mv; out["lines"].append(r); continue
                    time.sleep(0.6); st = live(pid, vid); s = st.get(cid); bal = s["insbal"]; r["before_after_move"] = {"insbal": bal, "patbal": s["patbal"]}
            if bal <= 0:
                r["outcome"] = ("residual %.2f" % paid) if paid > 0 else "skip - insurance balance already 0"
                if paid == 0 and s["patbal"] > 0: r["note"] = "patient balance %.2f on this charge (wrong-payer rule: see the run's follow-up)" % s["patbal"]
                out["lines"].append(r); L("v%s c%s %s bal 0 -> %s" % (vid, cid, ch["chargecode"], r["outcome"])); continue
            post_chk = chk
            if paid > 0:
                pay = min(paid, bal); wo = max(0.0, min(round(co, 2), round(bal - pay, 2))); code = "WOINS"
            else:
                denial = [c for c in carcs if c not in ("CO45", "45", "CO253", "253")]
                if any(c in ("OA18", "18") for c in carcs): r["outcome"] = "duplicate OA-18 - original adjudication stands, nothing posted"; out["lines"].append(r); continue
                watch = WATCH_VIDS.get(vid)
                pre0501 = r["dos"] < "2026-05-01" and bool(v.get("billedprimarysequence")) and s["carrier"] in ("UNI20", "BCBS")
                secondary_own = str(v.get("claimstatus")) == "2" and on_chart
                if not on_chart and chk["systemcarriercode"] in MEDICAID_CARS and paid == 0:
                    r["outcome"] = "HOLD - $0 answer %s %s from %s, which is NOT a plan on this chart (chart plans %s); live claim at %s (billed %s) - nothing written, listed for the report" % (carcs, rarcs, chk["systemcarriercode"], sorted(plans), s["carrier"], s["billdate"]); out["lines"].append(r); L("v%s c%s HOLD payer not on chart" % (vid, cid)); continue
                if s["carrier"] and s["carrier"] != chk["systemcarriercode"] and not alias_ok(chk, s["carrier"]) and not (co29 > 0 and (watch or pre0501)) and not secondary_own:
                    r["outcome"] = "HOLD - $0 answer %s %s from %s but the live claim is at %s (billed %s): the old plan's answer - nothing written, listed for the board" % (carcs, rarcs, chk["systemcarriercode"], s["carrier"], s["billdate"]); out["lines"].append(r); L("v%s c%s HOLD old-plan answer" % (vid, cid)); continue
                if co29 > 0 and (watch or pre0501):
                    code = "WOLATE"; pay = 0.0; wo = round(min(bal, co29), 2)
                    r["why"] = "timely-filing answer CARC 29 on %s - WOLATE per William 10/6/2026" % (("watch item " + watch) if watch else "a UNI20/BCBS pre-5/1/2026 primary claim")
                    r["watch"] = watch or "uni20-bcbs-pre0501 (not in an item)"
                elif any(c in ("OA23", "23") for c in carcs) and prior and chk["systemcarriercode"] in MEDICAID_CARS and on_chart:
                    code = "WOCAID2ND"; pay = 0.0; wo = round(min(bal, co), 2); r["why"] = "OA-23 $0 from the Medicaid-type secondary %s (on the chart) on a line already paid by %s - dual crossover residual WOCAID2ND (9/20, 10/4, 10/6 rule)" % (chk["systemcarriercode"], "/".join(sorted({p[2] or "?" for p in prior})))
                elif any(c in ("CO185", "185") for c in carcs) and prior and chk["systemcarriercode"] in MEDICAID_CARS and on_chart:
                    code = "WOINS"; pay = 0.0; wo = round(min(bal, co), 2); r["why"] = "CO-185 %s $0 from the Humana Medicaid MMA plan on a line already paid by %s - crossover residual WOINS (William 9/20/2026)" % ("+".join(rarcs), "/".join(sorted({p[2] or "?" for p in prior})))
                elif pr > 0 and not any(c.startswith(("CO", "OA", "PI")) for c in denial) and all(c in ("PR1", "PR2", "PR3", "1", "2", "3") for c in denial):
                    if prior: r["outcome"] = "HOLD - $0 deductible/coinsurance answer %s on a line already paid by %s (another payer's money is on it - review)" % ("+".join(carcs), "/".join(sorted({p[2] or "?" for p in prior}))); out["lines"].append(r); L("v%s c%s HOLD PR with prior payment" % (vid, cid)); continue
                    code = "WOINS"; pay = 0.0; wo = round(min(bal, co), 2); r["why"] = "deductible / coinsurance answer (%s): contractual WOINS, PR %.2f stays for the patient / secondary" % ("+".join(carcs), pr)
                    if wo <= 0: r["outcome"] = "skip - deductible line with no contractual to write off (PR %.2f stays)" % pr; out["lines"].append(r); continue
                else:
                    note = ""
                    if s["carrier"] and s["carrier"] != chk["systemcarriercode"]: note = " - live claim already at %s (billed %s), this is the old plan's answer" % (s["carrier"], s["billdate"])
                    r["outcome"] = "HOLD - $0 answer %s %s (denial handling / board)%s" % (carcs, rarcs, note); out["lines"].append(r); L("v%s c%s HOLD %s%s" % (vid, cid, carcs, note)); continue
            lc = s["carrier"]
            if lc and lc != chk["systemcarriercode"] and lc in CARRIERS and alias_ok(chk, lc):
                post_chk = dict(chk); post_chk["systemcarriercode"] = lc; post_chk["systemcarrierid"] = int(CARRIERS[lc].replace("car", "")); r["carrier_override"] = lc
            elif lc and lc != chk["systemcarriercode"]:
                r["note"] = (r.get("note", "") + "; " if r.get("note") else "") + "live claim is at %s (billed %s) - this %s answer posts under %s; the %s claim's own answer settles the rest" % (lc, s["billdate"], chk["systemcarriercode"], chk["systemcarriercode"], lc)
            r.update(pay=round(pay, 2), wo=round(wo, 2), wocode=code, residual=round(paid - pay, 2), carrier=post_chk["systemcarriercode"])
            if DRY: r["outcome"] = "DRY would post pay %.2f + %s %.2f (bal %.2f)" % (pay, code, wo, bal); out["lines"].append(r); L("v%s pat%s c%s %s %s paid %.2f bal %.2f -> %s" % (vid, pid, cid, ch["chargecode"], "+".join(carcs), paid, bal, r["outcome"])); continue
            ok, payid, resp = payreasons.post_line(pid, vid, post_chk, v, cid, ch, pay=round(pay, 2), wo=round(wo, 2), wocode=code)
            posted_once = True
            time.sleep(0.7); st = live(pid, vid); s2 = st.get(cid) or {}
            r.update(outcome="posted" if ok else "FAULT", paymentid=payid, resp=resp[:160], after={"insbal": s2.get("insbal"), "patbal": s2.get("patbal")})
            faults = 0 if ok else faults + 1
            L("v%s pat%s c%s %s paid %.2f bal %.2f -> pay %.2f %s %.2f ok=%s after ins %s pat %s" % (vid, pid, cid, ch["chargecode"], paid, bal, pay, code, wo, ok, s2.get("insbal"), s2.get("patbal")))
            out["lines"].append(r); time.sleep(0.4)
for r in out["lines"]:
    if r.get("wocode") == "WOLATE" and r.get("outcome", "").startswith(("posted", "DRY")):
        out["wolate"].append({"pid": r["pid"], "vid": r["visitid"], "cid": r["chargedetailid"], "dos": r["dos"], "cpt": r["cpt"], "wo": r["wo"], "watch": r.get("watch"), "outcome": r["outcome"].split()[0]})
json.dump(out, open("registers/era_new_%s%s.json" % (S, "_dry" if DRY else ""), "w"), indent=1)
if out["wolate"]: json.dump(out["wolate"], open("registers/tf_co29_writeoffs_%s%s.json" % (S, "_dry" if DRY else ""), "w"), indent=1)
if not DRY:
    for r in out["lines"]:
        if r.get("outcome", "").startswith(("posted", "already", "residual")):
            reg.append({"checkid": r["checkid"], "checkclaimid": r["checkclaimid"], "visitid": r["visitid"], "chargedetailid": r["chargedetailid"], "cpt": r["cpt"], "outcome": r["outcome"].split()[0], "pay": r.get("pay"), "wo": r.get("wo"), "wocode": r.get("wocode"), "when": S})
    json.dump(reg, open(REGF, "w"), indent=1)
from collections import Counter
L(str(Counter(r["outcome"].split(" (")[0][:34] for r in out["lines"])))
L("pay $%.2f  WOINS $%.2f  WOCAID2ND $%.2f  WOLATE $%.2f (%d lines)  residual $%.2f" % (
    sum(r.get("pay", 0) for r in out["lines"] if r["outcome"].startswith(("posted", "DRY"))),
    sum(r.get("wo", 0) for r in out["lines"] if r.get("wocode") == "WOINS" and r["outcome"].startswith(("posted", "DRY"))),
    sum(r.get("wo", 0) for r in out["lines"] if r.get("wocode") == "WOCAID2ND" and r["outcome"].startswith(("posted", "DRY"))),
    sum(r.get("wo", 0) for r in out["lines"] if r.get("wocode") == "WOLATE" and r["outcome"].startswith(("posted", "DRY"))),
    len([r for r in out["lines"] if r.get("wocode") == "WOLATE" and r["outcome"].startswith(("posted", "DRY"))]),
    sum(r.get("residual", 0) for r in out["lines"] if r["outcome"].startswith("posted"))))
