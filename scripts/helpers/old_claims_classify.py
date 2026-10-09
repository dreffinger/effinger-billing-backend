# PLAIN ENGLISH (Old-claims disposition - the classifier; no AMD calls)
# Decides: a PROPOSED disposition for every unpaid visit over 90 days old, from the live chart facts (old_claims_facts.py), the
#   payers' 277 answers (tonight's sweep, the earlier UNI20/BCBS registers, and the EXACT-DATE re-ask claim_status_exact.py whose
#   answer names the AMD claim id, check number and paid date) and William's standing rules. Nothing is written to AMD here - the
#   output is the list William approves (old_claims_disposition_<stamp>.json -> approval cards + the review page) and the input
#   of old_claims_apply.py.
# Rules it uses (William 9/7, 9/11, 10/6, 10/9/2026):
#   - adjudicated (any non-void payment on the visit, $0 with reason codes included) = not a claim-status disposition: a paid
#     visit's residual is cost-sharing / contractual -> sub-typed for the insurances-cleaning pass; two rule-backed packages are
#     offered from it (J: dual patient, Medicaid secondary on the chart -> WOCAID2ND; I: adjudicated cost-sharing with no other
#     plan and under $25 for the whole patient -> WOSMBAL); a posted $0 denial inside 12 months -> the denial cascade; a posted
#     $0 denial over 12 months -> untimely write-off (WOLATE).
#   - never adjudicated + the payer's EXACT-DATE 277 names a payment on this visit's own AMD claim id = POST the payer's own
#     figures (amount, check number, paid date); the remainder is WOINS contractual when the chart has no other plan, WOCAID2ND
#     when the other plan is Medicaid-family, and is LEFT OPEN (listed) when the other plan is a supplement. A windowed (+/-3 day)
#     PAID answer with no exact-date confirmation never posts - it is listed for review.
#   - never adjudicated + 277 says paid but gives no amount = WOPDEOB (paid per payer, remit never received).
#   - never adjudicated + over 12 months from DOS, primary position = write off: WOLATE when the payer answered (not on file /
#     denied / finalized $0), WOINS with the dated untimely note when there is no payer answer (Medicare never gets a claim over
#     12 months old).
#   - 277 NOT ON FILE inside 12 months = resend once as an original claim (freq 1); a visit that already carries a payer ICN is a
#     search miss, not a resend; a tf_writeoff_watch visit is never resent. 277 PENDING = wait. AET12 = hold (9/21 rule).
#   - a balance sitting at a secondary with no primary payment = review (order). deceased flag = confirm the DOS against the date
#     of death before anything (a DOS after the date of death is a VOID, never a write-off).
# Never touches: AMD.
"""Usage: python3 old_claims_classify.py [--stamp 1009] [--sweep claimstatus_20261009.json] [--exact claimstatus_exact_1009.json]"""
import json, datetime, collections, re, sys, os
a = sys.argv[1:]
def opt(n, d=None): return a[a.index(n) + 1] if n in a else d
STAMP = opt("--stamp", "1009"); TODAY = datetime.date(2026, 10, 9)
SWEEP = opt("--sweep", "claimstatus_%s.json" % TODAY.strftime("%Y%m%d")); EXACT = opt("--exact", "claimstatus_exact_%s.json" % STAMP)
facts = json.load(open("old_claims_facts_%s.json" % STAMP))["visits"]
sweep = {str(r["visitid"]): r for r in json.load(open(SWEEP))} if os.path.exists(SWEEP) else {}
EX = json.load(open(EXACT)) if os.path.exists(EXACT) else {}
ansf = json.load(open("answered_uni20_bcbs_%s.json" % STAMP)) if os.path.exists("answered_uni20_bcbs_%s.json" % STAMP) else {"answered": {}, "watch_vids": []}
answered, watch = ansf["answered"], set(ansf["watch_vids"])
DEC = {}
for p in ("deceased_cache.json", "registers/deceased_cache.json", "/home/user/effinger-billing-backend/practices/ehpa/registers/deceased_cache.json"):
    if os.path.exists(p):
        try: DEC = {k: v for k, v in json.load(open(p)).items() if v.get("dod")}; break
        except Exception: pass
