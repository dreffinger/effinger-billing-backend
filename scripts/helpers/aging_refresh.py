#!/usr/bin/env python3
# PLAIN ENGLISH (AR aging refresh - the "Refresh from AMD" button on the AR Aging page, William 10/15/2026: "make this chart as an
#   ar aging artifact ... with a refresh button at the top or in the hero like the rest of the artifacts")
# Decides: nothing in AMD. READ-ONLY. Pulls every open insurance balance (POST /api/claim/massrebillsearch {} - the unpaid list with
#   the LAST-BILLED carrier), reads each chart's live transaction history once (gettxhistory page 1; a listed visit missing from
#   page 1 is fetched by visitid) and its insurance plans (getdemographic), then ages every visit by DAYS SINCE THE CLAIM WAS LAST
#   SENT (the charge billdate) and by days since the date of service, and files it under William's standing rules:
#   WAIT / CORRECT & RESEND / WRITE OFF with the rule that decided it. Writes aging_latest.json - chart ids, visit ids, CPTs,
#   dollars and dates only, never a name, member id or DOB - for the AR Aging page and the Billing Button report.
# Rules it uses (practices/ehpa/rules.md 10/13-10/15/2026): 0-30 days since sent wait; 31-60 wait (UNI20/BCBS never auto-rebilled);
#   61-90 status check then resend as original; 91-120 fix+resend; >120 = the 10/13 rule (fix+resend or write off); a primary unpaid
#   > 12 months from DOS = WOINS untimely; a secondary is timely from the primary's remit; a visit whose last-billed carrier already
#   PAID it is a settled primary (leftover = cost-share to the chart's live secondary if the remit is < 12 months old, else WOCLTREQ /
#   WOCAID2ND, plus any unwritten contractual = WOINS); wrong-payer denials (PR27/26/200/22/204/24/31/109) -> insurance cascade;
#   CCM to straight Medicaid, and CCM DENIED on a hospice patient (GV / CO-B9), -> WONCS; CO-29 -> WOLATE; DOS after a Medicare
#   date of death -> void. Recommendations are for William's word - this script writes nothing in AMD.
#   A no-charge reporting line (1123F / 1124F / M0004, 11/10/2026) never makes a visit read as denied; reason 246 is informational.
# Never touches: AMD writes, balances, claims.
#   cd /home/claude/unbilled && python3 aging_refresh.py [--out aging_latest.json] [--threads 4] [--max N]
#   --offline <unpaid.json> <suffix>   no AMD at all: rows from a saved massrebillsearch answer, charts from
#                                      patient_db/<pid>/txh_<suffix>.json + plans_<suffix>.json (the unpaid_txh/unpaid_demo snapshots)
import collections, datetime, json, os, re, sys, threading, time
import xml.etree.ElementTree as ET
sys.path.insert(0, "/home/claude/unbilled")
# 11/26/2026: the denial-code sets come from the ONE table both engines read - TABLE in boards/working_denials.py (the workspace copy
#   beside this helper) - so the board and these sets can no longer disagree. Every set is what it was, plus the codes the table added
#   (wrong payer 32/177/140/20/21/B11, correctable 146, credentialing 170/147/256/299); CO-151 on a CCM claim is a re-date.
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "boards"))

WS = "/home/claude/unbilled"
a = sys.argv
OUT = a[a.index("--out") + 1] if "--out" in a else "aging_latest.json"
NT = int(a[a.index("--threads") + 1]) if "--threads" in a else 4
MAXP = int(a[a.index("--max") + 1]) if "--max" in a else 10 ** 9
OFFLINE = (a[a.index("--offline") + 1], a[a.index("--offline") + 2]) if "--offline" in a else None
if not OFFLINE:
    import amd, era_post, requests, txh
TODAY = datetime.date.fromisoformat(a[a.index("--today") + 1]) if "--today" in a else datetime.date.today()
CCM = {"99490", "99491", "99487", "99489", "99439", "99437", "G0506", "G0511", "99424", "99425", "99426", "99427"}
try:
    from working_denials import family as _family
    WRONG_PAYER = _family("WRONG_PAYER")      # 27 26 200 31 109 22 24 204 49 (+ 32 177 140 20 21 B11, 11/26/2026)
    BUNDLED = _family("BUNDLED")              # 97 234 B15 236
    CORRECTABLE = _family("CORRECT")          # 4 16 125 11 181 MA130 5 (+ 146)
    CRED_CODES = _family("CRED")              # 242 243 185 B7 (+ 170 147 256 299)
    REDATE = _family("REDATE")                # 151 - on a CCM claim: re-date to the last day of its month (rules.md 10/4/2026)
    NONCOVERED = _family("NONCOVERED") | REDATE   # 96 50 A1 151 119
