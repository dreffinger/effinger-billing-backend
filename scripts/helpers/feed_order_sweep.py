#!/usr/bin/env python3
# PLAIN ENGLISH (feed visits AdvancedMD can never bill: the daily listing, and the owner-approved save - round 7, 11/10/2026)
# Decides: which never-billed feed visits have an EMPTY insurance-order list. A visit entered while its chart had no plan keeps insorder "1",
#   but AdvancedMD builds no list for it, and a claim is built from the list: such a visit never bills and shows on no work list (84 visits,
#   $18,802 on 11/10/2026). A full-visit save after the plan exists builds the list. This helper finds those visits every day and, only on
#   the owner's word, saves them again - always through resave.set_insorder (the list-aware save of round 7), never with a call of its own.
#   THE LISTING (read only; every run, after the insurance check): every feed visit the import entered in the last --days days (30) and every
#   visit of the owner's approved file - one charge detail per charge the import entered (a visit an earlier sweep saw billed is not read
#   again). A visit with billins 1 and an EMPTY list gets a line at the TOP of the report (printed last, with what this run did about it; a
#   visit this run saved and read back gets none): chart, visit, date of service, age, payer, and what
#   else is wrong with it - the clinician the feed names against the one entered (tools/feed/feed_clinician_audit.py's mapping; an initial
#   nursing-facility visit 99304-99306, its 99497 included, is the physician's whatever the feed names - William 11/10/2026 - and the line
#   still shows the feed's clinician when it differs, so William can confirm who saw the patient), an admission date after the date of
#   service, two admission dates in one stay, a hospital visit with no admission date.
#   --coverage --live (paid, capped: 120 checks and $40 a run, $0.30 a check): for each visit this helper would save that has no proof of
#   coverage on its date of service yet, ONE eligibility check dated to that date per chart, date and plan, through the vendor client's own
#   call (stedi.elig): Medicare with the chart's Medicare number (payer CMS), any other plan with its member id. Active on the date = proof;
#   not active or an error = listed for William, never saved. Each answer goes into registers/feed_order_coverage_<stamp>.json (visit,
#   chart, date of service, payer, yes / no / error with the answer's own words and plan dates). Never a name, a birth date or a member id;
#   a plan date equal to the birth date is a placeholder and is neither used nor written.
#   --fix-clinician --approved <file> --live (William 11/10/2026, Q4): a visit the approved file marks "clinician": "prof15" is moved to that
#   profile with rebill_under_effinger.py's proven profile-change save (updvisitwithnewcharges: AdvancedMD voids the charges and creates new
#   ones, possibly under a new visit id) - only on a never-billed, unpaid visit, never on an initial nursing-facility visit, and only when
#   every other check of the save already passes (the move is itself a full-visit save and can make the visit bill at the next claim run).
#   Read back: profile, every live charge, codes, places of service, the admission date (written back with the import's call if lost),
#   the list; old -> new charge ids and visit id go into registers/feed_order_fixclin_<stamp>.json.
#   --resave --approved <file> --live: saves ONLY visits the owner's approved file names, each after every check passes: entered clinician
#   = the expected one (above); no bill, no payment, patient balance 0; exactly one open plan at the lead sequence (the carrier the approved
#   file names there, AdvancedMD's own dates not after the date of service); proof of coverage ON THE DATE OF SERVICE - a check dated to it
#   (--coverage), or for a visit the file sends on a face sheet / the feed's insurance block, that evidence; the admission date sane; the
#   deceased guard. --resave --standing --live (William's standing word, 11/10/2026, Q5) does the same WITHOUT the file for a never-billed
#   feed visit whose import row shows no open plan at entry, on a chart that now has exactly one open medical plan (never a visit the
#   approved file names: the file decides those). Then the list, the admission date and the clinician are read back; one register row
#   per visit (registers/feed_order_resave_<stamp>.json); the run STOPS at the first unexpected read-back and says so at the top.
#   PILOT (the remedy order, round 7 section 9): until one save of this helper has read back as asked, a live run saves ONE visit - the
#   oldest that passes every check, one whose clinician was never changed - and the clinician moves wait; then the first move is one
#   visit too; the next runs do the rest, oldest date of service first. STOP: an unexpected read-back in any earlier register stops every
#   save and move until a person has looked at that visit and written "cleared": "<who, date>" into that row.
# Never: resets a chart's default order, adds or ends a plan, rebills (chargerebill answers HTTP 500 on these visits), saves a billed or
#   paid visit, touches a visit the approved file keeps for William, takes the free 271 as proof for a date of service (it answers for
#   today) or a plan begin date in AdvancedMD as proof (68 of the 84 carry the add-plan default: one year before the day the plan was
#   added), writes a name, birth date or member id anywhere.
# Usage (from the workspace; nightly/claimocity_feed_step.md says when - without --live nothing is sent to AdvancedMD or the vendor):
#   python3 feed_order_sweep.py [--days 30] [--only vstA,vstB]                                      the listing
#   python3 feed_order_sweep.py --coverage --approved registers/feed_order_approved.json --live     + the dated checks
#   python3 feed_order_sweep.py --fix-clinician --approved registers/feed_order_approved.json --live + the clinician moves
#   python3 feed_order_sweep.py --resave --approved registers/feed_order_approved.json --live       + the owner's visits
#   python3 feed_order_sweep.py --resave --standing --live [--max N]                                + the standing word
#   The flags combine; one run does the listing, then the dated checks, then the moves, then the saves.
import os, re, sys, json, glob, time, datetime
import xml.etree.ElementTree as ET
os.environ.setdefault("DECEASED_CACHE", "/home/claude/unbilled/deceased_cache_local.json")      # the real dates live in the workspace (as claimocity_verify.py)
import amd, resave
REG = "registers"; APPROVED = os.path.join(REG, "feed_order_approved.json")
PHYSICIAN, NP = "prof13", "prof15"
WHO = {PHYSICIAN: "the physician (prof13)", NP: "the nurse practitioner (prof15)"}
LABELS = {"Dr. Effinger (DO)": PHYSICIAN, "Pamela G. (ARNP)": NP, "Pamela G.": NP}      # tools/feed/feed_clinician_audit.py's mapping of the feed's clinician (feed_recon "prov")
INITIAL_NF = {"99304", "99305", "99306"}      # William 11/10/2026: every initial nursing-facility visit, the 99497 of that visit included, is the physician's
CCM = ("99487", "99489", "99490", "99491", "99439", "99437")
PRICE, CAP_CHECKS, CAP_DOLLARS = 0.30, 120, 40.0      # the vendor's public list price for one eligibility check; the run's cap (round 7, 8.5)
# the vendor's payer ids, copied from precheck.py (the nightly pre-claim check) on 11/10/2026; Medicare goes to the vendor's CMS route with the chart's Medicare number
CAR2STEDI = {"UNI20": "87726", "UHCMA": "87726", "AAR01": "87726", "UMR": "87726", "CIPSC": "87726", "HUM01": "61101", "AET07": "60054",
             "CIG09": "62308", "CIG13": "63092", "BCBS": "BCBSF", "SUN01": "68069", "WEL04": "14163", "AMB03": "68069", "SIM01": "SMPLY",
             "CAP07": "95112", "MCAD": "77027", "TRI00": "99727", "TRI05": "99727", "VACCN": "VACCN", "FLO99": None, "PHI01": None}
