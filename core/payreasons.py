# PLAIN ENGLISH (Payment reason codes - the Payment Entry "Reason Codes" edit, from the backend)
# Decides: Which posted insurance payments carry NO reason codes (the fallback addpayments posts since 9/13/2026 -
#   addpayments silently drops reason codes, proven 9/12), and writes the remit's CARC list (CO-45 / PR-1 / PR-2 ...)
#   onto each of them the way the Payment Entry window's Reason Codes dialog + Save does (William's DevTools
#   capture 9/21/2026). A payment balances when paid + sum(reason amounts) == the charge fee; the PR amounts are
#   taken from the remit verbatim and the contractual CO-45 absorbs the rounding/residual so the check passes.
# Rules it uses: never invents a PR amount; never touches a payment that already has reason codes; never voids;
#   dry-run by default; every line goes to practices/ehpa/registers/payreason_repair_<stamp>.json.
# Never touches: write-offs, charges, claims, ERA Center. It only edits reason codes on existing payments.
# ---
"""Usage (from /home/claude/unbilled):
  python3 payreasons.py --scan                 # list code-less fallback payments (registers -> gettxhistory), no writes
  python3 payreasons.py --scan --since 2026-09-13 --pid 17471007   # chart-wide scan of one patient
  python3 payreasons.py --unbilled             # the Unbilled 'Payment reason codes are missing or do not balance' rows
  python3 payreasons.py --live [--limit N]     # apply the reason codes (registers + era_details cache), then verify
  python3 payreasons.py --live --unbilled --release   # repair the Unbilled rows and release them once balanced
Library: payreasons.candidates(), payreasons.plan(pay, fee, carc), payreasons.apply(pid, cid, payid, reasons), payreasons.verify(pid, payid)
"""
import amd, txh, json, os, re, sys, time, glob, datetime
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
WS = "/home/claude/unbilled"
ERA_DETAILS = os.path.join(WS, "era_details")
REG_DIRS = [os.path.join(WS, "registers"), os.path.join(HERE, "..", "practices", "ehpa", "registers"),
            "/home/claude/effinger-billing-backend/practices/ehpa/registers"]
