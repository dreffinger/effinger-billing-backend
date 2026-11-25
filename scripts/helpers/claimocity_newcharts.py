# PLAIN ENGLISH (Claimocity feed ingest (generic; born as the [DOB] backlog import) - new charts for feed patients with no AMD chart).
# A NEW CHART IS MADE ONLY ON RULE 9 OF THE IDENTITY RULE, ONE PER CLAIMOCITY ID, NEVER WITH AN EMPTY BIRTH DATE
# (feed_identity.py - William 11/25/2026, after the feed step twice made a second chart for a patient whose own chart was there). An
# entry of the match file that says MISSING but was not decided by rule 9 of this version (an older match / resolve step wrote it)
# gets NO chart - a failed row says so. The name-and-date keys the rule decided together (one Claimocity id that came with two dates;
# until 11/25/2026 that made two charts) share ONE chart, and each of them gets "resolved".
# Creates the chart from the DFT PID segment (name, DOB, sex, address, phone; Claimocity id kept as additionalmrn like the
# integration does), chart number F<yymmdd>-NN - first FREE number, probed with lookuppatient code= (its own series so
# Gregg's numeric series cannot collide and two batches on one day cannot either), address line 2 = line 1
# (the 9/14 rule for feed charts), then adds the feed's IN1 payers that map to an AMD carrier (member id from IN1-49) so the
# cascade check has something to verify. Writes registers/feed_newcharts_1028.json and updates feed_match_1028.json (resolved).
# The date written, for the patient AND the responsible party: the feed's when it is REAL (feed_identity.real_dob - a batch that
# carries the id with a real date and with the placeholder uses the real one); otherwise the placeholder date feed_identity.NO_DOB_MDY,
# never an empty "//" - the register row then says "dob": "none" and is for William (face sheet needed).
# The chart number (11/25/2026): counting starts after the highest -NN any registers/feed_newcharts_*.json in the workspace holds for
# the series, and a number addpatient answers "Duplicate chart" for although the probe saw it free is passed over - the next one,
# up to 200 for one patient (until then three: on 11/13/2026 three numbers in a row were taken and the patient was left with no chart).
# A patient who still gets no chart is written to "failed" with the Claimocity id and a fixed reason. A register row and a printed
# line hold chart ids, Claimocity ids and the fixed words of feed_identity.py - never a piece of the name (until 11/25/2026 a failed
# row kept the first six characters of the name key and AdvancedMD's own words, and a plan row could keep AdvancedMD's answer).
# Each created row carries rule, why, flags, dob (real / none) and for_william, as the identity rule gave them.
# A plan row holds the carrier code the feed's payer was mapped to, AdvancedMD's plan id and its place in the order - nothing of the
# feed's own payer text (11/25/2026, the independent verification: until then "from" kept the first 30 characters of the IN1 carrier
# field, and a field that carried more than a payer - a patient's name behind it - went to the repository as it stood).
# THE PATIENT THAT WAITS FOR A CHART OF THIS RUN (11/25/2026, the independent verification). The resolve step lets a patient wait
# for the new chart of another Claimocity id BEFORE this step has made that chart; its entries name the ids it waits for
# ("waits_for"). When that chart could NOT be made (AdvancedMD refused it; no free chart number; no PID segment) this step, which
# knows it, puts the fixed words WHY_WAIT_FAILED on the waiting entries and marks them for William - one line "FOR WILLIAM: ..."
# beside the first id's own "could NOT be made". Until then the waiting id said in every run that a new chart "is made in this
# run" for the other one, which was not true, and was never a question for William. No chart is made for the waiting patient on
# a guess: when the first one's chart is made, the wait goes on as before - one run, a plain line.
# Proven 10/28/2026 on pat17478199 (chart F1028-01). Never touches existing charts.
import os as _os
STAMP = _os.environ.get("FEED_STAMP", "1028")            # batch stamp: every feed_*_<STAMP>.* file and register belongs to one ingest run
HL7_DIR = _os.environ.get("FEED_HL7_DIR", "/tmp/claude-0/-home-claude/b8abe0d4-8133-5488-ad3a-bd2fb16f50f8/scratchpad/hl7/claimocity_oct")
DXCACHE = _os.environ.get("FEED_DX_CACHE", "dx_cache_feed.json")   # ICD-10 -> dcode map shared by every run (null = not in AMD's table)
CHART_PREFIX = _os.environ.get("FEED_CHART_PREFIX", "F" + STAMP)   # chart-number series for charts this run creates
import amd, add_ins, re, json, glob, time, collections, datetime
try:
    import feed_identity as FI      # 11/25/2026 (William): the identity rule - which entries get a chart, the date it is written with, the fixed words of every row