MEDICAID = {"MCAD", "FLO99", "SIM01", "SUN01", "GEO05"}
SUPPLEMENT = {"AET12", "AAR01", "TRI05", "CHA03", "UNI01", "BAN07", "MUT01", "USAA", "HIG06", "MAG01", "PHY10"}
MEDICARE = {"FLO02", "RET01"}
UHC = {"UNI20", "UHCMA", "AAR01", "UMR"}
SMALL = 25.0; RECENT_SEND = 30; RECENT_ANSWER = 45
def money(x): return round(float(x or 0) + 1e-9, 2)
def d8(s):
    s = (s or "").strip()
    for fmt in ("%Y%m%d", "%Y-%m-%d", "%m/%d/%Y"):
        try: return datetime.datetime.strptime(s[:10] if "-" in s or "/" in s else s[:8], fmt).date()
        except Exception: pass
    return None
S = lambda x: ("; ".join(str(y) for y in x) if isinstance(x, (list, tuple)) else str(x or ""))

def answer_for(v):
    """Normalize the payer's windowed 277 answer: tonight's sweep first, else the latest UNI20/BCBS register row."""
    vid = v["vid"]; r = sweep.get(vid); src = "sweep 10/9"
    if r is None:
        r = answered.get(vid); src = "register " + (r.get("_file", "")[-20:-5] if r else "")
    if r is None: return {"src": None, "kind": "NONE", "action": "", "paid": 0.0, "checks": [], "dates": [], "claims": [], "detail": ""}
    act = r.get("action") or ""; kind = "UNKNOWN"; paid = 0.0; checks = []; dates = []; claims = []; detail = ""
    rows = r.get("status") or []
    if isinstance(rows, list) and rows and isinstance(rows[0], dict):
        for s in rows:
            if s.get("cat") in ("F0", "F1") and s.get("check"): checks.append(str(s["check"]))
            if s.get("cat") in ("F0", "F1") and s.get("paidDate"): dates.append(str(s["paidDate"]))
            if s.get("payerClaim"): claims.append(str(s["payerClaim"]))
        detail = "; ".join("%s %s %s %s" % (s.get("cat", ""), s.get("code", ""), (s.get("codev") or "")[:60], ("$%s" % s.get("paid")) if s.get("paid") else "") for s in rows)[:400]
    else:
        ps = S(r.get("paid")); den = S(r.get("denied")); oth = S(r.get("other"))
        checks += re.findall(r"chk (\S+)", ps) + [str(c) for c in (r.get("checks") or [])]; dates += re.findall(r"(\d{4}-\d{2}-\d{2})", ps); claims += re.findall(r"icn (\S+)", ps)
        detail = ("paid: %s | denied: %s | other: %s" % (ps[:160], den[:160], oth[:100]))[:400]
    m = re.search(r"PAID \$([\d.]+)", act)
    if act.startswith("PAID") and m and float(m.group(1)) > 0: kind, paid = "PAID", float(m.group(1))
    elif act.startswith("PAID") and not m:
        ps = S(r.get("paid")); m2 = re.match(r"\s*([\d.]+)", ps)
        if m2 and float(m2.group(1)) > 0: kind, paid = "PAID", float(m2.group(1))
        else: kind = "PAID-NOAMT"
    elif act.startswith("FINALIZED"):
        rr = [s for s in (rows if isinstance(rows, list) else []) if isinstance(s, dict)]
        if any(s.get("cat") == "F1" for s in rr): kind = "PAID-NOAMT"
        elif any(s.get("cat") == "F0" and str(s.get("code")) in ("38", "41", "42", "43", "44", "20") for s in rr) and not any(s.get("cat") in ("F2", "F3", "F4") for s in rr): kind = "PENDING"
        else: kind = "FINALIZED0"
    elif act.startswith("DENIED"): kind = "DENIED"
    elif act.startswith("NOT ON FILE"): kind = "NOTONFILE"
    elif act.startswith("PENDING"): kind = "PENDING"
    elif act.startswith("ERROR"): kind = "ERROR"
    elif act.startswith("SKIP"): kind = "SKIP"
    return {"src": src, "kind": kind, "action": act[:90], "paid": money(paid), "checks": sorted(set(checks))[:4], "dates": sorted(set(dates))[:4], "claims": sorted(set(claims))[:4], "detail": detail}

