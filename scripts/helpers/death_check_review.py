#!/usr/bin/env python3
# PLAIN ENGLISH (the date-of-death check of the Charge Review step - William in chat, 11/25/2026: "add into the billing codes routines when
#   billing any ccm codes to straight medicare to do a stedi or advanced md check to see can you do a check to verify date of death first so
#   as not to bill any after the date of death to straight medicare ... and check before submitting")
# Decides: nothing by itself - the deceased guard decides (William 9/22/2026: a claim whose date of service is AFTER the day on Medicare's
#   record is never submitted - deceased_guard.py). READ-ONLY. A run starts this helper BEFORE approvecharges AND BEFORE ANY SAVE of a
#   Charge Review visit (WHEN A RUN STARTS IT, below). Until 11/25/2026 no standing
#   helper listed Charge Review and applied the guard: the Billing Button's text said "The deceased guard runs before every approval" (the
#   six-hourly columns text said nothing of it in its step 1) and every run wrote its own code for it - on 9/23/2026 a run bypassed
#   advisory rows on visits the guard had not seen (guard_sweep_1910.py tells it).
# WHEN A RUN STARTS IT (11/25/2026 review fix - the texts first said only "before approvecharges", and the step's two gates save before
#   that): before ANY save in the Charge Review step. The two gates of that step fix a visit with a full-visit save that carries
#   approval="1" and asks no guard: the modifier-25 fix (mod25_addon.py -> recode._save) and the primary-dx fix
#   (dx_primary_fix.save_visit_dx). A visit ENTERED with those attributes arrives approved (docs/captured_calls.md: 'Charge Review stays
#   empty'); whether a visit already waiting in Charge Review leaves it on such a save was never captured - so each such save is treated as
#   an approval. This helper lists only what is still waiting in Charge Review: a visit such a save has taken out of it is never put
#   through the guard here, and the summary line would still read as if every charge had been checked. So: this helper first; then the
#   gates' fixes and approvecharges, for the visits it has answered for; a visit with a BLOCKED or NOT CHECKED charge gets no gate fix
#   on that run.
# WHAT IT DOES: (1) ONE login the way the other helpers log in (amd.login_cached) and ONE list call: getreviewcharges class=chargeentry - the
#   call and the reading of columns_scan.py (every visit element with its id and patientid, every charge element under it with its id).
#   Nothing but those ids is taken from the listing: no kept answer of this call shows a date of service, a code or a carrier on its rows
#   (docs/captured_calls.md holds the call's name only; Charge Review was empty in every scan that was kept), so they are never read there.
#   (2) Each charge is read ONCE by its id (resave.detail - the read the guard makes too) for the visit's insurance order and for the WORDS:
#   the chart, the date of service, the code and the plans' carriers - for the lines, the register and the count of charges that needed a
#   Medicare answer. That same answer is handed to the guard when it reads the charge in (3): the guard decides on the answer that was
#   looked at here, never on a second read that may have failed in between (handed() below says why).
#   (3) EVERY charge goes through the guard: deceased_guard.check_charge(<charge id>, 1) - the guard reads the charge itself (the chart, the
#   visit's date, the procedure's id, the plan at sequence 1) and asks Medicare when the claim goes to straight Medicare or the code is a
#   care-management code and its own answer is stale. THE SECOND QUESTION: until now the runs' own code asked the guard with the claim's
#   own carrier and the code - deceased_guard.check(chart, date of service, carrier, code), insp_1014_1910.py - and this helper must not
#   ask less than they did. So the guard is asked once more, that same way - with the carrier of the plan the claim really goes to first
#   and the code - wherever check_charge did not hand it those: a visit whose insurance order STARTS with another plan than sequence 1
#   (about four in ten of the visit orders in the practice's registers do: "2", "2,1", "3" ...); a care-management code the guard's list
#   holds while its procedure id is not in it; a charge whose answer shows the first plan's carrier only on the insurance-order list's own
#   row (carrier, sequence, ordinal - docs/captured_calls.md), not on a plan element at that sequence, or shows it as bare digits. A
#   block from either answer stands. HOW the guard asks - AdvancedMD's free check first, a paid vendor answer only when the free one
#   cannot answer - is the guard's rule, not this helper's: this helper never asks Medicare anything itself.
#   (4) 'Not blocked' counts as CHECKED only when there was something to check: the guard does not raise on an answer that carries no
#   chart, no date of service or no row of that charge (a Fault, say) - it has nothing to compare and answers 'not blocked'. Such a
#   charge, and one the read of (2) could not read at all, is NOT CHECKED here. A block always stands, with "?" in its line for what could
#   not be read.
# WHAT IT PRINTS (and keeps word for word in the register under "lines"):
#   BLOCKED: pat<chart> visit <id> charge <id> DOS <date> code <code> - date of death before the date of service - do NOT approve; void
#     (William 10/4 and 11/25/2026)                 one line for every charge the guard blocks;
#   NOT CHECKED: pat<chart> visit <id> charge <id> (<why>) - could not be checked - do not approve this charge on this run
#                                                   one line for every charge the guard raised on, every charge with nothing to check
#                                                   in its own detail (4), every visit the listing shows without a charge (a visit
#                                                   still being entered) and every charge it shows without an id;
#   UNVERIFIED: pat<chart> visit <id> charge <id> DOS <date> code <code> - date of death unverified (the look-up failed) - not a block; say
#     it in the report                              one line for every charge whose look-up failed (the guard's own LOG line is the source):
#                                                   a failed check blocks nothing - only a date on Medicare's record does;
#   DEATH CHECK - Charge Review: N charge(s) on V visit(s) listed, K checked; M needed a Medicare answer (CCM or straight Medicare) - <free
#     and bought answers>; B BLOCKED; U could not be checked; X unverified - register <file>
#                                                   the LAST line, always: a run that sees no such line has no answer from this helper.
#     <free and bought answers> = "AdvancedMD's free check answered F of A asked, P went to the vendor" from the guard's own COUNTS
#     (what this start added to them); "free / vendor checks not counted by this guard" with a guard that has no COUNTS; "none asked" with --dry.
#     N - the charges LISTED, the line's first number - is the number a run compares with its own listing of Charge Review (taken before
#     any save): when the two differ the run does not rely on this helper. K is NOT that number: K and the NOT CHECKED lines about a charge
#     (every NOT CHECKED line but 'no charge listed under this visit', which is about a visit) always add up to N, so K is smaller than N
#     whenever a charge is NOT CHECKED - this helper working as designed. (11/25/2026 review fix: the texts first named K, so every answer
#     with a NOT CHECKED charge sent the run to guard calls of its own - and deceased_guard.check_charge raises nothing when it has nothing
#     to compare, it answers 'not blocked'. A NOT CHECKED charge stays unapproved on that run, whatever a guard call of the run's own answers.)
#   NEVER printed or written: the day itself, the guard's own reason (it holds that day), a name, a birth date, a Medicare or member
#   number, an error's words (they can name a patient - an error is shown by its kind). Every value taken from AdvancedMD's answers is kept
#   only in the shape of what it is: an id as its digits, a date of service as a date, a code as a code.
# WHAT IT WRITES: registers/death_check_review_<UTC stamp>.json under the folder it is started in (with --dry: ..._dry.json) - chart ids,
#   visit ids, charge ids, dates of service, codes, the counts and the fixed words above - and nothing else. NOTHING in AdvancedMD: its
#   only calls are the login, the one list call and one read by charge id for each charge (what the guard calls is the guard's; its read
#   of the charge it checks is answered with that one read).
#   The guard's own cache is the guard's too: this helper names no cache file - the guard takes the one the run's environment gives it
#   (DECEASED_CACHE, else its own default), exactly as it does for the code a run writes itself.
# EXIT: 0 = Charge Review was listed, every charge was checked and nothing is blocked. 3 = at least one charge is BLOCKED or could not be
#   checked - the lines say which. 2 = Charge Review could not be listed (the login or the call failed, the answer is no list - not
#   AdvancedMD's answer at all - or carries a Fault), an option it does not know, a helper it could not load, or an error of its own: it
#   has then checked NOTHING and nothing may be approved on its word - one plain line says so, never a traceback. What a run does then is
#   in step 1 of nightly/live/columns.txt and billing_button.txt: it applies the guard to every charge itself, as before, saves no gate
#   fix on a visit before the guard has answered for its charges, and approves nothing it has not checked.
# Usage (from the workspace): python3 death_check_review.py [--dry]
#   --dry = the guard's cache only (allow_lookup=False): Medicare is not asked and nothing is bought - a look, NOT a clearance to approve.
#   --live = the default, said out loud. An option it does not know is refused (exit 2), not passed over.
# Never: approves, saves, voids, bills, bypasses or releases anything; changes the guard, its cache or its wording; asks Medicare itself;
#   lists by batch id (no request of this call with a batch id is captured - docs/captured_calls.md).
import os, re, sys, json, time, datetime
import xml.etree.ElementTree as ET
DEATH_CHECK_REVIEW_VERSION = "2026-11-25.5"      # this helper's own version: change it with EVERY revision - it is written into the register (.2 = the 11/25/2026 review fix: the header's WHEN A RUN STARTS IT and the number a run compares; .3 = the same day: a charge that came out clear is put to the guard's cache once more at the end of the start; .4 = the second verification: the cache's state in counts, the code's own shape)
BLOCK_WORDS = "date of death before the date of service - do NOT approve; void (William 10/4 and 11/25/2026)"
UNCHECKED_WORDS = "could not be checked - do not approve this charge on this run"
UNVERIFIED_WORDS = "date of death unverified (the look-up failed) - not a block; say it in the report"
NOTHING = "approve NOTHING on this helper's word"
CACHE_UNREADABLE = "CACHE UNREADABLE: the deceased guard's cache file is there but cannot be read - the guard knows NOTHING the practice holds and can keep nothing it learns beyond this start; merge the copy from Drive (step 0c) and start this helper again before any approval - TOP OF THE REPORT"
CACHE_EMPTY = "CACHE EMPTY: the deceased guard's cache holds no chart at all - a date of death the practice already holds is unknown to it until Medicare answers again; merge the copy from Drive (step 0c) and start this helper again before any approval - TOP OF THE REPORT"
CACHE_LOST = "CACHE: %d chart(s) carry a date of death whose day cannot be read here (the scrubbed copy from the repository) - a charge of such a chart is asked about whatever its payer and is NOT CHECKED until somebody names the day; merge the copy from Drive (step 0c) to get the days back - TOP OF THE REPORT"
CACHE_MISSING = "CACHE MISSING: the deceased guard's cache file is not there - the guard starts with NOTHING: a date of death the practice already holds is unknown to it until Medicare answers again, and a charge that needs no Medicare answer is not asked about at all - TOP OF THE REPORT"
USAGE = "usage: python3 death_check_review.py [--dry]"
OUT = "death_check_review_%s%s.json"
COUNT_KEYS = ("free asked", "free answered", "paid asked")      # the guard's COUNTS (deceased_guard.py); an older guard has none
PAUSE = 0.2                                                      # seconds between two charges
class Unlistable(Exception):
    """Charge Review could not be listed. Its words are this helper's own - never AdvancedMD's (they can name a patient)."""

