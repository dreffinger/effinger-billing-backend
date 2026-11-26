#!/usr/bin/env python3
# PLAIN ENGLISH (the Monday scorecard - William's choice of 11/26/2026: "one page every Monday": money collected, what is owed and how
#   old, denials, and credentialing deadlines in the next 30 days - ONE e-mail to him plus a Weekly Scorecard page with the weeks side by side)
# Decides: nothing in AdvancedMD. It READS FILES ONLY and never logs in anywhere (no AdvancedMD, Gmail, Drive, Neon or web call). From the
#   files the runs already keep it builds the week's scorecard (the week = the seven days before the Monday it is made for):
#   COLLECTED - insurance and patient payments POSTED in AdvancedMD that week (the posted_last_7d block of working_denials_latest.json,
#     which the denials refresh totals from the chart histories it reads every 6 hours - a MINIMUM: a chart with no open balance and no
#     board row is not read) and the ERA dollars the routines posted (summary.posted.pay of the week's reports/button/<stamp>.json);
#   OWED - the open insurance balance of outstanding_latest.json by days since the date of service (0-30 / 31-60 / 61-90 / 91-120 /
#     121-365 / over 12 months) and Sunday's days-since-sent split of aging_latest.json (WAIT / RESEND / WRITE OFF);
#   DENIALS - the $0 denial lines posted that week (not cost-share 1/2/3, not contractual or informational 45/23/253/94/246) counted by
#     visit, the wrong-payer ones (27/26/200/31) among them, and what is still open on denied visits (status OPEN);
#   CREDENTIALING - the Credentialing Board cards (STEP 4b's cred_board_rows.json) due within 30 days or overdue: name, due date, days
#     left, what is needed, whose turn - and the night's cred_check_<date>.json (NPPES changes, OIG exclusion matches, revalidation dates);
#   plus the 'Your turn' exceptions and the change from last week (last week's document, passed with --last).
# Rules it uses: every figure carries its source file, field and as-of time; an input older than its usual refresh is marked STALE on
#   the page, never silently used; an input it cannot read is named and its section is marked MISSING - the scorecard is still written.
#   For each card on William's turn, due within 30 days or overdue, with an e-mail address in its 'Who to email' field, it writes the
#   Gmail DRAFT to prepare (to, subject, plain body); the run CREATES drafts and NEVER sends them - William signs and sends.
#   Card text that looks like patient data (a Medicare number, an SSN, a birth or death date, a LAST,FIRST name, a member or chart
#   number) is withheld from every output, and such a card gets no draft.
# Writes (into the WORKSPACE outbox - it refuses a folder inside a git checkout: the repository is public and carries no revenue totals):
#   scorecard_<date>.json (every figure with its source), scorecard_<date>.html (the e-mail body), scorecard_week_<date>.json (the week's
#   totals: the Weekly Scorecard page's document and the Neon run-log summary), drafts_<date>.json (the drafts to create, never send).
#   Totals, carrier codes and credentialing cards only - never a chart, visit, patient or member number.
# Never touches: AdvancedMD, Gmail, Drive, Neon, the boards, the repository (keep-aging writes the one file it is given).
#   cd /home/claude/unbilled && python3 weekly_scorecard.py build [--repo <clone>] [--ws <workspace>] [--monday YYYY-MM-DD]
#        [--last outbox/scorecard_last.json] [--page-url <the Weekly Scorecard page>] [--not-created <card id>,<card id>] [--now <ISO>]
#   cd /home/claude/unbilled && python3 weekly_scorecard.py keep-aging --src aging_latest.json --dst <clone>/reports/button/aging_latest.json
#        (cascade STEP 2 on Sundays: the same ageing file with every date of death taken out - Monday's run starts in a fresh container)
import argparse, collections, datetime, glob, html, json, os, re, sys, tempfile

VERSION = "2026-11-26.1"
UTC = datetime.timezone.utc
SKIP_CODES = {"1", "2", "3", "45", "23", "253", "94", "246"}       # cost-share and contractual / informational reasons - never a denial
WRONG_PAYER = {"27", "26", "200", "31"}                              # William 11/26/2026: wrong-payer denials are counted (and shown)
NOT_DENIAL = {"PATIENT", "CONTRACTUAL", "INFO"}                     # the board's dispositions for cost-share and contractual lines
DOS_BUCKETS = (("0-30", 0, 30), ("31-60", 31, 60), ("61-90", 61, 90), ("91-120", 91, 120), ("121-365", 121, 365), ("over 12 months", 366, 10 ** 6))
SPLIT = (("WAIT", "aging_wait", "Wait"), ("CORRECT & RESEND", "aging_resend", "Resend"), ("WRITE OFF", "aging_write_off", "Write off"))
# the usual refresh of each input plus a grace for a long night, in hours: older = STALE
LIMIT_H = {"outstanding": 9, "denials": 9, "runs": 9, "aging": 48, "cred_rows": 24, "cred_check": 30}
F_OUT, F_DEN, F_AGING = "reports/button/outstanding_latest.json", "reports/button/working_denials_latest.json", "reports/button/aging_latest.json"
F_RUNS, F_ROWS, F_TF = "reports/button/<stamp>.json", "cred_board_rows.json", "practices/ehpa/registers/tf_writeoff_watch.json"
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}")
VOCAB = {"NPI", "CAQH", "PECOS", "DEA", "OIG", "LEIE", "CMS", "NPPES", "PTAN", "EFT", "ERA", "MD", "DO", "ARNP", "APRN", "PA", "LLC", "FL",
         "AHCA", "MMA", "LTC", "CME", "BCBS", "UHC", "AARP", "HMO", "PPO", "FAX", "URL", "ID", "TBD"}
PATIENT_LIKE = [
    re.compile(r"\b[1-9][AC-HJKMNP-RT-Y][AC-HJKMNP-RT-Y0-9]\d[AC-HJKMNP-RT-Y][AC-HJKMNP-RT-Y0-9]\d[AC-HJKMNP-RT-Y]{2}\d{2}\b"),   # a Medicare number
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),                                                                       # a social security number
    re.compile(r"(?i)\b(dob|dod|born|birth\w*|death|deceased|died)\b\W{0,14}\d{1,4}[/-]\d{1,2}"),                 # a birth or death date
    re.compile(r"(?i)\b(member|subscriber|mrn|mbi|hicn|chart|patient|pat)\s*(?:id|#|no\.?|number)?\s*[:#]?\s*[A-Z]{0,3}\d{5,}"),   # a member / chart number
]
LASTFIRST = re.compile(r"\b([A-Z][A-Z'\-]{1,}),\s?([A-Z][A-Za-z'\-]{1,})\b")      # AdvancedMD's LAST,FIRST (a provider's own words are mixed case)


