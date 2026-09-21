# PLAIN ENGLISH (Probe + repair: give the hand-posted primaries their remit reason codes, William 9/21/2026 'probe one line now, then all 54')
# Decides: for an Unbilled 'Payment reason codes are missing or do not balance' visit: which of its payments were hand-posted
#   without CARCs (manual_post fallback), which ERA check/line they came from, and re-posts that ERA line the way the ERA
#   Center's Post button does (posterapayments carries the remit's CO/PR reasons) after voiding the code-less payment and its
#   write-off. Reads the chart back (gettxhistory) and only calls a visit repaired when every payment balances to the fee.
# Rules it uses: ONE visit per --go; nothing is voided unless the ERA line for it is in hand; never releases an unbalanced visit.
# Never touches: visits whose payments already carry reasons; charges not on the ERA claim.
# ---
"""Usage (cd /home/claude/unbilled):
  python3 reasons_probe.py --list                  # the Unbilled reason-code rows + what each visit's payments look like
  python3 reasons_probe.py --plan <visitid>        # what --go would do (no writes)
  python3 reasons_probe.py --go <visitid>          # void + ERA-post + verify (+ release when balanced)
  python3 reasons_probe.py --go-all [--limit N]    # every row in --list order, skipping visits without an ERA line
"""
import amd, txh, era_post, void_tx, json, os, re, sys, time, glob, datetime, requests
import xml.etree.ElementTree as ET

WS = os.path.dirname(os.path.abspath(__file__))
REGD = os.path.join(WS, "registers"); os.makedirs(REGD, exist_ok=True)
LOGF = open(os.path.join(WS, "reasons_probe.log"), "a")
def L(m):
    print(m, flush=True); LOGF.write("%s %s\n" % (time.strftime("%H:%M:%SZ", time.gmtime()), m)); LOGF.flush()
def f(v):
    try: return round(float(str(v).replace(",", "") or 0), 2)
    except Exception: return 0.0
def stamp(): return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H%MZ")
def num(s): return re.sub(r"\D", "", str(s or ""))

# ---------------------------------------------------------------- Unbilled rows
def unbilled_rows():
    r = amd.post(amd.msg("getclaimunbillablecharges", "claimsreports", {"lowdate": "", "highdate": "", "carrier": "", "provider": "", "nocookie": "1"}))
    open(os.path.join(WS, "unbilled_raw_%s.xml" % stamp()), "w").write(r)
    out = []
    for blk in re.findall(r"<visit\b[^>]*>.*?</visit>", r, flags=re.S):
        head = dict(re.findall(r'(\w+)="([^"]*)"', re.match(r"<visit\b[^>]*>", blk).group(0)))
        errs = re.findall(r'<error\b[^>]*\bname="([^"]*)"', blk)
        txt = " | ".join(dict.fromkeys(e for e in errs if e))
        pid = num(head.get("patientid") or head.get("patient") or "")
        if not pid:
            m = re.search(r'patientid="([^"]*)"|<patient\b[^>]*\bid="([^"]*)"', blk); pid = num((m.group(1) or m.group(2)) if m else "")
        out.append({"visitid": num(head.get("id")), "pid": pid, "name": head.get("patientname") or head.get("name", ""), "dos": head.get("dos") or head.get("dateofservice", ""),
                    "errors": txt, "reason_row": "payment reason codes" in blk.lower(), "next_carrier": head.get("carriercode", ""),
                    "charges": [dict(re.findall(r'(\w+)="([^"]*)"', c)) for c in re.findall(r"<charge\b[^>]*/>", blk)]})
    return out

