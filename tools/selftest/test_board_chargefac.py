#!/usr/bin/env python3
# PLAIN ENGLISH (offline self-test, 11/12/2026): tools/db/board_chargefac.py and the board page's badge - the facility each Insurance
#   Refresh Board card's charge came from (William: "there should always be a facility to list there where the charge came from").
# Decides: nothing. With a STAND-IN for the practice database (no network) it proves that the helper:
#   - only ever sends SELECT statements (anything else is refused before it leaves);
#   - maps a card to its charge in the documented order - a visit named on the card, a date of service in the facility text or the
#     need (single dates, m/d-m/d/yyyy spans, m/d + m/d/yyyy pairs), one facility id in the text, the chart's charge still owing, the
#     chart's newest charge - and names the facility most of those charges came from, the others as `also`, where a hospital patient
#     lives as `res`; a feed visit the history lacks is named through its facility id;
#   - leaves a card generic only when no facility can be found: no chart number, or the named charge has no facility in AdvancedMD;
#   - writes ONE board_updates_<stamp>.json (irb-board-updates/1): `update` ops that set only `chargefac`, never `updated`, only for
#     open cards whose charge facility is new or changed (--all adds done cards), and refuses an output folder inside the repository;
#   - stamps a run's own board file (new rows and rows whose facility it sets) and leaves it byte for byte when the database fails;
#   - reads board rows given as a list, an {id: row} object or an ArtifactData folder.
# And that the board page (boards/templates/tracker.html, run in node when node is installed) shows the charge's facility first,
#   keeps facnow / the facilities line / lastfac next, shows a generic SNF only when nothing names a facility, classifies facility
#   names like the helper does, and still carries the live page's other behaviour.
# Never touches: Neon, AdvancedMD, the board, Drive, the network. Nothing is started as a program but node on a temporary copy of the
#   page's badge code. No patient data: every chart, visit, facility and card is invented.
# Run: python3 tools/selftest/test_board_chargefac.py   (exit 1 on any failure)
import os, sys, re, io, json, shutil, tempfile, subprocess, contextlib, importlib.util
import socket as _socket
def _no_network(*a, **k): raise RuntimeError("the self-test must not use the network")
_socket.socket.connect = _no_network; _socket.socket.connect_ex = _no_network; _socket.create_connection = _no_network
sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PATH = os.path.join(ROOT, "tools", "db", "board_chargefac.py")
PAGE = os.path.join(ROOT, "boards", "templates", "tracker.html")
FAILS = []; RAN = [0]
def check(name, cond, extra=""):
    RAN[0] += 1
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else "  -> " + str(extra)[:700]))
    if not cond: FAILS.append(name)
src = open(PATH, encoding="utf-8").read() if os.path.exists(PATH) else ""
names = {m.split()[0].split(".")[0] for k, r in re.findall(r"^(import|from)[ \t]+([^\n#;]+)", src, re.M) for m in (r.split(",") if k == "import" else [r]) if m.strip()}
check("the helper is there and loads the standard library and board_ops only (nothing that talks to AdvancedMD)",
      src != "" and names <= {"os", "sys", "re", "json", "datetime", "collections", "urllib", "board_ops"}, sorted(names))
if FAILS: print("\ntest_board_chargefac: %d checks, %d failed" % (RAN[0], len(FAILS))); sys.exit(1)
def snapshot():
    out = {}
    for dp, dn, fn in os.walk(ROOT):
        dn[:] = [x for x in dn if x != ".git"]
        for f in fn:
            try: out[os.path.join(dp, f)] = os.stat(os.path.join(dp, f)).st_mtime_ns
            except OSError: pass
    return out
BEFORE = snapshot()
spec = importlib.util.spec_from_file_location("board_chargefac_t", PATH); B = importlib.util.module_from_spec(spec); spec.loader.exec_module(B)