MEDICARE = {"FLO02", "RET01"}
NOT_MEDICAL = r"DENTAL|VISION|\bLIFE\b|METLIFE|EYEMED|\bVSP\b|PDP|PART D|PRESCRIPTION|PHARMACY|OPTUMRX|CAREMARK|EXPRESS SCRIPTS"      # as claimocity_verify.py (TRICARE FOR LIFE is medical)
ACTIVE = {"1", "2", "3", "4", "5"}      # X12 benefit status 1-5 are all active (precheck.py, 11/6/2026); 6 = inactive
LIMITED = r"FAMILY PLANNING|LIMITED TO|EMERGENCY (?:SERVICES )?ONLY|QMB ONLY|\bSLMB\b"      # Florida Medicaid 'FP | Limited to family planning services' is not a physician payer (captured_calls)
MA_TYPES = {"HN", "HM", "PR", "PS", "IN", "MD"}      # a Medicare Advantage / other primary plan on a Medicare answer (precheck.py's list; Medicaid never leads over Medicare)
DECISIONS = {"send", "send_if_active_on_dos", "order_by_dated_check", "william"}
STANDING = "standing word, William 11/10/2026"

def d8(x):
    """A date as YYYYMMDD ("11/02/2026", "2026-11-02", "20261102" -> "20261102"); "" when it cannot be read."""
    s = str(x or "").strip(); m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m: return "%s%02d%02d" % (m.group(3), int(m.group(1)), int(m.group(2)))
    s = re.sub(r"\D", "", s)
    return s[:8] if len(s) >= 8 and s[:2] in ("19", "20") else ""
def mdy(x):
    x = d8(x); return "%s/%s/%s" % (x[4:6], x[6:8], x[:4]) if x else ""
def jload(path):
    try: return json.load(open(path))
    except Exception: return None
def regs(prefix):
    return sorted(f for f in glob.glob(os.path.join(REG, prefix + "*.json")) if not f.endswith("_decisions.json"))
def earlier(prefix):
    """[(stamp, register)] of every earlier register of that kind, oldest first."""
    return [(os.path.basename(f)[len(prefix):-5], jload(f) or {}) for f in regs(prefix)]
def num(x): return re.sub(r"\D", "", str(x or ""))
def utcnow(): return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
def age(today8, dos8):
    """Days from the date of service to today (both YYYYMMDD); None when a date cannot be read."""
    try: return (datetime.date(int(today8[:4]), int(today8[4:6]), int(today8[6:8])) - datetime.date(int(dos8[:4]), int(dos8[4:6]), int(dos8[6:8]))).days
    except (ValueError, TypeError): return None
def shape(charges):
    """What a clinician move must keep, per live charge: procedure, modifiers, place of service, units."""
    return sorted((c.get("proccode") or "", c.get("modcodes") or "", c.get("pos") or "", c.get("units") or "") for c in charges)

def verdict(j, dos8, cms, dob8=""):
    """One eligibility answer dated to the date of service -> (yes | no | error, the answer's own words, (plan begin, plan end) as YYYYMMDD).
    yes = active on that date: no error, an active plan status (X12 1-5) and the plan's own dates (when given) around the date; for Medicare
    (cms) Part B shown active on the date and no Medicare Advantage / other primary payer named for it. A date equal to the birth date is a
    placeholder: it is neither used nor written."""
    def keep(x): x = d8(x); return "" if (not x or x == dob8) else x
    def rng(d):
        b = e = ""
        if not isinstance(d, dict): return b, e
        b = next((keep(d.get(k)) for k in ("planBegin", "eligibilityBegin", "policyEffective", "periodStart", "benefitBegin") if keep(d.get(k))), "")
        e = next((keep(d.get(k)) for k in ("planEnd", "eligibilityEnd", "policyExpiration", "periodEnd", "benefitEnd") if keep(d.get(k))), "")
        for k in ("plan", "eligibility", "benefit"):
            a_, sep, z_ = str(d.get(k) or "").partition("-")
            b = b or keep(a_); e = e or (keep(z_) if sep else "")
        return b, e
    def covers(d):
        b, e = rng(d); return not ((b and dos8 < b) or (e and dos8 > e))
    j = j if isinstance(j, dict) else {}
    errs = [x for x in (j.get("errors") or []) if isinstance(x, dict)]
    if errs: return "error", "the answer carries an error: " + "; ".join("%s %s" % (x.get("code") or "", x.get("description") or "") for x in errs[:3])[:300], ("", "")
    begin, end = rng(j.get("planDateInformation"))
    st = [s for s in (j.get("planStatus") or []) if isinstance(s, dict)]
    words = "; ".join(sorted(set(re.sub(r"\s+", " ", "%s %s" % (s.get("status") or "", s.get("planDetails") or "")).strip() for s in st)))[:200]
    if (begin and dos8 < begin) or (end and dos8 > end):
        return "no", "the plan's own dates (%s to %s) do not cover %s%s" % (mdy(begin) or "?", mdy(end) or "open", mdy(dos8), ("; " + words) if words else ""), (begin, end)
    rows = [b for b in (j.get("benefitsInformation") or []) if isinstance(b, dict)]
    if cms:
        other = [b for b in rows if b.get("code") in ("R", "U") and (b.get("insuranceTypeCode") or "") in MA_TYPES and covers(b.get("benefitsDateInformation"))]
        if other:
            names = sorted(set((e_.get("entityName") or "?") for b in other for e_ in (b.get("benefitsRelatedEntities") or []) if isinstance(e_, dict))) or ["a plan of type %s" % other[0].get("insuranceTypeCode")]
            return "no", "Medicare names another primary payer on %s: %s" % (mdy(dos8), ", ".join(names)[:160]), (begin, end)
        partb = [b for b in rows if str(b.get("code")) == "1" and b.get("insuranceTypeCode") == "MB"]
        if [b for b in partb if covers(b.get("benefitsDateInformation"))]: return "yes", "Medicare Part B active on %s%s" % (mdy(dos8), ("; " + words) if words else ""), (begin, end)
        return "no", "Medicare Part B is not shown active on %s%s" % (mdy(dos8), ("; " + words) if words else ""), (begin, end)
    act = [s for s in st if str(s.get("statusCode")) in ACTIVE]; ina = [s for s in st if str(s.get("statusCode")) == "6"]
    lim = re.search(NOT_MEDICAL + "|" + LIMITED, words.upper().replace("TRICARE FOR LIFE", "TRICARE"))      # active, but not a plan that pays a physician's visit
    if act and lim: return "no", "active, but the answer says %s: %s" % (lim.group(0).lower(), words), (begin, end)
    if act and not ina: return "yes", words or "active", (begin, end)
    if ina and not act: return "no", words or "inactive", (begin, end)
    return "error", "the answer shows no clear plan status%s" % ((" (" + words + ")") if words else ""), (begin, end)

