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
#   4. open balance  the chart's newest live charge that still owes money (insurance or patient balance above zero) - the lines of the
#                    NEWEST such date, never the facility most of the owing lines came from (a patient who moved shows where they are now)
#   5. dos in notes  a date of service named in the lookup trail, the API blocks or the notes
#   6. newest charge the chart's newest LIVE charge (the lines of its newest date of service). A voided charge's facility is never named
#                    here: a chart none of whose live charges has a facility stays generic, as it did before 11/12 (second review).
#   The chart number is amdid (pid / chart are older spellings). A card with none falls back to the number its id ends with (the prompts'
#   id form last-first-<amdid>), then to pat<n> written in its text; the badge then says so (chart_from "card id" / "card text"). A
#   date-shaped id ending is never taken for a chart: mmdd (-1031), a year (-2026), mmddyy / yymmdd (-111226, -261112), yyyymmdd /
#   mmddyyyy (-20261112, -11122026), years 2020-2039.
#   A card whose named charge (rule 1 or 2) has no facility in AdvancedMD stays generic (William: "if no facility ok to put generic").
#   Several named charges at different facilities: the facility most of them came from is named (the newer one on a tie, shown with its
#   newest charge), the others are listed under `also`. A hospital (or other non-home) charge also carries `res`, the newest SNF / ALF /
#   IL / ICF facility on the chart - where the patient lives.
#   Every chargefac carries EVERY key of CF_KEYS (also [] and res / chart_from null when they do not apply): the board writes a set with
#   update(), which merges a nested object key by key, so a key left out would keep the earlier badge's value. `chart` is the card's AMD
#   chart number(s) the badge was worked out on (comma-separated, "" when the card had none).
# A stronger badge stays (_keeps, and the board page's applyOp makes the same check against the badge the row really holds when it
#   applies ANY file): a guess (open balance, dos in notes, newest charge) never replaces a badge found by a stronger rule - a visit match
#   is never replaced by the chart's newest charge - while the card still has the chart(s) that badge was worked out on. A corrected
#   chart number lets the new chart's result through.
# A badge belongs to the chart(s) it was worked out on (third review 11/12, _on_card; the board page's cfOnCard is the same test): the
#   page shows a badge, and applies a file's badge, only while the card still has every one of them (a card with no chart number of its
#   own, and a badge naming none, pass), and build / stamp clear a stored badge worked out on a chart the card no longer has when nothing
#   is found on the chart it has now (chargefac null) - a corrected chart number never leaves the old chart's facility, visit and date.
# Reads (SELECT only - anything else is refused before it leaves; Neon's HTTPS SQL route with NEON_DATABASE_URL, the way
#   tools/db/neon_db.py reaches it when port 5432 is closed): the board's copy (raw.documents source insurance_refresh_board, collection
#   items - as fresh as the last practice database sync) unless --items gives the rows; amd.charges (AdvancedMD history, pulled
#   11/10/2026); ehpa.feed_charges (Claimocity feed visits, for charges entered after the pull); the facility id -> code pairs of the
#   charge-detail documents (raw.documents source amd_history, collection chargedetail, visits{}).
# Writes: files only. Never AdvancedMD (nothing here calls it), never Neon, never the board (the board applies the file itself),
#   never Drive (delivering the file to the "board inbox" folder is a separate step), never the repository (an output folder inside the
#   checkout is refused).
# Usage:
#   python3 tools/db/board_chargefac.py plan [--items <file|dir>]          counts only: cards that get a specific facility, by the rule of the
#        badge each card ends up with (a card that keeps its stored badge counts under that badge's rule); how many keep their badge and how
#        many lose another chart's badge; generic, by reason
#   python3 tools/db/board_chargefac.py build --out <dir> [--stamp 2026-11-12T1500Z] [--all] [--items <file|dir>]
#        ONE board_updates_<stamp>.json (schema irb-board-updates/1): {"op":"update","collection":"items","id":...,"set":{"chargefac":{...}}}
#        for every open card whose charge facility is new or changed (--all: done cards too - applying stamps their `updated`, which the
#        page's "Also on this chart: ... (done <date>)" line reads, so they are left out by default). "update" never re-creates a card that
#        has left the board since the copy was made (that op fails and is listed by the page's sync log). A card whose badge stays
#        (_keeps) gets no op - the page would keep that badge anyway, and the file would re-send it on every build. A card whose stored
#        badge was worked out on a chart it no longer has, with nothing found on the chart it has now, gets "set":{"chargefac":null}.
#   python3 tools/db/board_chargefac.py stamp --file <board_updates_<stamp>.json> [--items <file|dir>]
#        for a run, after board_ops.clean_file and before the upload: adds `chargefac` to every row the file creates or whose facility /
#        amdid it sets. --items = the stored rows, from the run's inline board read, of the cards on the board that the file's ops touch
#        (only those): such a card is worked out from the whole card (its stored text plus the op's set and appends) and keeps the badge
#        it has (_keeps), or loses a stored badge worked out on a chart it no longer has (chargefac null, when nothing is found on the
#        chart it has now). A card stamp cannot see whole - not among the --items rows (second review 11/12: the rows given may be
#        partial, empty or wrongly shaped), or no --items - gets only a VISIT it names (third review 11/12: a date of service or facility
#        id read from the op alone could be outranked by a visit its stored row names), with its chart number read from the op's own
#        amdid / pid / chart only (the stored card may carry an amdid the op does not repeat); a new card - its set carries `created`, as
#        board_ops.plan_new_row writes it, or patient and dob - gets any match, even a guess. The page's applyOp keeps a stronger badge,
#        and refuses a badge worked out on a chart the card does not have, whatever the file holds. Prints counts only (row ids are
#        patient-name slugs). When the database cannot be read the file is left exactly as it was (exit 0) - the run goes on.
#   --items: a JSON list of rows (each with "id") or of ArtifactData documents ({id or doc_id, version, data}), either list under "items"
#        or "documents", a JSON object {id: row}, or the folder an ArtifactData list wrote (<dir>/items/<id>.json). stamp reads a file
#        that gives no row as no --items, and prints how many rows it gave.
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
ID_CHART_RE = re.compile(r"-(\d{4,9})$")
PAT_RE = re.compile(r"\bpat(\d{4,9})\b")
def _recent(y, m, d):
    try: datetime.date(y, m, d)
    except ValueError: return False
    return 2020 <= y <= 2039