# ---- the stand-in database (everything invented)
def ch(n): return "%d" % (9700000 + n)
NAMES = {"INV1": "INVENTED NURSING AND REHABILITATION CENTER", "INVH": "INVENTED GENERAL HOSPITAL", "INVA": "INVENTED GARDENS ALF", "INVS": "INVENTED SOUTHWOOD"}
FACIDS = [("fac901", "INV1", "50"), ("fac902", "INVH", "40"), ("fac902", "INVX", "1"), ("fac903", "INVA", "30"), ("fac904", "INVS", "20"), ("fac1", "", "5")]
def line(n, visit, dos, cpt, code, live="true", ins="0.00", pat="0.00"):
    return ["pat" + ch(n), "c" + visit, visit, dos, cpt, code, NAMES.get(code, ""), live, ins, pat]
CHARGES = [
    line(1, "19999001", "2026-10-02", "99309", "INV1"), line(1, "19999002", "2026-10-20", "99233", "INVH"),
    line(2, "19999011", "2026-11-04", "99309", "INVS"), line(2, "19999012", "2026-10-05", "99309", "INVS"), line(2, "19999013", "2026-09-01", "99223", "INVH"),
    line(3, "19999021", "2026-08-05", "99223", "INVH"), line(3, "19999022", "2026-08-06", "99233", "INVH"), line(3, "19999023", "2026-08-10", "99233", "INVH"),
    line(3, "19999024", "2026-08-17", "99238", "INVH"), line(3, "19999025", "2026-08-23", "99487", "INVA"),
    line(5, "19999041", "2025-03-01", "99349", "INVA"), line(5, "19999042", "2026-07-01", "99309", "INV1", ins="120.00"), line(5, "19999043", "2026-09-01", "99349", "INVA"),
    line(6, "19999051", "2026-06-01", "99349", "INVA"), line(6, "19999052", "2026-07-01", "99233", "INVH", live="false"),
    line(7, "19999070", "2026-10-11", "99309", ""), line(7, "19999071", "2026-10-12", "99309", "INV1"),
    line(9, "19999080", "2026-01-01", "99309", "INV1"),
    line(10, "19999100", "2026-09-09", "99309", "INV1"), line(11, "19999110", "2026-09-10", "99309", "INV1"),
    line(12, "19999121", "2026-10-01", "99309", "INV1"), line(13, "19999131", "2026-10-03", "99309", "INV1"),
    line(14, "19999140", "2026-10-14", "99309", ""), line(14, "19999141", "2026-10-20", "99349", "INVA", ins="80.00"),
]
FEED = [["pat" + ch(9), "vst19999090", "2026-11-08", "99223", "fac903", "Invented Gardens (feed spelling)"],
        ["pat" + ch(1), "vst19999001", "2026-10-02", "99309", "fac902", "should not replace the history's line"]]
CARDS = {
    "card-a": {"amdid": ch(1), "status": "william", "facility": "SNF", "need": "Medicare denied the 10/2 visit v19999001 (99309)."},
    "card-b": {"amdid": ch(2), "status": "claude", "facility": "SNF (99309 11/4/2026 + 10/5/2026, fac901)", "need": "Released."},
    "card-c": {"amdid": ch(3), "status": "william", "facility": "HCA hospital inpatient 8/5-8/17/2026; CCM 8/23/2026", "need": "Secondary never answered."},
    "card-d": {"amdid": "", "status": "claude", "facility": "HCA REHAB (TALLAHASSEE) - AMD facility fac902", "need": "Enrollment."},
    "card-e": {"amdid": ch(5), "status": "william", "facility": "ALF / home", "need": "Which plan pays?"},
    "card-f": {"amdid": ch(6), "status": "claude", "facility": "", "need": "Nothing named here."},
    "card-g": {"amdid": ch(7), "status": "william", "facility": "SNF (fac1)", "need": "Visit v19999070 has no facility on it."},
    "card-h": {"amdid": "", "status": "claude", "facility": "ALF / SNF (CCM) - various", "need": "Watching."},
    "card-i": {"amdid": ch(9), "status": "william", "facility": "HCA", "need": "The feed visit vst19999090 waits for a plan."},
    "card-j": {"amdid": ch(10), "status": "done", "facility": "SNF (99309 9/9/2026)", "need": "Done."},
    "card-k": {"amdid": ch(11), "status": "claude", "facility": "SNF (99309 9/10/2026)", "need": "Released."},
    "card-l": {"amdid": "%s, %s" % (ch(12), ch(13)), "status": "claude", "facility": "SNF / ALF", "need": "visits 19999121 / 19999131 re-sent."},
    "card-m": {"amdid": ch(14), "status": "william", "facility": "SNF (99309 10/14/2026)", "need": "Unbilled."},
}
SQL = []
def select(sql, params=()):
    SQL.append(sql)
    if not re.match(r"^\s*(select|with)\b", sql, re.I): raise AssertionError("not a SELECT: " + sql[:60])
    if "count(*)::text, coalesce(max(loaded_at)" in sql: return [[str(len(CARDS)), "2026-11-11 08:42:00+00"]]
    if "body::text from raw.documents" in sql: return [[k, json.dumps(v)] for k, v in CARDS.items()]
    if "jsonb_each(d.body->'visits')" in sql: return [list(x) for x in FACIDS]
    if "max(facility) from amd.charges" in sql: return [[k, v] for k, v in NAMES.items()]
    want = set((params[0] if params else "").split(","))
    if "from amd.charges where chart_id" in sql: return [list(r) for r in CHARGES if r[0] in want]
    if "from ehpa.feed_charges" in sql: return [list(r) for r in FEED if r[0] in want]
    raise AssertionError("unexpected query: " + sql[:80])
