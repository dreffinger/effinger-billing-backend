# PLAIN ENGLISH (ERA manual-post fallback, 5am ET 9/13/2026 run - prompt v5 step 5d; = era_fallback_0913.py + --stamp/--checks args + register de-duplication: a line whose (check, claim, charge, outcome) is already in the register is not appended again)
# Decides: for every unposted ERA check, every claim MONEY line the Post button refused or era_post skipped
#   (unvalidated 'procedure codes do not match', 'multiple adjustment amounts', refused faults) is matched to the
#   LIVE charge by CPT + DOS and posted through the ERA-linked Payment Entry shape (payreasons.post_line - carries the remit's
#   reason codes; manual_post.post dropped them until 9/21/2026), William's rule: post the
#   maximum AMD accepts, disregard the residual. Reversal lines (negative / 'reversal does not match') are never posted.
#   A non-void payment already carrying this check number on the charge = 'already posted' - nothing posted.
# Rules it uses: pay = min(ERA paid, open insurance balance); wo = CO adjustments capped so pay+wo <= balance
#   (WOINS contractual, WOLATE CO-29, WONCS CO-96/204); PR amounts never written off; $0 balance = already adjudicated.
# Never touches: denial-only ($0) lines, reversal lines, orphan lines (no matching charge), anything already posted.
"""Usage: python3 era_fallback_0913.py [--dry] [--max-faults 3]"""
import json, os, sys, time, datetime, collections
import txh, manual_post, amd, payreasons
dry = "--dry" in sys.argv
STAMP = sys.argv[sys.argv.index("--stamp") + 1] if "--stamp" in sys.argv else "2026-09-13T0930Z"
REGF = "registers/era_manual_register.json"
reg = json.load(open(REGF)) if os.path.exists(REGF) else []
settled = {(r["checkid"], r.get("checkclaimid"), r.get("chargedetailid") or r.get("cpt")) for r in reg if r["outcome"] in ("posted", "already-posted")}
checks = json.load(open(sys.argv[sys.argv.index("--checks") + 1] if "--checks" in sys.argv else "era_checks_before_2026-09-13T0930Z.json"))
seen = {(r["checkid"], r.get("checkclaimid"), r.get("chargedetailid") or r.get("cpt"), r["outcome"]) for r in reg}  # .get: the 9/21 2110Z hand-post-restored entries carry no checkclaimid (KeyError 9/22 0310Z)
TX = {}
def charges_of(pid):
    if pid not in TX:
        try: TX[pid] = [c for c in txh.fetch("pat%s" % pid).iter("charge") if c.get("void") != "1"]
        except Exception as e: print("txh err", pid, str(e)[:80]); TX[pid] = []
        time.sleep(0.3)
    return TX[pid]
def norm_dos(s):
    s = (s or "")[:10]
    if "-" in s:
        y, m, d = s.split("-"); return "%s/%s/%s" % (m, d, y)
    return s
