# PLAIN ENGLISH (new ERA checks of the 7 AM ET 10/15/2026 slot, run 2026-10-15T1110Z - stamp copy of era_new_1014_1710.py with this run's
#   check ids and stamp; posting rules unchanged):
#   Two NEW Medicare Part B 835s - 1053177 ($2,351.47 unposted, 27 primary claims, 37 money lines on 11 charts, all CO-45 + PR-2 + CO-253:
#   the 10/13 re-sends paying) and 1053179 ($0, 5 claims: OA-18 duplicate answers on charts 17472396 / 17476042 - recorded, never posted).
#     MONEY lines -> pay = min(paid, live open insurance balance), contractual -> WOINS capped so pay + WOINS never exceeds the balance,
#     posted ERA-linked (payreasons.post_line) so the reason codes stay on the payment. $0 OA-18 lines: duplicate, original stands.
#     'already posted by check number' guard protects against the Billing Button's Post-button pass in the same hour.
#   1053116 (UHC W0020208 takeback pair) is NOT touched: William's decision.
import amd, txh, payreasons, move_to_ins, json, sys, time, datetime
a = sys.argv; DRY = "--live" not in a; FIRST = "--first-only" in a; S = "2026-10-15T1110Z"
ONLY = a[a.index("--only") + 1].split(",") if "--only" in a else ["1053177", "1053179"]
NEVER = {"1052906", "1053116"}
RECORD_ONLY = {}
MEDICAID_CARS = {"SUN01", "MCAD", "FLO99", "WEL04", "HUM01", "SIM01", "AMB03"}
# Carrier override is for the SAME payer filed under another AMD carrier record (UHC family; Florida Blue 835s AMD files under FLORIDA
# MEDICARE) - never for a genuinely different payer: a Humana answer on a visit now billed to Medicare posts under Humana.
ALIAS = {"UNI20": {"UHCMA", "AAR01"}, "UHCMA": {"UNI20", "AAR01"}, "AAR01": {"UNI20", "UHCMA"}}
def alias_ok(chk, lc):
    if lc in ALIAS.get(chk["systemcarriercode"], set()): return True
    if lc == "HUM01" and str(chk.get("eracarriername", "")).upper().startswith("HUMANA"): return True   # 10/13 2110Z: Humana 835 AMD filed under another carrier record
    return lc == "BCBS" and str(chk.get("eracarriername", "")).upper().startswith("FLORIDA BLUE")
CARRIERS = json.load(open("carriers.json"))
WATCH = json.load(open("/home/claude/effinger-billing-backend/practices/ehpa/registers/tf_writeoff_watch.json"))
WATCH_VIDS = {str(v.get("vid")): it["id"] for it in WATCH.get("items", []) for v in it.get("visits", [])}
amd.login_cached()
_l = json.load(open("registers/era_checks_before_%s.json" % S)); _l = _l.get("checks") if isinstance(_l, dict) else _l  # era_list.py (10/8) writes {tag, stamp, count, total, checks}
chks = {str(c["id"]): c for c in _l}
def L(m): print(m, flush=True)
def live(pid, vid):
    root = txh.fetch_visit(pid, vid); res = {}
    for c in root.iter("charge"):
        if c.get("void") == "1" or c.get("visit") != str(vid): continue
        d = (c.get("dos") or "")
        iso = ("%s-%s-%s" % (d[6:10], d[0:2], d[3:5])) if "/" in d else d[:10]
        res[c.get("id").replace("charge", "")] = {"fee": float(c.get("fee") or 0), "paid": float(c.get("paid") or 0), "patbal": float(c.get("patbal") or 0), "insbal": float(c.get("insbal") or 0), "carrier": c.get("carrier"), "cpt": c.get("proccode"), "dos": iso, "billdate": c.get("billdate"),
            "pays": [(float(p.get("amount") or 0), (p.get("checknumber") or "").strip(), p.get("carrier"), p.get("void")) for p in c.iter("payment")]}
    return res
