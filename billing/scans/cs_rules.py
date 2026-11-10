# PLAIN ENGLISH (claim-status rules - look-ups part A, step 2, 11/10/2026)
# Decides: WHICH unpaid claims get a paid claim-status check (Stedi 276/277), how the payer's answer is read, and when a claim is asked
#   again, waits, or is handed to a person. William 11/10/2026: "get a better deal on all the look ups for that that we will need".
#   October 2026: 6,770 checks ($889.50) - four in five changed nothing, the same pending claims were asked up to 199 times, and a check
#   was bought for claims with a payment or a denial already posted (the claim-status reader, 11/10/2026).
# Rules it uses (the tables just below; every helper that buys a claim-status check asks through these rules):
#   - THE LEDGER: one row per claim and payer in practices/ehpa/registers/claim_status_ledger.json (in the workspace registers/...;
#     claim, visit and chart numbers only, never a name): the last answer, the day asked, the tries, the day the claim was last sent,
#     final or not, and the month's counters. A FINAL answer (paid, denied, finalized at $0) is recorded only when the answer names this
#     claim (the account number the payer echoes = the visit id + claim letter, or the payer's claim number) or was asked with the exact
#     date of service - the lesson of 10/9/2026: a 3-day window can answer for the next day's claim. A missing ledger is an error and
#     nothing is asked (the very first run is started with --new-ledger); a ledger that cannot be read is never treated as empty.
#   - BY NEED, NOT BY SIZE: a claim is due when nothing is posted for its payer (or it was sent again after that answer), it was last sent
#     45 or more days ago (60 for a secondary balance), it is less than a year old, its payer has a working route, and the ledger says
#     neither wait nor stop - worked out from the same night's ageing file (aging_latest.json, written by aging_refresh.py). An ageing
#     file that is missing or older than one day ends the run with an error and no call - never a fall-back to the largest balances.
#   - WAITS, STOP AND HAND OFF, PAYERS THAT DO NOT WORK, CAPS: the tables below. Two answers in a row with no usable content, or three
#     'pending' answers in a row, end the asking: the claim goes on the hand-off list ("ask the payer by portal or phone") until it is
#     sent again or a person clears its row (python3 cs_rules.py --clear <visit id>).
#   - READING THE ANSWER: paid / finalized at $0 / denied / pending / not found (may be resent, as before) / no electronic answer (the
#     payer cannot give the status electronically: stop and hand off) / not matched (date of service, member id, too many matches: ONE
#     more check with the exact date; not matched again = stop and hand off) / not eligible on that date (a coverage problem: the
#     insurance check, never a resend) / no usable answer. A wording the table does not know is 'no usable answer' and is printed.
# Never touches: AdvancedMD, the vendor, the network. It reads the ageing file, reads and writes the ledger (one file, written in one
#   step: a temporary file renamed into place), and keeps an unusable raw reply under patient_db/ (never in git). What is DONE with an
#   answer (post, write off, resend, denial work) stays with the standing helpers and the runbook.
import os, re, sys, json, datetime, tempfile, argparse, collections
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path: sys.path.append(HERE)
import stedi_prices                                        # the one price table (look-ups part A, step 1) - the caps are priced with it

# ---- WAITS: days before a claim is asked again, by its last answer (spec 9.3) ----------------------------------------------------------
WAITS = {
    "pending":                   14,   # answer 'pending' and the claim last sent under 120 days ago
    "pending, sent 120+ days":   30,   # answer 'pending' and the claim last sent 120 or more days ago
    "near the filing limit":      7,   # the claim's filing limit is within 30 days: 7 days instead of 14 or 30 for a 'pending' answer
    "no usable answer":           7,   # an empty reply, an unreadable reply, a failed call, the payer cannot answer now, an unknown wording
    "not found":                 30,   # no second check until the claim has been SENT AGAIN and this many days have passed since that send
    "not eligible":              30,   # (the spec is silent) the same as 'not found': a coverage problem is fixed by sending the claim again
    "a year old":              None,   # a claim a year old or more: no check at all (a secondary balance counts from the primary's remit)
}
OLD_PENDING_DAYS = 120                 # 'pending' on a claim last sent this many days ago or more -> the longer wait
NEAR_LIMIT_DAYS = 30                   # 'near the filing limit' = the limit is this many days away or fewer
YEAR_DAYS = 365                        # 'a year old'
NEED_DAYS = {"primary": 45, "secondary": 60}   # days since the claim was last sent before it is due at all (spec 9.2)
# filing limit per payer code, in days (rules.md: a PRIMARY claim more than 12 months from the date of service is written off for any
# carrier; a SECONDARY balance is timely from the primary's remit, never the date of service). No payer has a different limit on file.
FILING_LIMIT_DAYS = {"default": 365, "secondary": 365}
STOP_AFTER = {"no usable answer": 2, "pending": 3}   # answers in a row that end the asking (spec 9.4)
PAYER_RUN_STOP = 5                     # unusable answers in a row from one payer end that payer for the rest of the run (spec 9.5)
CAPS = {"run checks": 150, "run dollars": 25.00, "month checks": 400, "month dollars": 100.00}   # spec 9.6, priced with stedi_prices.py
HISTORY = 8                            # answers kept per ledger row (day, label)

