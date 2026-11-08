# PLAIN ENGLISH (Clear the ERA Center unposted list the way William does by hand)
# Decides: For every check still on the ERA Center list: (1) post any line that still carries real money onto a visit with an open balance (era_post.post_check - the Post button); (2) post the leftover $0-payment / $0-adjustment lines (duplicates, info-only) the way 'Process Accepted ($0.00)' does; (3) if no postable money is left on the check, DISMISS it (POST /api/era/checks/dismiss with the check id as a JSON string - captured from William's own click on check 1050132, 9/7/2026). A check with money that still refuses to post is left on the list and reported.
# Rules it uses: never write off a denial line here ($0 pay with an adjustment is not posted - the cascade handles those visits; the check is dismissed because the remit is already read). Payments on visits already at $0 are counted, not re-posted - but since 11/7/2026 only a non-void payment carrying THIS check's number on the charge the remit line pays counts as posted (read with txh.fetch_visit, so old visits on long charts are seen; every paid remit line gets its OWN live charge - twin charges with the same CPT and date are handed out one per line, the one already carrying this check's payment first - so a claim with one line posted and one not is HELD); a visit paid only by another check (a Medigap / secondary remit whose PR-2 the primary's Post moved to the patient - 10/7/2026 lesson: move_to_ins then the ERA-linked post) is HELD, and a line whose history could not be read is HELD, never dismissed. A negative line (takeback / recoupment), validated or not, is HELD for William (11/7/2026). A check whose checkdetails answer no lines, or cannot be read, while the list still shows money is HELD, not dismissed. Resumable: 'DISMISS <id>' lines in era_clear.log are skipped on rerun; a HELD check is looked at again on every run (11/7/2026 - until then a HOLD line hid the check from every later run, the 10/28 DONE-set lesson).
# Never touches: visit balances beyond what the Post button itself would do. A check whose unvalidated lines ('Procedure codes do not match' etc.) carry money is HELD, never dismissed - lesson of 9/7 when 32 such checks ($7.4K) were dismissed and had to be restored - unless the charge already carries this check's payment (the fallback posted it ERA-linked).
# Writes: registers/era_denials_<UTC date>.json - the denial ($0) lines of every check it dismisses (check, visit, chart, DOS, CPT, CARC group / code / amount, RARC remark codes, AMD's validation message; no names) so a remit's reasons survive the dismissal (11/7/2026; checkdetails answers nothing for a dismissed check). era_clear_reversal_<UTC date>.json rows carry only the write-offs on the charges the remit line pays (also for the unposted lines of a partly posted claim) and a safe_force flag (true when the check's remaining lines are ONLY such unrecorded payments - no other money, no denial lines - so the Post button may be forced on the visit without the 9/21 SWEEP RULE trap); an existing row is refreshed, not skipped.
# ---
"""Usage: python3 era_clear.py [--dry] [--max N] [--carrier UNI20,FFVA]"""
import era_post, txh, json, sys, time, os, collections, requests, datetime
from era_post import checks, details, batch, locks, build, H, XML, S, L, postable, post_check
dry = "--dry" in sys.argv; mx = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 10**9
carriers = set(sys.argv[sys.argv.index("--carrier") + 1].split(",")) if "--carrier" in sys.argv else None
API = "https://pm-api-103.advancedmd.com/api"
UTCDAY = datetime.datetime.utcnow().strftime("%Y%m%d")   # 11/7/2026: UTC like the engine (run_all.py) that reads these files; the runners are UTC anyway
LOGF = "era_clear.log"
if os.path.exists(LOGF):
    _lines = open(LOGF).read().splitlines()
    if len(_lines) > 3000:   # 11/7/2026: HELD checks are re-examined every run, so the log grows - keep every DISMISS line and the last 300 others
        keep = [l for l in _lines if l.startswith("DISMISS ")] + [l for l in _lines if not l.startswith("DISMISS ")][-300:]
        open(LOGF, "w").write("\n".join(keep) + "\n")
DONE = set(l.split()[1] for l in open(LOGF) if l.startswith("DISMISS ")) if os.path.exists(LOGF) else set(); CL = open(LOGF, "a")
def Z(m): L(m); CL.write(m + "\n"); CL.flush()
def adj(v): return sum(float(c.get("adjustmentamount") or 0) for c in v.get("charges") or [])
def norm_dos(s):
    s = (s or "")[:10]
    if "-" in s:
        y, m, d = s.split("-"); return "%s/%s/%s" % (m, d, y)
    return s