except ImportError:      # a workspace that does not hold the rule yet: the repository clone's copy (the bootstrap and the driver's make_current copy the helpers from there)
    import importlib.util as _iu
    _sp = _iu.spec_from_file_location("feed_identity", "/home/claude/effinger-billing-backend/scripts/helpers/feed_identity.py"); FI = _iu.module_from_spec(_sp); _sp.loader.exec_module(FI)
amd.login_cached()
MATCH = json.load(open(("feed_match_%s.json" % STAMP)))
CARRIERS = json.load(open("carriers_rich.json")); CODE2CAR = {v[0]: k for k, v in CARRIERS.items()}
try:
    import feed_payer_map as _fpm      # 11/19/2026 (William: "fix it for the insurance intake for sure"): ONE payer-name table for every feed helper
except Exception:
    _fpm = None                        # an old workspace without the table keeps the list below
PAYER_MAP = [
    (r"MEDICARE A\b|FCSO|MEDICARE PART A|MEDICARE B\b|TRADITIONAL MEDICARE|^MEDICARE$|^MCA-|^MCB", "FLO02"),
    (r"SUNSHINE", "SUN01"), (r"SIMPLY", "SIM01"), (r"WELLCARE", "WEL04"), (r"HUMANA", "HUM01"),
    (r"CAPITAL HEALTH", "CAP07"), (r"AMBETTER", "AMB03"), (r"FLORIDA COMMUNITY CARE|FCC\b", "FLO99"),
    (r"UNITED ?HEALTH|UHC|AARP MEDICARE ADV", "UNI20"), (r"AARP", "AAR01"), (r"AETNA", "AET07"),
    (r"CIGNA", "CIG09"), (r"FLORIDA BLUE|BCBS|BLUE CROSS|BC/BS", "BCBS"), (r"TRICARE FOR LIFE|TFL", "TRI05"),
    (r"TRICARE", "TRI00"), (r"CHAMPVA", "CHA03"), (r"VA COMMUNITY|VACCN|VETERAN", "VACCN"),
    (r"MEDICAID(?! MANAGED)|AHCA|FLORIDA MEDICAID|^MCD|-MCD\b|^MCD-", "MCAD"), (r"MOLINA", "MOL01"),
]
SKIP_IN1 = r"LIABILITY|SELF PAY|PRIVATE PAY|PENDING|COINS|CO-INS|THERAPY|VACCINE|LAB\b|PART D|PDP|PRESCRIPTION|HOSPICE"
def in1_member(s):
    """IN1-49 (Insured's ID number) is where Claimocity puts the member id (10/28/2026: 769 of 1,076 IN1 rows; IN1-36 is always empty).
    An SSN-shaped value or junk ('+', 1-5 chars) is never a member id."""
    for i in (49, 36):
        v = (s[i].strip() if len(s) > i else "")
        if v and not re.fullmatch(r"\d{3}-?\d{2}-?\d{4}", v) and re.fullmatch(r"[A-Za-z0-9\-]{6,20}", v): return v
    return ""