# ---- PAYERS WHOSE CLAIM STATUS DOES NOT WORK (spec 9.5) - beside the payer map (precheck.CAR2STEDI, which the helpers pass in) -------------
# payer code -> (date switched off, reason). Such claims are never sent: they are listed for portal or phone. Switch one on again by
# deleting its line when vendor support says it works (test one claim first).
CS_OFF = {
    "TRI00": ("2026-11-10", "military plan: 26 of 26 checks on 10/13/2026 gave an empty reply"),
    "TRI05": ("2026-11-10", "military plan: 26 of 26 checks on 10/13/2026 gave an empty reply"),
    "AAR01": ("2026-11-10", "Medigap plan: 2 of 2 checks in October 2026 gave an empty reply"),
}
# NOT switched off: AET07, the commercial plan the vendor named - 1 failure in 64 checks in October 2026.
CS_NO_ROUTE = {"FLO02": "Medicare offers no claim-status check through the vendor", "RET01": "Medicare offers no claim-status check through the vendor",
               "VACCN": "VA community care offers no claim-status check through the vendor"}   # from sweep_full.py (9/6/2026)
CS_ROUTE_EXTRA = {"BCBS1": "BCBSF"}    # payer codes the eligibility map lacks but claim status can reach (from sweep_full.py, 9/6/2026)

# ---- the labels (spec 9.8) ------------------------------------------------------------------------------------------------------------
PAID, FINAL0, DENIED = "paid", "finalized at $0", "denied"
PENDING, NOT_FOUND, NO_ELECTRONIC, NOT_MATCHED, NOT_ELIGIBLE, UNUSABLE = "pending", "not found", "no electronic answer", "not matched", "not eligible", "no usable answer"
FINAL = (PAID, FINAL0, DENIED)
PAID_CATS = {"F0", "F1"}                                        # finalized / finalized with payment: paid when money is shown, else $0
FINAL_CATS = {"F0", "F1", "F2", "F3", "F3F", "F3N", "F4"}       # F2 denial, F3 revised, F4 complete with no payment = denied
PENDING_CATS = {"A0", "A1", "A2", "A5", "P0", "P1", "P2", "P3", "P4", "P5"}
DOWN_CATS = {"E1", "E2"}                                        # the payer's system cannot answer now (the vendor's troubleshooting page)
NOT_ELIGIBLE_CODES = {"88", "97"}                               # not eligible for the dates of service / eligibility not found
NOT_MATCHED_CODES = {"187": "date of service", "33": "member id", "153": "member id", "485": "too many matches"}
NOT_FOUND_CODES = {"35"}                                        # claim/encounter not found
NO_ELECTRONIC_CODES = {"0"}                                     # cannot provide further status electronically
NOT_BILLED_CODES = {"484", "494", "667", "689"}                 # the vendor does not bill an answer that holds only these

class AgingError(Exception): pass
class LedgerMissing(Exception): pass
class LedgerBroken(Exception): pass
class LedgerWriteError(Exception): pass

def _date(s):
    try: return datetime.date.fromisoformat(str(s or "")[:10])
    except ValueError: return None
def _money(x):
    try: return round(float(x or 0), 2)
    except (TypeError, ValueError): return 0.0
def key(r):
    """The ledger key of an ageing row: one row per claim (visit) and payer."""
    return "%s|%s" % (re.sub(r"\D", "", str(r.get("visitid") or r.get("vid") or "")), str(r.get("payer") or "").strip())

# ---- reading one answer (spec 9.8) ----------------------------------------------------------------------------------------------------
def _line(s, service=None):
    return {"cat": str(s.get("statusCategoryCode") or "").strip().upper(), "catv": str(s.get("statusCategoryCodeValue") or "")[:90], "code": str(s.get("statusCode") or "").strip(),
            "codev": str(s.get("statusCodeValue") or "")[:90], "paid": s.get("amountPaid") if s.get("amountPaid") is not None else (service or {}).get("amountPaid"),
            "check": s.get("checkNumber"), "paidDate": s.get("paidDate") or s.get("checkIssueDate") or s.get("effectiveDate"), "payerClaim": s.get("tradingPartnerClaimNumber")}
def claims_of(j):
    """Every claim in a 277 answer: its status lines and the ids the payer echoes (account number, payer's claim number, service date)."""
    out = []
    for c in (j.get("claims") or []) if isinstance(j, dict) else []:
        if not isinstance(c, dict): continue
        cs = c.get("claimStatus") or c; cs = cs if isinstance(cs, list) else [cs]
        lines = [_line(s) for s in cs if isinstance(s, dict) and s.get("statusCategoryCode")]
        if not lines:                                                   # no claim-level status: the service lines' statuses
            for d in c.get("serviceDetails") or []:
                for s in (d or {}).get("status") or []:
                    if isinstance(s, dict) and s.get("statusCategoryCode"): lines.append(_line(s, (d or {}).get("service")))
        top = next((s for s in cs if isinstance(s, dict)), {})
        out.append({"lines": lines, "acct": str(top.get("patientAccountNumber") or c.get("patientAccountNumber") or ""),
                    "pccn": str(top.get("tradingPartnerClaimNumber") or ""), "svc": str(top.get("claimServiceDate") or top.get("serviceDate") or "")})
    if not out and isinstance(j, dict):
        cs = j.get("claimStatus") or []; cs = cs if isinstance(cs, list) else [cs]
        lines = [_line(s) for s in cs if isinstance(s, dict) and s.get("statusCategoryCode")]
        if lines:
            top = next((s for s in cs if isinstance(s, dict)), {})
            out.append({"lines": lines, "acct": str(top.get("patientAccountNumber") or ""), "pccn": str(top.get("tradingPartnerClaimNumber") or ""), "svc": str(top.get("claimServiceDate") or "")})
    return out
