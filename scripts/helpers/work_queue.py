#!/usr/bin/env python3
# PLAIN ENGLISH (the WORK QUEUE planner - William 11/26/2026, his answers to the denials / unpaid questions: "Yes, act")
# Decides: for every denied claim and every claim unpaid past 30 days, the NEXT STEP by William's standing rules, the rule id that
#   decided it, whose turn it is (claude = the actor does it; run = the run's RULE C cascade; william = one card on the Insurance Refresh
#   Board; wait / hold = nothing now), the due date, the tries so far and the payer's claim number (ICN) when the data has one.
#   It READS ONLY: the OPEN rows of working_denials_latest.json, the era_denials_*.json lines not yet worked (denials of checks era_clear
#   dismissed - until 11/26/2026 no helper read them), the CORRECT & RESEND and WRITE OFF rows of aging_latest.json, and the claim-status
#   ledger's answers (paid / finalized at $0 / denied / not found / not eligible / handed off) with the check numbers and payer claim
#   numbers of the claimstatus_*.json run files. It writes registers/work_queue.json - one row per visit: visit, chart and charge ids,
#   payer and procedure codes, denial and remark codes, dates, dollars, the step, the rule id, the turn, tries - NEVER a name, a birth
#   date or a member number (the repository is public; the chart NUMBER some remits carry is not copied either).
# Rules it uses (the RULES table below cites each one): a write-off only with a code the rulebook names (WOLATE, WONCS, WOINS, WOCLTREQ,
#   WOCAID2ND, WOINSBANK) and only where a rule says so - the 11/2 rule (aging WRITE OFF rows past 12 months, by the rule that decided
#   them), CCM to straight Medicaid and CCM denied on hospice (WONCS), a Medicaid-family plan's $0 secondary answer (WOCAID2ND), paid
#   but never posted (WOINSBANK, only after a Treasury deposit matches the check - the actor checks); a primary claim past 12 months is
#   never sent again (rules.md 11/20/2026: listed for William); a rebill only on a denial, a final answer, 'not on file' or a claim
#   silent past the aging limits of a payer that has no claim-status route; nothing on FLO99 balances, the timely-filing watch, a chart
#   held on William's turn, the AET12 hold, a date-of-death case or a visit the queue acted on in the last 30 days.
# Never touches: AMD, Stedi, Drive, the board. The actor (work_queue_act.py) acts, dry unless --live.
#   python3 work_queue.py [--repo /home/claude/effinger-billing-backend] [--registers registers] [--out registers/work_queue.json]
#   python3 work_queue.py sent <visit id> [--date YYYY-MM-DD]     # William's 'sent' note on an appeal card: the 30-day follow-up starts
#   python3 work_queue.py merge [--repo <clone>] [--registers registers]   # right before a live pass (after git pull --ff-only): the repository's
#       work_queue_act_*.jsonl and rebill_log.jsonl lines this workspace lacks are appended to its registers (overlapping runs)
# 11/26/2026, the independent review's fixes: WOINSBANK only on a Treasury row whose status is exactly MATCHED; a 'primary paid - bill the
#   secondary' row whose claim was billed on/after the primary's payment is never billed again (the secondary already holds it - rules.md
#   9/21/2026): its answer is awaited 61 days, then its claim status goes to William (one card: ask the payer); a visit the actor's deceased
#   guard did not clear (a HOLD-DEATH register line) is held for good; a line
#   that wrote in AdvancedMD (the re-date's new visit) counts as acted at once.
import argparse, collections, csv, datetime, glob, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path: sys.path.insert(0, HERE)
for _p in (os.path.join(os.path.dirname(os.path.dirname(HERE)), "boards"),):
    if os.path.isdir(_p) and _p not in sys.path: sys.path.append(_p)
from working_denials import triage_line, norm, DISPO_ORDER, CCM_CODES      # the ONE table (TABLE in working_denials.py) through the board's own triage

WORK_QUEUE_VERSION = "2026-11-26.1"
ALLOWED_WO = ("WOLATE", "WONCS", "WOINS", "WOCLTREQ", "WOCAID2ND", "WOINSBANK")      # the codes the rulebook names (rules.md 9/11, 11/2/2026)
MEDICAID_FAMILY = {"MCAD", "SUN01", "FLO99", "SIM01", "WEL04", "UHCMA", "HUM07"}      # as aging_refresh.py
NO_CS_ROUTE = {"FLO02", "RET01", "VACCN", "TRI00", "TRI05", "AAR01"}                # cs_rules.py CS_NO_ROUTE + CS_OFF: claim status cannot be asked
DX_REMARKS = {"MA63", "M76", "M64"}                                                # 'diagnosis cannot be primary' (billing_button.txt step 4 / 5(d))
RECORDS_CODES = {"226", "252", "163", "251"}
AUTH_CODES = {"197", "288"}
APPEAL_CODES = {"29", "50", "39", "167", "96", "272", "216", "119", "198", "286"}
RESEND_AFTER = {"primary": 91, "secondary": 61}      # a silent claim of a payer with no claim-status route (rules.md 10/15/2026 aging bands)
WAIT_DAYS = 30                                        # never two rebills of one visit inside 30 days (OA-18); an action waits 30 days
# the ageing rules that come from a DENIAL with nothing sent since (their 'carcs' are the visit's live denial); every other row lists old codes too
DENIAL_AGING_RULES = ("denied CO-29", "hospice CO-B9", "wrong-payer denial", "CO-18 duplicate", "CO-151", "bundled", "correctable denial",
                      "credentialing", "non-covered", "denied, nothing sent since", "CCM denied on a hospice")
COUNTING = ("RESEND", "SECONDARY", "REROUTE", "FIX_DX", "HOSPICE_GV", "REDATE", "WRITE_OFF", "WOINSBANK")   # what counts as acting on a visit