def clinician(cpts, label):
    """(the profile the visit belongs under, why) - round 7, 8.4: an initial nursing-facility visit is the physician's whatever the feed names;
    every other visit is the clinician its own feed message names. (None, why) when that cannot be told: William confirms."""
    if set(cpts or ()) & INITIAL_NF: return PHYSICIAN, "an initial nursing-facility visit is the physician's whatever the feed names (William 11/10/2026)"
    p = LABELS.get(str(label or "").strip())
    if p: return p, "the feed names " + WHO[p]
    return None, ("the clinician of its feed message is not on record" if not label else "the feed names a clinician who is neither of the practice's two")

def admission(vid, dos8, admit8, cpts, others):
    """What is wrong with the visit's admission date: a hospital visit without one, one after the date of service, two admission dates in one
    stay (another visit of the chart carries a different date although both dates are on or before both dates of service)."""
    out = []
    if (set(cpts or ()) & set(resave.HOSP_CODES)) and not admit8: out.append("a hospital visit with no admission date")
    if admit8 and dos8 and admit8 > dos8: out.append("its admission date %s is after its service date %s" % (mdy(admit8), mdy(dos8)))
    two = [(v, a) for v, d, a in others if v != vid and a and admit8 and a != admit8 and d and dos8 and max(a, admit8) <= min(d, dos8)] if admit8 else []
    if two: out.append("two admission dates in one stay: %s %s, %s" % (vid, mdy(admit8), ", ".join("%s %s" % (v, mdy(a)) for v, a in two[:3])))
    return out

def approved(path):
    """{visit: entry} from the owner's approved file (round 7, 8.8). Raises when the file cannot be read - nothing is saved or moved then.
    An entry whose decision this helper does not know is kept for William (never touched); a bare {visit: order} needs a dated check."""
    j = json.load(open(path)); v = j.get("visits") if isinstance(j, dict) and isinstance(j.get("visits"), dict) else j
    if not isinstance(v, dict): raise ValueError("no visits in it")
    out = {}
    for vid, e in v.items():
        if not str(vid).startswith("vst"): continue
        e = dict(e) if isinstance(e, dict) else {"order": str(e), "decision": "send_if_active_on_dos"}
        if e.get("decision") not in DECISIONS: e["decision_read"] = e.get("decision"); e["decision"] = "william"
        out[vid] = e
    return out

