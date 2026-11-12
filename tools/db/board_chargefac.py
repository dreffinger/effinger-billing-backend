#!/usr/bin/env python3
# PLAIN ENGLISH (Insurance Refresh Board - William 11/12/2026: "on the insurance refresh board instead of generic snf there should be a
#   specific facility to list so i know where to list if no facility ok to out gebneric but there should alsways be a facility to list
#   there where the charge came from").
# Decides: nothing about billing. For each card on the board it works out the charge the card is about and the facility AdvancedMD
#   billed that charge from, out of the practice's Neon database, and puts it on the card as `chargefac` - the badge the board shows
#   top-left (boards/templates/tracker.html facInfo(): chargefac first, then facnow, the facilities line, lastfac, the facility text;
#   a generic SNF / ALF only when none of them names a facility).
# Where the generic "SNF" came from: a run that creates a card fills `facility` itself, and until 11/12 nothing said what goes there,
#   so runs wrote a place-of-service guess from the visit codes ('SNF (99309 11/4/2026 + 10/5/2026, fac32)', 'SNF / ALF', 'NF') even
#   with the visit's facility id in hand. The specific names (facnow, the facilities line, lastfac) come only from boards/
#   board_identity.py and board_facnow.py, which read AdvancedMD from a chat session (9/14 and 10/4) - no routine runs them.
# How a card maps to its charge (the card holds the chart number and text, never a charge id) - the first rule that finds a charge wins:
#   1. visit    an AdvancedMD visit id named anywhere on the card (v19460514, vst19460514, "visits 19419032 / ...") that is a visit of
#               the card's chart(s)
#   2. dos      a date of service of the chart named in the card's facility text, then in its need / why (m/d/yyyy, m/d-m/d/yyyy,
#               m/d + m/d/yyyy, m/yyyy)
#   3. facility id   one AdvancedMD facility id in the facility text or the need (fac32) - the run had the visit's facility in hand
#   4. open balance  the chart's newest live charge that still owes money (insurance or patient balance above zero)
#   5. dos in notes  a date of service named in the lookup trail, the API blocks or the notes
#   6. newest charge the chart's newest live charge
#   A card whose named charge (rule 1 or 2) has no facility in AdvancedMD stays generic (William: "if no facility ok to put generic").
#   Several charges at different facilities: the facility most of them came from is named (the newer one on a tie, shown with its
#   newest charge), the others are listed under `also`. A hospital (or other non-home) charge also carries `res`, the newest SNF / ALF /
#   IL / ICF facility on the chart - where the patient lives.
# Reads (SELECT only - anything else is refused before it leaves; Neon's HTTPS SQL route with NEON_DATABASE_URL, the way
#   tools/db/neon_db.py reaches it when port 5432 is closed): the board's copy (raw.documents source insurance_refresh_board, collection
#   items - as fresh as the last practice database sync) unless --items gives the rows; amd.charges (AdvancedMD history, pulled
#   11/10/2026); ehpa.feed_charges (Claimocity feed visits, for charges entered after the pull); the facility id -> code pairs of the
#   charge-detail documents (raw.documents source amd_history, collection chargedetail, visits{}).
# Writes: files only. Never AdvancedMD (nothing here calls it), never Neon, never the board (the board applies the file itself),
#   never Drive (delivering the file to the "board inbox" folder is a separate step), never the repository (an output folder inside the
#   checkout is refused).
# Usage:
#   python3 tools/db/board_chargefac.py plan [--items <file|dir>]          counts only: cards that get a specific facility, by rule; generic, by reason
#   python3 tools/db/board_chargefac.py build --out <dir> [--stamp 2026-11-12T1500Z] [--all] [--items <file|dir>]
#        ONE board_updates_<stamp>.json (schema irb-board-updates/1): {"op":"update","collection":"items","id":...,"set":{"chargefac":{...}}}
#        for every open card whose charge facility is new or changed (--all: done cards too - applying stamps their `updated`, which the
#        page's "Also on this chart: ... (done <date>)" line reads, so they are left out by default). "update" never re-creates a card that
#        has left the board since the copy was made (that op fails and is listed by the page's sync log).
#   python3 tools/db/board_chargefac.py stamp --file <board_updates_<stamp>.json>
#        for a run, after board_ops.clean_file and before the upload: adds `chargefac` to every row the file creates or whose facility /
#        amdid it sets. When the database cannot be read the file is left exactly as it was (exit 0) - the run goes on.
#   --items: a JSON list of rows (each with "id"), a JSON object {id: row}, or the folder an ArtifactData list wrote (<dir>/items/<id>.json).
# Self-test: python3 tools/selftest/test_board_chargefac.py
import os, sys, re, json, datetime, collections, urllib.request, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "scripts", "helpers"))
import board_ops                                     # the one gate every board_updates file passes through (no `updated` in a set)