# ---- small readers --------------------------------------------------------------------------------------------------------------------
def num(x):
    try: return round(float(x or 0), 2)
    except (TypeError, ValueError): return 0.0


def parse_time(s):
    """an ISO time, 'YYYY-MM-DD HH:MM UTC', a run stamp 'YYYY-MM-DDTHHMMZ' or a bare date -> a UTC datetime, or None"""
    m = re.match(r"\s*(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):?(\d{2})(?::?(\d{2}))?)?", str(s or ""))
    if not m: return None
    y, mo, d, hh, mi, ss = m.groups()
    try: return datetime.datetime(int(y), int(mo), int(d), int(hh or 0), int(mi or 0), int(ss or 0), tzinfo=UTC)
    except ValueError: return None


def iso(t): return t.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ") if t else None


def load(path):
    """(the JSON in the file, '') or (None, why it could not be read)"""
    try:
        with open(path, encoding="utf-8") as fh: return json.load(fh), ""
    except FileNotFoundError: return None, "not found"
    except (OSError, ValueError) as e: return None, "unreadable (%s)" % type(e).__name__


def patient_like(s):
    """True when a card's free text looks like it holds patient data - it is then withheld from every output"""
    s = str(s or "")
    if any(rx.search(s) for rx in PATIENT_LIKE): return True
    return any(a not in VOCAB for a, _b in LASTFIRST.findall(s))


def safe(s, limit=240):
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    return ("(withheld - the card's text looks like patient data; see the card)", False) if patient_like(s) else (s[:limit], True)


def inside_checkout(path):
    p = os.path.abspath(path)
    while True:
        if os.path.lexists(os.path.join(p, ".git")): return True
        up = os.path.dirname(p)
        if up == p: return False
        p = up


def us(d): return "%d/%d/%d" % (d.month, d.day, d.year) if d else ""


def money(x): return "-" if x is None else ("-$%s" % format(abs(round(x)), ",") if x < 0 else "$%s" % format(round(x), ","))


def count(x): return "-" if x is None else format(int(x), ",")


def visits(n): return "%s visit%s" % (count(n), "" if n == 1 else "s")


def when(s): return (s or "unknown").replace("T", " ").replace(":00Z", " UTC").replace("Z", " UTC")


# ---- the inputs -----------------------------------------------------------------------------------------------------------------------
class Inputs:
    """what each input is, how old it is and whether it may be used: ok / STALE / MISSING"""
    def __init__(self, now): self.now = now; self.info = collections.OrderedDict()

    def note(self, key, file, asof, why="", ref=None, ref_name="now"):
        """ref: the time the age is measured from (the week's run reports are measured from the end of the week, not from now)"""
        if why:
            self.info[key] = {"file": file, "asof": None, "age_hours": None, "limit_hours": LIMIT_H.get(key), "status": "MISSING", "why": why}
            return self.info[key]
        age = round(((ref or self.now) - asof).total_seconds() / 3600.0, 1) if asof else None
        limit = LIMIT_H.get(key); status = "ok"; why = ""
        if asof is None: status, why = "STALE", "no as-of time in the file"
        elif limit is not None and age > limit:
            status, why = "STALE", "%.1f hours old %s - older than its usual refresh (%d hours with the grace)" % (age, "at the end of the week" if ref else "", limit)
        self.info[key] = {"file": file, "asof": iso(asof), "age_hours": age, "age_from": ref_name, "limit_hours": limit, "status": status, "why": why.replace("  ", " ")}
        return self.info[key]

    def listed(self, status): return [v["file"] for v in self.info.values() if v["status"] == status]


def fig(key, label, value, src, field, kind="money", note="", sub=False, status=None):
    """one figure of the page: its value, source file, field, as-of time and status (the source's, or MISSING when there is no value)"""
    st = status or (src["status"] if value is not None or src["status"] == "STALE" else "MISSING")
    return {"key": key, "label": label, "value": value, "kind": kind, "source": src["file"], "field": field, "asof": src["asof"], "status": st, "note": note, "sub": sub}


def week_runs(repo, frm, to):
    """the week's live run reports (reports/button/<stamp>.json, stamp date inside the week), one per stamp"""
    out = {}
    for p in sorted(glob.glob(os.path.join(repo, "reports", "button", "*.json"))):
        m = re.match(r"(\d{4}-\d{2}-\d{2})T\d{4}Z[a-z]?\.json$", os.path.basename(p))
        if not m or not (frm.isoformat() <= m.group(1) <= to.isoformat()): continue
        j, why = load(p)
        if why or not isinstance(j, dict) or j.get("schema") != "button-run/1" or j.get("mode") != "live": continue
        out.setdefault(str(j.get("stamp") or os.path.basename(p)), j)
    return list(out.values())


# ---- the four sections ----------------------------------------------------------------------------------------------------------------
def collected(I, den, runs, frm, to):
    s_den, s_runs = I.info["denials"], I.info["runs"]
    blk = den.get("posted_last_7d") if isinstance(den, dict) else None
    figs, top, note = [], [], ""
    if isinstance(blk, dict):
        if (blk.get("from"), blk.get("to")) != (frm.isoformat(), to.isoformat()):
            note = "covers %s to %s, not this week" % (blk.get("from"), blk.get("to"))
            s_den = dict(s_den, status="STALE" if s_den["status"] == "ok" else s_den["status"])
        ins, pat = num(blk.get("insurance")), num(blk.get("patient"))
        figs += [fig("collected_minimum", "Payments posted in AdvancedMD (a minimum)", round(ins + pat, 2), s_den, "posted_last_7d.insurance + posted_last_7d.patient", note=note),
                 fig("collected_insurance", "insurance", ins, s_den, "posted_last_7d.insurance", sub=True),
                 fig("collected_patient", "patient", pat, s_den, "posted_last_7d.patient", sub=True),
                 fig("collected_takebacks", "take-backs (already netted out)", num(blk.get("takebacks")), s_den, "posted_last_7d.takebacks", sub=True)]
        top = [{"carrier": k, "dollars": num(v)} for k, v in sorted((blk.get("by_carrier") or {}).items(), key=lambda kv: -num(kv[1]))[:5]]
    else:
        why = "" if den is None else "this file has no posted_last_7d block yet (the denials refresh writes it since 11/26/2026)"
        miss = dict(s_den, status="MISSING")
        figs += [fig(k, lab, None, miss, "posted_last_7d", note=why if k == "collected_minimum" else "", sub=k != "collected_minimum") for k, lab in (
                 ("collected_minimum", "Payments posted in AdvancedMD (a minimum)"), ("collected_insurance", "insurance"), ("collected_patient", "patient"),
                 ("collected_takebacks", "take-backs (already netted out)"))]
    if runs:
        figs.append(fig("routines_posted", "ERA dollars the routines posted (%d run reports)" % len(runs), round(sum(num(((r.get("summary") or {}).get("posted") or {}).get("pay")) for r in runs), 2),
                        s_runs, "summary.posted.pay, summed over the week's live run reports"))
    else:
        figs.append(fig("routines_posted", "ERA dollars the routines posted", None, s_runs, "summary.posted.pay"))
    return {"figures": figs, "top_payers": top, "basis": "posted in AdvancedMD that week, from the chart histories the runs read (charts with an open balance or a denial on the board) - a minimum"}


