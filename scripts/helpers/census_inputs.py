# PLAIN ENGLISH (census inputs - William 11/11/2026: "daily census inputs can be the app, or section, and claimocity feed will be one of
#   the sections in that category ... the claimocity integration is the best electronic input for a practice to input a census, but not
#   the only way a practice can send in daily census reports with the relevant information date patient name location and code").
# The category is CENSUS INPUTS. Its sections, by weight:
#   claimocity_feed   the Claimocity feed - electronic, entered by the feed step, THE RECORD (it is never saved through this helper);
#   claimocity_app    a screenshot of the Claimocity app's census list (room, name, visit code, clinician);
#   hospital_census   a hospital or facility census list - a picture, a scan or a fax (room, name, birth date, record number, admit date);
#   ortho_fax         the ortho report that arrives by fax;
#   practice_census   the daily census a practice sends in - a fax, a scan or an upload (who was seen, on what date, where, which code).
#   Every one carries the same kind of information: the date, the patient's name, the location, the code, and whatever else the page has.
#   The other sections SUPPORT the feed and stand in for it when it is not available - "the claimocity feed takes the paramount importance".
# Decides: nothing about a charge. Three commands, all in the workspace, none of them talks to AdvancedMD:
#   save     takes what a session READ from one picture or PDF (a census/1 record, see problems() below) and saves it under its day - only
#            when it is well formed. A cell the page did not show clearly is listed under "unread", never guessed; a note, a reason for a
#            visit or handwriting is not kept at all. The record is tied to the exact file (sha256), so the same file sent twice is read once.
#   status   one line per file read, with its Drive ids - so a run can tell which uploads in the census folder are new.
#   compare  puts the censuses of a day beside the Claimocity feed of that day and the same kind of place. THE FEED IS THE RECORD: where
#            they differ the feed's code stands and the difference is listed for a person - on both (same code / another code), on the
#            census only, in the feed only. The feed brings charges a day or two after the visit, so a day is called "nothing yet" for
#            three days; after that a census with no feed is the worklist, at the top of the report. NO ROUTINE ENTERS A VISIT FROM A CENSUS.
# Where things go: the census itself, with names, stays in the workspace (census/<day>/...json, and census_check_<day>.md for William -
#   Drive "chat history" with the run digest). GitHub gets registers/census_inputs.json and registers/census_check_<day>.json: counts,
#   chart ids, file and row numbers - never a patient name, a date of birth, a room or a file name.
# Never touches: AdvancedMD, the feed's own files and registers (read only), Drive, Gmail. Standard library only.
# Usage (workspace = BILLING_WORKSPACE, else /home/claude/unbilled):
#   python3 census_inputs.py save <record.json> --file <the picture or PDF it was read from> [--drive-id <id>] [--replace]
#   python3 census_inputs.py status
#   python3 census_inputs.py compare --date YYYY-MM-DD | --recent <days>
import os, sys, re, json, glob, hashlib, datetime, collections
WS = os.environ.get("BILLING_WORKSPACE", "/home/claude/unbilled")
CATEGORY = "Census inputs"
SECTIONS = {      # the sections of the category, the record first
    "claimocity_feed": "Claimocity feed (electronic - the record)",
    "claimocity_app": "Claimocity app census list (a screenshot)",
    "hospital_census": "Hospital or facility census list (a picture, a scan or a fax)",
    "ortho_fax": "Ortho report (a fax)",
    "practice_census": "Daily census a practice sends in (a fax, a scan or an upload)",
}
PLACES = ("hospital", "nursing", "home", "office")      # the kind of place a census is for: it is compared with the feed's visits of that kind
FIELDS = ("n", "name", "dob", "room", "mrn", "visit_no", "admit", "attending", "clinician", "code", "more_codes", "unread")
UNREADABLE = ("name", "dob", "room", "mrn", "visit_no", "admit", "attending", "clinician", "code")      # the cells a row may list under "unread"
RECORD_KEYS = ("schema", "source", "practice", "date", "place", "facility", "rows", "pages", "received")
# the feed's visit codes by kind of place (the same families claimocity_import.py reads); care management is no visit on a census
FAMILY = {"hospital": set("99221 99222 99223 99231 99232 99233 99234 99235 99236 99238 99239".split()),
          "nursing": set("99304 99305 99306 99307 99308 99309 99310 99315 99316".split()),
          "home": set("99341 99342 99344 99345 99347 99348 99349 99350".split()),
          "office": set("99202 99203 99204 99205 99211 99212 99213 99214 99215".split())}