except ImportError:                          # a copy run without the board's file beside it (a self-test's throwaway copy): the sets of 11/25/2026
    sys.stderr.write("aging_refresh: working_denials.py (the denial-code table) not found - the code sets of 11/25/2026 are used\n")
    WRONG_PAYER = {"27", "26", "200", "31", "109", "22", "24", "204", "49"}; BUNDLED = {"97", "234", "B15", "236"}
    CORRECTABLE = {"4", "16", "125", "11", "181", "MA130", "5"}; CRED_CODES = {"242", "243", "185", "B7"}
    REDATE = {"151"}; NONCOVERED = {"96", "50", "A1", "151", "119"}
BACKLOG = {"UNI20", "BCBS"}
MEDICAID_FAMILY = {"MCAD", "SUN01", "FLO99", "SIM01", "WEL04", "UHCMA", "HUM07"}
# REPORTING LINES (11/10/2026, second no-harm review): a no-charge quality code (1123F / 1124F) or option code (M0004) rides at $0.00 or
# $0.01 on a Medicare claim; Medicare answers it with reason 246 (remark N620). Its payment lines never make a visit read as denied or
# paid - they are left out of what decide() counts for the visit (their payments AND their bill dates: a line billed later is not the
# visit's last send) - and 246 is an informational reason.
REPORTING = {"1123F", "1124F", "M0004"}
INFO_REASONS = ("45", "253", "23", "94", "1", "2", "3", "246")
num = lambda s: re.sub(r"\D", "", str(s or ""))

def mdy(s):
    m = re.match(r"\s*(\d\d)/(\d\d)/(\d{4})", str(s or ""))
    return datetime.date(int(m.group(3)), int(m.group(1)), int(m.group(2))) if m else None
def iso(s):
    m = re.match(r"(\d{4})-(\d\d)-(\d\d)", str(s or ""))
    return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None
def norm(carc):
    c = str(carc or "").strip().upper()
    for g in ("CO", "OA", "PR", "PI", "CR"):
        if c.startswith(g) and len(c) > len(g): return c[len(g):]
    return c
def group(carc):
    c = str(carc or "").strip().upper()
    return c[:2] if c[:2] in ("CO", "OA", "PR", "PI", "CR") else ""
def bucket(days):
    if days is None: return "unknown"
    if days <= 30: return "0-30"
    if days <= 60: return "31-60"
    if days <= 90: return "61-90"
    if days <= 120: return "91-120"
    return "over 120"
def f(x):
    try: return float(x or 0)
    except (TypeError, ValueError): return 0.0

def carrier_map():
    for p in (os.path.join(WS, "carriers.json"), os.path.join(WS, "carriers_rich.json")):
        try:
            j = json.load(open(p)); m = {k: v[0] for k, v in j.items() if isinstance(v, list)}
            if m: return m
        except Exception: pass
    return {}
CAR = carrier_map()

def deceased():
    out = {}
    for p in (os.environ.get("DECEASED_CACHE", ""), "/home/claude/practices/ehpa/registers/deceased_cache.json", os.path.join(WS, "registers", "deceased_cache.json")):
        if not p or not os.path.exists(p): continue
        try:
            for k, v in json.load(open(p)).items():
                d = iso(v.get("dod")) if isinstance(v, dict) else None
                if d and k not in out: out[k] = d
        except Exception: pass
    return out
DEC = deceased()

def charge_rec(c):
    a_ = {k: v for k, v in c.attrib.items() if k not in ("patientname", "name", "subscribername", "respname")}
    a_["payments"] = [{k: v for k, v in p.attrib.items() if k not in ("patientname", "name")} | {"reasons": [(r.get("code", ""), r.get("amount", "")) for r in p.iter("payreason")]} for p in c.iter("payment")]
    a_["writeoffs"] = [dict(w.attrib) for w in c.iter("writeoff")]
    return a_