def owed(I, out, aging):
    s_out, s_ag = I.info["outstanding"], I.info["aging"]
    figs, buckets, split, checks, flo = [], [], [], [], None
    rows = out.get("rows") if isinstance(out, dict) else None
    if isinstance(rows, list):
        asof_d = (parse_time(out.get("as_of")) or parse_time(out.get("at")) or I.now).date()
        b = collections.OrderedDict((k, [0, 0.0]) for k, _lo, _hi in DOS_BUCKETS); total = 0.0; flo = [0, 0.0]; nodate = [0, 0.0]
        for r in rows:
            if not isinstance(r, dict): continue
            bal = num(r.get("insbalance")); total += bal
            days = r.get("days") if isinstance(r.get("days"), int) else None
            if days is None:
                d = parse_time(r.get("dos")); days = (asof_d - d.date()).days if d else None
            if days is None: nodate[0] += 1; nodate[1] += bal         # no date of service: in no bucket - the check below names it
            else:
                for k, lo, hi in DOS_BUCKETS:
                    if lo <= max(days, 0) <= hi: b[k][0] += 1; b[k][1] += bal; break
            if str(r.get("carriercode") or "").strip().upper() == "FLO99": flo[0] += 1; flo[1] += bal
        total = round(total, 2)
        figs += [fig("owed_total", "Open insurance balance", total, s_out, "rows[].insbalance (summed)"),
                 fig("owed_visits", "visits", len(rows), s_out, "rows (counted)", kind="count", sub=True)]
        for k, (n, amt) in b.items():
            key = "owed_" + k.replace("-", "_").replace(" ", "_")
            figs.append(fig(key, ("%s days since the date of service" % k) if k[0].isdigit() else "over 12 months since the date of service", round(amt, 2), s_out,
                            "rows[].insbalance where rows[].days is %s" % ("over 365" if not k[0].isdigit() else k), sub=True))
            buckets.append({"bucket": k, "visits": n, "dollars": round(amt, 2)})
        bsum = round(sum(x[1] for x in b.values()), 2)
        checks.append("open balance %s = the six buckets %s%s" % (money(total), money(bsum), "" if abs(total - bsum) < 0.01 else " - they DIFFER"))
        if nodate[0]: checks.append("%s (%s) carry no date of service - in no bucket" % (visits(nodate[0]), money(round(nodate[1], 2))))
        if isinstance(out.get("total"), (int, float)) and abs(num(out["total"]) - total) >= 0.01:
            checks.append("the file's own total %s differs from its rows %s" % (money(num(out["total"])), money(total)))
    else:
        miss = dict(s_out, status="MISSING")
        figs += [fig("owed_total", "Open insurance balance", None, miss, "rows[].insbalance"), fig("owed_visits", "visits", None, miss, "rows", kind="count", sub=True)]
        figs += [fig("owed_" + k.replace("-", "_").replace(" ", "_"), ("%s days since the date of service" % k) if k[0].isdigit() else "over 12 months since the date of service",
                     None, miss, "rows[].insbalance", sub=True) for k, _lo, _hi in DOS_BUCKETS]
    br = aging.get("by_rec") if isinstance(aging, dict) else None
    if isinstance(br, dict):
        for rec, key, lab in SPLIT:
            v = br.get(rec) or {}
            figs.append(fig(key, "Days since the claim was last sent - %s" % lab.lower(), num(v.get("amt")), s_ag, "by_rec['%s'].amt" % rec))
            split.append({"group": lab, "visits": int(v.get("n") or 0), "dollars": num(v.get("amt"))})
        if isinstance(rows, list) and isinstance(aging.get("total"), (int, float)):
            checks.append("Sunday's ageing total %s (as of %s) vs the open balance now %s" % (money(num(aging["total"])), when(s_ag["asof"]), money(total)))
    else:
        miss = dict(s_ag, status="MISSING")
        figs += [fig(key, "Days since the claim was last sent - %s" % lab.lower(), None, miss, "by_rec['%s'].amt" % rec) for rec, key, lab in SPLIT]
    return {"figures": figs, "buckets": buckets, "split": split, "checks": checks, "flo99": flo, "basis": "insurance balances only (the unpaid list carries no patient balances)"}


def carcs(v):
    """the reason codes of a Working Denials row ('CO/CO27' -> '27')"""
    out = set()
    for c in list(v.get("codes") or []) + [v.get("carc")]:
        c = str(c or "").split("/")[-1].strip().upper()
        out.add(re.sub(r"^(CO|OA|PR|PI|CR)(?=.)", "", c))
    return out - {""}