def quiet(fn, *a, **k):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf): r = fn(*a, **k)
    return r, buf.getvalue()
TMP = tempfile.mkdtemp(prefix="board_chargefac_test_")

# ---- 1. reads only
for bad in ("update raw.documents set body = '{}'", "select 1; delete from raw.documents", "insert into raw.documents values (1)"):
    try: B.neon_select(bad); refused = ""
    except ValueError as e: refused = str(e)
    check("1 refused before it leaves: %s" % bad[:32], "reads only" in refused, refused)

# ---- 2. names, kinds, dates
check("2 SOUTHWOOD and the generic words classify the nursing facilities (words the privacy gate leaves alone)",
      B.kind_of("INVENTED SOUTHWOOD") == "SNF" and B.kind_of("INVENTED HEALTH AND REHABILITATION CENTER") == "SNF" and B.kind_of("Invented Health & Rehab") == "SNF")
check("2 hospital / ALF / independent living / office", [B.kind_of(x) for x in ("INVENTED GENERAL HOSPITAL", "INVENTED GARDENS ALF", "INVENTED INDEPENDENT LIVING", "NORTH FLORIDA SENIOR CARE")] == ["HOSP", "ALF", "IL", "OFFICE"])
check("2 AdvancedMD's capitals are shortened like the facilities line; a name already in mixed case is left alone",
      B.short("INVENTED GARDENS ALF") == "Invented Gardens ALF" and B.short("INVENTED REHAB AT THE LAKE") == "Invented Rehab at The Lake" and B.short("Invented Feed Name") == "Invented Feed Name" and B.short("HCA REHAB") == "HCA Rehab")
sp = B.date_spans("stay 8/5-8/17/2026; 12/8 + 12/14/2023; 12/28-1/3/2026; x3 10/2025; 2026-11-09")
check("2 dates of service: a span, a pair sharing one year, a span over New Year, a month, an ISO date",
      ("2026-08-05", "2026-08-17") in sp and ("2023-12-08", "2023-12-08") in sp and ("2023-12-14", "2023-12-14") in sp and ("2025-12-28", "2026-01-03") in sp
      and ("2025-10-01", "2025-10-31") in sp and ("2026-11-09", "2026-11-09") in sp, sp)

# ---- 3. one card -> its charge's facility
rows = [dict(v, id=k) for k, v in CARDS.items()]
rows[[r["id"] for r in rows].index("card-k")]["chargefac"] = None
res = {r["id"]: (cf, why) for r, cf, why in B.compute(rows, select, now="2026-11-12T15:00:00Z")}
EXPECT_K = res["card-k"][0]
CARDS["card-k"]["chargefac"] = dict(EXPECT_K, at="2026-11-01T00:00:00Z")      # already on the card (another time stamp): unchanged
a = res["card-a"][0]
check("3 a visit named on the card wins over the chart's newer charges", a and a["name"] == "Invented Nursing and Rehabilitation Center" and a["how"] == "visit"
      and a["kind"] == "SNF" and a["label"] == "SNF resident" and a["dos"] == "10/02/2026" and a["cpt"] == "99309" and a["visit"] == "19999001", a)