ROWS_SQL = "select doc_id, body::text from raw.documents where source = 'insurance_refresh_board' and collection = 'items'"
COPY_SQL = "select count(*)::text, coalesce(max(loaded_at)::text, '') from raw.documents where source = 'insurance_refresh_board' and collection = 'items'"
CHARGES_SQL = ("select chart_id, coalesce(charge_id, ''), coalesce(visit_id, ''), coalesce(dos::text, ''), coalesce(cpt, ''), coalesce(facility_code, ''), "
               "coalesce(facility, ''), live::text, coalesce(insurance_balance, 0)::text, coalesce(patient_balance, 0)::text "
               "from amd.charges where chart_id = any(string_to_array(%s, ','))")
FEED_SQL = ("select chart_id, coalesce(visit_id, ''), coalesce(dos::text, ''), coalesce(array_to_string(cpts, '+'), ''), coalesce(facility_id, ''), "
            "coalesce(facility, '') from ehpa.feed_charges where chart_id = any(string_to_array(%s, ','))")
FACIDS_SQL = ("select v.value->>'facility', coalesce(v.value->>'facility_code', ''), count(*)::text from raw.documents d "
              "cross join lateral jsonb_each(d.body->'visits') v where d.source = 'amd_history' and d.collection = 'chargedetail' group by 1, 2")
CODES_SQL = "select coalesce(facility_code, ''), max(facility) from amd.charges where coalesce(facility, '') <> '' group by 1"

KIND_LABEL = {"SNF": "SNF resident", "ALF": "ALF resident", "IL": "IL resident", "ICF": "ICF resident", "HOSP": "hospital inpatient",
              "IRF": "inpatient rehab", "HOME": "home visit", "TELE": "telehealth", "OFFICE": "office", "OTHER": ""}
RES_KINDS = ("SNF", "ALF", "IL", "ICF")
SHORTALL = {"HCA FLORIDA CAPITAL HOSPITAL TALLAHASSEE MEDICAL C": "HCA Capital Hospital",      # board_identity.py's short names, so the
            "BRYNWOOD OPERATIONS LLC BRYNWOOD OPERATIONS LLC": "Brynwood (Monticello)",          # badge reads like the facilities line
            "CENTRE POINTE HEALTH AND REHAB CENTER CENTRE POINT": "Centre Pointe Health & Rehab"}


# ---- the database: one SELECT at a time --------------------------------------------------------------------------------------------
def database_url():
    for k in ("NEON_DATABASE_URL", "DATABASE_URL"):
        v = re.sub(r"\s+", "", os.environ.get(k) or "")
        if v.startswith("postgres"): return v
    for p in (os.path.join(REPO, "secrets", "neon_database_url"), "/home/claude/unbilled/secrets/neon_database_url",
              os.path.expanduser("~/.config/ehpa/neon_database_url")):
        if os.path.isfile(p):
            v = re.sub(r"\s+", "", open(p, encoding="utf-8").read())
            if v.startswith("postgres"): return v
    raise RuntimeError("no connection string (NEON_DATABASE_URL is not set)")

def neon_select(sql, params=()):
    """one SELECT over Neon's HTTPS SQL route; rows as lists of text. Anything but one SELECT is refused here, before it leaves.
    A %s is a place for a value only when values are sent (tools/db/neon_db.py, 11/12)."""
    if not re.match(r"^\s*(select|with)\b", sql, re.I) or ";" in sql.rstrip().rstrip(";"):
        raise ValueError("board_chargefac reads only: one SELECT statement")
    u = database_url()
    if params:
        n = [0]
        def ph(m): n[0] += 1; return "$%d" % n[0]
        sql = re.sub(r"%s", ph, sql)
    body = json.dumps({"query": sql, "params": [None if p is None else str(p) for p in params]}).encode("utf-8")
    req = urllib.request.Request("https://%s/sql" % urllib.parse.urlparse(u).hostname, data=body, method="POST",
                                 headers={"Neon-Connection-String": u, "Content-Type": "application/json", "Neon-Array-Mode": "true", "Neon-Raw-Text-Output": "true"})
    with urllib.request.urlopen(req, timeout=180) as r: return json.loads(r.read().decode("utf-8")).get("rows") or []