PID = {}; IN1 = collections.defaultdict(list)
for f in glob.glob((HL7_DIR + "/*.hl7")):
    raw = open(f, errors="replace").read().replace("\r", "\n"); cur = None
    for line in raw.split("\n"):
        s = line.split("|")
        if s[0] == "MSH": cur = None; continue      # 11/25/2026: a message without a PID line never puts its insurance rows on the patient of the message before it
        if s[0] == "PID": cur = s[3]; PID.setdefault(cur, s)
        elif s[0] == "IN1" and cur:
            payer = s[4].split("^")[0] if len(s) > 4 else ""; member = in1_member(s)
            if payer and (payer, member) not in IN1[cur]: IN1[cur].append((payer, member))
REGF = ("registers/feed_newcharts_%s.json" % STAMP)
import os
reg = json.load(open(REGF)) if os.path.exists(REGF) else {"created": [], "failed": []}
TODAY8 = datetime.date.today().strftime("%Y%m%d")
def highest_number():
    # 11/25/2026: the highest -NN of this series in ANY feed_newcharts register of the workspace (this stamp's own among them) - counting starts after it.
    # Until then it started at the number of charts THIS stamp had made, so a second batch of the day began again at numbers the first had used.
    hi = 0
    for f in glob.glob("registers/feed_newcharts_*.json"):
        try: rows = json.load(open(f)).get("created") or []
        except Exception: continue      # a register of another shape, or one half written, holds no number to count from
        for c in rows:
            mm = re.fullmatch(re.escape(CHART_PREFIX) + r"-(\d+)", str(c.get("chart") or "")) if isinstance(c, dict) else None
            if mm: hi = max(hi, int(mm.group(1)))
    return hi
n = highest_number()      # the last number of the series known to be used
def chart_taken(chart):
    # lookuppatient code= matches the CHART code (captured 9/2026): any hit carrying exactly this chart means the number is in use
    try:
        r = amd.post(amd.msg("lookuppatient", "lookup", {"code": chart, "nocookie": "1"}), timeout=60)
        return any(dict(re.findall(r'(\w+)="([^"]*)"', x)).get("chart", "").upper() == chart.upper() for x in re.findall(r'<patient [^>]*/?>', r))
    except Exception:
        return False
def next_chart(left):
    # first free number of this run's series F<yymmdd>-NN: two batches on one day (Billing Button + daily task) never collide.
    # 11/25/2026: every call takes the NEXT number (a number handed out once is never handed out again in this run); left = [how many numbers
    # this patient may still take] - None when they are used up.
    global n
    while left[0] > 0:
        n += 1; left[0] -= 1
        c = "%s-%02d" % (CHART_PREFIX, n)
        if not chart_taken(c): return c
    return None
def save():
    json.dump(reg, open(REGF, "w"), indent=1); json.dump(MATCH, open(("feed_match_%s.json" % STAMP), "w"), indent=1)
def fail(fid, keys, why, chart=None, tries=None, answer=""):
    # a patient who gets no chart: a row free of patient data (the Claimocity id, a fixed reason, the last number tried) - written at once,
    # also when it is the last patient (until 11/25/2026 the register was written only after a chart was made). AdvancedMD's own words can
    # name the patient: they stay in the match file, which never leaves the workspace.
    row = {"feed_id": fid, "why": why}
    if chart: row["chart"] = chart
    if tries is not None: row["tries"] = tries
    reg["failed"].append(row)
    for k in keys:
        e = MATCH[k]; e["resolution"] = "NEW CHART NOT MADE: " + why; e["for_william"] = True
        e["flags"] = [x for x in (e.get("flags") or []) if x != FI.FLAG_NO_CHART_MADE] + [FI.FLAG_NO_CHART_MADE]
        if answer: e["amd_answer"] = answer[:300]
    print("FAIL", FI.show_id(fid), "-", why)
    print("FOR WILLIAM: the new chart for Claimocity id %s could NOT be made (%s) - its visits are not entered" % (FI.show_id(fid), why)); save()
