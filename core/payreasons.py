# PLAIN ENGLISH (Payment reason codes - repair and prevent the 'Payment reason codes are missing or do not balance' hold)
# Decides: which posted insurance payments carry NO reason codes (the manual_post / plain-addpayments hand posts - addpayments
#   without an ERA link silently drops reason codes, proven 9/12 and again 9/21), and re-posts each such ERA line the way the
#   ERA Center's "post manually" does: addpayments postingmethod="era" with eraclaimid/erareportid and the remit's
#   <reasonlist> (William's 9/3/2026 Pinckney capture). That shape KEEPS the CO45/PR2/CO253 reasons on the payment (proven
#   9/21/2026 on 54 visits), so the next payer's claim can be built. Amounts: paid as paid, CO adjustments written off
#   (WOINS / WOLATE CO-29 / WONCS CO-96,204,50), PR amounts left on the visit for the secondary or the patient.
# Rules it uses: void the code-less payment AND the write-off posted with it (same createtime) before re-posting; a $0
#   code-less payment on the visit is voided too (9/12 rule); a visit is released only when every live payment balances
#   (|paid| + reasons == fee); a check whose details are gone (dismissed 9/13) is read through reversedismiss -> details
#   -> dismiss again, or from the era_details/ cache. NEVER the ERA Center Post button for single visits: AMD's engine may
#   then sweep the rest of the check and post every other claim capped at the visit's leftover balance (9/21 lesson).
# Never touches: payments that already carry reasons, charges not on the ERA claim, reversal / $0 denial lines.
# ---
"""Usage (cd /home/claude/unbilled):
  python3 payreasons.py --list                      # the Unbilled reason-code rows and what each visit's payments look like (read-only)
  python3 payreasons.py --unbilled --live [--no-release]   # repair every 'Payment reason codes' Unbilled row, then release the balanced ones
  python3 payreasons.py --visit <visitid> --pid <patientid> [--check <checkid>] --live   # one visit
  python3 payreasons.py --repost-file spec.json --live      # {"visits": [[visitid, pid, checkid], ...]} - re-post voided lines from the cache
  python3 payreasons.py --audit --since-payid 24653500      # every live payment created after that id on the register charts, vs the remit
Library: unbilled_rows(), visit_state(pid, vid), balanced(charges), era_line(vid, charges), era_linked_xml(pid, chk, v, lines),
         post_line(pid, vid, chk, v, cid, ch, pay, wo, wocode), repost_visit(pid, vid, checkid), repair_row(row), release_visit(vid)
"""
import amd, txh, era_post, void_tx, resave, json, os, re, sys, time, glob, datetime, requests
import xml.etree.ElementTree as ET

