# PLAIN ENGLISH (Sunshine ERA 0917789488 = check 1052885, run 2026-09-30T0110Z = 9 PM ET 9/29 slot; finishes the 2310Z plan).
# 2310Z LESSON applied: on a charge whose live carrier is the LAST payer (Sunshine/FCC secondary) any post that leaves a balance makes AMD
#   transfer the remainder to the PATIENT. So every dual-crossover $0 line that still needs Medicare's contractual correction is settled in
#   ONE ERA-linked Payment Entry post (payreasons shape, reasons kept) carrying TWO write-offs: WOINS = Medicare's contractual (fee - Medicare
#   paid - coinsurance; allowed = Medicare paid / 0.784, coinsurance 20% of allowed, 0 on G0439) and WOCAID2ND = the coinsurance the Medicaid
#   secondary answered $0 on (OA-23 / CO-96 N448) - pay 0, total write-off = the whole open balance, nothing left to move. The case note
#   names Medicare's check for the contractual part.
# Decides, per line, from the LIVE charge (gettxhistory):
#   already posted (a non-void payment with this check number) / balance 0 / CO-18 duplicate / CO-222 denial -> recorded, nothing written.
#   MONEY (paid > 0): pay = min(paid, balance); write-off = the remit's CO/OA adjustments capped so pay + wo = balance; WOCAID2ND on OA-23 lines,
#     else the remit's code or WOINS; a partial that would leave a last-payer balance is HELD.
#   $0 with NO Medicare payment: Sunshine-primary answer - CO-96/N448 CCM on a Medicaid-only chart -> WONCS (posted 2310Z); on a chart with
#     Medicare on file -> REROUTE: visit insorder Medicare first (move_to_ins.move), frequency 1, chargerebill to the Medicare sequence.
#   $0 with a Medicare payment: CO-16/M56 (SUN01 payer-id cluster) and CO-26/N650 (FCC file question) -> the coinsurance stays on insurance per
#     William's board rows and the contractual correction is DEFERRED with them (it alone would flip the coinsurance to the patient);
#     OA-23 / CO-96: the two-write-off post above (or WOCAID2ND alone when the balance already equals the coinsurance).
# Rules: --dry = read only; 3 consecutive addpayments faults stop the run; register registers/era_sun_<stamp>.json + era_manual_register.json.
# Never touches: the Post button, patient balances, plans, any other check.
import amd, txh, payreasons, resave, move_to_ins, freq1_visit, json, sys, time, os, re
import xml.etree.ElementTree as ET
DRY = "--dry" in sys.argv; S = "2026-09-30T0110Z"; CID = "1052885"
amd.login_cached()
chk = [c for c in json.load(open("scan_0930_0110/era_checks_before.json")) if str(c["id"]) == CID][0]
det = json.load(open("era_details/%s.json" % CID))["eracheckdetails"]
REROUTE = {"19455778": "1,2", "19455721": "2,3", "19455765": "4,5"}; REROUTE_SEQ = {"19455778": 1, "19455721": 2, "19455765": 4}   # verified 2110Z/2310Z (AMD 271 + prior Medicare payments)
MEDICAID_ONLY = {"17469541", "17477829", "17471755"}
HOLD_CO = {"CO26", "CO16", "26", "16"}
def L(m): print(m, flush=True)
def esc(x): return (str(x) if x is not None else "").replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")
def live(pid, vid):
    root = txh.fetch_visit(pid, vid); res = {}
    for c in root.iter("charge"):
        if c.get("void") == "1" or c.get("visit") != str(vid): continue
        res[c.get("id").replace("charge", "")] = {"fee": float(c.get("fee") or 0), "paid": float(c.get("paid") or 0), "patbal": float(c.get("patbal") or 0), "insbal": float(c.get("insbal") or 0), "carrier": c.get("carrier"), "cpt": c.get("proccode"), "dos": c.get("dos"),
            "pays": [(float(p.get("amount") or 0), (p.get("checknumber") or "").strip(), p.get("carrier"), p.get("void"), p.get("date")) for p in c.iter("payment")]}
    return res
def medicare_split(st):
    mp = [p for p in st["pays"] if p[2] == "FLO02" and p[3] != "1" and p[0] < 0]
    if not mp: return None
    paid = -sum(p[0] for p in mp); chkno = mp[0][1]; dt = mp[0][4] or ""
    if st["cpt"] in ("G0439", "G0438"): allowed = paid / 0.98; coins = 0.0
    else: allowed = paid / 0.784; coins = round(0.2 * allowed, 2)
    return paid, chkno, dt, coins, round(st["fee"] - paid - coins, 2)