def _digits(s):
    m = re.search(r"\d+", str(s or "")); return m.group(0).lstrip("0") if m else ""
def names_claim(c, vid=None, icn=None):
    """True when a claim in the answer names OUR claim: the account number the payer echoes starts with the visit id (AMD sends the visit
    id + the claim letter), or the payer's claim number is the one on file for the visit."""
    v = _digits(vid)
    if v and _digits(c.get("acct")) == v: return True
    norm = lambda x: re.sub(r"\W", "", str(x or "")).upper()
    return bool(icn) and bool(c.get("pccn")) and norm(c["pccn"]) == norm(icn)
def _same_day(c, dos):
    d = re.sub(r"\D", "", str(dos or ""))[:8]; s = [re.sub(r"\D", "", x) for x in str(c.get("svc") or "").split("-")]
    return bool(d) and bool(s[0]) and all(x == d for x in s if x)
def _amount(x):
    try: return float(x or 0)
    except (TypeError, ValueError): return 0.0
def payments(lines):
    """The payments in a set of status lines, each counted once per (check number, paid date, amount) - the lesson of 10/9/2026."""
    seen = collections.OrderedDict()
    for l in lines:
        a = _amount(l.get("paid"))
        if l.get("cat") in PAID_CATS and a > 0: seen.setdefault((str(l.get("check") or ""), str(l.get("paidDate") or ""), "%.2f" % a), l)
    return [{"check": k[0], "date": k[1], "amount": float(k[2]), "payerClaim": l.get("payerClaim")} for k, l in seen.items()]
def label_lines(lines):
    """The reading of a set of status lines (spec 9.8) -> (label, why). Order: final, pending, the payer cannot answer now, not eligible,
    not matched, not found, no electronic answer; anything else is 'no usable answer' (its wording is printed in the run report)."""
    cats = {str(l.get("cat") or "").strip().upper() for l in lines} - {""}
    codes = {str(l.get("code") or "").strip() for l in lines} - {""}
    words = " | ".join(str(l.get("codev") or "") for l in lines).lower()
    if cats & PAID_CATS:
        paid = sum(p["amount"] for p in payments(lines))
        return (PAID, "paid $%.2f" % paid) if paid > 0 else (FINAL0, "finalized, nothing paid")
    if cats & FINAL_CATS: return DENIED, "denied or revised"
    if cats & PENDING_CATS: return PENDING, "pending at the payer"
    if cats and cats <= DOWN_CATS: return UNUSABLE, "the payer cannot answer now"
    if codes & NOT_ELIGIBLE_CODES or "not eligible" in words or "eligibility not found" in words: return NOT_ELIGIBLE, "not eligible on the date of service"
    nm = sorted({NOT_MATCHED_CODES[c] for c in codes if c in NOT_MATCHED_CODES})
    if nm: return NOT_MATCHED, " / ".join(nm) + " not matched"
    if codes & NOT_FOUND_CODES or "claim/encounter not found" in words: return NOT_FOUND, "claim not found at the payer"
    if codes & NO_ELECTRONIC_CODES or "cannot provide further status electronically" in words: return NO_ELECTRONIC, "the payer cannot give the status electronically"
    if codes and codes <= NOT_BILLED_CODES: return UNUSABLE, "the payer does not take claim-status checks or the vendor could not route it"
    return UNUSABLE, "a wording the rules do not know"
def _decisive(lines, lab):
    group = {PAID: PAID_CATS, FINAL0: PAID_CATS, DENIED: FINAL_CATS - PAID_CATS, PENDING: PENDING_CATS, UNUSABLE: DOWN_CATS}.get(lab)
    codes = {NOT_ELIGIBLE: NOT_ELIGIBLE_CODES, NOT_MATCHED: set(NOT_MATCHED_CODES), NOT_FOUND: NOT_FOUND_CODES, NO_ELECTRONIC: NO_ELECTRONIC_CODES}.get(lab)
    for l in lines:
        if (group and l.get("cat") in group) or (codes and l.get("code") in codes): return "%s/%s" % (l.get("cat"), l.get("code"))
    return "%s/%s" % (lines[0].get("cat"), lines[0].get("code")) if lines else ""
def errors_of(j):
    return ["%s %s" % (e.get("code", ""), e.get("description", "")) for e in (j.get("errors") or []) if isinstance(e, dict)] if isinstance(j, dict) else []