def exact_for(v):
    """The exact-date 277: payments that belong to THIS visit (the payer echoes the AMD claim id = visit id + letter)."""
    x = EX.get(v["vid"])
    if not x: return None
    if x.get("error") or x.get("rows") is None: return {"state": "error", "detail": x.get("error") or "no rows", "payments": []}
    dos8 = v["dos"].replace("-", ""); pays = x.get("payments") or []
    mine = [p for p in pays if (p.get("acct") or "").startswith(v["vid"])]
    how = "claim id"
    if not mine:
        mine = [p for p in pays if (p.get("svcDate") or "").startswith(dos8)]; how = "service date"
    if not mine and pays: return {"state": "other-claims", "detail": "payments on other claim ids: %s" % ", ".join("%s $%.2f %s" % (p.get("acct") or "?", p["amount"], p.get("check") or "") for p in pays[:4]), "payments": []}
    if not mine:
        cats = x.get("cats") or []; rows = x.get("rows") or []
        txt = "; ".join("%s %s %s" % (r.get("cat"), r.get("code"), (r.get("codev") or "")[:50]) for r in rows[:5])[:300]
        codes = {(r.get("cat"), str(r.get("code"))) for r in rows}
        if "F1" in cats: return {"state": "paid-noamt", "detail": txt, "payments": []}
        if any(c in ("F2", "F3", "F4") for c in cats): return {"state": "denied", "detail": txt, "payments": []}
        if any(c in ("A0", "A1", "A2", "A5", "P0", "P1", "P2", "P3", "P4", "P5") for c in cats) or any(c == "F0" and k in ("38", "41", "42", "43", "44", "20") for c, k in codes): return {"state": "pending", "detail": txt, "payments": []}
        if "F0" in cats: return {"state": "finalized-other", "detail": txt, "payments": []}
        if any(c in ("A3", "A4", "A6", "A7", "A8", "E0", "E1", "E2", "E3", "E4", "D0") for c in cats): return {"state": "notonfile", "detail": txt, "payments": []}
        return {"state": "empty", "detail": txt or "no status rows", "payments": []}
    seen = collections.OrderedDict()
    for p in mine: seen.setdefault((p.get("check") or "", "%.2f" % p["amount"]), p)
    mine = list(seen.values())
    detail = "exact-date 277 (%s): %s" % (how, "; ".join("$%.2f chk %s %s acct %s" % (p["amount"], p.get("check") or "?", p.get("date") or "", p.get("acct") or "?") for p in mine))
    if len({(p.get("acct") or "")[len(v["vid"]):] for p in mine}) > 1 and len({p.get("check") or "" for p in mine}) > 1:
        return {"state": "multi", "payments": mine, "detail": "the payer paid this visit more than once (original claim + resends, different checks) - possible duplicate payments; " + detail}
    # deposit date = the check / EFT issue date when the payer gives one (what the bank deposit carries), else the 277 status date
    return {"state": "paid", "how": how, "payments": mine, "paid": money(sum(p["amount"] for p in mine)), "checks": [p.get("check") or "" for p in mine], "dates": [p.get("checkDate") or p.get("date") or "" for p in mine], "detail": detail}

def chart_position(v):
    """Where the balance carrier sits in the visit's insurance order, and what other plan the chart carries at the DOS."""
    plans = (v.get("chart") or {}).get("plans") or []; dos = d8(v["dos"]); car = v["carrier"]
    mine = [p for p in plans if p["code"] == car]; order = [x for x in (v.get("insorder") or "").split(",") if x]
    seq = mine[0]["seq"] if mine else None
    pos = (order.index(seq) if seq in order else None) if order else (0 if seq == "1" else None)
    others = []
    for p in plans:
        if p["code"] == car: continue
        end = d8(p["end"]); begin = d8(p["begin"])
        active = (end is None or (dos and end >= dos)) and (begin is None or dos is None or begin <= dos + datetime.timedelta(days=366))
        if active: others.append(p["code"])
    return pos, order, others

def pkg_for_wo(car): return "D" if car in MEDICARE else ("E" if car in UHC or car == "BCBS" else "F")
def pkg_for_post(car): return "A" if car in UHC else ("B" if car == "BCBS" else "C")

out = []; byp = collections.defaultdict(list); prnone_by_pid = collections.defaultdict(float)
pre = {}
for v in facts:   # first pass: per-patient totals of adjudicated cost-sharing with no other plan (the WOSMBAL test is per patient)
    live = [c for c in v["charges"] if c["void"] != "1" and c["insbal"] > 0.004]
    if not live or not v["adjudicated"]: continue
    pos, order, others = chart_position(v); sec = [o for o in others if o not in MEDICARE]
    pr = v["paid_total"] > 0 or any(r.startswith("PR") for r in v["pay_reasons"])
    if pr and not sec: prnone_by_pid[v["pid"]] += sum(c["insbal"] for c in live)