WS = os.path.dirname(os.path.abspath(__file__))
REGD = os.path.join(WS, "registers"); os.makedirs(REGD, exist_ok=True)
CACHE = os.path.join(WS, "era_details"); os.makedirs(CACHE, exist_ok=True)
_LOG = open(os.path.join(WS, "payreasons.log"), "a")
def L(m):
    print(m, flush=True); _LOG.write("%s %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), m)); _LOG.flush()
def f(v):
    try: return round(float(str(v).replace(",", "") or 0), 2)
    except Exception: return 0.0
def num(s): return re.sub(r"\D", "", str(s or ""))
def stamp(): return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H%MZ")
def esc(x): return (str(x) if x is not None else "").replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")
PAYMETHOD = {"ACH": "9", "NON": "10", "CHK": "11", "FWT": "12", "BOP": "13"}
# checks whose unposted list entry is gone but whose lines we still re-post from the cache (metadata for the ERA link)
KNOWN_CHECKS = {"1051714": {"id": 1051714, "paymentnumber": "819814877(0)", "depositdate": "2026-09-22T00:00:00", "paymentcode": "ACH", "systemcarriercode": "FLO02", "systemcarrierid": 6085},
                "1051715": {"id": 1051715, "paymentnumber": "819814877(1)", "depositdate": "2026-09-22T00:00:00", "paymentcode": "ACH", "systemcarriercode": "FLO02", "systemcarrierid": 6085}}

# ---------------------------------------------------------------- Unbilled rows of this error class
def unbilled_rows(all_rows=False):
    """getclaimunbillablecharges -> rows; reason_row = the visit block carries 'Payment reason codes are missing or do not balance'
    (at the visit level, or under 'One or more charges within this visit have errors')."""
    r = amd.post(amd.msg("getclaimunbillablecharges", "claimsreports", {"lowdate": "", "highdate": "", "carrier": "", "provider": "", "nocookie": "1"}))
    out = []
    for blk in re.findall(r"<visit\b[^>]*>.*?</visit>", r, flags=re.S):
        head = dict(re.findall(r'(\w+)="([^"]*)"', re.match(r"<visit\b[^>]*>", blk).group(0)))
        errs = re.findall(r'<error\b[^>]*\bname="([^"]*)"', blk)
        row = {"visitid": num(head.get("id")), "pid": num(head.get("patientid")), "name": "", "next_carrier": head.get("carriercode", ""),   # 10/6: no patient name in any register (chart id is enough; the registers reach GitHub)
               "errors": " | ".join(dict.fromkeys(e for e in errs if e)), "reason_row": "payment reason codes" in blk.lower(),
               "charges": [dict(re.findall(r'(\w+)="([^"]*)"', c)) for c in re.findall(r"<charge\b[^>]*/>", blk)]}
        if all_rows or row["reason_row"]: out.append(row)
    return out

def release_visit(vid):
    """hideunbillablevisits hide=-1 - the visit id is NUMERIC (vst-prefixed ids fault: 'Conversion failed ... nvarchar')."""
    r = amd.post(amd.msg("hideunbillablevisits", "claimsreports", {"hide": "-1", "nocookie": "1"}, '<visitlist><visit id="%s"/></visitlist>' % num(vid)))
    return ('success="1"' in r and "<Fault" not in r), re.sub(r"\s+", " ", r)[:160]

# ---------------------------------------------------------------- chart state (gettxhistory: amounts are negative credits there)
def visit_state(pid, vid, root=None):
    root = root if root is not None else txh.fetch(pid)
    charges = []
    for c in root.iter("charge"):
        if c.get("void") == "1" or num(c.get("visit")) != str(vid): continue
        pays = [{"id": num(p.get("id")), "amount": abs(f(p.get("amount"))), "checkno": p.get("checknumber") or "", "carrier": p.get("carrier", ""), "date": p.get("date", ""),
                 "createtime": p.get("createtime", ""), "void": p.get("void", ""), "reasons": [(r.get("code", ""), f(r.get("amount"))) for r in p.iter("payreason")]} for p in c.iter("payment")]
        wos = [{"id": num(w.get("id")), "amount": abs(f(w.get("amount"))), "code": w.get("wocode", ""), "date": w.get("date", ""), "createtime": w.get("createtime", ""), "void": w.get("void", "")} for w in c.iter("writeoff")]
        charges.append({"cid": num(c.get("id")), "cpt": c.get("proccode", ""), "dos": c.get("dos", ""), "fee": f(c.get("fee")), "paid": abs(f(c.get("paid"))),
                        "insbalance": f(c.get("insbal")), "patbalance": f(c.get("patbal")), "carrier": c.get("carrier", ""), "pays": pays, "wos": wos})
    return charges

def balanced(charges):
    """AMD's test behind the Unbilled error: every live payment's |paid| + sum(reason amounts) == the charge fee."""
    for c in charges:
        for p in c["pays"]:
            if p["void"] == "1": continue
            if not p["reasons"] or abs(p["amount"] + sum(a for _, a in p["reasons"]) - c["fee"]) >= 0.011: return False
    return True

def codeless(charges):
    return [(c, p) for c in charges for p in c["pays"] if p["void"] != "1" and not p["reasons"]]

# ---------------------------------------------------------------- ERA Center: unposted list, dismissed list, details (+ cache), restore
_CHECKS = None
def checks_index(refresh=False):
    global _CHECKS
    if _CHECKS is None or refresh: _CHECKS = {str(c["id"]): c for c in era_post.checks()}
    return _CHECKS

_DISMISSED = None
def dismissed_index(since="2026-08-01"):
    global _DISMISSED
    if _DISMISSED is None:
        r = requests.get(era_post.API + "/era/checks/dismiss", headers=era_post.H(), params={"DismissedDateBegin": since}, timeout=90)
        _DISMISSED = {str(x["id"]): x for x in (r.json() if r.status_code == 200 else [])}
    return _DISMISSED

RESTORED = set()
def restore(checkid):
    """reversedismiss - the 9/19 recipe: a dismissed check comes back to the unposted list so checkdetails answers again."""
    x = dismissed_index().get(str(checkid))
    if not x: return False, "not in the dismissed list"
    r = requests.post(era_post.API + "/era/checks/reversedismiss", headers=era_post.H(), data=json.dumps([{"id": int(checkid), "dismissedat": x["dismissedat"]}]), timeout=60)
    ok = r.status_code == 200; L("   reversedismiss %s -> HTTP %s %s" % (checkid, r.status_code, r.text[:90]))
    if ok: RESTORED.add(str(checkid)); _DET.pop(str(checkid), None); checks_index(refresh=True); time.sleep(1)
    return ok, r.text[:120]

def redismiss(checkid):
    r = requests.post(era_post.API + "/era/checks/dismiss", headers=era_post.H(), data=json.dumps(str(checkid)), timeout=60)
    ok = r.status_code == 200 and '"issuccess":true' in r.text; L("   dismiss %s again -> HTTP %s %s" % (checkid, r.status_code, r.text[:90]))
    if ok: RESTORED.discard(str(checkid)); checks_index(refresh=True)
    return ok, r.text[:120]

_DET = {}
def details(checkid, fresh=False):
    """Live checkdetails; when AMD returns no claims (check processed or dismissed) the era_details/<id>.json cache is used."""
    checkid = str(checkid)
    if fresh: _DET.pop(checkid, None)
    if checkid not in _DET:
        d = era_post.details(checkid); fn = os.path.join(CACHE, "%s.json" % checkid)
        if d.get("eracheckdetails"): json.dump(d, open(fn, "w"))
        elif os.path.exists(fn): d = json.load(open(fn)); d["_stale_cache"] = True
        _DET[checkid] = d
    return _DET[checkid]

def check_meta(checkid, v=None):
    """The check-level fields the ERA link needs (paymentnumber, depositdate, paymentcode, carrier) from wherever they survive."""
    cid = str(checkid)
    chk = checks_index().get(cid) or KNOWN_CHECKS.get(cid)
    if chk: return chk
    dm = dismissed_index().get(cid, {})
    return {"id": int(cid), "paymentnumber": dm.get("paymentnumber", ""), "depositdate": dm.get("checkoreftdate", ""), "paymentcode": dm.get("paymentcode", "ACH"),
            "systemcarriercode": "", "systemcarrierid": (v or {}).get("carrierid") or ""}

def register_index():
    """visitid -> the fallback register lines that hand-posted it (checkid, checkclaimid, chargeid ...)."""
    idx = {}
    for fn in [os.path.join(REGD, "era_manual_register.json")] + sorted(glob.glob(os.path.join(REGD, "era_fallback_*_live.json"))):
        if not os.path.exists(fn): continue
        try: data = json.load(open(fn))
        except Exception: continue
        for x in (data if isinstance(data, list) else data.get("lines") or []):
            if x.get("outcome") == "posted": idx.setdefault(str(x.get("visitid")), []).append(x)
    return idx

def era_line(vid, charges, allow_restore=True):
    """(checkid, chk, visit-detail) for the ERA claim behind the visit's hand posts: the register first, then the payments'
    check numbers against the unposted and dismissed lists; a dismissed check is restored on demand (and re-dismissed by the caller)."""
    cands = [str(x.get("checkid")) for x in register_index().get(str(vid), [])]
    chknos = {p["checkno"].split("(")[0] for c, p in codeless(charges) if p["checkno"]}
    for src in (checks_index(), dismissed_index()):
        cands += [cid for cid, c in src.items() if str(c.get("paymentnumber", "")).split("(")[0] in chknos]
    seen = set()
    for cid in cands:
        if not cid or cid in seen or cid == "None": continue
        seen.add(cid)
        try: d = details(cid)
        except Exception as e: L("   check %s details: %s" % (cid, e)); continue
        if not d.get("eracheckdetails") and allow_restore and cid in dismissed_index() and cid not in checks_index():
            ok, _ = restore(cid)
            if ok: d = details(cid, fresh=True)
        for v in d.get("eracheckdetails", []):
            if str(v.get("visitid")) == str(vid): return cid, check_meta(cid, v), v
    return None, None, None

# ---------------------------------------------------------------- the ERA-linked Payment Entry shape (carries the reasons)
def line_amounts(ch, bal):
    """pay = the remit's paid (capped at the open balance), wo = the CO/OA/PI adjustments capped so pay+wo <= balance,
    write-off code from the CARC (CO-29 WOLATE, CO-96/204/50 WONCS, else the remit's payreasonwocode or WOINS)."""
    paid = f(ch.get("paymentamount")); pay = min(paid, bal)
    co = 0.0; code = (ch.get("payreasonwocode") or "").strip() or "WOINS"
    for a in ch.get("carc", []):
        if str(a.get("payreasongroup")).upper() in ("CO", "OA", "PI"):
            co += f(a.get("reasonamt")); rc = re.sub(r"\D", "", str(a.get("reasoncode") or ""))
            if rc == "29": code = "WOLATE"
            elif rc in ("96", "204", "50"): code = "WONCS"
    wo = max(0.0, min(round(co, 2), round(bal - pay, 2)))
    return round(pay, 2), round(wo, 2), code, round(paid - pay, 2)

def era_linked_xml(pid, chk, v, lines):
    """lines = [(cid, era charge dict, pay, wo, wocode)] -> the addpayments message the ERA Center's manual post sends."""
    charges = ""; applied = 0.0; wo_total = 0.0; prof = "prof%s" % v["profileid"]
    for cid, ch, pay, wo, wocode in lines:
        rt = ET.fromstring(resave.detail(cid)); c = [x for x in rt.iter("charge") if x.get("id") == "charge" + str(cid)][0]
        bal = f(c.get("insbalance")); allowed = f(ch.get("allowedamount"))
        if pay + wo > bal + 0.005: raise RuntimeError("over-apply on charge %s: pay %.2f + wo %.2f > insbalance %.2f" % (cid, pay, wo, bal))
        reasons = "".join('<reason id="%s" reasonid="%s" code="%s" name="%s" amount="%s" units="0" group="%s"/>'
                          % (r["reportreasondetailid"], r["payreasonid"], r["reasoncode"], esc(r["reasontext"]), r["reasonamt"], r["payreasongroup"]) for r in ch.get("carc", []))
        first = ch["carc"][0]["reasoncode"] if ch.get("carc") else ""
        charges += ('<charge id="charge%s" allowed="%.2f" insportion="%s" patportion="%s" insbalance="%.2f" patbalance="%s" profile="%s">'
                    '<paymentlist><payment amount="%.2f" id="" reason="%s" status="B"><reasonlist payment="%.2f" allowed="%.2f">%s</reasonlist></payment></paymentlist>'
                    '<writeofflist>%s</writeofflist></charge>'
                    % (cid, allowed, c.get("insportion") or "%.2f" % bal, c.get("patportion") or "0.00", bal, c.get("patbalance") or "0.00", prof,
                       pay, first, pay, allowed, reasons, ('<writeoff id="" risk="0" amount="%.2f" code="%s" status="B"/>' % (wo, wocode)) if wo > 0 else ""))
        applied += pay; wo_total += wo
    dd = str(chk.get("depositdate") or "")[:10]; dd = "%s/%s/%s" % (dd[5:7], dd[8:10], dd[:4]) if "-" in dd else (dd or time.strftime("%m/%d/%Y"))
    carid = chk.get("systemcarrierid") or v.get("carrierid")
    return ('<ppmdmsg action="addpayments" class="paymententry" msgtime="%s" useopenedge="1" checkout="0" date="" nocookie="1">'
            '<patient patientid="pat%s" paysource="2" postingmethod="era" amount="%.2f" paycode="PE" woamount="%.2f" paymethod="%s" carrierid="car%s" '
            'depositdate="%s" eraclaimid="%s" erareportid="%s" case_note="" checknumber="%s" inclstmt="0" postedby="POI0712" batch="">'
            '<unappliedpaymentlist/><unappliedwriteofflist/><chargelist>%s</chargelist></patient></ppmdmsg>'
            % (amd._msgtime(), num(pid), applied, wo_total, PAYMETHOD.get(chk.get("paymentcode"), "9"), num(carid), dd,
               v["checkclaimid"], chk["id"], str(chk.get("paymentnumber", "")), charges)), applied, wo_total

def post_line(pid, vid, chk, v, cid, ch, pay=None, wo=None, wocode=None):
    """Post ONE ERA line (with its reasons) onto charge cid. Returns (ok, paymentid, response head)."""
    if pay is None:
        rt = ET.fromstring(resave.detail(cid)); c = [x for x in rt.iter("charge") if x.get("id") == "charge" + str(cid)][0]
        pay, wo, wocode, _ = line_amounts(ch, f(c.get("insbalance")))
    xml, applied, wot = era_linked_xml(pid, chk, v, [(str(cid), ch, pay, wo, wocode or "WOINS")])
    r = amd.post(xml); ok = 'success="1"' in r and "<Fault" not in r
    m = re.search(r'paymentid="(\d+)"', r)
    return ok, (m.group(1) if m else ""), re.sub(r"\s+", " ", r)[:200]

# ---------------------------------------------------------------- repair
def repost_visit(pid, vid, checkid, release=True):
    """Every ERA money line of the visit that has no live matching payment with reasons is re-posted through the ERA-linked shape."""
    d = details(checkid); vd = [v for v in d.get("eracheckdetails", []) if str(v["visitid"]) == str(vid)]
    rec = {"visitid": str(vid), "pid": str(pid), "checkid": str(checkid), "steps": []}
    if not vd: rec["outcome"] = "no-era-line"; return rec
    v = vd[0]; chk = check_meta(checkid, v); st = visit_state(pid, vid); lines = []
    for ch in v.get("charges", []):
        cid = str(ch.get("chargedetailid")); paid = f(ch.get("paymentamount"))
        if int(ch.get("chargedetailid") or -1) <= 0 or paid <= 0: continue
        live = [p for c in st if c["cid"] == cid for p in c["pays"] if p["void"] != "1" and abs(p["amount"] - paid) < 0.011 and p["reasons"]]
        hand = [p for c in st if c["cid"] == cid for p in c["pays"] if p["void"] != "1" and p["amount"] > 0 and not p["reasons"]]
        if hand: rec["outcome"] = "hand-post-still-live"; rec["hand"] = [(cid, p["id"], p["amount"]) for p in hand]; return rec
        if live: continue
        bal = [c for c in st if c["cid"] == cid][0]["insbalance"]
        pay, wo, code, resid = line_amounts(ch, bal)
        if pay <= 0: rec["steps"].append(("skip", cid, "no open balance", bal)); continue
        lines.append((cid, ch, pay, wo, code))
    if not lines: rec["outcome"] = "already-posted"; return rec
    xml, applied, wot = era_linked_xml(pid, chk, v, lines)
    r = amd.post(xml); ok = 'success="1"' in r and "<Fault" not in r
    rec["steps"].append(("addpayments-era", [(cid, ch.get("chargecode"), pay, wo, code) for cid, ch, pay, wo, code in lines], applied, wot, ok, re.sub(r"\s+", " ", r)[:160]))
    L("== REPOST visit %s pat%s: %d line(s) pay %.2f wo %.2f -> %s %s" % (vid, pid, len(lines), applied, wot, ok, re.sub(r"\s+", " ", r)[:100]))
    time.sleep(1.2)
    after = visit_state(pid, vid); rec["after"] = after
    good = ok and balanced(after) and all(any(p["void"] != "1" and abs(p["amount"] - pay) < 0.011 and p["reasons"] for c in after if c["cid"] == cid for p in c["pays"]) for cid, ch, pay, wo, code in lines)
    L("   after: %s" % json.dumps([(c["cid"], c["fee"], c["insbalance"], [(p["id"], p["amount"], p["reasons"]) for p in c["pays"] if p["void"] != "1"]) for c in after]))
    rec["outcome"] = "repaired" if good else ("posted-unverified" if ok else "post-failed")
    if good and release:
        rok, msg = release_visit(vid); rec["steps"].append(("release", rok, msg)); L("   release -> %s" % rok)
    return rec

def repair_row(row, live=False, release=True, keep_restored=False):
    """One Unbilled reason-code row: void the code-less payments (+ the write-off posted with each, + $0 code-less lines),
    then repost_visit from the remit. Dry (live=False) only plans."""
    pid, vid = row["pid"], row["visitid"]
    st = visit_state(pid, vid); cl = codeless(st)
    checkid, chk, v = era_line(vid, st, allow_restore=live)
    rec = {"visitid": vid, "pid": pid, "name": "", "next_carrier": row.get("next_carrier", ""), "checkid": checkid,
           "codeless": [(c["cid"], p["id"], p["amount"], p["checkno"]) for c, p in cl], "steps": []}
    wos = [(c["cid"], w["id"], w["amount"], w["code"]) for c, p in cl for w in c["wos"] if w["void"] != "1" and w["createtime"][:19] == p["createtime"][:19]]
    rec["wos_to_void"] = wos
    L("== visit %s pat%s -> %s: code-less %s; write-offs %s; check %s" % (vid, pid, rec["next_carrier"], rec["codeless"], wos, checkid))
    if balanced(st) and not cl: rec["outcome"] = "already-balanced"
    elif not v: rec["outcome"] = "no-era-line"
    else:
        chkno = str(chk.get("paymentnumber") or "").split("(")[0]
        if [1 for c, p in cl if p["checkno"] and chkno and p["checkno"].split("(")[0] != chkno]: rec["outcome"] = "mixed-checks"
        elif not live: rec["outcome"] = "would-repair"
        else:
            for c, p in cl:
                ok, msg = void_tx.void_payment(pid, c["cid"], p["id"]); rec["steps"].append(("void_payment", c["cid"], p["id"], p["amount"], ok)); L("   void payment %s $%.2f on %s -> %s" % (p["id"], p["amount"], c["cid"], ok))
                if not ok: rec["outcome"] = "void-failed"; break
                time.sleep(0.4)
            else:
                for cid, woid, amt, code in wos:
                    ok, msg = void_tx.void_writeoff(pid, cid, woid); rec["steps"].append(("void_writeoff", cid, woid, amt, code, ok)); L("   void write-off %s $%.2f %s on %s -> %s" % (woid, amt, code, cid, ok))
                    if not ok: rec["outcome"] = "void-wo-failed"; break
                    time.sleep(0.4)
                else:
                    sub = repost_visit(pid, vid, checkid, release=release); rec["steps"] += sub.get("steps", []); rec["after"] = sub.get("after"); rec["outcome"] = sub["outcome"]
    if rec["outcome"] == "already-balanced" and live and release and row.get("reason_row"):
        rok, msg = release_visit(vid); rec["steps"].append(("release", rok, msg))
    if checkid in RESTORED and not keep_restored: redismiss(checkid)
    return rec

def audit(since_payid, pids=None):
    """Every live payment with id > since_payid on the given charts vs the remit line (cache) - the 9/21 sweep check."""
    vis = {}
    for fn in glob.glob(os.path.join(CACHE, "*.json")):
        try: d = json.load(open(fn))
        except Exception: continue
        for v in d.get("eracheckdetails", []): vis.setdefault(str(v["visitid"]), (os.path.basename(fn)[:-5], str(v["patientid"]), v))
    pids = pids or sorted({p for _, p, _ in vis.values()}); out = []
    for pid in pids:
        root = txh.fetch(pid)
        for c in root.iter("charge"):
            if c.get("void") == "1": continue
            for p in c.iter("payment"):
                if p.get("void") == "1" or int(num(p.get("id")) or 0) <= since_payid: continue
                v = vis.get(c.get("visit")); era = [ch for ch in v[2].get("charges", []) if str(ch.get("chargedetailid")) == c.get("id")] if v else []
                paid = f(era[0]["paymentamount"]) if era else None; amt = abs(f(p.get("amount")))
                out.append({"pid": pid, "visit": c.get("visit"), "cid": c.get("id"), "payid": p.get("id"), "amount": amt, "remit_paid": paid,
                            "reasons": [(r.get("code"), r.get("amount")) for r in p.iter("payreason")], "verdict": "ok" if paid is not None and abs(amt - paid) < 0.011 else ("no-remit-line" if paid is None else "MISMATCH")})
        time.sleep(0.25)
    return out

# ---------------------------------------------------------------- CLI
if __name__ == "__main__":
    a = sys.argv[1:]
    def opt(name, default=None): return a[a.index(name) + 1] if name in a and a.index(name) + 1 < len(a) else default
    live = "--live" in a; release = "--no-release" not in a
    amd.login_cached()
    reg = {"stamp": stamp(), "mode": "live" if live else "dry", "results": []}
    if "--audit" in a:
        reg["results"] = audit(int(opt("--since-payid", "0")), [opt("--pid")] if opt("--pid") else None)
        from collections import Counter; L("audit: %s" % dict(Counter(x["verdict"] for x in reg["results"])))
        for x in reg["results"]:
            if x["verdict"] != "ok": L("   %s" % json.dumps(x))
    elif "--repost-file" in a:
        spec = json.load(open(opt("--repost-file")))
        for vid, pid, checkid in spec["visits"]:
            try: rec = repost_visit(str(pid), str(vid), str(checkid), release=release) if live else {"visitid": vid, "outcome": "dry"}
            except Exception as e: rec = {"visitid": vid, "pid": pid, "outcome": "error", "error": str(e)[:300]}; L("   ERROR %s %s" % (vid, e))
            reg["results"].append(rec); time.sleep(0.8)
    elif "--visit" in a:
        row = {"visitid": opt("--visit"), "pid": opt("--pid"), "name": "", "reason_row": True}
        reg["results"].append(repair_row(row, live=live, release=release))
    else:
        rows = unbilled_rows(); L("Unbilled 'Payment reason codes' rows: %d" % len(rows))
        for row in rows:
            try: rec = repair_row(row, live=live and "--unbilled" in a, release=release, keep_restored=True)
            except Exception as e: rec = {"visitid": row["visitid"], "pid": row["pid"], "outcome": "error", "error": str(e)[:300]}; L("   ERROR %s %s" % (row["visitid"], e))
            reg["results"].append(rec)
            json.dump(reg, open(os.path.join(REGD, "payreason_repair_%s.json" % reg["stamp"]), "w"), indent=1, default=str); time.sleep(0.5)
        for cid in list(RESTORED): redismiss(cid)
    json.dump(reg, open(os.path.join(REGD, "payreason_repair_%s.json" % reg["stamp"]), "w"), indent=1, default=str)
    from collections import Counter
    L("SUMMARY: %s" % dict(Counter(x.get("outcome", x.get("verdict", "?")) for x in reg["results"])))