# ---- every value in the shape of what it is: an id, a date, a code - and an error by its kind ------------------------------------------------
def num(x): return re.sub(r"\D", "", str(x or ""))
def kind_of(e): return re.sub(r"[^A-Za-z]", "", type(e).__name__)[:40] or "error"      # an error by its kind - never by its words
def day(x):
    """A date of service as YYYY-MM-DD, from AdvancedMD's MM/DD/YYYY, from YYYY-MM-DD or from YYYYMMDD (the forms the guard reads); "" for
    anything else - never a text passed on."""
    s = str(x or "").strip(); m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})(?!\d)", s)
    if m: return "%s-%02d-%02d" % (m.group(3), int(m.group(1)), int(m.group(2)))
    if re.match(r"\d{8}$", s): return "%s-%s-%s" % (s[:4], s[4:6], s[6:])
    m = re.match(r"\d{4}-\d{2}-\d{2}(?!\d)", s); return m.group(0) if m else ""
def code_of(x):
    """A procedure code or a procedure id as it is - the five characters of a code (99349, G0556, 1123F, M0004) or pcode and digits; "" for
    anything else. (11/25/2026, the second verification: any one word of 3 to 12 letters and digits passed - a name or a member number
    standing in the procedure attributes of an answer would have been printed and written to the register.)"""
    s = str(x or "").strip(); return s if re.match(r"(?:[0-9]{4}[0-9A-Za-z]|[A-Za-z][0-9]{4}|pcode[0-9]{1,12})$", s) else ""
