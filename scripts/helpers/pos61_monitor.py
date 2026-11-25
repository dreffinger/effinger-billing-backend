#!/usr/bin/env python3
# PLAIN ENGLISH (the payment monitor of the inpatient-rehab visits at place of service 61 - William, 11/25/2026)
# Decides: nothing. READ-ONLY. William, 11/25/2026, asked whether the visits he makes in the hospital's rehabilitation unit should go out at
#   place of service 61: "yes and let us monitor them to make sure they pay and dont deny the ones were already paying with the inpatient
#   hosptial as the place oif service though so we need to monitor that". Since that day the import enters a visit of a REHAB stay at
#   fac67 / 61 and keeps at 21 the remaining visits of a rehab stay whose initial visit already sits on the chart at 21 (claimocity_import.py).
#   In every run this helper shows whether the visits at 61 are being paid, beside how the same kind of visit fared at 21.
#   WHAT IT READS: (1) the import registers of the registers folder (feed_import_<stamp>.json, the rows of "created"): a row with a charge
#   line at place of service 61 - the import writes 61 for a rehab stay only (stay.kind "rehab", pos_kind "rehab") - is the NEW GROUP; a
#   rehab-stay row that went in at 21 - the import marks it pos_kind "rehab-stay-kept-21" - is the COMPARISON GROUP; every other row is left
#   alone. A visit named in two registers stands as the later one says. (2) For each such visit at most ONE read of that visit's own history
#   per run (txh.fetch_visit - the read the runs already use: the charge rows with their bill date, carrier and balances, and their payment
#   lines with the reason codes). (3) Its own register of the run before.
#   WHAT A READ SHOWS (the visit is its hospital-visit line; where it has none, every line; a no-charge reporting line never counts):
#     paid         a payment of the PAYER on the line (never the patient's: a line without a reason code that AdvancedMD marks source 1 or,
#                  where it names no source, that names no carrier); a payment taken back with the other sign leaves nothing paid;
#     denied       a $0 payment line with a reason code that denies, and nothing paid. The codes that never deny are the ones the practice's
#                  ageing page (aging_refresh.py) never counts as a denial either: 45, 253, 23, 94, 246 and the cost shares 1, 2, 3;
#     answered $0  a $0 payment line whose codes are only those (the whole allowed amount is the patient's deductible, say): not a denial,
#                  and not lost - it has its own count and its own line, as "paid $0.00";
#     written off  nothing paid, no answer, and no balance left; open / unanswered: billed, no answer, up to 30 days / more than 30 days
#                  since the bill date; not billed: no bill date; voided: every charge of the visit reads void - not counted as entered
#                  (a visit a later save made again under a NEW visit id reads voided too: the new visit is not followed);
#     could not be read: the read failed or came back without a charge row of the visit - counted and named, never a reason to stop.
#   WHAT IT SAYS (printed, and kept word for word in the register under "lines" and "top" for the digest):
#     REHAB AT 61: N visit(s) entered; B billed; P paid ($X, average $Y per initial visit - at 21 the average was $138.67 on 95 paid of
#       121 sent); D denied (codes ...); O billed and unanswered for over 30 days - and behind it, only when there is one: paid low, answered
#       with $0, written off unpaid, not billed yet, could not be read, not read yet, voided since. With no rehab visit yet: one line.
#     REHAB STAYS KEPT AT 21 (the comparison group): the same numbers for the visits kept at 21.
#     REHAB PAID PER CODE - at 61 / at 21: the average payment of each code in the two groups.
#     TOP OF THE REPORT - PLACE OF SERVICE 61 DENIED: one line for EVERY denied visit at 61 - the visit, the chart, the date of service, the
#       carrier code, the reason / remark codes - ending "- for William: keep 61 or go back to 21 for this payer?". It is printed in every
#       run for as long as the visit carries a balance (also after it went out again: the line says so). A denied visit with no balance left
#       (written off) is printed in every run for 14 days from the day this monitor first saw it denied, then it stays in the count.
#     TOP OF THE REPORT - PLACE OF SERVICE 61 paid low: one line for every visit at 61 paid under 60% of the 21 average for its code (an
#       initial hospital visit: the $138.67 below; any other code: what the comparison group averages for it, once three of its visits are
#       paid - until then there is nothing to measure against and the row says so), and for every visit answered with $0. Printed in every
#       run for 14 days from the day this monitor first saw the visit so - whatever date AdvancedMD gives the payment; after that the visit
#       stays in the count "paid low" and in the register. (Nothing ends such a line by itself, so it is not repeated for ever: --line-days N
#       changes the 14 days, --line-days 0 keeps every line for as long as the visit is denied or paid low.)
#     REHAB MONITOR: what the numbers above do not hold - a visit that could not be read, an import register that could not be read, a
#       line riding with a paid visit (99497 / 99498) that is denied, the reads this run did not get to and why.
#   WHAT IT WRITES: registers/pos61_monitor.json and nothing else - visit ids, chart ids, dates of service, bill and payment dates, codes,
#   the state, the carrier CODE, reason codes and dollars; never a name, a birth date or a member number. Every value taken from AdvancedMD's
#   answer or from a register is kept only in the shape of what it is (an id, a date, a code, a number); an error is kept by its kind,
#   never by its words (they can name a patient). The register is also this helper's memory: a visit that is SETTLED - paid, or answered
#   with $0, with no insurance balance left on any of its lines; denied or unanswered with no balance left at all; voided - is not read
#   again (--all reads every visit again: a payment taken back after that is only seen then). What comes back from that memory is taken
#   over field by field in its shape too. No date older than the visit's own date of service is ever kept - not from AdvancedMD's answer
#   (a placeholder bill date; the payment still counts, without a day), not from the memory. Without the memory (a new workspace, a
#   register that cannot be read) every visit is read again and every line is said again for its 14 days - nothing is lost.
# Rules it uses: at most ONE history read per visit and run. A RUN NEVER HANGS ON THIS HELPER: it reads for 90 seconds at most (--seconds;
#   the clock is looked at before each read, so a call with the usual two-minute limit ends by itself) and 400 visits at most (--max); after
#   three reads in a row that AdvancedMD does not answer, or when the login fails, the reading stops for this run; a run stopped from outside
#   in the middle of a read (a time limit) still prints its lines and writes its register. Whose turn it is: the visits never asked for
#   first, then the ones asked for longest ago - so the next run goes on where this one stopped, and a visit that never answers holds up
#   nobody. A visit read before and not read today keeps what its last read showed and is marked stale; the lines and the counts say how
#   many visits were not read. With more unsettled visits than one run reads, a denial is seen a run or two later: give the helper more
#   time (--seconds 500 in a call with the ten-minute limit) rather than starting it twice. --dry and --live are the same run.
# Never: sends anything to AdvancedMD or to a payer - no save, no bill, no change of a place of service, of a facility or of a claim (whether
#   a payer's visits go back to 21 is William's decision: the lines ask him); reads a whole chart; writes anything but its own register.
# Usage (from the workspace; nightly/claimocity_feed_step.md says when):
#   python3 pos61_monitor.py [--registers registers] [--workspace <folder>] [--today 2026-12-20] [--seconds 90] [--max 400] [--line-days 14] [--all] [--dry | --live]
#   Without --registers the folder is <workspace>/registers: the workspace from --workspace, else BILLING_WORKSPACE, else the folder it is started in.
#   Without --today the days are counted from the run's own day (UTC). An option it does not know is refused, not passed over.
#   Exit 0 = it ran (also when visits could not be read: the lines say so); exit 2 = it did not run or could not write its register (one plain line).
import os, re, sys, json, glob, time, datetime, collections
import amd, txh
POS61_MONITOR_VERSION = "2026-11-25.1"      # this helper's own version (not the import's POS_RULE_VERSION): change it with EVERY revision of the monitor - it is written into the register
# THE FIXED HISTORY OF PLACE OF SERVICE 21 - what the same kind of visit did before the rule. Constants, not read anywhere at run time.
BASELINE_21 = {"sent": 121, "paid": 95, "average": 138.67, "denied_unpaid": 10}      # the practice's own AdvancedMD history pulled 11/10/2026: second initial hospital visits within 30 days at place of service 21 since 11/2025 - 121 sent, 95 paid, average $138.67 a paid visit, 10 denied and never paid
BASELINE_WORDS = "the practice's history of 11/10/2026"
INITIAL = {"99221", "99222", "99223"}                                                    # an initial hospital visit: it opens a stay (the import's rule)
HOSP_FAMILY = INITIAL | {"99231", "99232", "99233", "99238", "99239", "99234", "99235", "99236"}      # the import's hospital visit family (EM_FAMILY): the line that IS the visit
REPORTING = {"1123F", "1124F", "M0004"}                                                  # no-charge reporting lines (aging_refresh.py REPORTING): never the visit, never its answer
INFO_REASONS = ("45", "253", "23", "94", "1", "2", "3", "246")                           # aging_refresh.py INFO_REASONS, code for code: contractual / prior payer / informational, and the cost shares - never a denial (an empty list here = every $0 line with a reason code is a denial)
UNANSWERED_DAYS = 30        # billed and no answer for MORE than this many days = unanswered
UNDER_SHARE = 0.60          # paid UNDER this share of the 21 average for its code = paid low
MIN_COMPARE = 3             # the comparison group's average for a code is used once this many of its visits are paid
LINE_DAYS = 14              # how long a line is repeated once nothing more is open on the visit (--line-days)
MAX_READS = 400             # history reads in one run at most (--max)
SECONDS = 90                # the time one run reads for (--seconds; 0 = no limit): looked at before each read, so a call with the usual two-minute limit ends by itself
STOP_AFTER = 3              # reads in a row without an answer after which the reading stops for this run
PAUSE = 0.2                 # seconds between two reads
CLOCK = time.monotonic      # the clock the time of a run is taken from
QUESTION = "- for William: keep 61 or go back to 21 for this payer?"
OUT = "pos61_monitor.json"
BASE_LINE = "at 21 the average was $%.2f on %d paid of %d sent" % (BASELINE_21["average"], BASELINE_21["paid"], BASELINE_21["sent"])
FACT_KEYS = ("read", "code", "fee", "carrier", "billed", "paid", "paid_on", "pay_codes", "denial", "remarks", "denied_on", "resent", "zero_codes", "before", "balance", "ins_balance", "other", "answer", "void", "closed")
ROW_ORDER = ("visit", "chart", "dos", "cpts", "group", "batch", "initial", "sign", "state", "days", "said", "since", "read", "stale", "asked", "unread", "code", "fee", "carrier", "billed", "paid", "paid_on", "pay_codes", "low", "low_vs", "low_of",
             "denial", "remarks", "denied_on", "resent", "zero_codes", "before", "balance", "ins_balance", "other", "answer", "void", "closed")
