# PLAIN ENGLISH (Deceased-patient guard - William 9/22/2026: "on any straight medicare claims we are never submitting bills on a
#          medicare deceased person"; check the MBI / Medicare record for a date of death before any claim goes out).
# Decides: whether a claim may be submitted. BLOCK when the date of service is AFTER the patient's date of death (any payer).
# Sources, in order: (1) the cache practices/ehpa/registers/deceased_cache.json (pid -> dod / checked date / source) - the GitHub copy is
#   PHI-scrubbed ('[DOB]' = unknown, re-looked-up; 10/14/2026), the real dates live in the workspace and Drive 'workspace mirror',
#          (2) AMD getdemographic 'deceased', (3) a fresh Medicare answer whose 271 carries the date of death (DTP*442 / dateOfDeath).
#          A fresh answer is asked when the claim goes to straight Medicare (FLO02 / car6085) or is CCM and the cache is missing or
#          older than 30 days. A lookup that fails does NOT block (logged 'unverified' for the daily report) - only a positive date of
#          death blocks.
#   11/10/2026 (look-ups part A): (3) is asked through the Stedi client, stedi.medicare(): a PLAIN Medicare check with the member number
#          of the chart's Medicare Part B plan (car6085: an open one first, else the one that ended last), and the look-up by name + DOB
#          + FL when the chart has no usable number, when Medicare does not know it, or when Medicare refuses the plain check for another
#          reason (41, 61, an answer with no Part A or Part B; after a refusal of OUR provider number the rest of the run skips the plain
#          check). The answer is shared with the pre-claim check through medicare_store.py: an answer any helper got in the last 30 days
#          is used (and its own date counts for the 30 days) - but only when it was asked on or after the claim's date of service (or
#          today, for a date still to come): an answer asked BEFORE that date cannot know of a death since, so Medicare is asked again
#          (one plain check; the same holds for the cache's own entry) unless that answer already shows a date of death, which is used
#          as it is with no call (a death is never undone) - and a chart whose call failed today is not bought again today
#          (it stays 'unverified', exactly as before). A date of death a Medicare answer carried during this very check (a plain answer
#          with error 61 and the date, then a look-up that failed) blocks this claim at once; so does a date of death any answer kept in
#          the store shows, whatever its age or month of service, when the guard's own call fails (11/10/2026 re-check fix: the store
#          and this cache travel apart - the cache may be lost, unreadable or scrubbed to '[DOB]'). That fallback takes the EARLIEST
#          date of death any kept answer shows, even when a newer kept answer shows none - it errs toward blocking, as this cache itself
#          keeps a death for good (once a death is in it, every claim of that chart dated after the death is blocked with no new call;
#          second re-check, 11/10/2026: kept as it is). A care-management
#          chart with no Medicare plan keeps the look-up by name, counted as 'guard, no Medicare plan on the chart'. The cache is
#          written one chart at a time into the ONE file it is configured with (DECEASED_CACHE, else the default below), read again just
#          before the write and replaced in one step, so nothing another helper learned meanwhile is lost. No own request, no key file.
#          Only a real Medicare answer is kept as 'no death on record': one that shows Part A / Part B (or a look-up's 72 alone, 'not a
#          Medicare beneficiary', as before); an empty reply with no error, a plain check's 'not found' or a failed call never is.
# CCM in the month of death: the DOS must be on/before the date of death; a month-end CCM date after the death is blocked.
import os, re, json, time, datetime, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
CACHE = os.environ.get("DECEASED_CACHE", os.path.join(REPO, "practices/ehpa/registers/deceased_cache.json"))
MEDICARE = {"FLO02", "car6085"}
CCM = {"99487", "99489", "99490", "99491", "99439", "99437", "G0556", "G0557", "G0558", "G2058",
       "pcode492674", "pcode492675", "pcode492676", "pcode492677"}
MAX_AGE_DAYS = 30
LOG = []
_ASKED = {}          # pid -> the day Medicare was asked for the answer stedi_lookup just used (a shared answer can be older than today)
def _load():
    try: return json.load(open(CACHE))
    except Exception: return {}
def _save(c):
    os.makedirs(os.path.dirname(CACHE), exist_ok=True); json.dump(c, open(CACHE, "w"), indent=1, sort_keys=True)
def _put(pid, rec):
    """11/10/2026: write ONE chart's entry into the one cache file (CACHE). The file is read again just before the write, so what another
    helper or the date-of-death hook wrote meanwhile stays; the new file replaces the old in one step (temporary file, then rename); a file
    that is there but cannot be read is never overwritten (it may hold dates of death)."""
    try:
        with open(CACHE) as fh: txt = fh.read()
        c = json.loads(txt) if txt.strip() else {}
    except FileNotFoundError: c = {}
    except Exception: return False
    if not isinstance(c, dict): return False
    c[pid] = rec; d = os.path.dirname(os.path.abspath(CACHE)); os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".deceased_cache.", suffix=".tmp", dir=d)
    try:
        with os.fdopen(fd, "w") as fh: json.dump(c, fh, indent=1, sort_keys=True)
        os.replace(tmp, os.path.abspath(CACHE))
    finally:
        if os.path.exists(tmp): os.remove(tmp)
    return True