# ---------------------------------------------------------------- chart state
def visit_state(pid, vid, root=None):
    root = root if root is not None else txh.fetch(pid)
    charges = []
    for c in root.iter("charge"):
        if c.get("void") == "1" or num(c.get("visit") or c.get("visitid")) != str(vid): continue
        pays = []; wos = []
        for p in c.iter("payment"):
            pays.append({"id": num(p.get("id")), "amount": abs(f(p.get("amount"))), "checkno": (p.get("checknumber") or ""), "carrier": p.get("carrier", ""),
                         "date": p.get("date", ""), "createtime": p.get("createtime", ""), "void": p.get("void", ""),
                         "reasons": [(r.get("code", ""), f(r.get("amount"))) for r in p.iter("payreason")]})
        for w in c.iter("writeoff"):
            wos.append({"id": num(w.get("id")), "amount": abs(f(w.get("amount"))), "code": w.get("wocode") or w.get("code", ""), "date": w.get("date", ""),
                        "createtime": w.get("createtime", ""), "void": w.get("void", ""), "source": w.get("source", "")})
        charges.append({"cid": num(c.get("id")), "cpt": c.get("proccode", ""), "dos": c.get("dos") or c.get("dateofservice", ""), "fee": f(c.get("fee")),
                        "paid": abs(f(c.get("paid"))), "insbalance": f(c.get("insbal")), "patbalance": f(c.get("patbal")), "carrier": c.get("carrier", ""), "pays": pays, "wos": wos})
    return charges

def balanced(charges):
    for c in charges:
        for p in c["pays"]:
            if p["void"] == "1": continue
            if not p["reasons"] or abs(p["amount"] + sum(a for _, a in p["reasons"]) - c["fee"]) >= 0.011: return False
    return True

# ---------------------------------------------------------------- the ERA line behind a hand post
def register_index():
    idx = {}
    for fn in [os.path.join(WS, "era_manual_register.json")] + sorted(glob.glob(os.path.join(WS, "era_fallback_*_live.json"))) + \
              [os.path.join(WS, "registers", "era_manual_register.json")] + sorted(glob.glob(os.path.join(WS, "registers", "era_fallback_*_live.json"))):
        if not os.path.exists(fn): continue
        try: data = json.load(open(fn))
        except Exception: continue
        for x in (data if isinstance(data, list) else data.get("lines") or []):
            if x.get("outcome") != "posted": continue
            idx.setdefault(str(x.get("visitid")), []).append(x)
    return idx

_CHECKS = None
def checks_index(refresh=False):
    global _CHECKS
    if _CHECKS is None or refresh:
        _CHECKS = {str(c["id"]): c for c in era_post.checks()}
    return _CHECKS

_DISMISSED = None
def dismissed_index():
    """Every check dismissed since 8/1/2026 (the 9/13 fallback dismissed its checks after hand-posting) -> restorable."""
    global _DISMISSED
    if _DISMISSED is None:
        r = requests.get(era_post.API + "/era/checks/dismiss", headers=era_post.H(), params={"DismissedDateBegin": "2026-08-01"}, timeout=90)
        _DISMISSED = {str(x["id"]): x for x in (r.json() if r.status_code == 200 else [])}
        L("dismissed list: %d checks" % len(_DISMISSED))
    return _DISMISSED

RESTORED = set()
def restore(checkid):
    """The 9/19 recipe: reversedismiss puts a dismissed check back on the unposted list (details + Post work again)."""
    x = dismissed_index().get(str(checkid))
    if not x: return False, "not in the dismissed list"
    r = requests.post(era_post.API + "/era/checks/reversedismiss", headers=era_post.H(), data=json.dumps([{"id": int(checkid), "dismissedat": x["dismissedat"]}]), timeout=60)
    ok = r.status_code == 200
    L("   reversedismiss %s -> HTTP %s %s" % (checkid, r.status_code, r.text[:100]))
    if ok:
        RESTORED.add(str(checkid)); _DET.pop(str(checkid), None); checks_index(refresh=True); time.sleep(1)
    return ok, r.text[:120]

def redismiss(checkid):
    r = requests.post(era_post.API + "/era/checks/dismiss", headers=era_post.H(), data=json.dumps(str(checkid)), timeout=60)
    ok = r.status_code == 200 and '"issuccess":true' in r.text
    L("   dismiss %s again -> HTTP %s %s" % (checkid, r.status_code, r.text[:100]))
    if ok: RESTORED.discard(str(checkid)); checks_index(refresh=True)
    return ok, r.text[:120]

