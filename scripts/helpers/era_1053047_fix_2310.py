# PLAIN ENGLISH (two leftover lines of UHC ERA 1053047 W0904074, 7 PM ET 10/7/2026 slot, run 2026-10-07T2310Z)
# Decides, per section:
#   A. chart 17476748 v19453702 99349 9/2/2026 (charge 23364586): UHC paid 104.25 (CO-45 91.63 + CO-253 2.12) but the charge sits at $0
#      because Medicare's $0 answer of 9/10/2026 was posted with a WOINS write-off of the whole $198 (write-off 22480287) before the claim
#      went on to UHC. The money is real: VOID that write-off (void_tx.void_writeoff - the Payment-Entry Void shape), re-read the charge
#      (a voided write-off can land on the patient balance -> move_to_ins.move(cid, rebill=False) first), then post the UHC line through the
#      ERA-LINKED Payment Entry shape (payreasons.post_line with check 1053047's own eraclaimid / erareportid, so the CO-45 / CO-253 reasons
#      stay on the payment) - pay = min(104.25, open balance), WOINS = the contractual capped so pay + wo <= the balance.
#   B. chart 17475777 v19435223 99306 + 99497 3/6/2026 (charges 23342218 / 23342219): UHC's OA-18 'exact duplicate' answers the 9/10/2026
#      frequency-1 re-send; the ORIGINAL adjudication is on the chart - UHC check V5475692 (ICN KLC0434879400) paid 162.19 + 52.34 on
#      9/2/2026 and its WOINS write-offs (93.81 / 80.66) were voided on 9/5/2026, leaving the contractual open as insurance balance.
#      Settle the original (the standing OA-18 rule - never rebill): write the contractual off WOINS under the original check number.
#      A write-off-only Payment Entry (no <payment> element) is tried first so no $0 code-less payment line is born; when AMD refuses that
#      shape the standard manual_post.post(pay 0, wo) shape is used (unbilled_repair.py voids the $0 line if it ever surfaces in Unbilled).
# Rules it uses: ERA step 5(d) (max accepted, residual disregarded, ERA-linked shape for an ERA line), the OA-18 duplicate rule (settle the
#   original adjudication, no rebill), the 10/7 1710Z lesson (balance moved back before the post). --dry by default; --live writes.
#   --only A|B limits the run to one section. Register registers/era_1053047_fix_2026-10-07T2310Z[_dry].json.
# Never touches: claims, rebills, plans, the ERA Center Post button, any other visit.
import amd, txh, payreasons, move_to_ins, void_tx, manual_post, resave, json, sys, time, re
import xml.etree.ElementTree as ET
a = sys.argv; DRY = "--live" not in a; S = "2026-10-07T2310Z"
ONLY = a[a.index("--only") + 1] if "--only" in a else "AB"
amd.login_cached()
chk = [c for c in json.load(open("registers/era_checks_before_%s.json" % S)) if str(c["id"]) == "1053047"][0]
det = json.load(open("era_details/1053047.json"))["eracheckdetails"]
out = []
def L(m): print(m, flush=True)
def live(pid, vid):
    root = txh.fetch_visit(pid, vid); res = {}
    for c in root.iter("charge"):
        if c.get("void") == "1" or c.get("visit") != str(vid): continue
        res[c.get("id").replace("charge", "")] = {"fee": float(c.get("fee") or 0), "paid": float(c.get("paid") or 0), "patbal": float(c.get("patbal") or 0), "insbal": float(c.get("insbal") or 0), "carrier": c.get("carrier"),
            "pays": [(float(p.get("amount") or 0), (p.get("checknumber") or "").strip(), p.get("void"), p.get("id")) for p in c.iter("payment")],
            "wos": [(float(w.get("amount") or 0), w.get("wocode"), w.get("void"), w.get("id"), w.get("date")) for w in c.iter("writeoff")]}
    return res