# ---- facility names and kinds ------------------------------------------------------------------------------------------------------
def short(n):
    """AdvancedMD's capitals -> the facilities line's spelling (board_identity.short); a name already written for people (the feed's) stays"""
    n = re.sub(r"\s+", " ", str(n or "")).strip()
    if not n or n != n.upper(): return n
    if n in SHORTALL: return SHORTALL[n]
    n = n.title().replace(" Alf", " ALF").replace(" Llc", "").replace("Of ", "of ").replace("At ", "at ").replace("And ", "and ")
    return re.sub(r"\s+", " ", re.sub(r"\bHca\b", "HCA", n)).strip()

def kind_of(name):
    """the board page's kindOf() - keep the two in step. Facility names are matched by words the repository's privacy gate leaves alone
    (it once took two facility names for patient names and rewrote them in the page source): SOUTHWOOD, and the generic words."""
    n = re.sub(r"\s+", " ", str(name or "").upper().replace("&", " AND "))
    if not n: return "OTHER"
    if re.search(r"\bALF\b|ASSISTED|MEMORY CARE|BROOKDALE|ALLEGRO|AZALEA|CANTERFIELD|CAPITAL SQUARE|GROVE AT CANOPY|HARBOR ?CHASE|PACIFICA|SODALIS|TAPESTRY|PARRY", n): return "ALF"
    if re.search(r"BRYNWOOD|SOUTHWOOD|ASPIRE|AVIATA|CENTRE POINTE|CENTER POINTE|EDEN SPRINGS|LAKE PARK|SEVEN HILLS|BERTRAND|HEALTH AND REHAB|REHABILITATION CENTER|NURSING", n): return "SNF"
    if re.search(r"HCA REHAB|INPATIENT REHAB|\bIRF\b", n): return "IRF"
    if re.search(r"HOSPITAL|\bHCA\b|\bTMH\b|MEMORIAL|MEDICAL CENTER|\bER\b|EMERGENCY", n): return "HOSP"
    if re.search(r"INDEPENDENT LIVING|\bIL\b", n): return "IL"
    if re.search(r"DEVELOPMENTAL|\bICF\b", n): return "ICF"
    if re.search(r"TELEHEALTH", n): return "TELE"
    if re.search(r"INDIVIDUAL PATIENT HOMES|\bHOME\b", n): return "HOME"
    if re.search(r"NORTH FLORIDA SENIOR CARE|\bOFFICE\b", n): return "OFFICE"
    if re.search(r"\bSNF\b|\bNF\b|\bLTC\b|SKILLED|REHAB|HEALTH CENTER|WESTMINSTER", n): return "SNF"
    return "OTHER"


# ---- what a card says about its charge ---------------------------------------------------------------------------------------------
def chart_ids(row):
    """'pat<n>' for every chart number on the card: amdid may list several ('45447, 17476874'); pid / chart are older spellings"""
    out = []
    for k in ("amdid", "pid", "chart"):
        for n in re.findall(r"(?<!\d)(\d{4,9})(?!\d)", str((row or {}).get(k) or "")):
            if "pat" + n not in out: out.append("pat" + n)
    return out

def _texts(row, keys):
    out = []
    for k in keys:
        v = (row or {}).get(k)
        if isinstance(v, str): out.append(v)
        elif isinstance(v, list):
            for e in v:
                if isinstance(e, dict): out.extend(str(e.get(x) or "") for x in ("src", "step", "result", "text"))
                elif isinstance(e, str): out.append(e)
    return " \n ".join(out)
def facility_text(row): return _texts(row, ("facility",))
def need_text(row): return _texts(row, ("need", "why", "title"))
def trail_text(row): return _texts(row, ("checks", "api", "notes", "note"))
def all_text(row): return " \n ".join((facility_text(row), need_text(row), trail_text(row)))

def _year(y): y = int(y); return y + 2000 if y < 100 else y
def _iso(y, m, d):
    try: return datetime.date(_year(y), int(m), int(d)).isoformat()
    except ValueError: return None