def car(x):
    """A carrier in the form the guard's own list holds it: car<digits> for an id that comes as bare digits (this answer gives the chart's
    id without its prefix too - docs/captured_calls.md), an id with its prefix or a carrier's code (FLO02) as it is; "" for anything that
    is not one word of letters and digits - never a text passed on."""
    s = str(x or "").strip()
    if re.match(r"\d{1,9}$", s): return "car" + s
    return s if re.match(r"[A-Za-z0-9]{2,12}$", s) else ""

# ---- the list of Charge Review -----------------------------------------------------------------------------------------------------------------
def fault(root):
    """Why a parsed answer of the list call is NOT a list, in this helper's own words; "" for a good answer: an ELEMENT named Fault anywhere
    (never the letters in the answer's text - resave.py's rule), success="0" on Results, an Error element that is not empty (every good
    answer carries an empty one), or an answer that is not AdvancedMD's at all - no PPMDResults and no Results element in it (a gateway's
    page can be well-formed too; claimocity_match.py knows a good answer by the same two names). The answer's own words are never passed on."""
    tags = [(e.tag if isinstance(e.tag, str) else "", e) for e in root.iter()]
    if any(t == "Fault" or t.endswith("}Fault") for t, e in tags): return "AdvancedMD answered a Fault"
    if any(t == "Results" and e.get("success") == "0" for t, e in tags): return "AdvancedMD answered success 0"
    if any(t == "Error" and (len(e) or (e.text or "").strip()) for t, e in tags): return "AdvancedMD answered an error"
    if not any(t in ("PPMDResults", "Results") for t, e in tags): return "the answer is not a list"
    return ""