def zero_post(chk, det, zero):
    b = batch(); locks(chk["id"], ",".join(S(v["visitid"]) for v in zero)); body = build(chk, det, zero, b)
    for vis in body["ppmdmsg"]["visitlist"]["visit"]:
        for ch in vis["chargelist"]["charge"]: ch["@adjustmentamount"] = "0"; ch["@payreasonwoamount"] = "0"; ch["@paymentamount"] = "0"
    r = requests.post(XML, headers=H(), data=json.dumps(body), timeout=300)
    return r.status_code == 200 and "Fault" not in r.text and "faultstring" not in r.text, r.text[:200]
TX = {}; REV = []
def charges_of(pid, vid):
    """The visit's non-void charges from its own transaction history (txh.fetch_visit - page 1 of the whole chart misses old visits, 9/22/2026); None when the history could not be read."""
    key = (str(pid), str(vid))
    if key not in TX:
        try: TX[key] = [ch for ch in txh.fetch_visit(pid, vid).iter("charge") if ch.get("void") != "1" and ch.get("visit") in (None, str(vid))]
        except Exception as e: L("   txh %s v%s failed: %s" % (pid, vid, str(e)[:80])); TX[key] = None
    return TX[key]
def live_match(chs, ln, vdos=None):
    """The live charges a remit charge line can pay: by chargedetailid when AMD gave one, else every charge with the same CPT + DOS (twins; the claim's DOS when the line carries none)."""
    cid = str(ln.get("chargedetailid") or "")
    if cid not in ("", "0", "-1", "None"):
        m = [ch for ch in chs if str(ch.get("id")) == cid]
        if m: return m
    cpt = (ln.get("chargecode") or "").strip(); ldos = norm_dos(ln.get("dos") or vdos)
    return [ch for ch in chs if (ch.get("proccode") or "").strip() == cpt and ch.get("dos") == ldos]
def pays_of(chs): return [p for ch in chs for p in ch.iter("payment") if p.get("void") != "1" and float(p.get("amount") or 0) != 0]
def has_this(ch, ck): return bool(ck) and any((p.get("checknumber") or "").strip() == ck for p in pays_of([ch]))
def assign(chs, lines, ck, vdos=None):
    """Give every paid remit line its OWN live charge: among its candidates (live_match) the one already carrying this check's payment first, else the first still free;
    a twin charge is never handed to two lines (11/7/2026 third review - two twin lines used to be counted on the same paid charge). Returns [(line, charge or None)]."""
    free = list(chs); out = []
    for ln in lines:
        cands = [c for c in live_match(chs, ln, vdos) if any(c is f for f in free)]
        pick = next((c for c in cands if has_this(c, ck)), None)
        if pick is None and cands: pick = cands[0]
        if pick is not None: free = [f for f in free if f is not pick]
        out.append((ln, pick))
    return out
def rev_row(v, chk, targets, safe=False):
    wos = [(ch.get("id"), w.get("id"), w.get("wocode"), w.get("amount"), w.get("date")) for ch in targets for w in ch.iter("writeoff") if w.get("void") != "1"]
    if wos: REV.append({"checkid": chk["id"], "check": chk.get("paymentnumber"), "carrier": chk.get("systemcarriercode") or "", "visitid": v["visitid"], "patientid": v["patientid"], "patient": v["patientname"],
                        "dos": (v.get("dos") or "")[:10], "era_pay": v["paymentamount"], "writeoffs": wos, "fee": sum(float(ch.get("fee") or 0) for ch in targets), "safe_force": safe})
    return bool(wos)
def recorded(v, chk):
    """How this remit line's money stands on the live visit, charge by charge: 'this' = every paid remit line's own charge carries a non-void payment with this check's number (posted);
    'partial' = some do, some do not (the unposted written-off charges get a reversal row, never safe to force); 'other' = payments exist but none from this check (a secondary / Medigap line - the primary's Post moved PR-2 to the patient:
    move_to_ins, then the ERA-linked post - 10/7/2026 lesson); 'none' = no payment at all (a reversal row when only write-offs sit on the paid charges); 'nomatch' = no live charge matches the remit lines; 'nocharges' = no live charge on the visit; 'unreadable' = the history could not be read."""
    chs = charges_of(v["patientid"], v["visitid"])
    if chs is None: return "unreadable"
    if not chs: return "nocharges"
    ck = str(chk.get("paymentnumber") or "").strip()
    paid_lines = [ln for ln in (v.get("charges") or []) if float(ln.get("paymentamount") or 0) > 0]
    pairs = assign(chs, paid_lines, ck, v.get("dos")) if paid_lines else [(None, c) for c in chs]
    if paid_lines and all(c is None for _, c in pairs): return "nomatch"
    n_this = sum(1 for _, c in pairs if c is not None and has_this(c, ck))
    if n_this == len(pairs): return "this"
    if n_this or any(has_this(c, ck) for c in chs):
        rev_row(v, chk, [c for _, c in pairs if c is not None and not has_this(c, ck) and not pays_of([c])], safe=False)
        return "partial"
    assigned = [c for _, c in pairs if c is not None]
    if pays_of(assigned) or pays_of(chs): return "other"
    rev_row(v, chk, assigned)
    return "none"