def _date_shaped(n):
    """the date a sweep's card id ends with, never a chart number: mmdd (-1031), a year (-2026), mmddyy / yymmdd (-111226 / -261112),
    yyyymmdd / mmddyyyy (-20261112 / -11122026) - years 2020-2039 (the second review 11/12 added the year, the 6-digit forms and
    mmddyyyy). The chart numbers in the repository's records are 4 digits starting with 7 or 9, 5 digits, or 8 digits starting with 12
    or 17 - none of them date-shaped by this test."""
    if not n.isdigit(): return False
    if len(n) == 4: return (1 <= int(n[:2]) <= 12 and 1 <= int(n[2:]) <= 31) or 2020 <= int(n) <= 2039
    if len(n) == 6: return _recent(2000 + int(n[4:]), int(n[:2]), int(n[2:4])) or _recent(2000 + int(n[:2]), int(n[2:4]), int(n[4:]))
    if len(n) == 8: return _recent(int(n[:4]), int(n[4:6]), int(n[6:])) or _recent(int(n[4:]), int(n[:2]), int(n[2:4]))
    return False

def chart_ids_found(row, fallback=True):
    """(['pat<n>', ...], where) - every chart number on the card and where it was read. "": amdid (it may list several: '45447,
    17476874'; pid / chart are older spellings). A card with none of those (review 11/12: 37 of the 42 open cards left generic carried
    their chart elsewhere): "card id" - the number the id ends with (the prompts' id form last-first-<amdid>; a date-shaped ending is
    passed over), then "card text" - pat<n> written on the card. fallback=False reads amdid / pid / chart only: stamp passes it for a
    card it cannot see whole (an op's set alone - the stored card may carry an amdid the op does not repeat)."""
    out = []
    for k in ("amdid", "pid", "chart"):
        for n in re.findall(r"(?<!\d)(\d{4,9})(?!\d)", str((row or {}).get(k) or "")):
            if "pat" + n not in out: out.append("pat" + n)
    if out or not fallback: return out, ""
    m = ID_CHART_RE.search(str((row or {}).get("id") or ""))
    if m and not _date_shaped(m.group(1)): return ["pat" + m.group(1)], "card id"
    for n in PAT_RE.findall(all_text(row)):
        if "pat" + n not in out: out.append("pat" + n)
    return out, ("card text" if out else "")

