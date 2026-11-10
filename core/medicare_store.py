# PLAIN ENGLISH (Medicare answer store - look-ups part A, 11/10/2026)
# Decides: nothing. Remembers the Medicare answers the vendor client (stedi.medicare) bought, ONE per chart and day (and month of service
#   asked about), so that the deceased-patient guard, the nightly pre-claim check and any other helper that asks Medicare about the same
#   chart share one answer instead of each buying its own. A call that failed is kept only as 'asked and failed today': no other helper
#   buys the same failing chart again that day, and the next day it is asked again.
# Rules it uses: every reader brings its own age limit (the guard 30 days, the pre-claim check the calendar month of the visit, anything
#   else the same day); an answer is reused only when it was asked about a date of service in the same calendar month as the one asked
#   now, or a later one. ONE file: $MEDICARE_STORE, default patient_db/medicare_answers.json beside this helper (the workspace root;
#   patient_db/ is never in git and travels only where patient_db/ already travels). A missing, empty or unreadable file is an empty
#   store (the caller simply asks); a write goes to a temporary file that is then renamed into place, and a write that fails never stops
#   the caller.
# Keeps per answer: the day asked, the date of service asked about, how it was got, who asked, active or not, Part A and Part B dates,
#   an Advantage or other plan named in the answer (name, payer id, dates), hospice, a date of death, the error codes, and whether a
#   look-up showed the chart's number to differ from Medicare's. NEVER keeps the Medicare number, a name, a birth date, an address or the
#   raw answer; anything shaped like a Medicare number is blanked before a write. A list keeps at most 20 items; the plan lines (U, R)
#   are put first, so the cut falls on the other lines before an Advantage plan. death(pid) gives the deceased-patient guard the date of
#   death any kept answer shows, whatever its age or month of service (a death is never undone - 11/10/2026 re-check fix).
# Never touches: AdvancedMD, the vendor, the guard's own cache (deceased_cache.json).
import os, re, json, datetime, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
KEEP_DAYS = 92                  # answers older than this are dropped (no reader looks back further than about a month and a half)
KEEP_PER_CHART = 6              # newest answers kept per chart
ANSWER_KEYS = ("active", "partA", "partB", "other", "hospice", "death", "errors", "number_differs")
PLAN_KEYS = ("code", "type", "typeName", "plan", "dates", "entity")
_SHAPE = re.compile(r"(?<![A-Za-z0-9])[1-9][A-Za-z][A-Za-z0-9][0-9][A-Za-z][A-Za-z0-9][0-9][A-Za-z]{2}[0-9]{2}(?![A-Za-z0-9])")
def path():
    return os.environ.get("MEDICARE_STORE") or os.path.join(HERE, "patient_db", "medicare_answers.json")
def _today():
    return datetime.date.today()
def _key(pid):
    return re.sub(r"\D", "", str(pid or ""))
def _d8(x):
    s = re.sub(r"\D", "", str(x or ""))[:8]
    return s if len(s) == 8 else None
def _clean(v):
    """Strings are cut short and anything shaped like a Medicare number is blanked - the file never holds one."""
    if isinstance(v, str): return _SHAPE.sub("[number]", v)[:200]
    if isinstance(v, dict): return {str(k)[:40]: _clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)): return [_clean(x) for x in v][:20]
    return v if v is None or isinstance(v, (bool, int, float)) else _clean(str(v))
def _load():
    try:
        with open(path()) as fh: d = json.load(fh)
        if isinstance(d, dict) and isinstance(d.get("charts"), dict): return d
    except Exception: pass
    return {"charts": {}}
def _write(data):
    p = os.path.abspath(path()); d = os.path.dirname(p); os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".medicare_answers.", suffix=".tmp", dir=d)
    try:
        with os.fdopen(fd, "w") as fh: json.dump(data, fh, indent=1)
        os.replace(tmp, p)
    finally:
        if os.path.exists(tmp): os.remove(tmp)