b = res["card-b"][0]
check("3 the dates in the facility text find the charges (and a facility id that disagrees does not override them)", b and b["name"] == "Invented Southwood" and b["how"] == "dos" and b["dos"] == "11/04/2026", b)
c = res["card-c"][0]
check("3 several charges: the facility most of them came from is named, the other is listed, and the hospital patient's home is given",
      c and c["name"] == "Invented General Hospital" and c["kind"] == "HOSP" and c["also"] == ["Invented Gardens ALF"] and c["res"] == {"name": "Invented Gardens ALF", "kind": "ALF", "thru": "8/26"} and c["dos"] == "08/17/2026", c)
d = res["card-d"][0]
check("3 no chart, one facility id in the text: named through the id (the id's usual code wins)", d and d["name"] == "Invented General Hospital" and d["how"] == "facility id" and d["code"] == "INVH", d)
e = res["card-e"][0]
check("3 nothing named: the chart's charge still owing, not its newest charge", e and e["name"] == "Invented Nursing and Rehabilitation Center" and e["how"] == "open balance", e)
f = res["card-f"][0]
check("3 nothing named, nothing owing: the chart's newest LIVE charge (a newer void line is passed over)", f and f["name"] == "Invented Gardens ALF" and f["how"] == "newest charge" and f["dos"] == "06/01/2026", f)
check("3 the card's named charge has no facility in AdvancedMD: generic, with the reason (no fall back to another charge)",
      res["card-g"][0] is None and "no facility in AdvancedMD" in res["card-g"][1], res["card-g"])
check("3 ... the same when the charge is found by its date of service (not the chart's other charge still owing)",
      res["card-m"][0] is None and "no facility in AdvancedMD" in res["card-m"][1], res["card-m"])
check("3 no chart number and no facility id: generic", res["card-h"][0] is None and res["card-h"][1] == "no chart number on the card", res["card-h"])
i = res["card-i"][0]
check("3 a feed visit the history lacks: named through the feed's facility id with AdvancedMD's spelling", i and i["name"] == "Invented Gardens ALF" and i["src"] == "neon feed" and i["dos"] == "11/08/2026", i)
l = res["card-l"][0]
check("3 a card on two charts: visits on both are found", l and l["name"] == "Invented Nursing and Rehabilitation Center" and l["how"] == "visit" and "also" not in l and l["dos"] == "10/03/2026", l)

# ---- 4. the board file
OUT = os.path.join(TMP, "out")
r, out = quiet(B.main, ["build", "--out", OUT, "--stamp", "2026-11-12T1500Z"], select=select)
files = sorted(os.listdir(OUT)) if os.path.isdir(OUT) else []
check("4 build writes ONE board_updates_<stamp>.json", r == 0 and files == ["board_updates_2026-11-12T1500Z.json"], (r, files, out))
doc = json.load(open(os.path.join(OUT, files[0]))) if files else {"ops": []}
ids = sorted(o["id"] for o in doc["ops"])
check("4 the board's own format: schema irb-board-updates/1, a source and a created time", doc.get("schema") == "irb-board-updates/1" and doc.get("source", "").startswith("tools/db/board_chargefac.py") and doc.get("created"))
check("4 only `update` ops on items that set only chargefac - never `updated`, never status / need / why",
      doc["ops"] and all(o["op"] == "update" and o["collection"] == "items" and list(o["set"]) == ["chargefac"] and "append" not in o for o in doc["ops"]), doc["ops"][:2])
check("4 open cards whose facility is new; not the generic ones, not the done card, not the card that already has it",
      ids == ["card-a", "card-b", "card-c", "card-d", "card-e", "card-f", "card-i", "card-l"], ids)