def chart_ids(row, fallback=True): return chart_ids_found(row, fallback)[0]

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

CF_KEYS = ("name", "kind", "label", "dos", "cpt", "visit", "code", "how", "src", "at", "also", "res", "chart", "chart_from")
def _cf(name, kind, how, src, at, dos="", cpt="", visit="", code="", also=(), res=None, chart="", chart_from=None):
    """one chargefac with EVERY key of CF_KEYS, every time (review 11/12): the board applies a set with update(), which merges a nested
    object key by key, so a key left out keeps the earlier badge's value - a nursing-home badge written over a hospital one kept its
    'resident at' / 'also billed at' lines and `build` re-sent it forever. also [] and res / chart_from None say "none" outright
    (update() replaces anything that is not an object - a list, null - wholesale). chart: the card's chart number(s) the badge was worked
    out on (second review 11/12 - a badge stays over a weaker guess only while the card still has them)."""
    return {"name": name, "kind": kind, "label": KIND_LABEL.get(kind, ""), "dos": dos, "cpt": cpt, "visit": visit, "code": code,
            "how": how, "src": src, "at": at, "also": list(also)[:3], "res": res, "chart": chart, "chart_from": chart_from}

def _pick(lines, how, all_lines, now, chart_from=None, chart=""):
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
    also = []
    for c in sorted(named, key=lambda c: c["dos"], reverse=True):
        s = short(c["name"])
        if s != nm and s not in also: also.append(s)
    res = None
    if k not in RES_KINDS:
        homes = [c for c in all_lines if c["name"] and c["live"] and kind_of(c["name"]) in RES_KINDS]
        if homes:
            h = max(homes, key=lambda c: c["dos"]); hn = short(h["name"])
            last = max(c["dos"] for c in homes if short(c["name"]) == hn)
            res = {"name": hn, "kind": kind_of(h["name"]), "thru": _mm_yy(last)}
    return _cf(nm, k, how, "neon " + ("feed" if best["src"] == "feed" else "amd.charges"), now, dos=_mdy(best["dos"]), cpt=best["cpt"],
               visit=best["visit"], code=best["code"], also=also, res=res, chart=chart, chart_from=chart_from)

def _newest(cs):
    """the lines of the newest date of service among those with a facility - rules 4 and 6 speak for the chart's NEWEST charge, not
    for the facility most of its charges came from (review 11/12: a patient who moved showed the old facility)"""
    cs = [c for c in cs if c["name"]]
    d = max((c["dos"] for c in cs), default=None)
    return [c for c in cs if c["dos"] == d]

def charge_facility(row, charges, fac_codes, fac_names, now=None, fallback=True):
    """(chargefac or None, why). charges: chart -> lines (load_charges). fallback: see chart_ids_found."""
    now = now or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    charts, chart_from = chart_ids_found(row, fallback)
    chart_from = chart_from or None
    chart = ",".join(c[3:] for c in charts)                                       # the card's chart numbers, without 'pat'
    lines = [c for ch in charts for c in charges.get(ch, [])]
    ftext, ntext, ttext = facility_text(row), need_text(row), trail_text(row)
    if lines:
        vis = visit_numbers(all_text(row))
        hit = [c for c in lines if c["visit"] and c["visit"] in vis]
        if hit:
            cf = _pick(hit, "visit", lines, now, chart_from, chart)
            return (cf, "visit") if cf else (None, "the card's charge has no facility in AdvancedMD")
        for how, text in (("dos", ftext), ("dos", ntext)):
            spans = date_spans(text)
            hit = [c for c in lines if c["dos"] and any(a <= c["dos"] <= b for a, b in spans)]
            if hit:
                cf = _pick(hit, how, lines, now, chart_from, chart)
                return (cf, how) if cf else (None, "the card's charge has no facility in AdvancedMD")
    ids = [i for i in facility_ids(ftext + " \n " + ntext) if i != "1"]          # fac1 is AdvancedMD's "no facility"
    codes = sorted({fac_codes.get("fac" + i, "") for i in ids} - {""})
    if len(codes) == 1 and fac_names.get(codes[0]):
        nm = fac_names[codes[0]]
        return _cf(short(nm), kind_of(nm), "facility id", "neon chargedetail", now, code=codes[0], chart=chart), "facility id"
    if not charts: return None, "no chart number on the card"
    if not lines: return None, "no charge of the chart in the practice database"
    owed = _newest([c for c in lines if c["live"] and c["owed"]])
    cf = _pick(owed, "open balance", lines, now, chart_from, chart) if owed else None
    if cf: return cf, "open balance"
    spans = date_spans(ttext)
    hit = [c for c in lines if c["dos"] and any(a <= c["dos"] <= b for a, b in spans)]
    cf = _pick(hit, "dos in notes", lines, now, chart_from, chart) if hit else None
    if cf: return cf, "dos in notes"
    # second review 11/12: the chart's newest LIVE charge only - never a voided one, not even when no live charge has a facility (000d983c
    # fell back to all lines there and named a voided charge's facility as "the chart's newest charge"); the card then stays generic
    cf = _pick(_newest([c for c in lines if c["live"]]), "newest charge", lines, now, chart_from, chart)
    return (cf, "newest charge") if cf else (None, "no live charge of the chart has a facility in AdvancedMD")