_DET = {}
def details(checkid, fresh=False):
    """Live check details; when AMD returns no claims (check processed/dismissed) fall back to the disk cache written earlier."""
    checkid = str(checkid)
    if fresh: _DET.pop(checkid, None)
    if checkid not in _DET:
        d = era_post.details(checkid); fn = os.path.join(WS, "era_details", "%s.json" % checkid)
        if d.get("eracheckdetails"):
            os.makedirs(os.path.dirname(fn), exist_ok=True); json.dump(d, open(fn, "w"))
        elif os.path.exists(fn):
            d = json.load(open(fn)); d["_stale_cache"] = True
        _DET[checkid] = d
    return _DET[checkid]

KNOWN_CHECKS = {"1051714": {"id": 1051714, "paymentnumber": "819814877(0)", "depositdate": "2026-09-22T00:00:00", "paymentcode": "ACH", "systemcarriercode": "FLO02", "systemcarrierid": 6085},
                "1051715": {"id": 1051715, "paymentnumber": "819814877(1)", "depositdate": "2026-09-22T00:00:00", "paymentcode": "ACH", "systemcarriercode": "FLO02", "systemcarrierid": 6085}}

def era_line(vid, charges, allow_restore=True):
    """(checkid, chk, visit-detail, listed) for the ERA claim behind this visit's hand posts: the register first, then the
    code-less payments' check numbers against the unposted and dismissed lists. A dismissed check is restored on demand."""
    cands = []
    for x in register_index().get(str(vid), []): cands.append(str(x.get("checkid")))
    chknos = {p["checkno"].split("(")[0] for c in charges for p in c["pays"] if p["void"] != "1" and not p["reasons"] and p["checkno"]}
    for cid, c in checks_index().items():
        if str(c.get("paymentnumber", "")).split("(")[0] in chknos: cands.append(cid)
    for cid, c in dismissed_index().items():
        if str(c.get("paymentnumber", "")).split("(")[0] in chknos: cands.append(cid)
    seen = set()
    for cid in cands:
        if cid in seen or not cid or cid == "None": continue
        seen.add(cid)
        try: d = details(cid)
        except Exception as e: L("   check %s details: %s" % (cid, e)); continue
        if not d.get("eracheckdetails") and cid in dismissed_index() and cid not in checks_index():
            if not allow_restore: continue
            ok, _ = restore(cid)
            if not ok: continue
            d = details(cid, fresh=True)
        for v in d.get("eracheckdetails", []):
            if str(v.get("visitid")) == str(vid):
                chk = checks_index().get(cid) or KNOWN_CHECKS.get(cid)
                if not chk:
                    dm = dismissed_index().get(cid, {})
                    chk = {"id": int(cid), "paymentnumber": dm.get("paymentnumber", ""), "depositdate": dm.get("checkoreftdate", ""), "paymentcode": dm.get("paymentcode", "ACH"),
                           "systemcarriercode": "", "systemcarrierid": "", "unpostedamount": 0, "paymentamount": dm.get("checkoreftamount", 0)}
                return cid, chk, v, cid in checks_index()
    return None, None, None, False

# ---------------------------------------------------------------- plan / go
def plan(row, allow_restore=False):
    pid, vid = row["pid"], row["visitid"]
    charges = visit_state(pid, vid)
    codeless = [(c, p) for c in charges for p in c["pays"] if p["void"] != "1" and not p["reasons"]]
    checkid, chk, v, listed = era_line(vid, charges, allow_restore=allow_restore)
    out = {"pid": pid, "visitid": vid, "name": row.get("name", ""), "charges": charges, "codeless": [(c["cid"], p["id"], p["amount"], p["checkno"]) for c, p in codeless],
           "checkid": checkid, "check_listed": listed, "era_visit": None if not v else {"paid": v.get("paymentamount"), "processok": v.get("processok"), "errors": v.get("errors"),
           "claimstatus": v.get("claimstatus"), "insbal": v.get("insurancebalance"),
           "lines": [{"cid": ch.get("chargedetailid"), "cpt": ch.get("chargecode"), "dos": str(ch.get("dos", ""))[:10], "paid": ch.get("paymentamount"), "adj": ch.get("adjustmentamount"),
                      "carc": [(x.get("payreasongroup"), x.get("reasoncode"), x.get("reasonamt")) for x in ch.get("carc", [])]} for ch in v.get("charges", [])]}}
    # the write-offs that came with the hand posts (same day, same charge)
    out["wos_to_void"] = []
    for c, p in codeless:
        for w in c["wos"]:
            if w["void"] != "1" and w["createtime"][:19] == p["createtime"][:19]: out["wos_to_void"].append((c["cid"], w["id"], w["amount"], w["code"]))
    out["already_balanced"] = balanced(charges)
    out["check_dismissed"] = bool(checkid) and checkid in dismissed_index() and not listed
    if not checkid:
        # which check numbers the code-less payments carry, and whether they are known at all
        out["checknos"] = sorted({p["checkno"] for c, p in codeless})
    return out