def label(answer, http=None, error=None, vid=None, dos=None, exact=False, icn=None):
    """Read ONE claim-status answer for one claim -> dict: label, why, status (category/code), http, exact, named, final, lines, payments,
    paid, errors, unknown (wordings the rules do not know). final = a final label AND (the answer names this claim OR it was asked with
    the exact date). When the answer holds several claims (a 3-day window), only the claims that name ours are read; with none named, the
    claims on the date of service, else all."""
    res = {"label": UNUSABLE, "why": "", "status": "", "http": http, "exact": bool(exact), "named": False, "final": False, "lines": [], "payments": [], "paid": 0.0, "errors": [], "unknown": []}
    if error is not None:
        res["why"] = "the call failed (%s)" % str(error)[:60]; return res
    try: failed = http is not None and int(http) >= 400
    except (TypeError, ValueError): failed = False
    if failed:
        res["why"] = "the call failed (http %s - not billed)" % http; res["errors"] = errors_of(answer); return res
    if not isinstance(answer, dict):
        res["why"] = "reply not readable"; return res
    res["errors"] = errors_of(answer)
    claims = [c for c in claims_of(answer) if c["lines"]]
    if not claims:
        res["why"] = "the payer or the vendor answered with an error" if res["errors"] else "empty reply (no status, no error)"
        return res
    named = [c for c in claims if names_claim(c, vid, icn)]
    pick = named or (claims if exact else ([c for c in claims if _same_day(c, dos)] or claims))
    lines = [l for c in pick for l in c["lines"]]
    lab, why = label_lines(lines)
    res.update(label=lab, why=why, status=_decisive(lines, lab), named=bool(named), lines=lines, payments=payments(lines), accts=sorted({c["acct"] for c in pick if c["acct"]}))
    res["paid"] = round(sum(p["amount"] for p in res["payments"]), 2)
    res["final"] = lab in FINAL and (bool(exact) or bool(named))
    if lab == UNUSABLE and why.startswith("a wording"): res["unknown"] = sorted({"%s/%s %s" % (l.get("cat"), l.get("code"), l.get("codev") or "") for l in lines})
    return res

# ---- by need, from the ageing row (spec 9.2) ------------------------------------------------------------------------------------------
AGING_FIELDS = ("visitid", "pid", "payer", "dos", "sent", "bal", "paid_by", "paid_on", "carcs", "denied", "rule")
def secondary(r):
    """A secondary balance: another payer already paid this visit (the ageing row's paid_by) and the claim now sits with this payer."""
    paid_by = set(str(r.get("paid_by") or "").split()); return bool(paid_by) and str(r.get("payer") or "").strip() not in paid_by
def claim_age(r, today):
    """Days old: from the date of service; a secondary balance from the primary's remit (rules.md: timely from the primary's remit)."""
    d = (_date(r.get("paid_on")) if secondary(r) else None) or _date(r.get("dos"))
    return (today - d).days if d else None
def filing_limit(r):
    """The last day to file: 12 months from the date of service (any carrier), a secondary balance 12 months from the primary's remit."""
    if secondary(r) and _date(r.get("paid_on")): return _date(r["paid_on"]) + datetime.timedelta(days=FILING_LIMIT_DAYS["secondary"])
    d = _date(r.get("dos"))
    return d + datetime.timedelta(days=FILING_LIMIT_DAYS.get(str(r.get("payer") or "").strip(), FILING_LIMIT_DAYS["default"])) if d else None
def posted(r):
    """A payment or a denial posted for this claim's payer -> (what, the day of that answer) or ('', None). The ageing row says which
    payers PAID (paid_by); for a denial it gives the codes and the date but not the payer - a denial dated on or after the last send is
    taken as this payer's, exactly as aging_refresh.decide() does."""
    payer = str(r.get("payer") or "").strip(); paid_by = set(str(r.get("paid_by") or "").split())
    if payer and payer in paid_by: return "payment posted for this payer", _date(r.get("paid_on"))
    if str(r.get("rule") or "").startswith("primary paid"): return "payment posted for this payer (a cost-share balance is left)", _date(r.get("paid_on")) or _date(r.get("denied"))
    if str(r.get("carcs") or "").strip() and _date(r.get("denied")): return "denial posted (%s)" % str(r.get("carcs")).strip(), _date(r.get("denied"))
    return "", None
def _posted_now(r):
    what, day = posted(r); sent = _date(r.get("sent"))
    return what if what and not (sent and day and sent > day) else ""
def need(r, today):
    """Is the claim due BY NEED tonight, from its ageing row alone? -> (True, why) / (False, why)."""
    if str(r.get("rec") or "") == "REVIEW": return False, "its chart history was not read tonight"
    if _money(r.get("bal")) <= 0: return False, "no open insurance balance"
    what = _posted_now(r)
    if what: return False, what
    sent = _date(r.get("sent"))
    if not sent: return False, "never sent (no bill date on its charges)"
    age = claim_age(r, today)
    if age is None: return False, "no date of service on its row"
    if age >= YEAR_DAYS: return False, "a year old or more - no check at all"
    days = (today - sent).days; limit = NEED_DAYS["secondary" if secondary(r) else "primary"]
    if days < limit: return False, "last sent %d days ago (due at %d days)" % (days, limit)
    return True, "silent %d days since it was last sent" % days
def silent(r, today, days=60):
    """Silent: nothing posted for its payer (or sent again since) and last sent `days` or more days ago (every report prints the count)."""
    sent = _date(r.get("sent")); return not _posted_now(r) and bool(sent) and (today - sent).days >= days
