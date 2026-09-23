#!/usr/bin/env python3
import os
# PLAIN ENGLISH (Post paper / virtual-card remittances through the ERA Center)
# Decides: For every (payer, check) group in plan.json, builds a synthetic 835, imports it into the AMD ERA Center, and posts each
#          money line with the ERA-linked Payment Entry shape (reason codes kept) under the PAYER'S carrier from the chart.
# Rules it uses: pay = the EOB's paid capped at the live insurance balance (post the maximum AMD accepts, report the residual);
#          no write-offs unless --wo (SIM01 residuals: WOMCAD on a primary claim, WOCAID2ND on a secondary one; FLO99 write-offs are HELD -
#          William's rule: FCC reconciles against the FCC portal/checks first); a premature write-off that zeroed a line the payer then paid is
#          voided before posting; a line already carrying a live payment with this check number is skipped; a $0 balance with another payer's
#          live payment = overpayment -> HOLD (refund/recoup decision); the payer's plan is added to the chart when missing (member id from
#          the EOB, NO group number); every check is dismissed after its lines are handled so the 2-hourly routine never Posts it under the
#          wrong (billed) carrier.  Never touches: charges, claims, other payers' payments.
# ---
"""Usage: python3 post_paper.py [--dry] [--only REF,REF] [--family FAM] [--max N] [--wo]
Reads /home/claude/scans/plan.json (plan.py), writes /home/claude/scans/out835/<fam>_<trace>.835 and post_register.json."""
import sys, os, re, json, time, copy, datetime, argparse, requests
sys.path.insert(0, os.environ.get("SCANS_DIR", "/home/claude/scans") + "")
import build835, amd, era_post, era_upload, txh, resave, add_ins, void_tx, payreasons
from payreasons import f, num, L

PLAN = os.environ.get("SCANS_DIR", "/home/claude/scans") + "/plan.json"; OUT = os.environ.get("SCANS_DIR", "/home/claude/scans") + "/out835"; REG = os.environ.get("SCANS_DIR", "/home/claude/scans") + "/post_register.json"
CAR = {"UA": "42005", "WN": "41999", "AET12": "42009", "MUT01": "42012", "ECHO": "302810", "SIM01": "42019", "FLO99": "42008", "USAA": "303211", "CHAMPVA": "6447"}
CARCODE = {"UA": "UNI01", "WN": "BAN07", "AET12": "AET12", "MUT01": "MUT01", "ECHO": "PHY10", "SIM01": "SIM01", "FLO99": "FLO99", "USAA": "USAA", "CHAMPVA": "CHA03"}
REUSE = {"1370764627": "1051743"}          # checks already in the Center from the 9/22 import tests (TRN suffixed 'T'; posted with the clean number)
WO_HOLD = {"FLO99"}                        # never write off from this engine
os.makedirs(OUT, exist_ok=True)
register = json.load(open(REG)) if os.path.exists(REG) else []
def save(): json.dump(register, open(REG, "w"), indent=1, default=str)
def rec(**kw):
    kw["when"] = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"); register.append(kw); save()
    L("   %-8s %s %s %s %s" % (kw.get("status"), kw.get("family"), kw.get("acct"), kw.get("cpt", ""), kw.get("note", "")))
def done_key(fam, ref, acct, cpt): return any(r.get("family") == fam and r.get("ref") == ref and r.get("acct") == acct and r.get("cpt") == cpt and r.get("status") == "POSTED" for r in register)

def plans(pid):
    r = amd.post('<ppmdmsg action="getdemographic" class="demographics" msgtime="%s" patientid="pat%s" nocookie="1"/>' % (amd._msgtime(), num(pid)))
    pl = []
    for blk in re.findall(r"<insplan [^>]*>", r):
        a = dict(re.findall(r'(\w+)="([^"]*)"', blk)); pl.append(a)
    dead = re.search(r'deathdate="([^"]+)"', r) or re.search(r'dod="([^"]+)"', r)
    return pl, (dead.group(1) if dead else "")