def go(row, release=True, dry=False, keep_restored=False):
    pl = plan(row, allow_restore=not dry); vid = row["visitid"]; pid = row["pid"]
    L("== visit %s pat%s %s: %d code-less payment(s) %s; write-offs %s; check %s listed=%s; era %s" % (
        vid, pid, pl["name"], len(pl["codeless"]), pl["codeless"], pl["wos_to_void"], pl["checkid"], pl["check_listed"], json.dumps(pl["era_visit"])[:600]))
    rec = {"visitid": vid, "pid": pid, "plan": {k: v for k, v in pl.items() if k != "charges"}, "steps": []}
    if pl["already_balanced"]:
        rec["outcome"] = "already-balanced"; L("   already balanced - release only")
        if release and not dry:
            ok, msg = release_visit(vid); rec["steps"].append(("release", ok, msg))
        return rec
    if not pl["codeless"]:
        rec["outcome"] = "no-codeless-payment"; L("   no code-less payment - not a hand-post case; leave for review"); return rec
    if not pl["era_visit"]:
        rec["outcome"] = "no-era-line"; L("   no ERA line found for this visit - skip"); return rec
    v = pl["era_visit"]
    if not v["processok"] or v["errors"]:
        rec["outcome"] = "era-visit-not-postable"; L("   ERA visit not postable (processok=%s errors=%s) - needs the manual ERA-linked shape; skip for now" % (v["processok"], v["errors"])); return rec
    if dry:
        rec["outcome"] = "dry"; return rec
    # guard: every code-less payment on the visit must come from THIS check (a second check's money would be voided and never re-posted)
    chk0 = checks_index().get(pl["checkid"]) or {}
    chkno = str(chk0.get("paymentnumber") or dismissed_index().get(pl["checkid"], {}).get("paymentnumber") or "").split("(")[0]
    other = [x for x in pl["codeless"] if x[3] and chkno and x[3].split("(")[0] != chkno]
    if other:
        rec["outcome"] = "mixed-checks"; L("   code-less payments from another check %s - skip (manual review)" % other); return rec
    # 1) void the code-less payments and their write-offs
    for cid, payid, amt, chkno in pl["codeless"]:
        ok, msg = void_tx.void_payment(pid, cid, payid); rec["steps"].append(("void_payment", cid, payid, amt, ok, msg)); L("   void payment %s $%.2f on %s -> %s %s" % (payid, amt, cid, ok, msg))
        if not ok: rec["outcome"] = "void-failed"; return rec
        time.sleep(0.5)
    for cid, woid, amt, code in pl["wos_to_void"]:
        ok, msg = void_tx.void_writeoff(pid, cid, woid); rec["steps"].append(("void_writeoff", cid, woid, amt, code, ok, msg)); L("   void write-off %s $%.2f %s on %s -> %s %s" % (woid, amt, code, cid, ok, msg))
        if not ok: rec["outcome"] = "void-wo-failed"; return rec
        time.sleep(0.5)
    # 2) post the ERA line for this visit only, the Post-button way (carries the remit's CO/PR reasons)
    checkid = pl["checkid"]; chk = checks_index().get(checkid) or era_line(vid, visit_state(pid, vid))[1]
    era_post.FORCE_VISITS.clear(); era_post.FORCE_VISITS.add(int(vid))
    n, total = era_post.post_check(chk)
    rec["steps"].append(("posterapayments", checkid, n, total)); L("   ERA post -> %d visit(s) $%.2f" % (n, total))
    time.sleep(1.2)
    # 3) verify
    after = visit_state(pid, vid); rec["after"] = after
    ok = balanced(after) and any(p["reasons"] for c in after for p in c["pays"] if p["void"] != "1")
    L("   after: %s" % json.dumps([(c["cid"], c["fee"], c["insbalance"], c["patbalance"], [(p["id"], p["amount"], p["reasons"], p["void"]) for p in c["pays"]]) for c in after]))
    rec["outcome"] = "repaired" if ok else "posted-unbalanced"
    if ok and release:
        rok, msg = release_visit(vid); rec["steps"].append(("release", rok, msg)); L("   release -> %s %s" % (rok, msg))
    if pl["checkid"] in RESTORED and not keep_restored:
        dok, msg = redismiss(pl["checkid"]); rec["steps"].append(("redismiss", pl["checkid"], dok, msg))
    return rec