REGF = "registers/era_manual_register.json"; reg = json.load(open(REGF))
out = {"stamp": S, "dry": DRY, "lines": [], "wolate": []}; faults = 0; posted_once = False
for CID in ONLY:
    if CID in NEVER: L("check %s: standing hold - not touched" % CID); continue
    chk = dict(chks[CID]); det = json.load(open("era_details/%s.json" % CID))["eracheckdetails"]; done = set()
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
                # NEW C: match the unmatched line to the live charge by CPT + DOS (then CPT alone when the visit has one such charge)
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
            if paid > 0 and bal <= 0 and s["patbal"] >= paid - 0.011:
                if DRY: r["note"] = "would move %.2f patient balance back to insurance first" % s["patbal"]; bal = s["patbal"]
                else:
                    mv = move_to_ins.move(cid, rebill=False); r["moved"] = mv; L("v%s c%s move back: %s" % (vid, cid, mv))
                    if not str(mv).startswith("moved"): r["outcome"] = "HOLD - move back failed: %s" % mv; out["lines"].append(r); continue
                    time.sleep(0.6); st = live(pid, vid); s = st.get(cid); bal = s["insbal"]; r["before_after_move"] = {"insbal": bal, "patbal": s["patbal"]}
            if bal <= 0:
                r["outcome"] = ("residual %.2f" % paid) if paid > 0 else "skip - insurance balance already 0"
                if paid == 0 and s["patbal"] > 0: r["note"] = "patient balance %.2f on this charge (wrong-payer rule: see the run's follow-up)" % s["patbal"]
                out["lines"].append(r); L("v%s c%s %s bal 0 -> %s" % (vid, cid, ch["chargecode"], r["outcome"])); continue
            post_chk = chk
            prior = [p for p in s["pays"] if p[3] != "1" and p[0] < 0]
            if paid > 0:
                pay = min(paid, bal); wo = max(0.0, min(round(co, 2), round(bal - pay, 2))); code = "WOINS"
            else:
                denial = [c for c in carcs if c not in ("CO45", "45", "CO253", "253")]
                if any(c in ("OA18", "18") for c in carcs): r["outcome"] = "duplicate OA-18 - original adjudication stands, nothing posted"; out["lines"].append(r); continue
                watch = WATCH_VIDS.get(vid)
                pre0501 = r["dos"] < "2026-05-01" and bool(v.get("billedprimarysequence")) and s["carrier"] in ("UNI20", "BCBS")
                if s["carrier"] and s["carrier"] != chk["systemcarriercode"] and not alias_ok(chk, s["carrier"]) and not (co29 > 0 and (watch or pre0501)):
                    r["outcome"] = "HOLD - $0 answer %s %s from %s but the live claim is at %s (billed %s): the old plan's answer - nothing written, listed for the board" % (carcs, rarcs, chk["systemcarriercode"], s["carrier"], s["billdate"]); out["lines"].append(r); L("v%s c%s HOLD old-plan answer %s (live %s)" % (vid, cid, carcs, s["carrier"])); continue
                if co29 > 0 and (watch or pre0501):
                    code = "WOLATE"; pay = 0.0; wo = round(min(bal, co29), 2)
                    r["why"] = "timely-filing answer CARC 29 on %s - WOLATE per William 10/6/2026" % (("watch item " + watch) if watch else "a UNI20/BCBS pre-5/1/2026 primary claim")
                    r["watch"] = watch or "uni20-bcbs-pre0501 (not in an item)"
                elif any(c in ("OA23", "23") for c in carcs) and prior and chk["systemcarriercode"] in MEDICAID_CARS:
                    # NEW D: dual crossover residual - the Medicaid-type secondary answers $0 on a line the primary already paid
                    code = "WOCAID2ND"; pay = 0.0; wo = round(min(bal, co), 2); r["why"] = "OA-23 $0 from the Medicaid-type secondary %s on a line already paid by %s - dual crossover residual WOCAID2ND (9/20, 10/4, 10/6 rule)" % (chk["systemcarriercode"], "/".join(sorted({p[2] or "?" for p in prior})))
                elif pr > 0 and not any(c.startswith(("CO", "OA", "PI")) for c in denial) and all(c in ("PR1", "PR2", "PR3", "1", "2", "3") for c in denial):
                    if prior: r["outcome"] = "HOLD - $0 deductible/coinsurance answer %s on a line already paid by %s (another payer's money is on it - review)" % ("+".join(carcs), "/".join(sorted({p[2] or "?" for p in prior}))); out["lines"].append(r); L("v%s c%s HOLD PR with prior payment" % (vid, cid)); continue
                    code = "WOINS"; pay = 0.0; wo = round(min(bal, co), 2); r["why"] = "deductible / coinsurance answer (%s): contractual WOINS, PR %.2f stays for the patient / secondary" % ("+".join(carcs), pr)
                    if wo <= 0: r["outcome"] = "skip - deductible line with no contractual to write off (PR %.2f stays)" % pr; out["lines"].append(r); continue
                elif any(c in ("CO185", "185") for c in carcs) and "N767" in rarcs and prior and str(chk.get("eracarriername", "")).upper().startswith("HUMANA"):
                    code = "WOINS"; pay = 0.0; wo = round(min(bal, co), 2); r["why"] = "CO-185/N767 $0 from Humana (Medicaid LOB, provider not enrolled) on a line already paid by %s - coinsurance residual WOINS per William 9/20/2026" % "/".join(sorted({p[2] or "?" for p in prior}))
                    if wo <= 0: r["outcome"] = "skip - CO-185 line with nothing left to write off"; out["lines"].append(r); continue
                else:
                    note = ""
                    if s["carrier"] and s["carrier"] != chk["systemcarriercode"]: note = " - live claim already at %s (billed %s), this is the old plan's answer" % (s["carrier"], s["billdate"])
                    r["outcome"] = "HOLD - $0 answer %s %s (denial handling / board)%s" % (carcs, rarcs, note); out["lines"].append(r); L("v%s c%s HOLD %s%s" % (vid, cid, carcs, note)); continue
            lc = s["carrier"]
            if lc and lc != chk["systemcarriercode"] and lc in CARRIERS and alias_ok(chk, lc):
                post_chk = dict(chk); post_chk["systemcarriercode"] = lc; post_chk["systemcarrierid"] = int(CARRIERS[lc].replace("car", "")); r["carrier_override"] = lc
            elif str(chk.get("eracarriername", "")).upper().startswith("HUMANA") and chk["systemcarriercode"] != "HUM01" and "HUM01" in CARRIERS:
                post_chk = dict(chk); post_chk["systemcarriercode"] = "HUM01"; post_chk["systemcarrierid"] = int(CARRIERS["HUM01"].replace("car", "")); r["carrier_override"] = "HUM01 (Humana 835 filed under %s)" % chk["systemcarriercode"]
            elif str(chk.get("eracarriername", "")).upper().startswith(("FLORIDA BLUE", "HEALTH OPTIONS")) and chk["systemcarriercode"] != "BCBS" and "BCBS" in CARRIERS:
                # 10/14 1710Z: a Florida Blue 835 AMD filed under FLORIDA MEDICARE posts under BCBS - the payer that paid (the Humana rule, made general for Florida Blue)
                post_chk = dict(chk); post_chk["systemcarriercode"] = "BCBS"; post_chk["systemcarrierid"] = int(CARRIERS["BCBS"].replace("car", "")); r["carrier_override"] = "BCBS (Florida Blue 835 filed under %s)" % chk["systemcarriercode"]
            elif lc and lc != chk["systemcarriercode"]:
                r["note"] = "live claim is at %s (billed %s) - this %s answer posts under %s; the %s claim's own answer settles the rest" % (lc, s["billdate"], chk["systemcarriercode"], chk["systemcarriercode"], lc)
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