def denials(I, den, frm, to):
    s = I.info["denials"]
    if not isinstance(den, dict):
        miss = dict(s, status="MISSING")
        keys = (("denials_new_visits", "New denied visits this week", "count"), ("denials_new_lines", "denial lines", "count"), ("denials_new_dollars", "dollars denied", "money"),
                ("denials_wrong_payer_visits", "wrong payer (27 / 26 / 200 / 31)", "count"), ("denial_rate", "denial rate", "rate"),
                ("denied_open_visits", "Denied visits still open", "count"), ("denied_open_balance", "open balance on them", "money"),
                ("denied_open_wrong_payer_visits", "of them wrong payer", "count"))
        return {"figures": [fig(k, lab, None, miss, "-", kind=kd, sub=lab[:1].islower()) for k, lab, kd in keys], "by_dispo": []}
    figs = []
    blk = den.get("posted_last_7d"); d = blk.get("denials") if isinstance(blk, dict) else None
    if isinstance(d, dict):
        s_w = s if (blk.get("from"), blk.get("to")) == (frm.isoformat(), to.isoformat()) else dict(s, status="STALE" if s["status"] == "ok" else s["status"])
        adj = int(blk.get("adjudicated_lines") or 0)
        figs += [fig("denials_new_visits", "New denied visits this week", int(d.get("visits") or 0), s_w, "posted_last_7d.denials.visits", kind="count"),
                 fig("denials_new_lines", "denial lines", int(d.get("lines") or 0), s_w, "posted_last_7d.denials.lines", kind="count", sub=True),
                 fig("denials_new_dollars", "dollars denied", num(d.get("dollars")), s_w, "posted_last_7d.denials.dollars", sub=True),
                 fig("denials_wrong_payer_visits", "wrong payer (27 / 26 / 200 / 31)", int(d.get("wrong_payer_visits") or 0), s_w, "posted_last_7d.denials.wrong_payer_visits", kind="count", sub=True),
                 fig("denial_rate", "denial rate (denial lines / payer answers)", round(int(d.get("lines") or 0) / adj, 4) if adj else None, s_w,
                     "posted_last_7d.denials.lines / posted_last_7d.adjudicated_lines", kind="rate", sub=True, status=None if adj else s_w["status"],
                     note="" if adj else "no payer answer was posted this week")]
    else:      # before the denials refresh wrote posted_last_7d: by the date of each visit's leading denial line - approximate
        wk = [v for v in den.get("visits") or [] if isinstance(v, dict) and frm.isoformat() <= str(v.get("denied_on") or "") <= to.isoformat() and v.get("dispo") not in NOT_DENIAL]
        note = "approximate: by the date of each visit's leading denial line (no posted_last_7d block yet)"
        figs += [fig("denials_new_visits", "New denied visits this week", len(wk), s, "visits[].denied_on inside the week", kind="count", note=note),
                 fig("denials_new_lines", "denial lines", None, dict(s, status="MISSING"), "posted_last_7d.denials.lines", kind="count", sub=True),
                 fig("denials_new_dollars", "dollars denied", round(sum(num(v.get("amt")) for v in wk), 2), s, "visits[].amt inside the week", sub=True),
                 fig("denials_wrong_payer_visits", "wrong payer (27 / 26 / 200 / 31)", sum(1 for v in wk if carcs(v) & WRONG_PAYER), s, "visits[].codes inside the week", kind="count", sub=True),
                 fig("denial_rate", "denial rate (denial lines / payer answers)", None, dict(s, status="MISSING"), "posted_last_7d.adjudicated_lines", kind="rate", sub=True)]
    op = [v for v in den.get("visits") or [] if isinstance(v, dict) and v.get("status") == "OPEN" and v.get("dispo") not in NOT_DENIAL]
    bd = collections.defaultdict(lambda: [0, 0.0])
    for v in op: bd[v.get("dispo") or "?"][0] += 1; bd[v.get("dispo") or "?"][1] += num(v.get("open_balance"))
    figs += [fig("denied_open_visits", "Denied visits still open", len(op), s, "visits[] with status OPEN (not cost-share / contractual)", kind="count"),
             fig("denied_open_balance", "open balance on them", round(sum(num(v.get("open_balance")) for v in op), 2), s, "visits[].open_balance with status OPEN", sub=True),
             fig("denied_open_wrong_payer_visits", "of them wrong payer", sum(1 for v in op if carcs(v) & WRONG_PAYER), s, "visits[].codes with status OPEN", kind="count", sub=True)]
    return {"figures": figs, "by_dispo": [{"disposition": k, "visits": n, "dollars": round(a, 2)} for k, (n, a) in sorted(bd.items(), key=lambda kv: -kv[1][1])]}


def credentialing(I, rows, chk, today, monday, now, not_created):
    s_rows = I.info["cred_rows"]
    items, drafts = [], []
    yt = {"urgent": [], "overdue": [], "needs": [], "info": []}
    for r in rows if isinstance(rows, list) else []:
        if not isinstance(r, dict): continue
        due = parse_time(r.get("due"))
        if not due or not re.match(r"\d{4}-\d{2}-\d{2}$", str(r.get("due"))): continue
        due = due.date(); days = (due - today).days
        if days > 30: continue
        name, ok1 = safe(r.get("name") or r.get("id"), 120); holder, ok2 = safe(r.get("holder"), 80); need, ok3 = safe(r.get("need"))
        turn = str(r.get("turn") or "").lower(); turn = turn if turn in ("william", "done") else "claude"
        emails = sorted(set(EMAIL_RE.findall(str(r.get("contacts") or ""))))[:3]
        card = str(r.get("id") or "")
        items.append({"card": card, "name": name, "holder": holder, "due": due.isoformat(), "days_left": days, "need": need, "turn": turn, "contact": bool(emails)})
        if turn != "william": continue
        if not (ok1 and ok2 and ok3):
            yt["needs"].append("%s: no draft made - the card's text looks like patient data; write it yourself" % name)
        elif emails:
            drafts.append(draft(card, name, holder, due, days, need, emails, monday, now, card not in not_created))
            if card in not_created: yt["needs"].append("%s: the draft to %s could not be prepared tonight - write it yourself" % (name, ", ".join(emails)))
        else:
            yt["needs"].append("%s, due %s: no e-mail address on the card - the next step is yours (a form or a call)" % (name, us(due)))
    items.sort(key=lambda x: (x["days_left"], x["name"]))
    for it in items:
        if it["days_left"] < 0 and it["turn"] != "done":
            yt["overdue"].append("OVERDUE %d days: %s (%s's turn)" % (-it["days_left"], it["name"], it["turn"].title()))
    figs = [fig("cred_due_30", "Cards due within 30 days", sum(1 for x in items if x["days_left"] >= 0) if isinstance(rows, list) else None, s_rows, "cred_board_rows.json due within 30 days", kind="count"),
            fig("cred_overdue", "Cards overdue", sum(1 for x in items if x["days_left"] < 0) if isinstance(rows, list) else None, s_rows, "cred_board_rows.json due before today", kind="count"),
            fig("drafts_prepared", "Gmail drafts prepared", sum(1 for x in drafts if x["created"]) if isinstance(rows, list) else None, s_rows, "drafts_<date>.json", kind="count")]
    check = {}
    if isinstance(chk, dict):
        lm = (chk.get("leie") or {}) if isinstance(chk.get("leie"), dict) else {}
        reval = []
        for npi, rv in (chk.get("revalidation") or {}).items() if isinstance(chk.get("revalidation"), dict) else []:
            for x in rv if isinstance(rv, list) else []:
                if isinstance(x, dict) and str(x.get("due") or "TBD") != "TBD": reval.append(str(x.get("adjusted") or x.get("due")))
        check = {"nppes_changes": len(chk.get("nppes_changes") or []), "leie_matches": len(lm.get("matches") or []), "leie_error": bool(lm.get("error")),
                 "revalidation_dates": sorted(set(reval)), "reminders": len(chk.get("reminders") or [])}
        if check["leie_matches"]: yt["urgent"].append("OIG EXCLUSION LIST: %d possible match(es) tonight - the grp-oig card is on your turn" % check["leie_matches"])
        if check["nppes_changes"]: yt["info"].append("NPPES: %d record(s) changed since the last snapshot - see the NPI cards" % check["nppes_changes"])
    return {"figures": figs, "items": items, "check": check, "drafts": drafts, "your_turn": yt}