def read_chart(pid, vids):
    root = txh.fetch(pid)
    charges = [charge_rec(c) for c in root.iter("charge")]
    have = {num(c.get("visit") or c.get("visitid")) for c in charges}
    for v in [v for v in vids if v not in have]:
        try: charges += [charge_rec(c) for c in txh.fetch_visit(pid, v).iter("charge")]
        except Exception: pass
    x = amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"}))
    r2 = ET.fromstring(x.encode("latin-1", "ignore")); p = r2.find(".//patient")
    plans = [{"code": CAR.get(i.get("carrier"), i.get("carrier")), "seq": i.get("sequence"), "begin": mdy(i.get("begindate")), "end": mdy(i.get("enddate"))} for i in r2.iter("insplan")]
    return charges, plans, (p.get("deceased") if p is not None else "")

def decide(r, charges, plans, dod):
    carrier = (r.get("carriercode") or "NONE").strip() or "NONE"
    bal = round(f(r.get("insbalance")), 2); dos = iso(r.get("dateofservice")); vid = str(r["visitid"]); pid = str(r["patientid"])
    charges = [c for c in charges if num(c.get("visit") or c.get("visitid")) == vid and c.get("void") != "1"]
    cpts = sorted({c.get("proccode", "") for c in charges})
    mods = sorted({(c.get("modcodes") or c.get("modifiers") or "").strip() for c in charges} - {""})
    bill_dates = [mdy(c.get("billdate")) for c in charges if mdy(c.get("billdate")) and str(c.get("proccode") or "").strip().upper() not in REPORTING]      # a reporting line's bill date is not the visit's (confirm review NH2-6): billed later, it would hide the visit's own denial
    last_sent = max(bill_dates) if bill_dates else None
    pays = [p for c in charges if str(c.get("proccode") or "").strip().upper() not in REPORTING for p in c.get("payments", []) if p.get("void") != "1"]      # a reporting line's payments are not the visit's
    real_pays = [p for p in pays if abs(f(p.get("amount"))) > 0.005]
    zero_pays = [p for p in pays if abs(f(p.get("amount"))) <= 0.005]
    zero_denials = [p for p in zero_pays if p.get("reasons")]
    pr_only_zero = [p for p in zero_denials if all(group(code) == "PR" and norm(code) in ("1", "2", "3") for code, amt in p.get("reasons", []))]
    denial_codes = sorted({norm(code) for p in zero_denials if p not in pr_only_zero for code, amt in p.get("reasons", []) if norm(code) not in INFO_REASONS})
    last_denial = max([mdy(p.get("date")) for p in zero_denials if mdy(p.get("date"))] or [None], key=lambda d: d or datetime.date.min)
    first_real = min([mdy(p.get("date")) for p in real_pays if mdy(p.get("date"))] or [None], key=lambda d: d or datetime.date.max)
    primary_paid_by = sorted({p.get("carrier", "") for p in real_pays})
    pr_left = round(sum(f(amt) for p in real_pays + pr_only_zero for code, amt in p.get("reasons", []) if group(code) == "PR"), 2)
    days_sent = (TODAY - last_sent).days if last_sent else None
    days_dos = (TODAY - dos).days if dos else None
    secondary = bool(real_pays) and (carrier not in primary_paid_by)
    settled_primary = (bool(real_pays) and carrier in primary_paid_by) or (bool(pr_only_zero) and not real_pays and carrier in {p.get("carrier") for p in pr_only_zero})
    is_ccm = bool(set(cpts) & CCM); has_gv = any("GV" in m.upper() for m in mods)
    live_secondary = []
    if dos:
        for pl in plans:
            if pl["code"] in primary_paid_by or pl["code"] == carrier: continue
            if pl["end"] and pl["end"] < dos: continue
            if pl["begin"] and pl["begin"] > dos + datetime.timedelta(days=400): continue
            live_secondary.append(pl["code"])
    live_secondary = sorted(set(live_secondary))
    b = bucket(days_sent); why = []; rec_ = "WAIT"; rule = ""
    if not charges:
        rec_, rule, why = "REVIEW", "chart history not readable this run", ["chart history not readable this run - read it before acting"]
    elif dod and dos and dos > dod:
        rec_, rule, why = "WRITE OFF", "DOS after the Medicare date of death -> void, never bill", ["date of service is AFTER the date of death on Medicare's record (%s) - void/write off, never bill" % dod.isoformat()]
    elif is_ccm and carrier == "MCAD":
        rec_, rule, why = "WRITE OFF", "CCM to straight Medicaid is never paid -> WONCS (10/13 rule)", ["CCM to straight Medicaid is never paid (10/13 rule) -> WONCS"]
    elif is_ccm and not real_pays and ("B9" in denial_codes or (has_gv and denial_codes and last_denial and (not last_sent or last_sent <= last_denial))):
        rec_, rule, why = "WRITE OFF", "CCM denied on a hospice patient (GV / CO-B9) -> WONCS, no appeal (10/15 rule)", ["CCM denied on a hospice patient (%s%s) -> WONCS, no appeal (10/15 rule)" % ("GV, " if has_gv else "", ",".join(denial_codes) or "B9")]
    elif settled_primary:
        primrose_age = (TODAY - first_real).days if first_real else ((TODAY - last_denial).days if last_denial else None)
        contractual_left = round(max(0.0, bal - pr_left), 2) if real_pays else 0.0
        extra = " + WOINS contractual $%.2f (unwritten adjustment)" % contractual_left if contractual_left > 0.01 else ""
        cs = min(bal, pr_left) if pr_left else bal
        if live_secondary and (primrose_age is None or primrose_age <= 365):
            rec_, rule = "CORRECT & RESEND", "primary paid - cost-share belongs to the live secondary on the chart: move it there and bill"
            why = ["primary paid - cost-share $%.2f belongs to the chart's secondary %s: move it there and bill%s" % (cs, "/".join(live_secondary), extra)]
        elif live_secondary:
            rec_, rule = "WRITE OFF", "primary paid > 12 months ago, the secondary's window is closed -> WOCLTREQ"
            why = ["primary paid %d days ago; secondary %s window closed -> WOCLTREQ $%.2f%s" % (primrose_age, "/".join(live_secondary), cs, extra)]
        else:
            code = "WOCAID2ND" if (set(primary_paid_by) & MEDICAID_FAMILY) else "WOCLTREQ"
            rec_, rule = "WRITE OFF", "primary paid, no secondary on the chart -> %s cost-share (10/13 rule: nothing stays on the patient)" % code
            why = ["primary paid, no secondary on the chart -> %s cost-share $%.2f%s" % (code, cs, extra)]
    elif denial_codes and last_denial and (not last_sent or last_sent <= last_denial):
        dc = ",".join(denial_codes)
        if "29" in denial_codes: rec_, rule, why = "WRITE OFF", "denied CO-29 timely filing -> WOLATE", ["denied CO-29 timely filing -> WOLATE unless proof of timely submission exists"]
        elif "B9" in denial_codes:
            if days_dos is not None and days_dos <= 365: rec_, rule, why = "CORRECT & RESEND", "hospice CO-B9 on an E/M -> rebill Medicare with GV", ["hospice CO-B9 on an E/M: rebill Medicare with GV"]
            else: rec_, rule, why = "WRITE OFF", "hospice CO-B9 and DOS > 12 months -> untimely write-off", ["hospice CO-B9 and DOS > 12 months -> untimely write-off"]
        elif set(denial_codes) & WRONG_PAYER: rec_, rule, why = "CORRECT & RESEND", "wrong-payer denial (PR27/26/200/22/204...) -> insurance cascade, re-route, never patient balance", ["wrong-payer denial (%s) -> insurance cascade (AMD 271 / Stedi), re-route, never patient balance" % ",".join(sorted(set(denial_codes) & WRONG_PAYER))]
        elif "18" in denial_codes and len(denial_codes) == 1: rec_, rule, why = "WAIT", "CO-18 duplicate - the original is in play; confirm it paid, then close", ["CO-18 duplicate - the original is in play; confirm it paid, then close (no rebill)"]
        elif is_ccm and set(denial_codes) & REDATE and days_dos is not None and days_dos <= 365: rec_, rule, why = "CORRECT & RESEND", "CO-151 frequency denial on CCM -> re-date the claim to the last day of its month, send it as an original (10/4 rule)", ["CO-151 frequency denial on CCM (%s): re-date the claim to the last day of its month and send it as an original (rules.md 10/4/2026)" % dc]
        elif set(denial_codes) & BUNDLED: rec_, rule, why = "WRITE OFF", "bundled / not paid separately (97/234/B15/236) -> contractual write-off", ["bundled / not paid separately (%s) -> contractual write-off" % dc]
        elif set(denial_codes) & CORRECTABLE: rec_, rule, why = "CORRECT & RESEND", "correctable denial (CO-16/4/11/125/181) -> fix the flagged data, rebill as an original", ["correctable denial (%s): fix the flagged data, rebill as an original" % dc]
        elif set(denial_codes) & CRED_CODES: rec_, rule, why = "CORRECT & RESEND", "credentialing / enrollment denial (242/243/185/B7) -> fix enrollment or write off", ["credentialing/enrollment denial (%s) - fix enrollment or write off" % dc]
        elif set(denial_codes) & NONCOVERED:
            rec_ = "WRITE OFF" if days_dos and days_dos > 365 else "CORRECT & RESEND"
            rule = "non-covered / medical-necessity / frequency denial (96/50/A1/151/119) -> read the RARC; appeal or write off" + (" (DOS > 12 months)" if rec_ == "WRITE OFF" else "")
            why = ["non-covered / medical-necessity / frequency denial (%s): review the RARC; appeal or write off" % dc]
        else: rec_, rule, why = "CORRECT & RESEND", "denied, nothing sent since -> triage the CARC", ["denied (%s) with nothing sent since - triage the CARC" % dc]
    elif secondary:
        primrose_age = (TODAY - first_real).days if first_real else None
        if primrose_age is not None and primrose_age > 365: rec_, rule, why = "WRITE OFF", "secondary balance, primary remit > 12 months old -> WOCLTREQ / WOINS", ["secondary / cost-share balance; primary remit %d days old (> 12 months) -> WOCLTREQ / WOINS" % primrose_age]
        elif days_sent is None: rec_, rule, why = "CORRECT & RESEND", "secondary never sent after the primary paid -> bill it now", ["secondary never sent; primary paid %s -> bill the secondary now" % (first_real.isoformat() if first_real else "?")]
        elif days_sent <= 60: rec_, rule, why = "WAIT", "secondary claim sent within 60 days", ["secondary claim sent %d days ago" % days_sent]
        else: rec_, rule, why = "CORRECT & RESEND", "secondary unanswered > 60 days -> check status, resend as original (verify the plan first)", ["secondary unanswered %d days: check status, resend as original (verify the plan is live first)" % days_sent]
    elif days_dos is not None and days_dos > 365 and not real_pays:
        rec_, rule = "WRITE OFF", "primary unpaid > 12 months from DOS, no adjudication -> WOINS untimely (dated note)"
        why = ["primary claim unpaid > 12 months from DOS, no adjudication on file -> WOINS untimely (dated note)%s" % (" - backlog payer: pull the 277 / ConnectCenter first" if carrier in BACKLOG else "")]
    elif days_sent is None: rec_, rule, why = "CORRECT & RESEND", "no bill date on the charges - the claim never went out -> send it", ["no bill date on the charges - the claim never went out; send it"]
    elif b == "0-30": rec_, rule, why = "WAIT", "sent 0-30 days ago - inside normal adjudication", ["sent %d days ago - inside normal adjudication" % days_sent]
    elif b == "31-60":
        rec_, rule = "WAIT", "sent 31-60 days ago - watch" + (" (ERA-backlog payer: never auto-rebilled)" if carrier in BACKLOG else " (277 status if still silent at 60)")
        why = ["sent %d days ago - watch; %s" % (days_sent, "ERA-backlog payer, do not rebill" if carrier in BACKLOG else "check 277 status if still silent at 60")]
    elif b == "61-90":
        if carrier in BACKLOG: rec_, rule, why = "WAIT", "sent 61-90 days ago to a backlog payer -> pull the 277 before any rebill", ["sent %d days ago, no answer: backlog payer - pull the 277 before any rebill" % days_sent]
        else: rec_, rule, why = "CORRECT & RESEND", "sent 61-90 days ago, no answer -> claim-status check; no record at the payer = resend as original", ["sent %d days ago, no answer: claim-status check; no record at the payer -> resend as original" % days_sent]
    elif b == "91-120": rec_, rule, why = "CORRECT & RESEND", "sent 91-120 days ago, no answer -> verify the plan, fix and resend as original", ["sent %d days ago, no answer - verify the plan, fix and resend as original" % days_sent]
    else:
        rec_, rule = "CORRECT & RESEND", "sent > 120 days ago, no adjudication on file (10/13 rule) -> " + ("277 / ConnectCenter check, then resend or write off" if carrier in BACKLOG else "verify the plan, fix and resend as original")
        why = ["sent %d days ago, no adjudication on file (10/13 rule) - %s" % (days_sent, "backlog payer: 277 / ConnectCenter check, then resend or write off" if carrier in BACKLOG else "verify the plan, fix and resend as original")]
    return {"pid": pid, "visitid": vid, "dos": dos.isoformat() if dos else "", "cpts": " ".join(cpts), "mods": " ".join(mods), "fee": round(f(r.get("totalvisitamount")), 2), "bal": bal,
            "payer": carrier, "sent": last_sent.isoformat() if last_sent else "", "days_sent": days_sent, "b_sent": b, "days_dos": days_dos, "b_dos": bucket(days_dos),
            "paid_by": " ".join(primary_paid_by), "paid_on": first_real.isoformat() if first_real else "", "secondary": " ".join(live_secondary), "pr": pr_left,
            "carcs": " ".join(denial_codes), "denied": last_denial.isoformat() if last_denial else "", "dod": dod.isoformat() if dod else "", "rec": rec_, "rule": rule, "why": "; ".join(why)}