def ensure_plan(pid, fam, member, dry):
    """the payer's carrier on the chart (any sequence, any dates) -> numeric carrier id; adds the plan when missing (no group number)."""
    pl, _ = plans(pid)
    for p in pl:
        if num(p.get("carrier")) == CAR[fam]: return CAR[fam], p.get("id"), "on chart seq %s" % p.get("sequence")
    if dry: return CAR[fam], None, "MISSING on chart (would add %s member %s)" % (CARCODE[fam], member or "?")
    if not member: return None, None, "plan missing and no member id on the EOB"
    insid, seq = add_ins.add(pid, "car" + CAR[fam], member)
    if insid: return CAR[fam], insid, "ADDED %s as %s seq %s (member %s, no group)" % (CARCODE[fam], insid, seq, member)
    return None, None, "addinsurance failed: %s" % seq

def find_check(trace, since="2026-09-22"):
    for c in checks_safe():
        if str(c.get("paymentnumber", "")).split("(")[0] == trace: return c
    d = payreasons.dismissed_index(since)
    for cid, x in d.items():
        if str(x.get("paymentnumber", "")).split("(")[0] == trace:
            ok, _ = payreasons.restore(cid)
            if ok:
                for c in checks_safe():
                    if str(c["id"]) == str(cid): return c
    return None
def upload_group(rm, ctrl, dry):
    text, total, trace = build835.build(rm, ctrl)
    fn = os.path.join(OUT, "%s_%s.835" % (rm["family"], trace)); open(fn, "w").write(text)
    if dry: return None, trace, fn, total
    if trace in REUSE:
        for c in checks_safe():
            if str(c["id"]) == REUSE[trace]: return c, trace, fn, total
    c = find_check(trace)
    if c: L("   check %s already in the Center for TRN %s (reusing)" % (c["id"], trace)); return c, trace, fn, total
    code, txt = era_upload.upload(fn); L("   upload %s -> HTTP %s %s" % (os.path.basename(fn), code, txt[:100].replace("\n", " ")))
    for i in range(30):                      # the import is asynchronous: 5 s .. 4 min seen on 9/22; polling every 5 s drew HTTP 500s
        time.sleep(10)
        for c in checks_safe():
            if str(c.get("paymentnumber", "")).split("(")[0] == trace: L("   check %s appeared after %d s" % (c["id"], (i + 1) * 5)); return c, trace, fn, total
    return None, trace, fn, total
def dismiss(chk):
    ok, t = payreasons.redismiss(chk["id"]); return ok

def checks_safe():
    for i in range(6):
        try: return era_post.checks()
        except Exception as e: L("   /era/checks: %s (retry %d)" % (str(e)[:80], i + 1)); time.sleep(8 + 4 * i)
    raise RuntimeError("/era/checks kept failing")
def live_lines(pid, vid):
    for i in range(4):
        try: st = payreasons.visit_state(pid, vid, root=txh.fetch_visit(pid, vid))   # visit-scoped: page 1 of a long chart misses old visits
        except Exception as e: L("   gettxhistory %s/%s: %s" % (pid, vid, str(e)[:80])); st = []
        if st: return st
        time.sleep(2 + i)
    return []