def listed(amd):
    """The charges waiting in Charge Review -> ([(visit id, chart id, charge id)] in the listing's order, visits, charges). The proven list
    call and its reading (columns_scan.py): getreviewcharges class=chargeentry; every visit element with its id and patientid, every charge
    element with its id. A charge row is taken wherever it stands - under its visit (the nearest visit element above it) or outside every
    visit. A charge listed twice counts once. charge id None = a visit the listing shows without a charge; "" = a charge without an id."""
    try: x = amd.post(amd.msg("getreviewcharges", "chargeentry", {"nocookie": "1"}), timeout=120)
    except Exception as e: raise Unlistable("the list call failed: " + kind_of(e))
    try: root = ET.fromstring(x)
    except Exception: raise Unlistable("the answer is not a list")
    why = fault(root)
    if why: raise Unlistable(why)
    at = {e: i for i, e in enumerate(root.iter())}; up = {c: p for p in root.iter() for c in p}
    def visit_of(e):
        while e in up:
            e = up[e]
            if e.tag == "visit": return e
        return None
    rows = []; seen = set(); holds = set(); charges = 0; visits = list(root.iter("visit"))
    for c in root.iter("charge"):
        v = visit_of(c); cid = num(c.get("id"))
        if v is not None: holds.add(v)
        if cid and cid in seen: continue
        seen.add(cid); charges += 1
        rows.append((at[c], num(v.get("id")) if v is not None else "", num(v.get("patientid")) if v is not None else "", cid))
    rows += [(at[v], num(v.get("id")), num(v.get("patientid")), None) for v in visits if v not in holds]
    return [r[1:] for r in sorted(rows, key=lambda r: r[0])], len(visits), charges

# ---- one charge's words, and the guard's counts -------------------------------------------------------------------------------------------------
def firsts(v):
    """What the visit's own insurance order STARTS with, as the charge's detail shows it -> [(plan sequence or None, the carrier that row
    names or "")]: the first row of the insurance-order list AdvancedMD built (visit/insuranceorderlist/insuranceorder by ordinal -
    resave.order_list's reading; the rows carry carrier, sequence and ordinal, the ordinal starts at 0 and the rows can come out of claim
    order: docs/captured_calls.md, 'The list, not the attribute'; a claim is built from that list) and the first number of the visit's
    insorder attribute (what the rebill rule reads; it names no carrier). Usually one plan; [] when the detail shows none."""
    if v is None: return []
    def ordinal(o):
        try: return int(o.get("ordinal") or 0)
        except ValueError: return 0
    rows = sorted(v.findall("insuranceorderlist/insuranceorder"), key=ordinal); out = []
    for s, c in ([((rows[0].get("sequence") or "").strip(), car(rows[0].get("carrier")))] if rows else []) + [((v.get("insorder") or "").split(",")[0].strip(), "")]:
        q = int(s) if re.match(r"\d{1,3}$", s) else None
        if (q is not None or c) and (q, c) not in out: out.append((q, c))
    return out