# ---- the board rows ----------------------------------------------------------------------------------------------------------------
ROW_KEYS = {"amdid", "pid", "chart", "facility", "patient", "status", "need", "why", "notes", "chargefac"}
def _unwrap(d):
    """a board row: an ArtifactData document {id or doc_id, version, data} gives its data under the DOCUMENT's id (second review 11/12:
    a list of such documents lost every row - the id is outside data); anything else is taken as the row itself"""
    if isinstance(d, dict) and isinstance(d.get("data"), dict) and ({"version", "id", "doc_id"} & set(d)) and not (ROW_KEYS & set(d)):
        rid = d.get("id") or d.get("doc_id") or d["data"].get("id")
        return dict(d["data"], id=rid) if rid else dict(d["data"])
    return d
def rows_from_items(path):
    """--items: a list of rows or of ArtifactData documents (also under "items" / "documents"), an {id: row} object, or the folder an
    ArtifactData list wrote (<dir>/items/<id>.json or <dir>/<id>.json)"""
    if os.path.isdir(path):
        base = os.path.join(path, "items") if os.path.isdir(os.path.join(path, "items")) else path
        out = []
        for f in sorted(os.listdir(base)):
            if f.endswith(".json"):
                d = _unwrap(json.load(open(os.path.join(base, f), encoding="utf-8")))
                if isinstance(d, dict): out.append(dict(d, id=d.get("id") or f[:-5]))
        return out
    d = json.load(open(path, encoding="utf-8"))
    if isinstance(d, dict):
        for k in ("items", "documents"):
            if isinstance(d.get(k), list): d = d[k]; break
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

def compute(rows, select, now=None, fallback=None):
    """[(row, chargefac or None, why)] for every row. fallback: per row, whether its chart number may be read from its id / text
    (default: yes for every row - see chart_ids_found)"""
    fb = list(fallback) if fallback is not None else [True] * len(rows)
    fac_codes, fac_names = load_facilities(select)
    charts = sorted({c for r, f in zip(rows, fb) for c in chart_ids(r, f)})
    charges = load_charges(select, charts, fac_codes, fac_names)
    return [(r,) + charge_facility(r, charges, fac_codes, fac_names, now, f) for r, f in zip(rows, fb)]

GENERIC_RE = re.compile(r"^(SNF|ALF|NF|HCA|TMH)(\b|[\s/(])", re.I)          # the page's test for a place-of-service guess
def badge_source(row, cf):
    """what the card's badge shows once the file is applied - the page's facInfo() order. A stored badge worked out on a chart the card
    no longer has is not shown (third review 11/12, _on_card; the file clears it when nothing new is found - _clears)"""
    old = row.get("chargefac")
    if cf or (isinstance(old, dict) and old.get("name") and _on_card(old, row)): return "charge facility"
    fn = row.get("facnow")
    if isinstance(fn, dict) and fn.get("name"): return "newest visit (facnow)"
    if str(row.get("facilities") or "").strip(): return "facilities line"
    if row.get("lastfac"): return "last facility"
    t = str(row.get("facility") or "").strip()
    if t: return "generic" if GENERIC_RE.match(t) else "the card's own facility text"
    return "no facility at all"