check("4 the counts are printed, and no card is named in them", "open cards 12: the charge's facility found for 9" in out and "done cards 1" in out and "card-" not in out, out)
OUT2 = os.path.join(TMP, "out_all")
quiet(B.main, ["build", "--out", OUT2, "--stamp", "2026-11-12T1501Z", "--all"], select=select)
doc2 = json.load(open(os.path.join(OUT2, "board_updates_2026-11-12T1501Z.json")))
check("4 --all adds the done card", sorted(o["id"] for o in doc2["ops"]) == sorted(ids + ["card-j"]))
r, out = quiet(B.main, ["build", "--out", os.path.join(ROOT, "tmp_never_chargefac")], select=select)
check("4 an output folder inside the repository is refused", r == 2 and "refused" in out and not os.path.exists(os.path.join(ROOT, "tmp_never_chargefac")), out)
r, out = quiet(B.main, ["plan"], select=select)
check("4 plan: counts only, nothing written", r == 0 and "open cards 12" in out and "card-" not in out, out)

# ---- 5. a run's own file
RUN = os.path.join(TMP, "board_updates_2026-11-12T1639Z.json")
run_doc = {"schema": "irb-board-updates/1", "source": "backend billing run 2026-11-12T1639Z", "created": "2026-11-12T16:45:00Z", "ops": [
    {"op": "upsert", "collection": "items", "id": "new-1", "set": {"amdid": ch(2), "facility": "SNF (99309 11/4/2026)", "need": "Unbilled.", "status": "claude"},
     "append": {"notes": [{"who": "Claude", "text": "Created by the run.", "at": "2026-11-12T16:45:00Z"}]}},
    {"op": "upsert", "collection": "items", "id": "card-a", "set": {}, "append": {"checks": [{"ok": "na", "src": "run", "result": "visit v19999002 looked at", "when": "11/12"}]}},
    {"op": "replace", "collection": "items", "id": "new-2", "data": {"amdid": ch(1), "facility": "SNF", "need": "Visit v19999002 waits."}},
    {"op": "upsert", "collection": "items", "id": "new-3", "set": {"amdid": ch(1), "facility": "SNF", "chargefac": {"name": "Kept as it was"}}},
    {"op": "delete", "collection": "drops", "id": "d1"}]}
json.dump(run_doc, open(RUN, "w"), indent=1)
r, out = quiet(B.main, ["stamp", "--file", RUN], select=select)
got = json.load(open(RUN)); ops = {o["id"]: o for o in got["ops"]}
check("5 stamp: a new row gets the charge's facility", r == 0 and ops["new-1"]["set"].get("chargefac", {}).get("name") == "Invented Southwood", (r, out, ops["new-1"]))
check("5 stamp: a replaced row too (in its data)", ops["new-2"]["data"].get("chargefac", {}).get("name") == "Invented General Hospital", ops["new-2"])
check("5 stamp: an append-only op, a row that already names its charge facility and a drops delete are left as they were",
      ops["card-a"]["set"] == {} and ops["new-3"]["set"]["chargefac"] == {"name": "Kept as it was"} and ops["d1"] == {"op": "delete", "collection": "drops", "id": "d1"}, (ops["card-a"], ops["new-3"]))
check("5 stamp: the file still passes the board_ops gate (no `updated` in any set)", not B.board_ops.clean_file_report(json.loads(json.dumps(got))), B.board_ops.clean_file_report(got))
RUN2 = os.path.join(TMP, "board_updates_2026-11-12T1640Z.json"); json.dump(run_doc, open(RUN2, "w"), indent=1); before = open(RUN2, "rb").read()
def broken(sql, params=()): raise RuntimeError("could not reach the database")
r, out = quiet(B.main, ["stamp", "--file", RUN2], select=broken)
check("5 stamp with the database out of reach: the file is left byte for byte, the run goes on (exit 0)", r == 0 and open(RUN2, "rb").read() == before and "left exactly as it was" in out, out)