class Unreadable(Exception):
    """A read that came back without what was asked for. Its words are this helper's own - never AdvancedMD's."""

# ---- every value in the shape of what it is: an id, a date, a code, a number ---------------------------------------------------------------
def num(x): return re.sub(r"\D", "", str(x or ""))
def f(x):
    """A dollar amount as a number; 0.0 for anything that is none (also "nan" and "inf": the register must stay plain JSON)."""
    try: v = float(str(x if x is not None else 0).replace(",", "").replace("$", "") or 0)
    except (TypeError, ValueError): return 0.0
    return v if (v == v and abs(v) != float("inf")) else 0.0
def day(x):
    """A date of AdvancedMD or of a register (11/28/2026, 2026-11-28, a time behind it or not) -> a date; None when it is no date."""
    s = str(x or "").strip(); m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})(?!\d)", s); iso = re.match(r"(\d{4})-(\d{2})-(\d{2})(?!\d)", s)
    try:
        if m: return datetime.date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
        if iso: return datetime.date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
    except ValueError: pass
    return None
def mdy(d): return d.strftime("%m/%d/%Y") if d else ""
def money(x): return "$" + format(round(float(x or 0), 2) + 0.0, ",.2f")
def cpt(x):
    s = str(x or "").strip().upper(); return s if re.fullmatch(r"\d{4}[0-9A-Z]|[A-Z]\d{4}", s) else ""      # a procedure code (99223, 1123F, M0004) - never five letters
