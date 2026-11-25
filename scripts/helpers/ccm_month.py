#!/usr/bin/env python3
# PLAIN ENGLISH (CCM documentation hub, the monthly add-on - William 11/24/2026: "make ccm notes for all the new ccm charges that will be
#   coming through soon and run that automatically to make those notes for signiature when they come through and make it do the notes any
#   time ccm charges come through monthly in batches to give me an email alert we have ccm notes to sign").
# Decides: nothing about a charge. It finds the CCM charge lines that reached AdvancedMD through the Claimocity feed after the AdvancedMD
#   history was pulled (11/10/2026) - ehpa.feed_charges keeps AdvancedMD's charge numbers in the same order as the codes - and reads each of
#   those visits back from AdvancedMD so a note is built from what AdvancedMD itself holds, not from the feed:
#     getchargedetaildataicd10 (one call per CCM charge - it answers for ONE charge, resave.visit_charges learned that 9/3/2026; READ ONLY,
#     already in docs/captured_calls.md) -> the charge's code, date of service, units, void flag and ICD-10 codes in AdvancedMD's order, and
#     its visit's provider profile and facility - parsed the way optimization/amd_history/amd_pull2.py detail_one() parses it;
#     getdemographic (ccm_patients.parse: name, birth date and sex only) for a chart the hub has no name for yet.
#   Why read AdvancedMD at all: four October feed lines were voided in AdvancedMD after the feed entered them (duplicates), and the feed's
#   diagnosis list is sorted its own way - a note has to show the charge as billed.
# Writes (workspace only - never the repository): <out>/neon/lines/<chart>_<visit>.json (one per visit: its CCM lines, void ones marked) and
#   <out>/neon/patients/<chart>.json; `python3 tools/db/neon_db.py load-docs --src <out>/neon --source ccm` loads them, and
#   scripts/helpers/ccm_build.py then builds the month's notes from amd.charges plus these lines.
# Re-reads: a visit whose month is not signed yet is read again once its last read is older than --recheck-hours (default 20), so a
#   duplicate deleted or a charge re-dated in AdvancedMD before he signs reaches the note. A signed month is final and never re-read.
# Rules: never writes to AdvancedMD; one amd.login_cached() and never a second login (a dead session stops the run, exit 3); the scheduled
#   billing routines' quiet windows (ccm_patients.QUIET) are never used (exit 5, run again after); paced; five failed reads in a row stop it
#   (exit 4); a STOP file in <out> ends it after the visit in hand.
# Usage:
#   python3 scripts/helpers/ccm_month.py plan                                   what is new or due a re-read (no login, no call)
#   python3 scripts/helpers/ccm_month.py read --out <dir> [--limit N] [--recheck-hours H]   the reads
# Exit: 0 done (nothing new is 0 too), 2 bad input, 3 session, 4 failures, 5 quiet window or STOP.
# Inside a billing routine (11/25/2026, William: "they only come through once a month and should be in the regular billing projects"): the
#   routine that owns the AdvancedMD window runs `read --in-routine` (no quiet-window stop - it IS that window's routine, behind its own
#   cross-container guard, sharing its cached login), and `plan` ends with one line the runbook reads:
#   "ccm_month plan: to_read=<visits> names=<charts without a name> unsigned=<unsigned CCM notes in Neon>" - all three 0 = nothing to do.
# Self-test: python3 tools/selftest/test_ccm_month.py
import os, sys, re, json, time, datetime, collections
import xml.etree.ElementTree as ET
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ccm_notes as N
import ccm_build as B
import ccm_patients as P
REPO = os.path.dirname(os.path.dirname(HERE))
CODES = N.CCM_CODES
PACE = 0.5
MAX_FAILS_IN_A_ROW = 5
ARR = "case when jsonb_typeof(fc.charges) = 'array' then fc.charges else '[]'::jsonb end"
# every CCM line the feed entered in AdvancedMD: chart, visit and charge numbers (digits only), code (same position as the charge), feed date,
# carrier and facility as the feed saw them
FEED_SQL = ("select fc.chart_id, regexp_replace(coalesce(fc.visit_id, ''), '[^0-9]', '', 'g'), regexp_replace(c.ch, '[^0-9]', '', 'g'), "
            "fc.cpts[c.i::int], fc.dos::date::text, coalesce(fc.lead_carrier_name, ''), coalesce(fc.facility, ''), coalesce(fc.clinician, '') "
            "from ehpa.feed_charges fc cross join lateral jsonb_array_elements_text(" + ARR + ") with ordinality c(ch, i) "
            "where fc.cpts && array[%s]::text[] and fc.chart_id like 'pat%%'")