def _iso(d):
    d = str(d or "").strip()
    if re.match(r"\d{8}$", d): return f"{d[:4]}-{d[4:6]}-{d[6:]}"
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", d)
    return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}" if m else d[:10]
def dod_from_271(j):
    s = json.dumps(j)
    hits = re.findall(r'"[A-Za-z]*[Dd]eath[A-Za-z]*"\s*:\s*"(\d{8})"', s) + re.findall(r"DTP\*442\*D8\*(\d{8})", s)
    return _iso(sorted(set(hits))[0]) if hits else None
def _answered(j):
    """11/10/2026: True for an answer that says something about the patient - Part A or Part B lines or a date of death (an answer read
    back from medicare_store.py counts: the store keeps real answers only). An empty reply with no error is not an answer."""
    if not isinstance(j, dict): return False
    if isinstance(j.get("stored"), dict): return True
    return bool(dod_from_271(j)) or any(isinstance(x, dict) and x.get("insuranceTypeCode") in ("MA", "MB") for x in (j.get("benefitsInformation") or []))
def _medicare_member(t, dos_iso):
    """11/10/2026: the member number of the chart's Medicare Part B plan (car6085) from the chart record already fetched - an open one first
    (no end date, or one on/after the date of service), else the one that ended last; "" when that plan has no number; None = no such plan."""
    plans = [dict(re.findall(r'(\w+)="([^"]*)"', x)) for x in re.findall(r"<insplan [^>]*>", t or "")]
    med = [p for p in plans if p.get("carrier") == "car6085"]
    if not med: return None
    def end(p):
        mm = re.match(r"(\d\d)/(\d\d)/(\d{4})", p.get("enddate") or ""); return f"{mm.group(3)}-{mm.group(1)}-{mm.group(2)}" if mm else ""
    still = [p for p in med if not end(p) or end(p) >= dos_iso]
    return ((still or sorted(med, key=end, reverse=True))[0].get("subscribernum") or "").strip()
def _asked_before(j, dos_iso):
    """11/10/2026 (review fix): True for an answer read back from the store that was asked BEFORE the claim's date of service (or before
    today, for a date of service still to come) - it cannot know of a death since then, so the guard asks Medicare again."""
    asked = str(((j or {}).get("stored") or {}).get("asked") or "") if isinstance(j, dict) else ""
    return bool(asked) and asked < min(str(dos_iso or ""), datetime.date.today().isoformat())
def _stored_death(pid):
    """11/10/2026 (re-check fix): the date of death any Medicare answer kept in the answer store (medicare_store.py) shows for this chart,
    whatever its age or month of service - a death is never undone, so it still blocks when the guard's own call fails (the store and this
    cache travel apart: the cache may be lost, unreadable or scrubbed to '[DOB]'). -> YYYY-MM-DD or None."""
    try:
        import sys
        if HERE not in sys.path: sys.path.append(HERE)
        import medicare_store
        d = medicare_store.death(pid)
        return _iso(d) if d else None
    except Exception: return None
def stedi_lookup(pid, dos_iso):
    """Medicare record for pid as of dos -> (dod or None, ok)."""
    import amd, stedi
    _ASKED.pop(pid, None)
    t = amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"}), timeout=60)
    m = re.search(r'<patient [^>]*>', t); a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(0))) if m else {}
    if a.get("deceased") not in (None, "", "0"): return _iso(a.get("deceased")) if re.search(r"\d", a.get("deceased")) else dos_iso, True
    last, first = (a.get("name", "").split(",") + [""])[:2]; first = first.strip().split(" ")[0]
    mm = re.match(r"(\d\d)/(\d\d)/(\d{4})", a.get("dob", "")); dob8 = f"{mm.group(3)}{mm.group(1)}{mm.group(2)}" if mm else ""
    # 11/10/2026: ONE Medicare answer through the client (it holds the key and the provider block, counts the call, shares the answer)
    number = _medicare_member(t, dos_iso)
    ask = dict(member_id=number or None, dos=dos_iso.replace("-", ""), state="FL", pid=pid,
               who="guard" if number is not None else "guard, no Medicare plan on the chart")
    try:
        if hasattr(stedi, "medicare"):
            j, how = stedi.medicare(first, last.strip(), dob8, **ask, max_age_days=MAX_AGE_DAYS)
            if how != "failed" and not dod_from_271(j) and _asked_before(j, dos_iso):   # a shared answer asked BEFORE this date of service: asked again, fresh
                j, how = stedi.medicare(first, last.strip(), dob8, **ask)            # (re-check fix: one that already shows a death is used as it is - a death is never undone)
        else:                       # an older client in this workspace: the look-up as before, through the client
            j, how = stedi.mbi(first, last.strip(), dob8, "FL", dos_iso.replace("-", ""), pid=pid), "lookup"
        errs = [str(e).split(" ")[0] for e in stedi.med_summ(j)["errors"]]
    except Exception: return None, False
    dod = dod_from_271(j)
    if how == "failed": return dod, False
    ok = how == "plain" or errs == ["72"] or (not errs and _answered(j))     # 72 on a LOOK-UP = not a Medicare beneficiary: nothing to find, still a valid answer
    if ok or dod: _ASKED[pid] = (j.get("stored") or {}).get("asked") or datetime.date.today().isoformat()
    return dod, ok