def main():
    a = sys.argv[1:]
    def stop(words): print(words); sys.exit(2)
    def opt(name, default=None):
        if name not in a: return default
        if a.index(name) + 1 >= len(a) or a[a.index(name) + 1].startswith("--"): stop("%s needs a value after it - nothing done" % name)
        return a[a.index(name) + 1]
    LIVE = "--live" in a; COVER = "--coverage" in a; FIX = "--fix-clinician" in a; SAVE = "--resave" in a; STAND = "--standing" in a
    days = int(opt("--days", "30")); cap_n = int(opt("--max", "0") or 0); only = set((opt("--only") or "").split(",")) - {""}
    apath = opt("--approved")
    if SAVE and not (apath or STAND): stop("--resave needs --approved <file> (the owner's visits) or --standing (William's standing word, 11/10/2026) - nothing done")
    if FIX and not apath: stop("--fix-clinician needs --approved <file> - nothing done")
    need = ("detail", "visit_charges", "CHG_FIELDS", "order_list", "billed_reasons", "admit_of", "restore_admit", "HOSP_CODES", "set_insorder")
    old = [n for n in need if not hasattr(resave, n)]
    if old: print("TOP OF THE REPORT - FEED ORDER SWEEP DID NOT RUN: resave.py in this folder is older than 11/10/2026 (no %s) - copy the repository's scripts/helpers/resave.py here and run again" % ", ".join(old)); sys.exit(2)
    AP = {}; ap_err = ""      # the owner's approved file: the one named, else the workspace's own copy when there is one (its William visits are never touched)
    try:
        if apath: AP = approved(apath)
        elif os.path.exists(APPROVED): AP = approved(APPROVED)
    except Exception as e: ap_err = "%s: %s" % (type(e).__name__, str(e)[:120])
    if ap_err and (SAVE or FIX or COVER):
        print("TOP OF THE REPORT - FEED ORDER SWEEP: the owner's approved file %s could not be read (%s) - nothing was bought, moved or saved" % (apath or APPROVED, ap_err)); sys.exit(2)
    amd.login_cached(); os.makedirs(REG, exist_ok=True)
    now = utcnow(); stamp = now.strftime("%Y%m%dT%H%M%SZ"); today8 = now.strftime("%Y%m%d"); cutoff = (now - datetime.timedelta(days=days)).isoformat()
    for i_ in range(2, 99):      # two runs in one second never write over each other's registers
        if not any(os.path.exists(os.path.join(REG, "feed_order_%s_%s.json" % (k_, stamp))) for k_ in ("sweep", "coverage", "fixclin", "resave")): break
        stamp = now.strftime("%Y%m%dT%H%M%SZ") + "_%d" % i_
    # ---- what earlier runs left: import rows, the feed's clinicians, clinician moves, dated checks, stops, visits already seen billed ----------
    ROWS = {}
    for f in regs("feed_import_"):
        for r in (jload(f) or {}).get("created") or []:
            if r.get("visit"): ROWS[r["visit"]] = dict(r, stamp=os.path.basename(f)[len("feed_import_"):-5])
    FEED = {}
    for f in regs("feed_recon_"):
        for r in (jload(f) or {}).get("rows") or []:
            if r.get("v") and r.get("prov") and r["v"] not in FEED: FEED[r["v"]] = r["prov"]
    MOVES = {}
    for st, j in earlier("feed_order_fixclin_"):
        for m in j.get("moves") or []:
            if m.get("visit"): MOVES[m["visit"]] = dict(m, stamp=st)
    ANS = {}
    for st, j in earlier("feed_order_coverage_"):
        for x in j.get("answers") or []: ANS.setdefault((x.get("chart"), d8(x.get("dos")), x.get("plan_id")), []).append(x)
    STOPS = ["%s (%s; registers/%s%s.json)" % (r.get("visit"), r.get("unexpected"), p_, st) for p_, k_ in (("feed_order_resave_", "rows"), ("feed_order_fixclin_", "moves"))
             for st, j in earlier(p_) for r in j.get(k_) or [] if r.get("unexpected") and not r.get("cleared")]
    PILOT = {k_: not any(r.get("sent") and r.get("ok") for st, j in earlier(p_) for r in j.get(k_) or []) for p_, k_ in (("feed_order_resave_", "rows"), ("feed_order_fixclin_", "moves"))}
    sw = earlier("feed_order_sweep_"); BILLED = set(sw[-1][1].get("billed") or []) if sw else set()
    VREC = {}
    def vrec(row):
        s_ = row.get("stamp")
        if s_ not in VREC: VREC[s_] = jload(os.path.join(REG, "feed_verify_%s.json" % s_)) or {}
        return VREC[s_].get(row.get("pid"))
    CARS = {}
    for f in ("carriers_rich.json", "carriers.json"):
        for k, v in (jload(f) or {}).items():
            if isinstance(v, (list, tuple)) and v: CARS.setdefault(k, (str(v[0]), str(v[1]) if len(v) > 1 else ""))
            elif isinstance(v, str) and v.startswith("car"): CARS.setdefault(v, (k, ""))
    CH = {}
    def chart(pid):
        """The chart's plans as AdvancedMD shows them now (one getdemographic per chart and run). The patient's name and birth date stay in memory
        for the dated check only - never printed, never written."""
        if pid not in CH:
            try:
                r = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "pat%s" % num(pid), "nocookie": "1"}))
                p = re.search(r"<patient [^>]*>", r)
                if "Fault" in r or not p: raise RuntimeError("the chart could not be read")
                plans = []
                for t in re.findall(r"<insplan ([^>]*)>", r):
                    x = dict(re.findall(r'(\w+)="([^"]*)"', t))
                    if not x.get("id"): continue
                    code, name = CARS.get(x.get("carrier"), (x.get("carrier") or "?", ""))
                    plans.append({"id": x["id"], "code": code, "name": name, "seq": x.get("sequence") or "", "begin": d8(x.get("begindate")), "end": d8(x.get("enddate")), "member": x.get("subscribernum") or ""})
                CH[pid] = {"pa": dict(re.findall(r'(\w+)="([^"]*)"', p.group(0))), "plans": plans, "open": [x for x in plans if not x["end"]]}
            except Exception as e: CH[pid] = {"error": str(e)[:100], "open": [], "plans": []}
        return CH[pid]
    # ---- the listing ------------------------------------------------------------------------------------------------------------------------
    pick = sorted(v for v, r in ROWS.items() if (r.get("at") or "") >= cutoff and r.get("charges")) + [v for v in AP if v in ROWS]
    pick = sorted(set(x for x in pick if not only or x in only), key=lambda x: (d8(ROWS[x].get("dos")), ROWS[x].get("pid") or "", x))
    INFO = []; counts = {"read": 0, "charge reads": 0, "billed": 0, "billed before": 0, "waiting for the claim run": 0, "not billed to insurance": 0, "voided": 0, "could not be read": 0, "EMPTY insurance order": 0}
    newly_billed = set()
    for vid in pick:
        row = ROWS[vid]; mv = MOVES.get(vid) if (MOVES.get(vid) or {}).get("ok") else None
        if vid in BILLED: counts["billed before"] += 1; continue
        cids = list(mv.get("new_charges") or []) if mv else list(row.get("charges") or [])
        exempt = {row.get("quality_charge"), row.get("mvp_charge")} - {None, ""}
        vis = None; live = []; void = []; unread = "" if cids else "the import register holds no charge id for it"; cpt = {}
        for cid in cids:
            try:
                d = ET.fromstring(resave.detail(num(cid))); counts["charge reads"] += 1
            except Exception as e:
                unread = "%s could not be read (%s)" % (cid, type(e).__name__); break
            c = next((x for x in d.iter("charge") if x.get("id") == cid), None)
            if c is None: unread = "%s is not in its own detail" % cid; break
            if vis is None: vis = d.find(".//visit")
            cpt[cid] = {x.get("id"): x.get("code") for x in d.findall(".//proccodelist/proccode") if x.get("id")}.get(c.get("proccode"), "")
            if c.get("void") == "1":
                if cid not in exempt: void.append(cid)      # a void no-charge quality line (1123F / M0004) never counts against the visit (round 6)
            else: live.append(c)
            if live and resave.billed_reasons(live): break      # billed: one read is enough
        counts["read"] += 1; time.sleep(0.2)
        billed = resave.billed_reasons(live) if not unread else []
        st = ("could not be read" if unread or vis is None else "voided" if not live else "billed" if billed else
              "not billed to insurance" if not any(c.get("billins") == "1" for c in live) else "EMPTY insurance order" if resave.order_list(vis) == "" else "waiting for the claim run")
        counts[st] += 1
        if st == "billed": newly_billed.add(vid); continue
        if st in ("waiting for the claim run", "not billed to insurance") or (st == "voided" and vid not in AP): continue
        dos8 = d8(row.get("dos")); cpts = list(row.get("cpts") or [])
        info = {"visit": vid, "now": (mv or {}).get("new_visit") or (vis.get("id") if vis is not None else vid), "chart": row.get("pid"), "dos": mdy(dos8), "dos8": dos8, "state": st,
                "age": age(today8, dos8),
                "cpts": cpts, "charges": [c.get("id") for c in live], "void": void, "unread": unread, "billed": billed,
                "list": resave.order_list(vis) if vis is not None else None, "profile": vis.get("profile") if vis is not None else None,
                "admit8": d8(resave.admit_of(vis)) if vis is not None else "", "patbal": round(sum(float(c.get("patbalance") or 0) for c in live), 2), "codes": sorted(set(cpt.values()) - {""})}
        info["expected"], info["clin_why"] = clinician(cpts, FEED.get(vid))
        INFO.append(info)
    ADM = {x["visit"]: x["admit8"] for x in INFO}; BYC = {}      # admission dates: every visit of the chart the registers know (what AdvancedMD shows for the visits read now)
    for v, r in ROWS.items(): BYC.setdefault(r.get("pid"), []).append((v, d8(r.get("dos")), ADM[v] if v in ADM else d8(r.get("admit"))))
    for info in INFO: info["admission"] = admission(info["visit"], info["dos8"], info["admit8"], info["cpts"], BYC.get(info["chart"]) or []) if info["state"] == "EMPTY insurance order" else []
    empty = [x for x in INFO if x["state"] == "EMPTY insurance order"]
    for info in empty:
        ch = chart(info["chart"]); ap = AP.get(info["visit"])
        med = [p for p in ch["open"] if not re.search(NOT_MEDICAL, ("%s %s" % (p["code"], p["name"])).upper().replace("TRICARE FOR LIFE", "TRICARE"))]
        row = ROWS[info["visit"]]
        if "open_plans_at_entry" in row and not (row.get("open_plans_at_entry") is None and row.get("chart_insorder") is None):
            nope = row.get("open_plans_at_entry") == 0 or row.get("chart_insorder") == ""      # the import's own record (round 7, section 7)
        else:      # a batch from before 11/10/2026: the insurance check's record of that batch says whether the chart had an open plan
            rec = vrec(row); nope = (not [p for p in rec.get("plans") or [] if not str(p.get("end") or "").strip()] or rec.get("insorder") == "") if isinstance(rec, dict) else None
        info["no_plan_at_entry"] = nope; info["standing"] = med[0]["seq"] if (nope and len(med) == 1 and ap is None) else ""
        payer = ", ".join("%s seq %s" % (p["code"], p["seq"]) for p in sorted(ch["open"], key=lambda p: p["seq"])) or ("the chart could not be read" if ch.get("error") else "no open plan on the chart")
        prob = []
        if info["expected"] and info["profile"] != info["expected"]: prob.append("clinician: entered under %s - %s" % (WHO.get(info["profile"], info["profile"]), info["clin_why"]))
        elif not info["expected"]: prob.append("clinician: %s - William confirms who saw the patient" % info["clin_why"])
        if set(info["cpts"]) & INITIAL_NF and LABELS.get(str(FEED.get(info["visit"]) or "").strip(), PHYSICIAN) != PHYSICIAN:      # 8.4: shown, so William can confirm who saw the patient
            prob.append("an initial nursing-facility visit: the physician's by William's rule - the feed names %s: William confirms who saw the patient" % WHO[LABELS[FEED[info["visit"]].strip()]])
        if info["void"]: prob.append("charge(s) the import entered now read void: %s" % ",".join(info["void"]))
        if info["patbal"] > 0.004: prob.append("$%.2f sits on the patient" % info["patbal"])
        prob += info["admission"]
        nxt = ("kept for William by the owner's approved file - never saved or changed by this helper" if ap is not None and ap["decision"] == "william" else
               "the owner's approved file: %s%s%s" % (ap["decision"], (", order " + str(ap.get("order"))) if ap.get("order") else "", (", moved to %s first" % WHO.get(ap["clinician"], ap["clinician"])) if ap.get("clinician") else "") if ap is not None else
               "standing word: saved once every check passes" if info["standing"] else
               "for William: %s" % ("its import row does not say whether the chart had a plan when it was entered" if nope is None else "it had an open plan when it was entered" if not nope
                                    else "the chart has %d open medical plans now - exactly one is needed" % len(med)))
        info["payer"] = payer; info["problems"] = prob; info["next"] = nxt      # the TOP line itself is printed at the end, with what this run did about the visit
        info["top"] = "TOP OF THE REPORT - NO CLAIM CAN BE MADE: %s %s%s service date %s (%s days old), payer %s: its insurance order is empty - AdvancedMD makes no claim for it and shows it on no work list%s | %s" % (
            info["chart"], info["visit"], (" (now %s)" % info["now"]) if info["now"] != info["visit"] else "", info["dos"], "?" if info["age"] is None else info["age"], payer, ("; " + "; ".join(prob)) if prob else "", nxt)
    for info in INFO:
        if info["state"] in ("could not be read", "voided"):
            print("FEED ORDER SWEEP: %s %s service date %s %s%s - for a person" % (info["chart"], info["visit"], info["dos"], info["state"], (": " + info["unread"]) if info["unread"] else
                  " - every charge the import entered reads void (if a clinician move made new charges, its register registers/feed_order_fixclin_<stamp>.json is missing)" if info["state"] == "voided" else ""))
    for s_ in STOPS: print("TOP OF THE REPORT - FEED ORDER SWEEP STOPPED: an earlier save or move did not read back as asked: %s - nothing more is saved or moved until a person has looked at that visit and written \"cleared\" into its row" % s_)
    for v in sorted(set(AP) - set(ROWS)): print("FEED ORDER SWEEP: %s is in the owner's approved file but in no import register - for a person" % v)
    print("Feed order sweep %s: %d visit(s) read (entered in the last %d days or in the owner's approved file; %d charge detail(s))%s; %d visit(s) on %d chart(s) with an EMPTY insurance order" % (
        stamp, counts["read"], days, counts["charge reads"], "".join(": " + ", ".join(x_) for x_ in [["%s %d" % (k, n) for k, n in counts.items() if k not in ("read", "charge reads", "EMPTY insurance order") and n]] if x_),
        len(empty), len({x["chart"] for x in empty})))
    # ---- what every save needs (round 7, 8.2) -----------------------------------------------------------------------------------------------
    def proof(info, ap, plan):
        """(yes | no | error | "", words): the proof of coverage on the visit's date of service for that plan."""
        if ap is not None and ap.get("decision") == "send" and ap.get("evidence"): return "yes", "the approved file: %s" % str(ap["evidence"])[:80]
        got = ANS.get((info["chart"], info["dos8"], plan["id"])) or []
        if not got: return "", "no eligibility check dated to %s yet" % info["dos"]
        return got[-1].get("active") or "error", "the check dated to %s answered: %s" % (info["dos"], got[-1].get("words") or "")[:180]
    def order_for(info, ap):
        """(the order to save, why there is none)."""
        if ap is None: return info.get("standing") or "", ("" if info.get("standing") else "not standing-word work")
        if ap.get("decision") != "order_by_dated_check": return str(ap.get("order") or "").replace(" ", ""), ("" if ap.get("order") else "the approved file gives no order")
        cand = [p for p in chart(info["chart"])["open"] if p["seq"] in [str(s) for s in ap.get("order_candidates") or []]]
        res = {p["seq"]: proof(info, ap, p)[0] for p in cand}; yes = [s for s, r in res.items() if r == "yes"]
        if len(yes) == 1: return yes[0], ""
        if len(yes) > 1: return "", "both plans answer active on %s - William decides the order" % info["dos"]
        if res and all(r == "no" for r in res.values()): return "", "neither plan answers active on %s - for William" % info["dos"]
        return "", "the plans have no answer from a check dated to %s yet" % info["dos"]
    def checks(info, ap, order, move=False):
        """[(what, words)] for every check of the save that fails - [] = all pass. move: the approved file moves the visit to its clinician first."""
        bad = []; ch = chart(info["chart"])
        if ch.get("error"): return [("chart", ch["error"])]
        if not info["expected"]: bad.append(("clinician", info["clin_why"] + " - William confirms who saw the patient"))
        elif info["profile"] != info["expected"] and not (move and ap is not None and ap.get("clinician") == info["expected"]):
            bad.append(("clinician", "entered under %s, but %s" % (WHO.get(info["profile"], info["profile"]), info["clin_why"])))
        elif not move and ap is not None and ap.get("clinician") and info["profile"] != ap["clinician"]:      # the file moves it first; never saved under another clinician than it names
            bad.append(("clinician", "the owner's approved file moves this visit to %s first (--fix-clinician) - it is still under %s" % (WHO.get(ap["clinician"], ap["clinician"]), WHO.get(info["profile"], info["profile"]))))
        if info["billed"]: bad.append(("billed", "already billed (%s) - never saved" % ", ".join(info["billed"])))
        if info["patbal"] > 0.004: bad.append(("balance", "$%.2f sits on the patient" % info["patbal"]))
        if info["void"]: bad.append(("charges", "charge(s) the import entered now read void: %s" % ",".join(info["void"])))
        for i_, s_ in enumerate([x for x in (order or "").split(",") if x]):      # no order: the caller says why (nothing to check here)
            at = [p for p in ch["open"] if p["seq"] == s_]
            if len(at) != 1: bad.append(("plan", "%d open plan(s) at sequence %s - exactly one is needed" % (len(at), s_))); continue
            p = at[0]; want = next((str(x.get("carrier")) for x in (ap or {}).get("plans_in_force_today") or [] if str(x.get("seq")) == s_), None)
            if want and want != p["code"]: bad.append(("plan", "the plan at sequence %s is %s now - the approved file names %s" % (s_, p["code"], want)))
            if p["begin"] and info["dos8"] and p["begin"] > info["dos8"]: bad.append(("plan", "AdvancedMD's plan at sequence %s begins %s, after the service date" % (s_, mdy(p["begin"]))))
            if i_ == 0:
                r_, w_ = proof(info, ap, p)
                if r_ != "yes": bad.append(("coverage", "no proof of coverage on %s: %s" % (info["dos"], w_) if not r_ else w_))
        bad += [("admission", w_) for w_ in info.get("admission") or []]
        return bad
    def deceased(info, order):
        import deceased_guard
        p = next((x for x in chart(info["chart"])["open"] if x["seq"] == order.split(",")[0]), {})
        blocked, why = deceased_guard.check(num(info["chart"]), info["dos"], p.get("code"), next((c for c in info["cpts"] if c in CCM), None), allow_lookup=LIVE)
        return [("deceased", why)] if blocked else []
    stopped = []; MOVED = set()
    # ---- --coverage: one eligibility check dated to the date of service per chart, date and plan (paid, capped) -------------------------------
    if COVER:
        bought = 0; cost = 0.0; new = []; waits = []; would = []; asked = set()
        for info in empty:
            ap = AP.get(info["visit"]); ch = chart(info["chart"])
            if ap is not None and (ap.get("decision") == "william" or (ap.get("decision") == "send" and ap.get("evidence"))): continue
            if ap is None and not info.get("standing"): continue
            seqs = [str(s) for s in ap.get("order_candidates") or []] if (ap is not None and ap.get("decision") == "order_by_dated_check") else [(order_for(info, ap)[0] or "?").split(",")[0]]
            pre = [b for b in checks(info, ap, seqs[0] if seqs else "", move=True) if b[0] not in ("coverage", "plan")]
            if pre or not seqs: info["coverage"] = "no check bought: " + ("; ".join(w for k, w in pre) or "no plan to check"); continue
            for p in [x for x in ch["open"] if x["seq"] in seqs]:
                key = (info["chart"], info["dos8"], p["id"]); got = ANS.get(key) or []
                if key in asked or (got and (got[-1].get("active") in ("yes", "no") or got[-1].get("final"))): continue      # answered (proof, or listed for William), or nothing a new check can change
                if sum(1 for x in got if x.get("active") == "error") >= 2: info["coverage"] = "asked twice, the vendor answered with an error both times - for William"; continue
                asked.add(key)
                if bought >= CAP_CHECKS or round((bought + 1) * PRICE, 2) > CAP_DOLLARS: waits.append("%s %s %s" % (info["visit"], info["dos"], p["code"])); continue
                if not LIVE: would.append("%s %s %s seq %s" % (info["visit"], info["dos"], p["code"], p["seq"])); bought += 1; continue
                x = {"visit": info["visit"], "chart": info["chart"], "dos": info["dos"], "plan_id": p["id"], "code": p["code"], "seq": p["seq"], "at": utcnow().isoformat()}
                payer = "CMS" if p["code"] in MEDICARE else CAR2STEDI.get(p["code"]); pa = ch.get("pa") or {}
                last, _c, first = (pa.get("name") or "").partition(","); first = first.strip().split(" ")[0] if first.strip() else ""; last = last.strip(); b8 = d8(pa.get("dob"))
                if not payer: x.update(active="error", words="the vendor has no eligibility route for %s - nothing was bought" % p["code"], bought=False, final=True)
                elif not p["member"]: x.update(active="error", words="the plan has no member number in AdvancedMD - nothing was bought", bought=False, final=True)
                elif not (first and last and b8): x.update(active="error", words="the chart lacks what the check needs - nothing was bought", bought=False, final=True)
                else:
                    import stedi
                    x.update(payer=payer, bought=True); bought += 1; cost = round(bought * PRICE, 2)
                    try:
                        act, words, (pb, pe) = verdict(stedi.elig(payer, first, last, b8, p["member"], info["dos8"], pid=num(info["chart"])), info["dos8"], payer == "CMS", b8)
                        x.update(active=act, words=words, plan_begin=mdy(pb), plan_end=mdy(pe))
                    except Exception as e:
                        x.update(active="error", words="the check failed (%s %s)" % (type(e).__name__, getattr(getattr(e, "response", None), "status_code", "") or ""))
                    time.sleep(0.3)
                ANS.setdefault(key, []).append(x); new.append(x)
        if LIVE and new: json.dump({"what": "eligibility checks dated to the service date (feed_order_sweep.py --coverage, round 7) - no name, birth date or member id", "stamp": stamp,
                                    "price_per_check": PRICE, "checks": bought, "cost": cost, "answers": new}, open(os.path.join(REG, "feed_order_coverage_%s.json" % stamp), "w"), indent=1)
        n = {k: sum(1 for x in new if x.get("active") == k) for k in ("yes", "no", "error")}
        print("Feed order coverage: %d eligibility check(s) dated to the service date %s - $%.2f at $%.2f a check (cap %d checks / $%.0f a run)%s%s" % (
            bought, "bought" if LIVE else "would be bought (dry run - nothing bought)", round(bought * PRICE, 2), PRICE, CAP_CHECKS, CAP_DOLLARS,
            ("; active on the date %d, not active %d, error %d" % (n["yes"], n["no"], n["error"])) if LIVE else "", ("; %d wait for the next run (cap reached)" % len(waits)) if waits else ""))
        for x in new:
            if x.get("active") != "yes": print("FEED ORDER COVERAGE - for William: %s %s service date %s, %s seq %s: %s - %s" % (x["chart"], x["visit"], x["dos"], x["code"], x["seq"], x["active"], x.get("words")))
        for w in would: print("FEED ORDER COVERAGE (dry run): would check %s" % w)
    # ---- --fix-clinician: the approved file's clinician moves (William 11/10/2026, Q4) ----------------------------------------------------------
    if FIX:
        out = []; done = 0
        for info in empty:
            ap = AP.get(info["visit"]); target = (ap or {}).get("clinician")
            if not target or (ap or {}).get("decision") == "william" or info["profile"] == target: continue
            rec = {"visit": info["visit"], "chart": info["chart"], "dos": info["dos"], "to": target, "live": LIVE, "sent": False, "ok": False, "at": utcnow().isoformat()}
            order, why = order_for(info, ap)
            bad = ([("clinician", "the approved file names %s - only the nurse practitioner's profile is moved here" % target)] if target != NP else
                   [("clinician", "an initial nursing-facility visit stays under the physician (William 11/10/2026)")] if set(info["cpts"]) & INITIAL_NF else
                   [("clinician", "the feed names %s, the approved file %s - for William" % (WHO.get(info["expected"], "no clinician of the practice"), WHO[target]))] if info["expected"] != target else [])
            bad += ([] if order else [("order", why or "no order to save")]) + [b for b in checks(info, ap, order, move=True) if b[0] != "clinician"]
            if not bad: bad = deceased(info, order)
            if STOPS or stopped: bad = [("stop", "an earlier save or move did not read back as asked - nothing is moved")]
            if bad:
                rec["refused"] = info["move"] = "; ".join(w for k, w in bad); out.append(rec)
                print("FEED ORDER CLINICIAN - not moved: %s %s %s - %s" % (info["chart"], info["visit"], info["dos"], rec["refused"])); continue
            if PILOT["rows"]:      # the remedy order (round 7, 9): first ONE save of a visit whose clinician matches, read back; the moves come after it
                rec["waits"] = info["move"] = "the clinician moves wait until the first save of this helper (the pilot) has read back as asked"; out.append(rec)
                print("FEED ORDER CLINICIAN - waits: %s %s %s - %s" % (info["chart"], info["visit"], info["dos"], rec["waits"])); continue
            if (PILOT["moves"] and done >= 1) or (cap_n and done >= cap_n):
                rec["waits"] = info["move"] = "the pilot moves ONE visit and reads it back first - the next run does the rest" if PILOT["moves"] else "--max %d reached" % cap_n; out.append(rec)
                print("FEED ORDER CLINICIAN - waits: %s %s %s - %s" % (info["chart"], info["visit"], info["dos"], rec["waits"])); continue
            if not LIVE:
                rec["dry"] = True; info["move"] = "would be moved (dry run)"; out.append(rec); done += 1
                print("FEED ORDER CLINICIAN (dry run): would move %s %s %s to %s" % (info["chart"], info["visit"], info["dos"], WHO[target])); continue
            vis, pat, allc = resave.visit_charges(num(info["charges"][0]))
            old_ids = [c.get("id") for c in allc]; admit = resave.admit_of(vis)
            rec.update(old_visit=vis.get("id"), old_charges=old_ids)
            if resave.billed_reasons(allc) or [c for c in allc if float(c.get("patbalance") or 0) > 0.004]:
                rec["refused"] = info["move"] = "billed, paid or a balance on the patient (read just now) - never moved"; out.append(rec); continue
            va = dict(vis.attrib); va["profile"] = target; va["force"] = "1"
            chg = "".join("<charge %s/>" % " ".join('%s="%s"' % kv for kv in ([("id", c.get("id"))] + [(f, c.get(f)) for f in resave.CHG_FIELDS if c.get(f) is not None])) for c in allc)
            # rebill_under_effinger.py's proven profile change, the same call: AdvancedMD voids the echoed charges and creates them again under the new profile
            r = amd.post(amd.msg("updvisitwithnewcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1",
                         "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"}, "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % kv for kv in va.items()), chg)))
            rec["sent"] = True; done += 1; time.sleep(0.8); prob = []
            if "Fault" in r:
                v0, p0, c0 = resave.visit_charges(num(old_ids[0]))
                rec["refused"] = "AdvancedMD refused the move: " + re.sub(r"\s+", " ", (re.search(r"<description>([^<]*)", r) or [None, r[:150]])[1])[:150]
                if [c.get("id") for c in c0] != old_ids or v0.get("profile") != vis.get("profile"): prob.append("the visit changed although the move was refused")
                rec["ok"] = False
            else:
                try: new = [c.get("id") for c in ET.fromstring(r).iter("charge") if c.get("void") != "1" and c.get("id") and c.get("id") not in old_ids]
                except Exception: new = []
                if not new: new = [c.get("id") for c in resave.visit_charges(num(old_ids[0]))[2] if c.get("id") not in old_ids]
                if not new: prob.append("the new charges could not be found after the move - look at the visit in AdvancedMD")
                else:
                    v2, p2, c2 = resave.visit_charges(num(new[0])); ids2 = [c.get("id") for c in c2]
                    rec.update(new_visit=v2.get("id"), new_charges=ids2, profile_now=v2.get("profile"), list_now=resave.order_list(v2))
                    if v2.get("profile") != target: prob.append("the visit reads profile %s, not %s" % (v2.get("profile"), target))
                    if [x for x in old_ids if x in ids2]: prob.append("old charge(s) still live beside the new ones: %s" % ",".join(x for x in old_ids if x in ids2))
                    if shape(c2) != shape(allc): prob.append("the charges read %s, before the move %s (procedure, modifiers, place of service, units)" % (shape(c2), shape(allc)))
                    if v2.get("id") != vis.get("id") and resave.visit_charges(num(old_ids[0]))[2]: prob.append("the old visit %s still has live charges" % vis.get("id"))
                    if admit and resave.admit_of(v2) != admit:      # the import's own call puts it back, then one more read
                        codes, refused = resave.restore_admit(v2.get("id"), c2, admit)
                        back = resave.admit_of(ET.fromstring(resave.detail(num(ids2[0]))).find(".//visit"))
                        rec["admit"] = "admission date %s was lost on the move and %s (%s)" % (admit, "written back" if back == admit else "NOT written back - now %s" % (back or "none"), ",".join(codes) or "no hospital code")
                        if back != admit: prob.append(rec["admit"])
                rec["ok"] = not prob
            if prob: rec["unexpected"] = "; ".join(prob); stopped.append("%s %s: %s" % (info["chart"], info["visit"], rec["unexpected"]))
            out.append(rec); MOVED.add(info["visit"])
            info["move"] = ("moved, read back as asked (new visit %s, charges %s, insurance order [%s])" % (rec.get("new_visit"), ",".join(rec.get("new_charges") or []), rec.get("list_now")) if rec["ok"]
                            else rec.get("unexpected") or rec.get("refused"))
            print("FEED ORDER CLINICIAN: %s %s %s -> %s: %s" % (info["chart"], info["visit"], info["dos"], WHO[target], info["move"]))
            if prob: break
        if LIVE and [r for r in out if r.get("sent")]:      # the memory of old -> new charges: the next runs read the new charges from here
            json.dump({"what": "clinician moves (feed_order_sweep.py --fix-clinician, round 7; William 11/10/2026 Q4): old -> new charges and visit", "stamp": stamp, "moves": out}, open(os.path.join(REG, "feed_order_fixclin_%s.json" % stamp), "w"), indent=1)
    # ---- --resave: the owner's approved visits, and the standing word ---------------------------------------------------------------------
    if SAVE:
        rows = []; done = 0
        for info in empty:
            vid = info["visit"]; ap = AP.get(vid)
            if vid in MOVED: continue      # moved this run: the next run saves it, after the move's read-back
            if ap is not None and apath:
                if ap.get("decision") == "william": rows.append({"visit": vid, "chart": info["chart"], "dos": info["dos"], "mode": "the owner's approved file", "kept": "kept for William - never saved or changed"}); continue
                mode = "the owner's approved file (%s)" % ap.get("decision")
            elif ap is None and STAND and info.get("standing"): mode = STANDING
            else:
                if apath and ap is None: rows.append({"visit": vid, "chart": info["chart"], "dos": info["dos"], "refused": "not in the owner's approved file - never saved by --resave --approved"})
                continue
            row = {"visit": vid, "chart": info["chart"], "dos": info["dos"], "mode": mode, "live": LIVE, "sent": False, "ok": False, "list_before": info["list"], "admit_before": mdy(info["admit8"]), "at": utcnow().isoformat()}
            order, why = order_for(info, ap); row["order"] = order
            bad = ([] if order else [("order", why or "no order to save")]) + checks(info, ap, order)
            if not bad: bad = deceased(info, order)
            if STOPS or stopped: bad = [("stop", "an earlier save or move did not read back as asked - nothing is saved")]
            if bad:
                row["refused"] = info["save"] = "; ".join(w for k, w in bad); rows.append(row)
                print("FEED ORDER SAVE - not saved: %s %s %s (%s) - %s" % (info["chart"], vid, info["dos"], mode, row["refused"])); continue
            if (PILOT["rows"] and (done >= 1 or vid in MOVES)) or (cap_n and done >= cap_n):      # the pilot is one visit whose clinician was never changed
                row["waits"] = info["save"] = ("the pilot saves ONE visit whose clinician was never changed and reads it back first - the next run does the rest" if PILOT["rows"] else "--max %d reached" % cap_n); rows.append(row)
                print("FEED ORDER SAVE - waits: %s %s %s - %s" % (info["chart"], vid, info["dos"], row["waits"])); continue
            if not LIVE:
                row["dry"] = True; info["save"] = "would be saved (dry run)"; rows.append(row); done += 1
                print("FEED ORDER SAVE (dry run): would save %s %s %s insurance order %s (%s)" % (info["chart"], vid, info["dos"], order, mode)); continue
            v0, p0, c0 = resave.visit_charges(num(info["charges"][0]))      # every live charge of the visit, also one the import register does not list: nothing billed, paid or on the patient
            if resave.billed_reasons(c0) or [c for c in c0 if float(c.get("patbalance") or 0) > 0.004]:
                row["refused"] = info["save"] = "billed, paid or a balance on the patient on one of its %d live charges (read just now) - never saved" % len(c0); rows.append(row)
                print("FEED ORDER SAVE - not saved: %s %s %s (%s) - %s" % (info["chart"], vid, info["dos"], mode, row["refused"])); continue
            ok, m = resave.set_insorder(num(info["charges"][0]), order)      # the list-aware save of round 7: skips nothing but a visit already right, refuses a billed one, reads back
            row.update(sent=m.startswith("resave "), words=m); done += 1; time.sleep(0.8)      # "resave ..." = a save went out ("visit ... already" / "... not saved" = none did)
            v2, p2, c2 = resave.visit_charges(num(info["charges"][0])); ids2 = [c.get("id") for c in c2]
            row.update(list_after=resave.order_list(v2), admit_after=mdy(resave.admit_of(v2)), profile=v2.get("profile"))
            prob = ([] if ok else ["the save did not read back as asked: " + m]) + (["its insurance order reads [%s], not [%s]" % (row["list_after"], order)] if row["list_after"] != order else [])
            prob += (["the admission date reads %s, before the save %s" % (row["admit_after"] or "none", row["admit_before"])] if d8(row["admit_after"]) != info["admit8"] else [])
            prob += (["the clinician reads %s, expected %s" % (row["profile"], info["expected"])] if row["profile"] != info["expected"] else [])
            prob += (["charge(s) no longer live: %s" % ",".join(x for x in info["charges"] if x not in ids2)] if [x for x in info["charges"] if x not in ids2] else [])
            row["ok"] = info["saved"] = not prob; rows.append(row)
            info["save"] = ("saved - insurance order [%s], admission date %s, clinician %s read back as asked" % (row["list_after"], row["admit_after"] or "none", row["profile"])) if row["ok"] else "; ".join(prob)
            print("FEED ORDER SAVE: %s %s %s (%s): %s" % (info["chart"], vid, info["dos"], mode, info["save"]))
            if prob: row["unexpected"] = "; ".join(prob); stopped.append("%s %s: %s" % (info["chart"], vid, row["unexpected"])); break
        if LIVE and [r for r in rows if r.get("sent") or r.get("unexpected")]:      # one row per visit of a run that sent something: the pilot and the stop live here
            json.dump({"what": "feed visits saved again with their insurance order (feed_order_sweep.py --resave, round 7) - one row per visit", "stamp": stamp, "rows": rows}, open(os.path.join(REG, "feed_order_resave_%s.json" % stamp), "w"), indent=1)
        n_ok = sum(1 for r in rows if r.get("ok")); n_ref = sum(1 for r in rows if r.get("refused")); n_wait = sum(1 for r in rows if r.get("waits"))
        print("Feed order saves%s: %d saved and read back, %d not saved (a check failed - listed above for William), %d waiting%s" % ("" if LIVE else " (dry run - nothing sent)", n_ok, n_ref, n_wait, " (pilot: one visit first)" if PILOT["rows"] and n_wait else ""))
    for s_ in stopped: print("TOP OF THE REPORT - FEED ORDER SWEEP STOPPED at %s - nothing more was sent; look at this visit in AdvancedMD before anything else is done" % s_)
    for info in empty:      # the visits still without an insurance order after this run (a visit saved and read back as asked is no longer one)
        if info.get("saved"): continue
        did = info.get("save") or info.get("move") or info.get("coverage") or ""
        print(info["top"] + ((" | this run: " + did) if did else ""))
    json.dump({"what": "feed visits with an EMPTY insurance order (feed_order_sweep.py, round 7) - read only; no name, birth date or member id", "stamp": stamp, "days": days,
               "live": LIVE, "phases": [k for k, on in (("coverage", COVER), ("fix-clinician", FIX), ("resave", SAVE), ("standing", STAND)) if on], "counts": counts,
               "visits": [{k: x.get(k) for k in ("visit", "now", "chart", "dos", "age", "state", "payer", "list", "profile", "expected", "problems", "next", "coverage", "move", "save", "unread") if x.get(k) not in (None, "", [])} for x in INFO],
               "billed": sorted(BILLED | newly_billed)}, open(os.path.join(REG, "feed_order_sweep_%s.json" % stamp), "w"), indent=1)
    print("register: registers/feed_order_sweep_%s.json" % stamp)

if __name__ == "__main__": main()