def carrier_code(x):
    s = str(x or "").strip(); return s if re.fullmatch(r"[A-Za-z0-9]{1,12}", s) else ""      # a carrier CODE (FLO02) - anything else is left out
def kind_of(e): return re.sub(r"[^A-Za-z]", "", type(e).__name__)[:40] or "error"           # an error by its kind - never by its words
def reason(code):
    """One code of a payment line -> (kind, group letters, code): "carc" a reason code (CO45 -> CO, 45; a bare 45 too), "remark" a remark code
    (MA04, N620, M56), "odd" anything that has not the shape of a code (never written: it shows as "?"); None for an empty field."""
    raw = str(code or "").strip().upper()
    if not raw: return None
    c = raw.replace("-", "").replace(" ", "") if re.fullmatch(r"[A-Z0-9][A-Z0-9 \-]{0,7}", raw) else ""
    m = re.fullmatch(r"(CO|OA|PR|PI|CR)([A-Z]?\d{1,3})", c)
    if m: return ("carc", m.group(1), m.group(2))
    if re.fullmatch(r"(MA|M|N)\d{1,4}", c): return ("remark", "", c)
    if re.fullmatch(r"[A-Z]?\d{1,3}", c): return ("carc", "", c)
    return ("odd", "", "?")
def show(r):
    """A code as the report writes it: CO-58, a bare 58, N620, "?"."""
    return "" if not r else ("%s-%s" % (r[1], r[2]) if r[1] else r[2])
def denies(r):
    """Does this code make a $0 payment line a denial? Every reason code but INFO_REASONS; a code this helper cannot read counts as one."""
    return r[0] == "odd" or (r[0] == "carc" and r[2] not in INFO_REASONS)
def codes_of(xs): return sorted({c for c in (show(reason(x)) for x in (xs if isinstance(xs, list) else []) if isinstance(x, str)) if c})

# ---- the import registers: which rows are rehab-stay visits -----------------------------------------------------------------------------
def kinds(row):
    """The row's pos_kind words: the import writes one per charge line (a list); one word alone is read the same."""
    k = row.get("pos_kind"); return {str(x) for x in (k if isinstance(k, (list, tuple)) else [k]) if x}
def group_of(row):
    """"61" = a visit with a charge line at place of service 61 (the new group: the import writes 61 for a rehab stay only); "21" = a rehab-stay
    visit that went in at 21 (the comparison group - the import marks it rehab-stay-kept-21); "other" = a rehab-stay row at neither (named,
    never read); None = no rehab-stay visit at all."""
    st = row.get("stay") if isinstance(row.get("stay"), dict) else {}
    lines = [str(x) for x in (row.get("pos_lines") if isinstance(row.get("pos_lines"), list) and row.get("pos_lines") else [row.get("pos")]) if x not in (None, "")]
    if "61" in lines: return "61"
    if "rehab-stay-kept-21" in kinds(row): return "21"
    if st.get("kind") != "rehab": return None
    return "21" if (lines and all(x == "21" for x in lines)) else "other"
def import_rows(regdir):
    """({key: (row, batch stamp, group)}, [import registers that could not be read]) - the rehab-stay rows of "created" of every import register,
    oldest register first: a visit named in two registers stands as the later one says."""
    rows = {}; bad = []
    for path in sorted(glob.glob(os.path.join(regdir, "feed_import_*.json"))):
        name = os.path.basename(path)
        if name.endswith("_decisions.json"): continue
        try:
            with open(path) as fh: reg = json.load(fh)
            if not isinstance(reg, dict): raise ValueError("not a register")
        except Exception: bad.append(name); continue
        for r in reg.get("created") if isinstance(reg.get("created"), list) else []:
            try:      # row by row: a row that is not what the import writes is passed over, the rows after it are still read
                key = ("vst" + num(r.get("visit"))) if num(r.get("visit")) else "no visit|%s|%s|%s" % (num(r.get("pid")), mdy(day(r.get("dos"))), "+".join(cpt(x) for x in r.get("cpts") or []))
                g = group_of(r)
            except Exception: continue
            if g is None: rows.pop(key, None)
            else: rows[key] = (r, name[len("feed_import_"):-len(".json")], g)
    return rows, bad
def static(r, stamp, g):
    """What the import register says of the visit - ids, the date of service, the codes, the stay - each in its own shape."""
    st = r.get("stay") if isinstance(r.get("stay"), dict) else {}; sign = str(st.get("sign") or "")
    return {"visit": ("vst" + num(r.get("visit"))) if num(r.get("visit")) else "", "chart": ("pat" + num(r.get("pid"))) if num(r.get("pid")) else "", "dos": mdy(day(r.get("dos"))),
            "cpts": [c for c in (cpt(x) for x in (r.get("cpts") if isinstance(r.get("cpts"), list) else [])) if c], "group": g, "batch": stamp if re.fullmatch(r"[0-9A-Za-z_]+", stamp) else "",
            "initial": mdy(day(st.get("initial"))), "sign": sign if re.fullmatch(r"[a-z0-9 \-]{0,60}", sign) else ""}
def kept_day(x, dos):
    """A date of the register of the run before, as text - "" when it is no date, or a date before the visit's own date of service (no bill,
    payment or run of this monitor is older than the visit: such a date is not what the field says it is, and is not carried on)."""
    d = day(x); return mdy(d) if d and not (dos and d < dos) else ""