def read_chart_offline(pid, suffix):
    base = os.path.join(WS, "patient_db", pid)
    t = json.load(open(os.path.join(base, "txh_%s.json" % suffix)))
    charges = [{k: v for k, v in c.items() if k not in ("patient", "patientname", "resppartyname", "name")} for c in t.get("charges", [])]
    for c in charges:
        c["payments"] = [{k: v for k, v in p.items() if k not in ("patient", "patientname", "name")} for p in c.get("payments", [])]
    pl = json.load(open(os.path.join(base, "plans_%s.json" % suffix)))
    plans = [{"code": CAR.get(i.get("carrier"), i.get("carrier")), "seq": i.get("sequence"), "begin": mdy(i.get("begindate")), "end": mdy(i.get("enddate"))} for i in pl.get("plans", [])]
    return charges, plans, pl.get("deceased", "")

def save_payments(charts):
    """11/27/2026: the payer tracker (run_alerts.py, amd.payer_tracker) counts only REAL insurance dollars - AdvancedMD logs a $0 write-off
    post as 'Payment received' too. Every insurance payment on the charts read tonight (amount > 0, not void) is upserted into the practice
    database (amd.insurance_payments: payment id, visit, charge, carrier, date, amount, check number - ids and dollars, no names), so the
    tracker sees paper-check payers paying. Never fails the ageing run: a database that does not answer is reported in one line."""
    rows = []
    for pid, (charges, _pl, _d) in charges_by_chart(charts):
        for c in charges:
            for p_ in c.get("payments") or []:
                amt = -f(p_.get("amount")); d_ = mdy(p_.get("date"))
                if p_.get("void") == "1" or str(p_.get("source")) != "2" or amt <= 0.005 or not p_.get("id"): continue
                rows.append({"payment_id": str(p_["id"]), "visit_id": num(c.get("visit") or c.get("visitid")) or None, "charge_id": str(c.get("id") or ""),
                             "carrier": (p_.get("carrier") or "").strip() or None, "payment_date": d_.isoformat() if d_ else None,
                             "posted_at": (p_.get("createtime") or None), "paid": round(amt, 2), "check_number": p_.get("checknumber") or None})
    if not rows: return "payments: none to save"
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "credentialing"))
        saved = sys.argv[:]; sys.argv = sys.argv[:1]
        try: import cred_vault
        finally: sys.argv = saved
        d = cred_vault.DB()
        for i in range(0, len(rows), 1500):
            d.q("""insert into amd.insurance_payments (payment_id, visit_id, charge_id, carrier, payment_date, posted_at, paid, check_number, source_note)
                   select payment_id, visit_id, charge_id, carrier, payment_date, posted_at, paid, check_number, 'aging refresh'
                   from jsonb_to_recordset(%s::jsonb) as x(payment_id text, visit_id bigint, charge_id text, carrier text, payment_date date,
                        posted_at timestamp, paid numeric, check_number text)
                   on conflict (payment_id) do nothing""", [json.dumps(rows[i:i + 1500])])
        return "payments: %d insurance payments on the charts read, saved to the practice database" % len(rows)
    except BaseException as e:          # cred_vault exits on a refused statement - the ageing file still gets written
        return "payments: not saved (%s)" % (str(e)[:120] or type(e).__name__)