def check(pid, dos, carrier=None, proc=None, allow_lookup=True):
    """-> (blocked: bool, reason: str). Blocks only on a known date of death earlier than the DOS."""
    pid = re.sub(r"\D", "", str(pid)); dos = _iso(dos); c = _load(); rec = c.get(pid)
    # 10/14/2026: a cache restored from GitHub carries the PHI gate's '[DOB]' in place of the date of death (35 charts) - a
    # non-date dod is UNKNOWN (re-lookup), never compared as a string (which silently let every DOS through).
    if rec and rec.get("dod") and not re.match(r"\d{4}-\d{2}-\d{2}$", str(rec.get("dod"))):
        rec = dict(rec); rec["dod"] = None; rec["checked"] = "2000-01-01"; c[pid] = rec
    stale = rec is None or (datetime.date.today() - datetime.date.fromisoformat(rec.get("checked", "2000-01-01"))).days > MAX_AGE_DAYS
    # 11/10/2026 (review fix): an entry checked BEFORE this claim's date of service cannot know of a death since - asked again (one plain check)
    stale = stale or str(rec.get("checked") or "") < min(dos, datetime.date.today().isoformat())
    needs = (carrier in MEDICARE) or ((proc or "") in CCM)
    if allow_lookup and needs and stale and not (rec and rec.get("dod")):
        dod, ok = stedi_lookup(pid, dos)
        if not ok and not dod:              # 11/10/2026 (review fix): a date of death the hook wrote during THIS check (a plain answer with 61) counts now
            try: seen = (_load().get(pid) or {}).get("dod")
            except Exception: seen = None
            if seen and re.match(r"\d{4}-\d{2}-\d{2}$", str(seen)): dod = seen
        if not ok and not dod: dod = _stored_death(pid)     # 11/10/2026 (re-check fix): a death an answer in the store already shows still blocks
        if ok or dod:
            rec = {"dod": dod, "checked": _ASKED.pop(pid, None) or datetime.date.today().isoformat(), "src": "stedi-medicare-271" if dod else "stedi: no death on record"}
            c[pid] = rec; _put(pid, rec)
        else: LOG.append(f"pat{pid} DOS {dos}: date of death UNVERIFIED (lookup failed)")
    dod = (rec or {}).get("dod")
    if dod and dos and dos > dod:
        return True, f"pat{pid} DOS {dos} is after date of death {dod} ({(rec or {}).get('src')}) - claim must not be submitted" + \
                     ("; CCM in the month of death needs a DOS on/before the death date, else void" if (proc or "") in CCM and dos[:7] == dod[:7] else "; void the charge")
    return False, ""
def check_charge(chargeid, sequencenumber=None, allow_lookup=True):
    """Reads the charge (patient, visit date, procedure, carrier at the billed sequence) and applies check()."""
    import resave
    import xml.etree.ElementTree as ET
    cid = re.sub(r"\D", "", str(chargeid)); d = ET.fromstring(resave.detail(cid))
    v = d.find(".//visit"); p = d.find(".//patient"); ch = [x for x in d.iter("charge") if x.get("id") == "charge" + cid]
    pid = re.sub(r"\D", "", p.get("id")) if p is not None else ""
    carrier = None
    if sequencenumber is not None:
        for ip in d.iter("insplan"):
            if str(ip.get("sequence")) == str(sequencenumber): carrier = ip.get("carrier")
    proc = ch[0].get("proccode") if ch else None
    return check(pid, v.get("date") if v is not None else "", carrier, proc, allow_lookup)
def record(pid, j, src="stedi-medicare-271"):
    """Store what a Medicare 271 says about death for pid (called by scripts/helpers/stedi.py on every Medicare lookup)."""
    pid = re.sub(r"\D", "", str(pid)); dod = dod_from_271(j); c = _load()
    errs = [e.get("code") for e in (j.get("errors") or [])]
    if dod or errs == ["72"] or (not errs and _answered(j)):          # 11/10/2026: an empty reply is not kept as 'no death on record'
        _put(pid, {"dod": dod, "checked": datetime.date.today().isoformat(), "name": (c.get(pid) or {}).get("name"),
                   "src": src if dod else ("stedi: not a Medicare beneficiary" if errs == ["72"] else "stedi: no death on record")})
    return dod