# rule id -> (step, turn, what it means, where the rule is written). The step is what the actor does; the turn whose move it is.
RULES = {
 "WO-OLD-1102":         ("WRITE_OFF", "claude", "aging WRITE OFF past 12 months from the DOS - written off by the code of the rule that decided it", "rules.md 11/2/2026 OLD CLAIMS OVER A YEAR"),
 "WO-CCM-HOSPICE-1015": ("WRITE_OFF", "claude", "CCM denied on a hospice patient (GV / CO-B9) - WONCS, no appeal, no rebill", "rules.md 10/4 and 10/15/2026"),
 "WO-CCM-MEDICAID-0911":("WRITE_OFF", "claude", "CCM billed to straight Medicaid is never paid - WONCS", "rules.md 9/11/2026; aging 10/13 rule"),
 "WO-CROSSOVER-0911":   ("WRITE_OFF", "claude", "a Medicaid-family plan answered the cost-share $0 as secondary - WOCAID2ND (contractual, never the patient)", "rules.md lines 6 and 9/11/2026, 10/4/2026"),
 "WO-PAID-NOT-POSTED-1102": ("WOINSBANK", "claude", "the payer says paid, never posted - WOINSBANK once the check matches a Treasury deposit; no match = his list", "rules.md 11/2/2026; William 11/26/2026 decision 2"),
 "FIX-DX-0914":         ("FIX_DX", "claude", "the payer refuses the primary diagnosis on an adjudicated claim - the dx cascade (dx_primary_fix) and a frequency-7 resend with the payer's claim number; no number = William's turn", "rules.md 9/14/2026; billing_button.txt step 5(d)"),
 "FIX-HOSPICE-0920":    ("HOSPICE_GV", "claude", "hospice CO-B9 on an E/M inside 12 months - modifier GV and ONE frequency-1 rebill to Medicare (working_denials_act hospice)", "rules.md 9/20/2026"),
 "FIX-REDATE-1004":     ("REDATE", "claude", "CO-151 on a CCM claim - re-date it to the last day of its month as a new visit, void the old lines (sent as an original)", "rules.md 10/4/2026 and 11/19/2026"),
 "COB-WRONG-PAYER":     ("CASCADE", "run", "wrong payer / coverage - the RULE C cascade decides the live plan, then ONE re-route through the actor (never the patient balance)", "rules.md line 6; 10/14/2026 RULE C"),
 "BILL-SECONDARY-1015": ("SECONDARY", "claude", "the primary paid - the cost-share belongs to the live secondary: move_to_ins --no-rebill, then ONE frequency-1 rebill to the secondary (only when the claim detail shows it does not hold the claim already - rules.md 9/21/2026)", "rules.md 10/15/2026 aging; billing_button.txt STANDING FLAGS"),
 "RESEND-NOT-ON-FILE-1110": ("RESEND", "claude", "claim status: the payer has no record of the claim - ONE frequency-1 resend", "rules.md 11/10/2026; cascade.txt STEP 2"),
 "RESEND-NEVER-SENT":   ("RESEND", "claude", "no bill date on the charges - the claim never went out: send it", "aging 10/15/2026"),
 "RESEND-SILENT-NOROUTE-1015": ("RESEND", "claude", "silent past the aging limit at a payer with no claim-status route - the free checks (ERA cache, AdvancedMD eligibility), then ONE frequency-1 resend", "rules.md 10/15/2026 aging bands; William 11/26/2026 decision 3"),
 "STATUS-BY-NEED-1110": ("WAIT", "payer", "silent - the Sunday claim-status step asks it by need (cs_rules.py, caps unchanged)", "rules.md 11/10/2026"),
 "WAIT-PENDING-1110":   ("WAIT", "payer", "the payer says pending - wait", "rules.md 11/10/2026"),
 "WAIT-SILENT":         ("WAIT", "payer", "silent, not yet at the aging limit for a resend", "rules.md 10/15/2026"),
 "HOLD-CROSSOVER-1127": ("WAIT", "claude", "a secondary balance the unpaid list hid (aging_refresh's Mass Write-off source) that the secondary already holds - crossed over or billed on/after the primary's payment - at a payer with no electronic claim status (TRICARE For Life, AARP): MONEY FIRST - matched against the remits, ERA files and deposits, then the payer's portal; never a resend or a second claim until the payer says it does not have it, and no card per visit", "rules.md 9/21/2026; William 11/27/2026: '1 money first'"),
 "STATUS-CROSSOVER-1127": ("WAIT", "payer", "the same held crossover at a payer that answers claim status electronically: the Sunday claim status asks the SECONDARY - 'paid' goes to the paid-not-posted path, 'not found' to ONE resend (the payer does not have it), a denial to its rule", "rules.md 9/21/2026; William 11/27/2026: '1 money first'"),
 "WAIT-CROSSOVER-0921": ("WAIT", "payer", "the secondary already holds the claim (crossed over / billed after the primary paid) - its answer is awaited 61 days from that bill; never a second claim", "rules.md 9/21/2026; 10/15/2026 aging"),
 "WAIT-COSTSHARE-12M":  ("WAIT", "wait", "primary paid, no secondary on the chart, inside 12 months - written off WOCLTREQ by the 11/2 rule at 12 months (rules.md 9/11: cost-share inside the year is not a write-off)", "rules.md 9/11 and 11/2/2026"),
 "WAIT-ACTED-30D":      ("WAIT", "wait", "the queue (or another helper) acted on this visit in the last 30 days - the claim's answer is awaited", "William 11/26/2026; OA-18 duplicate trap"),
 "FOLLOWUP-APPEAL-1126":("FOLLOW_UP", "claude", "an appeal William sent 30 days ago - free checks, then claim status (his card again when nothing came)", "William 11/26/2026 decision 3"),
 "OWNER-APPEAL":        ("OWNER", "william", "an appeal fits - the run drafts the letter (Drive 'appeals' + a Gmail draft to William); he signs and sends", "William 11/26/2026 decisions 1 and 3"),
 "OWNER-RECORDS":       ("OWNER", "william", "records / attachments requested - William sends them", "boards/working_denials.py 226; William 11/26/2026"),
 "OWNER-AUTH":          ("OWNER", "william", "an authorization or referral is needed - face sheet / VA authorization", "boards/working_denials.py 197 / 288"),
 "OWNER-CORRECT":       ("OWNER", "william", "a correction no rule makes by itself - William says what to change (CO-16: dig deeper before any rebill, William 9/12)", "boards/working_denials.py"),
 "OWNER-REVIEW":        ("OWNER", "william", "a REVIEW code - William's judgment", "boards/working_denials.py REVIEW"),
 "OWNER-CRED":          ("OWNER", "william", "credentialing / enrollment denial - fix the enrollment (Credentialing Board) or William's word", "boards/working_denials.py CRED"),
 "OWNER-POS-1110":      ("OWNER", "william", "place of service (Part A stay) - William says for that claim whether it goes again at 31", "rules.md 11/10/2026 part 7"),
 "OWNER-PAST-12M-1120": ("OWNER", "william", "a primary claim past 12 months from the DOS - listed for William, not sent and not written off", "rules.md 11/20/2026"),
 "OWNER-HOSPICE-OLD":   ("OWNER", "william", "hospice CO-B9 past 12 months - the 9/20 rule says never write it off, the 12-month rule says never send it: William decides", "rules.md 9/7 and 9/20/2026"),
 "OWNER-NO-ICN":        ("OWNER", "william", "a correction to a claim the payer adjudicated needs its claim number (ICN) - none on file, never a guess", "rules.md line 8; billing_button.txt step 5(d)"),
 "OWNER-REDATE-1004":   ("OWNER", "william", "a CO-151 re-date did not finish (a new visit was made, then a later step did not) - William checks the chart: never two CCM claims in one month", "rules.md 10/4/2026 and 11/19/2026"),
 "OWNER-HANDOFF-1110":  ("OWNER", "william", "claim status handed off (no usable answer) - ask the payer by portal or phone", "rules.md 11/10/2026 HAND-OFF LIST"),
 "OWNER-TWO-SECONDARIES": ("OWNER", "william", "two live secondaries on the chart - William says which is billed", "rules.md 10/15/2026 aging"),
 "OWNER-CROSSOVER-SILENT-0921": ("OWNER", "william", "the secondary has held the claim 61 days or more since it crossed over, with no answer - ask it by portal or phone (the Sunday claim status asks the claim's own carrier, the primary that paid, never the secondary); never a second claim", "rules.md 9/21/2026; 10/15/2026 aging"),
 "OWNER-NO-RULE":       ("OWNER", "william", "no standing rule covers it - William's turn", "William 11/26/2026 decision 1"),
 "LIST-PAID-NO-MATCH":  ("LIST", "william", "paid but never posted, no Treasury deposit matches the check yet - stays on his list", "William 11/26/2026 decision 2"),
 "HOLD-FLO99-0922":     ("HOLD", "hold", "FCC (FLO99) pays by paper check - every FLO99 write-off and re-route waits for the reconciliation", "rules.md 9/22/2026"),
 "HOLD-ENROLLMENT-1127": ("HOLD", "hold", "waiting for the rendering clinician's enrollment with this payer (registers/enrollment_holds.json): resent under her once the enrollment is effective - never written off, re-rendered or carded meanwhile", "William 11/27/2026: enroll Pam with Humana with a backdated start, then resend the secondary claims under her"),
 "HOLD-TF-WATCH-1006":  ("HOLD", "hold", "on the timely-filing watch - the watch rule settles it, never re-sent on our own", "billing_button.txt TIMELY-FILING WATCH"),
 "HOLD-BOARD":          ("HOLD", "hold", "the chart waits on William's turn on the Insurance Refresh Board", "BOARD ACCESS RULE"),
 "HOLD-AET12-0921":     ("HOLD", "hold", "AET12 hold - do not rebill", "rules.md 9/21/2026"),
 "HOLD-DEATH":          ("HOLD", "hold", "date of death - the date-of-death rule of the runs decides (void), never the queue", "rules.md 10/4 and 11/25/2026"),
 "HOLD-OPEN-CARD":      ("HOLD", "hold", "the queue's card for this visit is already on William's turn", "William 11/26/2026: one card per visit"),
}
WRITE_OFF_RULES = {r for r, v in RULES.items() if v[0] in ("WRITE_OFF", "WOINSBANK")}