for v in facts:
    live = [c for c in v["charges"] if c["void"] != "1" and c["insbal"] > 0.004]
    allive = [c for c in v["charges"] if c["void"] != "1"]
    ans = answer_for(v); ex = exact_for(v); pos, order, others = chart_position(v)
    sec_other = [o for o in others if o not in MEDICARE]
    med_sec = [o for o in sec_other if o in MEDICAID]; sup_sec = [o for o in sec_other if o not in MEDICAID]
    dec = bool((v.get("chart") or {}).get("deceased")) or (v["pid"] in DEC)
    age = v["age"]; car = v["carrier"]; old = age > 365
    tier = None; pkg = None; note = []; acts = []; wocode = None; sub = None
    openbal = money(sum(c["insbal"] for c in live)); patbal = money(sum(c["patbal"] for c in allive))
    def wo_all(code, chk="OLD%s" % STAMP, date="", split_pr=False, pr_code=None):
        """One write-off per live charge; with split_pr the patient-share part (PR reasons on the payer's own payment) gets pr_code and
        the rest - an unadjusted contractual (CO45/CO253 never re-posted after the WOINSBANK void) - gets WOINS (William 9/22)."""
        out = []
        for c in live:
            if not split_pr: out.append({"cid": c["cid"], "cpt": c["cpt"], "insbal": c["insbal"], "patbal": c["patbal"], "pay": 0.0, "wo": c["insbal"], "wocode": code, "check": chk, "paiddate": date}); continue
            pr = money(min(c["insbal"], sum(r[1] for p in c["pays"] if p["void"] != "1" and p["amount"] > 0 for r in p["reasons"] if str(r[0]).startswith("PR"))))
            co = money(c["insbal"] - pr)
            if pr > 0.004: out.append({"cid": c["cid"], "cpt": c["cpt"], "insbal": c["insbal"], "patbal": c["patbal"], "pay": 0.0, "wo": pr, "wocode": pr_code or code, "check": chk, "paiddate": date})
            if co > 0.004: out.append({"cid": c["cid"], "cpt": c["cpt"], "insbal": c["insbal"], "patbal": c["patbal"], "pay": 0.0, "wo": co, "wocode": "WOINS", "check": chk, "paiddate": date, "why": "unadjusted contractual (no PR reason covers it)"})
        return out
    if not allive or openbal <= 0:
        tier = "SETTLED"; note.append("no open insurance balance on the live chart any more")
    elif v["adjudicated"]:
        pr = v["paid_total"] > 0 or any(r.startswith("PR") for r in v["pay_reasons"])
        if pr:
            tier = "ADJ-RESIDUAL"
            pays = [p for c in allive for p in c["pays"] if p["void"] != "1"]
            bal_med = car in MEDICAID; bal_supp = car in SUPPLEMENT
            sec0 = sorted({p["carrier"] for p in pays if p["amount"] == 0 and (p["carrier"] in MEDICAID or p["carrier"] == "HUM01") and any(r[0] in ("OA23", "CO256", "CO170") for r in p["reasons"])})
            med_answered = sorted({p["carrier"] for p in pays if (p["carrier"] in MEDICAID) or (p["carrier"] == "HUM01" and any(r[0] == "OA23" for r in p["reasons"]))})
            prim_paid = [p for p in pays if p["amount"] > 0 and p["carrier"] not in MEDICAID]
            dual = bal_med or (med_sec and not sup_sec) or bool(sec0)
            sub = ("PR/" if any(r.startswith("PR") for r in v["pay_reasons"]) else "CO/") + ("dual" if dual else ("supp" if (sup_sec or bal_supp) else "none"))
            note.append("payer %s paid $%.2f on %s (%s); open $%.2f is the residual" % ("/".join(v["pay_carriers"]), v["paid_total"], v["last_pay_date"], "/".join(v["pay_reasons"])[:60], openbal))
            if set(v["pay_carriers"]) - {car}: note.append("balance sits at %s" % car)
            if car == "AET12": tier = "HOLD-AET12"; note.append("balance sits at Aetna Senior Supplemental - on hold (9/21 rule), worked from the Aetna side")
            elif dual and prim_paid:
                hum185 = any(p["carrier"] == "HUM01" and p["amount"] == 0 and any(r[0] in ("CO185", "N767") for r in p["reasons"]) for p in pays)
                if hum185: med_answered = sorted(set(med_answered) | {"HUM01"})
                tier, pkg, wocode = "WO-DUAL", ("J" if med_answered else "K"), ("WOINS" if hum185 else "WOCAID2ND"); acts = wo_all(wocode, split_pr=True, pr_code=wocode)
                note.append("dual: Medicaid-family coverage (%s) and the primary paid $%.2f - the cost-sharing residual is %s, never billed to the patient (9/11 rule%s); %s%s" % ("/".join(sorted(set(([car] if bal_med else []) + med_sec + sec0 + (["HUM01"] if hum185 else [])))), sum(p["amount"] for p in prim_paid),
                            wocode, "; Humana Medicaid answered CO185 provider-not-enrolled -> WOINS per William 9/20" if hum185 else "",
                            ("the Medicaid plan already answered on this visit (%s)" % "/".join(med_answered)) if med_answered else "the Medicaid plan has NOT answered on this visit yet - approving K skips the crossover",
                            "; the part no PR reason covers is an unadjusted contractual -> WOINS" if any(x.get("why") for x in acts) else ""))
            elif dual: note.append("dual, but the primary paid $0 (deductible) - the Medicaid plan may owe up to its own allowed: bill / crossover it, not a write-off (insurances cleaning task)")
            elif sub.endswith("none") and prnone_by_pid[v["pid"]] <= SMALL: note.append("no other plan on the chart; the patient's open cost-sharing here is $%.2f - small-balance candidate (WOSMBAL) once the whole account is read (insurances cleaning task)" % prnone_by_pid[v["pid"]])
            elif sub.endswith("none"): note.append("no other plan on the chart; patient cost-sharing $%.2f across the chart - patient statement (insurances cleaning task), not a write-off" % prnone_by_pid[v["pid"]])
            elif sub.endswith("supp"): note.append("supplement/commercial secondary %s - bill the secondary; timely from the primary's remit (insurances cleaning task)" % "/".join(sorted(set(sup_sec + ([car] if bal_supp else [])))))
            if sub.startswith("CO/"): note.append("no PR reason on the payment: the residual may be an unadjusted contractual (WOINS after an allowed-vs-paid read)")
        else:
            if old and (pos in (0, None)): tier, wocode = "WO-UNTIMELY", "WOLATE"; note.append("$0 denial posted (%s) and over 12 months - untimely" % "/".join(v["pay_reasons"]))
            else: tier = "CASCADE"; note.append("$0 denial posted (%s) inside 12 months - denial cascade" % "/".join(v["pay_reasons"]))
    else:
        if car == "AET12": tier = "HOLD-AET12"; note.append("Aetna Senior Supplemental hold (9/21 rule) - crossover claim, work from the Aetna side")
        elif v["vid"] in watch: tier = "WAIT"; note.append("on tf_writeoff_watch (sent 10/6-10/7) - waiting for the payer's answer")
        elif pos not in (0, None) and car not in MEDICARE:
            tier = "REVIEW-ORDER"; note.append("balance sits at position %d of order %s but no primary payment is posted" % (pos + 1, ",".join(order)))
        elif ans["kind"] in ("PAID", "PAID-NOAMT") or (ex and ex["state"] == "paid"):
            if ex is None:
                tier = "REVIEW"; note.append("windowed 277 says %s but no exact-date answer was obtained - not posted on a +/-3-day answer" % ans["action"])
            elif ex["state"] == "multi":
                tier = "REVIEW"; note.append(ex["detail"] + " - treasury check (which payments were deposited, which recouped) before anything is posted")
            elif ex["state"] == "paid":
                tier = "POST-277"; pkg = pkg_for_post(car); paid = min(ex["paid"], openbal)
                lines = collections.defaultdict(float); denied = set()
                for p in ex["payments"]:
                    for l in (p.get("lines") or []):
                        if l.get("cpt") and l.get("paid"): lines[str(l["cpt"])] += float(l["paid"] or 0)
                        elif l.get("cpt") and (l.get("cat") in ("F2", "F3", "F4") or not float(l.get("paid") or 0)): denied.add(str(l["cpt"]))
                alloc = []
                if lines and all((c["cpt"] in lines or c["cpt"] in denied) for c in live) and abs(sum(lines.values()) - ex["paid"]) < 0.02:
                    for c in live: alloc.append(money(min(lines.get(c["cpt"], 0.0), c["insbal"])))
                    note.append("per-line amounts from the 277 service details")
                else:
                    fees = sum(c["fee"] for c in live) or 1.0; left = paid
                    for i, c in enumerate(live):
                        share = money(paid * c["fee"] / fees) if i < len(live) - 1 else money(left)
                        share = max(0.0, min(share, c["insbal"], left)); alloc.append(share); left = money(left - share)
                chk = ex["checks"][0] if ex["checks"] else "277"; pdate = ex["dates"][0] if ex["dates"] else ""
                for c, pay in zip(live, alloc):
                    resid = money(c["insbal"] - pay); wo = 0.0; wc = None
                    if c["cpt"] in denied and pay <= 0:
                        note.append("line %s shows denied / unpaid on the 277 - left open for the denial cascade, no write-off" % c["cpt"]); continue
                    if resid > 0 and not sec_other: wo, wc = resid, "WOINS"
                    elif resid > 0 and med_sec and not sup_sec: wo, wc = resid, "WOCAID2ND"
                    acts.append({"cid": c["cid"], "cpt": c["cpt"], "insbal": c["insbal"], "patbal": c["patbal"], "pay": pay, "wo": wo, "wocode": wc, "check": chk, "paiddate": pdate})
                if len(ex["payments"]) > 1: note.append("the payer lists %d separate payments on this claim id - posted as one line under check %s" % (len(ex["payments"]), chk))
                plans_ = (v.get("chart") or {}).get("plans") or []; myseq = next((int(p["seq"]) for p in plans_ if p["code"] == car and p["seq"].isdigit()), 99)
                if car not in MEDICARE and any(p["code"] in MEDICARE and p["seq"].isdigit() and int(p["seq"]) < myseq and (d8(p["end"]) is None or d8(p["end"]) >= d8(v["dos"])) for p in plans_):
                    note.append("a Medicare plan sits ahead of the paying %s plan on the chart - the payer paid as primary, so the MA/commercial plan replaced Medicare on this DOS; the remainder is treated as contractual (if Medicare should have been primary, decline this row)" % car)
                if sup_sec: note.append("remainder $%.2f left open for the %s secondary (manual post carries no reason codes - the secondary claim will hold in Unbilled)" % (money(openbal - sum(alloc)), "/".join(sup_sec)))
                if ex["paid"] > openbal + 0.005: note.append("277 paid $%.2f exceeds the open $%.2f - posting the open balance only" % (ex["paid"], openbal))
                if patbal > 0: note.append("$%.2f sits on the patient balance - moved back to insurance first" % patbal)
                note.append(ex["detail"])
            elif ex["state"] == "paid-noamt":
                tier, wocode = "WO-PAID-NOREMIT", "WOPDEOB"; pkg = pkg_for_post(car); acts = wo_all(wocode, (ans["checks"] or ["277"])[0], (ans["dates"] or [""])[0]); note.append("exact-date 277 says paid/finalized on this claim but reports no amount - write off as paid per payer, remit never received (WOPDEOB): " + ex["detail"])
            elif ex["state"] in ("denied", "paid-noamt") and old: tier, wocode = "WO-UNTIMELY", "WOLATE"; note.append("exact-date 277 on this visit shows only %s (the windowed PAID answer came from a neighbouring day's claim) and the DOS is over 12 months" % ex["state"])
            elif ex["state"] == "denied": tier = "CASCADE"; note.append("exact-date 277 on this visit shows a denial, not a payment (the windowed PAID answer came from a neighbouring day's claim): " + ex["detail"])
            elif ex["state"] == "notonfile": tier, pkg = ("WO-UNTIMELY", None) if old else ("RESEND", "G"); wocode = "WOLATE" if old else None; note.append("exact-date 277: no claim on file for this visit (the windowed PAID answer came from a neighbouring day's claim): " + ex["detail"])
            elif ex["state"] == "pending": tier = "WAIT"; note.append("exact-date 277: pending on this visit - " + ex["detail"])
            else: tier = "REVIEW"; note.append("windowed 277 said %s; exact-date answer: %s %s" % (ans["action"], ex["state"], ex["detail"][:160]))
        elif ans["kind"] in ("FINALIZED0", "DENIED"):
            if old: tier, wocode = "WO-UNTIMELY", "WOLATE"; note.append("payer answered %s and the DOS is over 12 months - past every filing window (%s)" % (ans["kind"], ans["detail"][:100]))
            else: tier = "CASCADE"; note.append("payer denial inside 12 months - denial cascade (%s)" % ans["detail"][:140])
        elif ans["kind"] == "NOTONFILE":
            if v.get("icn"): tier = "REVIEW"; note.append("277 'not on file' but the visit carries payer ICN %s - a search miss (10/6 trap), not a resend" % v["icn"])
            elif old: tier, wocode = "WO-UNTIMELY", "WOLATE"; note.append("payer has no claim on file and the DOS is over 12 months")
            else: tier, pkg = "RESEND", "G"; note.append("payer has no claim on file - resend once as an original claim (freq 1)")
        elif ans["kind"] == "PENDING":
            tier = "WAIT"; note.append("277 pending at the payer" + (" - over 12 months, likely stuck; next sweep" if old else ""))
        else:
            if car in MEDICARE:
                if old: tier, wocode = "WO-UNTIMELY", "WOINS"; note.append("Medicare, never adjudicated, over 12 months - never sent to Medicare past a year (William 9/7)")
                else:
                    tier, pkg = "MEDICARE-UNANSWERED", "H"; sent = [b for b in (v.get("insbills") or []) if "MEDICARE" in (b.get("carriername") or "").upper()]
                    note.append("no Medicare adjudication on the chart %d days after the DOS; %s" % (age, ("last sent %s (claim %s)" % (sent[-1]["billeddate"], sent[-1]["claimid"])) if sent else "NO Medicare claim send on record"))
            elif old: tier, wocode = "WO-UNTIMELY", "WOINS"; note.append("never adjudicated, over 12 months, no payer answer (%s)" % (ans["kind"] if ans["src"] else "no 277 for this payer"))
            else: tier = "NO-ANSWER"; note.append("inside 12 months, no usable payer answer (%s) - next sweep" % (ans["action"] or "no 277 for this payer"))
        if tier in ("RESEND", "MEDICARE-UNANSWERED"):
            recent = [c for c in live if (d8(c["billdate"]) or datetime.date(2000, 1, 1)) >= TODAY - datetime.timedelta(days=RECENT_SEND)]
            sends = [b for b in (v.get("insbills") or []) if (car in MEDICARE and "MEDICARE" in (b.get("carriername") or "").upper()) or (car not in MEDICARE and (b.get("carriername") or "")[:8].upper() == (v.get("carriername") or "")[:8].upper())]
            if recent: tier, pkg, acts = "WAIT", None, []; note.append("last billed %s (inside %d days) - the answer to that send is still due; not resent" % (recent[0]["billdate"], RECENT_SEND))
            elif len(sends) >= 2: tier, pkg, acts = "REVIEW", None, []; note.append("already sent %d times to this payer with no answer on the chart (%s) - a plain resend is not the fix; needs the claim-run / 277CA rejection reason" % (len(sends), ", ".join(b.get("billeddate", "") for b in sends)))
            elif not acts: acts.append({"cid": live[0]["cid"], "cpt": live[0]["cpt"], "resend_seq": (order[0] if order else "1")})
    if tier == "WO-UNTIMELY":
        recent = [c for c in live if (d8(c["billdate"]) or datetime.date(2000, 1, 1)) >= TODAY - datetime.timedelta(days=RECENT_ANSWER)]
        if recent: tier, wocode = "WAIT", None; note.append("sent %s (inside %d days) - the payer's answer to that send is still due; write-off deferred" % (recent[0]["billdate"], RECENT_ANSWER))
        else: pkg = pkg_for_wo(car); acts = wo_all(wocode)
    if dec and tier not in ("SETTLED",):
        note.append("DECEASED flag on the chart - confirm the DOS is before the date of death (after = VOID, never a write-off)")
        if pkg: pkg = pkg + "-dec"
    rec = {"vid": v["vid"], "pid": v["pid"], "patient": v["patient"], "carrier": car, "dos": v["dos"], "age": age, "open": openbal, "patbal": patbal, "cpts": "+".join(c["cpt"] for c in allive), "provider": v.get("provider", ""),
           "tier": tier, "sub": sub, "pkg": pkg, "wocode": wocode, "answer": ans, "exact": ex, "position": pos, "order": ",".join(order), "other_plans": others, "deceased": dec, "notes": note, "actions": acts,
           "pay_total": money(sum(x.get("pay", 0) for x in acts)), "wo_total": money(sum(x.get("wo", 0) for x in acts)),
           "facts": {"live_insbal": v.get("live_insbal"), "live_patbal": v.get("live_patbal"), "paid_total": v["paid_total"], "pay_carriers": v["pay_carriers"], "last_pay_date": v["last_pay_date"], "pay_reasons": v["pay_reasons"], "wo_codes": v["wo_codes"],
                     "insorder": v.get("insorder", ""), "insbills": [(b.get("carriername", "")[:22], b.get("billeddate", ""), b.get("claimid", "")) for b in (v.get("insbills") or [])][-6:],
                     "charges": [{"cid": c["cid"], "cpt": c["cpt"], "mods": c.get("mods", ""), "fee": c["fee"], "paid": c["paid"], "insbal": c["insbal"], "patbal": c["patbal"], "carrier": c["carrier"], "billdate": c["billdate"], "void": c["void"],
                                  "pays": [(p["carrier"], p["amount"], p["date"], p["checkno"], p["void"], [r for r in p["reasons"]]) for p in c["pays"]], "wos": [(w["code"], w["amount"], w["date"], w["void"]) for w in c["wos"]]} for c in v["charges"]]}}
    out.append(rec); byp[v["pid"]].append(rec)