def words(text, cid):
    """What the charge's own detail shows (text = the answer of getchargedetaildataicd10 by charge id - resave.detail, the read the guard
    makes; the names are the ones deceased_guard.check_charge and resave.py read): the chart, the visit, its date and what its insurance
    order starts with (firsts), whether the charge's own row is there, its procedure id and the code the procedure list gives for it, the
    carrier of each plan by its sequence, as the answer writes it. Raises when the answer cannot be read."""
    d = ET.fromstring(text); v = d.find(".//visit"); p = d.find(".//patient")
    ch = [x for x in d.iter("charge") if x.get("id") == "charge" + cid]
    proc = (ch[0].get("proccode") or "") if ch else ""
    cpt = {x.get("id"): x.get("code") for x in d.findall(".//proccodelist/proccode") if x.get("id")}.get(proc, "")
    return {"chart": num(p.get("id")) if p is not None else "", "visit": num(v.get("id")) if v is not None else "", "dos": day(v.get("date")) if v is not None else "",
            "firsts": firsts(v), "found": bool(ch), "code": code_of(cpt) or code_of(proc), "cpt": code_of(cpt), "proc": proc, "plans": {str(ip.get("sequence")): ip.get("carrier") or "" for ip in d.iter("insplan")}}
def handed(resave, cid, text, ask):
    """ask() - the guard's questions about ONE charge - while resave.detail(<that charge>) answers with `text`, the answer this helper has
    just read and looked at. 11/25/2026: the guard reads the charge it checks itself, and it does not raise on an answer that carries no
    chart (a Fault, say) - it passes it; read a second time, a charge whose first answer was good could so be passed unseen while this
    helper called it clear (tools/selftest/test_death_check_review.py 10n). Handed the same answer, the guard decides on what was looked at
    here, and AdvancedMD is asked ONCE per charge. A read of any other charge goes to AdvancedMD as always. text None (this helper had no
    good answer to hand over): nothing is put in the way - the guard reads for itself, as it always did. resave.detail is put back whatever
    happens."""
    if text is None: return ask()
    real = resave.detail
    resave.detail = lambda c: text if num(c) == cid else real(c)
    try: return ask()
    finally: resave.detail = real
def counts(G):
    """The guard's COUNTS as three numbers; None for a guard that does not count (an older guard, or a COUNTS of another shape)."""
    c = getattr(G, "COUNTS", None)
    if not isinstance(c, dict): return None
    try: return {k: int(c.get(k) or 0) for k in COUNT_KEYS}
    except (TypeError, ValueError): return None
def write(path, reg):
    """The register, written whole: a temporary file beside it, then put in its place in one step (none is left behind)."""
    os.makedirs(os.path.dirname(path), exist_ok=True); tmp = path + ".tmp"
    try:
        with open(tmp, "w") as fh: json.dump(reg, fh, indent=1)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.remove(tmp)

def main(argv=None):
    """The check's run -> its exit code. An error of this helper's own ends it with ONE plain line - the error's kind and the line of this
    file, never the error's words - and exit 2: it is never a traceback in a run's log, and it never reads as an answer."""
    try: return review(sys.argv[1:] if argv is None else argv)
    except Exception as e:
        here = main.__code__.co_filename; n = 0; tb = e.__traceback__
        while tb is not None:
            if tb.tb_frame.f_code.co_filename == here: n = tb.tb_lineno
            tb = tb.tb_next
        print("DEATH CHECK - this helper ended on an error of its own (%s at line %d of death_check_review.py) - whatever it printed above does not count: %s" % (kind_of(e), n, NOTHING)); return 2