def tidy(old, dos=None):
    """The facts an earlier run wrote for a visit, taken over field by field and only in the shape each field has: the register comes back
    through the repository, and nothing that is not a date, a code, a state word or a number is ever carried on."""
    out = {}
    for k in ("read", "billed", "paid_on", "denied_on", "resent"):
        if kept_day(old.get(k), dos): out[k] = kept_day(old.get(k), dos)
    for k in ("fee", "paid", "balance", "ins_balance"):
        if isinstance(old.get(k), (int, float)) and not isinstance(old.get(k), bool): out[k] = round(f(old[k]), 2)
    for k in ("pay_codes", "denial", "remarks", "zero_codes", "before"):
        if codes_of(old.get(k)): out[k] = codes_of(old.get(k))
    if cpt(old.get("code")): out["code"] = cpt(old.get("code"))
    if carrier_code(old.get("carrier")): out["carrier"] = carrier_code(old.get("carrier"))
    out["answer"] = old.get("answer") if old.get("answer") in ("paid", "denied", "zero", "none") else "none"
    if old.get("void") is True: out["void"] = True
    oth = [{"code": cpt(x.get("code")), "answer": x.get("answer") if x.get("answer") in ("paid", "denied", "zero", "none") else "none", "paid": round(f(x.get("paid")), 2),
            "denial": codes_of(x.get("denial")), "balance": round(f(x.get("balance")), 2)} for x in (old.get("other") if isinstance(old.get("other"), list) else []) if isinstance(x, dict)]
    if oth: out["other"] = oth
    out["closed"] = old.get("closed") is True and settled(out)      # settled only when the row says so AND the facts taken over bear it out - otherwise the visit is read again
    return out if out.get("read") else {}
def settled(fa):
    """Nothing more is expected of the payer for this visit: it is voided; or no insurance balance is left on any of its lines and it is paid
    or answered with $0; or no balance is left at all (a denial written off, a visit written off unpaid). A fact that is missing settles nothing."""
    if fa.get("void"): return True
    ins = fa.get("ins_balance"); bal = fa.get("balance")
    if ins is None or ins > 0.005: return False
    return fa.get("answer") in ("paid", "zero") or (bal is not None and bal <= 0.005 and (fa.get("answer") == "denied" or (fa.get("fee") or 0) > 0.005))
def previous(path):
    """{visit: its row} of the register the run before wrote. A register that is not there or cannot be read is no memory: every visit is read again."""
    try:
        with open(path) as fh: return {str(v["visit"]): v for v in json.load(fh).get("visits") or [] if isinstance(v, dict) and v.get("visit")}
    except Exception: return {}

# ---- ONE read of a visit's own history -----------------------------------------------------------------------------------------------------
def patient_line(p, reasons):
    """A payment line of the PATIENT, not the payer's answer: AdvancedMD marks it source 1; where it gives no source, a line with no carrier.
    A line that carries a reason code is always the payer's."""
    if reasons: return False
    src = str(p.get("source") or "").strip()
    return src == "1" if src else not str(p.get("carrier") or "").strip()
def facts(root, vid, dos=None):
    """What ONE read of a visit's history shows -> the facts of the visit as the register keeps them (dates as text), or None when the answer
    holds no charge row of the visit. Amounts are stored as credits (negative) in this history: they are netted and read without the sign.
    A bill date or a payment date older than the visit's own date of service (dos) is no such date - a placeholder, or another field's value -
    and is not kept: the payment still counts, without a day."""
    lines = []; seen = 0; day_ = lambda x: (lambda d: d if (d and not (dos and d < dos)) else None)(day(x))
    for c in root.iter("charge"):
        v = num(c.get("visit") or c.get("visitid"))
        if v and v != num(vid): continue                                                  # a row of another visit
        seen += 1
        if c.get("void") == "1" or str(c.get("fee") or "").strip().startswith("-"): continue      # a void charge; a reversal row
        code = cpt(c.get("proccode"))
        if code in REPORTING: continue
        real = []; zero = []                                                              # (dollars, day, carrier, codes) of the payer's payments; (day, carrier, codes) of its $0 lines
        for p in c.iter("payment"):
            if p.get("void") == "1": continue
            rs = [r for r in (reason(x.get("code") or x.get("reasoncode")) for x in p.iter("payreason")) if r]
            amt = f(p.get("amount")); when = day_(p.get("date")) or day_(p.get("createtime")); car = carrier_code(p.get("carrier"))
            if abs(amt) > 0.005:
                if not patient_line(p, rs): real.append((amt, when, car, rs))
            elif rs: zero.append((when, car, rs))
        paid = round(abs(sum(x[0] for x in real)), 2); deny = [z for z in zero if any(denies(r) for r in z[2])]
        ln = {"code": code, "fee": round(f(c.get("fee")), 2), "billed": day_(c.get("billdate")), "carrier": carrier_code(c.get("carrier") or c.get("carriercode")),
              "ins": round(f(c.get("insbal") or c.get("insbalance")), 2), "pat": round(f(c.get("patbal") or c.get("patbalance")), 2), "paid": paid if paid > 0.005 else 0.0, "answer": "none", "codes": []}
        if ln["paid"]:
            top = max(real, key=lambda x: x[1] or datetime.date.min)
            ln.update(answer="paid", when=top[1], payer=top[2], codes=sorted({show(r) for x in real for r in x[3] if r[0] != "remark"}), before=sorted({show(r) for z in deny for r in z[2] if denies(r)}))
        elif deny:
            top = max(deny, key=lambda x: x[0] or datetime.date.min)
            ln.update(answer="denied", when=top[0], payer=top[1], codes=sorted({show(r) for z in deny for r in z[2] if denies(r)}), remarks=sorted({show(r) for z in zero for r in z[2] if r[0] == "remark"}))
        elif zero:
            top = max(zero, key=lambda x: x[0] or datetime.date.min)
            ln.update(answer="zero", when=top[0], payer=top[1], codes=sorted({show(r) for z in zero for r in z[2] if r[0] != "remark"}))
        lines.append(ln)
    if not seen: return None
    if not lines: return {"void": True, "answer": "none", "closed": True}      # every charge of the visit reads void
    main = [l for l in lines if l["code"] in HOSP_FAMILY]; other = [l for l in lines if l["code"] not in HOSP_FAMILY] if main else []; main = main or lines
    ans = lambda a: [l for l in main if l["answer"] == a]
    answer = "denied" if ans("denied") else "paid" if ans("paid") else "zero" if ans("zero") else "none"      # the worst answer of the visit's own line(s) leads
    top = max(ans(answer), key=lambda l: l.get("when") or datetime.date.min); billed = max((l["billed"] for l in main if l["billed"]), default=None)
    fa = {"code": next((l for l in main if l["code"] in INITIAL), main[0])["code"], "fee": round(sum(l["fee"] for l in main), 2), "carrier": top.get("payer") or next((l["carrier"] for l in main if l["carrier"]), ""),
          "billed": mdy(billed), "paid": round(sum(l["paid"] for l in main), 2), "balance": round(sum(l["ins"] + l["pat"] for l in main), 2), "ins_balance": round(sum(l["ins"] for l in lines), 2), "answer": answer}
    if answer == "paid":
        fa.update(paid_on=mdy(max((l["when"] for l in ans("paid") if l.get("when")), default=None)), pay_codes=sorted({c for l in ans("paid") for c in l["codes"]}), before=sorted({c for l in ans("paid") for c in l.get("before") or []}))
    elif answer == "denied":
        fa.update(denial=sorted({c for l in ans("denied") for c in l["codes"]}), remarks=sorted({c for l in ans("denied") for c in l.get("remarks") or []}), denied_on=mdy(top.get("when")))
        if billed and top.get("when") and billed > top["when"]: fa["resent"] = mdy(billed)      # it went out again after the denial
    elif answer == "zero":
        fa.update(zero_codes=sorted({c for l in ans("zero") for c in l["codes"]}), paid_on=mdy(top.get("when")))
    if other: fa["other"] = [{"code": l["code"], "answer": l["answer"], "paid": l["paid"], "denial": l["codes"] if l["answer"] == "denied" else [], "balance": round(l["ins"] + l["pat"], 2)} for l in other]
    fa["closed"] = settled(fa)
    return fa