def draft(card, name, holder, due, days, need, emails, monday, now, created):
    """the Gmail DRAFT for one card - plain text, no patient data; the run creates it and never sends it"""
    who = " (%s)" % holder if holder else ""
    subj = "Effinger Health PA - %s%s - due %s" % (name, who, us(due))
    body = ["Hello,", "", "I am writing about %s for Effinger Health PA%s. It %s due on %s." % (name, who, "was" if days < 0 else "is", due.strftime("%B %d, %Y").replace(" 0", " "))]
    if need: body += ["", "What is needed: %s" % need]
    body += ["", "Could you tell me what you still need from us to complete it, or confirm that it is already on file?", "", "Thank you,", "William Effinger, DO", "Effinger Health PA"]
    note = "Monday scorecard %s: a Gmail draft to %s is waiting in your Drafts (subject '%s') - review it, sign and send it; nothing was sent." % (us(monday), ", ".join(emails), subj)
    return {"card": card, "name": name, "due": due.isoformat(), "action": "create_draft", "to": emails, "subject": subj, "body": "\n".join(body), "created": created,
            "card_op": {"op": "update", "collection": "cred", "id": card, "set": {}, "append": {"notes": [{"who": "Claude", "text": note, "at": iso(now)}]}}}   # an empty set: the card keeps every field, the note is added


def tf_watch(repo):
    """(visits, dollars) on the timely-filing watch still waiting for the payer's answer - counts only; None when the register is absent"""
    j, why = load(os.path.join(repo, F_TF))
    if why or not isinstance(j, dict): return None
    n, amt = 0, 0.0
    for it in j.get("items") or []:
        if not isinstance(it, dict) or str(it.get("status")) != "open": continue
        for v in it.get("visits") or []:
            if isinstance(v, dict) and not str(v.get("outcome") or "").strip(): n += 1; amt += num(v.get("insbal"))
    return n, round(amt, 2)


# ---- the scorecard --------------------------------------------------------------------------------------------------------------------
CHANGE_KEYS = (("collected_minimum", "Collected in AdvancedMD (minimum)", "money"), ("routines_posted", "ERA dollars the routines posted", "money"),
               ("owed_total", "Open insurance balance", "money"), ("owed_121_365", "121-365 days", "money"), ("owed_over_12_months", "over 12 months", "money"),
               ("aging_resend", "Resend (days since sent)", "money"), ("aging_write_off", "Write off (days since sent)", "money"),
               ("denials_new_visits", "New denied visits", "count"), ("denied_open_balance", "Open on denied visits", "money"), ("cred_overdue", "Credentialing cards overdue", "count"))