HIST_SQL = "select distinct charge_id::text from amd.charges where cpt in (%s)"      # in the AdvancedMD history already (void or not)
LINES_SQL = "select doc_id, body->>'read_at', body->>'month' from raw.documents where source = 'ccm' and collection = 'lines'"
SIGNED_SQL = "select doc_id from raw.documents where source = 'ccm' and collection = 'signed'"
PATIENTS_SQL = ("select doc_id from raw.documents where source = 'ccm' and collection = 'patients' "
                "and coalesce(body->>'name', '') <> '' and coalesce(body->>'dob', '') <> ''")

def _codes(): return ", ".join("'%s'" % c for c in CODES)
def _now():
    s = os.environ.get("CCM_NOW")      # the self-test sets the clock
    return datetime.datetime.fromisoformat(s.replace("Z", "+00:00")) if s else datetime.datetime.now(datetime.timezone.utc)
def _iso(t): return t.strftime("%Y-%m-%dT%H:%M:%SZ")
def _day(s):
    """MM/DD/YYYY or YYYY-MM-DD -> YYYY-MM-DD ("" when unreadable)"""
    s = (s or "").strip()[:10]
    for f in ("%m/%d/%Y", "%Y-%m-%d"):
        try: return datetime.datetime.strptime(s, f).date().isoformat()
        except ValueError: pass
    return ""

UNSIGNED_SQL = ("select count(*) from raw.documents m where m.source = 'ccm' and m.collection = 'months' and m.doc_id not in "
                "(select doc_id from raw.documents where source = 'ccm' and collection = 'signed')")
def unsigned(select):
    try: return int((select(UNSIGNED_SQL) or [[0]])[0][0] or 0)
    except Exception: return -1      # unknown: the runbook then lists the page's signings as if some were waiting
def plan(select, recheck_hours=20.0):
    """(visits to read, charts with no name): a visit is read when one of its feed CCM charges is not in the AdvancedMD history and it has
    no lines document yet, or its lines document is older than recheck_hours and its month is not signed. A visit: {"chart", "visit",
    "charges" (its CCM charge numbers as the feed entered them), "month" (the feed's), "carrier", "facility", "clinician", "why"}."""
    hist = {r[0] for r in select(HIST_SQL % _codes())}
    read = {r[0]: (r[1] or "", r[2] or "") for r in select(LINES_SQL)}
    signed = {r[0] for r in select(SIGNED_SQL)}
    named = {r[0] for r in select(PATIENTS_SQL)}
    now = _now(); visits = collections.OrderedDict()
    for chart, visit, charge, code, dos, carrier, facility, clinician in select(FEED_SQL % _codes()):
        if not (chart and visit and charge) or charge in hist: continue
        key = "%s_%s" % (chart, visit)
        if key in visits:
            if charge not in visits[key]["charges"]: visits[key]["charges"].append(charge)
            continue
        month = (dos or "")[:7]
        if key in read:
            at, m = read[key]
            if "%s_%s" % (chart, m or month) in signed: continue      # a signed month is final
            try: age = (now - datetime.datetime.fromisoformat(at.replace("Z", "+00:00"))).total_seconds() / 3600.0
            except ValueError: age = 1e9
            if age < recheck_hours: continue
            why = "re-read (unsigned, last read %.0f h ago)" % age
        else: why = "new"
        visits[key] = {"chart": chart, "visit": visit, "charges": [charge], "month": month, "carrier": carrier, "facility": facility, "clinician": clinician, "why": why}
    charts = sorted({v["chart"] for v in visits.values()} - named)
    return list(visits.values()), charts