def post_multi(pid, v, cid, ch, pay, wos, note):
    """ERA-linked addpayments (payreasons shape) with a LIST of write-offs [(amount, code), ...] on one charge."""
    rt = ET.fromstring(resave.detail(cid)); c = [x for x in rt.iter("charge") if x.get("id") == "charge" + str(cid)][0]
    bal = float(c.get("insbalance") or 0); allowed = float(ch.get("allowedamount") or 0); wot = round(sum(a for a, _ in wos), 2)
    if pay + wot > bal + 0.005: raise RuntimeError("over-apply on charge %s: pay %.2f + wo %.2f > insbalance %.2f" % (cid, pay, wot, bal))
    reasons = "".join('<reason id="%s" reasonid="%s" code="%s" name="%s" amount="%s" units="0" group="%s"/>' % (r["reportreasondetailid"], r["payreasonid"], r["reasoncode"], esc(r["reasontext"]), r["reasonamt"], r["payreasongroup"]) for r in ch.get("carc", []))
    first = ch["carc"][0]["reasoncode"] if ch.get("carc") else ""
    wox = "".join('<writeoff id="" risk="0" amount="%.2f" code="%s" status="B"/>' % (a, code) for a, code in wos if a > 0)
    charges = ('<charge id="charge%s" allowed="%.2f" insportion="%s" patportion="%s" insbalance="%.2f" patbalance="%s" profile="prof%s">'
               '<paymentlist><payment amount="%.2f" id="" reason="%s" status="B"><reasonlist payment="%.2f" allowed="%.2f">%s</reasonlist></payment></paymentlist>'
               '<writeofflist>%s</writeofflist></charge>' % (cid, allowed, c.get("insportion") or "%.2f" % bal, c.get("patportion") or "0.00", bal, c.get("patbalance") or "0.00", v["profileid"], pay, first, pay, allowed, reasons, wox))
    dd = str(chk.get("depositdate") or "")[:10]; dd = "%s/%s/%s" % (dd[5:7], dd[8:10], dd[:4])
    xml = ('<ppmdmsg action="addpayments" class="paymententry" msgtime="%s" useopenedge="1" checkout="0" date="" nocookie="1">'
           '<patient patientid="pat%s" paysource="2" postingmethod="era" amount="%.2f" paycode="PE" woamount="%.2f" paymethod="%s" carrierid="car%s" '
           'depositdate="%s" eraclaimid="%s" erareportid="%s" case_note="%s" checknumber="%s" inclstmt="0" postedby="POI0712" batch="">'
           '<unappliedpaymentlist/><unappliedwriteofflist/><chargelist>%s</chargelist></patient></ppmdmsg>'
           % (amd._msgtime(), pid, pay, wot, payreasons.PAYMETHOD.get(chk.get("paymentcode"), "9"), chk["systemcarrierid"], dd, v["checkclaimid"], chk["id"], esc(note), chk["paymentnumber"], charges))
    r = amd.post(xml); ok = 'success="1"' in r and "<Fault" not in r; m = re.search(r'paymentid="(\d+)"', r)
    return ok, (m.group(1) if m else ""), re.sub(r"\s+", " ", r)[:200]