def esc(x): return (str(x) if x is not None else "").replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")
PAYMETHOD = {"ACH": "9", "NON": "10", "CHK": "11", "FWT": "12", "BOP": "13"}

def manual_era_xml(pid, vid, chk, v, targets):
    """The UI's 'post manually' shape for an ERA line the Post button refuses ('Procedure codes do not match'): addpayments
    postingmethod=era with eraclaimid/erareportid and the remit's reasonlist (William's 9/3 Pinckney capture, era_manual_post.build),
    amounts per line = paid as paid, CO adjustments written off, PR left on the visit for the next payer.
    targets = [(cid, era charge dict)]."""
    import resave
    charges = ""; applied = 0.0; wo_total = 0.0; prof = "prof%s" % v["profileid"]
    for cid, ch in targets:
        rt = ET.fromstring(resave.detail(cid)); c = [x for x in rt.iter("charge") if x.get("id") == "charge" + str(cid)][0]
        bal = f(c.get("insbalance")); pay = f(ch.get("paymentamount")); allowed = f(ch.get("allowedamount"))
        co = round(sum(f(r.get("reasonamt")) for r in ch.get("carc", []) if str(r.get("payreasongroup")) in ("CO", "OA", "PI")), 2)
        wo = min(co, round(bal - pay, 2))
        if pay + wo > bal + 0.005: raise RuntimeError("over-apply on %s: pay %.2f + wo %.2f > bal %.2f" % (cid, pay, wo, bal))
        reasons = "".join('<reason id="%s" reasonid="%s" code="%s" name="%s" amount="%s" units="0" group="%s"/>'
                          % (r["reportreasondetailid"], r["payreasonid"], r["reasoncode"], esc(r["reasontext"]), r["reasonamt"], r["payreasongroup"]) for r in ch.get("carc", []))
        first = ch["carc"][0]["reasoncode"] if ch.get("carc") else ""
        wocode = (ch.get("payreasonwocode") or "WOINS").strip() or "WOINS"
        charges += ('<charge id="charge%s" allowed="%.2f" insportion="%s" patportion="%s" insbalance="%.2f" patbalance="%s" profile="%s">'
                    '<paymentlist><payment amount="%.2f" id="" reason="%s" status="B"><reasonlist payment="%.2f" allowed="%.2f">%s</reasonlist></payment></paymentlist>'
                    '<writeofflist>%s</writeofflist></charge>'
                    % (cid, allowed, c.get("insportion") or "%.2f" % bal, c.get("patportion") or "0.00", bal, c.get("patbalance") or "0.00", prof,
                       pay, first, pay, allowed, reasons, ('<writeoff id="" risk="0" amount="%.2f" code="%s" status="B"/>' % (wo, wocode)) if wo > 0 else ""))
        applied += pay; wo_total += wo
    dd = str(chk.get("depositdate") or "")[:10]; dd = "%s/%s/%s" % (dd[5:7], dd[8:10], dd[:4]) if "-" in dd else time.strftime("%m/%d/%Y")
    carid = chk.get("systemcarrierid") or v.get("carrierid")
    xml = ('<ppmdmsg action="addpayments" class="paymententry" msgtime="%s" useopenedge="1" checkout="0" date="" nocookie="1">'
           '<patient patientid="pat%s" paysource="2" postingmethod="era" amount="%.2f" paycode="PE" woamount="%.2f" paymethod="%s" carrierid="car%s" '
           'depositdate="%s" eraclaimid="%s" erareportid="%s" case_note="" checknumber="%s" inclstmt="0" postedby="POI0712" batch="">'
           '<unappliedpaymentlist/><unappliedwriteofflist/><chargelist>%s</chargelist></patient></ppmdmsg>'
           % (amd._msgtime(), pid, applied, wo_total, PAYMETHOD.get(chk.get("paymentcode"), "9"), carid, dd,
              v["checkclaimid"], chk["id"], str(chk.get("paymentnumber", "")), charges))
    return xml, applied, wo_total

