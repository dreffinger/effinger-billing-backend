# b-copy (same run, 20:3xZ): the four UNPOSTED Medicare lines of check 1053023 (chart 17476042 v19453207 v19453499 v19453703 v19453717, paid 85.46 each) whose balances UHC PR-27 $0 posts moved to the PATIENT - move back (no rebill) then ERA-linked post, the NEW 1 branch below.
# PLAIN ENGLISH (new ERA check of the 3 PM ET 10/7/2026 slot, run 2026-10-07T1910Z - copy of era_new_1007_1710.py with two additions):
#   UnitedHealthcare W0686193 (ERA 1053038, $97.59, 52 claims): ONE money line (a 99309 on a UHC Dual Complete chart, CO-45 + CO-253),
#   43 CO-29 'time limit for filing has expired' answers on UNI20-primary claims with DOS before 5/1/2026 (three charts whose AARP /
#   UHC Medicare Advantage plan was in force on those dates; two of the visits are on the TIMELY-FILING WATCH item united-12232248-2025),
#   PR-27 'coverage terminated' answers (a secondary whose UHC plan is dead, two visits already re-routed to Florida Blue, lines already
#   at $0) and one OA-18 duplicate whose original adjudication (W0616257) is on the charge.
# Decides, per line, through the ERA-linked Payment Entry shape (payreasons.post_line):
#   MONEY line: pay = min(remit paid, open insurance balance), WOINS = the CO/OA contractual capped so pay + wo <= that balance; PR never
#     written off. NEW A: when the LIVE charge is billed to a different UHC carrier than the check's system carrier (UHCMA Dual Complete
#     vs UNI20), the post carries the live charge's carrier (the 10/7 1710Z lesson: the ERA-linked addpayments accepts the override).
#   NEW B: a $0 CO-29 line on a visit in practices/ehpa/registers/tf_writeoff_watch.json, or on a UNI20/BCBS PRIMARY claim with DOS before
#     5/1/2026 (billedprimarysequence true, live carrier UNI20/BCBS) = the payer's timely-filing answer -> pay 0 + WOLATE of the whole open
#     balance (William 10/6/2026: 'send all these United ones and then write them off if they return timely filing'; v12 STANDING FLAGS
#     TIMELY-FILING WATCH + UNI20/BCBS BEFORE 5/1/2026). A CO-29 on a secondary claim is never written off here (HOLD).
#   Patient-side coinsurance the payer now pays is moved back first (move_to_ins.move, no rebill); a reversal is recorded, never posted;
#   OA-18 = duplicate, nothing posted; every other $0 line (PR-27 etc.) is HELD and listed for the board / report.
# --dry = read only (default is dry unless --live). 3 consecutive addpayments faults stop the run. --only <checkid,...>, --first-only.
# Register: registers/era_new_2026-10-07T1910Z[_dry].json; settled lines appended to registers/era_manual_register.json; the WOLATE
#   lines are listed in registers/tf_co29_writeoffs_2026-10-07T1910Z.json for the watch-register commit.
# Never touches: the ERA Center Post button, the held Florida Blue check 1052906, the Medicare checks 1053023 / 1053024 (approval cards),
#   plans, claims, rebills.
import amd, txh, payreasons, move_to_ins, json, sys, time, datetime
a = sys.argv; DRY = "--live" not in a; FIRST = "--first-only" in a; S = "2026-10-07T1910Zb"
ONLY = a[a.index("--only") + 1].split(",") if "--only" in a else ["1053023"]
NEVER = {"1052906", "1053024"}
CARRIERS = json.load(open("carriers.json"))
WATCH = json.load(open("/home/claude/effinger-billing-backend/practices/ehpa/registers/tf_writeoff_watch.json"))
WATCH_VIDS = {str(v.get("vid")): it["id"] for it in WATCH.get("items", []) for v in it.get("visits", [])}
amd.login_cached()
chks = {str(c["id"]): c for c in json.load(open("registers/era_checks_before_2026-10-07T1910Z.json"))}
def L(m): print(m, flush=True)
def live(pid, vid):
    root = txh.fetch_visit(pid, vid); res = {}
    for c in root.iter("charge"):
        if c.get("void") == "1" or c.get("visit") != str(vid): continue
        res[c.get("id").replace("charge", "")] = {"fee": float(c.get("fee") or 0), "paid": float(c.get("paid") or 0), "patbal": float(c.get("patbal") or 0), "insbal": float(c.get("insbal") or 0), "carrier": c.get("carrier"), "cpt": c.get("proccode"), "billdate": c.get("billdate"),
            "pays": [(float(p.get("amount") or 0), (p.get("checknumber") or "").strip(), p.get("carrier"), p.get("void")) for p in c.iter("payment")]}
    return res