def build(a):
    now = parse_time(a.now) if a.now else datetime.datetime.now(UTC)
    today = now.date()
    monday = datetime.date.fromisoformat(a.monday) if a.monday else today - datetime.timedelta(days=today.weekday())
    frm, to = monday - datetime.timedelta(days=7), monday - datetime.timedelta(days=1)
    out_dir = os.path.abspath(a.out or os.path.join(a.ws, "outbox"))
    if inside_checkout(out_dir):
        sys.exit("weekly_scorecard: REFUSED - %s is inside a git checkout; the scorecard's totals never go into the repository (it is public)" % out_dir)
    I = Inputs(now)
    out, why = load(os.path.join(a.repo, F_OUT))
    if not why and not (isinstance(out, dict) and out.get("schema") == "outstanding-claims/1"): out, why = None, "not an outstanding-claims/1 file"
    I.note("outstanding", F_OUT, parse_time((out or {}).get("at")) if out else None, why)
    den, why = load(os.path.join(a.repo, F_DEN))
    if not why and not (isinstance(den, dict) and den.get("schema") == "working-denials-snapshot/1"): den, why = None, "not a working-denials-snapshot/1 file"
    I.note("denials", F_DEN, parse_time((den or {}).get("asof")) if den else None, why)
    runs = week_runs(a.repo, frm, to)
    newest = max((parse_time(r.get("ended")) or parse_time(r.get("stamp")) for r in runs), default=None) if runs else None
    week_end = datetime.datetime(monday.year, monday.month, monday.day, tzinfo=UTC)
    I.note("runs", "%s (%d of this week)" % (F_RUNS, len(runs)), newest, "" if runs else "no live run report dated inside the week",
           ref=min(week_end, now), ref_name="the end of the week")
    aging, why = load(os.path.join(a.repo, F_AGING))
    if not why and not (isinstance(aging, dict) and aging.get("schema") == "ar-aging/1"): aging, why = None, "not an ar-aging/1 file"
    I.note("aging", F_AGING, parse_time((aging or {}).get("asof")) if aging else None, why)
    rows_p = os.path.join(a.ws, F_ROWS)
    rows, why = load(rows_p)
    if not why and not isinstance(rows, list): rows, why = None, "not a list of cards"
    I.note("cred_rows", F_ROWS, datetime.datetime.fromtimestamp(os.path.getmtime(rows_p), UTC) if rows is not None else None, why)
    chk_name = "cred_check_%s.json" % today.strftime("%Y%m%d")
    chk_p = os.path.join(a.ws, chk_name)
    if not os.path.exists(chk_p):
        older = sorted(glob.glob(os.path.join(a.ws, "cred_check_*.json")))
        chk_p = older[-1] if older else chk_p
    chk, why = load(chk_p)
    if not why and not isinstance(chk, dict): chk, why = None, "not a cred_check file"
    I.note("cred_check", os.path.basename(chk_p), parse_time((chk or {}).get("date")) if chk else None, why)
    last, lwhy = load(a.last) if a.last else (None, "no earlier scorecard - this week is the baseline")
    for k in ("totals", "data"):                 # a whole scorecard_<date>.json, or a page document written with its 'data' wrapper
        if isinstance(last, dict) and isinstance(last.get(k), dict): last = last[k]
    if not isinstance(last, dict): last = None; lwhy = lwhy if lwhy.startswith("no earlier") else "last week's document could not be read (%s) - no comparison" % lwhy
    elif last.get("week_of") == monday.isoformat(): last, lwhy = None, "the document passed as last week's is this week's own - no comparison"
    not_created = {x.strip() for x in (a.not_created or "").split(",") if x.strip()}

    sec = collections.OrderedDict()
    sec["collected"] = collected(I, den, runs, frm, to)
    sec["owed"] = owed(I, out, aging)
    sec["denials"] = denials(I, den, frm, to)
    cr = credentialing(I, rows, chk, today, monday, now, not_created)
    drafts = cr.pop("drafts"); yt_cred = cr.pop("your_turn")
    sec["credentialing"] = cr
    for name, s in sec.items():
        st = [f_["status"] for f_ in s["figures"]]
        s["status"] = "MISSING" if st and all(x == "MISSING" for x in st) else ("STALE" if "STALE" in st else ("partial" if "MISSING" in st else "ok"))
    totals = collections.OrderedDict((f_["key"], f_["value"]) for s in sec.values() for f_ in s["figures"])

    done = [d for d in drafts if d["created"]]
    yt = yt_cred["urgent"] + yt_cred["overdue"]  # the exceptions only, most urgent first (an input that is not current has its own box above)
    if done: yt.append("%d Gmail draft(s) waiting in your Drafts - review, sign and send (listed below)" % len(done))
    yt += yt_cred["needs"] + yt_cred["info"]
    flo = sec["owed"].get("flo99")
    if flo and flo[0]: yt.append("FCC (FLO99): %s open on %s - paper checks deposited in Square; reconcile before any write-off (9/22 rule)" % (money(flo[1]), visits(flo[0])))
    tf = tf_watch(a.repo)
    if tf and tf[0]: yt.append("Timely-filing watch: %s (%s) sent once and still waiting for the payer's answer" % (visits(tf[0]), money(tf[1])))
    change = []
    if last:
        for k, lab, kind in CHANGE_KEYS:
            t, l_ = totals.get(k), last.get(k)
            if isinstance(t, (int, float)) and isinstance(l_, (int, float)):
                change.append({"key": k, "label": lab, "kind": kind, "this_week": t, "last_week": l_, "change": round(t - l_, 2)})
    stale, missing = I.listed("STALE"), I.listed("MISSING")
    tv = lambda k: totals.get(k)
    head = ["week %s-%s" % (frm.strftime("%m/%d"), to.strftime("%m/%d"))]
    if isinstance(tv("collected_minimum"), (int, float)): head.append("collected at least %s dollars" % format(round(tv("collected_minimum")), ","))
    if isinstance(tv("owed_total"), (int, float)): head.append("owed %s dollars on %s visits" % (format(round(tv("owed_total")), ","), count(tv("owed_visits"))))
    if isinstance(tv("denials_new_visits"), (int, float)): head.append("%d new denied visits" % tv("denials_new_visits"))
    if isinstance(tv("cred_due_30"), (int, float)): head.append("credentialing %d due in 30 days, %d overdue, %d drafts" % (tv("cred_due_30"), tv("cred_overdue") or 0, tv("drafts_prepared") or 0))
    if stale or missing: head.append("%d input(s) stale, %d missing" % (len(stale), len(missing)))
    headline = "; ".join(head)
    subject = "Weekly Scorecard - week of %s to %s: %s collected (minimum), %s owed%s" % (us(frm), us(to), money(tv("collected_minimum")), money(tv("owed_total")),
                                                                                        " - %d input(s) STALE or MISSING" % (len(stale) + len(missing)) if stale or missing else "")
    page = a.page_url if (a.page_url or "").startswith("https://") else None
    sc = collections.OrderedDict([("schema", "weekly-scorecard/1"), ("version", VERSION), ("week_of", monday.isoformat()), ("period", {"from": frm.isoformat(), "to": to.isoformat()}),
                                  ("generated", iso(now)), ("headline", headline), ("email_subject", subject), ("page_url", page), ("inputs", I.info), ("sections", sec),
                                  ("your_turn", yt), ("drafts", [{k: d[k] for k in ("card", "name", "due", "to", "subject", "created")} for d in drafts]),
                                  ("change", change), ("last_week", (last or {}).get("week_of") if last else None), ("last_week_note", "" if last else lwhy)])
    week = collections.OrderedDict([("schema", "weekly-scorecard-week/1"), ("version", VERSION), ("week_of", monday.isoformat()), ("period_from", frm.isoformat()),
                                    ("period_to", to.isoformat()), ("generated", iso(now))])
    week.update(totals); week["stale"] = stale; week["missing"] = missing
    sc["totals"] = week
    os.makedirs(out_dir, exist_ok=True)
    d = monday.isoformat()
    files = {"scorecard_%s.json" % d: json.dumps(sc, indent=1), "scorecard_week_%s.json" % d: json.dumps(week, indent=1),
             "drafts_%s.json" % d: json.dumps({"schema": "scorecard-drafts/1", "week_of": d, "rule": "create each entry with mcp__Gmail__create_draft (to, subject, body) - NEVER send it; William signs and sends",
                                               "drafts": drafts}, indent=1),
             "scorecard_%s.html" % d: render(sc)}
    for name, text in files.items():
        fd, tmp = tempfile.mkstemp(prefix="." + name + ".", dir=out_dir)
        with os.fdopen(fd, "w", encoding="utf-8") as fh: fh.write(text)
        os.replace(tmp, os.path.join(out_dir, name))
    print("scorecard %s: %s | files -> %s (scorecard_%s.json / .html, scorecard_week_%s.json, drafts_%s.json: %d draft(s))%s%s" % (
        d, headline, out_dir, d, d, d, len(done), " | STALE: " + ", ".join(stale) if stale else "", " | MISSING: " + ", ".join(missing) if missing else ""))
    return 0