todo = collections.OrderedDict()      # the Claimocity id(s) of one patient -> its name-and-date keys: ONE chart for all of them
for k, v in MATCH.items():
    if v["status"] != "MISSING" or v.get("resolved"): continue
    if v.get("rule") != 9 or not v.get("decided_for") or v.get("identity_rule") != FI.IDENTITY_RULE_VERSION:      # not rule 9 of this version: an older step's "MISSING" (it made the second charts)
        fail((v.get("feed_ids") or [""])[0], [k], FI.FAIL_NOT_DECIDED); continue
    todo.setdefault(tuple(v["decided_for"]), []).append(k)
for ids, keys in todo.items():
    v = MATCH[keys[0]]; fid = ids[0]
    mdy, dobkind = FI.chart_dob([k.rpartition("|")[2] for k in keys], TODAY8)      # the feed's date when it is real, else the placeholder date - never "//"
    k = next((x for x in keys if dobkind == "real" and FI.real_dob(x.rpartition("|")[2], TODAY8)), keys[0])      # the name the real date came with
    name = k.rpartition("|")[0]; last, _, first = name.partition(","); last = last.strip(); first = first.strip()
    seg = next((PID[i] for i in ids if i in PID), None)
    if not seg: fail(fid, keys, FI.FAIL_NO_PID); continue
    sex = seg[8] or "U"; addr = (seg[11] or "^^^^^").split("^"); phone = re.sub(r"\D", "", seg[14] or "")[-10:]
    left = [FI.CHART_TRIES]; chart = next_chart(left); tried = chart; tries = 0; m = None; r = ""
    street = addr[0] or "HCA"; city = addr[2] or "TALLAHASSEE"; st = addr[3] or "FL"; zipc = (addr[4] or "32308-4486")[:10]
    xml = ('<patient id="" name="%s,%s" dob="%s" sex="%s" chart="%s" profile="prof13" finclasscode="CC" relationship="1" hipaarelationship="18" '
           'additionalmrn="%s" respparty=""><address zip="%s" city="%s" state="%s" address1="%s" address2="%s" areacode="%s" countrycode="USA"/>'
           '<contactinfo homephone="%s"/></patient>') % (last, first, mdy, sex, chart, fid.upper()[:24], zipc, city, st, street, street, phone[:3], phone)
    while chart:
        tries += 1; tried = chart
        r = amd.post(amd.msg("addpatient", "demographics", {"nocookie": "1"}, xml), timeout=90)
        m = re.search(r'<patient id="(pat\d+)"', r)
        if m and 'success="1"' in r: break
        m = None
        if "uplicate chart" not in r: break      # a refusal that is not about the number: another number would not help
        chart = next_chart(left)   # the number was taken although the probe did not see it - the next number, same patient, until AdvancedMD stops answering Duplicate chart (11/25/2026)
        if chart: xml = re.sub(r'chart="[^"]*"', 'chart="%s"' % chart, xml, count=1)
    if not m:
        d = re.search(r"<description>(.*?)</description>", r, re.S)
        fail(fid, keys, FI.FAIL_REFUSED if tried and "uplicate chart" not in r else FI.FAIL_NUMBER, chart=tried, tries=tries, answer=(d.group(1) if d else r)); continue
    pid = m.group(1); chart = tried
    why = v.get("why") if v.get("why") in FI.WHY_WORDS else FI.WHY[9]      # only the rule's own fixed words reach the register
    rec = {"pid": pid, "chart": chart, "feed_ids": list(ids), "plans": [], "rule": 9, "why": why, "flags": [x for x in (v.get("flags") or []) if x in FI.FLAG_WORDS],
           "dob": dobkind, "for_william": bool(v.get("for_william")) or dobkind == "none"}
    # addpatient creates the responsible party with an EMPTY name -> inspector 117080083 "Relationship of Subscriber to Patient is
    # invalid" on every claim (10/28/2026). Name it right away with the proven updaterespparty shape.
    try:
        rd = amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"}, ""), timeout=60)
        rp = re.search(r'<patient [^>]*respparty="(resp\d+)"', rd)
        if rp:
            rr = amd.post(amd.msg("updaterespparty", "demographics", {"patientid": pid, "nocookie": "1"},
                         '<respparty id="%s" changed="1" name="%s,%s" o_name="" dob="%s" o_dob="" sex="%s" o_sex="M"/>' % (rp.group(1), last, first, mdy, sex)), timeout=60)
            rec["respparty"] = rp.group(1); rec["respparty_named"] = "Fault" not in rr and 'success="0"' not in rr
        else:
            rec["respparty_named"] = False
    except Exception as e:
        rec["respparty_named"] = "error %s" % type(e).__name__      # the kind of error only: its words could name the patient
    # insurance from IN1 (every message of this patient), first mappable payers, no group numbers (William's rule)
    seen = set()
    for i in ids:
        for payer, member in IN1.get(i, []):
            up = payer.upper()
            if re.search(SKIP_IN1, up) or (_fpm and (_fpm.skip(payer) or _fpm.kind(payer) == "ltc")): continue      # 11/19/2026: the shared table - a long-term-care-only plan is never the physician's payer
            code = _fpm.code(payer) if _fpm else next((c for pat, c in PAYER_MAP if re.search(pat, up)), None)
            if not code or code in seen or code not in CODE2CAR or not member: continue
            seen.add(code)
            try:
                insid, seq = add_ins.add(pid, CODE2CAR[code], member, finclass="CC")
                if insid: rec["plans"].append({"code": code, "ins": insid, "seq": seq})      # (11/25/2026: no "from" - the feed's own payer text can carry more than a payer, and this register travels to the repository)
                else: rec["plans"].append({"code": code, "err": FI.PLAN_NOT_ADDED})      # add_ins answers (None, AdvancedMD's own words) - words that can name the member number
            except Exception as e:
                rec["plans"].append({"code": code, "err": "%s (%s)" % (FI.PLAN_NOT_ADDED, type(e).__name__)})
            time.sleep(0.3)
    for x in keys: MATCH[x]["resolved"] = pid; MATCH[x]["resolution"] = "NEW CHART created %s (%s)" % (STAMP, chart); MATCH[x]["for_william"] = rec["for_william"]
    reg["created"].append(rec); print("OK", pid, chart, FI.show_id(fid), [(p["code"], p.get("seq")) for p in rec["plans"]])
    for line in FI.william_lines(dict(v, feed_dob=dobkind, flags=rec["flags"]), pid, fid): print("FOR WILLIAM: " + line)      # chart ids only - they belong at the top of the report
    save()
    time.sleep(0.5)