out = {"stamp": S, "check": CID, "dry": DRY, "lines": []}; faults = 0; done = set(); rerouted = set()
REGF = "registers/era_manual_register.json"; reg = json.load(open(REGF))
def rec(r): out["lines"].append(r); L("  -> %s" % r.get("outcome"))
for v in det:
    pid = str(v["patientid"]); vid = str(v["visitid"]); st_all = None
    for ch in v.get("charges") or []:
        cid = str(ch["chargedetailid"]); paid = float(ch.get("paymentamount") or 0)
        carcs = [str(a["reasoncode"]).strip().upper() for a in ch.get("carc") or []]; rarcs = [x["remarkcode"] for x in ch.get("rarc") or [] if x["remarkcode"] != "#AM"]
        co = sum(float(a["reasonamt"] or 0) for a in ch.get("carc") or [] if a["payreasongroup"] in ("CO", "OA", "PI"))
        r = {"pid": pid, "vid": vid, "cid": cid, "claim": v["checkclaimid"], "cpt": ch["chargecode"], "dos": ch["dos"][:10], "paid": paid, "carcs": carcs, "rarcs": rarcs, "when": S}
        key = (cid, "+".join(carcs)); L("v%s pat%s c%s %s %s paid=%.2f %s %s" % (vid, pid, cid, ch["chargecode"], ch["dos"][:10], paid, "+".join(carcs), "+".join(rarcs)))
        if faults >= 3: r["outcome"] = "not attempted - 3 consecutive addpayments faults"; rec(r); continue
        if key in done: r["outcome"] = "skip - same charge/answer already handled on this check"; rec(r); continue
        done.add(key)
        if st_all is None: st_all = live(pid, vid); time.sleep(0.3)
        st = st_all.get(cid)
        if not st: r["outcome"] = "skip - charge not live"; rec(r); continue
        r["before"] = {k: st[k] for k in ("fee", "paid", "insbal", "patbal", "carrier")}
        if any(p[1] == chk["paymentnumber"] and p[3] != "1" for p in st["pays"]): r["outcome"] = "already-posted"; rec(r); continue
        bal = st["insbal"]
        if paid > 0:
            if bal <= 0: r["outcome"] = "residual %.2f" % paid; rec(r); continue
            pay = min(paid, bal); wo = max(0.0, min(round(co, 2), round(bal - pay, 2)))
            code = "WOCAID2ND" if any(c.endswith("23") and c.startswith("OA") for c in carcs) else ((ch.get("payreasonwocode") or "").strip() or "WOINS")
            r.update(pay=round(pay, 2), wo=round(wo, 2), wocode=code, residual=round(paid - pay, 2))
            if pay + wo < bal - 0.01: r["outcome"] = "HELD - pay %.2f + wo %.2f leaves %.2f on a last-payer charge" % (pay, wo, bal - pay - wo); rec(r); continue
            if DRY: r["outcome"] = "DRY would post pay %.2f + %s %.2f" % (pay, code, wo); rec(r); continue
            ok, payid, resp = payreasons.post_line(pid, vid, chk, v, cid, ch, pay=round(pay, 2), wo=round(wo, 2), wocode=code)
            time.sleep(0.7); st_all = live(pid, vid); s2 = st_all.get(cid) or {}
            r.update(outcome="posted" if ok else "FAULT", paymentid=payid, resp=resp[:160], after={"insbal": s2.get("insbal"), "patbal": s2.get("patbal")}); faults = 0 if ok else faults + 1; rec(r); continue
        if any(c in ("CO18", "18") for c in carcs): r["outcome"] = "duplicate CO-18/N522 - original adjudication on this check, nothing to post"; rec(r); continue
        if any(c in ("CO222", "222") for c in carcs): r["outcome"] = "DENIAL CO-222/N640 (frequency/units) - listed for William, nothing written"; rec(r); continue
        if bal <= 0: r["outcome"] = "skip - insurance balance already 0"; rec(r); continue
        ms = medicare_split(st)
        if ms is None:
            if vid in REROUTE and vid not in rerouted:
                r["outcome"] = "REROUTE to Medicare (insorder %s, freq 1, seq %s)" % (REROUTE[vid], REROUTE_SEQ[vid])
                if DRY: r["outcome"] = "DRY " + r["outcome"]; rec(r); continue
                m = move_to_ins.move(cid, REROUTE[vid]); r["move"] = str(m)[:160]; time.sleep(0.8)
                if "FAULT" in str(m).upper() or "not live" in str(m): r["outcome"] = "REROUTE FAULT " + str(m)[:120]
                else: r["rebill"] = str(freq1_visit.run(vid, cid, REROUTE_SEQ[vid]))[:120]; r["outcome"] += " -> " + r["rebill"][:80]; rerouted.add(vid)
                rec(r); continue
            if vid in rerouted: r["outcome"] = "rerouted with the visit's first line (whole visit re-sent to Medicare)"; rec(r); continue
            if pid in MEDICAID_ONLY and any(c in ("CO96", "96") for c in carcs):
                r.update(pay=0.0, wo=round(bal, 2), wocode="WONCS")
                if DRY: r["outcome"] = "DRY would post $0 + WONCS %.2f" % bal; rec(r); continue
                ok, payid, resp = payreasons.post_line(pid, vid, chk, v, cid, ch, pay=0.0, wo=round(bal, 2), wocode="WONCS")
                r.update(outcome="posted WONCS" if ok else "FAULT", paymentid=payid, resp=resp[:160]); faults = 0 if ok else faults + 1; rec(r); time.sleep(0.7); continue
            r["outcome"] = "HOLD - $0 primary answer %s with no rule (%s)" % ("+".join(carcs), "+".join(rarcs)); rec(r); continue
        mpaid, mchk, mdt, coins, contr = ms; r["medicare"] = {"paid": mpaid, "check": mchk, "coins": coins, "contractual": contr}
        needs_fix = abs(bal - (coins + contr)) < 0.06 and contr > 0.005
        if not needs_fix and abs(bal - coins) >= 0.06: r["outcome"] = "HOLD - balance %.2f is neither coinsurance %.2f nor coinsurance+contractual %.2f" % (bal, coins, coins + contr); rec(r); continue
        if any(c in HOLD_CO for c in carcs):
            r["outcome"] = "coinsurance %.2f stays on insurance (%s - William's row)%s" % (coins, "+".join(carcs), "; contractual correction WOINS %.2f DEFERRED with it (alone it flips the coinsurance to the patient)" % contr if needs_fix else ""); rec(r); continue
        if coins <= 0.005 and needs_fix: wos = [(round(bal, 2), "WOINS")]
        elif needs_fix: wos = [(round(contr, 2), "WOINS"), (round(bal - contr, 2), "WOCAID2ND")]
        else: wos = [(round(min(coins, bal), 2), "WOCAID2ND")]
        r.update(pay=0.0, wos=wos, wo=round(sum(a for a, _ in wos), 2), wocode="+".join(c for _, c in wos))
        note = ("Medicare contractual correction WOINS %.2f (CO-45 never adjusted, Medicare check %s) + Sunshine %s coinsurance WOCAID2ND, run %s" % (contr, mchk, "+".join(carcs), S)) if needs_fix else ""
        if DRY: r["outcome"] = "DRY would post $0 + %s" % " + ".join("%s %.2f" % (c, a) for a, c in wos); rec(r); continue
        try: ok, payid, resp = post_multi(pid, v, cid, ch, 0.0, wos, note)
        except RuntimeError as e: ok, payid, resp = False, "", str(e)
        time.sleep(0.7); st_all = live(pid, vid); s2 = st_all.get(cid) or {}
        r.update(outcome=("posted " + r["wocode"]) if ok else "FAULT", paymentid=payid, resp=resp[:160], after={"insbal": s2.get("insbal"), "patbal": s2.get("patbal")}); faults = 0 if ok else faults + 1; rec(r)
        if ok and (s2.get("patbal") or 0) > 0.005: L("!!! patient balance appeared on c%s after the post - stopping" % cid); faults = 3