def counts(results, include_done=False):
    """per part (open / done cards): how many get the charge's facility, by the rule of the badge each card ENDS UP with (third review
    11/12: a card that keeps its stored badge - _keeps - counts under that badge's rule, not under the weaker guess this run found;
    `kept` says how many); why the others do not; how many lose a badge worked out on a chart they no longer have (`cleared`); what each
    badge then shows (a done card left out of the file keeps the badge it has)"""
    c = collections.OrderedDict()
    for part, keep in (("open", lambda r: str(r.get("status") or "") != "done"), ("done", lambda r: str(r.get("status") or "") == "done")):
        sub = [(r, cf, why) for r, cf, why in results if keep(r)]
        applied = part == "open" or include_done
        fin = [_final(r, cf) for r, cf, _ in sub]
        c[part] = {"cards": len(sub), "specific": sum(1 for _, cf, _ in sub if cf), "generic": sum(1 for _, cf, _ in sub if not cf),
                   "by_rule": dict(collections.Counter(f.get("how") for f in fin if f).most_common()),
                   "kept": sum(1 for r, cf, _ in sub if cf and _keeps(r.get("chargefac"), cf)),
                   "cleared": sum(1 for r, cf, _ in sub if _clears(r, cf)),
                   "chart_from": dict(collections.Counter(f["chart_from"] for f in fin if f and f.get("chart_from")).most_common()),
                   "not_found_why": dict(collections.Counter(why for _, cf, why in sub if not cf).most_common()),
                   "in_file": applied,
                   "badge": dict(collections.Counter(badge_source(r, cf if applied else None) for r, cf, _ in sub).most_common())}
    return c


# ---- the commands -------------------------------------------------------------------------------------------------------------------
def _inside_repo(p): p = os.path.abspath(p); return p == REPO or p.startswith(REPO + os.sep)
def _now(): return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

GUESS = ("open balance", "dos in notes", "newest charge")    # rules that guess; visit / dos / facility id find a charge the card names
RANK = {"visit": 1, "dos": 2, "facility id": 3, "open balance": 4, "dos in notes": 5, "newest charge": 6}
def _charts_of(v): return [c.strip() for c in str(v or "").split(",") if c.strip()]
def _keeps(old, new):
    """True when a card's badge `old` stays and `new` is not written: `new` is only a guess (open balance / dos in notes / newest charge)
    from a weaker rule than the one that found `old` - a visit-matched badge is never replaced by the chart's newest charge - and the
    card still has every chart `old` was worked out on (new["chart"] is the card's charts now). A corrected chart number lets the new
    chart's result through (second review 11/12), and so does a badge that does not say its chart (no badge this helper writes). The
    board page's applyOp (keepsBadge) makes the same check with the row it holds when it applies the file - keep the two in step."""
    if not (isinstance(old, dict) and old.get("name")) or not isinstance(new, dict) or new.get("how") not in GUESS: return False
    if RANK[new["how"]] <= RANK.get(old.get("how"), 99): return False
    if not isinstance(old.get("chart"), str): return False
    now = _charts_of(new.get("chart"))
    return all(c in now for c in _charts_of(old["chart"]))

def _on_card(cf, row):
    """True while the card `row` still has EVERY chart the badge `cf` was worked out on (its `chart`) - third review 11/12: a chart
    number corrected with no new badge left the old chart's badge (its facility, visit, date and code - perhaps another patient's) on
    the card. The card's charts here are its own numbers (amdid / pid / chart): a card with none - matched through its id or text - and
    a badge that names no chart pass. The board page's cfOnCard() is the same test - facInfo shows a badge, and applyOp writes a file's
    badge, only while it holds - keep the two in step."""
    if not isinstance(cf, dict): return True
    was = _charts_of(cf.get("chart")) if isinstance(cf.get("chart"), str) else []
    now = [c[3:] for c in chart_ids(row, fallback=False)]
    return not (was and now) or all(c in now for c in was)

def _clears(row, cf):
    """no badge found now (cf None) and the card's stored badge was worked out on a chart it no longer has: the file writes chargefac
    null (the store's update() replaces null wholesale), so the old chart's badge does not stay in the card's data"""
    old = (row or {}).get("chargefac")
    return not cf and isinstance(old, dict) and bool(old.get("name")) and not _on_card(old, row)

def _final(row, cf):
    """the badge the card ends up with once a file built from cf is applied: its stored badge when that stays (_keeps), else cf"""
    old = (row or {}).get("chargefac")
    return old if cf and _keeps(old, cf) else cf