def parse_charge(xml, charge):
    """one CCM line from a getchargedetaildataicd10 answer for that charge: {"charge", "visit", "code", "dos", "units", "void", "dx",
    "provider_code", "facility"} - nothing else of the answer is kept (no payment, balance, note or patient detail)"""
    root = ET.fromstring(xml)
    look = lambda path, attr="code": {x.get("id"): (x.get(attr) or x.get("code") or "") for x in root.findall(path) if x.get("id")}
    proc = look(".//proccodelist/proccode"); dx = look(".//diagcodelist/diagcode"); facs = look(".//facilitylist/facility", "name"); profs = look(".//profilelist/profile")
    v = root.find(".//visit"); c = next((e for e in root.iter("charge") if re.sub(r"\D", "", e.get("id") or "") == str(charge)), None)
    if v is None or c is None: raise ValueError("no charge in the answer: " + " ".join((e.text or "")[:80] for e in root.iter("Error"))[:160])
    u = c.get("units") or "1"
    return {"charge": str(charge), "visit": re.sub(r"\D", "", v.get("id") or ""), "code": proc.get(c.get("proccode"), c.get("proccode") or ""),
            "dos": _day(c.get("begindate")), "units": str(int(float(u))) if re.match(r"^\d+(\.\d+)?$", u) else "1",
            "void": (c.get("void") or "0").strip().lower() in ("1", "true", "t", "y", "yes"),
            "dx": [dx.get(x, x) for x in (c.get("diagcodes") or "").split()], "provider_code": profs.get(v.get("profile"), "") or "",
            "facility": facs.get(v.get("facility"), "") or ""}

def lines_doc(v, lines, at):
    live = [l for l in lines if not l["void"]]
    month = min((l["dos"][:7] for l in live if l["dos"]), default="") or v["month"]
    return {"chart": v["chart"], "visit": v["visit"], "month": month, "read_at": at, "source": "AdvancedMD getchargedetaildataicd10",
            "feed": {"carrier": v.get("carrier", ""), "facility": v.get("facility", ""), "clinician": v.get("clinician", "")},
            "charges": lines, "_written": at}

def _write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: json.dump(obj, f, ensure_ascii=False, sort_keys=True, indent=1)
    os.replace(tmp, path)