WAIT_DAYS = 3      # the feed brings charges a day or two after the visit: a census day is compared again until it is this many days old
NOT_ENTERED = "no routine enters a visit from a census"

def _day(s):
    """a date written YYYY-MM-DD, else None"""
    try: return datetime.datetime.strptime(s, "%Y-%m-%d").date() if isinstance(s, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", s) else None
    except ValueError: return None
def today():
    return _day(os.environ.get("CENSUS_TODAY", "")) or datetime.datetime.now(datetime.timezone.utc).date()
def problems(rec):
    """Why a census record cannot be saved ([] = it can). A record is what a session wrote after reading ONE picture or PDF:
    {"schema": "census/1", "source", "practice", "date", "place", "facility", "rows": [{"n", "name", ...}]} - nothing else."""
    out = []
    if not isinstance(rec, dict): return ["the record is not an object"]
    if rec.get("schema") != "census/1": out.append('schema must be "census/1"')
    if rec.get("source") not in SECTIONS or rec.get("source") == "claimocity_feed": out.append("source must be one of %s" % ", ".join(s for s in SECTIONS if s != "claimocity_feed"))
    if _day(rec.get("date")) is None: out.append("date must be the census day written YYYY-MM-DD")
    if rec.get("place") not in PLACES: out.append("place must be one of %s" % ", ".join(PLACES))
    if not (isinstance(rec.get("facility"), str) and rec["facility"].strip()): out.append("facility must be the building's name as the page prints it")
    if not (isinstance(rec.get("practice", "ehpa"), str) and re.fullmatch(r"[a-z0-9_]{2,20}", rec.get("practice", "ehpa"))): out.append("practice must be the practice's short code")
    for k in rec:
        if k not in RECORD_KEYS: out.append("the record keeps nothing but %s (found: %s)" % (", ".join(RECORD_KEYS), k))
    rows = rec.get("rows")
    if not (isinstance(rows, list) and 1 <= len(rows) <= 500): return out + ["rows must be a list of 1 to 500 rows"]
    seen = set()
    for i, r in enumerate(rows, 1):
        w = "row %d" % i
        if not isinstance(r, dict): out.append("%s is not an object" % w); continue
        for k in r:
            if k not in FIELDS: out.append("%s keeps a field this helper does not keep (%s) - a note, a reason for a visit or handwriting is never saved" % (w, k))
        un = r.get("unread", [])
        if not (isinstance(un, list) and all(u in UNREADABLE for u in un)): out.append("%s: unread must list cells out of %s" % (w, ", ".join(UNREADABLE))); un = []
        if not (isinstance(r.get("n"), int) and not isinstance(r.get("n"), bool) and r["n"] >= 1) or r.get("n") in seen: out.append("%s: n must be the row's own place on the page, counted from 1" % w)
        seen.add(r.get("n"))
        if not (isinstance(r.get("name"), str) and name_key(r["name"])[0]) and "name" not in un: out.append("%s has no name and does not say the name could not be read" % w)
        if r.get("code") is not None and not (isinstance(r["code"], str) and re.fullmatch(r"[0-9A-Z]{5}", r["code"])): out.append("%s: code must be a five-character code or left out" % w)
        if r.get("code") is not None and "code" in un: out.append("%s gives a code and says the code could not be read" % w)
        for k in ("dob", "admit"):
            if r.get(k) is not None and _day(r[k]) is None: out.append("%s: %s must be a day written YYYY-MM-DD or left out" % (w, k))
        for k in ("room", "mrn", "visit_no", "attending", "clinician"):
            if r.get(k) is not None and not (isinstance(r[k], str) and len(r[k]) <= 80): out.append("%s: %s must be a short text or left out" % (w, k))
        if r.get("more_codes") is not None and not (isinstance(r["more_codes"], int) and 0 <= r["more_codes"] <= 9): out.append("%s: more_codes must be a small number" % w)
    return out
def name_key(name):
    """(family name, first given name) in capital letters only - what two lists must agree on to be one patient. Punctuation inside a name,
    a middle initial, a second given name and a preferred name in brackets do not count; the family name stands before the comma."""
    s = re.sub(r"\([^)]*\)", " ", str(name or "")).upper()
    last, _, rest = s.partition(",")
    first = (rest.split() or [""])[0]
    return re.sub(r"[^A-Z]", "", last), re.sub(r"[^A-Z]", "", first)
def _load(p, default):
    try: return json.load(open(p))
    except Exception: return default
REGF = os.path.join("registers", "census_inputs.json")
def _register():
    r = _load(os.path.join(WS, REGF), None)
    return r if isinstance(r, dict) and isinstance(r.get("files"), dict) else {"schema": "census-inputs/1", "category": CATEGORY, "files": {}}
def _saved_path(e, sha): return os.path.join(WS, "census", e["date"], "%s_%s.json" % (e["source"], sha[:8]))

# ---- save -----------------------------------------------------------------------------------------------------------------------------
def save(argv):
    if not argv or "--file" not in argv: print("usage: census_inputs.py save <record.json> --file <picture or PDF> [--drive-id <id>] [--replace]"); return 2
    recp = argv[0]; filep = argv[argv.index("--file") + 1] if argv.index("--file") + 1 < len(argv) else ""
    drive = argv[argv.index("--drive-id") + 1] if "--drive-id" in argv and argv.index("--drive-id") + 1 < len(argv) else ""
    for p, what in ((recp, "the record"), (filep, "the file it was read from")):
        if not os.path.isfile(p): print("NOT SAVED: %s is not there (%s)" % (what, os.path.basename(p) or "no path given")); return 2
    try: rec = json.load(open(recp))
    except Exception as e: print("NOT SAVED: the record cannot be read as JSON (%s)" % type(e).__name__); return 2
    bad = problems(rec)
    if bad:
        print("NOT SAVED: %d problem(s) in the record - correct what was read and save again" % len(bad))
        for b in bad[:20]: print("  - " + b)
        return 2
    sha = hashlib.sha256(open(filep, "rb").read()).hexdigest(); reg = _register(); old = reg["files"].get(sha)
    rows = rec["rows"]
    entry = {"source": rec["source"], "practice": rec.get("practice", "ehpa"), "date": rec["date"], "place": rec["place"], "rows": len(rows),
             "with_code": sum(1 for r in rows if r.get("code")), "with_dob": sum(1 for r in rows if r.get("dob")), "unread": sum(len(r.get("unread") or []) for r in rows),
             "drive_ids": list((old or {}).get("drive_ids") or []), "read": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    if drive and drive not in entry["drive_ids"]: entry["drive_ids"].append(drive)
    if old:
        same = _load(_saved_path(old, sha), {}).get("rows") == rows and all(old.get(k) == entry[k] for k in ("source", "date", "place"))
        if same or "--replace" not in argv:
            if same:
                old["drive_ids"] = entry["drive_ids"]; _write_register(reg)
                print("census already saved: file %s was read before (%s %s %s, %d row(s)) - the same content, noted and not read again" % (sha[:8], old["source"], old["date"], old["place"], old["rows"])); return 0
            print("NOT SAVED: file %s was already read (%s %s, %d row(s)) and this reading differs - give --replace to put this reading in its place" % (sha[:8], old["source"], old["date"], old["rows"])); return 2
        if _saved_path(old, sha) != _saved_path(entry, sha) and os.path.exists(_saved_path(old, sha)): os.remove(_saved_path(old, sha))
    dest = _saved_path(entry, sha); os.makedirs(os.path.dirname(dest), exist_ok=True)
    json.dump(dict({k: rec[k] for k in RECORD_KEYS if k in rec}, practice=entry["practice"], file={"sha256": sha, "drive_ids": entry["drive_ids"]}), open(dest, "w"), indent=1)
    reg["files"][sha] = entry; _write_register(reg)
    print("census saved: %s %s %s - %d row(s) (%d with a code, %d with a birth date, %d cell(s) could not be read) from file %s" % (
        entry["source"], entry["date"], entry["place"], entry["rows"], entry["with_code"], entry["with_dob"], entry["unread"], sha[:8]))
    return 0
def _write_register(reg):
    os.makedirs(os.path.join(WS, "registers"), exist_ok=True); json.dump(reg, open(os.path.join(WS, REGF), "w"), indent=1, sort_keys=True)
def status(argv):
    reg = _register()
    if not reg["files"]: print("census inputs: no census read yet"); return 0
    for sha, e in sorted(reg["files"].items(), key=lambda kv: (kv[1].get("date", ""), kv[0])):
        print("%s %s %s %s %d row(s) drive: %s" % (sha[:8], e.get("source"), e.get("date"), e.get("place"), e.get("rows") or 0, ", ".join(e.get("drive_ids") or []) or "-"))
    return 0

# ---- compare ---------------------------------------------------------------------------------------------------------------------------
def _feed(day):
    """The Claimocity feed's visits of one day, per feed patient: {feed id: {"codes", "chart", "name", "dob"}}; and whether any feed file is on hand.
    Counts, codes and charts come from the feed's reconciliation registers (they are on main); names and birth dates from the parsed feed
    files, which stay in a workspace and are missing on a fresh machine - then only counts and codes can be compared."""
    iso = day.isoformat(); ymd = day.strftime("%Y%m%d"); out = {}; on_hand = False
    for f in sorted(glob.glob(os.path.join(WS, "registers", "feed_recon_*.json"))):
        rows = _load(f, {}).get("rows") if isinstance(_load(f, {}), dict) else None
        if not isinstance(rows, list): continue
        on_hand = True
        for r in rows:
            if isinstance(r, dict) and r.get("d") == iso and r.get("f"):
                v = out.setdefault(str(r["f"]), {"codes": set(), "chart": None, "name": None, "dob": None})
                v["codes"] |= {str(c) for c in r.get("c") or []}; v["chart"] = v["chart"] or r.get("p")
    for f in sorted(glob.glob(os.path.join(WS, "feed_parsed_*.json"))):
        msgs = _load(f, [])
        if not isinstance(msgs, list): continue
        on_hand = True
        for m in msgs:
            if not (isinstance(m, dict) and m.get("pid")): continue
            codes = {str(c.get("cpt")) for c in m.get("FT1") or [] if isinstance(c, dict) and str(c.get("dos") or "")[:8] == ymd and c.get("cpt")}
            if not codes: continue
            v = out.setdefault(str(m["pid"]), {"codes": set(), "chart": None, "name": None, "dob": None})
            v["codes"] |= codes; v["name"] = v["name"] or m.get("name")
            d = re.sub(r"\D", "", str(m.get("dob") or ""))[:8]
            v["dob"] = v["dob"] or ("%s-%s-%s" % (d[:4], d[4:6], d[6:8]) if len(d) == 8 else None)
    return out, on_hand
def _people(files):
    """The censuses of one day and one kind of place read as ONE list: [{"key", "name", "dob", "code", "where": (file, row)}], a patient two
    censuses name counted once (the app list gives the code, the hospital's list the birth date); a row whose name could not be read stays alone."""
    order = list(SECTIONS); people = {}; lone = []
    for sha, e, rec in sorted(files, key=lambda x: (order.index(x[1]["source"]), x[0])):
        for r in rec.get("rows") or []:
            k = name_key(r.get("name")) if r.get("name") else ("", "")
            p = people.get(k) if k[0] else None
            if p is None:
                p = {"key": k, "name": r.get("name") or "(name could not be read)", "dob": None, "code": None, "where": (sha[:8], r.get("n"))}
                if k[0]: people[k] = p
                else: lone.append(p)
            p["dob"] = p["dob"] or r.get("dob"); p["code"] = p["code"] or r.get("code")
    return list(people.values()) + lone
def compare_day(day, reg, now):
    iso = day.isoformat(); age = (now - day).days; lines = []; top = []; md = ["# Census check %s - for William (names stay in the workspace and the run digest; the feed is the record)" % iso, ""]
    feed, on_hand = _feed(day); result = {"schema": "census-check/1", "category": CATEGORY, "date": iso, "today": now.isoformat(), "places": {}}
    by_place = collections.defaultdict(list)
    for sha, e in reg["files"].items():
        if e.get("date") == iso:
            rec = _load(_saved_path(e, sha), None)
            if isinstance(rec, dict): by_place[e.get("place")].append((sha, e, rec))
    for place in [p for p in PLACES if p in by_place]:
        people = _people(by_place[place]); visits = {f: v for f, v in feed.items() if v["codes"] & FAMILY[place]}
        named = bool(visits) and all(v["name"] for v in visits.values())
        res = {"census_files": len(by_place[place]), "census_rows": len(people), "feed_visits": len(visits), "names_compared": named,
               "census_codes": dict(sorted(collections.Counter(p["code"] for p in people if p["code"]).items())),
               "feed_codes": dict(sorted(collections.Counter(c for v in visits.values() for c in v["codes"]).items())),
               "both": None, "code_differs": [], "dob_differs": 0, "census_only": [], "feed_only": [],
               "feed_state": "present" if visits else ("not known" if not on_hand else "nothing yet" if age < WAIT_DAYS else "not available")}
        head = "census check %s %s: census %d patient(s) from %d file(s) | feed %d visit(s)" % (iso, place, len(people), len(by_place[place]), len(visits))
        md += ["## %s - %d on the census (%d file(s)), %d in the feed" % (place, len(people), len(by_place[place]), len(visits)), ""]
        if not visits:
            if res["feed_state"] == "not available":
                lines.append(head + " | the feed has brought nothing for this day - the census is the worklist")
                top.append("  - TOP OF THE REPORT - CENSUS WITHOUT A FEED: %s (%s) - the Claimocity feed has brought no visit for that day and the census lists %d patient(s): the census is the worklist "
                           "(the names are in census/%s/census_check_%s.md in the workspace and in the run digest) - William says how these visits are entered; %s" % (iso, place, len(people), iso, iso, NOT_ENTERED))
                md += ["The Claimocity feed has brought no visit for this day. The census is the worklist - William says how these visits are entered; %s:" % NOT_ENTERED, ""]
                md += ["- %s%s%s" % (p["name"], (" - born %s" % p["dob"]) if p["dob"] else "", (" - %s" % p["code"]) if p["code"] else "") for p in people] + [""]
            elif res["feed_state"] == "nothing yet": lines.append(head + " | the feed has nothing yet for this day (charges arrive a day or two after the visit) - compared again at the next run")
            else: lines.append(head + " | the feed's registers are not on hand in this workspace - not compared")
        elif not named:
            lines.append(head + " | names not on hand (the parsed feed files are not in this workspace) - counts and codes only: census %s, feed %s" % (
                " ".join("%sx%d" % kv for kv in res["census_codes"].items()) or "no codes", " ".join("%sx%d" % kv for kv in res["feed_codes"].items())))
            md += ["The feed's names are not on hand in this workspace: counts and codes only.", ""]
        else:
            fkey = {}
            for f, v in visits.items(): fkey.setdefault(name_key(v["name"]), []).append(f)
            used = set(); both = 0; only = []; differs = []; dobs = []
            for p in people:
                fs = [f for f in fkey.get(p["key"], []) if f not in used] if p["key"][0] else []
                if not fs: only.append(p); continue
                f = fs[0]; used.add(f); v = visits[f]; both += 1
                if p["code"] and p["code"] not in v["codes"]: differs.append((p, f, v))
                if p["dob"] and v["dob"] and p["dob"] != v["dob"]: dobs.append((p, f, v))
            fonly = [(f, v) for f, v in sorted(visits.items()) if f not in used]
            res.update(both=both, dob_differs=len(dobs), census_only=[{"file": p["where"][0], "n": p["where"][1]} for p in only],
                       code_differs=[{"chart": v["chart"], "feed": f, "census_code": p["code"], "feed_codes": sorted(v["codes"]), "stands": "feed"} for p, f, v in differs],
                       feed_only=[{"chart": v["chart"], "feed": f, "codes": sorted(v["codes"])} for f, v in fonly])
            lines.append(head + " | on both %d (code differs %d) | census only %d | feed only %d%s" % (both, len(differs), len(only), len(fonly), (" | birth date differs %d" % len(dobs)) if dobs else ""))
            if only and age >= WAIT_DAYS:
                top.append("  - TOP OF THE REPORT - ON THE CENSUS, NOT IN THE FEED: %d patient(s) on %s (%s) are on a census and have no visit in the Claimocity feed, which did bring that day's visits - possible missed charges, "
                           "for William (the names are in census/%s/census_check_%s.md in the workspace and in the run digest); %s" % (len(only), iso, place, iso, iso, NOT_ENTERED))
            md += ["On the census only (no visit in the feed - a missed charge, or not seen that day):"] + ["- %s%s%s" % (p["name"], (" - born %s" % p["dob"]) if p["dob"] else "", (" - census code %s" % p["code"]) if p["code"] else "") for p in only] + [""]
            md += ["In the feed only (on no census of that day):"] + ["- %s (%s) - %s" % (v["name"], v["chart"] or f, " ".join(sorted(v["codes"]))) for f, v in fonly] + [""]
            md += ["Code differs (the feed is the record - its code stands):"] + ["- %s (%s): census %s, feed %s" % (p["name"], v["chart"] or f, p["code"], " ".join(sorted(v["codes"]))) for p, f, v in differs] + [""]
            md += ["Same name, but the birth date differs between the census and the feed (taken as one patient - a person checks the chart):"] + ["- %s (%s): census %s, feed %s" % (p["name"], v["chart"] or f, p["dob"], v["dob"]) for p, f, v in dobs] + [""]
        result["places"][place] = res
    if not result["places"]: return ["census check %s: no census saved for that day" % iso], [], None
    os.makedirs(os.path.join(WS, "registers"), exist_ok=True); os.makedirs(os.path.join(WS, "census", iso), exist_ok=True)
    json.dump(result, open(os.path.join(WS, "registers", "census_check_%s.json" % iso), "w"), indent=1)
    open(os.path.join(WS, "census", iso, "census_check_%s.md" % iso), "w").write("\n".join(md) + "\n")
    return lines, top, result
def compare(argv):
    reg = _register(); now = today()
    if "--date" in argv and argv.index("--date") + 1 < len(argv):
        d = _day(argv[argv.index("--date") + 1])
        if d is None: print("census check: the date must be written YYYY-MM-DD"); return 2
        days = [d]
    elif "--recent" in argv and argv.index("--recent") + 1 < len(argv) and argv[argv.index("--recent") + 1].isdigit():
        n = int(argv[argv.index("--recent") + 1])
        days = sorted({_day(e.get("date")) for e in reg["files"].values() if _day(e.get("date")) and 0 <= (now - _day(e.get("date"))).days <= n})
        if not days: print("census check: no census saved for the last %d day(s)" % n); return 0
    else: print("usage: census_inputs.py compare --date YYYY-MM-DD | --recent <days>"); return 2
    tops = []
    for d in days:
        lines, top, _res = compare_day(d, reg, now)
        for l in lines: print(l)
        tops += top
    for t in tops: print(t)
    return 0
def main(argv):
    global WS
    WS = os.environ.get("BILLING_WORKSPACE", "/home/claude/unbilled")      # read at every start, not when the file is loaded
    cmd = argv[0] if argv else ""
    if cmd == "save": return save(argv[1:])
    if cmd == "status": return status(argv[1:])
    if cmd == "compare": return compare(argv[1:])
    print("usage: census_inputs.py save <record.json> --file <picture or PDF> [--drive-id <id>] [--replace] | status | compare --date YYYY-MM-DD | compare --recent <days>")
    return 2
if __name__ == "__main__": sys.exit(main(sys.argv[1:]))