# ---- the e-mail (inline styles only; every colour is the LONGHAND background-color - Gmail strips the shorthand) --------------------------
def render(sc):
    e = html.escape
    srcs = []                                    # the footnotes: (file, field, as of, status)

    def ref(f_):
        key = (f_["source"], f_["field"], f_["asof"], f_["status"])
        if key not in srcs: srcs.append(key)
        return '<sup style="color:#6b7280;">%d</sup>' % (srcs.index(key) + 1)

    def val(f_):
        stale = ' <span style="color:#b45309;font-weight:bold;">STALE</span>' if f_["status"] == "STALE" else ""
        if f_["value"] is None: return '<span style="color:#b91c1c;font-weight:bold;">MISSING</span>' if f_["status"] == "MISSING" else "-" + stale
        v = money(f_["value"]) if f_["kind"] == "money" else ("%.1f%%" % (100 * f_["value"]) if f_["kind"] == "rate" else count(f_["value"]))
        return v + stale

    def badge(st):
        c = {"STALE": ("#fef3c7", "#92400e"), "MISSING": ("#fee2e2", "#991b1b"), "partial": ("#fef3c7", "#92400e")}.get(st)
        return "" if not c else ' <span style="background-color:%s;color:%s;font-size:11px;font-weight:bold;padding:2px 6px;border-radius:4px;">%s</span>' % (c[0], c[1], e(st.upper()))

    def table(figs):
        rows = []
        for f_ in figs:
            ind = f_.get("sub")
            rows.append('<tr><td style="padding:4px 8px 4px %dpx;border-bottom:1px solid #e5e7eb;color:%s;">%s%s</td><td style="padding:4px 8px;border-bottom:1px solid #e5e7eb;text-align:right;white-space:nowrap;%s">%s</td></tr>' % (
                24 if ind else 8, "#4b5563" if ind else "#111827", e(f_["label"]), ref(f_), "" if ind else "font-weight:bold;", val(f_)))
            if f_.get("note"): rows.append('<tr><td colspan="2" style="padding:0 8px 4px 24px;color:#6b7280;font-size:12px;">%s</td></tr>' % e(f_["note"]))
        return '<table role="presentation" cellpadding="0" cellspacing="0" style="width:100%;border-collapse:collapse;font-size:14px;">' + "".join(rows) + "</table>"

    def h2(title, st, sub=""):
        return '<h2 style="font-size:16px;margin:22px 0 6px;color:#111827;">%s%s</h2>%s' % (e(title), badge(st), '<p style="margin:0 0 6px;color:#6b7280;font-size:12px;">%s</p>' % e(sub) if sub else "")

    S = sc["sections"]; p = sc["period"]
    fd = lambda s: datetime.date.fromisoformat(s).strftime("%b %d, %Y").replace(" 0", " ")
    parts = ['<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Weekly Scorecard</title></head>',
             '<body style="margin:0;padding:0;background-color:#f3f4f6;">',
             '<table role="presentation" cellpadding="0" cellspacing="0" style="width:100%;background-color:#f3f4f6;"><tr><td style="padding:16px;">',
             '<div style="max-width:680px;margin:0 auto;background-color:#ffffff;border-radius:8px;padding:20px;font-family:Arial,Helvetica,sans-serif;color:#111827;">',
             '<div style="font-size:11px;letter-spacing:1px;color:#6b7280;text-transform:uppercase;">Effinger Health PA - Weekly Scorecard</div>',
             '<h1 style="font-size:21px;margin:4px 0 6px;">Week of %s to %s</h1>' % (e(fd(p["from"])), e(fd(p["to"]))),
             '<p style="margin:0 0 12px;color:#4b5563;font-size:13px;">Made %s by the nightly cascade from the files the runs keep - nothing on this page was looked up live. Every figure names its source below.</p>' % e(when(sc["generated"]))]
    if sc.get("page_url"):
        parts.append('<p style="margin:0 0 14px;"><a href="%s" style="display:inline-block;background-color:#1d4ed8;color:#ffffff;text-decoration:none;font-weight:bold;font-size:14px;padding:10px 18px;border-radius:6px;">Open the Weekly Scorecard - the weeks side by side</a></p>' % e(sc["page_url"], quote=True))
    else:
        parts.append('<p style="margin:0 0 14px;color:#6b7280;font-size:12px;">(the Weekly Scorecard page link is not set yet.)</p>')
    bad = [v for v in sc["inputs"].values() if v["status"] in ("STALE", "MISSING")]
    if bad:
        parts.append('<div style="background-color:#fff7ed;border:1px solid #fdba74;border-radius:6px;padding:10px 12px;margin:0 0 12px;font-size:13px;"><b>Inputs not current:</b><ul style="margin:6px 0 0 18px;padding:0;">%s</ul></div>' % "".join(
            "<li><b>%s</b> %s - %s</li>" % (e(v["status"]), e(v["file"]), e(v["why"])) for v in bad))
    parts.append('<div style="background-color:#eef2ff;border-left:4px solid #4f46e5;border-radius:4px;padding:10px 14px;margin:0 0 6px;"><div style="font-weight:bold;font-size:15px;margin-bottom:4px;">Your turn</div>%s</div>' % (
        '<ul style="margin:0 0 0 18px;padding:0;font-size:14px;">%s</ul>' % "".join("<li style=\"margin:2px 0;\">%s</li>" % e(x) for x in sc["your_turn"]) if sc["your_turn"] else '<div style="font-size:14px;color:#4b5563;">Nothing needs you this week.</div>'))
    dr = [d for d in sc["drafts"] if d["created"]]
    parts.append(h2("Drafts waiting for you", "", "Prepared by the run in your Gmail Drafts - nothing was sent; you review, sign and send."))
    parts.append('<ul style="margin:0 0 0 18px;padding:0;font-size:14px;">%s</ul>' % "".join("<li style=\"margin:2px 0;\"><b>%s</b> - to %s - subject: %s</li>" % (e(d["name"]), e(", ".join(d["to"])), e(d["subject"])) for d in dr)
                 if dr else '<p style="margin:0;font-size:14px;color:#4b5563;">None this week.</p>')
    c = S["collected"]
    parts.append(h2("Collected", c["status"], c["basis"]))
    parts.append(table(c["figures"]))
    if c["top_payers"]:
        parts.append('<p style="margin:6px 0 0;font-size:13px;color:#374151;">Top payers: %s</p>' % e("; ".join("%s %s" % (t["carrier"], money(t["dollars"])) for t in c["top_payers"])))
    o = S["owed"]
    parts.append(h2("Owed", o["status"], o["basis"]))
    parts.append(table(o["figures"]))
    if o["checks"]: parts.append('<p style="margin:6px 0 0;font-size:12px;color:#6b7280;">Checks: %s</p>' % e("; ".join(o["checks"])))
    dn = S["denials"]
    parts.append(h2("Denials", dn["status"], "$0 denial lines posted that week (not cost-share, not contractual), counted by visit; wrong-payer denials (27 / 26 / 200 / 31) counted"))
    parts.append(table(dn["figures"]))
    if dn["by_dispo"]:
        parts.append('<p style="margin:6px 0 0;font-size:13px;color:#374151;">Open by disposition: %s</p>' % e("; ".join("%s %d (%s)" % (x["disposition"], x["visits"], money(x["dollars"])) for x in dn["by_dispo"][:6])))
    cr = S["credentialing"]
    parts.append(h2("Credentialing", cr["status"], "Cards due within 30 days or overdue"))
    parts.append(table(cr["figures"]))
    if cr["items"]:
        th = '<th style="text-align:left;padding:4px 6px;border-bottom:2px solid #d1d5db;font-size:12px;color:#374151;">%s</th>'
        parts.append('<table role="presentation" cellpadding="0" cellspacing="0" style="width:100%;border-collapse:collapse;font-size:13px;margin-top:8px;"><tr>' + "".join(th % h for h in ("Card", "Due", "Days left", "What is needed", "Whose turn")) + "</tr>" + "".join(
            '<tr><td style="padding:4px 6px;border-bottom:1px solid #e5e7eb;">%s%s</td><td style="padding:4px 6px;border-bottom:1px solid #e5e7eb;white-space:nowrap;">%s</td><td style="padding:4px 6px;border-bottom:1px solid #e5e7eb;text-align:right;%s">%s</td><td style="padding:4px 6px;border-bottom:1px solid #e5e7eb;">%s</td><td style="padding:4px 6px;border-bottom:1px solid #e5e7eb;">%s</td></tr>' % (
                e(it["name"]), (" <span style=\"color:#6b7280;\">(%s)</span>" % e(it["holder"])) if it["holder"] else "", e(us(datetime.date.fromisoformat(it["due"]))),
                "color:#b91c1c;font-weight:bold;" if it["days_left"] < 0 else "", "%d overdue" % -it["days_left"] if it["days_left"] < 0 else str(it["days_left"]), e(it["need"]),
                e({"william": "William", "claude": "Claude", "done": "Done (set the next due date)"}[it["turn"]])) for it in cr["items"]) + "</table>")
    ck = cr.get("check") or {}
    if ck:
        parts.append('<p style="margin:6px 0 0;font-size:12px;color:#6b7280;">Tonight\'s check: NPPES changes %d; OIG exclusion matches %d%s; Medicare revalidation dates %s; reminders %d.</p>' % (
            ck["nppes_changes"], ck["leie_matches"], " (the list could not be read)" if ck["leie_error"] else "", e(", ".join(ck["revalidation_dates"]) or "none set"), ck["reminders"]))
    parts.append(h2("Change from last week", ""))
    if sc["change"]:
        parts.append('<table role="presentation" cellpadding="0" cellspacing="0" style="width:100%;border-collapse:collapse;font-size:13px;"><tr>' + "".join(
            '<th style="text-align:%s;padding:4px 6px;border-bottom:2px solid #d1d5db;font-size:12px;color:#374151;">%s</th>' % (al, h) for al, h in (("left", ""), ("right", "This week"), ("right", "Last week"), ("right", "Change"))) + "</tr>" + "".join(
            '<tr><td style="padding:4px 6px;border-bottom:1px solid #e5e7eb;">%s</td><td style="padding:4px 6px;border-bottom:1px solid #e5e7eb;text-align:right;">%s</td><td style="padding:4px 6px;border-bottom:1px solid #e5e7eb;text-align:right;color:#6b7280;">%s</td><td style="padding:4px 6px;border-bottom:1px solid #e5e7eb;text-align:right;font-weight:bold;">%s</td></tr>' % (
                e(x["label"]), (money if x["kind"] == "money" else count)(x["this_week"]), (money if x["kind"] == "money" else count)(x["last_week"]),
                ("+" if x["change"] > 0 else "") + (money if x["kind"] == "money" else count)(x["change"])) for x in sc["change"]) + "</table>")
    else:
        parts.append('<p style="margin:0;font-size:14px;color:#4b5563;">%s</p>' % e(sc.get("last_week_note") or "No figures to compare."))
    parts.append('<h2 style="font-size:13px;margin:22px 0 4px;color:#374151;">Sources</h2><ol style="margin:0 0 0 18px;padding:0;font-size:11px;color:#6b7280;">%s</ol>' % "".join(
        "<li>%s - %s - as of %s%s</li>" % (e(s_[0]), e(s_[1]), e(when(s_[2])), " - " + e(s_[3]) if s_[3] != "ok" else "") for s_ in srcs))
    parts.append('<p style="margin:16px 0 0;font-size:11px;color:#9ca3af;">weekly_scorecard.py %s - totals only, no patient data. This e-mail goes to you alone.</p></div></td></tr></table></body></html>' % VERSION)
    return "".join(parts)