def get(pid, max_age_days, dos=None):
    """-> the newest stored answer this reader may use (a dict), or {'failed': True, 'day', 'who', 'errors', 'reason'} when the chart was
    asked today and the call failed, or None. max_age_days is the reader's own age limit (0 = asked today); dos the date of service
    asked about now (YYYYMMDD or YYYY-MM-DD; none = today)."""
    key = _key(pid)
    if not key or max_age_days is None: return None
    rec = _load()["charts"].get(key)
    if not isinstance(rec, dict): return None
    today = _today(); want = _d8(dos) or today.strftime("%Y%m%d"); best = None
    for a in rec.get("answers") or []:
        try: age = (today - datetime.date.fromisoformat(a["asked"])).days
        except Exception: continue
        if age < 0 or age > max_age_days: continue
        have = _d8(a.get("dos")) or a["asked"].replace("-", "")       # an answer asked with no date of service is about the day it was asked
        if not (have[:6] == want[:6] or have > want): continue          # same calendar month of service, or a later date of service
        if best is None or a["asked"] > best["asked"]: best = a
    if best: return dict(best)
    f = rec.get("failed")
    if isinstance(f, dict) and f.get("day") == today.isoformat(): return dict(f, failed=True)
    return None
def put(pid, summary, how, who, dos):
    """Remember one answer (how = 'plain', 'lookup' or 'lookup after plain'), or - for how = 'failed' - that the chart was asked today and
    the call failed. -> True when written. Never raises: a store that cannot be written only means the next helper asks again."""
    try:
        key = _key(pid)
        if not key: return False
        today = _today(); day = today.isoformat(); d8 = _d8(dos); s = summary if isinstance(summary, dict) else {}
        data = _load(); charts = data["charts"]; rec = charts.get(key) if isinstance(charts.get(key), dict) else {}
        if how == "failed":
            rec["failed"] = _clean({"day": day, "who": str(who or "")[:60], "dos": d8, "errors": list(s.get("errors") or [])[:6], "reason": str(s.get("reason") or "failed")[:80]})
        else:
            entry = {"asked": day, "dos": d8, "how": str(how), "who": str(who or "")[:60]}
            for k in ANSWER_KEYS: entry[k] = s.get(k)
            entry["other"] = [{k: o.get(k) for k in PLAN_KEYS} for o in (s.get("other") or []) if isinstance(o, dict)]
            # 11/10/2026 (review fix): the plan lines (codes U and R: an Advantage or other plan) first, then the facility lines (X: hospice,
            # a skilled nursing stay), so the 20-line cut of _clean drops the other lines before an Advantage plan the pre-claim words read
            entry["other"].sort(key=lambda o: 0 if o.get("code") in ("U", "R") else 1 if o.get("code") == "X" else 2)
            month = (d8 or day.replace("-", ""))[:6]
            keep = [a for a in rec.get("answers") or [] if isinstance(a, dict) and not (a.get("asked") == day and ((_d8(a.get("dos")) or day.replace("-", ""))[:6] == month))]
            rec["answers"] = keep + [_clean(entry)]
            if isinstance(rec.get("failed"), dict) and rec["failed"].get("day") == day: rec.pop("failed")
        charts[key] = rec
        for k in list(charts):                                          # drop what no reader can use any more
            r = charts[k] if isinstance(charts[k], dict) else {}
            ans = [a for a in r.get("answers") or [] if isinstance(a, dict) and _age(a.get("asked"), today) <= KEEP_DAYS]
            r["answers"] = sorted(ans, key=lambda a: str(a.get("asked")))[-KEEP_PER_CHART:]
            if isinstance(r.get("failed"), dict) and r["failed"].get("day") != day: r.pop("failed")
            if r["answers"] or r.get("failed"): charts[k] = r
            else: charts.pop(k)
        data["about"] = "Medicare answers per chart id (medicare_store.py): no Medicare number, no name, no birth date"
        _write(data); return True
    except Exception:
        return False
def _age(asked, today):
    try: return (today - datetime.date.fromisoformat(str(asked))).days
    except Exception: return 10 ** 6
def death(pid):
    """11/10/2026 (re-check fix): the earliest date of death (YYYYMMDD) any kept answer for this chart shows, else None - whatever the
    answer's age or month of service: a death is never undone. The deceased-patient guard reads it when its own call fails. Never raises."""
    try:
        rec = _load()["charts"].get(_key(pid))
        days = sorted(d for d in (_d8(a.get("death")) for a in (rec or {}).get("answers") or [] if isinstance(a, dict)) if d)
        return days[0] if days else None
    except Exception:
        return None