# ---------------------------------------------------------------- small helpers
def _date(s):
    s = str(s or "").strip()
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m: return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m: return datetime.date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
    m = re.match(r"(\d{4})(\d{2})(\d{2})", s)
    if m: return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None
def _money(x):
    try: return round(float(x or 0), 2)
    except (TypeError, ValueError): return 0.0
def _digits(x): return re.sub(r"\D", "", str(x or ""))
def _load(path, default=None):
    try:
        with open(path) as fh: return json.load(fh)
    except (OSError, ValueError): return default
def norm_check(c):
    """A check / EFT number for matching: letters and digits only, upper case, leading zeros dropped."""
    s = re.sub(r"[^0-9A-Za-z]", "", str(c or "")).upper().lstrip("0")
    return s
def last_day_of_month(d):
    nxt = (d.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
    return nxt - datetime.timedelta(days=1)
def code_for(rule):
    """The write-off code a standing aging rule names (generalized from aging_writeoff_1102.py, 11/2/2026) - None when the rule names none.
    Only the codes the rulebook names can come back."""
    r = str(rule or "").lower()
    if "wocaid2nd" in r: return "WOCAID2ND"
    if "wolate" in r or "co-29" in r: return "WOLATE"
    if "woncs" in r: return "WONCS"
    if "wocltreq" in r: return "WOCLTREQ"
    if "woinsbank" in r: return "WOINSBANK"
    if "woins" in r: return "WOINS"
    return None
def _newest(paths):
    """The newest readable JSON snapshot among paths, by its 'asof' (then the file time)."""
    best = None
    for p in paths:
        if not p or not os.path.exists(p): continue
        j = _load(p)
        if not isinstance(j, dict): continue
        key = (str(j.get("asof") or ""), os.path.getmtime(p))
        if best is None or key > best[0]: best = (key, p, j)
    return (best[1], best[2]) if best else (None, None)


# ---------------------------------------------------------------- registers the actor writes (also read by denials_refresh.py)
def act_lines(dirs):
    """Every LIVE line of the actor's registers (work_queue_act_<stamp>.jsonl) in the given folders, each line once."""
    out, seen = [], set()
    for d in dirs:
        for p in sorted(glob.glob(os.path.join(d, "work_queue_act_*.jsonl"))):
            if p.endswith("_dry.jsonl"): continue
            try: lines = open(p).read().splitlines()
            except OSError: continue
            for l in lines:
                try: e = json.loads(l)
                except ValueError: continue
                if not isinstance(e, dict) or not e.get("live"): continue
                k = (e.get("at"), str(e.get("visit")), e.get("action"), e.get("stamp"), e.get("rule"), bool(e.get("ok")), bool(e.get("wrote")))      # the same line in two copies of one register once; the re-date's two lines of one second both
                if k in seen: continue
                seen.add(k); out.append(e)
    return out
def last_actions(lines):
    """visit -> {'acted': last date it was acted on (COUNTING actions that succeeded, or any line that WROTE in AdvancedMD - the re-date's new
    visit), 'card': {rule: date}, 'tries': n, 'death': day the deceased guard held it (a HOLD-DEATH line), 'new_visit': a re-date's new visit}."""
    out = {}
    for e in lines:
        v = str(e.get("visit") or ""); d = _date(e.get("at"))
        if not v or not d: continue
        s = out.setdefault(v, {"acted": None, "card": {}, "tries": 0})
        if e.get("action") == "CARD":      # a card counts once it went into a board file (ok) - a card only in the outbox is proposed again
            if e.get("ok"): s["card"][e.get("rule")] = max(d, s["card"].get(e.get("rule")) or d)
        elif e.get("action") == "HOLD-DEATH":      # the deceased guard did not clear the visit: held for good - the date-of-death rule decides (void)
            s["death"] = max(d, s.get("death") or d)
        elif e.get("action") in COUNTING and e.get("ok"):
            s["tries"] += 1; s["acted"] = max(d, s["acted"] or d)
        if e.get("wrote"):                 # a partial write counts as acted at once (the independent review of 11/26/2026: a re-date whose charge step
            s["acted"] = max(d, s["acted"] or d)      # faulted was 'not acted on', and every start made another new visit)
        if e.get("new_visit"): s["new_visit"] = str(e.get("new_visit"))
    return out
def merge_registers(src, dst):
    """Overlapping runs (the independent review of 11/26/2026, finding 6): right before a live pass, after `git pull --ff-only`, the repository's
    act registers and rebill log are merged INTO this workspace's registers folder - every line of practices/ehpa/registers/work_queue_act_*.jsonl
    (not the _dry files) and rebill_log.jsonl that the workspace copy lacks is appended; nothing is removed or rewritten. So a run that started
    before another run's end-of-run mirror still sees that run's actions and rebills, and the mirror's overwrite of rebill_log.jsonl keeps them.
    -> (files touched, new act lines, new rebill lines)."""
    if not (src and dst and os.path.isdir(src)) or os.path.realpath(src) == os.path.realpath(dst): return 0, 0, 0
    os.makedirs(dst, exist_ok=True)
    files = n_act = n_rb = 0
    names = sorted(os.path.basename(p) for p in glob.glob(os.path.join(src, "work_queue_act_*.jsonl")) if not p.endswith("_dry.jsonl")) + ["rebill_log.jsonl"]
    for name in names:
        sp, dp = os.path.join(src, name), os.path.join(dst, name)
        try: lines = [l for l in open(sp).read().splitlines() if l.strip()]
        except OSError: continue
        try: old = open(dp).read()
        except OSError: old = ""
        have = set(old.splitlines())
        new = [l for l in lines if l not in have]
        if not new: continue
        with open(dp, "a") as fh: fh.write(("\n" if old and not old.endswith("\n") else "") + "\n".join(new) + "\n")
        files += 1
        if name == "rebill_log.jsonl": n_rb += len(new)
        else: n_act += len(new)
    return files, n_act, n_rb
def rebill_dates(paths):
    """visit -> the last day a rebill went out (registers/rebill_log.jsonl, written by amd.rebill_charge for every helper)."""
    out = {}
    for p in paths:
        try: lines = open(p).read().splitlines()
        except OSError: continue
        for l in lines:
            try: e = json.loads(l)
            except ValueError: continue
            v = _digits(e.get("visit")); d = _date(e.get("at"))
            if v and d and (v not in out or d > out[v]): out[v] = d
    return out
def worked_visits(lines):
    """visit -> {'pid', 'at' (first day the queue worked it - a resend, re-route, fix or card), 'actions'} - the claims whose payments count
    as recovered (write-offs close a balance; they recover nothing)."""
    out = {}
    for e in sorted(lines, key=lambda x: str(x.get("at"))):
        if e.get("action") in ("WRITE_OFF", "WOINSBANK", "HOLD-DEATH") or not e.get("ok"): continue      # a card counts once it went into a board file; a death hold sent nothing
        v = str(e.get("visit") or ""); d = _date(e.get("at"))
        if not v or not d: continue
        w = out.setdefault(v, {"pid": str(e.get("pid") or ""), "at": d.isoformat(), "actions": []})
        w["actions"].append(e.get("action"))
        if not w["pid"] and e.get("pid"): w["pid"] = str(e.get("pid"))
    return out
def paid_since(payments, at):
    """Insurance payments dated after the action day: payments = [(date, amount)]; at = the action day (date or ISO text)."""
    a = _date(at)
    return round(sum(_money(amt) for d, amt in payments if a and _date(d) and _date(d) > a), 2)
def week_of(today):
    mon = today - datetime.timedelta(days=today.weekday()); return mon, mon + datetime.timedelta(days=6)
def recovered_block(worked, payments_by_visit, lines, today, baseline=None):
    """The 'recovered' block of working_denials_latest.json and the button report (William 11/26/2026, B4).
    worked = worked_visits(); payments_by_visit = visit -> [(date, amount)] insurance payments read live; lines = act_lines()."""
    mon, sun = week_of(today); lmon, lsun = mon - datetime.timedelta(days=7), mon - datetime.timedelta(days=1)
    def window(a, b):
        amt, n = 0.0, 0
        for v, w in worked.items():
            got = sum(_money(x) for d, x in payments_by_visit.get(v, []) if _date(d) and a <= _date(d) <= b and _date(d) > _date(w["at"]))
            if got > 0: amt += got; n += 1
        return round(amt, 2), n
    rec, n = window(mon, sun); lrec, ln = window(lmon, lsun)
    resent = [e for e in lines if e.get("ok") and e.get("action") in ("RESEND", "SECONDARY", "REROUTE", "FIX_DX", "HOSPICE_GV", "REDATE") and _date(e.get("at")) and mon <= _date(e.get("at")) <= sun]
    wo = collections.defaultdict(float)
    for e in lines:
        if e.get("ok") and e.get("action") in ("WRITE_OFF", "WOINSBANK") and _date(e.get("at")) and mon <= _date(e.get("at")) <= sun:
            wo[e.get("code") or "?"] += _money(e.get("dollars"))
    total = {v: paid_since(payments_by_visit.get(v, []), w["at"]) for v, w in worked.items()}
    block = {"week": "%s..%s" % (mon.isoformat(), sun.isoformat()), "recovered": rec, "claims": n,
             "resent": round(sum(_money(e.get("dollars")) for e in resent), 2), "resent_claims": len({str(e.get("visit")) for e in resent}),
             "written_off": {k: round(v, 2) for k, v in sorted(wo.items())}, "written_off_total": round(sum(wo.values()), 2),
             "last_week": {"week": "%s..%s" % (lmon.isoformat(), lsun.isoformat()), "recovered": lrec, "claims": ln},
             "since_start": {"recovered": round(sum(total.values()), 2), "claims": sum(1 for x in total.values() if x > 0), "worked": len(worked)}}
    if baseline: block["baseline"] = baseline
    wtxt = ", ".join("%s $%.2f" % (k, v) for k, v in block["written_off"].items()) or "none"
    block["line"] = ("Recovered this week (%s - %s): $%.2f on %d claims (insurance payments posted Mon-Sun on claims the queue worked, after the action); "
                     "re-sent $%.2f; written off $%.2f by code (%s)" % (mon.strftime("%m/%d"), sun.strftime("%m/%d"), rec, n, block["resent"], block["written_off_total"], wtxt))
    if baseline:
        block["line"] += "; baseline before the queue: %s rebills on %s visits, $%.2f paid after them on %s visits" % (
            baseline.get("rebills"), baseline.get("visits"), _money(baseline.get("paid_after")), baseline.get("paid_visits"))
    return block


# ---------------------------------------------------------------- Treasury (decision 2: WOINSBANK only on a matched deposit)
def treasury_checks(paths):
    """Check / EFT numbers that match a deposit on the Treasury ledger -> {normalized check number: deposit date}. ONLY rows whose status is
    exactly MATCHED count - in every file, deposits_ledger.csv (date, amount, descriptor, family, era_check, status) and availity_remit_recon_*.csv
    alike. A row with any other status (PROBABLE / POSSIBLE: a guess by amount and lag; NO-ERA, UNKNOWN, NO-DEPOSIT ...) or with no status at
    all never counts: the ledger's era_check is a lag-based guess until a MATCHED row confirms check and amount (the independent review of
    11/26/2026, finding 1 - the filter used to run only on files that also had a deposit_date column, so on the real ledger it never ran)."""
    out = {}
    for p in [x for x in (paths or []) if x]:
        try: rows = list(csv.DictReader(open(p, newline="", encoding="utf-8-sig")))
        except OSError: continue
        for r in rows:
            low = {str(k or "").strip().lower(): (v or "").strip() for k, v in r.items()}
            if low.get("status", "").strip().upper() != "MATCHED": continue      # every file: only a MATCHED row is a deposit matching the check
            for k in ("era_check", "check", "check_number", "checknumber", "check/eft #", "trace"):
                c = norm_check(low.get(k))
                if c: out.setdefault(c, low.get("deposit_date") or low.get("date") or "")
    return out


# ---------------------------------------------------------------- the inputs
def era_lines(paths):
    """The denial lines of dismissed checks (era_clear.py, three shapes since 9/20/2026) -> [{visitid, pid, charges, carrier, dos, when, ...}].
    The chart NUMBER the newer files carry is not copied (some charts are numbered with a member id)."""
    out = []
    for p in paths:
        j = _load(p)
        if j is None: continue
        stamp = os.path.basename(p)
        if isinstance(j, list):                                     # 11/7/2026 era_clear.save_denials
            for v in j:
                if not isinstance(v, dict) or not v.get("visitid"): continue
                ch = [{"cpt": str(c.get("cpt") or "").strip(), "charge": _digits(c.get("chargedetailid")),
                       "carc": [(str(a.get("grp") or "")[:2].upper(), norm(a.get("code"))) for a in (c.get("carc") or []) if a.get("code")],
                       "rarc": [r for r in (c.get("rarc") or []) if r and not str(r).startswith("#")]} for c in (v.get("charges") or [])]
                out.append({"visitid": _digits(v.get("visitid")), "pid": "", "carrier": str(v.get("carrier") or "").strip(), "dos": str(v.get("dos") or "")[:10],
                            "claimstatus": v.get("claimstatus"), "charges": ch, "rarc": [r for r in (v.get("rarc") or []) if r and not str(r).startswith("#")],
                            "when": str(v.get("when") or v.get("deposit") or ""), "icn": "", "file": stamp})
        elif isinstance(j, dict) and isinstance(j.get("lines"), list):  # 10/2026 per-check files
            for l in j["lines"]:
                if not isinstance(l, dict) or not l.get("visitid"): continue
                carc = [(str(c[0])[:2].upper(), norm(c[0])) for c in (l.get("carc") or []) if isinstance(c, (list, tuple)) and c]
                out.append({"visitid": _digits(l.get("visitid")), "pid": _digits(l.get("pid")), "carrier": "", "dos": str(l.get("dos") or "")[:10], "claimstatus": None,
                            "charges": [{"cpt": str(l.get("cpt") or "").strip(), "charge": _digits(l.get("chargeid")), "carc": carc, "rarc": [r for r in (l.get("rarc") or []) if r and not str(r).startswith("#")]}],
                            "rarc": [], "when": str(j.get("stamp") or j.get("checkdate") or ""), "icn": str(l.get("icn") or ""), "file": stamp})
        elif isinstance(j, dict) and isinstance(j.get("by_code"), dict):  # 10/11/2026 by-code file
            for code, rows in j["by_code"].items():
                parts = [x.strip() for x in str(code).split("+") if x.strip()]      # a key may join two reasons: '45+PR1', '197+CO45'
                carc = [(x[:2].upper() if x[:2].upper() in ("CO", "PR", "OA", "PI", "CR") else "", norm(x)) for x in parts]
                for l in rows or []:
                    if not isinstance(l, dict) or not (l.get("vid") or l.get("visitid")): continue
                    out.append({"visitid": _digits(l.get("vid") or l.get("visitid")), "pid": _digits(l.get("pid")), "carrier": "", "dos": str(l.get("dos") or "")[:10],
                                "claimstatus": l.get("claimstatus"), "charges": [{"cpt": str(l.get("cpt") or "").strip(), "charge": _digits(l.get("cdid")), "carc": carc, "rarc": []}],
                                "rarc": [], "when": str(j.get("stamp") or ""), "icn": "", "file": stamp})
    return out
def claimstatus_rows(paths):
    """vid -> {'checks': [...], 'paid_on', 'paid', 'icn'} from the claim-status run files (payments: check, date, amount, payerClaim)."""
    out = {}
    for p in paths:
        j = _load(p)
        rows = j if isinstance(j, list) else (list(j.values()) if isinstance(j, dict) else [])
        for r in rows:
            if not isinstance(r, dict): continue
            v = _digits(r.get("visitid") or r.get("vid"))
            if not v: continue
            s = out.setdefault(v, {"checks": [], "paid_on": "", "paid": 0.0, "icn": "", "carrier": str(r.get("carrier") or "")})
            for pay in r.get("payments") or []:
                c = str(pay.get("check") or "").strip()
                if c and c not in s["checks"]: s["checks"].append(c); s["paid"] = round(s["paid"] + _money(pay.get("amount")), 2)
                s["paid_on"] = max(s["paid_on"], str(pay.get("date") or "")[:10])
                s["icn"] = s["icn"] or str(pay.get("payerClaim") or "")
            for l in (r.get("status") if isinstance(r.get("status"), list) else []) or []:
                if isinstance(l, dict): s["icn"] = s["icn"] or str(l.get("payerClaim") or "")
    return out
def watch_visits(path):
    w = _load(path, {}) or {}
    items = w if isinstance(w, list) else w.get("items", [])
    return {_digits(v.get("visitid") or v.get("visit") or v.get("vid")) for it in items if isinstance(it, dict) for v in it.get("visits", []) if isinstance(v, dict)}
def enrollment_holds(path):
    """registers/enrollment_holds.json: {"items": [{"clinician", "payer", "reason", "until": "YYYY-MM-DD", "card", "visits": [{"visitid"}]}]}
    -> {visit id: until date} for the items still in force (11/27/2026, Pam's Humana enrollment)."""
    w = _load(path, {}) or {}
    out = {}
    for it in (w if isinstance(w, list) else w.get("items", [])):
        if not isinstance(it, dict): continue
        until = _date(it.get("until"))
        for v in it.get("visits", []):
            vid = _digits((v or {}).get("visitid") or (v or {}).get("vid")) if isinstance(v, dict) else _digits(v)
            if vid: out[vid] = until
    return out
def board_charts(dirs):
    """The charts waiting on William's turn for a FACE SHEET, a card or a number in the newest board_turn_<stamp>.json (facesheets_needed.py): their
    insurance is in question, so the board holds every visit of them. A 'decision' card holds only its own visit (the queue's own cards are
    decisions, one per visit - the actor tracks them by visit in its register)."""
    files = sorted({p for d in dirs for p in glob.glob(os.path.join(d, "board_turn_*.json"))}, key=lambda p: os.path.basename(p))
    if not files: return set(), None
    j = _load(files[-1], {}) or {}
    return {_digits(c) for r in j.get("rows", []) if isinstance(r, dict) and r.get("kind") != "decision" for c in (r.get("charts") or []) if _digits(c)}, os.path.basename(files[-1])


# ---------------------------------------------------------------- the decision for one visit
def _row(ev, rule, today, due=None, **kw):
    step, turn = RULES[rule][0], RULES[rule][1]
    r = {"visitid": ev["visitid"], "pid": ev.get("pid") or "", "charge": ev.get("charge") or "", "payer": ev.get("payer") or "", "dos": ev.get("dos") or "",
         "cpts": " ".join(sorted(ev.get("cpts") or [])), "codes": sorted(ev.get("codes_g") or []), "rarc": sorted(ev.get("rarc") or []),
         "amount": _money(ev.get("amount")), "step": step, "rule": rule, "turn": turn, "due": (due or today).isoformat(), "tries": ev.get("tries", 0),
         "icn": ev.get("icn") or "", "sent": ev.get("sent") or "", "source": sorted(ev.get("source") or []),
         "basis": min(ev.get("basis") or [today]).isoformat()}      # the day of the oldest evidence read: a payment after it = a payment since the plan
    r.update({k: v for k, v in kw.items() if v not in (None, "", [])})
    return r

def decide(ev, ctx):
    """One visit's evidence -> its queue row (or None when nothing is to be done). ev: visitid, pid, payer, dos, cpts, mods, amount, codes
    (CARC set), codes_g ('CO16' style), rarc, aging (the aging row), cs (ledger row), cs_pay (claimstatus payments), secondary, sent."""
    today = ctx["today"]; vid = ev["visitid"]; a = ev.get("aging") or {}; cs = ev.get("cs") or {}
    dos = _date(ev.get("dos")); age = (today - dos).days if dos else None
    payer = ev.get("payer") or ""; secs = [s for s in str(ev.get("secondary") or a.get("secondary") or "").split() if s]
    rule_txt = str(a.get("rule") or ""); rec = str(a.get("rec") or "")
    is_secondary = bool(str(a.get("paid_by") or "").strip()) and payer not in str(a.get("paid_by") or "").split()
    is_ccm = bool(set(ev.get("cpts") or []) & CCM_CODES)
    # 0. an appeal William sent: the 30-day follow-up
    sent = ctx["appeals"].get(vid)
    if sent and _date(sent):
        due = _date(sent) + datetime.timedelta(days=WAIT_DAYS)
        return _row(ev, "FOLLOWUP-APPEAL-1126", today, due=max(due, today), appeal_sent=sent)
    # 1. holds
    if payer == "FLO99" or "FLO99" in secs: return _row(ev, "HOLD-FLO99-0922", today)
    if vid in ctx["watch"]: return _row(ev, "HOLD-TF-WATCH-1006", today)
    hold_until = (ctx.get("enroll_hold") or {}).get(vid, False)
    if hold_until is not False and (hold_until is None or today <= hold_until):
        return _row(ev, "HOLD-ENROLLMENT-1127", today, due=hold_until or today + datetime.timedelta(days=30))
    if ev.get("pid") and ev["pid"] in ctx["board"]: return _row(ev, "HOLD-BOARD", today)
    if rule_txt.startswith("DOS after the Medicare date of death") or "13" in (ev.get("codes") or set()): return _row(ev, "HOLD-DEATH", today)
    held = (ctx["acted"].get(vid) or {}).get("death")      # the actor's deceased guard did not clear this visit (a HOLD-DEATH register line): held for good
    if held: return _row(ev, "HOLD-DEATH", today, held_since=held.isoformat())
    if payer == "AET12" or "AET12" in secs: return _row(ev, "HOLD-AET12-0921", today)
    row = _decide_step(ev, ctx, age, payer, secs, rule_txt, rec, is_secondary, is_ccm, cs)
    if row is None: return None
    # 2. guards on every row: past 12 months, acted on in the last 30 days, a card already on his turn
    # (a secondary is timely from the primary's remit - rules.md 9/7/2026 - so billing the secondary, and a secondary balance, are never held here)
    if row["step"] in ("FIX_DX", "HOSPICE_GV", "REDATE", "RESEND", "CASCADE") and not is_secondary and age is not None and age > 365:
        row = _row(ev, "OWNER-PAST-12M-1120", today, was=row["rule"])
    last = ctx["acted"].get(vid) or {}
    acted = max([d for d in (last.get("acted"), ctx["rebilled"].get(vid)) if d] or [None], key=lambda d: d or datetime.date.min)
    if acted and (today - acted).days < WAIT_DAYS and row["turn"] in ("claude", "run") and row["step"] != "FOLLOW_UP":
        return _row(ev, "WAIT-ACTED-30D", today, due=acted + datetime.timedelta(days=WAIT_DAYS), was=row["rule"], last_action=acted.isoformat())
    if acted and row["rule"] == "OWNER-CROSSOVER-SILENT-0921" and (today - acted).days < RESEND_AFTER["secondary"]:      # re-sent since the snapshot: its answer is awaited first
        return _row(ev, "WAIT-CROSSOVER-0921", today, due=acted + datetime.timedelta(days=RESEND_AFTER["secondary"]), payer=row["payer"], secondary=row.get("secondary"),
                    why=row.get("why"), was=row["rule"], last_action=acted.isoformat())
    if row["turn"] == "william" and row["rule"] in (last.get("card") or {}):
        return _row(ev, "HOLD-OPEN-CARD", today, was=row["rule"], card_made=last["card"][row["rule"]].isoformat())
    return row

def _silent_secondary(ev, today, sec, sent, paid):
    """'Primary paid - the cost-share belongs to the live secondary', but the claim was billed ON/AFTER the primary's payment: the crossover
    signature of rules.md 9/21/2026 (billed date = the primary's posting date, claim run N/A) or the secondary AdvancedMD sent itself - the
    secondary already HOLDS the claim. Never a second claim (the independent review of 11/26/2026, finding 3): its answer is awaited 61 days
    from that bill (the aging band of a secondary), then its claim status goes to William - ONE card: ask the payer by portal or phone. (Not a
    STATUS-BY-NEED row: the Sunday claim-status step asks the claim's own carrier - cs_rules.due reads the ageing row's payer, here the primary
    that already paid, 'payment posted for this payer' - so it never asks the secondary, and such a row would wait for ever.)"""
    why = "the secondary %s already holds the claim: billed %s, on/after the primary's payment %s - claim status, never a second claim (rules.md 9/21/2026)" % (sec, sent.isoformat(), paid.isoformat())
    days = (today - sent).days; limit = RESEND_AFTER["secondary"]
    if days >= limit:
        return _row(ev, "OWNER-CROSSOVER-SILENT-0921", today, payer=sec, secondary=sec, why=why, days_silent=days, kind="secondary %s silent %d days since it got the claim" % (sec, days))
    return _row(ev, "WAIT-CROSSOVER-0921", today, due=sent + datetime.timedelta(days=limit), payer=sec, secondary=sec, why=why, days_silent=days)

def _decide_step(ev, ctx, age, payer, secs, rule_txt, rec, is_secondary, is_ccm, cs):
    today = ctx["today"]; codes = set(ev.get("codes") or set()); rarc = set(ev.get("rarc") or set()); a = ev.get("aging") or {}
    ans = str(cs.get("answer") or ""); final = bool(cs.get("final"))
    # paid but never posted (a FINAL 'paid' claim-status answer) - WOINSBANK after a Treasury match (decision 2)
    if ans == "paid" and final:
        pay = ev.get("cs_pay") or {}
        return _row(ev, "WO-PAID-NOT-POSTED-1102", today, code="WOINSBANK", checks=pay.get("checks") or [], paid=pay.get("paid") or None, paid_on=pay.get("paid_on") or "")
    # the 11/2 rule: an aging WRITE OFF row past 12 months, by the code of the rule that decided it
    code = code_for(rule_txt)
    if rec == "WRITE OFF" and code and code != "WOINSBANK" and age is not None and age > 365:
        return _row(ev, "WO-OLD-1102", today, code=code, aging_rule=rule_txt)      # the actor ties the code to this rule text (code_for)
    # standing write-offs at any age (the aging engine's own rules)
    if rec == "WRITE OFF" and rule_txt.startswith("CCM to straight Medicaid"): return _row(ev, "WO-CCM-MEDICAID-0911", today, code="WONCS")
    if rec == "WRITE OFF" and rule_txt.startswith("CCM denied on a hospice patient"): return _row(ev, "WO-CCM-HOSPICE-1015", today, code="WONCS")
    if rec == "WRITE OFF" and rule_txt.startswith("primary paid, no secondary") and code == "WOCAID2ND": return _row(ev, "WO-CROSSOVER-0911", today, code="WOCAID2ND")
    # a Medicaid-family plan's $0 answer as SECONDARY with only informational / cost-share reasons (OA-23): contractual
    for l in ev.get("era") or []:
        cods = {c for ch in l["charges"] for _, c in ch["carc"]}
        if l.get("claimstatus") == 2 and (l.get("carrier") or payer) in MEDICAID_FAMILY and cods and cods <= {"23", "45", "253", "1", "2", "3", "94"}:
            return _row(ev, "WO-CROSSOVER-0911", today, code="WOCAID2ND", era_file=l.get("file"))
    # denials: the most actionable code decides (the board's own order)
    best = None
    for c in codes:
        dispo, _ = triage_line(c, next(iter(sorted(ev.get("cpts") or [""]))), " ".join(ev.get("mods") or []))
        if is_ccm and c == "B9": dispo = "WRITEOFF"
        if dispo in ("PATIENT", "DUPLICATE", "CONTRACTUAL", "INFO"): continue
        rank = DISPO_ORDER.index(dispo) if dispo in DISPO_ORDER else len(DISPO_ORDER)
        if c == "58" and dispo == "REVIEW": rank = -1
        if best is None or rank < best[0]: best = (rank, dispo, c)
    if best:
        _, dispo, c = best
        if dispo == "WRITEOFF": return _row(ev, "WO-CCM-HOSPICE-1015", today, code="WONCS")
        if dispo == "COB": return _row(ev, "COB-WRONG-PAYER", today)
        if dispo == "TIMELY":
            return _row(ev, "OWNER-APPEAL", today, kind="appeal: timely filing", ask="proof of timely submission" + (" - a secondary's CO-29 is appealed with the primary's remit date" if is_secondary else ""))
        if dispo == "CRED": return _row(ev, "OWNER-CRED", today, kind="credentialing")
        if dispo == "FIX":
            if c == "B9": return _row(ev, "FIX-HOSPICE-0920" if age is not None and age <= 365 else "OWNER-HOSPICE-OLD", today)
            if c == "151": return _row(ev, "FIX-REDATE-1004", today, redate_to=last_day_of_month(_date(ev["dos"])).isoformat()) if is_ccm and _date(ev.get("dos")) else _row(ev, "OWNER-REVIEW", today, kind="review: CO-151 on a non-CCM line")
            if c in ("16", "11", "146") and rarc & DX_REMARKS: return _row(ev, "FIX-DX-0914", today)
            if c in RECORDS_CODES: return _row(ev, "OWNER-RECORDS", today, kind="records")
            if c in AUTH_CODES: return _row(ev, "OWNER-AUTH", today, kind="authorization")
            return _row(ev, "OWNER-CORRECT", today, kind="correction: CO-%s%s" % (c, (" remark " + ",".join(sorted(rarc))) if rarc else " (remark not on file)"))
        if dispo == "REVIEW":
            if c == "58": return _row(ev, "OWNER-POS-1110", today, kind="place of service")
            if c in APPEAL_CODES: return _row(ev, "OWNER-APPEAL", today, kind="appeal: CO-%s" % c)
            return _row(ev, "OWNER-REVIEW", today, kind="review: CO-%s" % c)
        return _row(ev, "OWNER-NO-RULE", today, kind="no rule for CO-%s" % c)
    # claim-status answers without a denial on file
    if ans == "not found": return _row(ev, "RESEND-NOT-ON-FILE-1110", today)
    if ans == "not eligible": return _row(ev, "COB-WRONG-PAYER", today, why="claim status: not eligible on the date of service")
    if ans in ("finalized at $0", "denied") and final:
        st = str(cs.get("status") or "").split("/")[-1]
        if st in ("88", "97"): return _row(ev, "COB-WRONG-PAYER", today, why="claim status %s" % cs.get("status"))
        if rec not in ("CORRECT & RESEND", "WRITE OFF"):          # with an ageing row its rule reads the posted answer (a $0 to the deductible = cost-share)
            return _row(ev, "OWNER-NO-RULE", today, kind="claim status %s with no denial reason on file" % ans, status=cs.get("status"))
    if cs.get("stopped"): return _row(ev, "OWNER-HANDOFF-1110", today, kind="claim status handed off (%s)" % (cs.get("answer") or "no usable answer"))
    # the aging rules (no denial, no answer)
    if rec == "CORRECT & RESEND":
        if rule_txt.startswith("primary paid - cost-share belongs to the live secondary") or rule_txt.startswith("secondary never sent"):
            if len(secs) > 1: return _row(ev, "OWNER-TWO-SECONDARIES", today, secondary=" ".join(secs), kind="two live secondaries")
            sent, paid = _date(a.get("sent")), _date(a.get("paid_on")) or _date(a.get("denied"))
            if secs and sent and paid and sent >= paid:      # billed on/after the primary's payment: the secondary already holds the claim
                return _silent_secondary(ev, today, secs[0], sent, paid)
            return _row(ev, "BILL-SECONDARY-1015", today, secondary=" ".join(secs), paid_on=paid.isoformat() if paid else "")
        if rule_txt.startswith("no bill date on the charges"): return _row(ev, "RESEND-NEVER-SENT", today)
        if rule_txt.startswith("wrong-payer denial"): return _row(ev, "COB-WRONG-PAYER", today)
        if rule_txt.startswith(("sent 61-90", "sent 91-120", "sent > 120", "secondary unanswered")):
            if rule_txt.startswith("secondary unanswered") and is_secondary:       # 11/27/2026: the secondary holds the claim (crossover)
                sent_, paid_ = _date(a.get("sent")), _date(a.get("paid_on"))
                if sent_ and paid_ and sent_ >= paid_ and ans not in ("not found", "paid", "denied", "finalized at $0", "not eligible"):
                    why = "billed %s, on/after the primary's payment %s - the secondary holds the claim" % (sent_.isoformat(), paid_.isoformat())
                    if payer in NO_CS_ROUTE:
                        return _row(ev, "HOLD-CROSSOVER-1127", today, due=today + datetime.timedelta(days=7), payer=payer, secondary=payer, why=why)
                    return _row(ev, "STATUS-CROSSOVER-1127", today, due=today + datetime.timedelta(days=(6 - today.weekday()) % 7), payer=payer, secondary=payer, why=why)
            if ans == "pending":
                return _row(ev, "WAIT-PENDING-1110", today, due=(_date(cs.get("asked")) or today) + datetime.timedelta(days=14))
            sent = _date(a.get("sent")); days = (today - sent).days if sent else None
            limit = RESEND_AFTER["secondary" if is_secondary else "primary"]
            if payer in NO_CS_ROUTE:
                if days is not None and days >= limit: return _row(ev, "RESEND-SILENT-NOROUTE-1015", today, days_silent=days)
                return _row(ev, "WAIT-SILENT", today, due=(sent + datetime.timedelta(days=limit)) if sent else today)
            return _row(ev, "STATUS-BY-NEED-1110", today, due=today + datetime.timedelta(days=(6 - today.weekday()) % 7))
        return _row(ev, "OWNER-NO-RULE", today, kind="aging: %s" % rule_txt[:60])
    if rec == "WRITE OFF":
        if rule_txt.startswith("primary paid, no secondary"):
            return _row(ev, "WAIT-COSTSHARE-12M", today, due=(_date(ev["dos"]) + datetime.timedelta(days=366)) if _date(ev.get("dos")) else today, code=code)
        return _row(ev, "OWNER-NO-RULE", today, kind="aging write-off without a named code: %s" % rule_txt[:60])
    return None


# ---------------------------------------------------------------- the plan
def build(inputs, today):
    """inputs: wd (working denials snapshot), era (era_lines), aging (snapshot), ledger (rows), cs (claimstatus_rows), acted (last_actions),
    rebilled (rebill_dates), watch, board (charts), appeals -> {schema, rows, counts, ...}."""
    ev = {}
    def get(vid):
        return ev.setdefault(vid, {"visitid": vid, "pid": "", "payer": "", "dos": "", "cpts": set(), "mods": set(), "amount": 0.0, "codes": set(), "codes_g": set(),
                                   "rarc": set(), "source": set(), "era": [], "aging": None, "cs": None, "charge": ""})
    wd = inputs.get("wd") or {}
    wd_status = {}
    for v in wd.get("visits") or []:
        vid = _digits(v.get("visitid")); wd_status[vid] = v.get("status")
        if v.get("status") != "OPEN" or not vid: continue
        e = get(vid); e["source"].add("denials"); e.setdefault("basis", []).append(_date(wd.get("asof")) or today)
        e["pid"] = e["pid"] or _digits(v.get("pid")); e["payer"] = e["payer"] or str(v.get("carrier") or "").strip(); e["dos"] = e["dos"] or str(v.get("dos") or "")[:10]
        if v.get("cpt"): e["cpts"].add(str(v["cpt"]).strip())
        e["amount"] = max(e["amount"], _money(v.get("open_balance") or v.get("amt")))
        for c in v.get("codes") or [v.get("carc")]:
            g = str(c).split("/")[0] if "/" in str(c) else ""; k = norm(str(c).split("/")[-1])
            if k: e["codes"].add(k); e["codes_g"].add((g if g not in ("??", "") else "") + k)
        e["rarc"] |= {r for r in (v.get("rarc") or []) if r}
    wd_asof = str(wd.get("asof") or "")[:10]
    acted = inputs.get("acted") or {}
    ag = inputs.get("aging") or {}
    unpaid = {_digits(r.get("visitid")) for r in ag.get("rows") or []}               # every open insurance balance (the ageing file, all three kinds)
    ag_asof = _date(ag.get("asof") or ag.get("today"))
    for l in inputs.get("era") or []:
        vid = l["visitid"]
        last = (acted.get(vid) or {}).get("acted")
        when = _date(l.get("when"))
        if last and when and last >= when: continue                                   # the queue acted after this line: worked
        if vid not in unpaid and wd_status.get(vid) != "OPEN" and not (when and ag_asof and when > ag_asof): continue   # settled: no open balance on the last ageing read
        if wd_status.get(vid) in ("RESOLVED", "WRITTEN-OFF", "RESUBMITTED") and when and wd_asof and wd_asof >= when.isoformat(): continue
        cods = {c for ch in l["charges"] for _, c in ch["carc"]}
        if not cods: continue
        e = get(vid); e["source"].add("era"); e["era"].append(l); e.setdefault("basis", []).append(when or today)
        e["pid"] = e["pid"] or l.get("pid") or ""; e["payer"] = e["payer"] or l.get("carrier") or ""; e["dos"] = e["dos"] or l.get("dos") or ""
        e["icn"] = e.get("icn") or l.get("icn") or ""
        for ch in l["charges"]:
            if ch.get("cpt"): e["cpts"].add(ch["cpt"])
            if ch.get("charge") and not e["charge"]: e["charge"] = ch["charge"]
            for g, c in ch["carc"]:
                if c not in ("23", "45", "253", "94", "1", "2", "3") or l.get("claimstatus") != 2:
                    e["codes"].add(c); e["codes_g"].add(g + c)
            e["rarc"] |= set(ch.get("rarc") or [])
        e["rarc"] |= set(l.get("rarc") or [])
    aging_any = {_digits(r.get("visitid")): r for r in ag.get("rows") or [] if _digits(r.get("visitid"))}
    for vid, r in aging_any.items():
        if r.get("rec") not in ("CORRECT & RESEND", "WRITE OFF"): continue
        e = get(vid); e["source"].add("aging"); e["aging"] = r; e.setdefault("basis", []).append(ag_asof or today)
        # the ageing row's denial codes are evidence only when ITS rule is a denial rule (a settled or silent row lists old denials too)
        if str(r.get("rule") or "").startswith(DENIAL_AGING_RULES):
            for c in str(r.get("carcs") or "").split():
                e["codes"].add(norm(c)); e["codes_g"].add(norm(c))
    for vid, e in ev.items():                       # the ageing row (any kind) fills what the other sources lack: chart, payer, balance, last send
        r = aging_any.get(vid)
        if not r: continue
        e["pid"] = e["pid"] or _digits(r.get("pid")); e["payer"] = str(r.get("payer") or "").strip() or e["payer"]; e["dos"] = e["dos"] or str(r.get("dos") or "")[:10]
        e["cpts"] |= set(str(r.get("cpts") or "").split()); e["mods"] |= set(str(r.get("mods") or "").split())
        e["amount"] = max(e["amount"], _money(r.get("bal"))); e["secondary"] = str(r.get("secondary") or ""); e["sent"] = str(r.get("sent") or "")
    aging_sent = {v: str(r.get("sent") or "") for v, r in aging_any.items()}
    aging_pid = {v: _digits(r.get("pid")) for v, r in aging_any.items()}
    for key, L in (inputs.get("ledger") or {}).items():
        vid = _digits(L.get("vid") or str(key).split("|")[0]); ans = L.get("answer")
        if not vid or ans not in ("paid", "finalized at $0", "denied", "not found", "not eligible") and not L.get("stopped"): continue
        if ans in ("paid", "finalized at $0", "denied") and not L.get("final"): continue
        s_now = aging_sent.get(vid, "")
        if s_now and str(L.get("sent") or "") and s_now > str(L.get("sent")): continue      # sent again since that answer: the answer is stale
        if vid not in aging_sent and ans != "paid": continue                             # no longer on the unpaid list
        if L.get("stopped") and not L.get("final") and _date(L.get("dos")) and (today - _date(L.get("dos"))).days > 365: continue   # listed while under a year old (rules.md 11/10/2026)
        e = get(vid); e["source"].add("claim status"); e["cs"] = L; e.setdefault("basis", []).append(_date(L.get("asked")) or today)
        r = aging_any.get(vid) or {}
        e["amount"] = max(e["amount"], _money(r.get("bal"))); e["sent"] = e.get("sent") or str(r.get("sent") or ""); e["cpts"] |= set(str(r.get("cpts") or "").split())
        e["pid"] = e["pid"] or _digits(L.get("pid")) or aging_pid.get(vid, ""); e["payer"] = e["payer"] or str(L.get("payer") or ""); e["dos"] = e["dos"] or str(L.get("dos") or "")[:10]
        e["cs_pay"] = (inputs.get("cs") or {}).get(vid) or {}
        e["icn"] = e.get("icn") or e["cs_pay"].get("icn") or ""
    rows = []
    for vid, e in ev.items():
        e["pid"] = e["pid"] or aging_pid.get(vid, "")
        e["tries"] = ((acted.get(vid) or {}).get("tries")) or 0
        r = decide(e, {"today": today, "watch": inputs.get("watch") or set(), "enroll_hold": inputs.get("enroll_hold") or {}, "board": inputs.get("board") or set(), "acted": acted,
                       "rebilled": inputs.get("rebilled") or {}, "appeals": inputs.get("appeals") or {}})
        if r: rows.append(r)
    rows.sort(key=lambda r: ({"claude": 0, "run": 1, "william": 2}.get(r["turn"], 3), r["due"], -r["amount"]))
    counts = collections.Counter(r["rule"] for r in rows); dollars = collections.defaultdict(float)
    for r in rows: dollars[r["rule"]] += r["amount"]
    by_step = collections.Counter(r["step"] for r in rows)
    return {"schema": "work-queue/1", "version": WORK_QUEUE_VERSION, "planned": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "today": today.isoformat(), "rows": rows, "counts": dict(counts), "dollars": {k: round(v, 2) for k, v in dollars.items()}, "by_step": dict(by_step),
            "by_turn": dict(collections.Counter(r["turn"] for r in rows))}


def gather(repo, regs, ws, today):
    """Read every input from the workspace (preferred when newer) and the repository clone."""
    rr = os.path.join(repo, "practices", "ehpa", "registers") if repo else None
    dirs = [d for d in (regs, rr) if d and os.path.isdir(d)]
    srcs = {}
    wd_path, wd = _newest([os.path.join(ws, "working_denials_latest.json"), os.path.join(repo, "reports", "button", "working_denials_latest.json") if repo else None])
    ag_path, ag = _newest([os.path.join(ws, "aging_latest.json"), os.path.join(repo, "reports", "button", "aging_latest.json") if repo else None])
    srcs["denials"] = {"file": wd_path, "asof": (wd or {}).get("asof")}; srcs["aging"] = {"file": ag_path, "asof": (ag or {}).get("asof")}
    era_files = {}
    for d in dirs:
        for p in glob.glob(os.path.join(d, "era_denials_*.json")):
            if not p.endswith("_dry.json"): era_files.setdefault(os.path.basename(p), p)
    era = era_lines(sorted(era_files.values()))
    led = None
    for d in dirs:
        led = _load(os.path.join(d, "claim_status_ledger.json"))
        if isinstance(led, dict): break
    cs_files = sorted(set(glob.glob(os.path.join(ws, "claimstatus_*.json"))) | {p for d in dirs for p in glob.glob(os.path.join(d, "claimstatus_2*.json"))})
    lines = act_lines(dirs)
    appeals = {}
    for d in reversed(dirs):
        appeals.update({str(k): (v.get("sent") if isinstance(v, dict) else v) for k, v in ((_load(os.path.join(d, "work_queue_appeals.json"), {}) or {}).get("sent", {}) or {}).items()})
    board, bfile = board_charts(dirs)
    watch = set(); enroll_hold = {}
    for d in dirs:
        watch |= watch_visits(os.path.join(d, "tf_writeoff_watch.json"))
        enroll_hold.update(enrollment_holds(os.path.join(d, "enrollment_holds.json")))
    srcs.update({"era_denials": {"files": len(era_files), "lines": len(era)}, "ledger": {"rows": len((led or {}).get("rows") or {})}, "claimstatus_files": len(cs_files),
                 "act_lines": len(lines), "board_turn": bfile, "watch_visits": len(watch), "appeals_sent": len(appeals)})
    inputs = {"wd": wd, "era": era, "aging": ag, "ledger": (led or {}).get("rows") or {}, "cs": claimstatus_rows(cs_files), "acted": last_actions(lines),
              "rebilled": rebill_dates([os.path.join(d, "rebill_log.jsonl") for d in dirs]), "watch": watch, "enroll_hold": enroll_hold, "board": board, "appeals": appeals}
    return inputs, srcs


def main(argv=None):
    ap = argparse.ArgumentParser(description="the work-queue planner (reads only; writes registers/work_queue.json)")
    ap.add_argument("cmd", nargs="?", default="plan", choices=["plan", "sent", "merge"])
    ap.add_argument("visit", nargs="?")
    ap.add_argument("--repo", default="/home/claude/effinger-billing-backend")
    ap.add_argument("--registers", default="registers")
    ap.add_argument("--ws", default=".")
    ap.add_argument("--out", default=None)
    ap.add_argument("--today", default=None)
    ap.add_argument("--date", default=None, help="sent: the day William's 'sent' note was posted (default today)")
    a = ap.parse_args(argv)
    today = _date(a.today) or datetime.date.today()
    if a.cmd == "merge":
        src = os.path.join(a.repo, "practices", "ehpa", "registers") if a.repo else ""
        if not os.path.isdir(src): print("RESULT work_queue merge: no repository registers at %s - nothing merged (no live pass without them)" % (src or "-")); return 1
        files, n_act, n_rb = merge_registers(src, a.registers)
        print("RESULT work_queue merge: %d file(s) - %d act line(s) and %d rebill line(s) of %s added to %s" % (files, n_act, n_rb, src, a.registers))
        return 0
    if a.cmd == "sent":
        vid = _digits(a.visit)
        if not vid: ap.error("sent needs the visit id")
        os.makedirs(a.registers, exist_ok=True); p = os.path.join(a.registers, "work_queue_appeals.json")
        j = _load(p, {}) or {}; j.setdefault("about", "Appeals William marked 'sent' on their board cards (visit ids and dates only) - each starts a 30-day follow-up (work_queue.py, William 11/26/2026)")
        j.setdefault("sent", {})[vid] = {"sent": (_date(a.date) or today).isoformat()}
        json.dump(j, open(p, "w"), indent=1, sort_keys=True)
        print("RESULT work_queue sent: visit %s appeal sent %s - follow-up due %s -> %s" % (vid, j["sent"][vid]["sent"], ((_date(a.date) or today) + datetime.timedelta(days=WAIT_DAYS)).isoformat(), p))
        return 0
    inputs, srcs = gather(a.repo if a.repo and os.path.isdir(a.repo) else None, a.registers, a.ws, today)
    q = build(inputs, today); q["sources"] = srcs
    out = a.out or os.path.join(a.registers, "work_queue.json")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    json.dump(q, open(out, "w"), indent=1)
    turn = q["by_turn"]
    print("RESULT work_queue %s: %d visits - claude %d, run (RULE C) %d, william %d, wait %d, hold %d -> %s" % (
        today.isoformat(), len(q["rows"]), turn.get("claude", 0), turn.get("run", 0), turn.get("william", 0), turn.get("payer", 0) + turn.get("wait", 0), turn.get("hold", 0), out))
    for rule, n in sorted(q["counts"].items(), key=lambda kv: (RULES[kv[0]][1], -kv[1])):
        print("  %-28s %-10s %4d  $%10.2f  %s" % (rule, RULES[rule][0], n, q["dollars"].get(rule, 0), RULES[rule][2][:90]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