# ---- keep-aging: Sunday's ageing file kept for Monday, with every date of death taken out -------------------------------------------------
def keep_aging(a):
    j, why = load(a.src)
    if why or not isinstance(j, dict) or j.get("schema") != "ar-aging/1" or not isinstance(j.get("rows"), list):
        sys.exit("weekly_scorecard keep-aging: REFUSED - %s is not an ar-aging/1 file (%s); nothing copied" % (a.src, why or "another shape"))
    n = 0
    for r in j["rows"]:
        if not isinstance(r, dict): continue
        if r.get("dod"): r["dod"] = ""; n += 1
        for k in ("why", "rule"):
            v = r.get(k)
            if isinstance(v, str) and re.search(r"(?i)death|deceas|died", v):
                r[k] = re.sub(r"\b(?:19|20)\d{2}-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}/(?:19|20)?\d{2}\b", "[DOB]", v)
    os.makedirs(os.path.dirname(os.path.abspath(a.dst)), exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".aging_keep.", dir=os.path.dirname(os.path.abspath(a.dst)))
    with os.fdopen(fd, "w", encoding="utf-8") as fh: json.dump(j, fh, separators=(",", ":"))
    os.replace(tmp, a.dst)
    print("keep-aging: %d rows (as of %s) -> %s; %d row(s) carried a date of death - taken out" % (len(j["rows"]), j.get("asof"), a.dst, n))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="the Monday scorecard (reads files only)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--repo", default=os.environ.get("EHPA_REPO") or ("/home/claude/effinger-billing-backend" if os.path.isdir("/home/claude/effinger-billing-backend")
                                                                    else os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    b.add_argument("--ws", default=os.environ.get("EHPA_WS") or os.getcwd())
    b.add_argument("--out", default=None, help="the outbox (default <ws>/outbox) - never a folder inside a git checkout")
    b.add_argument("--monday", default=None, help="the Monday the scorecard is made for (default: this week's Monday)")
    b.add_argument("--last", default=None, help="last week's document (scorecard_week_<date>.json or the page's week document)")
    b.add_argument("--page-url", default=None)
    b.add_argument("--not-created", default="", help="card ids whose Gmail draft could not be created")
    b.add_argument("--now", default=None, help="the time to measure ages against (default: now)")
    k = sub.add_parser("keep-aging")
    k.add_argument("--src", required=True); k.add_argument("--dst", required=True)
    a = ap.parse_args(argv)
    return build(a) if a.cmd == "build" else keep_aging(a)


if __name__ == "__main__":
    sys.exit(main())