def state_of(r, today):
    """(the visit's state today, days since it was billed - for a visit still waiting) from what its last read showed."""
    if not r.get("read"): return ("could not be read" if r.get("unread") else "not read yet"), None
    if r.get("void"): return "voided", None
    a = r.get("answer")
    if a in ("paid", "denied"): return a, None
    if a == "zero": return "answered $0", None
    if (r.get("balance") or 0) <= 0.005 and (r.get("fee") or 0) > 0.005: return "written off", None
    b = day(r.get("billed"))
    if not b: return "not billed", None
    return ("unanswered" if (today - b).days > UNANSWERED_DAYS else "open"), (today - b).days

# ---- the numbers and the lines ----------------------------------------------------------------------------------------------------------------
def tally(rows, group):
    rs = [r for r in rows if r["group"] == group]; live = [r for r in rs if r["state"] != "voided"]
    S = lambda *names: [r for r in live if r["state"] in names]
    cnt = lambda rws, key: dict(sorted(collections.Counter(c for r in rws for c in r.get(key) or []).items(), key=lambda kv: (-kv[1], kv[0])))
    paid = S("paid"); den = S("denied"); zero = S("answered $0"); ini = [r for r in paid if r.get("code") in INITIAL]
    return {"entered": len(live), "billed": len([r for r in live if r.get("read") and (r.get("billed") or r.get("answer") in ("paid", "denied", "zero"))]), "paid": len(paid),
            "paid_dollars": round(sum(r.get("paid") or 0 for r in paid), 2), "initial_paid": len(ini), "initial_average": round(sum(r.get("paid") or 0 for r in ini) / len(ini), 2) if ini else None,
            "denied": len(den), "denied_codes": cnt(den, "denial"), "denied_written_off": len([r for r in den if (r.get("balance") or 0) <= 0.005]), "unanswered": len(S("unanswered")), "open": len(S("open")),
            "not_billed": len(S("not billed")), "paid_low": len([r for r in paid if r.get("low")]), "zero_answer": len(zero), "zero_codes": cnt(zero, "zero_codes"), "written_off": len(S("written off")),
            "unread": len(S("could not be read", "not read yet")), "could_not_be_read": len(S("could not be read")), "not_read_yet": len(S("not read yet")), "voided": len(rs) - len(live)}
def x_codes(d): return ", ".join("%s x%d" % kv for kv in d.items())
def said(c, low):
    """The parts both group lines share: denied with its codes, unanswered, and - only where there is one - what the first numbers do not hold."""
    den = "%d denied" % c["denied"] + ((" (codes %s%s)" % (x_codes(c["denied_codes"]), (" - %d of them written off since" % c["denied_written_off"]) if c["denied_written_off"] else "")) if c["denied"] else "")
    more = [("%d paid low" % c["paid_low"]) if (low and c["paid_low"]) else "", ("%d answered with $0 and no denial code (%s)" % (c["zero_answer"], x_codes(c["zero_codes"]))) if c["zero_answer"] else "",
            ("%d written off unpaid" % c["written_off"]) if c["written_off"] else "", ("%d not billed yet" % c["not_billed"]) if c["not_billed"] else "", ("%d could not be read" % c["could_not_be_read"]) if c["could_not_be_read"] else "",
            ("%d not read yet" % c["not_read_yet"]) if c["not_read_yet"] else "", ("%d voided since (not counted)" % c["voided"]) if c["voided"] else ""]
    return "%s; %d billed and unanswered for over %d days%s" % (den, c["unanswered"], UNANSWERED_DAYS, "".join("; " + m for m in more if m))