def go_manual(row, release=True, dry=False, keep_restored=False):
    """The 'Procedure codes do not match' rows (Post button refuses): same voids, then the manual ERA-linked post."""
    pl = plan(row, allow_restore=not dry); vid = row["visitid"]; pid = row["pid"]
    L("== MANUAL visit %s pat%s %s: code-less %s; write-offs %s; check %s listed=%s" % (vid, pid, pl["name"], pl["codeless"], pl["wos_to_void"], pl["checkid"], pl["check_listed"]))
    rec = {"visitid": vid, "pid": pid, "mode": "manual", "plan": {k: v for k, v in pl.items() if k != "charges"}, "steps": []}
    if not pl["era_visit"]: rec["outcome"] = "no-era-line"; return rec
    chk = checks_index().get(pl["checkid"]) or KNOWN_CHECKS.get(pl["checkid"]) or era_line(vid, visit_state(pid, vid))[1] or {}
    chkno = str(chk.get("paymentnumber") or "").split("(")[0]
    if [x for x in pl["codeless"] if x[3] and chkno and x[3].split("(")[0] != chkno]: rec["outcome"] = "mixed-checks"; return rec
    if dry: rec["outcome"] = "dry"; return rec
    for cid, payid, amt, chkno_ in pl["codeless"]:
        ok, msg = void_tx.void_payment(pid, cid, payid); rec["steps"].append(("void_payment", cid, payid, amt, ok, msg)); L("   void payment %s $%.2f on %s -> %s" % (payid, amt, cid, ok))
        if not ok: rec["outcome"] = "void-failed"; return rec
        time.sleep(0.5)
    for cid, woid, amt, code in pl["wos_to_void"]:
        ok, msg = void_tx.void_writeoff(pid, cid, woid); rec["steps"].append(("void_writeoff", cid, woid, amt, code, ok, msg)); L("   void write-off %s $%.2f %s on %s -> %s" % (woid, amt, code, cid, ok))
        if not ok: rec["outcome"] = "void-wo-failed"; return rec
        time.sleep(0.5)
    sub = repost_manual(pid, vid, pl["checkid"], release=release); rec["steps"] += sub.get("steps", []); rec["after"] = sub.get("after"); rec["outcome"] = sub["outcome"]
    if pl["checkid"] in RESTORED and not keep_restored: redismiss(pl["checkid"])
    return rec