# ---- the patients that wait for a chart of this run (11/25/2026, the independent verification) -----------------------------------------------
# claimocity_resolve.py wrote on every entry that waits the Claimocity ids whose new chart it waits for ("waits_for"). A chart was made for
# an id when an entry decided for it now carries "resolved". Where one of the awaited charts was NOT made the wait's own words would say what
# is not true: the entry gets the fixed words for it and goes to William - no chart is made for the waiting patient here.
has_chart = {i for v in MATCH.values() if v.get("resolved") for i in (v.get("decided_for") or [])}; told = set()
for k, v in MATCH.items():
    awaited = [i for i in (v.get("waits_for") or []) if isinstance(i, str)] if isinstance(v.get("waits_for"), list) else []
    if v.get("rule") != 0 or v.get("why") != FI.WHY_SAME_RUN or not awaited or all(i in has_chart for i in awaited): continue
    v["why"] = FI.WHY_WAIT_FAILED; v["for_william"] = True; v["resolution"] = "not decided: %s - no chart chosen, none made" % FI.WHY_WAIT_FAILED
    ids = tuple(v.get("decided_for") or v.get("feed_ids") or [])
    if ids not in told:      # (said once for a patient that came under several name-and-date keys)
        told.add(ids)
        for line in FI.william_lines(v, "", list(ids)): print("FOR WILLIAM: " + line)
if told: save()
print("DONE created", len(reg["created"]), "failed", len(reg["failed"]))