REVF = "era_clear_reversal_%s.json" % UTCDAY
def save_rev():
    """Append this check's reversal rows to today's file; a row already there (same check and visit) is refreshed - its safe_force may have changed."""
    if not REV: return
    try: old = json.load(open(REVF)) if os.path.exists(REVF) else []
    except ValueError: old = []
    new = {(r["checkid"], r["visitid"]): r for r in REV if r.get("checkid") is not None}
    kept = [r for r in old if (r.get("checkid"), r.get("visitid")) not in new]
    json.dump(kept + list(new.values()), open(REVF, "w"), indent=1); REV.clear()
DENF = os.path.join("registers", "era_denials_%s.json" % UTCDAY)
def save_denials(chk, lines):
    """PHI-light record of a dismissed check's denial ($0) lines: check, visit, chart, DOS, CPT, CARC group / code / amount, RARC codes, AMD's message - no names."""
    if not lines: return 0
    os.makedirs("registers", exist_ok=True)
    try: old = json.load(open(DENF)) if os.path.exists(DENF) else []
    except ValueError: old = []
    seen = {(str(r.get("checkid")), str(r.get("visitid"))) for r in old}; new = []
    for v in lines:
        if (str(chk["id"]), str(v.get("visitid"))) in seen: continue
        chs = []
        for c in v.get("charges") or []:
            carc = c.get("carc") or [a for a in (v.get("carc") or []) if a.get("chargedetailid") in (None, c.get("chargedetailid"))]
            chs.append({"cpt": c.get("chargecode"), "chargedetailid": c.get("chargedetailid"), "paid": c.get("paymentamount"), "adj": c.get("adjustmentamount"),
                        "carc": [{"grp": a.get("payreasongroup"), "code": a.get("reasoncode"), "amt": a.get("reasonamt")} for a in carc],
                        "rarc": [r.get("remarkcode") for r in (c.get("rarc") or []) if r.get("remarkcode")]})
        new.append({"checkid": chk["id"], "check": chk.get("paymentnumber"), "carrier": chk.get("systemcarriercode") or "", "deposit": (chk.get("depositdate") or "")[:10],
                    "visitid": v.get("visitid"), "chart": v.get("chartnum"), "dos": (v.get("dos") or "")[:10], "claimstatus": v.get("claimstatus"), "processok": v.get("processok"),
                    "rarc": [r.get("remarkcode") for r in (v.get("rarc") or []) if r.get("remarkcode")],
                    "errors": [str(e.get("paymententrymessage") or e.get("id") or e)[:120] for e in (v.get("errors") or [])], "charges": chs,
                    "when": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")})
    if new: json.dump(old + new, open(DENF, "w"), indent=1)
    return len(new)
def dismiss(cid):
    r = requests.post(API + "/era/checks/dismiss", headers=H(), data=json.dumps(str(cid)), timeout=60)
    return r.status_code == 200 and '"issuccess":true' in r.text, r.text[:120]
def listed_money(chk):
    """What the list says is still unposted on the check (its payment amount when the list carries no unposted figure)."""
    u = chk.get("unpostedamount")
    return float(u if u is not None else (chk.get("paymentamount") or 0))
allc = checks(); todo = [c for c in allc if str(c["id"]) not in DONE and (not carriers or c["systemcarriercode"] in carriers)]
Z("=== ERA CLEAR %s: %d on the list, %d to do, dry=%s ===" % (time.ctime(), len(allc), len(todo), dry))
K_UNREC = "unrecorded payment (reversal pipeline)"
K_UNVAL = "not validated with money (the fallback era_fallback_0913b.py posts it ERA-linked; by hand: era_manual_post.py)"
HOLDK = ("postable money", K_UNREC, K_UNVAL,
         "takeback line (William decides: recoupment - never dismissed)", "paid by another check only (secondary line: move_to_ins + ERA-linked post)",
         "some lines of this check still unposted on the visit", "no live charge matches the remit line - left",
         "visit history unreadable - left", "visit has no live charge - left", "checkdetails answered no lines while the list shows money - left")
NOT_ALONE = ("denial with write-off (cascade handles)", "not validated $0")   # with these on the check a forced single-visit Post may sweep them (9/21 SWEEP RULE) - the routine settles them first
cat = collections.Counter(); money = collections.Counter(); n = 0; nd = 0; nz = 0; np_ = 0.0
for chk in sorted(todo, key=lambda x: x["depositdate"]):
    if n >= mx: break
    n += 1
    ckno = chk.get("paymentnumber")
    try: det = details(chk["id"])
    except Exception as e:
        Z("HOLD %s %s %s $%s: checkdetails could not be read (%s) - left on the list" % (chk["id"], chk.get("systemcarriercode") or "", ckno, chk.get("paymentamount"), str(e)[:60])); cat["details unreadable"] += 1; continue
    vs = det.get("eracheckdetails") or []; pay_lines = [v for v in vs if postable(v)]
    if pay_lines and not dry:
        k, t = post_check(chk); np_ += t; cat["money posted"] += k
        det = details(chk["id"]); vs = det.get("eracheckdetails") or []; pay_lines = [v for v in vs if postable(v)]
    zero = []; held = collections.Counter(); den = []
    if not vs and listed_money(chk) > 0:
        held["checkdetails answered no lines while the list shows money - left"] += 1; money["unreadable"] += listed_money(chk)
    def by_history(pay, st):
        if st == "this": held["money already on the visit"] += 1; money["already posted"] += pay
        elif st == "partial": held["some lines of this check still unposted on the visit"] += 1; money["partly posted"] += pay
        elif st == "other": held["paid by another check only (secondary line: move_to_ins + ERA-linked post)"] += 1; money["secondary unposted"] += pay
        elif st == "none": held[K_UNREC] += 1; money["unrecorded"] += pay
        elif st == "nomatch": held["no live charge matches the remit line - left"] += 1; money["unreadable"] += pay
        elif st == "nocharges": held["visit has no live charge - left"] += 1; money["unreadable"] += pay
        else: held["visit history unreadable - left"] += 1; money["unreadable"] += pay
    for v in vs:
        pay = float(v.get("paymentamount") or 0); a = adj(v); bal = float(v.get("insurancebalance") or 0)
        if pay < 0: held["takeback line (William decides: recoupment - never dismissed)"] += 1; money["takeback"] += pay
        elif v.get("errors") or not v.get("processok"):
            if pay > 0:
                st = recorded(v, chk)
                if st == "this": held["money already on the visit"] += 1; money["already posted"] += pay
                elif st == "partial": held["some lines of this check still unposted on the visit"] += 1; money["partly posted"] += pay
                else: held[K_UNVAL] += 1; money["unvalidated"] += pay
            else: held["not validated $0"] += 1; den.append(v)
        elif pay == 0 and a == 0: zero.append(v)
        elif pay == 0: held["denial with write-off (cascade handles)"] += 1; money["denial writeoff"] += a; den.append(v)
        elif bal <= 0: by_history(pay, recorded(v, chk))
        else: held["postable money"] += 1; money["postable"] += pay
    alone = not any(held.get(k) for k in HOLDK + NOT_ALONE if k != K_UNREC)
    for r in REV:
        if r.get("checkid") == chk["id"] and r.get("safe_force") is not False or (r.get("checkid") == chk["id"] and alone and held.get("some lines of this check still unposted on the visit", 0) == 0):
            r["safe_force"] = alone   # the Post button may be forced on these visits only when nothing else on the check is unposted (9/21 SWEEP RULE)
    for k, v in held.items(): cat[k] += v
    if dry:
        Z("DRY %s %s %s: zero %d held %s" % (chk["id"], chk["systemcarriercode"], ckno, len(zero), dict(held)))
        save_rev(); continue
    if zero:
        ok, t = zero_post(chk, det, zero); nz += len(zero) if ok else 0
        if not ok: Z("   zero-post failed on %s: %s" % (chk["id"], t.replace("\n", " ")))
    if any(held.get(k) for k in HOLDK):
        save_rev(); Z("HOLD %s %s %s $%s: %s - left on the list" % (chk["id"], chk["systemcarriercode"], ckno, chk["paymentamount"], ", ".join("%d %s" % (held[k], k) for k in HOLDK if held.get(k)))); continue
    REV.clear()
    nden = save_denials(chk, den)
    if nden: Z("DENIALS %s %s: %d visit line(s) recorded in %s" % (chk["id"], ckno, nden, DENF))
    ok, t = dismiss(chk["id"])
    Z("%s %s %s %s $%s: zero-posted %d, held %s -> %s" % ("DISMISS" if ok else "FAILD", chk["id"], chk["systemcarriercode"], ckno, chk["paymentamount"], len(zero), dict(held) or "-", "ok" if ok else t)); nd += 1 if ok else 0
    time.sleep(0.4)
save_rev()
Z("=== done: %d looked at, money posted $%.2f, %d $0 lines posted, %d checks dismissed; lines %s; $ %s ===" % (n, np_, nz, nd, dict(cat), {k: round(v) for k, v in money.items()}))