if "A" in ONLY:
    pid, vid, cid, woid = "17476748", "19453702", "23364586", "22480287"
    v = [x for x in det if str(x["visitid"]) == vid][0]; ch = [c for c in v["charges"] if str(c["chargedetailid"]) == cid][0]
    paid = float(ch["paymentamount"]); co = sum(float(x["reasonamt"] or 0) for x in ch["carc"] if x["payreasongroup"] in ("CO", "OA", "PI"))
    st = live(pid, vid); s = st[cid]; r = {"section": "A", "pid": pid, "vid": vid, "cid": cid, "before": {k: s[k] for k in ("fee", "paid", "insbal", "patbal", "carrier")}, "wos": s["wos"], "pays": s["pays"]}
    L("A before: %s" % r["before"]); L("A write-offs: %s" % s["wos"])
    wo_live = [w for w in s["wos"] if w[3] == woid and w[2] != "1"]
    if any(p[1] == chk["paymentnumber"] and p[2] != "1" for p in s["pays"]): r["outcome"] = "already-posted"; L("A already posted")
    elif not wo_live and s["insbal"] <= 0: r["outcome"] = "HOLD - write-off %s not live and balance 0 (someone else settled it)" % woid; L(r["outcome"])
    elif DRY: r["outcome"] = "DRY would void write-off %s (%.2f), move any patient balance back, then post pay %.2f + WOINS %.2f ERA-linked" % (woid, wo_live[0][0] if wo_live else 0, paid, min(co, s["fee"] - paid)); L(r["outcome"])
    else:
        if wo_live:
            ok, msg = void_tx.void_writeoff(pid, cid, woid); r["void"] = (ok, msg); L("A void write-off %s -> %s %s" % (woid, ok, msg))
            if not ok: r["outcome"] = "FAULT void"; out.append(r); json.dump(out, open("registers/era_1053047_fix_%s.json" % S, "w"), indent=1); sys.exit(1)
            time.sleep(0.7)
        st = live(pid, vid); s = st[cid]; r["after_void"] = {k: s[k] for k in ("insbal", "patbal")}; L("A after void: %s" % r["after_void"])
        if s["insbal"] <= 0 and s["patbal"] > 0:
            mv = move_to_ins.move(cid, rebill=False); r["moved"] = mv; L("A move back: %s" % mv); time.sleep(0.7); st = live(pid, vid); s = st[cid]
        bal = s["insbal"]
        if bal <= 0: r["outcome"] = "HOLD - balance still 0 after the void (%s)" % r.get("after_void"); L(r["outcome"])
        else:
            pay = min(paid, bal); wo = max(0.0, min(round(co, 2), round(bal - pay, 2)))
            ok, payid, resp = payreasons.post_line(pid, vid, chk, v, cid, ch, pay=round(pay, 2), wo=round(wo, 2), wocode="WOINS")
            time.sleep(0.7); s2 = live(pid, vid).get(cid, {})
            r.update(outcome="posted" if ok else "FAULT", pay=pay, wo=wo, wocode="WOINS", paymentid=payid, resp=resp[:160], after={"insbal": s2.get("insbal"), "patbal": s2.get("patbal")})
            L("A post pay %.2f WOINS %.2f ok=%s after %s" % (pay, wo, ok, r["after"]))
    out.append(r)