out = []; faults = 0; tot = collections.Counter(); dol = collections.Counter()
for chk in checks:
    cid = str(chk["id"]); chkno = chk["paymentnumber"]; car = chk["systemcarriercode"] or ""
    ddate = (chk.get("depositdate") or chk.get("receiveddate") or "")[:10]
    dd = norm_dos(ddate)
    f = "era_details/%s.json" % cid
    if not os.path.exists(f): continue
    det = json.load(open(f))["eracheckdetails"]
    for cl in det:
        if float(cl.get("paymentamount") or 0) <= 0: continue          # denial-only claim -> denial handling
        vid = cl.get("visitid"); pid = cl.get("patientid")
        errs = [e.get("id") for e in (cl.get("errors") or [])]
        if not vid or not pid or pid <= 0 or 1 in errs:
            out.append({"checkid": cid, "checkclaimid": cl["checkclaimid"], "visitid": vid, "outcome": "orphan", "amt": cl["paymentamount"], "carrier": car, "when": STAMP, "why": "no visit AMD can identify"}); tot["orphan"] += 1; dol["orphan"] += float(cl["paymentamount"]); continue
        if cl.get("hasreversals") or 11 in errs:
            out.append({"checkid": cid, "checkclaimid": cl["checkclaimid"], "visitid": vid, "outcome": "reversal-skipped", "amt": cl["paymentamount"], "carrier": car, "when": STAMP}); tot["reversal"] += 1; dol["reversal"] += float(cl["paymentamount"]); continue
        live = [c for c in charges_of(pid) if c.get("visit") == str(vid)]
        for ln in cl.get("charges") or []:
            paid = float(ln.get("paymentamount") or 0)
            if paid <= 0: continue
            key = (cid, cl["checkclaimid"], ln.get("chargedetailid") or ln.get("chargecode"))
            if key in settled: tot["register-skip"] += 1; continue
            cpt = (ln.get("chargecode") or "").strip(); ldos = norm_dos(ln.get("dos"))
            m = [c for c in live if (c.get("proccode") or "").strip() == cpt and c.get("dos") == ldos]
            if not m and len(live) == 1 and live[0].get("dos") == ldos and len(cl.get("charges") or []) == 1: m = live  # single-charge visit, single ERA line, same DOS
            rec = {"checkid": cid, "checkclaimid": cl["checkclaimid"], "visitid": vid, "pid": pid, "cpt": cpt, "dos": ldos, "era_paid": paid, "carrier": car, "checkno": chkno, "when": STAMP, "chargedetailid": ln.get("chargedetailid")}
            if not m:
                rec.update(outcome="orphan", why="no live charge with CPT %s on %s (live: %s)" % (cpt, ldos, [(c.get("proccode"), c.get("dos")) for c in live])); out.append(rec); tot["orphan"] += 1; dol["orphan"] += paid; continue
            c = m[0]; chg = c.get("id"); rec["chargeid"] = chg
            pays = [p for p in c.iter("payment") if p.get("void") != "1" and float(p.get("amount") or 0) != 0]
            if any((p.get("checknumber") or "").strip() == str(chkno).strip() for p in pays):
                rec.update(outcome="already-posted"); out.append(rec); tot["already"] += 1; dol["already"] += paid; continue
            insbal = float(c.get("insbal") or 0)
            if insbal <= 0:
                rec.update(outcome="residual %.2f" % paid, why="open insurance balance $0 - already adjudicated (paid by %s)" % [(p.get("carrier"), p.get("amount"), p.get("checknumber")) for p in pays][:2]); out.append(rec); tot["residual-zero"] += 1; dol["residual"] += paid; continue
            pay = min(paid, insbal)
            co = 0.0; code = "WOINS"
            for a in cl.get("carc") or []:
                if a.get("chargedetailid") not in (None, ln.get("chargedetailid")) and ln.get("chargedetailid"): continue
                grp = (a.get("payreasongroup") or "").upper(); rc = str(a.get("reasoncode") or "")
                if grp == "CO":
                    co += float(a.get("reasonamt") or 0)
                    if rc == "29": code = "WOLATE"
                    elif rc in ("96", "204", "50"): code = "WONCS"
            wo = max(0.0, min(co, insbal - pay))
            rec.update(pay=round(pay, 2), wo=round(wo, 2), wocode=code, residual=round(paid - pay, 2), insbal=insbal)
            if dry:
                rec.update(outcome="DRY would post"); out.append(rec); tot["would-post"] += 1; dol["would-pay"] += pay; dol["would-wo"] += wo; continue
            try:
                # 9/21/2026: post through the ERA-LINKED Payment Entry shape (payreasons.post_line = addpayments postingmethod=era with
                # eraclaimid/erareportid + the remit's reasonlist) - it keeps the CO45/PR2/CO253 reason codes on the payment, so the
                # next payer's claim can be built. manual_post.post (plain addpayments) drops reason codes -> 54 secondaries held 9/15-9/21.
                ln_c = dict(ln); ln_c["chargedetailid"] = int(chg)
                ok, payid, msg = payreasons.post_line(pid, vid, chk, cl, chg, ln_c, pay=pay, wo=wo, wocode=code)
                if ok: rec["paymentid"] = payid
            except Exception as e: ok, msg = False, str(e)
            if ok:
                rec.update(outcome="posted"); tot["posted"] += 1; dol["posted-pay"] += pay; dol["posted-wo"] += wo
                if paid - pay > 0.004: dol["residual"] += paid - pay; tot["residual-partial"] += 1
            else:
                rec.update(outcome="fault", why=str(msg)[:200]); tot["fault"] += 1; faults += 1
            out.append(rec); time.sleep(0.5)
            if faults >= 3: print("3 consecutive addpayments faults - stopping fallback"); break
            if ok: faults = 0
        if faults >= 3: break
    if faults >= 3: break
json.dump(out, open("registers/era_fallback_%s_%s.json" % (STAMP, "dry" if dry else "live"), "w"), indent=1)
if not dry:
    reg += [r for r in out if r["outcome"] not in ("DRY would post",) and (r["checkid"], r["checkclaimid"], r.get("chargedetailid") or r.get("cpt"), r["outcome"]) not in seen]
    json.dump(reg, open(REGF, "w"), indent=1)
print("counts", dict(tot)); print("dollars", {k: round(v, 2) for k, v in dol.items()})
for r in out:
    if r["outcome"] in ("fault",) or r["outcome"].startswith("DRY") or r["outcome"] == "posted": print(" ", r["outcome"], r["checkid"], r["carrier"], "v", r["visitid"], r.get("cpt"), r.get("dos"), "paid", r["era_paid"], "->pay", r.get("pay"), "wo", r.get("wo"), r.get("wocode"), "insbal", r.get("insbal"), r.get("why", "")[:90])