def route(payer, car2stedi):
    """The vendor payer id for a claim-status check -> (payer id, '') or (None, why): switched off (CS_OFF), no route, or not mapped."""
    payer = str(payer or "").strip()
    if payer in CS_OFF: return None, "claim status does not work for %s (switched off %s: %s) - ask by portal or phone" % (payer, CS_OFF[payer][0], CS_OFF[payer][1])
    if payer in CS_NO_ROUTE: return None, CS_NO_ROUTE[payer]
    pid = CS_ROUTE_EXTRA.get(payer) or (car2stedi or {}).get(payer)
    if not pid or pid in ("MEDICARE", "UNKNOWN"): return None, "no claim-status route for %s" % (payer or "this payer")
    return pid, ""

# ---- what the ledger says (spec 9.1, 9.3, 9.4, 9.8) ---------------------------------------------------------------------------------
def wait_days(L, r, today):
    """Days to wait after the row's last answer (WAITS)."""
    if L.get("answer") == PENDING:
        lim = filing_limit(r)
        if lim and (lim - today).days <= NEAR_LIMIT_DAYS: return WAITS["near the filing limit"]
        sent = _date(r.get("sent"))
        return WAITS["pending, sent 120+ days"] if sent and (today - sent).days >= OLD_PENDING_DAYS else WAITS["pending"]
    return WAITS["no usable answer"]
def ledger_says(L, r, today):
    """May the claim be asked tonight, by its ledger row? -> (True/False, why, exact date?). A send after the row's last answer re-opens
    a final answer, a stop and a 'not found' (a 'not found' or 'not eligible' then waits 30 days from that send)."""
    if not L or not L.get("answer"):
        return True, ("re-opened by a person on %s" % L["cleared"]) if L and L.get("cleared") else "not asked before", bool(L and L.get("ask_exact"))
    ans = L.get("answer"); sent = _date(r.get("sent")); was = _date(L.get("sent")); asked = _date(L.get("asked"))
    if sent and was and sent > was:
        if ans in (NOT_FOUND, NOT_ELIGIBLE) and (today - sent).days < WAITS["not found"]:
            return False, "sent again %d days ago after '%s' - asked %d days after that send" % ((today - sent).days, ans, WAITS["not found"]), False
        return True, "sent again since its last answer ('%s')" % ans, False
    if L.get("stopped"): return False, "handed off on %s (%s) - not asked until it is sent again or a person clears its row" % (L["stopped"], L.get("stop_why") or ans), False
    if L.get("final"): return False, "final answer on file ('%s', asked %s)" % (ans, L.get("asked")), False
    if L.get("exact_next"): return True, "one check with the exact date of service is due", True
    if ans in (NOT_FOUND, NOT_ELIGIBLE): return False, "'%s' on file - asked again only after the claim is sent again" % ans, False
    if ans == NO_ELECTRONIC: return False, "the payer cannot give its status electronically - ask by portal or phone", False
    w = wait_days(L, r, today); n = (today - asked).days if asked else w
    if n < w: return False, "'%s' on %s - next check after %d days" % (ans, L.get("asked"), w), False
    return True, "'%s' on %s, %d days ago" % (ans, L.get("asked"), n), bool(L.get("ask_exact"))
def due(r, L, today, car2stedi):
    """Is this claim asked tonight? -> dict: due, why, exact, payer_id, stage ('need' / 'route' / 'ledger' / 'due')."""
    ok, why = need(r, today)
    if not ok: return {"due": False, "why": why, "exact": False, "payer_id": None, "stage": "need"}
    pid, rwhy = route(r.get("payer"), car2stedi)
    if not pid: return {"due": False, "why": rwhy, "exact": False, "payer_id": None, "stage": "route"}
    ok, lwhy, exact = ledger_says(L, r, today)
    if not ok: return {"due": False, "why": lwhy, "exact": False, "payer_id": pid, "stage": "ledger"}
    return {"due": True, "why": "%s; %s" % (why, lwhy), "exact": bool(exact), "payer_id": pid, "stage": "due"}
def stop(L, today, why):
    L["stopped"] = today.isoformat(); L["stop_why"] = why
def record(L, res, r, today, exact=False):
    """The ledger row after ONE answer. The in-a-row counters and the stops of 9.4 are applied at the end of the run (finish_run)."""
    L = dict(L or {}); sent = str(r.get("sent") or "")[:10]
    if L.get("answer") and str(L.get("sent") or "") < sent: L = {"history": list(L.get("history") or [])}   # sent again since: a fresh start
    L.pop("cleared", None)
    lab = res["label"]
    L.update(pid=re.sub(r"\D", "", str(r.get("pid") or "")), vid=re.sub(r"\D", "", str(r.get("visitid") or r.get("vid") or "")), payer=str(r.get("payer") or "").strip(),
             dos=str(r.get("dos") or "")[:10], sent=sent, asked=today.isoformat(), answer=lab, why=str(res.get("why") or "")[:80], status=str(res.get("status") or "")[:12],
             http=res.get("http"), exact=bool(exact), named=bool(res.get("named")), final=bool(res.get("final")), tries=int(L.get("tries") or 0) + 1, exact_next=False)
    L.setdefault("pending_row", 0); L.setdefault("unusable_row", 0)
    if exact: L["ask_exact"] = True                      # once a claim needed the exact date, later checks use it
    if lab in FINAL and not L["final"]: L["exact_next"] = True     # a 3-day window answered but did not name this claim: ONE exact-date check
    if lab == NOT_MATCHED:
        if exact: stop(L, today, "not matched again with the exact date of service")
        else: L["exact_next"] = True                     # ONE more check with the exact date
    if lab == NO_ELECTRONIC: stop(L, today, "the payer cannot give this claim's status electronically")
    L["history"] = (list(L.get("history") or []) + [[today.isoformat(), lab]])[-HISTORY:]
    return L