RANGE_RE = re.compile(r"(?<![\d/])(\d{1,2})/(\d{1,2})\s*[-–]\s*(\d{1,2})/(\d{1,2})/(\d{4}|\d{2})(?![\d/])")
PAIR_RE = re.compile(r"(?<![\d/])(\d{1,2})/(\d{1,2})\s*(?:\+|&|,|and)\s*(\d{1,2})/(\d{1,2})/(\d{4}|\d{2})(?![\d/])")
DATE_RE = re.compile(r"(?<![\d/])(\d{1,2})/(\d{1,2})/(\d{4}|\d{2})(?![\d/])")
ISO_RE = re.compile(r"(?<!\d)(20\d{2})-(\d{2})-(\d{2})(?!\d)")
MONTH_RE = re.compile(r"(?<![\d/])(\d{1,2})/(20\d{2})(?![\d/])")
def date_spans(text):
    """every date (or span of dates) of service the text names, as (first, last) ISO pairs"""
    out = []
    for m in RANGE_RE.finditer(text):
        a, b = m.group(1, 2), m.group(3, 4); y = _year(m.group(5))
        end = _iso(y, *b); start = _iso(y - 1 if int(a[0]) > int(b[0]) else y, *a)
        if start and end and start <= end: out.append((start, end))
    for m in PAIR_RE.finditer(text):
        y = _year(m.group(5)); first = _iso(y, m.group(1), m.group(2))
        if first: out.append((first, first))
    for m in DATE_RE.finditer(text):
        d = _iso(m.group(3), m.group(1), m.group(2))
        if d: out.append((d, d))
    for m in ISO_RE.finditer(text):
        d = _iso(m.group(1), m.group(2), m.group(3))
        if d: out.append((d, d))
    for m in MONTH_RE.finditer(text):
        y, mo = int(m.group(2)), int(m.group(1))
        if 1 <= mo <= 12:
            last = (datetime.date(y + (mo == 12), mo % 12 + 1, 1) - datetime.timedelta(days=1)).isoformat()
            out.append(("%04d-%02d-01" % (y, mo), last))
    return out
def visit_numbers(text): return set(re.findall(r"(?<!\d)(\d{8})(?!\d)", text))
def facility_ids(text): return sorted(set(re.findall(r"(?<![A-Za-z0-9])fac(\d{1,5})(?!\d)", text)))


# ---- the charges -------------------------------------------------------------------------------------------------------------------
def _num(v):
    try: return float(v)
    except (TypeError, ValueError): return 0.0
def load_facilities(select):
    """facility id ('fac32') -> AdvancedMD code, and code -> AdvancedMD name"""
    by_id = {}
    for fid, code, n in select(FACIDS_SQL):
        if fid and (fid not in by_id or int(n or 0) > by_id[fid][1]): by_id[fid] = (code or "", int(n or 0))
    names = {code: name for code, name in select(CODES_SQL) if code}
    return {k: v[0] for k, v in by_id.items()}, names

def load_charges(select, charts, fac_codes, fac_names):
    """chart -> its charge lines {visit, dos, cpt, code, name, live, owed, src}: AdvancedMD's history, then the feed's visits it lacks"""
    by = collections.defaultdict(list)
    if not charts: return by
    arg = ",".join(sorted(charts))
    for chart, charge, visit, dos, cpt, code, name, live, insbal, patbal in select(CHARGES_SQL, (arg,)):
        by[chart].append({"visit": re.sub(r"\D", "", visit), "charge": charge, "dos": dos, "cpt": cpt, "code": code, "name": name,
                          "live": live in ("true", "t", "1"), "owed": _num(insbal) > 0.004 or _num(patbal) > 0.004, "src": "amd"})
    try: feed = select(FEED_SQL, (arg,))
    except Exception as e:                            # the feed view is a convenience; the history alone still answers
        print("board_chargefac: feed visits not read (%s)" % str(e)[:120], file=sys.stderr); feed = []
    for chart, visit, dos, cpts, fid, fname in feed:
        v = re.sub(r"\D", "", visit)
        if not v or any(c["visit"] == v for c in by[chart]): continue
        code = fac_codes.get(fid, "")
        by[chart].append({"visit": v, "charge": "", "dos": dos, "cpt": cpts, "code": code, "name": fac_names.get(code) or fname,
                          "live": True, "owed": False, "src": "feed"})
    return by