# ---- 6. board rows from a file or an ArtifactData folder
LST = os.path.join(TMP, "rows.json"); json.dump([dict(v, id=k) for k, v in CARDS.items()], open(LST, "w"))
OBJ = os.path.join(TMP, "rows_obj.json"); json.dump(CARDS, open(OBJ, "w"))
DIR = os.path.join(TMP, "artifactdata"); os.makedirs(os.path.join(DIR, "items"))
for k, v in CARDS.items(): json.dump({"id": k, "version": 3, "data": v}, open(os.path.join(DIR, "items", k + ".json"), "w"))
shape = lambda rs: sorted((r["id"], r.get("amdid"), r.get("facility")) for r in rs)
check("6 --items: a list, an {id: row} object and an ArtifactData folder (wrapped with their version) give the same rows",
      shape(B.rows_from_items(LST)) == shape(B.rows_from_items(OBJ)) == shape(B.rows_from_items(DIR)) == shape(rows), shape(B.rows_from_items(DIR))[:3])
r, out = quiet(B.main, ["plan", "--items", DIR], select=select)
check("6 plan --items reads the folder, not the database copy", r == 0 and "rows from " + DIR in out and "open cards 12" in out, out)

# ---- 7. the board page
page = open(PAGE, encoding="utf-8").read()
check("7 the page keeps the live page's other behaviour (Details fold, chart twins, the two inbox guards, Refresh, Run all billing)",
      all(x in page for x in ('data-more', 'chartSibs', 'MAX_AGE_DAYS', 'reg.codeRev', '__ehpaRefresh', 'ehpa-refresh-top', 'fab-run', "kind==='update'")))
check("7 the page's classifier names the nursing facilities by words the privacy gate leaves alone (no pseudonym in it)",
      "SOUTHWOOD" in page and not re.search(r"OAKES|JASPER", page))
check("7 no privacy-gate placeholder anywhere in the page's code (the gate once turned the Refresh pill's storage call into [name](...))",
      not re.search(r"\[(name|first|DOB|MBI|SSN|member id)\]", page), re.findall(r".{0,30}\[(?:name|first|DOB|MBI|SSN|member id)\].{0,30}", page)[:3])
for p in ("boards/board_facnow.py", "scripts/helpers/board_facnow.py"):
    t = open(os.path.join(ROOT, p), encoding="utf-8").read()
    check("7 %s classifies like the page (SOUTHWOOD, no pseudonym)" % p, "SOUTHWOOD" in t and not re.search(r"OAKES|JASPER", t))
check("7 the two board_facnow.py copies are identical", open(os.path.join(ROOT, "boards", "board_facnow.py"), "rb").read() == open(os.path.join(ROOT, "scripts", "helpers", "board_facnow.py"), "rb").read())
NODE = shutil.which("node")
m1 = re.search(r"\n  const esc=[^\n]+\n", page); m2 = re.search(r"\n  // ---- 10/3 \(William\): the actual facility[\s\S]*?\n  function render\(\)\{", page)
check("7 the badge code is where the test expects it in the page", bool(m1 and m2))
if not NODE:
    print("skip 7 node is not installed here - the page's badge code was not run")
