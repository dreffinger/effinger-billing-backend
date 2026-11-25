# PLAIN ENGLISH (Insurance intake from the feed for charts that already exist - the secondaries the import never entered)
# Decides: which insurance blocks the Claimocity feed carried are worth putting on an EXISTING chart, and does it. Built 11/19/2026
#   (William: "fix it for the insurance intake for sure ... optimize getting the correct insurances for billing on the back end using
#   apis first") after the comparison of all 31 feed files with the charts: the import enters feed insurance only when it CREATES a
#   chart, so on existing charts 74 usable blocks (55 charts) never arrived - nearly all the Medicaid side of a nursing-home resident
#   (Florida Community Care, Medicaid, Sunshine, Simply) and a few Medigap plans.
# What it does, per chart, cheapest source first:
#   1. the feed block: payer name -> carrier and kind through the ONE table (feed_payer_map.py); rows that are not a plan to bill
#      (liability, coinsurance rows, pending, dental ...) and long-term-care-only plans are dropped;
#   2. the chart (free): a carrier the chart already holds, open or ended, is never added again; a chart that already has an open
#      Medicaid-family plan is left to the nightly cascade (listed, not changed);
#   3. a block that names a different PRIMARY plan is never entered here - the feed only informs; the dated eligibility check of the
#      import / the cascade decides who is primary (listed for it);
#   4. Medicaid side: ONE Florida Medicaid eligibility check through Stedi with the feed's Medicaid number (the ordinary eligibility
#      price) - active or not, and WHICH managed plan the state names; the plan the STATE names wins over the feed's wording. Not
#      active = nothing added. Medicaid cannot answer (an error, an outage) = nothing added, tried again next run;
#      11/25/2026 (William: "correct every one that comes to the correct date of birth and insurance and fix them ... where we know the
#      correct dob but claimocity sends the wrong one or the 01011900 default date"): Medicaid is asked
#      with the CHART's own name and birth date - from the chart answer read in step 2, no extra call - whenever the chart's birth date
#      is a real one; else with the feed's, as before; never a mix of the two. Until that day it was asked with the FEED's name and birth
#      date - also when the feed carries a wrong date or the year-1900 placeholder for a patient whose chart was corrected from a face
#      sheet. The line it prints and the register entry say which one was asked whenever the two dates are not the same - by the kind
#      of slip, never with a name or a date. See lookup_who;
#   5. Medigap / TRICARE For Life / CHAMPVA: the plan is added and AdvancedMD's free eligibility check is run on it; a clear
#      'inactive' or 'not found' ends the plan again the same minute;
#   6. the plan is added with no group number and, when the chart's insurance order holds no Medicaid-family / secondary plan yet,
#      appended as the LAST plan of the order (Medicare or the Advantage plan stays first - William's standing order).
# Never touches: visits, claims, balances, the primary plan, a chart's existing plans. Nothing is re-billed here.
# Usage: python3 feed_in1_intake.py [--hl7-dir inbox/claimocity] [--live] [--max 60] [--stamp <run stamp>]
# Register: registers/feed_in1_intake.json (chart + carrier + outcome; one entry per chart and carrier - never asked twice)
import amd, add_ins, ins_update, elig_amd, stedi, adt_ingest, feed_payer_map as fpm, json, os, re, sys, time, datetime, collections
def opt(n, d=None): return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d
LIVE = "--live" in sys.argv; DIR = opt("--hl7-dir", "inbox/claimocity"); MAX = int(opt("--max", "60")); STAMP = opt("--stamp", datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H%MZ"))
CAR = json.load(open("carriers_rich.json")); CODE2CAR = {v[0]: k for k, v in CAR.items()}; CAR2CODE = {k: v[0] for k, v in CAR.items()}
PMAP = json.load(open("registers/claimocity_patient_map.json"))
REGF = "registers/feed_in1_intake.json"; REG = json.load(open(REGF)) if os.path.exists(REGF) else {}
STATE_PLAN = [(r"FLORIDA COMMUNITY", "FLO99"), (r"SUNSHINE", "SUN01"), (r"SIMPLY", "SIM01"), (r"HUMANA", "HUM01"), (r"MOLINA", "MOL10"), (r"STAYWELL|WELLCARE", "STA03")]
norm = lambda s: re.sub(r"[^A-Z0-9]", "", (s or "").upper())
def medicaid_answer(first, last, dob8, medicaid_id, pid):
    """('active'|'inactive'|'unknown', carrier code the state names or 'MCAD', short text). One Stedi eligibility check (payer 77027)."""
    try: j = stedi.elig("77027", first, last, dob8, medicaid_id, datetime.date.today().strftime("%Y%m%d"), pid=pid)
    except Exception as e: return "unknown", None, "Medicaid check failed (%s)" % type(e).__name__
    os.makedirs("patient_db/%s" % pid, exist_ok=True); json.dump(j, open("patient_db/%s/stedi_medicaid_%s.json" % (pid, datetime.date.today().strftime("%Y%m%d")), "w"))
    errs = [str(e.get("code")) for e in j.get("errors") or []]
    if errs: return "unknown", None, "Medicaid answered error %s" % ",".join(errs)
    ben = j.get("benefitsInformation") or []
    if not any(b.get("code") == "1" for b in ben): return "inactive", None, "Medicaid: no active coverage"
    names = []
    for b in ben:
        if b.get("code") in ("MC", "1", "R", "U"):
            for e in b.get("benefitsRelatedEntities") or []:
                if e.get("entityName"): names.append((b.get("code"), " ".join(str(x) for x in (b.get("planCoverage"), b.get("insuranceType"), e.get("entityName")) if x)))
    mma = [t for c, t in names if c == "MC" and not re.search(r"\bLTC\b|LONG.?TERM|DENTAL|TRANSPORT", t.upper())] or [t for c, t in names if c == "MC" and re.search(r"FLORIDA COMMUNITY", t.upper())]
    for t in mma:
        for pat, code in STATE_PLAN:
            if re.search(pat, t.upper()): return "active", code, "Medicaid active; the state names %s" % t[:60]
    return "active", "MCAD", "Medicaid active; no managed medical plan named (%s)" % ("; ".join(t[:30] for c, t in names[:3]) or "fee-for-service")
# ---- William 11/25/2026 ("correct every one that comes to the correct date of birth and insurance and fix them figure our how to do this for other charts that have the
# same mistake where we know the correct dob but claimocity sends the wrong one or the 01011900 default date") - WHOM MEDICAID IS ASKED ABOUT -----------------------------
# The feed sends some patients with a WRONG birth date or with the year-1900 placeholder although the chart holds the right one. The Medicaid check below was asked with the
# FEED's name and birth date. How Florida Medicaid answers a check whose birth date is not the one it holds has not been captured (the repository's notes record the
# refusal AAA 71 for such a check from Centene - docs/captured_calls.md - and from Medicare - docs/SHARED_LESSONS.md); an answer that is an error counts as 'could not
# answer' here - nothing added, bought again next run. The chart is read here anyway (ins_update._plans, step 2) and its answer carries the patient's own name and birth
# date: lookup_who takes them from it - no extra call - and falls back to the feed's only when the chart's birth date is not a real one. What it says goes into the printed
# line and the register, so its words carry no name and no date.
# _real_dob and _slip are the owner's rule as scripts/helpers/feed_identity.py states it (real_dob, slip); they are private copies here - the same text stands in
# claimocity_import.py and claimocity_verify.py, and tools/selftest/test_pos_rule.py checks the three read the same - until the helpers point at that one module.
# _dob8 and lookup_who stand, the same text, in claimocity_verify.py (its paid look-up).
def _real_dob(d8, today8):
    """True when d8 is a REAL birth date (the owner's rule): 8 digits, a real calendar date, the year 1901 or later, not after today8 and not more than 120 years before
    it. Anything else - empty, the year-1900 placeholder, zeros, a day that does not exist - is NO BIRTH DATE. (Mirrors real_dob in feed_identity.py.)"""
    d8 = str(d8 if d8 is not None else ""); today8 = str(today8 if today8 is not None else "")
    if not re.fullmatch(r"[0-9]{8}", d8) or not re.fullmatch(r"[0-9]{8}", today8) or d8[:4] < "1901": return False
    try: __import__("datetime").date(int(d8[:4]), int(d8[4:6]), int(d8[6:8]))
    except ValueError: return False
    return "%04d%s" % (int(today8[:4]) - 120, today8[4:]) <= d8 <= today8
def _slip(a8, b8):
    """How two REAL birth dates differ (the owner's rule) - the kind of slip, the first that fits: "one digit" (one digit differs), "two digits swapped" (two neighbouring
    digits swapped), "month and day swapped" (MMDD read as DDMM), "one day apart"; anything else is "far". "" when the two are the same date. (Mirrors slip in
    feed_identity.py.)"""
    a8, b8 = str(a8), str(b8)
    if a8 == b8: return ""
    if len(a8) != 8 or len(b8) != 8: return "far"
    diff = [i for i in range(8) if a8[i] != b8[i]]
    if len(diff) == 1: return "one digit"
    if len(diff) == 2 and diff[1] == diff[0] + 1 and a8[diff[0]] == b8[diff[1]] and a8[diff[1]] == b8[diff[0]]: return "two digits swapped"
    if a8[:4] == b8[:4] and a8[4:6] == b8[6:8] and a8[6:8] == b8[4:6]: return "month and day swapped"
    try:
        day = __import__("datetime").date
        if abs((day(int(a8[:4]), int(a8[4:6]), int(a8[6:8])) - day(int(b8[:4]), int(b8[4:6]), int(b8[6:8]))).days) == 1: return "one day apart"
    except ValueError: pass
    return "far"
def _dob8(s):
    """A birth date as AdvancedMD writes it (MM/DD/YYYY, with or without leading zeros or a time behind it), as the feed writes it (YYYYMMDD, or longer with a time) or
    with dashes (YYYY-MM-DD) -> the 8 digits YYYYMMDD; "" for anything that cannot be read that way. It reads the shape only: whether the date is a REAL one is _real_dob's."""
    s = str(s if s is not None else "").strip(); m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m: return "%s%02d%02d" % (m.group(3), int(m.group(1)), int(m.group(2)))
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m: return "".join(m.groups())
    x = re.sub(r"\D", "", s)
    return x[:8] if len(x) >= 8 else ""
def lookup_who(pa, first, last, dob8, today8=None, what="look-up"):
    """Whom a paid look-up of a chart is asked about: (first name, last name, birth date YYYYMMDD, words). pa = the chart's own patient attributes as AdvancedMD's
    getdemographic answer gives them (name "LAST,FIRST ...", dob MM/DD/YYYY) - the answer the caller already holds, so this costs no call. first, last, dob8 = what the
    feed carries. When the chart's birth date is a REAL one (_real_dob) and its name can be read, the answer is the CHART's first name (its first word), last name and
    birth date; else it is the feed's three values exactly as they were passed - never a mix of the two. words = which one was asked and how the other differs, in fixed
    words that carry no name and no date (a slip is named by its kind); they begin with `what` ("look-up", "Medicaid") and go into registers and reports.
    It never raises: whatever cannot be compared leaves the feed's values, and the words say so."""
    try:
        today8 = today8 or __import__("datetime").date.today().strftime("%Y%m%d"); a = pa if isinstance(pa, dict) else {}
        cl, _, cf = __import__("html").unescape(str(a.get("name") or "")).partition(","); cl = cl.strip(); cf = cf.strip().split(" ")[0]
        c8 = _dob8(a.get("dob")); f8 = _dob8(dob8); fr = _real_dob(f8, today8)
        if _real_dob(c8, today8):
            if not (cl and cf): return first, last, dob8, "%s asked with Claimocity's name and birth date; the chart's name could not be read" % what
            return cf, cl, c8, "%s asked with the chart's birth date; %s" % (what, ("Claimocity's is the same" if f8 == c8 else "Claimocity's differs: " + _slip(f8, c8)) if fr else "no birth date from Claimocity")
        return first, last, dob8, ("%s asked with Claimocity's birth date; the chart has no birth date of its own" if fr else "%s asked with what Claimocity sent; no birth date on either side") % what
    except Exception:
        return first, last, dob8, "%s asked with what Claimocity sent; the chart's name and birth date could not be compared" % what
recs = adt_ingest.read([DIR]); feed = collections.defaultdict(dict); who = {}
for r in recs:
    fid = r["patient"].get("id"); who[fid] = r["patient"]
    for b in r["insurance"]:
        if not b["skip"] and b["member"]: feed[fid][(b["name"], b["member"])] = b
amd.login_cached(); done = 0; tally = collections.Counter()
print("feed files in %s: %d messages, %d patients with a usable insurance block%s" % (DIR, len(recs), len(feed), "" if LIVE else "  (DRY RUN - nothing is written)"))
for fid, blocks in feed.items():
    pid = re.sub(r"\D", "", PMAP.get(fid, ""))
    if not pid: tally["no chart yet"] += 1; continue
    r, plans, order = ins_update._plans(pid); plans = list(plans.values())
    _pt = re.search(r'<patient [^>]*>', r or ""); cpat = dict(re.findall(r'(\w+)="([^"]*)"', _pt.group(0))) if _pt else {}      # 11/25/2026: the chart's own patient attributes (its name, its birth date) from the answer just read - no extra call (lookup_who)
    have = {p.get("carrier") for p in plans}; live_codes = {CAR2CODE.get(p.get("carrier")) for p in plans if not p.get("enddate")}
    live_medicaid = bool((live_codes & fpm.MEDICAID_FAMILY) or any(CAR2CODE.get(p.get("carrier")) == "HUM01" and len(norm(p.get("subscribernum"))) == 10 and norm(p.get("subscribernum")).isdigit() for p in plans if not p.get("enddate")))
    asked_medicaid = False
    for (name, member), b in blocks.items():
        code = fpm.code(name); kind = fpm.kind(name, code)
        if not code or code not in CODE2CAR: tally["name not in the table"] += 1; continue
        if kind == "ltc": tally["long-term-care-only plan (not the physician's payer)"] += 1; continue
        if CODE2CAR[code] in have: tally["already on the chart"] += 1; continue
        key = "%s|%s" % (pid, code)
        if key in REG and REG[key].get("outcome", "").startswith(("added", "not active", "listed")): tally["settled by an earlier run"] += 1; continue
        if kind == "primary":
            REG[key] = {"outcome": "listed - the feed names another primary plan (%s); the dated check decides" % code, "stamp": STAMP}; tally["another PRIMARY named by the feed (listed for the cascade)"] += 1
            print("  pat%s: feed names %s as a plan the chart does not hold - primary plans are decided by the dated eligibility check, not entered here" % (pid, code)); continue
        if kind == "medicaid":
            if live_medicaid: REG[key] = {"outcome": "listed - the chart already has an open Medicaid-family plan; feed says %s" % code, "stamp": STAMP}; tally["chart already has a Medicaid plan (listed)"] += 1; continue
            if asked_medicaid: continue
            if not re.fullmatch(r"\d{10}", norm(member)): tally["Medicaid row without a 10-digit Medicaid number"] += 1; continue
            if done >= MAX: tally["over this run's limit (next run)"] += 1; continue
            p = who.get(fid, {}); asked_medicaid = True; done += 1
            # 11/25/2026 (William, WHOM MEDICAID IS ASKED ABOUT above): the chart's own name and birth date when the chart's birth date is a real one, else the feed's as before
            _mf, _ml, _md, _how = lookup_who(cpat, p.get("first", "").split()[0] if p.get("first") else "", p.get("last", ""), re.sub(r"\D", "", p.get("dob", "")), what="Medicaid")
            status, scode, text = medicaid_answer(_mf, _ml, _md, norm(member), pid)
            if not _how.endswith("is the same"): text = "%s - %s" % (text, _how)      # which one was asked, in fixed words: into the printed line and the register entry
            if status == "unknown": print("  pat%s: %s - nothing added, asked again next run" % (pid, text)); tally["Medicaid could not answer (next run)"] += 1; continue
            if status == "inactive": REG[key] = {"outcome": "not active - " + text, "stamp": STAMP}; print("  pat%s: %s - nothing added" % (pid, text)); tally["Medicaid not active (nothing added)"] += 1; continue
            use = scode if scode in CODE2CAR else code
            if CODE2CAR[use] in have: REG[key] = {"outcome": "listed - the state names %s, already on the chart" % use, "stamp": STAMP}; tally["already on the chart"] += 1; continue
            fin = "MD"
        else:
            use = code; text = "feed block '%s'" % name[:30]; fin = "CC"
            if done >= MAX: tally["over this run's limit (next run)"] += 1; continue
            done += 1
        if LIVE: _r, _pl, order = ins_update._plans(pid); plans = list(_pl.values())      # 11/19/2026: read the order again - a second plan added on the same chart must not drop the first from it
        seqs = [s for s in (order or "").replace(" ", "").split(",") if s]
        if not LIVE:
            print("  pat%s: DRY would add %s (%s) and %s" % (pid, use, text, "append it to the order %s" % order if 1 <= len(seqs) <= 2 else "leave the order %r" % order)); tally["would add %s" % ("a Medicaid plan" if kind == "medicaid" else "a secondary plan")] += 1; continue
        insid, seq = add_ins.add(pid, CODE2CAR[use], norm(member) if kind == "medicaid" else member, "01/01/%d" % datetime.date.today().year, "1", fin)
        if not insid: print("  pat%s: add %s FAILED %s" % (pid, use, str(seq)[:100])); tally["add failed"] += 1; continue
        time.sleep(0.4); msg = "added %s as %s seq %s (%s)" % (use, insid, seq, text)
        if kind != "medicaid":
            try: s = elig_amd.run_plan(pid, insid.replace("ins", ""), True); st = str(s.get("status") or "")
            except Exception as e: st = "check failed %s" % type(e).__name__
            if st.upper().startswith(("INACTIVE", "REJECTED")):
                ins_update.update(pid, insid, enddate="01/01/%d" % datetime.date.today().year)
                REG[key] = {"outcome": "not active - AdvancedMD's check on the feed's %s answered %s; plan ended again" % (use, st[:40]), "ins": insid, "stamp": STAMP}
                print("  pat%s: %s - but AdvancedMD's check answered %s: ended again" % (pid, msg, st[:40])); tally["secondary not active (ended again)"] += 1; continue
            msg += "; AdvancedMD 271 %s" % st[:30]
        if 1 <= len(seqs) <= 3 and seq not in seqs:
            first = [p["id"] for p in plans if p.get("sequence") == seqs[0]]
            medicaid_seqs = [x for x in seqs[1:] if any(p.get("sequence") == x and CAR2CODE.get(p.get("carrier")) in fpm.MEDICAID_FAMILY for p in plans)]
            new = [x for x in seqs if x not in medicaid_seqs] + ([str(seq)] + medicaid_seqs if kind != "medicaid" else medicaid_seqs + [str(seq)])      # Medicare / Advantage, then Medigap, Medicaid last
            if first:
                ok, m2 = ins_update.update(pid, first[0], sequence=",".join(new)); msg += "; order %s -> %s (%s)" % (order, ",".join(new), "ok" if ok else "NOT set: " + m2[:60])
        REG[key] = {"outcome": msg, "ins": insid, "stamp": STAMP}; print("  pat%s: %s" % (pid, msg)); tally["added %s" % ("a Medicaid plan" if kind == "medicaid" else "a secondary plan")] += 1
        json.dump(REG, open(REGF, "w"), indent=1); time.sleep(0.3)
    time.sleep(0.1)
if LIVE: json.dump(REG, open(REGF, "w"), indent=1)
print("RESULT feed insurance intake %s: %s" % (STAMP, "; ".join("%s %d" % (k, v) for k, v in sorted(tally.items()))))