def build_file(results, stamp, now, include_done=False):
    ops = []
    for r, cf, _ in results:
        if not include_done and str(r.get("status") or "") == "done": continue
        if _clears(r, cf):                          # third review 11/12: nothing found now, and the stored badge is another chart's
            ops.append({"op": "update", "collection": "items", "id": r["id"], "set": {"chargefac": None}}); continue
        if not cf or _same(cf, r.get("chargefac")) or _keeps(r.get("chargefac"), cf): continue
        ops.append({"op": "update", "collection": "items", "id": r["id"], "set": {"chargefac": cf}})
    doc = {"schema": "irb-board-updates/1", "source": "tools/db/board_chargefac.py build %s (read-only on Neon)" % stamp, "created": now, "ops": ops}
    return board_ops.clean_file(doc)

def _creates(body):
    """the op creates its card: board_ops.plan_new_row's set carries `created`; the BOARD ACCESS RULE's new row carries patient and dob"""
    return "created" in body or ("patient" in body and "dob" in body)

def stamp_file(doc, select, now=None, items=None):
    """adds chargefac to every items row the run's file creates or whose facility / amdid it sets; returns [(id, chargefac written or
    None, why)]. items: the board's stored rows of the cards the file touches, as the run read them (--items; None or [] = not given).
    Review 11/12: an op alone is not the card - a card found in items is worked out from the whole card (its stored row, the op's set
    over it, notes / checks / api with the op's appends, as the page applies them) and keeps the badge it has (_keeps). Second review
    11/12: a card NOT found in items is not taken for a new card - items may be partial, empty or wrongly shaped - so its stored badge is
    unknown: it gets only a VISIT it names (third review 11/12: a date of service or facility id read from the op alone can be outranked
    by a visit the stored card names, and the page lets any named match replace another), worked out on the op's own amdid / pid / chart
    (never its id's number: the stored card may carry an amdid the op does not repeat), unless the op creates it (_creates). A card seen
    whole whose stored badge was worked out on a chart it no longer has, with nothing found on the chart it has now, gets chargefac null
    (third review 11/12 - cleared). A `replace` writes the whole row - the card's old badge goes with it - so it is always stamped.
    Whatever is written, the page keeps a stronger badge, and refuses a badge from a chart the card does not have, when it applies it."""
    board = {str(r.get("id")): r for r in (items or []) if isinstance(r, dict) and r.get("id")}
    targets = []
    for o in doc.get("ops") or []:
        if not isinstance(o, dict) or str(o.get("collection") or "items") != "items": continue
        kind = str(o.get("op") or "upsert").lower()
        body = o.get("data") if kind == "replace" else o.get("set")
        if not isinstance(body, dict) or not ({"amdid", "facility", "pid"} & set(body)) or body.get("chargefac"): continue
        rid = str(o.get("id") or "")
        cur = board.get(rid) if kind != "replace" else None
        whole = kind == "replace" or cur is not None              # the whole card is in hand: the replace's data, or the stored row
        new = not whole and kind != "update" and _creates(body)
        row = dict(cur or {}); row.update(body); row["id"] = rid
        if kind != "replace":
            app = o.get("append") if isinstance(o.get("append"), dict) else {}
            for k in ("notes", "checks", "api"):
                base = list(body[k]) if isinstance(body.get(k), list) else list((cur or {}).get(k) or [])
                add = app[k] if isinstance(app.get(k), list) else ([app[k]] if app.get(k) else [])
                for e in add:
                    if e not in base: base.append(e)
                row[k] = base
        targets.append((body, row, cur, whole, new))
    if not targets: return []
    results = compute([t[1] for t in targets], select, now, fallback=[t[3] for t in targets])
    out = []
    for (body, row, cur, whole, new), (_, cf, why) in zip(targets, results):
        old = (cur or {}).get("chargefac")
        if cf and not (whole or new) and cf["how"] != "visit":
            out.append((row["id"], None, "not written: %s read from the op alone - the card is not among the --items rows, so its own badge is not known%s"
                        % (("only a guess (%s)" % cf["how"]) if cf["how"] in GUESS else ("a %s match" % cf["how"]),
                           "" if cf["how"] in GUESS else " (a visit it names would outrank this)")))
        elif cf and _keeps(old, cf):
            out.append((row["id"], None, "kept the card's badge: found by a stronger rule (%s) than this guess (%s)" % (old.get("how"), cf["how"])))
        elif cf and _same(cf, old):
            out.append((row["id"], None, "kept the card's badge: the same facility"))
        elif not cf and cur is not None and isinstance(old, dict) and old.get("name") and not _on_card(old, row):
            body["chargefac"] = None                 # third review 11/12: the stored badge is another chart's - the store's update() clears it
            out.append((row["id"], None, "cleared: worked out on another chart"))
        else:
            if cf: body["chargefac"] = cf
            out.append((row["id"], cf, why))
    return out