def main(argv=None, select=None, amd=None, sleep=time.sleep):
    a = list(sys.argv[1:] if argv is None else argv); select = select or B.neon_select
    cmd = a[0] if a else ""
    def opt(k, d=None): return a[a.index(k) + 1] if k in a and a.index(k) + 1 < len(a) else d
    try: rh = float(opt("--recheck-hours", "20")); limit = int(opt("--limit", "0"))
    except ValueError: print("ccm_month: --recheck-hours and --limit take numbers"); return 2
    if cmd not in ("plan", "read"):
        print("usage: ccm_month.py plan | read --out <dir> [--limit N] [--recheck-hours H] [--in-routine]"); return 2
    in_routine = "--in-routine" in a
    visits, charts = plan(select, rh)
    why = collections.Counter(v["why"].split(" (")[0] for v in visits)
    months = sorted({v["month"] for v in visits})
    q = None if in_routine else P.quiet_window(_now())
    print("ccm_month: %d visit(s) to read (%d new, %d re-read) in %s; %d chart(s) without a name%s" % (len(visits), why["new"], why["re-read"],
          ", ".join(months) or "-", len(charts), (" - a scheduled billing routine uses AdvancedMD until %s UTC" % P.hhmm(q[1])) if q else ""))
    if cmd == "plan":
        print("ccm_month plan: to_read=%d names=%d unsigned=%d" % (len(visits), len(charts), unsigned(select))); return 0
    out = opt("--out")
    if not out: print("ccm_month: read needs --out <dir>"); return 2
    out = os.path.abspath(out)
    if out == REPO or out.startswith(REPO + os.sep): print("ccm_month: %s is inside the repository - patient data never goes there" % out); return 2
    if not visits and not charts: return 0
    if q: print("ccm_month: not now - run it again after %s UTC" % P.hhmm(q[1])); return 5
    if amd is None:
        import amd as _amd      # only for a live run: the self-test passes its own stand-in
        amd = _amd
    try: amd.login_cached()
    except Exception as e:
        print("ccm_month: the AdvancedMD session could not be opened (%s) - stopping, NOT logging in again" % str(e)[:160]); return 3
    n = fails = void = 0; lines_n = 0; errors = []
    todo = visits[:limit or None]
    for v in todo:
        if os.path.exists(os.path.join(out, "STOP")): print("ccm_month: STOP file - stopped after %d visits" % n); return 5
        q = None if in_routine else P.quiet_window(_now())
        if q: print("ccm_month: a scheduled billing routine starts now - stopped after %d visits; run again after %s UTC" % (n, P.hhmm(q[1]))); return 5
        at = _iso(_now())
        try:
            lines = []
            for cid in v["charges"]:
                l = parse_charge(amd.post(amd.msg("getchargedetaildataicd10", "demographics", {"chargeid": cid, "nocookie": "1"}), timeout=60), cid)
                if l["visit"] and l["visit"] != v["visit"]: raise ValueError("charge %s belongs to visit %s in AdvancedMD, not %s" % (cid, l["visit"], v["visit"]))
                if l["code"] not in CODES: raise ValueError("charge %s is %s in AdvancedMD, not a CCM code" % (cid, l["code"] or "no code"))
                lines.append(l); sleep(PACE)
            _write(os.path.join(out, "neon", "lines", "%s_%s.json" % (v["chart"], v["visit"])), lines_doc(v, lines, at))
            n += 1; fails = 0; lines_n += len(lines); void += sum(1 for l in lines if l["void"])
        except Exception as e:
            fails += 1; errors.append("%s_%s: %s: %s" % (v["chart"], v["visit"], type(e).__name__, str(e)[:120]))
            sleep(PACE)
            if fails >= MAX_FAILS_IN_A_ROW: print("ccm_month: %d reads in a row failed - stopped (the last: %s)" % (fails, errors[-1])); return 4
    pn = 0
    for c in charts:
        q = None if in_routine else P.quiet_window(_now())
        if q: print("ccm_month: quiet window - %d patient read(s) left for the next run" % (len(charts) - pn)); break
        at = _iso(_now())
        try:
            p = P.parse(amd.post(amd.msg("getdemographic", "demographics", {"patientid": c, "nocookie": "1"}), timeout=60))
            if p.get("name") and p.get("dob"):
                _write(os.path.join(out, "neon", "patients", c + ".json"), dict(p, chart=c, read_at=at, _written=at)); pn += 1
            else: errors.append("%s: no name or birth date in AdvancedMD" % c)
        except Exception as e: errors.append("%s: %s: %s" % (c, type(e).__name__, str(e)[:120]))
        sleep(PACE)
    if errors: _write(os.path.join(out, "ccm_month_errors.json"), {"errors": errors, "_written": _iso(_now())})
    print("ccm_month: read %d of %d visit(s) (%d CCM line(s), %d void in AdvancedMD) and %d patient name(s); %d error(s)%s -> %s" % (
        n, len(todo), lines_n, void, pn, len(errors), (" (" + "; ".join(errors[:3]) + ")") if errors else "", os.path.join(out, "neon")))
    return 0

if __name__ == "__main__":
    sys.exit(main())