def line_plan(fam, seq, ch, live, ref):
    """decide one ERA charge line against the live charge -> dict(action, pay, wo, wocode, void_wos, note)"""
    paid = f(ch.get("paymentamount")); bal = f(live["insbalance"])
    live_pays = [p for p in live["pays"] if p["void"] != "1"]
    if any(p["checkno"].split("(")[0] == ref and abs(p["amount"] - paid) < 0.011 for p in live_pays): return {"action": "SKIP", "note": "already posted (live payment %s with this check number)" % ref}
    carc = ch.get("carc", [])
    secondary = any(str(x.get("payreasongroup")).upper() == "OA" and num(x.get("reasoncode")) == "23" for x in carc)
    contractual = round(sum(f(x.get("reasonamt")) for x in carc if num(x.get("reasoncode")) in ("45", "253")), 2)   # the primary's contractual + sequestration
    wos = [w for w in live["wos"] if w["void"] != "1"]
    # OVERPAYMENT first: another payer already put the same money on this line (a crossover paid by a Medigap supplement AND a Medicaid plan)
    twin = [p for p in live_pays if p["amount"] > 0 and abs(p["amount"] - paid) < 0.02 and p["checkno"].split("(")[0] != ref]
    if twin and paid > bal + 0.004:
        return {"action": "HOLD", "note": "OVERPAYMENT: %s already paid $%.2f on this line (check %s) and the balance is %.2f - refund/recoup decision" % (twin[0]["carrier"], twin[0]["amount"], twin[0]["checkno"], bal)}
    plan = {"action": "POST", "pay": min(paid, bal), "wo": 0.0, "wocode": None, "void_wos": [], "note": ""}
    need = round(paid - bal, 2)
    if need > 0.004 and wos:
        # a PREMATURE write-off = one whose amount is exactly what the payer then paid (or exactly the shortfall); nothing else is ever voided here
        exact = [w for w in wos if abs(w["amount"] - need) < 0.02 or abs(w["amount"] - paid) < 0.02]
        if exact:
            w = exact[0]; plan["void_wos"] = [w]; plan["note"] = "void premature write-off %s#%s $%.2f first; " % (w["code"], w["id"], w["amount"])
            bal = round(bal + w["amount"], 2); plan["pay"] = min(paid, bal)
        elif bal <= 0.004:
            return {"action": "HOLD", "note": "no insurance balance and no premature write-off to void (live write-offs %s, live payments %s) - review" % ([(w["code"], w["amount"]) for w in wos], [(p["carrier"], p["amount"]) for p in live_pays])}
    if plan["pay"] <= 0.004:
        other = [p for p in live_pays if p["amount"] > 0]
        if other: return {"action": "HOLD", "note": "no insurance balance - already paid by %s (%s $%.2f): OVERPAYMENT/refund decision" % (other[0]["carrier"], other[0]["checkno"], other[0]["amount"])}
        return {"action": "HOLD", "note": "no insurance balance left on the charge (patbal %.2f) - nothing AMD will accept" % f(live["patbalance"])}
    resid = round(bal - plan["pay"], 2); short = round(paid - plan["pay"], 2)
    if short > 0.004: plan["note"] += "SHORTALL: EOB paid %.2f, balance only %.2f -> posting the maximum; " % (paid, plan["pay"])
    if resid > 0.004:
        # what is left after the payer's money: Medicaid plans (SIM01/FLO99) -> dual cost-share / Medicaid contractual write-off in the SAME post
        # (nothing may transfer to a dual's patient balance); Medigap supplements -> WOINS only when it is exactly the primary's contractual
        # that was never adjusted; otherwise leave it to AMD (a Plan N copay etc. is patient responsibility and AMD moves it there itself).
        if fam in ("SIM01", "FLO99"): plan["wo"], plan["wocode"] = resid, ("WOCAID2ND" if secondary else "WOMCAD")
        elif contractual and abs(resid - contractual) < 0.02: plan["wo"], plan["wocode"] = resid, "WOINS"
        plan["resid"] = resid
        plan["note"] += ("write-off %.2f %s; " % (plan["wo"], plan["wocode"])) if plan["wo"] else ("residual %.2f left after the post (AMD: next payer / patient); " % resid)
    return plan