def charges_by_chart(charts):
    for pid, v in charts.items():
        if isinstance(v, tuple) and v: yield pid, (v[0], v[1] if len(v) > 1 else [], v[2] if len(v) > 2 else "")


def leftover_rows(seen):
    """11/27/2026 (William: "find the problem that missed rebilling the secondaries and fix that for ongoing"): AdvancedMD's unpaid list
    (massrebillsearch) drops a visit once ANY payer has paid on it, so the balance left on the SECONDARY after Medicare paid never reached
    this file, the work queue or the claim status - 1,761 visits / $56K sat unseen (old_balances_dry.py, 11/27). The Mass Write-off search
    lists every charge that still carries an INSURANCE balance; asked per carrier (one answer stops at 5,000 charges), every visit it holds
    that the unpaid list lacks joins the rows, in the unpaid list's shape, under the carrier that HOLDS the balance - decide() then files it
    by the standing rules (a secondary never sent -> bill it; sent and unanswered past 60 days -> status / resend; remit > 12 months ->
    write-off) and the work queue's guards still refuse a second claim to a secondary that already holds the crossover.
    -> (rows, one-line note). Read-only; a carrier that does not answer is skipped and counted."""
    try: car = json.load(open(os.path.join(WS, "carriers.json")))
    except (OSError, ValueError): return [], "leftovers skipped: carriers.json unreadable"
    ids = sorted({int(d) for d in (re.sub(r"\D", "", str(k)) for k in car) if d})
    by, failed = {}, 0
    for cid in ids:
        try:
            j = requests.post(era_post.API + "/masswriteoff/masswriteoffsearch", headers=era_post.H(), timeout=240,
                              json={"carrierids": [cid], "isinsbalance": True, "billstartdate": None, "billenddate": None}).json()
        except Exception:
            failed += 1; continue
        for x in (j.get("chargedetails") or []) if isinstance(j, dict) else []:
            vid = str(x.get("visitid") or ""); bal = f(x.get("insbalance"))
            if not vid or vid in seen or bal <= 0.005: continue
            r = by.setdefault(vid, {"patientid": x.get("patientid"), "visitid": x.get("visitid"), "carriercode": (x.get("carriercode") or "").strip(),
                                    "insbalance": 0.0, "dateofservice": x.get("dateofservice"), "source": "masswriteoffsearch"})
            r["insbalance"] = round(r["insbalance"] + bal, 2)
        time.sleep(0.2)
    return list(by.values()), "%d visits with an insurance balance the unpaid list leaves out (Mass Write-off search, %d of %d carriers answered)" % (
        len(by), len(ids) - failed, len(ids))