def finish_run(rows, answers, today):
    """At the end of a run: the in-a-row counters and the stops (spec 9.4). rows: ledger key -> row (changed in place); answers:
    [(key, payer, label)] in the order asked. A 'no usable answer' counts as a try only when ANOTHER claim of the same payer gave a usable
    answer in this run (a night when a payer or the vendor is down uses up nobody's tries); a 'pending' answer always counts - the payer
    answered for this very claim. -> the keys handed off tonight."""
    good = collections.defaultdict(set)
    for k, payer, lab in answers:
        if lab != UNUSABLE: good[payer].add(k)
    out = []
    for k, payer, lab in answers:
        L = rows.get(k)
        if L is None: continue
        if lab == UNUSABLE:
            if good[payer] - {k}: L["unusable_row"] = int(L.get("unusable_row") or 0) + 1; L["pending_row"] = 0
            else: L["uncounted"] = int(L.get("uncounted") or 0) + 1
        elif lab == PENDING: L["pending_row"] = int(L.get("pending_row") or 0) + 1; L["unusable_row"] = 0
        else: L["pending_row"] = 0; L["unusable_row"] = 0
        if not L.get("stopped"):
            if int(L.get("unusable_row") or 0) >= STOP_AFTER[UNUSABLE]: stop(L, today, "two answers in a row with no usable content"); out.append(k)
            elif int(L.get("pending_row") or 0) >= STOP_AFTER[PENDING]: stop(L, today, "three 'pending' answers in a row"); out.append(k)
        elif L.get("stopped") == today.isoformat() and k not in out: out.append(k)
    return out
def clear(L, today):
    """A person re-opens a row (a handed-off claim): its answers are forgotten, its history is kept; it is asked again by need."""
    L = dict(L or {})
    return {"pid": L.get("pid", ""), "vid": L.get("vid", ""), "payer": L.get("payer", ""), "dos": L.get("dos", ""), "cleared": today.isoformat(), "history": list(L.get("history") or [])}

# ---- the caps (spec 9.6) ------------------------------------------------------------------------------------------------------------
def price(n, before=0):
    """List price of n claim-status checks after `before` checks this month (stedi_prices.py, the one price table)."""
    return stedi_prices.price("claim status", n, before=before)
class Caps:
    """150 checks or $25 a run; 400 checks or $100 a calendar month (the month's checks counted in the ledger). --max may lower the run cap."""
    def __init__(self, month_before=0, run_max=None):
        self.before = int(month_before or 0); self.run = 0
        self.run_cap = CAPS["run checks"] if run_max is None else max(0, min(int(run_max), CAPS["run checks"]))
    def next_ok(self):
        n = self.run + 1
        if n > self.run_cap: return False, "run cap: %d checks" % self.run_cap
        if price(n, self.before) > CAPS["run dollars"] + 1e-9: return False, "run cap: $%.2f" % CAPS["run dollars"]
        if self.before + n > CAPS["month checks"]: return False, "month cap: %d checks" % CAPS["month checks"]
        if price(self.before + n) > CAPS["month dollars"] + 1e-9: return False, "month cap: $%.2f" % CAPS["month dollars"]
        return True, ""
    def count(self): self.run += 1
    def run_dollars(self): return price(self.run, self.before)
    def month_dollars(self): return price(self.before + self.run)

# ---- the ledger (spec 9.1) -------------------------------------------------------------------------------------------------------------
def ledger_path():
    return os.environ.get("CLAIM_STATUS_LEDGER") or os.path.join(HERE, "registers", "claim_status_ledger.json")
ABOUT = ("Claim-status ledger (look-ups part A, 11/10/2026): one row per claim and payer - the last answer, the day asked, the tries since the claim "
         "was last sent, the day it was last sent, final or not, a hand-off - and the checks bought per calendar month. Written by the claim-status "
         "helpers through cs_rules.py; claim, visit and chart numbers only.")
def _empty():
    return {"about": ABOUT, "schema": "claim-status-ledger/1", "updated": "", "months": {}, "rows": {}}
def _dumps(d):
    """One claim per line, so a week's changes read as a short diff."""
    rows = d.get("rows") or {}
    head = {k: v for k, v in d.items() if k != "rows"}
    body = ",\n".join("  %s: %s" % (json.dumps(k), json.dumps(rows[k], sort_keys=True)) for k in sorted(rows))
    return json.dumps(head, sort_keys=True)[:-1] + ',\n "rows": {\n' + body + ("\n" if body else "") + " }}\n"