REGF = "registers/era_manual_register.json"; reg = json.load(open(REGF))
out = {"stamp": S, "dry": DRY, "lines": [], "wolate": []}; faults = 0; posted_once = False
for CID in ONLY:
    if CID in NEVER: L("check %s: standing hold - not touched" % CID); continue
    chk = dict(chks[CID]); det = json.load(open("era_details/%s.json" % CID))["eracheckdetails"]; done = set()
    L("=== check %s %s %s $%s" % (CID, chk["systemcarriercode"], chk["paymentnumber"], chk["paymentamount"]))
    for v in det:
        pid = str(v["patientid"]); vid = str(v["visitid"]); st = None
        for ch in v.get("charges") or []:
            cid = str(ch["chargedetailid"]); paid = float(ch.get("paymentamount") or 0)
            carcs = ["%s" % x["reasoncode"] for x in ch.get("carc") or []]; rarcs = [r["remarkcode"] for r in ch.get("rarc") or [] if r["remarkcode"] != "#AM"]
            co = sum(float(x["reasonamt"] or 0) for x in ch.get("carc") or [] if x["payreasongroup"] in ("CO", "OA", "PI"))
            co29 = sum(float(x["reasonamt"] or 0) for x in ch.get("carc") or [] if x["reasoncode"] in ("CO29", "29", "PI29", "OA29"))
            pr = sum(float(x["reasonamt"] or 0) for x in ch.get("carc") or [] if x["payreasongroup"] == "PR")
            r = {"checkid": CID, "checkclaimid": v["checkclaimid"], "visitid": vid, "pid": pid, "chargedetailid": cid, "cpt": ch["chargecode"], "dos": ch["dos"][:10], "paid": paid, "carcs": carcs, "rarcs": rarcs, "claimstatus": v.get("claimstatus"), "primary": v.get("billedprimarysequence")}
            if faults >= 3: r["outcome"] = "not attempted - 3 consecutive addpayments faults"; out["lines"].append(r); continue
            if FIRST and posted_once: r["outcome"] = "not attempted - --first-only"; out["lines"].append(r); continue
            if str(v.get("claimstatus")) == "3" or float(ch.get("claimamount") or 0) < 0:
                r["outcome"] = "reversal of an earlier $0 denial (%s) - recorded, nothing posted" % "+".join(carcs); out["lines"].append(r); L("v%s c%s reversal %s" % (vid, cid, carcs)); continue
            if int(ch.get("chargedetailid") or -1) <= 0: r["outcome"] = "orphan - no AMD charge on the line"; out["lines"].append(r); L("v%s ORPHAN" % vid); continue
            if (cid, paid) in done: r["outcome"] = "skip - charge already handled on this check (repeated claim)"; out["lines"].append(r); continue
            done.add((cid, paid))
            if st is None: st = live(pid, vid); time.sleep(0.3)
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
            if paid > 0:
                pay = min(paid, bal); wo = max(0.0, min(round(co, 2), round(bal - pay, 2))); code = "WOINS"
                # NEW A: live charge billed to a different UHC carrier than the check's system carrier
                lc = s["carrier"]
                if lc and lc != chk["systemcarriercode"] and lc in CARRIERS:
                    post_chk = dict(chk); post_chk["systemcarriercode"] = lc; post_chk["systemcarrierid"] = int(CARRIERS[lc].replace("car", "")); r["carrier_override"] = lc
            else:
                denial = [c for c in carcs if c not in ("CO45", "45", "CO253", "253")]
                if any(c in ("OA18", "18") for c in carcs): r["outcome"] = "duplicate OA-18 - original adjudication stands, nothing posted"; out["lines"].append(r); continue
                watch = WATCH_VIDS.get(vid)
                pre0501 = r["dos"] < "2026-05-01" and bool(v.get("billedprimarysequence")) and s["carrier"] in ("UNI20", "BCBS")
                if co29 > 0 and (watch or pre0501):
                    # NEW B: the payer's timely-filing answer on a watch visit / UNI20-BCBS pre-5/1 primary claim -> WOLATE the open balance
                    code = "WOLATE"; pay = 0.0; wo = round(min(bal, co29), 2)
                    r["why"] = "timely-filing answer CARC 29 on %s - WOLATE per William 10/6/2026" % (("watch item " + watch) if watch else "a UNI20/BCBS pre-5/1/2026 primary claim")
                    r["watch"] = watch or "uni20-bcbs-pre0501 (not in an item)"
                elif pr > 0 and not any(c.startswith(("CO", "OA", "PI")) for c in denial) and all(c in ("PR1", "PR2", "PR3", "1", "2", "3") for c in denial):
                    code = "WOINS"; pay = 0.0; wo = round(min(bal, co), 2); r["why"] = "deductible / coinsurance answer (%s): contractual WOINS, PR %.2f stays for the patient / secondary" % ("+".join(carcs), pr)
                    if wo <= 0: r["outcome"] = "skip - deductible line with no contractual to write off (PR %.2f stays)" % pr; out["lines"].append(r); continue
                else:
                    note = ""
                    if s["carrier"] and s["carrier"] != chk["systemcarriercode"]: note = " - live claim already at %s (billed %s), this is the old plan's answer" % (s["carrier"], s["billdate"])
                    r["outcome"] = "HOLD - $0 answer %s %s (denial handling / board)%s" % (carcs, rarcs, note); out["lines"].append(r); L("v%s c%s HOLD %s%s" % (vid, cid, carcs, note)); continue
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
json.dump(out["wolate"], open("registers/tf_co29_writeoffs_%s%s.json" % (S, "_dry" if DRY else ""), "w"), indent=1)
if not DRY:
    for r in out["lines"]:
        if r.get("outcome", "").startswith(("posted", "already", "residual")):
            reg.append({"checkid": r["checkid"], "checkclaimid": r["checkclaimid"], "visitid": r["visitid"], "chargedetailid": r["chargedetailid"], "cpt": r["cpt"], "outcome": r["outcome"].split()[0], "pay": r.get("pay"), "wo": r.get("wo"), "wocode": r.get("wocode"), "when": S})
    json.dump(reg, open(REGF, "w"), indent=1)
from collections import Counter
L(str(Counter(r["outcome"].split(" (")[0][:34] for r in out["lines"])))
L("pay $%.2f  WOINS $%.2f  WOLATE $%.2f (%d lines)  residual $%.2f" % (
    sum(r.get("pay", 0) for r in out["lines"] if r["outcome"].startswith(("posted", "DRY"))),
    sum(r.get("wo", 0) for r in out["lines"] if r.get("wocode") == "WOINS" and r["outcome"].startswith(("posted", "DRY"))),
    sum(r.get("wo", 0) for r in out["lines"] if r.get("wocode") == "WOLATE" and r["outcome"].startswith(("posted", "DRY"))),
    len([r for r in out["lines"] if r.get("wocode") == "WOLATE" and r["outcome"].startswith(("posted", "DRY"))]),
    sum(r.get("residual", 0) for r in out["lines"] if r["outcome"].startswith("posted"))))