def main():
    if OFFLINE:
        unp = json.load(open(OFFLINE[0]))
    else:
        amd.login_cached()
        unp = requests.post(era_post.API + "/claim/massrebillsearch", headers=era_post.H(), json={}, timeout=240).json()
    rows = unp if isinstance(unp, list) else (unp.get("data") or unp.get("rows") or [])
    rows = [r for r in rows if isinstance(r, dict)]
    leftover_note = ""
    if not OFFLINE and "--no-leftovers" not in sys.argv:
        extra, leftover_note = leftover_rows({str(r.get("visitid")) for r in rows})
        rows += extra
    by_pid = collections.defaultdict(list)
    for r in rows: by_pid[str(r["patientid"])].append(str(r["visitid"]))
    pids = sorted(by_pid, key=int)[:MAXP]
    charts = {}; lock = threading.Lock(); q = list(pids); errors = []
    def worker():
        while True:
            with lock:
                if not q: return
                pid = q.pop(0)
            try: charts[pid] = read_chart_offline(pid, OFFLINE[1]) if OFFLINE else read_chart(pid, by_pid[pid])
            except Exception as e:
                with lock: errors.append("pat%s: %s" % (pid, str(e)[:80]))
            if not OFFLINE: time.sleep(0.2)
    ts = [threading.Thread(target=worker, daemon=True) for _ in range(NT)]; [t.start() for t in ts]; [t.join() for t in ts]
    pay_note = save_payments(charts) if not OFFLINE else ""
    out = []
    for r in rows:
        pid = str(r["patientid"])
        ch, pl, dflag = charts.get(pid, ([], [], ""))
        dod = DEC.get(pid)
        out.append(decide(r, ch, pl, dod))
    def tbl(key):
        t = collections.OrderedDict()
        for v in out:
            d = t.setdefault(v[key], {"n": 0, "amt": 0.0, "b": collections.OrderedDict((x, [0, 0.0]) for x in ("0-30", "31-60", "61-90", "91-120", "over 120", "unknown")), "r": collections.OrderedDict((x, [0, 0.0]) for x in ("WAIT", "CORRECT & RESEND", "WRITE OFF", "REVIEW"))})
            d["n"] += 1; d["amt"] += v["bal"]; d["b"][v["b_sent"]][0] += 1; d["b"][v["b_sent"]][1] += v["bal"]; d["r"][v["rec"]][0] += 1; d["r"][v["rec"]][1] += v["bal"]
        for d in t.values():
            d["amt"] = round(d["amt"], 2)
            for x in d["b"].values(): x[1] = round(x[1], 2)
            for x in d["r"].values(): x[1] = round(x[1], 2)
        return collections.OrderedDict(sorted(t.items(), key=lambda kv: -kv[1]["amt"]))
    reasons = collections.defaultdict(lambda: [0, 0.0])
    for v in out:
        k = v["rec"] + " | " + v["rule"]
        reasons[k][0] += 1; reasons[k][1] += v["bal"]
    bk = lambda key, vals: {b: {"n": sum(1 for v in out if v[key] == b), "amt": round(sum(v["bal"] for v in out if v[key] == b), 2)} for b in vals}
    snap = {"schema": "ar-aging/1", "asof": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "today": TODAY.isoformat(),
            "source": ("saved AMD reads of %s (unpaid list + chart histories + plans)" % OFFLINE[1]) if OFFLINE else "AMD live (massrebillsearch + gettxhistory + getdemographic) - Billing Button aging step",
            "visits": len(out), "leftovers": leftover_note, "patients": len(by_pid), "total": round(sum(v["bal"] for v in out), 2), "charts_read": len(charts), "errors": errors[:20],
            "by_bucket_sent": bk("b_sent", ("0-30", "31-60", "61-90", "91-120", "over 120", "unknown")), "by_bucket_dos": bk("b_dos", ("0-30", "31-60", "61-90", "91-120", "over 120", "unknown")),
            "by_rec": bk("rec", ("WAIT", "CORRECT & RESEND", "WRITE OFF", "REVIEW")), "by_payer": tbl("payer"),
            "by_rec_reason": collections.OrderedDict(sorted(((k, {"n": v[0], "amt": round(v[1], 2)}) for k, v in reasons.items()), key=lambda kv: -kv[1]["amt"])),
            "rows": sorted(out, key=lambda v: ({"CORRECT & RESEND": 0, "WRITE OFF": 1, "WAIT": 2}.get(v["rec"], 3), -v["bal"]))}
    json.dump(snap, open(OUT, "w"))
    print("aging: %d visits / %d patients / $%.2f -> WAIT $%.2f / RESEND $%.2f / WRITE OFF $%.2f (charts read %d, errors %d) -> %s" % (
        snap["visits"], snap["patients"], snap["total"], snap["by_rec"]["WAIT"]["amt"], snap["by_rec"]["CORRECT & RESEND"]["amt"], snap["by_rec"]["WRITE OFF"]["amt"], len(charts), len(errors), OUT))
    if leftover_note: print("aging: " + leftover_note)
    if pay_note: print("aging: " + pay_note)

if __name__ == "__main__":
    main()