if "B" in ONLY:
    pid, vid = "17475777", "19435223"; CHK = "V5475692"; ICN = "KLC0434879400"
    st = live(pid, vid)
    for cid in ("23342218", "23342219"):
        s = st.get(cid); r = {"section": "B", "pid": pid, "vid": vid, "cid": cid, "before": {k: s[k] for k in ("fee", "paid", "insbal", "patbal", "carrier")}, "orig_check": CHK, "icn": ICN}
        orig = [p for p in s["pays"] if p[1] == CHK and p[2] != "1"]
        if not orig: r["outcome"] = "HOLD - the original payment %s is not live on the charge" % CHK; L(r["outcome"]); out.append(r); continue
        bal = s["insbal"]; wo = round(bal, 2)
        if bal <= 0: r["outcome"] = "skip - balance already 0"; L("B c%s balance 0" % cid); out.append(r); continue
        if abs(s["fee"] - abs(orig[0][0]) - bal) > 0.011: r["outcome"] = "HOLD - open balance %.2f is not fee %.2f minus the original payment %.2f" % (bal, s["fee"], abs(orig[0][0])); L(r["outcome"]); out.append(r); continue
        note = "OA-18 duplicate on W0904074 (ERA 1053047) of the original adjudication %s (ICN %s, paid %.2f 9/2/2026) - contractual of the original, run %s" % (CHK, ICN, abs(orig[0][0]), S)
        if DRY: r["outcome"] = "DRY would write off %.2f WOINS under %s (write-off-only shape, manual_post fallback)" % (wo, CHK); L("B c%s %s" % (cid, r["outcome"])); out.append(r); continue
        # write-off-only Payment Entry: the manual_post shape without the <payment> element
        rt = ET.fromstring(resave.detail(cid)); vis = rt.find(".//visit"); c = [x for x in rt.iter("charge") if x.get("id") == "charge" + cid][0]
        prof = vis.get("profile")
        chg = ('<charge id="charge%s" allowed="0.00" insportion="%s" patportion="%s" insbalance="%.2f" patbalance="%s" profile="%s"><paymentlist/>'
               '<writeofflist><writeoff id="" risk="0" amount="%.2f" code="WOINS" status="B"/></writeofflist></charge>'
               % (cid, c.get("insportion") or "%.2f" % bal, c.get("patportion") or "0.00", bal, c.get("patbalance") or "0.00", prof, wo))
        xml = ('<ppmdmsg action="addpayments" class="paymententry" msgtime="%s" useopenedge="1" checkout="0" date="" nocookie="1">'
               '<patient patientid="pat%s" paysource="2" postingmethod="" amount="0.00" paycode="PE" woamount="%.2f" paymethod="9" carrierid="%s" '
               'depositdate="09/02/2026" case_note="%s" checknumber="%s" inclstmt="0" postedby="POI0712" batch="">'
               '<unappliedpaymentlist/><unappliedwriteofflist/><chargelist>%s</chargelist></patient></ppmdmsg>'
               % (amd._msgtime(), pid, wo, manual_post.CAR["UNI20"], note, CHK, chg))
        resp = amd.post(xml); ok = 'success="1"' in resp and "<Fault" not in resp; r["shape"] = "write-off-only"; r["resp"] = re.sub(r"\s+", " ", resp)[:200]
        time.sleep(0.7); s2 = live(pid, vid).get(cid, {})
        if not ok or (s2.get("insbal") or 0) > bal - wo + 0.011:
            L("B c%s write-off-only shape refused or did not apply (%s) - manual_post fallback" % (cid, r["resp"][:120]))
            ok, msg = manual_post.post(cid, "UNI20", 0.0, wo, "WOINS", checknumber=CHK, depositdate="09/02/2026", note=note); r["shape"] = "manual_post pay 0"; r["resp"] = msg[:200]
            time.sleep(0.7); s2 = live(pid, vid).get(cid, {})
        r.update(outcome="posted" if ok else "FAULT", wo=wo, wocode="WOINS", after={"insbal": s2.get("insbal"), "patbal": s2.get("patbal")})
        L("B c%s WOINS %.2f under %s ok=%s shape=%s after %s" % (cid, wo, CHK, ok, r["shape"], r["after"])); out.append(r)

json.dump(out, open("registers/era_1053047_fix_%s%s.json" % (S, "_dry" if DRY else ""), "w"), indent=1)
if not DRY:
    REGF = "registers/era_manual_register.json"; reg = json.load(open(REGF))
    for r in out:
        if r.get("outcome") == "posted": reg.append({"checkid": "1053047" if r["section"] == "A" else r["orig_check"], "visitid": r["vid"], "chargedetailid": r["cid"], "outcome": "posted", "pay": r.get("pay", 0), "wo": r.get("wo"), "wocode": r.get("wocode"), "when": S, "note": "era_1053047_fix_2310 section " + r["section"]})
    json.dump(reg, open(REGF, "w"), indent=1)
L(json.dumps([{k: r[k] for k in ("section", "vid", "cid", "outcome")} for r in out]))