class Ledger:
    def __init__(self, path, data):
        self.path = path; self.data = data; self.changed = {}; self.delta = collections.Counter(); self.saved = collections.Counter()
    @classmethod
    def open(cls, path=None, new=False):
        """The ledger, or LedgerMissing / LedgerBroken - nothing may be asked then. new=True (--new-ledger) starts an empty one where none
        exists (it is written at the first save); an existing ledger is never replaced."""
        p = path or ledger_path()
        if not os.path.exists(p):
            if not new: raise LedgerMissing("no claim-status ledger at %s - nothing is asked (the very first run is started with --new-ledger)" % p)
            return cls(p, _empty())
        if new: raise LedgerBroken("--new-ledger was given but a ledger already exists at %s - it is never replaced" % p)
        try:
            with open(p) as fh: d = json.load(fh)
            if not isinstance(d, dict) or not isinstance(d.get("rows"), dict) or not isinstance(d.get("months", {}), dict): raise ValueError("not a ledger")
        except Exception as e:
            raise LedgerBroken("the claim-status ledger at %s cannot be read (%s) - nothing is asked until a person fixes it" % (p, type(e).__name__))
        d.setdefault("months", {}); return cls(p, d)
    def row(self, k): return dict((self.data["rows"].get(k) or {}))
    def put(self, k, row): self.data["rows"][k] = row; self.changed[k] = row
    def rows(self): return self.data["rows"]
    def month_checks(self, month): return int(((self.data.get("months") or {}).get(month) or {}).get("checks") or 0)
    def add_check(self, month):
        self.delta[month] += 1
        m = self.data["months"].setdefault(month, {"checks": 0}); m["checks"] = int(m.get("checks") or 0) + 1; m["dollars"] = price(m["checks"])
    def save(self, now=None):
        """Re-read the file, put this run's rows and month counts on top of it, and write it in ONE step (a temporary file renamed into
        place). A ledger that cannot be written raises LedgerWriteError: the helper then stops asking."""
        try:
            with open(self.path) as fh: cur = json.load(fh)
            if not isinstance(cur, dict) or not isinstance(cur.get("rows"), dict): cur = None
        except Exception: cur = None
        cur = cur or json.loads(json.dumps(self.data))
        cur.setdefault("rows", {}); cur.setdefault("months", {}); cur["about"] = ABOUT; cur["schema"] = "claim-status-ledger/1"
        for k, v in self.changed.items(): cur["rows"][k] = v
        for m, n in self.delta.items():
            add = n - self.saved[m]
            if add:
                mm = cur["months"].setdefault(m, {"checks": 0}); mm["checks"] = int(mm.get("checks") or 0) + add; mm["dollars"] = price(mm["checks"])
        cutoff = ((now or datetime.datetime.now()).date() - datetime.timedelta(days=YEAR_DAYS + 35)).isoformat()
        cur["rows"] = {k: v for k, v in cur["rows"].items() if str((v or {}).get("asked") or (v or {}).get("cleared") or "9") >= cutoff}   # rows nobody can ask any more
        cur["updated"] = (now or datetime.datetime.now(datetime.timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
        d = os.path.dirname(os.path.abspath(self.path))
        try:
            os.makedirs(d, exist_ok=True)
            fd, tmp = tempfile.mkstemp(prefix=".claim_status_ledger.", suffix=".tmp", dir=d)
            with os.fdopen(fd, "w") as fh: fh.write(_dumps(cur))
            os.replace(tmp, self.path)
        except Exception as e:
            try: os.remove(tmp)
            except Exception: pass
            raise LedgerWriteError("the claim-status ledger at %s could not be written (%s)" % (self.path, type(e).__name__))
        self.data = cur; self.saved = collections.Counter(self.delta)

# ---- the ageing file (spec 9.2) ----------------------------------------------------------------------------------------------------
def _asof(s):
    for fmt in ("%Y-%m-%d %H:%M UTC", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%MZ"):
        try: return datetime.datetime.strptime(str(s or ""), fmt).replace(tzinfo=datetime.timezone.utc)
        except ValueError: pass
    return None
def aging_rows(path, now=None):
    """The same night's ageing file -> (rows, asof). Missing, unreadable, of another shape, older than one day, or lacking a field the
    rules need -> AgingError: the run ends with no call (never a fall-back to the largest balances)."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    if not path or not os.path.exists(path): raise AgingError("no ageing file at %s - run aging_refresh.py first; nothing is asked" % path)
    try:
        with open(path) as fh: j = json.load(fh)
    except Exception as e: raise AgingError("the ageing file %s cannot be read (%s) - nothing is asked" % (path, type(e).__name__))
    if not isinstance(j, dict) or j.get("schema") != "ar-aging/1" or not isinstance(j.get("rows"), list):
        raise AgingError("%s is not an ageing file (schema ar-aging/1 with rows) - nothing is asked" % path)
    asof = _asof(j.get("asof"))
    if asof is None: raise AgingError("the ageing file %s does not say when it was made - nothing is asked" % path)
    if now - asof > datetime.timedelta(days=1): raise AgingError("the ageing file %s was made %s, older than one day - run aging_refresh.py tonight; nothing is asked" % (path, j.get("asof")))
    if asof - now > datetime.timedelta(hours=1): raise AgingError("the ageing file %s is dated in the future (%s) - nothing is asked" % (path, j.get("asof")))
    rows = [r for r in j["rows"] if isinstance(r, dict)]
    missing = [f for f in AGING_FIELDS if rows and all(f not in r for r in rows)]
    if missing: raise AgingError("the ageing file %s lacks the field(s) %s that these rules need - nothing is asked" % (path, ", ".join(missing)))
    return rows, asof

# ---- tonight's list (spec 9.2-9.5) --------------------------------------------------------------------------------------------------
def plan(rows, ledger_rows, today, car2stedi, carriers=None, vids=None):
    """Tonight's claims BY NEED -> dict: due (in asking order: the filing limit soonest, then the longest silence, then the balance), waits
    (why -> count), payer_off (due by need but the payer's claim status does not work: portal or phone), handed_off (claims still on the
    hand-off list), silent60 (count), skipped (rows lacking a field), outside (rows the --carriers / visit filter left out)."""
    out = {"due": [], "waits": collections.Counter(), "payer_off": [], "handed_off": [], "silent60": 0, "skipped": 0, "outside": 0, "rows": 0, "not_due": [], "found": set()}
    seen = set(); carriers = set(carriers or []) or None; vids = set(re.sub(r"\D", "", str(v)) for v in (vids or [])) or None
    for r in rows:
        if any(f not in r for f in ("visitid", "payer", "dos", "sent")): out["skipped"] += 1; continue
        k = key(r)
        if k in seen: continue
        seen.add(k); out["rows"] += 1
        if silent(r, today): out["silent60"] += 1
        if (carriers and str(r.get("payer") or "").strip() not in carriers) or (vids and re.sub(r"\D", "", str(r.get("visitid"))) not in vids): out["outside"] += 1; continue
        L = dict(ledger_rows.get(k) or {})
        d = due(r, L, today, car2stedi)
        if vids: out["found"].add(re.sub(r"\D", "", str(r.get("visitid"))))
        if d["due"]: out["due"].append(dict(d, key=k, row=r)); continue
        out["waits"][_why_group(d)] += 1
        if vids: out["not_due"].append(dict(d, key=k, row=r))
        if d["stage"] == "route" and str(r.get("payer") or "").strip() in CS_OFF: out["payer_off"].append(dict(d, key=k, row=r))
        if d["stage"] == "ledger" and L.get("stopped") and not _posted_now(r): out["handed_off"].append(dict(d, key=k, row=r, ledger=L))
    far = datetime.date(9999, 1, 1)
    out["due"].sort(key=lambda d: (filing_limit(d["row"]) or far, -((today - (_date(d["row"].get("sent")) or today)).days), -_money(d["row"].get("bal"))))
    return out
def _why_group(d):
    w = d["why"]
    for pat, name in ((r"^payment posted", "payment posted for its payer"), (r"^denial posted", "denial posted for its payer"), (r"^last sent", "sent too recently (under 45 / 60 days)"),
                      (r"^a year old", "a year old or more"), (r"^never sent", "never sent"), (r"^final answer", "final answer on file"), (r"^handed off", "handed off - waiting for a person"),
                      (r"^'(not found|not eligible)' on file", "'not found' / 'not eligible' - waits for a resend"), (r"^sent again \d+ days ago", "sent again - waits 30 days"),
                      (r"next check after", "waiting after its last answer"), (r"^claim status does not work", "payer switched off - portal or phone"),
                      (r"no claim-status route|offers no claim-status", "no claim-status route"), (r"chart history", "chart history not read tonight"), (r"no open insurance", "no open balance")):
        if re.search(pat, w): return name
    return w[:60]
def age_and_dollars(r, today):
    a = claim_age(r, today); return "%s days old, $%.2f" % (a if a is not None else "?", _money(r.get("bal")))

# ---- an unusable raw reply (spec 9.8) ------------------------------------------------------------------------------------------------
def raw_folder():
    return os.environ.get("CLAIM_STATUS_RAW") or os.path.join(HERE, "patient_db", "claimstatus_raw")
def keep_raw(answer, http, vid, payer, stamp, folder=None):
    """An unusable reply is kept as it came, with its reply code, under patient_db/ (never in git) for a person or vendor support. Never
    stops the run -> the file's path or None."""
    try:
        d = folder or raw_folder(); os.makedirs(d, exist_ok=True)
        p = os.path.join(d, "%s_%s_%s.json" % (re.sub(r"\W", "", str(stamp)), re.sub(r"\D", "", str(vid)), re.sub(r"\W", "", str(payer))))
        with open(p, "w") as fh: json.dump({"http": http, "answer": answer}, fh)
        return p
    except Exception: return None

# ---- a person re-opens handed-off claims (spec 9.4) ---------------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(prog="cs_rules.py", description="Claim-status rules. As a program it only re-opens ledger rows: a person clears a handed-off claim so it is asked again by need. No call of any kind.", allow_abbrev=False)
    ap.add_argument("--clear", required=True, help="visit id(s), comma separated - every row of these visits (any payer) is re-opened")
    ap.add_argument("--ledger", default=None, help="the ledger file (default $CLAIM_STATUS_LEDGER or registers/claim_status_ledger.json beside this file)")
    o = ap.parse_args(argv)
    try: led = Ledger.open(o.ledger)
    except (LedgerMissing, LedgerBroken) as e: print("STOPPED: %s" % e); return 2
    want = {re.sub(r"\D", "", v) for v in o.clear.split(",") if re.sub(r"\D", "", v)}; today = datetime.date.today(); n = 0
    for k, L in sorted(led.rows().items()):
        if k.split("|")[0] in want: led.put(k, clear(L, today)); n += 1; print("re-opened %s (was: %s%s)" % (k, L.get("answer") or "-", ", handed off " + L["stopped"] if L.get("stopped") else ""))
    if n: led.save()
    print("%d ledger row(s) re-opened" % n); return 0
if __name__ == "__main__": sys.exit(main())
