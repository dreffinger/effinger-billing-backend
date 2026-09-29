# PLAIN ENGLISH (Sunshine ERA 0917789488 = check 1052885, 5pm ET 9/29/2026 run 2026-09-29T2110Z). The check carries 92 claims, 11 money lines
#   and 81 $0 answers. The Post button is NOT used on this check (the engine would attribute the dual lines to the claim's chart carrier,
#   MCAD, instead of Sunshine) - every line goes through the ERA-linked Payment Entry shape (payreasons.post_line, reasons kept).
# Decides, per line, from the LIVE charge:
#   MONEY (paid>0): pay = min(paid, open insurance balance); write-off = the remit's CO/OA adjustments capped so pay+wo <= balance;
#     WOCAID2ND when the line is a dual crossover (OA-23 present), else the remit's code / WOINS. A $0 balance = already adjudicated (residual).
#   $0 Sunshine-SECONDARY answer on a Medicare-paid charge (OA-23/CO-45 $0, CO-96/N448 CCM-AWV-ACP, CO-26/N650, CO-16/M56): first the
#     Medicare CO-45 correction the 9/23 lesson calls for - insurance balance = fee - Medicare paid means Medicare's contractual never
#     came off: WOINS = balance - coinsurance (coinsurance = 20% of allowed, allowed = Medicare paid / 0.784; 0 on G0439) with Medicare's
#     check number (era_co45_fix_1110 PART B arithmetic); then the coinsurance: OA-23 / N448 lines -> $0 ERA-linked post + WOCAID2ND
#     (rules.md 9/11, 9/22, 9/23: a dual crossover paying $0 on Medicare coinsurance is never a patient balance; CCM/AWV/ACP are never
#     payable by a Medicaid secondary); CO-26 (pat24039, FCC file question on William's turn) and CO-16/M56 (the SUN01 payer-id cluster on
#     the board) keep the coinsurance on the insurance balance - only the contractual correction is made.
#   $0 Sunshine-PRIMARY N448 on a Medicaid-only chart -> WONCS (CCM/ACP billed Medicaid-primary, rules.md 9/11).
#   $0 N448 on a chart where MEDICARE is on file and the visit went to Sunshine first (wrong order) -> re-route: visit insorder Medicare
#     first (move_to_ins.move), frequency 1, chargerebill to the Medicare sequence (freq1_visit.run; deceased guard inside).
#   CO-18 duplicates: nothing (the original adjudication is on the same check). CO-222/N640: denial - listed, nothing written.
# Rules: --dry = read only, nothing posted; 3 consecutive addpayments faults stop the run; every line lands in registers/era_sun_<stamp>.json
#   and registers/era_manual_register.json. Never touches: patient balances, plans, the Post button, any other check.
import amd, txh, payreasons, manual_post, move_to_ins, freq1_visit, json, sys, time, os, re
DRY = "--dry" in sys.argv; S = "2026-09-29T2110Z"; CID = "1052885"
amd.login_cached()
chk = [c for c in json.load(open("scan_0929_2110/era_checks_before.json")) if str(c["id"]) == CID][0]
det = json.load(open("era_details/%s.json" % CID))["eracheckdetails"]
REROUTE = {"19455778": "1,2", "19455721": "2,3", "19455765": "4,5"}          # visit -> new insorder (Medicare first); AMD 271 / prior Medicare payments verified
REROUTE_SEQ = {"19455778": 1, "19455721": 2, "19455765": 4}
MEDICAID_ONLY = {"17469541", "17477829", "17471755"}                            # Sunshine-primary charts: CCM/ACP N448 -> WONCS
HOLD_CO = {"CO26", "CO16", "26", "16"}                                                       # coinsurance stays (FCC file / SUN01 payer id - William)
def L(m): print(m, flush=True)
def live(pid, vid):
    root = txh.fetch_visit(pid, vid); res = {}
    for c in root.iter("charge"):
        if c.get("void") == "1" or c.get("visit") != str(vid): continue
        res[c.get("id").replace("charge", "")] = {"fee": float(c.get("fee") or 0), "paid": float(c.get("paid") or 0), "patbal": float(c.get("patbal") or 0), "insbal": float(c.get("insbal") or 0), "carrier": c.get("carrier"), "cpt": c.get("proccode"), "dos": c.get("dos"),
            "pays": [(float(p.get("amount") or 0), (p.get("checknumber") or "").strip(), p.get("carrier"), p.get("void"), p.get("date")) for p in c.iter("payment")],
            "wos": [(float(w.get("amount") or 0), (w.get("wocode") or "").strip(), w.get("void"), (w.get("checknumber") or "").strip()) for w in c.iter("writeoff")]}
    return res