# ---- one card -> its charge facility -------------------------------------------------------------------------------------------------
def _mdy(iso): return "%s/%s/%s" % (iso[5:7], iso[8:10], iso[:4]) if len(iso or "") >= 10 else ""
def _mm_yy(iso): return "%d/%s" % (int(iso[5:7]), iso[2:4]) if len(iso or "") >= 10 else ""

def _pick(lines, how, all_lines, now):
    """the facility most of the card's named charges came from (the newer one on a tie; live lines before void ones), shown with its
    newest charge; None when none of them has a facility"""
    named = [c for c in lines if c["name"]]
    if not named: return None
    live = [c for c in named if c["live"]] or named
    by = collections.defaultdict(list)
    for c in live: by[short(c["name"])].append(c)
    nm = max(by, key=lambda s: (len(by[s]), max(c["dos"] for c in by[s])))
    best = max(by[nm], key=lambda c: (c["dos"], c["visit"]))
    k = kind_of(best["name"])
    cf = {"name": nm, "kind": k, "label": KIND_LABEL.get(k, ""), "dos": _mdy(best["dos"]), "cpt": best["cpt"], "visit": best["visit"],
          "code": best["code"], "how": how, "src": "neon " + ("feed" if best["src"] == "feed" else "amd.charges"), "at": now}
    also = []
    for c in sorted(named, key=lambda c: c["dos"], reverse=True):
        s = short(c["name"])
        if s != nm and s not in also: also.append(s)
    if also: cf["also"] = also[:3]
    if k not in RES_KINDS:
        homes = [c for c in all_lines if c["name"] and c["live"] and kind_of(c["name"]) in RES_KINDS]
        if homes:
            h = max(homes, key=lambda c: c["dos"]); hn = short(h["name"])
            last = max(c["dos"] for c in homes if short(c["name"]) == hn)
            cf["res"] = {"name": hn, "kind": kind_of(h["name"]), "thru": _mm_yy(last)}
    return cf

def charge_facility(row, charges, fac_codes, fac_names, now=None):
    """(chargefac or None, why). charges: chart -> lines (load_charges)."""
    now = now or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    charts = chart_ids(row)
    lines = [c for ch in charts for c in charges.get(ch, [])]
    ftext, ntext, ttext = facility_text(row), need_text(row), trail_text(row)
    if lines:
        vis = visit_numbers(all_text(row))
        hit = [c for c in lines if c["visit"] and c["visit"] in vis]
        if hit:
            cf = _pick(hit, "visit", lines, now)
            return (cf, "visit") if cf else (None, "the card's charge has no facility in AdvancedMD")
        for how, text in (("dos", ftext), ("dos", ntext)):
            spans = date_spans(text)
            hit = [c for c in lines if c["dos"] and any(a <= c["dos"] <= b for a, b in spans)]
            if hit:
                cf = _pick(hit, how, lines, now)
                return (cf, how) if cf else (None, "the card's charge has no facility in AdvancedMD")
    ids = [i for i in facility_ids(ftext + " \n " + ntext) if i != "1"]          # fac1 is AdvancedMD's "no facility"
    codes = sorted({fac_codes.get("fac" + i, "") for i in ids} - {""})
    if len(codes) == 1 and fac_names.get(codes[0]):
        nm = fac_names[codes[0]]; k = kind_of(nm)
        cf = {"name": short(nm), "kind": k, "label": KIND_LABEL.get(k, ""), "dos": "", "cpt": "", "visit": "", "code": codes[0],
              "how": "facility id", "src": "neon chargedetail", "at": now}
        return cf, "facility id"
    if not charts: return None, "no chart number on the card"
    if not lines: return None, "no charge of the chart in the practice database"
    owed = [c for c in lines if c["live"] and c["owed"]]
    cf = _pick(owed, "open balance", lines, now) if owed else None
    if cf: return cf, "open balance"
    spans = date_spans(ttext)
    hit = [c for c in lines if c["dos"] and any(a <= c["dos"] <= b for a, b in spans)]
    cf = _pick(hit, "dos in notes", lines, now) if hit else None
    if cf: return cf, "dos in notes"
    cf = _pick([c for c in lines if c["live"]] or lines, "newest charge", lines, now)
    return (cf, "newest charge") if cf else (None, "no charge of the chart has a facility in AdvancedMD")


# ---- the board rows ----------------------------------------------------------------------------------------------------------------
def _unwrap(d):
    if isinstance(d, dict) and isinstance(d.get("data"), dict) and ("version" in d or "id" in d) and len(d) <= 4: return d["data"]
    return d