LOG = open(os.path.join(WS if os.path.isdir(WS) else HERE, "payreasons.log"), "a")
def L(m):
    print(m, flush=True); LOG.write("%s %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), m)); LOG.flush()
def f(v):
    try: return round(float(str(v).replace(",", "") or 0), 2)
    except Exception: return 0.0
def stamp(): return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H%MZ")

# ---------------------------------------------------------------- registers -> which payments the fallback posted
def register_lines():
    """Every 'posted' line of era_manual_register.json + era_fallback_*_live.json (the addpayments fallback posts)."""
    seen = {}; files = []
    for d in REG_DIRS:
        if not os.path.isdir(d): continue
        files += [os.path.join(d, "era_manual_register.json")] + sorted(glob.glob(os.path.join(d, "era_fallback_*_live.json")))
    for fn in files:
        if not os.path.exists(fn): continue
        try: data = json.load(open(fn))
        except Exception as e: L("register unreadable %s: %s" % (fn, e)); continue
        items = data if isinstance(data, list) else (data.get("lines") or data.get("results") or [])
        for x in items:
            if x.get("outcome") != "posted" or not x.get("chargeid") and not x.get("chargedetailid"): continue
            cid = str(x.get("chargeid") or x.get("chargedetailid"))
            key = (str(x.get("pid")), cid, str(x.get("checkno") or "").split("(")[0])
            if key in seen: continue
            seen[key] = {"pid": str(x["pid"]), "cid": cid, "visitid": x.get("visitid"), "checkid": str(x.get("checkid") or ""),
                         "checkclaimid": x.get("checkclaimid"), "checkno": key[2], "carrier": x.get("carrier"), "cpt": x.get("cpt"),
                         "dos": x.get("dos"), "pay": f(x.get("pay")), "wo": f(x.get("wo")), "when": x.get("when"), "register": os.path.basename(fn)}
    return list(seen.values())

# ---------------------------------------------------------------- tx history: the diagnostic (payreason children)
def chart_payments(pid, root=None):
    """[(charge attrs, payment attrs, [ (group+code, amount) reasons ])] for every non-void payment on the chart."""
    root = root if root is not None else txh.fetch(pid)
    out = []
    for c in root.iter("charge"):
        if c.get("void") == "1": continue
        for p in c.iter("payment"):
            if p.get("void") == "1": continue
            reasons = [(r.get("code", ""), f(r.get("amount")), r.get("description", "")) for r in p.iter("payreason")]
            out.append((c.attrib, p.attrib, reasons))
    return out

def fee_of(cattrs):
    for k in ("fee", "amount", "netfee", "charge", "chargeamount"):
        if cattrs.get(k) not in (None, ""): return f(cattrs.get(k))
    return 0.0

def codeless(pid, since=None, root=None):
    """Non-void insurance payments with amount != 0 (or any amount when since is None) and no payreason children."""
    out = []
    for c, p, reasons in chart_payments(pid, root):
        if reasons: continue
        ct = (p.get("createtime") or p.get("date") or "")[:10]
        if since and ct and ct < since: continue
        out.append({"pid": str(pid), "cid": re.sub(r"\D", "", c.get("id", "")), "payid": re.sub(r"\D", "", p.get("id", "")),
                    "amount": f(p.get("amount")), "checkno": p.get("checknumber", ""), "carrier": p.get("carrier", ""),
                    "createtime": p.get("createtime", ""), "fee": fee_of(c), "cpt": c.get("proccode", ""), "dos": c.get("dos") or c.get("dateofservice", ""),
                    "insbalance": f(c.get("insbalance")), "patbalance": f(c.get("patbalance"))})
    return out

def candidates(since=None, pids=None, chartwide=False):
    """The repair set. Default = register-driven: every fallback-posted line whose payment (same charge, same check
    number, same amount) still has no reason codes. chartwide=True = every code-less non-zero insurance payment on the
    register patients (or --pid) since <since>."""
    lines = register_lines()
    by_pid = {}
    for x in lines: by_pid.setdefault(x["pid"], []).append(x)
    targets = [str(p) for p in pids] if pids else sorted(by_pid)
    out = []
    for pid in targets:
        root = txh.fetch(pid)
        cl = codeless(pid, since=since, root=root)
        if chartwide:
            for x in cl:
                if x["amount"] != 0: out.append(dict(x, source="chartwide"))
            continue
        for reg in by_pid.get(pid, []):
            hits = [x for x in cl if x["cid"] == reg["cid"] and abs(x["amount"] - reg["pay"]) < 0.011
                    and (not reg["checkno"] or not x["checkno"] or x["checkno"].split("(")[0] == reg["checkno"])]
            for x in hits: out.append(dict(x, source=reg["register"], checkid=reg["checkid"], checkclaimid=reg["checkclaimid"], era_cpt=reg["cpt"], era_dos=reg["dos"]))
        time.sleep(0.4)
    return out

# ---------------------------------------------------------------- the remit's CARC list for one charge
def era_details(checkid):
    fn = os.path.join(ERA_DETAILS, "%s.json" % checkid)
    if os.path.exists(fn):
        try: return json.load(open(fn))
        except Exception: pass
    try:
        import era_post
        d = era_post.details(checkid)
        os.makedirs(ERA_DETAILS, exist_ok=True); json.dump(d, open(fn, "w"))
        return d
    except Exception as e:
        L("era_details %s unavailable: %s" % (checkid, e)); return None

def find_check_for_charge(cid, checkno=None):
    """No check id on file (a hand post outside the registers): search every cached era_details file for the charge."""
    for fn in sorted(glob.glob(os.path.join(ERA_DETAILS, "*.json")), key=os.path.getmtime, reverse=True):
        try: d = json.load(open(fn))
        except Exception: continue
        for v in d.get("eracheckdetails") or []:
            for ch in v.get("charges", []):
                if str(ch.get("chargedetailid")) == str(cid) and (not checkno or str(d.get("paymentnumber", "")).split("(")[0] in ("", checkno)):
                    return os.path.basename(fn)[:-5], v.get("checkclaimid")
    return None, None

def remit_carc(checkid, cid=None, checkclaimid=None, cpt=None, dos=None):
    """[{group, code, amount, payreasonid, reportreasondetailid, text}] for the ERA line matched to this charge."""
    if not checkid and cid:
        checkid, checkclaimid = find_check_for_charge(cid)
        if not checkid: return None, "charge %s not found in any cached era_details file" % cid
    d = era_details(checkid)
    if not d: return None, "no era details for check %s" % checkid
    visits = d.get("eracheckdetails") or d.get("visits") or []
    for v in visits:
        if checkclaimid and str(v.get("checkclaimid")) != str(checkclaimid): continue
        for ch in v.get("charges", []):
            m = (cid and str(ch.get("chargedetailid")) == str(cid)) or \
                (cpt and dos and str(ch.get("chargecode")) == str(cpt) and str(ch.get("dos", ""))[:10] == _iso(dos))
            if not m: continue
            carc = [{"group": str(r.get("payreasongroup") or ""), "code": str(r.get("reasoncode") or ""), "amount": f(r.get("reasonamt")),
                     "payreasonid": r.get("payreasonid"), "reportreasondetailid": r.get("reportreasondetailid"), "text": r.get("reasontext", "")}
                    for r in ch.get("carc", [])]
            rarc = [r.get("remarkcode") for r in ch.get("rarc", []) if r.get("remarkcode") and r.get("remarkcode") != "#AM"]
            return {"carc": carc, "rarc": rarc, "era_paid": f(ch.get("paymentamount")), "allowed": f(ch.get("allowedamount")),
                    "claimamount": f(ch.get("claimamount")), "visit": v.get("visitid")}, ""
    return None, "charge %s / %s %s not on check %s" % (cid, cpt, dos, checkid)

def _iso(d):
    d = str(d or "")
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", d)
    return "%s-%s-%s" % (m.group(3), m.group(1), m.group(2)) if m else d[:10]

# ---------------------------------------------------------------- the balanced reason list
def plan(paid, fee, carc):
    """PR (patient responsibility) amounts verbatim from the remit; the contractual CO-45 absorbs whatever is needed
    so paid + sum(reasons) == fee (AMD's 'do not balance' check). Returns (reasons, note) or (None, why)."""
    reasons = [dict(r) for r in (carc or []) if r.get("code")]
    if fee <= 0: return None, "charge fee unknown"
    s = round(sum(r["amount"] for r in reasons), 2)
    delta = round(fee - paid - s, 2)
    note = "remit balances" if abs(delta) < 0.011 else "CO45 adjusted by %+.2f (remit CARCs sum %.2f, paid %.2f, fee %.2f)" % (delta, s, paid, fee)
    if abs(delta) >= 0.011:
        co45 = next((r for r in reasons if r["group"] == "CO" and r["code"] == "45"), None)
        if co45 is None:
            if delta < 0: return None, "reasons exceed the fee by %.2f and there is no CO-45 to reduce" % -delta
            co45 = {"group": "CO", "code": "45", "amount": 0.0, "payreasonid": None, "text": "Charge exceeds fee schedule/maximum allowable"}
            reasons.append(co45)
        if round(co45["amount"] + delta, 2) < 0: return None, "CO-45 would go negative (%.2f%+.2f)" % (co45["amount"], delta)
        co45["amount"] = round(co45["amount"] + delta, 2)
    reasons = [r for r in reasons if abs(r["amount"]) >= 0.005 or r["group"] != "CO"]
    return reasons, note

# ---------------------------------------------------------------- the captured Payment Entry edit (filled in 9/21/2026)
REASON_IDS = {}   # "CO45" -> payreasonid, learned from era_details carc entries and the Reason Codes dialog lookup

def learn_reason_ids():
    for fn in glob.glob(os.path.join(ERA_DETAILS, "*.json")):
        try: d = json.load(open(fn))
        except Exception: continue
        for v in d.get("eracheckdetails") or []:
            for ch in v.get("charges", []):
                for r in ch.get("carc", []):
                    k = "%s%s" % (r.get("payreasongroup"), r.get("reasoncode"))
                    if r.get("payreasonid") and k not in REASON_IDS: REASON_IDS[k] = r["payreasonid"]
    return REASON_IDS

def build_edit_xml(pid, cid, payid, reasons, current):
    """The Payment Entry Save with reason codes - shape pending William's DevTools capture (9/21/2026)."""
    raise NotImplementedError("Payment Entry reason-code edit call not captured yet - paste William's DevTools request")

def apply(pid, cid, payid, reasons, current, dry=True):
    xml = build_edit_xml(pid, cid, payid, reasons, current)
    if dry: return True, "DRY " + re.sub(r"\s+", " ", xml)[:400]
    r = amd.post(xml)
    ok = 'success="1"' in r and "<Fault" not in r
    return ok, re.sub(r"\s+", " ", r)[:300]

def verify(pid, payid, expect=None):
    """Re-read the chart: the payment now carries payreason children and paid + reasons == fee."""
    for c, p, reasons in chart_payments(pid):
        if re.sub(r"\D", "", p.get("id", "")) != str(payid): continue
        fee = fee_of(c); paid = f(p.get("amount")); s = round(sum(a for _, a, _ in reasons), 2)
        ok = bool(reasons) and abs(paid + s - fee) < 0.011
        if expect: ok = ok and sorted((k, a) for k, a, _ in reasons) == sorted((r["group"] + r["code"], r["amount"]) for r in expect)
        return ok, {"reasons": reasons, "paid": paid, "fee": fee, "sum": s}
    return False, "payment %s not found on chart %s" % (payid, pid)

# ---------------------------------------------------------------- Unbilled rows of this error class
def unbilled_reason_rows():
    """getclaimunbillablecharges rows whose error starts 'Payment reason codes' -> [(pid, visitid, cid?, error)]."""
    r = amd.post(amd.msg("getclaimunbillablecharges", "claimsreports", {"lowdate": "", "highdate": "", "carrier": "", "provider": "", "nocookie": "1"}))
    out = []
    # robust to the exact nesting: one <visit ...> ... </visit> block per row; the error text sits inside it
    for blk in re.findall(r"<visit\b[^>]*>.*?</visit>", r, flags=re.S) or re.findall(r"<visit\b[^>]*/>", r):
        if "payment reason codes" not in blk.lower(): continue
        head = dict(re.findall(r'(\w+)="([^"]*)"', re.match(r"<visit\b[^>]*>", blk).group(0)))
        pid = re.sub(r"\D", "", head.get("patientid") or head.get("patient") or "")
        if not pid:
            m = re.search(r'patientid="([^"]*)"|<patient\b[^>]*\bid="([^"]*)"', blk); pid = re.sub(r"\D", "", (m.group(1) or m.group(2)) if m else "")
        err = re.search(r"Payment reason codes[^<\"]*", blk); err = err.group(0) if err else "Payment reason codes are missing or do not balance"
        out.append({"pid": pid, "visitid": re.sub(r"\D", "", head.get("id", "")), "error": err, "name": head.get("patientname", "")})
    return out

def unbilled_candidates(rows):
    """For the flagged visits: every non-void payment on their charges with no payreason children (any amount - a $0
    code-less 'Process Accepted' post blocks the next payer too; those are voided per the 9/12 rule, non-zero ones repaired)."""
    reg = {(x["pid"], x["cid"]): x for x in register_lines()}
    by_pid = {}
    for r in rows:
        if r["pid"]: by_pid.setdefault(r["pid"], set()).add(r["visitid"])
    out = []
    for pid, vids in sorted(by_pid.items()):
        root = txh.fetch(pid)
        for c, p, reasons in chart_payments(pid, root):
            if reasons or (c.get("visit") or c.get("visitid") or "") not in vids: continue
            cid = re.sub(r"\D", "", c.get("id", "")); rg = reg.get((pid, cid), {})
            out.append({"pid": pid, "cid": cid, "visitid": c.get("visit") or c.get("visitid"), "payid": re.sub(r"\D", "", p.get("id", "")),
                        "amount": f(p.get("amount")), "checkno": (p.get("checknumber") or "").split("(")[0], "carrier": p.get("carrier", ""),
                        "createtime": p.get("createtime", ""), "fee": fee_of(c), "cpt": c.get("proccode", ""), "dos": c.get("dos") or c.get("dateofservice", ""),
                        "insbalance": f(c.get("insbalance")), "patbalance": f(c.get("patbalance")), "source": "unbilled",
                        "checkid": rg.get("checkid"), "checkclaimid": rg.get("checkclaimid"), "era_cpt": rg.get("cpt"), "era_dos": rg.get("dos")})
        time.sleep(0.4)
    return out

def visit_balanced(pid, visitid):
    """True when every non-void payment on the visit's charges carries reasons that balance to the fee."""
    for c, p, reasons in chart_payments(pid):
        if (c.get("visit") or c.get("visitid") or "") != str(visitid): continue
        if not reasons or abs(f(p.get("amount")) + sum(a for _, a, _ in reasons) - fee_of(c)) >= 0.011: return False
    return True

def release(visitid):
    r = amd.post(amd.msg("hideunbillablevisits", "claimsreports", {"hide": "-1", "nocookie": "1"}, '<visitlist><visit id="vst%s"/></visitlist>' % visitid))
    return ('success="1"' in r and "<Fault" not in r), re.sub(r"\s+", " ", r)[:200]

# ---------------------------------------------------------------- CLI
if __name__ == "__main__":
    a = sys.argv[1:]
    def opt(name, default=None):
        return a[a.index(name) + 1] if name in a and a.index(name) + 1 < len(a) else default
    live = "--live" in a; do_release = "--release" in a; since = opt("--since"); pids = [opt("--pid")] if opt("--pid") else None
    limit = int(opt("--limit", "0") or 0)
    amd.login_cached()
    rows = []
    if "--unbilled" in a:
        rows = unbilled_reason_rows(); L("Unbilled 'Payment reason codes' rows: %d" % len(rows))
        cands = unbilled_candidates(rows); mode = "unbilled rows"
    else:
        cands = candidates(since=since, pids=pids, chartwide=bool(since)); mode = "chart-wide since %s" % since if since else "register-driven"
    L("code-less candidate payments: %d (%s)" % (len(cands), mode))
    reg = {"stamp": stamp(), "mode": "live" if live else "scan", "scope": mode, "unbilled_rows": rows, "candidates": len(cands), "lines": []}
    n = 0
    for x in cands:
        rec = dict(x)
        if x["amount"] == 0 and x.get("source") == "unbilled":
            # 9/12 standing rule: a $0 payment with no reason codes on an Unbilled 'Payment reason codes' row = void it
            if live:
                import void_tx
                ok, msg = void_tx.void_payment(x["pid"], x["cid"], x["payid"]); rec.update({"outcome": "voided-zero" if ok else "void-failed", "apply": msg})
            else: rec["outcome"] = "would-void-zero"
            reg["lines"].append(rec); L("  %s" % json.dumps(rec)); continue
        carc, why = remit_carc(x.get("checkid"), x["cid"], x.get("checkclaimid"), x.get("era_cpt") or x["cpt"], x.get("era_dos") or x["dos"])
        if not carc:
            rec["outcome"] = "no-remit"; rec["why"] = why; reg["lines"].append(rec); L("  %s" % json.dumps(rec)); continue
        reasons, note = plan(x["amount"], x["fee"], carc["carc"])
        rec.update({"remit": carc, "plan": reasons, "note": note})
        if not reasons:
            rec["outcome"] = "unbalanced"; reg["lines"].append(rec); L("  %s" % json.dumps(rec)); continue
        if not live:
            rec["outcome"] = "would-apply"; reg["lines"].append(rec); L("  %s" % json.dumps(rec)); continue
        if limit and n >= limit: rec["outcome"] = "limit"; reg["lines"].append(rec); continue
        ok, msg = apply(x["pid"], x["cid"], x["payid"], reasons, x, dry=False); n += 1
        rec["apply"] = msg
        if ok:
            time.sleep(0.8); vok, v = verify(x["pid"], x["payid"], reasons); rec["verify"] = v
            rec["outcome"] = "repaired" if vok else "applied-unverified"
        else:
            rec["outcome"] = "failed"
        reg["lines"].append(rec); L("  %s" % json.dumps(rec)); time.sleep(0.6)
    if live and do_release and rows:
        for r in rows:
            touched = [l for l in reg["lines"] if l["pid"] == r["pid"] and l.get("outcome") in ("repaired", "voided-zero")]
            if not touched: continue
            time.sleep(0.5)
            if not visit_balanced(r["pid"], r["visitid"]):
                L("vst%s still unbalanced after repair - NOT released" % r["visitid"]); reg.setdefault("held", []).append(r["visitid"]); continue
            ok, msg = release(r["visitid"]); L("release vst%s -> %s %s" % (r["visitid"], ok, msg)); reg.setdefault("released", []).append({"visitid": r["visitid"], "ok": ok})
    out = os.path.join(REG_DIRS[0] if os.path.isdir(REG_DIRS[0]) else ".", "payreason_repair_%s.json" % reg["stamp"])
    os.makedirs(os.path.dirname(out), exist_ok=True); json.dump(reg, open(out, "w"), indent=1)
    from collections import Counter
    L("SUMMARY %s -> %s" % (dict(Counter(l.get("outcome") for l in reg["lines"])), out))