def review(argv):
    a = [str(x) for x in argv]
    for x in a:
        if x not in ("--dry", "--live"):
            print("DEATH CHECK - it does not know '%s' - nothing was checked: %s (%s)" % (re.sub(r"[^A-Za-z0-9_=-]", "?", x)[:40], NOTHING, USAGE)); return 2
    if "--dry" in a and "--live" in a:
        print("DEATH CHECK - --dry and --live were both given - nothing was checked: %s (%s)" % (NOTHING, USAGE)); return 2
    dry = "--dry" in a
    try: import amd, resave, deceased_guard as G
    except Exception as e:
        print("DEATH CHECK - amd.py, resave.py or deceased_guard.py could not be loaded (%s) - nothing was checked: %s" % (kind_of(e), NOTHING)); return 2
    try: amd.login_cached()
    except Exception as e:
        print("DEATH CHECK - Charge Review could not be listed (the login failed: %s) - nothing was checked: %s" % (kind_of(e), NOTHING)); return 2
    try: listing, visits, charges = listed(amd)
    except Unlistable as e:
        print("DEATH CHECK - Charge Review could not be listed (%s) - nothing was checked: %s" % (e, NOTHING)); return 2
    MED = getattr(G, "MEDICARE", None) or (); CCM = getattr(G, "CCM", None) or ()      # the guard's own lists - never a second copy here
    log = getattr(G, "LOG", None); log = log if isinstance(log, list) else None
    before = counts(G); lines = []; rows = []; checked = needed = nb = nu = nx = 0
    def say(s): lines.append(s); print(s, flush=True)
    # 11/25/2026 (the integration; the review's finding on the cache): a guard that finds NO cache file starts with nothing - a day the practice
    # already holds is unknown to it until Medicare answers again, and a charge that needs no Medicare answer is not asked about at all. This
    # helper names no cache and cannot know what a missing file would have held; it says that the file is missing, once, for the top of the
    # report. (deceased_guard.py finds the workspace's own registers/deceased_cache.json since that day; a guard that names no file gets no line.)
    cpath = getattr(G, "CACHE", None); cache_missing = isinstance(cpath, str) and bool(cpath) and not os.path.isfile(cpath)
    if cache_missing: say(CACHE_MISSING)
    # 11/25/2026 (the second verification): after the bootstrap the file is always THERE - the repository's register is copied in when the
    # state bundle brought none, and that copy holds no day anyone can read. So the helper also says, in counts only (the guard's own
    # cache_state; a guard from before has none and gets no line): a file that cannot be read, a file with no chart at all, and how many
    # charts carry a day that cannot be read here. A charge of such a chart is asked about whatever its payer; when nobody answers the
    # guard raises DayLost and the charge is NOT CHECKED - never clear.
    state = None
    try:
        st = getattr(G, "cache_state", None); st = st() if callable(st) else None
        if isinstance(st, dict): state = {k: (bool(st.get(k)) if k in ("file", "readable") else int(st.get(k) or 0)) for k in ("file", "readable", "charts", "days", "lost")}
    except Exception: state = None
    if state and state["file"] and not cache_missing:
        if not state["readable"]: say(CACHE_UNREADABLE)
        elif not state["charts"]: say(CACHE_EMPTY)
        elif state["lost"]: say(CACHE_LOST % state["lost"])
    def unchecked(pid, vid, cid, why):
        rows.append({"chart": ("pat" + pid) if pid else "", "visit": vid, "charge": cid, "result": "could not be checked", "why": why, "words": UNCHECKED_WORDS})
        say("NOT CHECKED: pat%s visit %s charge %s (%s) - " % (pid or "?", vid or "?", cid or "?", why) + UNCHECKED_WORDS)
    for vid, pid, cid in listing:
        if not cid:
            nu += 1; unchecked(pid, vid, "", "no charge listed under this visit" if cid is None else "a charge without an id in the listing"); continue
        try: text = resave.detail(cid); w = words(text, cid); bad = ""
        except Exception as e: text = None; w = {}; bad = "the charge could not be read: " + kind_of(e)
        if not (w and w["chart"] and w["dos"] and w["found"]): text = None      # only an answer with something to check in it is handed to the guard (handed, above); with any other the guard reads for itself - it may still find a block
        chart = w.get("chart") or pid; visit = vid or w.get("visit") or ""
        # 11/25/2026 - THE SECOND QUESTION. check_charge(<charge id>, 1) hands the guard the carrier of the plan element at sequence 1, as the
        # answer writes it, and the procedure's ID. Until now the runs' own code asked deceased_guard.check(chart, date of service, the
        # CLAIM's carrier, the CODE) (insp_1014_1910.py), and this helper must not ask less than they did: (a) about four in ten of the visit
        # orders in the practice's registers start with plan 2, 3 or 4 - asked about sequence 1 alone, a straight-Medicare claim whose
        # Medicare plan stands at sequence 2 is not asked about at all; (b) the guard's list knows the care-management codes by their code and
        # four of them by their procedure id - a code entered under another id is no care-management code to check_charge; (c) the carrier of
        # the plan a claim goes to first is on the insurance-order list's own first row (the registry: carrier, sequence, ordinal), while
        # nothing on record shows the plan elements check_charge looks for in this answer, or the form their carrier takes - without them
        # check_charge hands the guard no carrier at all, and a straight-Medicare claim is asked about nothing. So the guard is asked once
        # more, the runs' way, wherever the carrier of the visit's first plan as THIS helper reads it (that row's own carrier, and the plan
        # element at that row's sequence; bare digits written car<digits>, as the guard's list holds them) is not the carrier check_charge
        # handed over, or the code is a care-management code its procedure id is not. A block from either answer stands.
        # (tools/selftest/test_death_check_review.py 10k, 10l and 10q show the three with the real guard.)
        again = []
        if w and w["chart"] and w["dos"]:
            seq1 = w["plans"].get("1") or None; first = []
            for q, c in w["firsts"]:
                for x in (c, car(w["plans"].get(str(q))) if q is not None else ""):
                    if x and x not in first: first.append(x)
            again = [x for x in first if x != seq1 and not (x in MED and seq1 in MED)] or ([seq1] if w["cpt"] in CCM and w["proc"] not in CCM else [])      # (the guard's list holds straight Medicare under its id and its code: one payer, one question)
        n0 = len(log) if log is not None else 0
        def ask():
            r = G.check_charge(cid, 1, allow_lookup=False) if dry else G.check_charge(cid, 1)      # the guard reads the charge itself and decides; its reason is never kept (it holds the day)
            for carrier in again:
                if r[0]: break
                r = G.check(w["chart"], w["dos"], carrier, w["cpt"] or w["proc"] or None, allow_lookup=not dry)
            return bool(r[0])
        try: blocked = handed(resave, cid, text, ask)
        except Exception as e:
            nu += 1; unchecked(chart, visit, cid, "the guard raised " + kind_of(e)); continue
        unverified = (not blocked) and log is not None and any("UNVERIFIED" in str(x) for x in log[n0:])
        # 11/25/2026: 'not blocked' counts as CHECKED only when there was something to check. The guard does not raise on an answer that carries
        # no chart, no date of service or no row of that charge (a Fault, say): it has nothing to compare and answers 'not blocked' - found
        # with the real guard in tools/selftest/test_death_check_review.py (10j). A block always stands, whatever the read above showed.
        if not blocked:
            bad = bad or ("" if w["chart"] and w["dos"] else "no chart or no date of service in the charge's own detail") or ("" if w["found"] else "the charge is not in its own detail")
            if bad:
                nu += 1; unchecked(chart, visit, cid, bad); continue
        checked += 1
        need = bool(any(c in MED for c in [w["plans"].get("1")] + again) or w["proc"] in CCM or w["cpt"] in CCM) if w else None      # the guard's own rule, on what the guard was asked with: straight Medicare, or a care-management code
        needed += 1 if need else 0
        row = {"chart": ("pat" + chart) if chart else "", "visit": visit, "charge": cid, "dos": w.get("dos") or "", "code": w.get("code") or "", "needed": need, "result": "BLOCKED" if blocked else "clear"}
        who = (chart or "?", visit or "?", cid, w.get("dos") or "?", w.get("code") or "?")
        if blocked:
            nb += 1; row["words"] = BLOCK_WORDS; say("BLOCKED: pat%s visit %s charge %s DOS %s code %s - " % who + BLOCK_WORDS)
        elif unverified:
            nx += 1; row["unverified"] = True; row["words"] = UNVERIFIED_WORDS      # its line is said when the listing is through (below): a later answer of this start can overtake it
        rows.append(row); time.sleep(PAUSE)
    # 11/25/2026 (the integration; found by the review's fixer and left open): ONE START, ONE CHART, TWO CHARGES - the answer must not depend on
    # which of them the listing shows first. An ordinary visit on a plan that is not Medicare needs no Medicare answer: the guard looks into its
    # cache only, and came out clear when the care-management visit of the SAME chart, which brought the day from Medicare's record, stood behind
    # it in the listing. So a charge that came out clear, and after which ANOTHER charge of the same chart was looked at, is put to the guard's
    # cache once more when the listing is through - nothing is asked, nothing is bought - and a day the start learned after it blocks it too
    # ("late" in its register row). A chart with one charge in the start is asked about once, as before.
    last_of = {num(r.get("chart")): i for i, r in enumerate(rows) if num(r.get("chart"))}      # where each chart stands LAST among this start's rows (also a row that could not be checked: the guard may have asked before it gave up)
    for i, row in enumerate(rows):
        if row.get("result") != "clear" or not num(row.get("chart")) or not row.get("dos"): continue
        if last_of.get(num(row["chart"])) == i: continue      # nothing of this chart was looked at after this charge: no later answer can have changed its own
        try: late = bool(G.check(num(row["chart"]), row["dos"], None, None, allow_lookup=False)[0])
        except Exception: continue      # the cache could not be read a second time: the answer the charge already has stands
        if late:
            nb += 1; nx -= 1 if row.pop("unverified", None) else 0
            row.update(result="BLOCKED", late=True, words=BLOCK_WORDS)
            say("BLOCKED: pat%s visit %s charge %s DOS %s code %s - " % (num(row["chart"]), row.get("visit") or "?", row.get("charge") or "?", row["dos"], row.get("code") or "?") + BLOCK_WORDS)
    # 11/25/2026 (the second verification): an UNVERIFIED line used to be said during the walk and stayed - in the output and in the register - also when a later
    # answer of the same start had overtaken it: beside a BLOCKED line for the same charge, or although a later charge of the same chart had brought Medicare's
    # answer. Now the lines are said when the listing is through: none for a charge that ended BLOCKED (above), and none for a charge AFTER which another charge of
    # the same chart needed Medicare's answer and got it (that answer is the chart's; had it named a day, the look above would have blocked this charge).
    for i, row in enumerate(rows):
        if not row.get("unverified"): continue
        if any(num(r.get("chart")) == num(row.get("chart")) and r.get("needed") and not r.get("unverified") and r.get("result") in ("clear", "BLOCKED") for r in rows[i + 1:]):
            nx -= 1; row.pop("unverified", None); row.pop("words", None); row["answered_later"] = True; continue
        say("UNVERIFIED: pat%s visit %s charge %s DOS %s code %s - " % (num(row.get("chart")) or "?", row.get("visit") or "?", row.get("charge") or "?", row.get("dos") or "?", row.get("code") or "?") + UNVERIFIED_WORDS)
    after = counts(G); added = {k: after[k] - before[k] for k in COUNT_KEYS} if before is not None and after is not None else None
    if dry: how = " - none asked (--dry: the guard's cache only, NOT a clearance to approve)"
    elif added is not None: how = " - AdvancedMD's free check answered %d of %d asked, %d went to the vendor" % (added["free answered"], added["free asked"], added["paid asked"])      # (11/25/2026, the second verification: the count is the guard's CHECKS that went to the vendor, not its paid requests - stedi_usage.py has those and the dollars)
    else: how = " - free / vendor checks not counted by this guard"
    code = 3 if (nb or nu) else 0
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H%M%SZ"); name = OUT % (stamp, "_dry" if dry else "")
    head = "DEATH CHECK - Charge Review: %d charge(s) on %d visit(s) listed, %d checked; %d needed a Medicare answer (CCM or straight Medicare)%s; %d BLOCKED; %d could not be checked; %d unverified - register " % (
        charges, visits, checked, needed, how, nb, nu, nx)
    reg = {"helper": "death_check_review.py", "version": DEATH_CHECK_REVIEW_VERSION, "stamp": stamp, "dry": dry, "exit": code, "listed": {"visits": visits, "charges": charges},
           "checked": checked, "needed": needed, "counts": added, "blocked": nb, "unchecked": nu, "unverified": nx, "cache_missing": cache_missing, "cache": state, "rows": rows, "lines": lines + [head + "registers/" + name]}
    try: write(os.path.join("registers", name), reg); last = head + "registers/" + name
    except Exception as e: last = head + "NOT written (%s)" % kind_of(e)
    say(last); return code
if __name__ == "__main__": sys.exit(main())