def average21(code, cmp):
    """(the 21 average a payment of this code is measured against, where it comes from) - (None, why) while there is none."""
    if code in INITIAL: return BASELINE_21["average"], BASELINE_WORDS
    xs = cmp.get(code) or []
    if len(xs) >= MIN_COMPARE: return round(sum(xs) / len(xs), 2), "%d paid visit(s) of the comparison group" % len(xs)
    return None, "no 21 average for %s yet" % (code or "this code")
def who(r): return " ".join(x for x in (r.get("visit"), r.get("chart"), ("service date " + r["dos"]) if r.get("dos") else "") if x)
def top_lines(rows, today, line_days):
    """The TOP OF THE REPORT lines of the visits at 61: every denied visit first, then every visit paid low or answered with $0. A line is
    repeated in every run for line_days days from the day this monitor first saw the visit so (0 = always) - a denied visit that still
    carries a balance keeps its line for as long as it does."""
    den = []; low = []; fresh = lambda r: line_days == 0 or not day(r.get("since")) or (today - day(r["since"])).days <= line_days
    for r in rows:
        if r["group"] != "61": continue
        head = "%s %s carrier %s" % (who(r), r.get("code") or "+".join(r.get("cpts") or []) or "?", r.get("carrier") or "not named")
        if r["state"] == "denied" and ((r.get("balance") or 0) > 0.005 or fresh(r)):
            rem = r.get("remarks") or []
            den.append("TOP OF THE REPORT - PLACE OF SERVICE 61 DENIED: %s denied%s with %s%s, balance %s%s%s %s" % (head, (" " + r["denied_on"]) if r.get("denied_on") else "", ", ".join(r.get("denial") or ["?"]),
                       (" (remark%s %s)" % ("s" if len(rem) > 1 else "", ", ".join(rem))) if rem else "", money(r.get("balance")), " (written off since)" if (r.get("balance") or 0) <= 0.005 else "",
                       (", sent again %s - no answer yet" % r["resent"]) if r.get("resent") else "", QUESTION))
        elif r["state"] == "paid" and r.get("low") and fresh(r):
            low.append("TOP OF THE REPORT - PLACE OF SERVICE 61 paid low: %s paid %s%s - under %d%% of the %s average at 21 for %s (%s) %s" % (head, money(r.get("paid")), (" on " + r["paid_on"]) if r.get("paid_on") else "",
                       round(UNDER_SHARE * 100), money(r.get("low_vs")), r.get("code") or "its code", r.get("low_of") or "", QUESTION))
        elif r["state"] == "answered $0" and fresh(r):
            low.append("TOP OF THE REPORT - PLACE OF SERVICE 61 paid low: %s paid $0.00%s - the payer's answer carries only cost-share / contractual codes (%s), no denial code %s" % (head, (" on " + r["paid_on"]) if r.get("paid_on") else "",
                       ", ".join(r.get("zero_codes") or ["none"]), QUESTION))
    return den + low

# ---- the reads ---------------------------------------------------------------------------------------------------------------------------------
def turn(r):
    """Whose turn it is: the visit asked for longest ago first (never asked = first of all); among the visits asked for on one day, the ones
    still waiting for the payer's answer before the ones that are paid and only wait for a second payer; then the oldest date of service."""
    asked = max([d for d in (day(r.get("read")), day(r.get("asked"))) if d] or [datetime.date.min])
    return (asked, 0 if not r.get("read") else 2 if r.get("answer") in ("paid", "zero") else 1, day(r["dos"]) or datetime.date.min, r["visit"])
def read_visits(due, today, cap, seconds):
    """At most ONE history read for each visit of the list, in the list's order -> (reads tried, why the reading ended early or "").
    Nothing leaves a single visit's read: a read that fails is written on its row (the error's kind, never its words) and the next visit is
    read. The reading ends early at --max reads, when --seconds are used up (looked at before each read), after STOP_AFTER reads in a row that
    AdvancedMD did not answer, when the login fails, and when the run is stopped from outside (a time limit) - what was read stands."""
    import signal
    tried = 0; fails = 0; ended = ""; t0 = CLOCK(); keep = signal.getsignal(signal.SIGTERM) if hasattr(signal, "SIGTERM") else None; hooked = False
    def _stopped(*_a): raise SystemExit("stopped from outside")
    try:
        try: signal.signal(signal.SIGTERM, _stopped); hooked = True      # a time limit ends the READING, not the report: the lines and the register are still written
        except (ValueError, AttributeError, OSError): hooked = False     # (not the main thread, or no such signal here)
        for r in due:
            if tried >= cap: ended = "cap"; break
            if seconds and CLOCK() - t0 >= seconds: ended = "time"; break
            if not tried:
                try: amd.login_cached()
                except Exception as e: ended = "login " + kind_of(e); break
            tried += 1; r["_asked"] = True; r.pop("unread", None); r["asked"] = mdy(today)
            try: root = txh.fetch_visit(num(r["chart"]), num(r["visit"]))
            except Exception as e:      # AdvancedMD did not answer this read
                r["unread"] = kind_of(e); fails += 1
                if fails >= STOP_AFTER: ended = "silent"; break
                time.sleep(PAUSE); continue
            fails = 0
            try:
                fa = facts(root, r["visit"], day(r["dos"]))
                if fa is None: raise Unreadable("no charge row in the answer")
                for k in FACT_KEYS: r.pop(k, None)
                r.update(fa); r["read"] = mdy(today); r.pop("asked", None)
            except Exception as e: r["unread"] = str(e) if isinstance(e, Unreadable) else kind_of(e)      # an answer this helper cannot work out: this visit only
            time.sleep(PAUSE)
    except SystemExit: ended = "stopped"
    finally:
        if hooked:
            try: signal.signal(signal.SIGTERM, keep if keep is not None else signal.SIG_DFL)
            except (ValueError, TypeError, OSError): pass
    return tried, ended