def rows_from_items(path):
    """--items: a list of rows, an {id: row} object, or the folder an ArtifactData list wrote (<dir>/items/<id>.json or <dir>/<id>.json)"""
    if os.path.isdir(path):
        base = os.path.join(path, "items") if os.path.isdir(os.path.join(path, "items")) else path
        out = []
        for f in sorted(os.listdir(base)):
            if f.endswith(".json"):
                d = _unwrap(json.load(open(os.path.join(base, f), encoding="utf-8")))
                if isinstance(d, dict): out.append(dict(d, id=d.get("id") or f[:-5]))
        return out
    d = json.load(open(path, encoding="utf-8"))
    if isinstance(d, dict) and isinstance(d.get("items"), list): d = d["items"]
    if isinstance(d, dict): return [dict(_unwrap(v), id=k) for k, v in d.items() if isinstance(_unwrap(v), dict)]
    return [dict(_unwrap(r)) for r in d if isinstance(_unwrap(r), dict) and _unwrap(r).get("id")]

def rows_from_neon(select):
    out = []
    for doc_id, body in select(ROWS_SQL):
        try: b = json.loads(body)
        except ValueError: continue
        if isinstance(b, dict): out.append(dict(b, id=doc_id))
    return out

def _same(a, b):
    strip = lambda x: {k: v for k, v in (x or {}).items() if k != "at"} if isinstance(x, dict) else x
    return json.dumps(strip(a), sort_keys=True) == json.dumps(strip(b), sort_keys=True)

def compute(rows, select, now=None):
    """[(row, chargefac or None, why)] for every row"""
    fac_codes, fac_names = load_facilities(select)
    charts = sorted({c for r in rows for c in chart_ids(r)})
    charges = load_charges(select, charts, fac_codes, fac_names)
    return [(r,) + charge_facility(r, charges, fac_codes, fac_names, now) for r in rows]

GENERIC_RE = re.compile(r"^(SNF|ALF|NF|HCA|TMH)(\b|[\s/(])", re.I)          # the page's test for a place-of-service guess
def badge_source(row, cf):
    """what the card's badge shows once the file is applied - the page's facInfo() order"""
    old = row.get("chargefac")
    if cf or (isinstance(old, dict) and old.get("name")): return "charge facility"
    fn = row.get("facnow")
    if isinstance(fn, dict) and fn.get("name"): return "newest visit (facnow)"
    if str(row.get("facilities") or "").strip(): return "facilities line"
    if row.get("lastfac"): return "last facility"
    t = str(row.get("facility") or "").strip()
    if t: return "generic" if GENERIC_RE.match(t) else "the card's own facility text"
    return "no facility at all"

def counts(results, include_done=False):
    """per part (open / done cards): how many get the charge's facility, by rule; why the others do not; what each badge then shows
    (a done card left out of the file keeps the badge it has)"""
    c = collections.OrderedDict()
    for part, keep in (("open", lambda r: str(r.get("status") or "") != "done"), ("done", lambda r: str(r.get("status") or "") == "done")):
        sub = [(r, cf, why) for r, cf, why in results if keep(r)]
        applied = part == "open" or include_done
        c[part] = {"cards": len(sub), "specific": sum(1 for _, cf, _ in sub if cf), "generic": sum(1 for _, cf, _ in sub if not cf),
                   "by_rule": dict(collections.Counter(why for _, cf, why in sub if cf).most_common()),
                   "not_found_why": dict(collections.Counter(why for _, cf, why in sub if not cf).most_common()),
                   "in_file": applied,
                   "badge": dict(collections.Counter(badge_source(r, cf if applied else None) for r, cf, _ in sub).most_common())}
    return c


# ---- the commands -------------------------------------------------------------------------------------------------------------------
def _inside_repo(p): p = os.path.abspath(p); return p == REPO or p.startswith(REPO + os.sep)
def _now(): return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def build_file(results, stamp, now, include_done=False):
    ops = []
    for r, cf, _ in results:
        if not cf or (not include_done and str(r.get("status") or "") == "done"): continue
        if _same(cf, r.get("chargefac")): continue
        ops.append({"op": "update", "collection": "items", "id": r["id"], "set": {"chargefac": cf}})
    doc = {"schema": "irb-board-updates/1", "source": "tools/db/board_chargefac.py build %s (read-only on Neon)" % stamp, "created": now, "ops": ops}
    return board_ops.clean_file(doc)