json.dump(out, open("registers/era_sun_%s%s.json" % (S, "_dry" if DRY else ""), "w"), indent=1)
if not DRY:
    for r in out["lines"]:
        if r.get("outcome", "").startswith(("posted", "already", "residual")):
            reg.append({"checkid": CID, "checkclaimid": r["claim"], "visitid": r["vid"], "chargedetailid": r["cid"], "cpt": r["cpt"], "outcome": r["outcome"].split()[0], "pay": r.get("pay"), "wo": r.get("wo"), "wocode": r.get("wocode"), "when": S})
    json.dump(reg, open(REGF, "w"), indent=1)
from collections import Counter
L(str(Counter(r["outcome"].split(" (")[0][:34] for r in out["lines"])))
L("pay $%.2f | WOINS $%.2f | WOCAID2ND $%.2f | WONCS $%.2f | other %s" % (sum(r.get("pay", 0) for r in out["lines"] if r["outcome"].startswith(("posted", "DRY"))),
  sum(a for r in out["lines"] if r["outcome"].startswith(("posted", "DRY")) for a, c in (r.get("wos") or [(r.get("wo", 0), r.get("wocode", ""))]) if c == "WOINS"),
  sum(a for r in out["lines"] if r["outcome"].startswith(("posted", "DRY")) for a, c in (r.get("wos") or [(r.get("wo", 0), r.get("wocode", ""))]) if c == "WOCAID2ND"),
  sum(a for r in out["lines"] if r["outcome"].startswith(("posted", "DRY")) for a, c in (r.get("wos") or [(r.get("wo", 0), r.get("wocode", ""))]) if c == "WONCS"),
  Counter(c for r in out["lines"] if r["outcome"].startswith(("posted", "DRY")) for a, c in (r.get("wos") or [(r.get("wo", 0), r.get("wocode", ""))]) if c not in ("WOINS", "WOCAID2ND", "WONCS"))))