pkgs = collections.OrderedDict()
for r in out:
    k = r["pkg"] or ("list:" + r["tier"] + (("/" + r["sub"]) if r["sub"] else "")); s = pkgs.setdefault(k, {"visits": 0, "charges": 0, "open": 0.0, "paid277": 0.0, "pay": 0.0, "wo": 0.0, "carriers": collections.Counter()})
    s["visits"] += 1; s["charges"] += len(r["actions"]); s["open"] = money(s["open"] + r["open"]); s["paid277"] = money(s["paid277"] + ((r["exact"] or {}).get("paid", 0) if r["tier"] == "POST-277" else 0)); s["pay"] = money(s["pay"] + r["pay_total"]); s["wo"] = money(s["wo"] + r["wo_total"]); s["carriers"][r["carrier"]] += 1
for s in pkgs.values(): s["carriers"] = dict(s["carriers"].most_common())
PKG = {"A": "POST per 277 - UnitedHealthcare family (UNI20/UHCMA/AARP): post the payer's paid amount + check number + paid date as the payment, write off the remainder (WOINS, WOCAID2ND when the other plan is Medicaid)",
       "B": "POST per 277 - Florida Blue: same shape", "C": "POST per 277 - other carriers answered PAID on the exact date of service (Aetna, Simply, Humana, Cigna, Medicaid ...)",
       "D": "WRITE OFF untimely - Medicare, never adjudicated (or a $0 denial posted), DOS over 12 months (WOINS no answer / WOLATE answered; never sent to Medicare past a year)",
       "E": "WRITE OFF untimely - UHC family / Florida Blue, never adjudicated, DOS over 12 months (WOLATE when the payer answered, WOINS when it did not)",
       "F": "WRITE OFF untimely - every other carrier, never adjudicated, DOS over 12 months (WOLATE / WOINS as above)",
       "G": "RESEND once as an original claim (freq 1) - payer says NOT ON FILE, inside 12 months (standing Sunday-sweep rule)",
       "H": "Medicare, inside 12 months, no adjudication on the chart - resend once as an original claim (freq 1; deceased guard + one-rebill rule apply)",
       "I": "SMALL BALANCE - adjudicated cost-sharing, no other plan on the chart, the patient's whole open cost-sharing is under $25 -> WOSMBAL (9/11 rule) - not offered tonight (needs the whole account read)",
       "J": "DUAL, Medicaid plan already answered - Medicare/MA paid, a Medicaid-family plan (Medicaid / FCC / Simply / Sunshine / Georgia Medicaid / Humana Medicaid) has posted its $0 answer on the visit -> the cost-sharing residual is WOCAID2ND, never billed to the patient (9/11 rule)",
       "K": "DUAL, Medicaid plan not yet answered - same facts but the Medicaid-family plan has no posting on the visit yet: WOCAID2ND now skips the crossover (it would almost always answer $0 - primary paid at or above the Medicaid allowed)"}
json.dump({"stamp": STAMP, "built": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z", "sweep": SWEEP, "exact": EXACT, "exact_n": len(EX), "packages": PKG, "summary": pkgs, "visits": out}, open("old_claims_disposition_%s.json" % STAMP, "w"), indent=1)
groups = [{"pid": pid, "patient": rs[0]["patient"], "chart": next((f.get("chart") for f in facts if f["pid"] == pid), None), "visits": rs} for pid, rs in byp.items()]
json.dump(groups, open("old_claims_review_%s.json" % STAMP, "w"))
print("visits classified: %d (exact-date answers on file: %d); packages:" % (len(out), len(EX)))
for k, s in sorted(pkgs.items(), key=lambda x: (x[0].startswith("list"), x[0])): print("  %-28s %4d visits %4d charges  open $%9.2f  277-paid $%8.2f  post $%8.2f  wo $%9.2f  %s" % (k, s["visits"], s["charges"], s["open"], s["paid277"], s["pay"], s["wo"], s["carriers"]))