def main(argv, select=None):
    select = select or neon_select
    a = list(argv)
    def opt(name, default=None): return a[a.index(name) + 1] if name in a and a.index(name) + 1 < len(a) else default
    cmd = a[0] if a and not a[0].startswith("--") else ""
    now = _now()
    if cmd == "stamp":
        path = opt("--file")
        if not path or not os.path.isfile(path): print("usage: board_chargefac.py stamp --file <board_updates_<stamp>.json> [--items <file|dir>]"); return 2
        doc = json.load(open(path, encoding="utf-8"))
        items = None
        if opt("--items"):
            try:
                items = rows_from_items(opt("--items"))
                # second review 11/12: say how many rows --items gave (a count only) - a file that gives none is read as no --items
                print("board_chargefac stamp: --items gave %d row(s)%s" % (len(items), "" if items else " - read as no --items"))
            except Exception as e:
                print("board_chargefac stamp: --items could not be read (%s) - read as no --items" % type(e).__name__)
            items = items or None
        before = json.dumps(doc, sort_keys=True)
        try: got = stamp_file(doc, select, now, items)
        except Exception as e:
            print("board_chargefac stamp: the practice database could not be read (%s) - %s left exactly as it was" % (str(e)[:160], os.path.basename(path)))
            return 0
        if json.dumps(doc, sort_keys=True) != before:   # a badge written, or (third review 11/12) another chart's badge cleared
            with open(path, "w", encoding="utf-8") as f: json.dump(doc, f, indent=1, ensure_ascii=False)
        # counts only (review 11/12): a row id is a patient-name slug (last-first-<amdid>), and this output lands in the run's transcript
        print("board_chargefac stamp %s: %d row(s) looked at, %d given the charge's facility%s" % (os.path.basename(path), len(got),
              sum(1 for _, cf, _ in got if cf), "" if items is not None else " (no --items rows: a card already on the board gets only a visit it names)"))
        print("  by rule: %s" % json.dumps(dict(collections.Counter(why for _, cf, why in got if cf).most_common())))
        print("  not given: %s" % json.dumps(dict(collections.Counter(why for _, cf, why in got if not cf).most_common())))
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
        if v["chart_from"]: print("    chart number read from the card's id / text (no amdid on the card): %s" % json.dumps(v["chart_from"]))
        # third review 11/12: plan says these too (it said only what this run found, so a card keeping its visit badge read as a guess)
        if v["in_file"] and v["kept"]:
            print("    %d card(s) keep the badge they have: found by a stronger rule than this run's guess, on a chart they still have (counted under that rule)" % v["kept"])
        if v["in_file"] and v["cleared"]:
            print("    %d card(s) lose a badge worked out on a chart they no longer have (nothing found on the chart they have now)" % v["cleared"])
        print("    the badge then shows%s: %s" % ("" if v["in_file"] else " (done cards are left out of the file - --all adds them)", json.dumps(v["badge"])))
    if cmd == "plan": return 0
    stamp = re.sub(r"[^0-9A-Za-z\-]", "", opt("--stamp") or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H%MZ"))
    doc = build_file(results, stamp, now, include_done="--all" in a)
    os.makedirs(out, exist_ok=True)
    name = os.path.join(out, "board_updates_%s.json" % stamp)
    with open(name, "w", encoding="utf-8") as f: json.dump(doc, f, indent=1, ensure_ascii=False)
    given = sum(1 for o in doc["ops"] if isinstance(o["set"].get("chargefac"), dict))
    lost = len(doc["ops"]) - given
    print("board_chargefac build: %d card(s) get the charge's facility%s -> %s (not delivered: the board applies it once it is in the Drive folder 'board inbox')"
          % (given, (", %d lose a badge worked out on a chart they no longer have" % lost) if lost else "", name))
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