def stamp_file(doc, select, now=None):
    """adds chargefac to every items row the run's file creates or whose facility / amdid it sets; returns [(id, chargefac or None, why)]"""
    targets = []
    for o in doc.get("ops") or []:
        if not isinstance(o, dict) or str(o.get("collection") or "items") != "items": continue
        kind = str(o.get("op") or "upsert").lower()
        body = o.get("data") if kind == "replace" else o.get("set")
        if not isinstance(body, dict) or not ({"amdid", "facility", "pid"} & set(body)) or body.get("chargefac"): continue
        app = o.get("append") if isinstance(o.get("append"), dict) else {}
        row = dict(body, id=o.get("id"))
        for k in ("notes", "checks", "api"):
            if isinstance(app.get(k), list): row[k] = list(row.get(k) or []) + app[k]
        targets.append((body, row))
    if not targets: return []
    results = compute([row for _, row in targets], select, now)
    out = []
    for (body, row), (_, cf, why) in zip(targets, results):
        if cf: body["chargefac"] = cf
        out.append((row.get("id"), cf, why))
    return out

def main(argv, select=None):
    select = select or neon_select
    a = list(argv)
    def opt(name, default=None): return a[a.index(name) + 1] if name in a and a.index(name) + 1 < len(a) else default
    cmd = a[0] if a and not a[0].startswith("--") else ""
    now = _now()
    if cmd == "stamp":
        path = opt("--file")
        if not path or not os.path.isfile(path): print("usage: board_chargefac.py stamp --file <board_updates_<stamp>.json>"); return 2
        doc = json.load(open(path, encoding="utf-8"))
        try: got = stamp_file(doc, select, now)
        except Exception as e:
            print("board_chargefac stamp: the practice database could not be read (%s) - %s left exactly as it was" % (str(e)[:160], os.path.basename(path)))
            return 0
        if any(cf for _, cf, _ in got):
            with open(path, "w", encoding="utf-8") as f: json.dump(doc, f, indent=1, ensure_ascii=False)
        for rid, cf, why in got: print("  %s: %s" % (rid, ("%s (%s)" % (cf["name"], why)) if cf else "generic - " + why))
        print("board_chargefac stamp %s: %d row(s) looked at, %d given the charge's facility" % (os.path.basename(path), len(got), sum(1 for _, cf, _ in got if cf)))
        return 0
    if cmd not in ("plan", "build"):
        print("usage: board_chargefac.py plan | build --out <dir> [--stamp <UTC stamp>] [--all] | stamp --file <file>   [--items <file|dir>]"); return 2
    out = opt("--out")
    if cmd == "build":
        if not out: print("board_chargefac build: --out <dir> is required (a folder outside the repository)"); return 2
        if _inside_repo(out): print("board_chargefac build: refused - %s is inside the repository (board files carry patient data)" % out); return 2
    items = opt("--items")
    if items: rows, copy = rows_from_items(items), "rows from %s" % items
    else:
        n, at = (select(COPY_SQL) or [["0", ""]])[0]
        rows, copy = rows_from_neon(select), "the board's copy in Neon (%s rows, loaded up to %s)" % (n, at or "?")
    results = compute(rows, select, now)
    c = counts(results, include_done="--all" in a)
    print("board_chargefac %s: %s" % (cmd, copy))
    for part, v in c.items():
        print("  %s cards %d: the charge's facility found for %d %s; not found for %d %s" % (part, v["cards"], v["specific"], json.dumps(v["by_rule"]), v["generic"], json.dumps(v["not_found_why"])))
        print("    the badge then shows%s: %s" % ("" if v["in_file"] else " (done cards are left out of the file - --all adds them)", json.dumps(v["badge"])))
    if cmd == "plan": return 0
    stamp = re.sub(r"[^0-9A-Za-z\-]", "", opt("--stamp") or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H%MZ"))
    doc = build_file(results, stamp, now, include_done="--all" in a)
    os.makedirs(out, exist_ok=True)
    name = os.path.join(out, "board_updates_%s.json" % stamp)
    with open(name, "w", encoding="utf-8") as f: json.dump(doc, f, indent=1, ensure_ascii=False)
    print("board_chargefac build: %d card(s) get the charge's facility -> %s (not delivered: the board applies it once it is in the Drive folder 'board inbox')" % (len(doc["ops"]), name))
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