def main(argv=None):
    """The monitor's run -> its exit code. An error of this helper's own ends it with ONE plain line - the error's kind and the line of this
    file, never the error's words - and exit 2: it is never a traceback in a run's log, and never a reason for a run to stop."""
    try: return monitor(argv)
    except Exception as e:
        here = main.__code__.co_filename; n = 0; tb = e.__traceback__
        while tb is not None:
            if tb.tb_frame.f_code.co_filename == here: n = tb.tb_lineno
            tb = tb.tb_next
        print("REHAB MONITOR: the monitor ended on an error of its own (%s at line %d of pos61_monitor.py) - nothing was sent anywhere; the next run tries again" % (kind_of(e), n)); return 2
def monitor(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    def stop(words): print("pos61_monitor: " + words + " - nothing read, nothing written"); return 2
    known = ("--registers", "--workspace", "--today", "--max", "--seconds", "--line-days", "--all", "--dry", "--live"); numbers = ("--max", "--seconds", "--line-days"); takes = ("--registers", "--workspace", "--today") + numbers
    vals = {}; i = 0
    while i < len(a):
        if a[i] not in known: return stop("it does not know '%s'" % str(a[i])[:40])
        if a[i] in takes:
            if i + 1 >= len(a) or a[i + 1].startswith("--"): return stop("%s needs a %s after it" % (a[i], "number" if a[i] in numbers else "day" if a[i] == "--today" else "folder"))
            vals[a[i]] = a[i + 1]; i += 1
        i += 1
    ALL = "--all" in a      # "--dry" and "--live" are taken and change nothing: this helper never sends anything, so there is nothing to hold back
    today = day(vals["--today"]) if "--today" in vals else datetime.datetime.now(datetime.timezone.utc).date()
    if today is None: return stop("--today needs a day as 2026-12-20 or 12/20/2026")
    try: cap = int(vals.get("--max", MAX_READS)); seconds = int(vals.get("--seconds", SECONDS)); line_days = int(vals.get("--line-days", LINE_DAYS))
    except ValueError: return stop("--max, --seconds and --line-days need a number after them")
    if cap < 1 or seconds < 0 or line_days < 0: return stop("--max needs a number from 1, --seconds and --line-days a number from 0")
    ws = vals.get("--workspace") or os.environ.get("BILLING_WORKSPACE") or ""
    regdir = vals.get("--registers") or os.path.join(ws, "registers")
    if not os.path.isdir(regdir): return stop("registers folder not found: %s (start it in the workspace, or name the folder with --registers)" % regdir)
    path = os.path.join(regdir, OUT); found, bad = import_rows(regdir); prev = previous(path)
    rows = []; other = []
    for key, (r, stamp, g) in found.items():
        row = static(r, stamp, g)
        if g == "other": other.append(row); continue
        old = prev.get(row["visit"]) if row["visit"] else None
        if isinstance(old, dict) and old.get("chart") == row["chart"]:      # what the run before knew of this visit: the facts of its last read, when it was last asked for, since when its line is said
            row.update(tidy(old, day(row["dos"])))
            for k in ("asked", "since"):
                if kept_day(old.get(k), day(row["dos"])): row[k] = kept_day(old.get(k), day(row["dos"]))
            if old.get("said") in ("denied", "paid low"): row["said"] = old["said"]
        if not row["visit"]: row["unread"] = "no visit id in the import register"
        elif not row["chart"]: row["unread"] = "no chart id in the import register"
        rows.append(row)
    rows.sort(key=lambda r: (r["group"] != "61", day(r["dos"]) or datetime.date.min, r["visit"], r["chart"]))
    # ---- the reads: a settled visit is not read again (--all: every visit) ---------------------------------------------------------------------------
    due = sorted([r for r in rows if r["visit"] and r["chart"] and (ALL or not r.get("read") or not r.get("closed"))], key=turn)
    tried, ended = read_visits(due, today, cap, seconds) if due else (0, "")
    waiting = [r for r in due if not r.pop("_asked", False)]
    for r in due:
        if r.get("read") and r["read"] != mdy(today): r["stale"] = True      # read before, not read today: what the last read showed stands
    # ---- today's state of every visit, the low payments, and since when a visit has its line ---------------------------------------------------------
    for r in rows:
        r["state"], d = state_of(r, today)
        if d is not None: r["days"] = d
        if r.get("read") and not r.get("code"): r["code"] = r["cpts"][0] if r["cpts"] else ""
    cmp = collections.defaultdict(list)
    for r in rows:
        if r["group"] == "21" and r["state"] == "paid": cmp[r.get("code") or ""].append(r.get("paid") or 0)
    for r in rows:
        if r["group"] == "61" and r["state"] == "paid":
            avg, src = average21(r.get("code") or "", cmp); r["low_of"] = src
            if avg is not None:
                r["low_vs"] = avg
                if (r.get("paid") or 0) < UNDER_SHARE * avg - 1e-9: r["low"] = True
        kind = "" if r["group"] != "61" else "denied" if r["state"] == "denied" else "paid low" if (r["state"] == "answered $0" or r.get("low")) else ""
        if not kind: r.pop("said", None); r.pop("since", None)
        elif r.get("said") != kind or not day(r.get("since")): r["said"] = kind; r["since"] = mdy(today)      # first seen so today
    c61 = tally(rows, "61"); c21 = tally(rows, "21"); n61 = len([r for r in rows if r["group"] == "61"]); n21 = len([r for r in rows if r["group"] == "21"])
    lines = []
    if not n61: lines.append("REHAB AT 61: no inpatient-rehab visit has been entered%s yet%s (%s)" % (" at place of service 61" if n21 else "", "" if n21 else " - nothing to monitor", BASE_LINE))
    else: lines.append("REHAB AT 61: %d visit(s) entered; %d billed; %d paid (%s, %s - %s); %s" % (c61["entered"], c61["billed"], c61["paid"], money(c61["paid_dollars"]),
                       ("average %s per initial visit" % money(c61["initial_average"])) if c61["initial_average"] is not None else "no initial visit paid yet", BASE_LINE, said(c61, True)))
    if n21: lines.append("REHAB STAYS KEPT AT 21 (the comparison group): %d visit(s) entered; %d billed; %d paid (%s); %s" % (c21["entered"], c21["billed"], c21["paid"], money(c21["paid_dollars"]), said(c21, False)))
    by = {}
    for r in rows:
        if r["state"] == "paid" and r.get("code"): by.setdefault(r["code"], {"61": [], "21": []})[r["group"]].append(r.get("paid") or 0)
    by_code = {}
    for code in sorted(by):
        p61 = by[code]["61"]; p21 = by[code]["21"]
        by_code[code] = {"at 61": {"paid": len(p61), "average": round(sum(p61) / len(p61), 2) if p61 else None},
                         "at 21": {"paid": BASELINE_21["paid"], "average": BASELINE_21["average"], "from": BASELINE_WORDS} if code in INITIAL else {"paid": len(p21), "average": round(sum(p21) / len(p21), 2) if p21 else None, "from": "the comparison group"}}
    if by_code:
        side = lambda s: ("%s x%d" % (money(s["average"]), s["paid"])) if s["average"] is not None else "none yet"
        lines.append("REHAB PAID PER CODE - at 61 / at 21: " + "; ".join("%s %s / %s%s" % (code, side(v["at 61"]), side(v["at 21"]), (" (%s)" % BASELINE_WORDS) if code in INITIAL else "") for code, v in by_code.items()))
    top = top_lines(rows, today, line_days)
    # ---- what the numbers do not hold ------------------------------------------------------------------------------------------------------------------
    noted = []; nxt = "%d visit(s) were not read and wait for the next run" % len(waiting)
    if bad: noted.append("REHAB MONITOR: %d import register(s) could not be read - their visits are not in the counts above: %s" % (len(bad), ", ".join(bad[:20])))
    if ended.startswith("login"): noted.append("REHAB MONITOR: the login to AdvancedMD failed (%s) - nothing was read in this run; %s" % (ended[6:], nxt))
    if ended == "silent": noted.append("REHAB MONITOR: AdvancedMD did not answer %s reads in a row - the reading stopped for this run; %s" % ({2: "two", 3: "three", 4: "four", 5: "five"}.get(STOP_AFTER, str(STOP_AFTER)), nxt))
    if ended == "stopped": noted.append("REHAB MONITOR: the run was stopped from outside (a time limit) after %d read(s) - what was read stands; %s" % (tried, nxt))
    if ended == "cap": noted.append("REHAB MONITOR: %d visit(s) were not read in this run (--max %d reads a run) - the next run reads them first" % (len(waiting), cap))
    if ended == "time": noted.append("REHAB MONITOR: %d visit(s) were not read in this run (--seconds %d: the time of one run was used up after %d read(s)) - the next run reads them first" % (len(waiting), seconds, tried))
    unread = [r for r in rows if r.get("unread")]
    if unread: noted.append("REHAB MONITOR: %d visit(s) could not be read this run: %s" % (len(unread), "; ".join("%s (%s%s)" % (who(r), r["unread"], (" - what the read of %s showed stands" % r["read"]) if r.get("read") else "") for r in unread[:40])
                            + (" ... and %d more, each in the register" % (len(unread) - 40) if len(unread) > 40 else "")))
    riding = ["%s %s (%s)" % (who(r), o["code"] or "a line", ", ".join(o["denial"]) or "?") for r in rows if r["group"] == "61" and r["state"] == "paid" for o in r.get("other") or [] if o["answer"] == "denied" and o["balance"] > 0.005]
    if riding: noted.append("REHAB MONITOR: %d line(s) riding with a paid visit at 61 are denied - not a place-of-service line of this monitor, the denial work lists carry them: %s" % (len(riding), "; ".join(riding[:20])))
    if other: noted.append("REHAB MONITOR: %d rehab-stay row(s) of the import registers stand at neither 61 nor 21 - not read, not counted: %s" % (len(other), "; ".join(who(r) for r in other[:20])))
    quiet = not rows and not noted      # no rehab-stay visit at all and nothing else to say: ONE printed line, with the register named in it
    for l in ([] if quiet else lines + top + noted): print(l)
    reg = {"what": "read-only payment monitor of the inpatient-rehab visits at place of service 61 (pos61_monitor.py): chart ids, visit ids, dates of service, codes, carrier codes, reason codes and dollars - no name, no birth date and no member number is ever written here",
           "version": POS61_MONITOR_VERSION, "at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "today": mdy(today), "mode": "read only - nothing is ever sent to AdvancedMD; --dry and --live are the same run",
           "baseline_21": dict(BASELINE_21), "limits": {"unanswered_days": UNANSWERED_DAYS, "low_share": UNDER_SHARE, "min_compare": MIN_COMPARE, "line_days": line_days, "max_reads": cap, "seconds": seconds},
           "counts": {"at 61": c61, "kept at 21": c21}, "by_code": by_code, "reads": tried, "ended": ended.split(" ")[0], "unreadable_registers": bad, "lines": lines + noted, "top": top,
           "visits": [{k: r[k] for k in ROW_ORDER if k in r and r[k] is not None and r[k] != "" and r[k] != []} for r in rows]}
    tmp = path + ".tmp"
    try:
        with open(tmp, "w") as fh: json.dump(reg, fh, indent=1, allow_nan=False)
        os.replace(tmp, path)      # whole or not at all: the register is the next run's memory
    except Exception as e:
        try: os.remove(tmp)
        except OSError: pass
        for l in (lines if quiet else []): print(l)
        print("REHAB MONITOR: its register %s could not be written (%s) - the lines above stand; the next run reads again what this run read" % (path, kind_of(e))); return 2
    print(("%s - register: %s" % (lines[0], path)) if quiet else "register: %s" % path)
    return 0

if __name__ == "__main__": sys.exit(main())