def repost_manual(pid, vid, checkid, release=True):
    """After the capped payments were voided: re-post every ERA line of the visit that has money and no live matching
    payment with reasons, through the manual ERA-linked shape (proven 9/21 02:06 AMD time on pat17471365 v19422334)."""
    d = details(checkid); vdet = [v for v in d.get("eracheckdetails", []) if str(v["visitid"]) == str(vid)]
    rec = {"visitid": vid, "pid": pid, "checkid": checkid, "mode": "repost-manual", "steps": []}
    if not vdet: rec["outcome"] = "no-era-line"; return rec
    vdet = vdet[0]; chk = checks_index().get(str(checkid)) or KNOWN_CHECKS.get(str(checkid))
    if not chk:
        dm = dismissed_index().get(str(checkid), {})
        chk = {"id": int(checkid), "paymentnumber": dm.get("paymentnumber", ""), "depositdate": dm.get("checkoreftdate", ""), "paymentcode": dm.get("paymentcode", "ACH"),
               "systemcarriercode": "", "systemcarrierid": vdet.get("carrierid") or ""}
    st = visit_state(pid, vid); targets = []
    for ch in vdet.get("charges", []):
        cid = str(ch.get("chargedetailid")); paid = f(ch.get("paymentamount"))
        if int(ch.get("chargedetailid") or -1) <= 0 or paid <= 0: continue
        live = [p for c in st if c["cid"] == cid for p in c["pays"] if p["void"] != "1" and abs(p["amount"] - paid) < 0.011 and p["reasons"]]
        codeless = [p for c in st if c["cid"] == cid for p in c["pays"] if p["void"] != "1" and p["amount"] > 0 and not p["reasons"]]
        if codeless: rec["outcome"] = "hand-post-still-live"; rec["codeless"] = [(cid, p["id"], p["amount"]) for p in codeless]; return rec
        if not live: targets.append((cid, ch))
    if not targets: rec["outcome"] = "already-posted"; return rec
    xml, applied, wo = manual_era_xml(pid, vid, chk, vdet, targets)
    r = amd.post(xml); ok = 'success="1"' in r and "<Fault" not in r
    rec["steps"].append(("addpayments-era", [(cid, ch.get("chargecode"), ch.get("paymentamount")) for cid, ch in targets], applied, wo, ok, re.sub(r"\s+", " ", r)[:160]))
    L("== REPOST visit %s pat%s: %d line(s) pay %.2f wo %.2f -> %s %s" % (vid, pid, len(targets), applied, wo, ok, re.sub(r"\s+", " ", r)[:120]))
    time.sleep(1.2)
    after = visit_state(pid, vid); rec["after"] = after
    good = ok and balanced(after) and all(any(p["void"] != "1" and abs(p["amount"] - f(ch.get("paymentamount"))) < 0.011 and p["reasons"] for c in after if c["cid"] == cid for p in c["pays"]) for cid, ch in targets)
    L("   after: %s" % json.dumps([(c["cid"], c["fee"], c["insbalance"], [(p["id"], p["amount"], p["reasons"], p["void"]) for p in c["pays"] if p["void"] != "1"]) for c in after]))
    rec["outcome"] = "repaired" if good else ("posted-unverified" if ok else "post-failed")
    if good and release:
        rok, msg = release_visit(vid); rec["steps"].append(("release", rok, msg)); L("   release -> %s" % rok)
    return rec

def release_visit(vid):
    r = amd.post(amd.msg("hideunbillablevisits", "claimsreports", {"hide": "-1", "nocookie": "1"}, '<visitlist><visit id="%s"/></visitlist>' % vid))
    return ('success="1"' in r and "<Fault" not in r), re.sub(r"\s+", " ", r)[:160]