def medicare_split(st):
    """(medicare paid, check#, date, coinsurance, contractual) from the live charge; None when no Medicare payment."""
    mp = [p for p in st["pays"] if p[2] == "FLO02" and p[3] != "1" and p[0] < 0]
    if not mp: return None
    paid = -sum(p[0] for p in mp); chkno = mp[0][1]; dt = mp[0][4] or ""
    if st["cpt"] in ("G0439", "G0438"): allowed = paid / 0.98; coins = 0.0
    else: allowed = paid / 0.784; coins = round(0.2 * allowed, 2)
    contr = round(st["fee"] - paid - coins, 2)
    return paid, chkno, dt, coins, contr
out = {"stamp": S, "check": CID, "dry": DRY, "lines": []}; faults = 0; done = set()
REGF = "registers/era_manual_register.json"; reg = json.load(open(REGF)) if os.path.exists(REGF) else []
def rec_add(r):
    out["lines"].append(r); L("  -> %s" % r.get("outcome"))
for v in det:
    pid = str(v["patientid"]); vid = str(v["visitid"]); errs = [e["id"] for e in v.get("errors") or []]
    carcs_claim = []
    for ch in v.get("charges") or []:
        cid = str(ch["chargedetailid"]); paid = float(ch.get("paymentamount") or 0)
        carcs = [str(a["reasoncode"]).strip().upper() for a in ch.get("carc") or []]; rarcs = [r["remarkcode"] for r in ch.get("rarc") or [] if r["remarkcode"] != "#AM"]   # e.g. CO45, OA23, CO16; rarcs = [r["remarkcode"] for r in ch.get("rarc") or [] if r["remarkcode"] != "#AM"]
        co = sum(float(a["reasonamt"] or 0) for a in ch.get("carc") or [] if a["payreasongroup"] in ("CO", "OA", "PI"))
        r = {"pid": pid, "vid": vid, "cid": cid, "claim": v["checkclaimid"], "cpt": ch["chargecode"], "dos": ch["dos"][:10], "paid": paid, "carcs": carcs, "rarcs": rarcs, "when": S}
        key = (cid, "+".join(carcs))
        L("v%s pat%s c%s %s %s paid=%.2f %s %s" % (vid, pid, cid, ch["chargecode"], ch["dos"][:10], paid, "+".join(carcs), "+".join(rarcs)))
        if faults >= 3: r["outcome"] = "not attempted - 3 consecutive addpayments faults"; rec_add(r); continue
        if key in done: r["outcome"] = "skip - same charge/answer already handled on this check (repeated claim)"; rec_add(r); continue
        done.add(key)
        st = live(pid, vid).get(cid)
        if not st: r["outcome"] = "skip - charge not live"; rec_add(r); continue
        r["before"] = {k: st[k] for k in ("fee", "paid", "insbal", "patbal", "carrier")}
        if any(p[1] == chk["paymentnumber"] and p[3] != "1" for p in st["pays"]): r["outcome"] = "already-posted"; rec_add(r); continue
        bal = st["insbal"]
        # ---------- MONEY
        if paid > 0:
            if bal <= 0: r["outcome"] = "residual %.2f" % paid; r["why"] = "open insurance balance $0 - already adjudicated"; rec_add(r); continue
            pay = min(paid, bal); wo = max(0.0, min(round(co, 2), round(bal - pay, 2)))
            code = "WOCAID2ND" if any(c.endswith("23") and c.startswith("OA") for c in carcs) else ((ch.get("payreasonwocode") or "").strip() or "WOINS")
            r.update(pay=round(pay, 2), wo=round(wo, 2), wocode=code, residual=round(paid - pay, 2))
            if DRY: r["outcome"] = "DRY would post pay %.2f wo %.2f %s" % (pay, wo, code); rec_add(r); continue
            ok, payid, resp = payreasons.post_line(pid, vid, chk, v, cid, ch, pay=round(pay, 2), wo=round(wo, 2), wocode=code)
            r.update(outcome="posted" if ok else "FAULT", paymentid=payid, resp=resp[:160]); faults = 0 if ok else faults + 1; rec_add(r); time.sleep(0.8); continue
        # ---------- $0 lines
        if any(c in ("CO18", "18") for c in carcs): r["outcome"] = "duplicate CO-18/N522 - original adjudication on this check, nothing to post"; rec_add(r); continue
        if any(c in ("CO222", "222") for c in carcs): r["outcome"] = "DENIAL CO-222/N640 (frequency/units) - listed, nothing written"; rec_add(r); continue
        if bal <= 0: r["outcome"] = "skip - insurance balance already 0"; rec_add(r); continue
        ms = medicare_split(st)
        if ms is None:
            # no Medicare payment on the charge: Sunshine-primary answer
            if vid in REROUTE:
                r["outcome"] = "REROUTE to Medicare (insorder %s, freq 1, seq %s)" % (REROUTE[vid], REROUTE_SEQ[vid])
                if not DRY:
                    m = move_to_ins.move(cid, REROUTE[vid]); r["move"] = str(m)[:160]; time.sleep(0.8)
                    if "FAULT" in str(m): r["outcome"] = "REROUTE FAULT " + str(m)[:120]
                    else: r["rebill"] = freq1_visit.run(vid, cid, REROUTE_SEQ[vid]); r["outcome"] += " -> " + str(r["rebill"])[:80]
                    REROUTE.pop(vid, None)   # one rebill per visit
                else: r["outcome"] = "DRY " + r["outcome"]
                rec_add(r); continue
            if vid in ("19455721", "19455765", "19455778"): r["outcome"] = "rerouted with the visit's first line"; rec_add(r); continue
            if pid in MEDICAID_ONLY and any(c in ("CO96", "96") for c in carcs):
                r.update(pay=0.0, wo=round(bal, 2), wocode="WONCS")
                if DRY: r["outcome"] = "DRY would post $0 + WONCS %.2f (CCM/ACP billed Medicaid-primary)" % bal; rec_add(r); continue
                ok, payid, resp = payreasons.post_line(pid, vid, chk, v, cid, ch, pay=0.0, wo=round(bal, 2), wocode="WONCS")
                r.update(outcome="posted WONCS" if ok else "FAULT", paymentid=payid, resp=resp[:160]); faults = 0 if ok else faults + 1; rec_add(r); time.sleep(0.8); continue
            r["outcome"] = "HOLD - $0 primary answer %s with no rule (%s)" % ("+".join(carcs), "+".join(rarcs)); rec_add(r); continue
        mpaid, mchk, mdt, coins, contr = ms; r["medicare"] = {"paid": mpaid, "check": mchk, "coins": coins, "contractual": contr}
        if abs(bal - (coins + contr)) < 0.06 and contr > 0.005:
            # the CO-45 correction: Medicare's contractual never came off this charge
            dd = mdt if re.match(r"\d\d/\d\d/\d\d\d\d", mdt or "") else None
            if DRY: r["fix45"] = "DRY WOINS %.2f (Medicare %s)" % (contr, mchk)
            else:
                ok, msg = manual_post.post(cid, "FLO02", 0.0, round(contr, 2), "WOINS", checknumber=mchk, depositdate=dd, note="Medicare contractual correction (CO-45 never adjusted) run %s" % S)
                r["fix45"] = (ok, str(msg)[:120]); faults = 0 if ok else faults + 1
                if not ok: r["outcome"] = "FAULT on the contractual correction"; rec_add(r); continue
                time.sleep(0.8); bal = coins
        elif abs(bal - coins) < 0.06: r["fix45"] = "not needed (balance = coinsurance)"
        else: r["outcome"] = "HOLD - balance %.2f is neither coinsurance %.2f nor coinsurance+contractual %.2f" % (bal, coins, coins + contr); rec_add(r); continue
        if coins <= 0.005: r["outcome"] = "contractual corrected; no coinsurance on this code (100%% Medicare) - $0 line settled"; rec_add(r); continue
        if any(c in HOLD_CO for c in carcs):
            r["outcome"] = "coinsurance %.2f stays on insurance (%s - William's row); contractual %s" % (coins, "+".join(carcs), r.get("fix45")); rec_add(r); continue
        # OA-23 $0 or N448 on a Medicare-paid line -> WOCAID2ND coinsurance, ERA-linked
        r.update(pay=0.0, wo=round(coins, 2), wocode="WOCAID2ND")
        if DRY: r["outcome"] = "DRY would post $0 + WOCAID2ND %.2f (after %s)" % (coins, r.get("fix45")); rec_add(r); continue
        ok, payid, resp = payreasons.post_line(pid, vid, chk, v, cid, ch, pay=0.0, wo=round(coins, 2), wocode="WOCAID2ND")
        r.update(outcome="posted WOCAID2ND" if ok else "FAULT", paymentid=payid, resp=resp[:160]); faults = 0 if ok else faults + 1; rec_add(r); time.sleep(0.8)
json.dump(out, open("registers/era_sun_%s%s.json" % (S, "_dry" if DRY else ""), "w"), indent=1)
if not DRY:
    for r in out["lines"]:
        if r.get("outcome", "").startswith(("posted", "already", "residual")):
            reg.append({"checkid": CID, "checkclaimid": r["claim"], "visitid": r["vid"], "chargedetailid": r["cid"], "cpt": r["cpt"], "outcome": r["outcome"].split()[0] if r["outcome"].startswith("posted") else r["outcome"], "when": S})
    json.dump(reg, open(REGF, "w"), indent=1)
from collections import Counter
print(Counter(r["outcome"].split(" (")[0][:40] for r in out["lines"]))