def process_group(g, a, ctrl):
    fam, ref = g["family"], g["ref"]
    claims = [copy.deepcopy(c) for c in g["claims"] if not all(done_key(fam, ref, c["acct"], l.get("cpt")) for l in (c.get("lines") or [{}]))]
    if not claims: L("== %s %s: every line already in the register" % (fam, ref)); return
    L("== %s %s (%s, %s) %d claims $%.2f expected %s" % (fam, ref, g["ref_source"], g["date"], len(claims), g["claims_total"], g["expected_total"]))
    rm = {"id": "G%s" % ref, "family": fam, "claims": claims, "check_number": ref + g.get("trn_suffix", ""), "date": g["date"], "method": "check"}   # trn_suffix: a new TRN for a re-filed group, posted under the clean check number
    chk, trace, fn, total = upload_group(rm, ctrl, a.dry)
    if a.dry:
        L("   built %s ($%.2f) - dry run, no upload" % (os.path.basename(fn), total))
        for c in claims: L("      %s %s $%.2f lines=%s" % (c["acct"], (c.get("patient") or "")[:22], c["paid"], [(l.get("cpt"), l.get("paid")) for l in c.get("lines") or []]))
        return
    if not chk: rec(status="ERROR", family=fam, ref=ref, acct="*", note="uploaded %s but the check never appeared in the Center" % trace); return
    det = era_post.details(chk["id"]); visits = det.get("eracheckdetails", [])
    L("   check %s %s $%s -> %d claims in details" % (chk["id"], chk.get("paymentnumber"), chk.get("paymentamount"), len(visits)))
    chk2 = dict(chk); chk2["paymentnumber"] = ref; chk2["paymentcode"] = "CHK"
    if not chk2.get("depositdate") and g.get("date"): chk2["depositdate"] = g["date"]
    relines = []   # claims that need a second file with CPT lines
    for v in visits:
        vid = str(v["visitid"]); pid = str(v["patientid"]); claim = next((c for c in claims if c["acct"][:8] == vid), None)
        seq = claim["acct"][8:] if claim else "?"
        errs = "; ".join(e.get("description", "") for e in v.get("errors", []))
        matched = [ch for ch in v.get("charges", []) if int(ch.get("chargedetailid") or -1) > 0 and f(ch.get("paymentamount")) > 0]
        if not matched:
            codes = [ch.get("chargecode") for ch in v.get("charges", [])]
            if claim and v.get("charges") and (not claim.get("lines") or "Procedure codes do not match" in errs):
                relines.append((claim, pid, vid, codes)); L("   %s: %s - AMD shows charges %s; re-filing with AMD's own CPT lines" % (claim["acct"], "no CPT lines on the EOB" if not claim.get("lines") else "EOB CPT differs from the chart", codes)); continue
            rec(status="HOLD", family=fam, ref=ref, acct=claim["acct"] if claim else vid, pid=pid, vid=vid, checkid=chk["id"], paid=claim["paid"] if claim else None, note="no matched money line: %s charges=%s" % (errs or "-", codes)); continue
        carid, insid, pnote = ensure_plan(pid, fam, (claim or {}).get("member"), False)
        if not carid: rec(status="HOLD", family=fam, ref=ref, acct=claim["acct"] if claim else vid, pid=pid, vid=vid, checkid=chk["id"], note=pnote); continue
        chk3 = dict(chk2); chk3["systemcarrierid"] = carid; chk3["systemcarriercode"] = CARCODE[fam]
        live = {c["cid"]: c for c in live_lines(pid, vid)}
        for ch in matched:
            cid = str(ch["chargedetailid"]); lv = live.get(cid)
            if not lv: rec(status="HOLD", family=fam, ref=ref, acct=claim["acct"] if claim else vid, pid=pid, vid=vid, cid=cid, cpt=ch.get("chargecode"), checkid=chk["id"], note="ERA line charge %s not on the live chart" % cid); continue
            if done_key(fam, ref, claim["acct"] if claim else vid, lv["cpt"]): continue
            lp = line_plan(fam, seq, ch, lv, ref)
            base = dict(family=fam, ref=ref, acct=claim["acct"] if claim else vid, pid=pid, vid=vid, cid=cid, cpt=lv["cpt"], dos=lv["dos"], fee=lv["fee"], eob_paid=f(ch.get("paymentamount")), checkid=chk["id"], carrier=CARCODE[fam], plan=pnote)
            if lp["action"] != "POST": rec(status=lp["action"], note=lp["note"], **base); continue
            for w in lp["void_wos"]:
                ok, t = void_tx.void_writeoff(pid, cid, w["id"]); L("   void write-off %s %s $%.2f on %s -> %s %s" % (w["code"], w["id"], w["amount"], cid, ok, t[:80]))
                if not ok: rec(status="ERROR", note="void write-off %s failed: %s" % (w["id"], t[:120]), **base); lp = None; break
            if lp is None: continue
            wo, wocode = (0.0, None) if a.nowo else (lp["wo"], lp["wocode"])
            try:
                ok, payid, head = payreasons.post_line(pid, vid, chk3, v, cid, ch, pay=lp["pay"], wo=wo, wocode=wocode or "WOINS")
            except Exception as e:
                ok, payid, head = False, "", str(e)[:200]
            if ok:
                time.sleep(1); after = {c["cid"]: c for c in live_lines(pid, vid)}.get(cid, {})
                live_pay = next((p for p in after.get("pays", []) if p["void"] != "1" and p["checkno"].split("(")[0] == ref), None)
                rec(status="POSTED", pay=lp["pay"], wo=wo, wocode=wocode, paymentid=payid or (live_pay or {}).get("id"), insbal_after=after.get("insbalance"), reasons=(live_pay or {}).get("reasons"),
                    verified=bool(live_pay and abs(live_pay["amount"] - lp["pay"]) < 0.011), note=lp["note"], **base)
            else:
                rec(status="ERROR", pay=lp["pay"], note="addpayments refused: %s | %s" % (head[:160], lp["note"]), **base)
            time.sleep(0.5)
    if relines:
        rm2 = {"id": "G%sL" % ref, "family": fam, "claims": [], "check_number": ref + "L", "date": g["date"], "method": "check"}
        for claim, pid, vid, codes in relines:
            live = live_lines(pid, vid); active = [c for c in live if c["fee"] > 0]
            if not active: rec(status="HOLD", family=fam, ref=ref, acct=claim["acct"], pid=pid, vid=vid, note="no live charges on the visit"); continue
            c2 = copy.deepcopy(claim); w = [c["fee"] for c in active]
            c2["lines"] = []
            for c, p in zip(active, build835.allocate(claim["paid"], w)):
                prior = any(x["void"] != "1" and x["amount"] > 0 for x in c["pays"])     # another payer already paid this line -> the payer is secondary: OA-23
                rest = round(c["fee"] - p, 2)
                c2["lines"].append({"dos": c["dos"][:10] if "-" in c["dos"] else datetime.datetime.strptime(c["dos"][:10], "%m/%d/%Y").strftime("%Y-%m-%d"), "cpt": c["cpt"], "mod": "", "billed": c["fee"], "allowed": None, "paid": p,
                                    "cas": ([{"group": "OA", "code": "23", "amount": rest}] if prior and rest > 0 else [])})
            c2["billed"] = round(sum(w), 2); rm2["claims"].append(c2)
        if rm2["claims"]:
            g2 = dict(g); g2["claims"] = rm2["claims"]; g2["_relined"] = True
            L("   -- second file with CPT lines for %d claims (TRN %sL, posted as check %s)" % (len(rm2["claims"]), ref, ref))
            chkL, traceL, fnL, totL = upload_group(rm2, ctrl + 500, a.dry)
            if chkL:
                detL = era_post.details(chkL["id"]); chkL2 = dict(chkL); chkL2["paymentnumber"] = ref; chkL2["paymentcode"] = "CHK"
                for v in detL.get("eracheckdetails", []):
                    vid = str(v["visitid"]); pid = str(v["patientid"]); claim = next((c for c in rm2["claims"] if c["acct"][:8] == vid), None); seq = claim["acct"][8:] if claim else "?"
                    matched = [ch for ch in v.get("charges", []) if int(ch.get("chargedetailid") or -1) > 0 and f(ch.get("paymentamount")) > 0]
                    carid, insid, pnote = ensure_plan(pid, fam, (claim or {}).get("member"), False)
                    if not carid or not matched: rec(status="HOLD", family=fam, ref=ref, acct=claim["acct"] if claim else vid, pid=pid, vid=vid, checkid=chkL["id"], note=pnote if not carid else "second file: no matched money line: %s" % "; ".join(e.get("description", "") for e in v.get("errors", []))); continue
                    chk3 = dict(chkL2); chk3["systemcarrierid"] = carid; chk3["systemcarriercode"] = CARCODE[fam]
                    live = {c["cid"]: c for c in live_lines(pid, vid)}
                    for ch in matched:
                        cid = str(ch["chargedetailid"]); lv = live.get(cid)
                        if not lv: continue
                        lp = line_plan(fam, seq, ch, lv, ref)
                        base = dict(family=fam, ref=ref, acct=claim["acct"] if claim else vid, pid=pid, vid=vid, cid=cid, cpt=lv["cpt"], dos=lv["dos"], fee=lv["fee"], eob_paid=f(ch.get("paymentamount")), checkid=chkL["id"], carrier=CARCODE[fam], plan=pnote, relined=True)
                        if lp["action"] != "POST": rec(status=lp["action"], note=lp["note"], **base); continue
                        for w in lp["void_wos"]:
                            ok, t = void_tx.void_writeoff(pid, cid, w["id"]); L("   void write-off %s %s -> %s %s" % (w["code"], w["id"], ok, t[:80]))
                        wo, wocode = (0.0, None) if a.nowo else (lp["wo"], lp["wocode"])
                        try: ok, payid, head = payreasons.post_line(pid, vid, chk3, v, cid, ch, pay=lp["pay"], wo=wo, wocode=wocode or "WOINS")
                        except Exception as e: ok, payid, head = False, "", str(e)[:200]
                        if ok:
                            time.sleep(1); after = {c["cid"]: c for c in live_lines(pid, vid)}.get(cid, {})
                            live_pay = next((p for p in after.get("pays", []) if p["void"] != "1" and p["checkno"].split("(")[0] == ref), None)
                            rec(status="POSTED", pay=lp["pay"], wo=wo, wocode=wocode, paymentid=payid or (live_pay or {}).get("id"), insbal_after=after.get("insbalance"), reasons=(live_pay or {}).get("reasons"), verified=bool(live_pay and abs(live_pay["amount"] - lp["pay"]) < 0.011), note=lp["note"], **base)
                        else: rec(status="ERROR", pay=lp["pay"], note="addpayments refused: %s | %s" % (head[:160], lp["note"]), **base)
                        time.sleep(0.5)
                if not a.keep: L("   dismiss %s -> %s" % (chkL["id"], dismiss(chkL)))
    if not a.keep: L("   dismiss %s -> %s" % (chk["id"], dismiss(chk)))

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--dry", action="store_true"); ap.add_argument("--only", default=""); ap.add_argument("--family", default="")
    ap.add_argument("--max", type=int, default=999); ap.add_argument("--nowo", action="store_true", help="payments only, no write-offs"); ap.add_argument("--keep", action="store_true", help="leave the checks in the Center (no dismiss)")
    a = ap.parse_args()
    P = json.load(open(PLAN)); groups = P["groups"]
    if a.only: groups = [g for g in groups if g["ref"] in a.only.split(",")]
    if a.family: groups = [g for g in groups if g["family"] == a.family]
    if not a.dry: amd.login_cached()
    n = 0
    for i, g in enumerate(groups):
        if n >= a.max: break
        n += 1
        try: process_group(g, a, 100 + i)
        except Exception as e:
            import traceback; traceback.print_exc(); rec(status="ERROR", family=g["family"], ref=g["ref"], acct="*", note="group failed: %s" % str(e)[:200])
    from collections import Counter
    L("REGISTER: %s  posted $%.2f" % (dict(Counter(r["status"] for r in register)), sum(r.get("pay") or 0 for r in register if r["status"] == "POSTED")))