elif m1 and m2:
    PROBE = [dict(CARDS["card-c"], id="p-charge", chargefac=c, facnow={"name": "Somewhere Newer", "kind": "SNF", "dos": "11/01/2026"}),
             {"id": "p-facnow", "facility": "SNF (99309 9/9/2026)", "facnow": {"name": "Invented Southwood", "kind": "SNF", "dos": "10/02/2026"}},
             {"id": "p-line", "facility": "SNF", "facilities": "Invented General Hospital 9/26 · Invented Gardens ALF 1/26–8/26"},
             {"id": "p-guess", "amdid": ch(7), "facility": "SNF (99309 10/11/2026)"},
             {"id": "p-none", "amdid": ch(20)}]
    KINDS = ["INVENTED SOUTHWOOD", "INVENTED HEALTH AND REHABILITATION CENTER", "INVENTED GENERAL HOSPITAL", "INVENTED GARDENS ALF", "INVENTED INDEPENDENT LIVING",
             "HCA REHAB", "INVENTED DEVELOPMENTAL CENTER", "NORTH FLORIDA SENIOR CARE", "SNF (99309)", "Westminster Invented", "Invented Place"]
    JS = os.path.join(TMP, "badge.js")
    open(JS, "w", encoding="utf-8").write(m1.group(0) + m2.group(0)[:-len("\n  function render(){")] +
        "\nconst probe=JSON.parse(require('fs').readFileSync(process.argv[2],'utf8'));\n"
        "process.stdout.write(JSON.stringify({info:probe.rows.map(r=>facInfo(r)),html:probe.rows.map(r=>facBadge(r)),kinds:probe.kinds.map(kindOf)}));\n")
    IN = os.path.join(TMP, "probe.json"); json.dump({"rows": PROBE, "kinds": KINDS}, open(IN, "w"))
    scripts = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)</script>", page); bad = []
    for n, s in enumerate(scripts):
        p = os.path.join(TMP, "script%d.js" % n); open(p, "w", encoding="utf-8").write(s)
        cr = subprocess.run([NODE, "--check", p], capture_output=True, text=True, timeout=60)
        if cr.returncode: bad.append((n, cr.stderr.strip()[-200:]))
    check("7 every inline script of the page parses (node --check)", len(scripts) >= 2 and not bad, bad)
    pr = subprocess.run([NODE, JS, IN], capture_output=True, text=True, timeout=60)
    try: o = json.loads(pr.stdout)
    except ValueError: o = {"info": [None] * 5, "html": [""] * 5, "kinds": []}
    check("7 node ran the page's badge code", pr.returncode == 0, pr.stderr[-400:])
    inf = o["info"]
    check("7 page: the charge's facility comes first - before the chart's newest visit (facnow)",
          inf[0] and inf[0]["src"] == "charge" and inf[0]["name"] == "Invented General Hospital" and inf[0]["kind"] == "HOSP" and inf[0]["also"] == ["Invented Gardens ALF"], inf[0])
    h = o["html"][0]
    check("7 page: the badge shows the name, hospital inpatient, the charge's date and code, where the patient lives and the other facility",
          "Invented General Hospital" in h and "hospital inpatient" in h and "08/17/2026 · 99238" in h and "resident at <b>Invented Gardens ALF</b>" in h
          and "also billed at <b>Invented Gardens ALF</b>" in h and "unknown" not in h and "visit 19999024" in h, h)
    check("7 page: without a charge facility, facnow and the facilities line still lead (the generic text never shows over them)",
          inf[1]["src"] == "chart" and inf[1]["name"] == "Invented Southwood" and inf[2]["src"] == "visits" and inf[2]["name"] == "Invented General Hospital"
          and inf[2]["res"] == {"name": "Invented Gardens ALF", "kind": "ALF"}, inf[1:3])
    check("7 page: a generic SNF only when nothing names a facility - shown as a guess", inf[3]["src"] == "guess" and "facbadge unknown" in o["html"][3], (inf[3], o["html"][3]))
    check("7 page: a chart with no facility at all says so", inf[4] is None and "facility not on file yet" in o["html"][4], o["html"][4])
    check("7 page and helper classify every name alike", o["kinds"] == [B.kind_of(k) for k in KINDS], (o["kinds"], [B.kind_of(k) for k in KINDS]))

# ---- 8. what it did not touch
check("8 every statement sent to the database was a SELECT", all(re.match(r"^\s*(select|with)\b", s, re.I) for s in SQL) and len(SQL) > 10)
check("8 no module that talks to AdvancedMD was loaded", all(m not in sys.modules for m in ("amd", "txh", "resave", "void_tx", "era_clear")))
shutil.rmtree(TMP, ignore_errors=True)
AFTER = snapshot()
check("8 nothing was written in the repository while the test ran", AFTER == BEFORE, sorted(set(AFTER.items()) ^ set(BEFORE.items()))[:5])
print("\ntest_board_chargefac: %d checks, %d failed%s" % (RAN[0], len(FAILS), "" if not FAILS else " - " + "; ".join(FAILS)[:1200]))
sys.exit(1 if FAILS else 0)