if __name__ == "__main__":
    a = sys.argv[1:]
    amd.login_cached()
    rows = [r for r in unbilled_rows() if r["reason_row"]]
    L("Unbilled reason-code rows: %d" % len(rows))
    reg = {"stamp": stamp(), "rows": rows, "results": []}
    if "--list" in a:
        for r in rows:
            pl = plan(r); r2 = dict(r); r2.update({k: v for k, v in pl.items() if k in ("codeless", "checkid", "check_listed", "already_balanced", "wos_to_void")})
            r2["era"] = None if not pl["era_visit"] else {"processok": pl["era_visit"]["processok"], "errors": pl["era_visit"]["errors"], "lines": pl["era_visit"]["lines"]}
            L(json.dumps(r2)); reg["results"].append(r2); time.sleep(0.3)
    elif "--plan" in a:
        vid = a[a.index("--plan") + 1]; r = [x for x in rows if x["visitid"] == vid][0]
        pl = plan(r); L(json.dumps(pl, indent=1, default=str)); reg["results"].append(pl)
    elif "--go" in a:
        vid = a[a.index("--go") + 1]; r = [x for x in rows if x["visitid"] == vid][0]
        reg["results"].append(go(r, release="--no-release" not in a))
    elif "--repost-file" in a:
        spec = json.load(open(a[a.index("--repost-file") + 1]))   # {"visits": [[vid, pid, checkid], ...]}
        for vid, pid, checkid in spec["visits"]:
            try: rec = repost_manual(str(pid), str(vid), str(checkid), release="--no-release" not in a)
            except Exception as e: rec = {"visitid": vid, "pid": pid, "outcome": "error", "error": str(e)[:300]}; L("   ERROR %s %s" % (vid, e))
            reg["results"].append(rec)
            json.dump(reg, open(os.path.join(REGD, "payreason_repair_%s.json" % reg["stamp"]), "w"), indent=1, default=str)
            time.sleep(0.8)
    elif "--go-manual" in a:
        vid = a[a.index("--go-manual") + 1]; r = [x for x in rows if x["visitid"] == vid][0]
        reg["results"].append(go_manual(r, release="--no-release" not in a, dry="--dry" in a))
        for cid in list(RESTORED): redismiss(cid)
    elif "--go-all-manual" in a:
        lim = int(a[a.index("--limit") + 1]) if "--limit" in a else 0; n = 0
        for r in rows:
            if lim and n >= lim: break
            try: rec = go_manual(r, release="--no-release" not in a, keep_restored=True)
            except Exception as e: rec = {"visitid": r["visitid"], "pid": r["pid"], "outcome": "error", "error": str(e)[:300]}; L("   ERROR %s" % e)
            reg["results"].append(rec); n += 1
            json.dump(reg, open(os.path.join(REGD, "payreason_repair_%s.json" % reg["stamp"]), "w"), indent=1, default=str)
            time.sleep(0.8)
        for cid in list(RESTORED): redismiss(cid)
    elif "--go-all" in a:
        lim = int(a[a.index("--limit") + 1]) if "--limit" in a else 0; n = 0
        # group the rows by the ERA check behind their hand posts (register, else the payment's check number in the unposted/dismissed lists)
        groups = {}; unknown = []
        for r in rows:
            pl = plan(r, allow_restore=False); cid = pl["checkid"]
            if not cid:
                for chkno in pl.get("checknos", []):
                    hit = [k for k, c in list(checks_index().items()) + list(dismissed_index().items()) if str(c.get("paymentnumber", "")).split("(")[0] == chkno.split("(")[0]]
                    if hit: cid = hit[0]; break
            (groups.setdefault(cid, []) if cid else unknown).append(r)
            time.sleep(0.2)
        L("groups: %s; unknown check: %d" % ({k: len(v) for k, v in groups.items()}, len(unknown)))
        for r in unknown: reg["results"].append({"visitid": r["visitid"], "pid": r["pid"], "outcome": "no-era-line"})
        for cid, grp in groups.items():
            if lim and n >= lim: break
            if "--skip-dismissed" in a and str(cid) not in checks_index():
                L("group %s (%d rows): dismissed check - skipped (--skip-dismissed)" % (cid, len(grp))); continue
            for r in grp:
                if lim and n >= lim: break
                try: rec = go(r, release="--no-release" not in a, keep_restored=True)
                except Exception as e: rec = {"visitid": r["visitid"], "pid": r["pid"], "outcome": "error", "error": str(e)[:300]}; L("   ERROR %s" % e)
                reg["results"].append(rec); n += 1
                json.dump(reg, open(os.path.join(REGD, "payreason_repair_%s.json" % reg["stamp"]), "w"), indent=1, default=str)
                time.sleep(0.8)
            if str(cid) in RESTORED: redismiss(cid)
        for cid in list(RESTORED): redismiss(cid)
    json.dump(reg, open(os.path.join(REGD, "payreason_repair_%s.json" % reg["stamp"]), "w"), indent=1, default=str)
    from collections import Counter
    L("SUMMARY: %s" % dict(Counter(x.get("outcome", "listed") for x in reg["results"])))
