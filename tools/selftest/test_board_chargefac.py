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
#   - (review 11/12) writes every chargefac with EVERY key, so a later badge merged over an earlier one by the store's update() keeps
#     none of its 'resident at' / 'also billed at' and `build` settles; names the chart's NEWEST charge under rules 4 and 6 (not the
#     facility most of its charges came from); reads a card's chart from the end of its id or pat<n> in its text when it has no amdid
#     (never from a date-shaped id ending) and says so;
#   - writes ONE board_updates_<stamp>.json (irb-board-updates/1): `update` ops that set only `chargefac`, never `updated`, only for
#     open cards whose charge facility is new or changed (--all adds done cards), and refuses an output folder inside the repository;
#   - stamps a run's own board file (new rows and rows whose facility it sets) and leaves it byte for byte when the database fails;
#     with --items it works a card already on the board out from the whole card and never replaces a stronger badge (a visit match)
#     with a weaker guess; without --items it writes only a charge the card names; it prints counts by rule, never a row id; the three
#     live prompts pass --items;
#   - reads board rows given as a list, an {id: row} object or an ArtifactData folder.
#   - (second review 11/12) whatever --items holds - rows without the card, an empty list, ArtifactData documents, a {documents: [...]}
#     object - a stored visit badge is never replaced by a guess, and a new card (created / patient and dob in its set) still gets one;
#     a corrected chart number does not keep the old chart's badge (stamp and build); build re-sends no badge the page would keep; rule 6
#     never names a voided charge's facility; a date-shaped id ending (a year, mmddyyyy, mmddyy / yymmdd) is never a chart number; the
#     prompts ask only for the stored rows of the cards a file touches.
#   - (third review 11/12) a chart corrected with no new badge: stamp (card seen whole) and build clear the old chart's badge (chargefac
#     null) - only when nothing is found on the chart the card has now, never a badge on that chart - and count it as cleared; a badge is
#     on the card only while the card has EVERY chart it was worked out on (_on_card; a card with no chart number of its own passes);
#     a card stamp cannot see whole gets only a VISIT it names (no date-of-service or facility-id match read from the op alone), a new
#     card any match; plan and build count a card that keeps its badge under that badge's rule and say so; the prompts say all of it.
#   - (third review, page) the badge is shown only while the card has every chart it was worked out on (else facnow / the facilities
#     line / lastfac / the facility text show) - cfOnCard equals _on_card on a table of cases; applyOp never writes a file's badge worked
#     out on a chart the card will not have (merge, replace, a new row), applies the helper's clear only to another chart's badge, and
#     runSync (run against a stand-in Drive inbox) counts an op it kept as kept, never as a change, in the registry and the Applied list.
# And that the board page (boards/templates/tracker.html, run in node when node is installed) shows the charge's facility first,
#   keeps facnow / the facilities line / lastfac next, shows a generic SNF only when nothing names a facility, classifies facility
#   names like the helper does, and still carries the live page's other behaviour; that its applyOp (run against a stand-in store
#   whose update() merges like the real one) leaves `updated` alone for an op that only sets chargefac, and that a home's badge never
#   shows a 'resident at' line; (second review) that applyOp itself keeps a stronger stored badge against a file's guess - unless the
#   card's chart was corrected - and that its rule table equals the helper's.
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
    # review 11/12 - charts found only through a card's id / text, and charts whose most-billed facility is not their newest one
    line(21, "19999210", "2026-10-05", "99349", "INVA"), line(22, "19999220", "2026-10-06", "99309", "INV1"),
    line(30, "19999301", "2026-05-01", "99309", "INV1"), line(30, "19999302", "2026-05-02", "99309", "INV1"), line(30, "19999303", "2026-05-03", "99309", "INV1"),
    line(30, "19999304", "2026-05-04", "99309", "INV1"), line(30, "19999305", "2026-05-05", "99309", "INV1"), line(30, "19999306", "2026-06-10", "99349", "INVA"),
    line(31, "19999311", "2026-08-01", "99223", "INVH", ins="50.00"), line(31, "19999312", "2026-08-02", "99233", "INVH", ins="50.00"),
    line(31, "19999313", "2026-08-03", "99233", "INVH", ins="50.00"), line(31, "19999314", "2026-09-15", "99309", "INV1", ins="75.00"),
    # second review 11/12 - voided charges rule 6 must never name, and charts a date-shaped id ending would wrongly read (each has a charge,
    # so a wrong reading would put a wrong facility on the card)
    line(40, "19999401", "2026-03-02", "99309", "INV1", live="false"), line(40, "19999402", "2026-10-20", "99309", ""),
    line(41, "19999411", "2026-09-01", "99233", "INVH", live="false"),
    # third review 11/12 - a chart whose only charge has no facility: a card corrected onto it gets no new badge
    line(42, "19999421", "2026-10-15", "99309", ""),
] + [["pat" + n, "c1999990%d" % i, "1999990%d" % i, "2026-10-01", "99233", "INVH", NAMES["INVH"], "true", "0.00", "0.00"]
     for i, n in enumerate(("2026", "11122026", "111226", "261112"))]
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
check("3 a card on two charts: visits on both are found", l and l["name"] == "Invented Nursing and Rehabilitation Center" and l["how"] == "visit" and l.get("also") == [] and l["dos"] == "10/03/2026", l)

# ---- 3b. (review 11/12, blocking) every chargefac carries every key, so a later badge merged over an earlier one keeps none of it
def update_merge(cur, patch):
    """the board store's update() (db contract 0.2.96): nested objects merge key by key; anything else - a list, null - replaces the field"""
    out = dict(cur)
    for k, v in patch.items(): out[k] = update_merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out
found = [(k, cf) for k, (cf, _) in res.items() if cf]
check("3b every chargefac carries every key of CF_KEYS (also [] and res / chart_from null when they do not apply) - the facility-id one too",
      len(found) >= 9 and all(list(cf) == list(B.CF_KEYS) for _, cf in found), [(k, sorted(set(B.CF_KEYS) ^ set(cf))) for k, cf in found if list(cf) != list(B.CF_KEYS)])
HOSP_CF, HOME_CF, FACID_CF = res["card-c"][0], res["card-a"][0], res["card-d"][0]
for label, new in (("a nursing-home badge", HOME_CF), ("a facility-id badge", FACID_CF)):
    merged = update_merge({"chargefac": HOSP_CF}, {"chargefac": new})["chargefac"]
    check("3b %s written over a hospital badge with 'resident at' / 'also billed at': the store's merge keeps neither, and it equals the new badge" % label,
          HOSP_CF.get("res") and HOSP_CF.get("also") and merged.get("res") is None and merged.get("also") == [] and B._same(new, merged), merged)
settled = B.build_file([(dict(id="merged-1", status="claude", chargefac=update_merge({"chargefac": HOSP_CF}, {"chargefac": HOME_CF})["chargefac"]), HOME_CF, "visit")],
                       "2026-11-12T1502Z", "2026-11-12T15:02:00Z")
check("3b ... so the next build settles on that card (no op re-sent)", settled["ops"] == [], settled["ops"])

# ---- 3c. (review 11/12) rules 4 and 6 name the chart's NEWEST charge, not the facility most of its charges came from
EXTRA = {"newest-6": {"amdid": ch(30), "status": "claude", "facility": "", "need": "Nothing named here."},
         "newest-4": {"amdid": ch(31), "status": "william", "facility": "", "need": "Which plan pays?"},
         "fromid-9700021": {"status": "claude", "facility": "ALF", "need": "Which plan pays?"},
         "fromtext-card": {"status": "claude", "facility": "", "need": "Chart pat9700022 per the facesheet."},
         "sweep-x-1031": {"status": "claude", "facility": "", "need": "Sweep of 10/31 - every open denial."},
         "sweep-x-20261112": {"status": "claude", "facility": "", "need": "Sweep of the day."},
         "sweep-x-2026": {"status": "claude", "facility": "", "need": "Year-end sweep."},
         "sweep-x-11122026": {"status": "claude", "facility": "", "need": "Sweep of the day."},
         "sweep-x-111226": {"status": "claude", "facility": "", "need": "Sweep of the day."},
         "sweep-x-261112": {"status": "claude", "facility": "", "need": "Sweep of the day."},
         "void-6": {"amdid": ch(40), "status": "claude", "facility": "", "need": "Nothing named here."},
         "void-all": {"amdid": ch(41), "status": "claude", "facility": "", "need": "Nothing named here."}}
xres = {r["id"]: (cf, why) for r, cf, why in B.compute([dict(v, id=k) for k, v in EXTRA.items()], select, now="2026-11-12T15:00:00Z")}
n6, n4 = xres["newest-6"][0], xres["newest-4"][0]
check("3c newest charge: five older nursing-home visits and one newer ALF visit - the newer ALF is named",
      n6 and n6["how"] == "newest charge" and n6["name"] == "Invented Gardens ALF" and n6["dos"] == "06/10/2026", n6)
check("3c open balance: three older owing hospital lines and one newer owing nursing-home line - the newer one is named",
      n4 and n4["how"] == "open balance" and n4["name"] == "Invented Nursing and Rehabilitation Center" and n4["dos"] == "09/15/2026" and n4.get("res") is None, n4)

# ---- 3d. (review 11/12) a card with no amdid: the chart from the end of its id, then pat<n> in its text - marked as found that way
fi, ft = xres["fromid-9700021"][0], xres["fromtext-card"][0]
check("3d no amdid, the id ends with the chart number (last-first-<amdid>): the chart's charge is found, marked chart_from 'card id'",
      fi and fi["name"] == "Invented Gardens ALF" and fi.get("chart_from") == "card id" and fi["dos"] == "10/05/2026", fi)
check("3d no amdid and no number at the end of the id: pat<n> in the card's text, marked chart_from 'card text'",
      ft and ft["name"] == "Invented Nursing and Rehabilitation Center" and ft.get("chart_from") == "card text", ft)
check("3d a date-shaped id ending (a sweep's -1031, -20261112) is never taken for a chart number",
      xres["sweep-x-1031"] == (None, "no chart number on the card") and xres["sweep-x-20261112"] == (None, "no chart number on the card"), (xres["sweep-x-1031"], xres["sweep-x-20261112"]))
check("3d a card with its own amdid is not marked (chart_from null)", res["card-a"][0].get("chart_from", "missing") is None and res["card-c"][0].get("chart_from", "missing") is None)
check("3d every badge says the card's chart number(s) it was worked out on ('' when the card has none)",
      res["card-a"][0].get("chart") == ch(1) and res["card-l"][0].get("chart") == "%s,%s" % (ch(12), ch(13)) and res["card-d"][0].get("chart") == "" and fi.get("chart") == ch(21),
      [(k, (v[0] or {}).get("chart")) for k, v in (("card-a", res["card-a"]), ("card-l", res["card-l"]), ("card-d", res["card-d"]), ("fromid", xres["fromid-9700021"]))])

# ---- 3e. (second review 11/12) rule 6 never names a voided charge's facility - the card stays generic, as before 11/12
NOLIVE = (None, "no live charge of the chart has a facility in AdvancedMD")
check("3e newest charge: an older VOIDED line at a nursing home next to a newer live line with no facility - generic, the voided charge's facility is not named",
      xres["void-6"] == NOLIVE, xres["void-6"])
check("3e newest charge: a chart whose only charge was voided - generic too (never a voided charge's facility)", xres["void-all"] == NOLIVE, xres["void-all"])

# ---- 3f. (second review 11/12) a bare year, mmddyyyy and 6-digit dates at the end of a card id are never chart numbers
for sfx in ("2026", "11122026", "111226", "261112"):
    check("3f a date-shaped id ending -%s is never taken for a chart number (that chart has a charge - the card would get a wrong facility)" % sfx,
          xres["sweep-x-" + sfx] == (None, "no chart number on the card"), xres["sweep-x-" + sfx])
CHARTLIKE = ("7953", "9468", "45807", "12311998", "17460023", "958217")
check("3f numbers shaped like the records' chart numbers (4 digits from 7 or 9, 5 digits, 8 digits from 12 or 17, a 6-digit non-date) are still read as charts",
      not [n for n in CHARTLIKE if B._date_shaped(n)], [n for n in CHARTLIKE if B._date_shaped(n)])

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
    {"op": "upsert", "collection": "items", "id": "new-1", "set": {"amdid": ch(2), "facility": "SNF (99309 11/4/2026)", "need": "Unbilled.", "status": "claude", "created": "2026-11-12T16:45:00Z"},
     "append": {"notes": [{"who": "Claude", "text": "Created by the run.", "at": "2026-11-12T16:45:00Z"}]}},
    {"op": "upsert", "collection": "items", "id": "card-a", "set": {}, "append": {"checks": [{"ok": "na", "src": "run", "result": "visit v19999002 looked at", "when": "11/12"}]}},
    {"op": "replace", "collection": "items", "id": "new-2", "data": {"amdid": ch(1), "facility": "SNF", "need": "Visit v19999002 waits."}},
    {"op": "upsert", "collection": "items", "id": "new-3", "set": {"amdid": ch(1), "facility": "SNF", "chargefac": {"name": "Kept as it was"}}},
    {"op": "delete", "collection": "drops", "id": "d1"}]}
json.dump(run_doc, open(RUN, "w"), indent=1)
r, out = quiet(B.main, ["stamp", "--file", RUN], select=select)
got = json.load(open(RUN)); ops = {o["id"]: o for o in got["ops"]}
check("5 stamp: a new row (`created` in its set, as board_ops.plan_new_row writes it) gets the charge's facility", r == 0 and ops["new-1"]["set"].get("chargefac", {}).get("name") == "Invented Southwood", (r, out, ops["new-1"]))
check("5 stamp: a replaced row too (in its data)", ops["new-2"]["data"].get("chargefac", {}).get("name") == "Invented General Hospital", ops["new-2"])
check("5 stamp: an append-only op, a row that already names its charge facility and a drops delete are left as they were",
      ops["card-a"]["set"] == {} and ops["new-3"]["set"]["chargefac"] == {"name": "Kept as it was"} and ops["d1"] == {"op": "delete", "collection": "drops", "id": "d1"}, (ops["card-a"], ops["new-3"]))
check("5 stamp: the file still passes the board_ops gate (no `updated` in any set)", not B.board_ops.clean_file_report(json.loads(json.dumps(got))), B.board_ops.clean_file_report(got))
check("5 stamp prints counts by rule only - no row id (ids are patient-name slugs in the runs)",
      '"dos": 1' in out and '"visit": 1' in out and not [i for i in ("new-1", "new-2", "new-3", "card-a") if i in out], out)
RUN2 = os.path.join(TMP, "board_updates_2026-11-12T1640Z.json"); json.dump(run_doc, open(RUN2, "w"), indent=1); before = open(RUN2, "rb").read()
def broken(sql, params=()): raise RuntimeError("could not reach the database")
r, out = quiet(B.main, ["stamp", "--file", RUN2], select=broken)
check("5 stamp with the database out of reach: the file is left byte for byte, the run goes on (exit 0)", r == 0 and open(RUN2, "rb").read() == before and "left exactly as it was" in out, out)

# ---- 5b. (review 11/12) stamp --items: a card already on the board is worked out from the whole card and keeps a stronger badge
GUESS_1 = B.compute([{"id": "probe-guess", "amdid": ch(1)}], select, now="2026-11-01T00:00:00Z")[0][1]     # chart 1's newest charge (a guess)
VISIT_1 = dict(res["card-a"][0], at="2026-11-01T00:00:00Z")                                               # chart 1's visit 19999001 (a match)
check("5b the stand-in: chart 1's newest charge is the hospital, its visit 19999001 the nursing home",
      GUESS_1["how"] == "newest charge" and GUESS_1["name"] == "Invented General Hospital" and VISIT_1["how"] == "visit" and VISIT_1["name"] == "Invented Nursing and Rehabilitation Center")
ITEMS_ROWS = [{"id": "keep-1", "amdid": ch(1), "status": "william", "facility": "SNF", "need": "Secondary pending.", "chargefac": VISIT_1},
              {"id": "known-1", "amdid": ch(1), "status": "claude", "facility": "SNF", "need": "Watch."},
              {"id": "weak-1", "amdid": ch(1), "status": "claude", "facility": "SNF", "need": "Pending.", "chargefac": GUESS_1},
              {"id": "whole-1", "amdid": ch(1), "status": "claude", "facility": "SNF", "need": "Medicare denied v19999001.", "chargefac": GUESS_1},
              {"id": "known-2", "amdid": ch(1), "status": "claude", "facility": "SNF", "need": "Watch."}]
ITEMS_FILE = os.path.join(TMP, "board_rows.json"); json.dump(ITEMS_ROWS, open(ITEMS_FILE, "w"))
NOTE = lambda t: {"notes": [{"who": "Claude", "text": t, "at": "2026-11-12T17:45:00Z"}]}
run3 = {"schema": "irb-board-updates/1", "source": "backend billing run 2026-11-12T1739Z", "created": "2026-11-12T17:45:00Z", "ops": [
    {"op": "upsert", "collection": "items", "id": "keep-1", "set": {"amdid": ch(1), "facility": "SNF"}, "append": NOTE("Looked again.")},
    {"op": "upsert", "collection": "items", "id": "known-1", "set": {"facility": "SNF"}},
    {"op": "upsert", "collection": "items", "id": "weak-1", "set": {"amdid": ch(1), "facility": "SNF"}, "append": NOTE("Medicare paid visit v19999001.")},
    {"op": "upsert", "collection": "items", "id": "whole-1", "set": {"facility": "Invented Nursing and Rehabilitation Center"}},
    {"op": "upsert", "collection": "items", "id": "fresh-1", "set": {"amdid": ch(1), "facility": "SNF", "need": "New card.", "status": "claude", "created": "2026-11-12T17:45:00Z"}},
    {"op": "update", "collection": "items", "id": "gone-1", "set": {"amdid": ch(1), "facility": "SNF"}},
    {"op": "upsert", "collection": "items", "id": "known-2", "set": {"amdid": ch(1), "facility": "SNF (99233 10/20/2026)"}}]}
RUN3, RUN4 = os.path.join(TMP, "board_updates_2026-11-12T1739Z.json"), os.path.join(TMP, "board_updates_2026-11-12T1740Z.json")
json.dump(run3, open(RUN3, "w"), indent=1); json.dump(run3, open(RUN4, "w"), indent=1)
r3, out3 = quiet(B.main, ["stamp", "--file", RUN3, "--items", ITEMS_FILE], select=select)
s3 = {o["id"]: o["set"].get("chargefac") for o in json.load(open(RUN3))["ops"]}
check("5b --items: a card whose badge came from its visit keeps it - the run's op alone would give only the chart's newest charge",
      r3 == 0 and s3["keep-1"] is None and "stronger rule (visit)" in out3, (s3["keep-1"], out3))
check("5b --items: the card is worked out from its stored row - the op sets only the facility, the stored need names the visit (a weaker stored badge is replaced)",
      (s3["whole-1"] or {}).get("how") == "visit" and s3["whole-1"]["name"] == "Invented Nursing and Rehabilitation Center", s3["whole-1"])
check("5b --items: the op's appended note counts (it names the visit), and a match replaces a stored guess",
      (s3["weak-1"] or {}).get("how") == "visit", s3["weak-1"])
check("5b --items: a card on the board with no badge yet, and a new card (`created` in its set, as board_ops.plan_new_row writes it), get even a guess",
      (s3["known-1"] or {}).get("how") == "newest charge" and (s3["fresh-1"] or {}).get("how") == "newest charge", (s3["known-1"], s3["fresh-1"]))
check("5b --items: an `update` of a card missing from the rows given gets no guess (its badge is not known)", s3["gone-1"] is None, s3["gone-1"])
r4, out4 = quiet(B.main, ["stamp", "--file", RUN4], select=select)
s4 = {o["id"]: o["set"].get("chargefac") for o in json.load(open(RUN4))["ops"]}
check("5b without --items: a card already on the board gets only a charge it names (the visit in the appended note), never a guess; the new card still gets one",
      r4 == 0 and (s4["weak-1"] or {}).get("how") == "visit" and all(s4[i] is None for i in ("keep-1", "known-1", "whole-1", "gone-1"))
      and (s4["fresh-1"] or {}).get("how") == "newest charge", (s4, out4))
check("5b --items: a date of service the card names, on a card seen whole, is still written (third review: only a card stamp cannot see whole is held to a visit)",
      (s3["known-2"] or {}).get("how") == "dos" and s3["known-2"]["name"] == "Invented General Hospital", s3["known-2"])
check("5b without --items (third review): a date of service read from the op alone is not written either - a visit the stored card names would outrank it",
      s4["known-2"] is None and "read from the op alone" in out4, (s4["known-2"], out4))
check("5b stamp prints no row id, with or without --items", not [i for o in run3["ops"] for i in [o["id"]] if i in out3 or i in out4], (out3, out4))
for p in ("columns.txt", "cascade.txt", "billing_button.txt"):
    t = open(os.path.join(ROOT, "nightly", "live", p), encoding="utf-8").read()
    check("5b nightly/live/%s: the stamp sentence passes the run's inline board rows (--items)" % p,
          re.search(r"board_chargefac\.py stamp --file <that board_updates file> --items <", t) is not None, re.findall(r".{0,40}board_chargefac\.py stamp[^`]*", t)[:1])
    check("5b nightly/live/%s: <rows file> is only the stored rows of the cards the file touches - never ALL the board's rows (second review: ~500 rows no run can write out)" % p,
          "ALL the items rows" not in t and "of the cards already on the board that this file's ops touch, and only those" in t, re.findall(r"where <rows file> is.{0,160}", t)[:1])
    check("5b nightly/live/%s: a card missing from <rows file> gets only a visit it names (third review), and the page never shows or writes a badge worked out on a chart the card no longer has" % p,
          "gives a card missing from <rows file> only a visit it names" in t and "only a charge it names" not in t and "worked out on a chart the card no longer has" in t,
          re.findall(r"gives a card missing.{0,120}", t)[:1])

# ---- 5c. (second review 11/12, blocking) whatever --items holds, a stored visit badge is never replaced by a guess
KEEP2 = {"amdid": ch(1), "status": "william", "facility": "SNF", "need": "Secondary pending.", "chargefac": VISIT_1}     # on the board
run5 = {"schema": "irb-board-updates/1", "source": "backend billing run 2026-11-12T1839Z", "created": "2026-11-12T18:45:00Z", "ops": [
    {"op": "upsert", "collection": "items", "id": "keep-2", "set": {"amdid": ch(1), "facility": "SNF"}},
    {"op": "upsert", "collection": "items", "id": "fresh-2", "set": {"amdid": ch(1), "facility": "SNF", "patient": "", "dob": "", "need": "New card.", "status": "claude"}},
    {"op": "upsert", "collection": "items", "id": "x-moved-" + ch(1), "set": {"facility": "SNF (99309 10/2/2026)"}},
    # third review 11/12: a card stamp cannot see whole gets only a VISIT it names - a dos or facility-id match read from the op alone
    # could be outranked by a visit its stored row names (the page lets any named match replace another)
    {"op": "upsert", "collection": "items", "id": "dosonly-2", "set": {"amdid": ch(1), "facility": "SNF (99233 10/20/2026)"}},
    {"op": "upsert", "collection": "items", "id": "facid-2", "set": {"amdid": ch(1), "facility": "SNF (fac903)"}},
    {"op": "upsert", "collection": "items", "id": "visit-3", "set": {"amdid": ch(1), "facility": "SNF", "need": "Visit v19999001 denied."}},
    {"op": "upsert", "collection": "items", "id": "fresh-3", "set": {"amdid": ch(1), "facility": "SNF (99233 10/20/2026)", "created": "2026-11-12T18:45:00Z"}}]}
SHAPES = [("rows without the card", ITEMS_ROWS), ("an empty list", []),
          ("ArtifactData documents", [{"id": "keep-2", "version": 4, "data": KEEP2}]),
          ("a {documents: [...]} object", {"documents": [{"id": "keep-2", "version": 4, "data": KEEP2}], "next_cursor": None}),
          ("doc_id documents", [{"doc_id": "keep-2", "version": 4, "data": KEEP2}])]
got5 = {}
for n, (label, rows5) in enumerate(SHAPES):
    ip, rp = os.path.join(TMP, "items5_%d.json" % n), os.path.join(TMP, "board_updates_2026-11-12T18%02dZ.json" % (40 + n))
    json.dump(rows5, open(ip, "w")); json.dump(run5, open(rp, "w"), indent=1)
    r5, out5 = quiet(B.main, ["stamp", "--file", rp, "--items", ip], select=select)
    got5[label] = (r5, out5, {o["id"]: o["set"].get("chargefac") for o in json.load(open(rp))["ops"]})
g = got5["rows without the card"]
check("5c --items rows without the card (a partial read): a card on the board with a visit badge gets no guess - its badge is not known",
      g[0] == 0 and g[2]["keep-2"] is None and "not among the --items rows" in g[1], (g[2]["keep-2"], g[1]))
g = got5["an empty list"]
check("5c --items an empty list: read as no --items, the count printed - still no guess for that card",
      g[0] == 0 and g[2]["keep-2"] is None and "--items gave 0 row(s) - read as no --items" in g[1], (g[2]["keep-2"], g[1]))
for label in ("ArtifactData documents", "a {documents: [...]} object", "doc_id documents"):
    g = got5[label]
    check("5c --items as %s: the rows keep the document's id, so the card is seen whole and its visit badge kept" % label,
          g[0] == 0 and g[2]["keep-2"] is None and "--items gave 1 row(s)" in g[1] and "stronger rule (visit)" in g[1], (g[2]["keep-2"], g[1]))
check("5c a card stamp cannot see whole takes its chart only from the op's own amdid - never from the number its id ends with (the stored card may carry another)",
      all(v[2]["x-moved-" + ch(1)] is None for v in got5.values()), {k: (v[2]["x-moved-" + ch(1)] or {}).get("how") for k, v in got5.items()})
check("5c a new card (patient and dob in its set - --items cannot hold it) still gets even a guess, whatever --items holds",
      all((v[2]["fresh-2"] or {}).get("how") == "newest charge" for v in got5.values()), {k: (v[2]["fresh-2"] or {}).get("how") for k, v in got5.items()})
check("5c (third review) a card stamp cannot see whole gets no date-of-service match read from the op alone, whatever --items holds (a visit its stored row names would outrank it)",
      all(v[2]["dosonly-2"] is None and "read from the op alone" in v[1] for v in got5.values()), {k: ((v[2]["dosonly-2"] or {}).get("how"), v[1][-300:]) for k, v in got5.items()})
check("5c (third review) ... nor a facility-id match read from the op alone",
      all(v[2]["facid-2"] is None for v in got5.values()), {k: (v[2]["facid-2"] or {}).get("how") for k, v in got5.items()})
check("5c (third review) ... while a visit the op names is still written (nothing outranks a visit match), and a new card still gets a date-of-service match",
      all((v[2]["visit-3"] or {}).get("how") == "visit" and (v[2]["fresh-3"] or {}).get("how") == "dos" for v in got5.values()),
      {k: ((v[2]["visit-3"] or {}).get("how"), (v[2]["fresh-3"] or {}).get("how")) for k, v in got5.items()})
check("5c rows_from_items: ArtifactData documents give their rows under the document's id", [r["id"] for r in B.rows_from_items(os.path.join(TMP, "items5_2.json"))] == ["keep-2"]
      and [r["id"] for r in B.rows_from_items(os.path.join(TMP, "items5_3.json"))] == ["keep-2"] and [r["id"] for r in B.rows_from_items(os.path.join(TMP, "items5_4.json"))] == ["keep-2"])
WHAT_OLD_STAMP_WROTE = GUESS_1          # 000d983c wrote this guess for keep-2 in the first two shapes above - section 7c applies it to the page

# ---- 5d. (second review 11/12) a corrected chart number does not keep the old chart's badge; build re-sends no badge the page keeps
GUESS_6 = B.compute([{"id": "probe-6", "amdid": ch(6)}], select, now="2026-11-01T00:00:00Z")[0][1]     # chart 6's newest live charge
check("5d the stand-in: chart 6's newest live charge is a guess on chart 6", GUESS_6.get("how") == "newest charge" and GUESS_6.get("chart") == ch(6) and GUESS_6.get("name") == "Invented Gardens ALF", GUESS_6)
MOVED = os.path.join(TMP, "moved_rows.json")
json.dump([{"id": "moved-1", "amdid": ch(1), "status": "claude", "facility": "SNF", "need": "Pending.", "chargefac": VISIT_1}], open(MOVED, "w"))
run6 = {"schema": "irb-board-updates/1", "source": "backend billing run 2026-11-12T1939Z", "created": "2026-11-12T19:45:00Z", "ops": [
    {"op": "upsert", "collection": "items", "id": "moved-1", "set": {"amdid": ch(6), "facility": "SNF"}}]}
RUN6 = os.path.join(TMP, "board_updates_2026-11-12T1939Z.json"); json.dump(run6, open(RUN6, "w"), indent=1)
r6, out6 = quiet(B.main, ["stamp", "--file", RUN6, "--items", MOVED], select=select)
s6 = json.load(open(RUN6))["ops"][0]["set"].get("chargefac")
check("5d stamp: the run corrects the card's chart number - the old chart's visit badge is not kept, the new chart's facility is written",
      r6 == 0 and (s6 or {}).get("how") == "newest charge" and s6.get("chart") == ch(6) and s6.get("name") == "Invented Gardens ALF" and "stronger rule" not in out6, (s6, out6))
check("5d _keeps: a stronger badge stays on its own chart; not over a corrected chart, a named charge, a weaker stored guess, or a badge that does not say its chart",
      B._keeps(VISIT_1, GUESS_1) and not B._keeps(VISIT_1, GUESS_6) and not B._keeps(GUESS_1, VISIT_1) and not B._keeps(GUESS_1, dict(GUESS_1, how="open balance"))
      and not B._keeps({k: v for k, v in VISIT_1.items() if k != "chart"}, GUESS_1))
STORED = os.path.join(TMP, "stored_rows.json")
json.dump([{"id": "settle-1", "amdid": ch(1), "status": "claude", "facility": "SNF", "need": "Pending.", "chargefac": VISIT_1},
           {"id": "moved-2", "amdid": ch(6), "status": "claude", "facility": "SNF", "need": "Pending.", "chargefac": VISIT_1}], open(STORED, "w"))
OUT3 = os.path.join(TMP, "out_stored")
r, out = quiet(B.main, ["build", "--out", OUT3, "--stamp", "2026-11-12T1503Z", "--items", STORED], select=select)
bops = json.load(open(os.path.join(OUT3, "board_updates_2026-11-12T1503Z.json")))["ops"] if r == 0 else []
check("5d build: a stored visit badge is not re-sent as a guess on every build (the page keeps it); a card whose chart was corrected gets the new chart's facility",
      [(o["id"], o["set"]["chargefac"].get("chart")) for o in bops] == [("moved-2", ch(6))] and "1 card(s) keep the badge they have" in out, ([o["id"] for o in bops], out))

# ---- 5e. (third review 11/12, blocking) a chart corrected with no new badge: the old chart's badge is cleared, never left showing
NOFAC = B.compute([{"id": "probe-42", "amdid": ch(42)}], select, now="2026-11-01T00:00:00Z")[0]
check("5e the stand-in: chart 42's only charge has no facility - a card on it gets no badge", NOFAC[1] is None and "no live charge" in NOFAC[2], NOFAC[1:])
STALE_ROWS = os.path.join(TMP, "stale_rows.json")
json.dump([{"id": "stale-1", "amdid": ch(1), "status": "claude", "facility": "SNF", "need": "Pending.", "chargefac": VISIT_1},
           {"id": "same-42", "amdid": ch(42), "status": "claude", "facility": "SNF", "need": "Pending.", "chargefac": dict(VISIT_1, chart=ch(42))}], open(STALE_ROWS, "w"))
run7 = {"schema": "irb-board-updates/1", "source": "backend billing run 2026-11-12T2039Z", "created": "2026-11-12T20:45:00Z", "ops": [
    {"op": "upsert", "collection": "items", "id": "stale-1", "set": {"amdid": ch(42), "facility": "SNF"}},
    {"op": "upsert", "collection": "items", "id": "same-42", "set": {"facility": "SNF"}}]}
RUN7 = os.path.join(TMP, "board_updates_2026-11-12T2039Z.json"); json.dump(run7, open(RUN7, "w"), indent=1)
r7, out7 = quiet(B.main, ["stamp", "--file", RUN7, "--items", STALE_ROWS], select=select)
s7 = {o["id"]: o["set"] for o in json.load(open(RUN7))["ops"]}
check("5e stamp: the op moves the card to a chart with no badge - the old chart's visit badge is cleared (chargefac null), counted under 'not given', no row id printed",
      r7 == 0 and "chargefac" in s7["stale-1"] and s7["stale-1"]["chargefac"] is None and "cleared: worked out on another chart" in out7 and "stale-1" not in out7, (s7["stale-1"], out7))
check("5e stamp: a card with no badge found whose stored badge is on the chart it has keeps that badge (nothing written)", "chargefac" not in s7["same-42"], s7["same-42"])
check("5e stamp: the cleared badge passes the board_ops gate", not B.board_ops.clean_file_report(json.loads(json.dumps(json.load(open(RUN7))))))
STALE_B = os.path.join(TMP, "stale_build_rows.json")
json.dump([{"id": "stale-2", "amdid": ch(42), "status": "claude", "facility": "SNF", "need": "Pending.", "chargefac": VISIT_1},
           {"id": "same-42b", "amdid": ch(42), "status": "claude", "facility": "SNF", "need": "Pending.", "chargefac": dict(VISIT_1, chart=ch(42))}], open(STALE_B, "w"))
OUT4 = os.path.join(TMP, "out_stale")
r, out = quiet(B.main, ["build", "--out", OUT4, "--stamp", "2026-11-12T1504Z", "--items", STALE_B], select=select)
sops = json.load(open(os.path.join(OUT4, "board_updates_2026-11-12T1504Z.json")))["ops"] if r == 0 else []
check("5e build: a stored badge worked out on a chart the card no longer has, and nothing found on the chart it has - the file clears it (chargefac null), and only that card",
      [(o["id"], o["set"]) for o in sops] == [("stale-2", {"chargefac": None})], [(o["id"], o["set"]) for o in sops])
check("5e build: the clear is counted as such - not as a card that gets the charge's facility",
      "1 card(s) lose a badge worked out on a chart they no longer have" in out and "0 card(s) get the charge's facility" in out, out)
check("5e badge_source (what the badge then shows) follows the page: a badge on another chart is not 'charge facility'",
      B.badge_source({"amdid": ch(42), "facility": "SNF", "chargefac": VISIT_1}, None) == "generic"
      and B.badge_source({"amdid": ch(42), "facility": "SNF", "chargefac": dict(VISIT_1, chart=ch(42))}, None) == "charge facility"
      and B.badge_source({"facility": "SNF", "chargefac": VISIT_1}, None) == "charge facility", "")
ONC = getattr(B, "_on_card", None)
ON_CASES = [(VISIT_1, {"amdid": ch(1)}, True), (VISIT_1, {"amdid": ch(42)}, False), (VISIT_1, {"amdid": "%s, %s" % (ch(1), ch(3))}, True),
            (res["card-l"][0], {"amdid": ch(12)}, False), (res["card-l"][0], {"amdid": "%s, %s" % (ch(12), ch(13))}, True),
            (VISIT_1, {"id": "x-" + ch(42)}, True), (FACID_CF, {"amdid": ch(1)}, True), ({k: v for k, v in VISIT_1.items() if k != "chart"}, {"amdid": ch(42)}, True),
            (VISIT_1, {"pid": ch(42)}, False), (VISIT_1, {"chart": ch(1)}, True)]
check("5e _on_card: a badge is on the card while the card still has EVERY chart it was worked out on; a card with no chart number of its own, or a badge naming none, passes",
      ONC is not None and [ONC(cf, row) for cf, row, _ in ON_CASES] == [w for _, _, w in ON_CASES], ONC and [ONC(cf, row) for cf, row, _ in ON_CASES])

# ---- 5f. (third review 11/12) plan and build count the badge each card ENDS UP with - a card that keeps its visit badge is a visit
PLAN_ROWS = os.path.join(TMP, "plan_rows.json")
json.dump([{"id": "plan-1", "amdid": ch(1), "status": "claude", "facility": "SNF", "need": "Pending.", "chargefac": VISIT_1},
           {"id": "plan-2", "amdid": ch(42), "status": "claude", "facility": "SNF", "need": "Pending.", "chargefac": VISIT_1}], open(PLAN_ROWS, "w"))
r, out = quiet(B.main, ["plan", "--items", PLAN_ROWS], select=select)
check("5f plan: a card that keeps its visit badge is counted under the visit (not the guess this run found), and plan says it keeps it",
      r == 0 and 'found for 1 {"visit": 1}' in out and "newest charge" not in out and "1 card(s) keep the badge they have" in out, out)
check("5f plan: a badge worked out on another chart is counted as cleared, and the badge then shows the card's own facility text (generic), not the charge facility",
      "1 card(s) lose a badge worked out on a chart they no longer have" in out and '"charge facility": 1' in out and '"generic": 1' in out, out)

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
             {"id": "p-none", "amdid": ch(20)},
             # third review 11/12 (blocking): a badge worked out on a chart the card no longer has falls through to the next source
             {"id": "p-moved", "amdid": ch(7), "facility": "SNF", "chargefac": VISIT_1},
             {"id": "p-moved-fn", "amdid": ch(42), "chargefac": VISIT_1, "facnow": {"name": "Invented Southwood", "kind": "SNF", "dos": "10/02/2026"}},
             {"id": "p-fewer", "amdid": ch(12), "facility": "SNF", "chargefac": res["card-l"][0]},
             {"id": "p-added", "amdid": "%s, %s" % (ch(1), ch(3)), "facility": "SNF", "chargefac": VISIT_1},
             {"id": "p-nochart", "facility": "SNF", "chargefac": VISIT_1}]
    NPROBE = len(PROBE)
    KINDS = ["INVENTED SOUTHWOOD", "INVENTED HEALTH AND REHABILITATION CENTER", "INVENTED GENERAL HOSPITAL", "INVENTED GARDENS ALF", "INVENTED INDEPENDENT LIVING",
             "HCA REHAB", "INVENTED DEVELOPMENTAL CENTER", "NORTH FLORIDA SENIOR CARE", "SNF (99309)", "Westminster Invented", "Invented Place"]
    JS = os.path.join(TMP, "badge.js")
    open(JS, "w", encoding="utf-8").write(m1.group(0) + m2.group(0)[:-len("\n  function render(){")] +
        "\nconst probe=JSON.parse(require('fs').readFileSync(process.argv[2],'utf8'));\n"
        "process.stdout.write(JSON.stringify({info:probe.rows.map(r=>facInfo(r)),html:probe.rows.map(r=>facBadge(r)),kinds:probe.kinds.map(kindOf),\n"
        "  oncard:probe.oncard.map(([cf,row])=>typeof cfOnCard==='function'?cfOnCard(cf,row):null)}));\n")
    IN = os.path.join(TMP, "probe.json"); json.dump({"rows": PROBE, "kinds": KINDS, "oncard": [[cf, row] for cf, row, _ in ON_CASES]}, open(IN, "w"))
    scripts = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)</script>", page); bad = []
    for n, s in enumerate(scripts):
        p = os.path.join(TMP, "script%d.js" % n); open(p, "w", encoding="utf-8").write(s)
        cr = subprocess.run([NODE, "--check", p], capture_output=True, text=True, timeout=60)
        if cr.returncode: bad.append((n, cr.stderr.strip()[-200:]))
    check("7 every inline script of the page parses (node --check)", len(scripts) >= 2 and not bad, bad)
    pr = subprocess.run([NODE, JS, IN], capture_output=True, text=True, timeout=60)
    try: o = json.loads(pr.stdout)
    except ValueError: o = {"info": [None] * NPROBE, "html": [""] * NPROBE, "kinds": [], "oncard": []}
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
    # third review 11/12 (blocking): the badge is shown only while the card still has every chart it was worked out on
    pm, pf, pw, pa, pn = inf[5:10]; hm = o["html"][5]
    check("7 page: the card's chart was corrected and no new badge came - the old chart's badge is not shown (its facility, visit and date are gone; the card's own facility text shows, as a guess)",
          isinstance(pm, dict) and pm.get("src") == "guess" and "Invented Nursing and Rehabilitation Center" not in hm and "19999001" not in hm and "10/02/2026" not in hm, (pm, hm))
    check("7 page: ... with facnow on the card, facnow shows instead", isinstance(pf, dict) and pf.get("src") == "chart" and pf.get("name") == "Invented Southwood", pf)
    check("7 page: a card left with only some of the charts the badge was worked out on does not show it", isinstance(pw, dict) and pw.get("src") == "guess", pw)
    check("7 page: a card that gained a chart, and a card with no chart number of its own (matched through its id / text), still show the badge",
          isinstance(pa, dict) and pa.get("src") == "charge" and isinstance(pn, dict) and pn.get("src") == "charge", (pa, pn))
    check("7 page and helper decide alike whether a badge is on the card (cfOnCard = _on_card)",
          o.get("oncard") == [w for _, _, w in ON_CASES], (o.get("oncard"), [w for _, _, w in ON_CASES]))

# ---- 7b. (review 11/12) the page's applyOp against a stand-in store whose update() merges like the real one
m_apply = re.search(r"\n  const CF_RANK=[\s\S]*?\n  async function applyOp\(op, now, fileCreated\)\{[\s\S]*?\n  \}\n(?=  async function runSync\()", page)   # with keepsBadge
m_same = re.search(r"\n  const isObj=[^\n]+\n  const canon=[^\n]+\n  const same=[^\n]+\n", page)
m_coll = re.search(r"\n  const COLL_OK=[^\n]+\n", page)
check("7b applyOp and the helpers it uses are where the test expects them in the page", bool(m_apply and m_same and m_coll))
if NODE and m1 and m2 and m_apply and m_same and m_coll:
    JS2 = os.path.join(TMP, "apply.js")
    open(JS2, "w", encoding="utf-8").write(
        "// stand-ins: the board store - update() merges nested objects key by key, anything else replaces the field (db contract 0.2.96)\n"
        "const store={}; const clone=v=>JSON.parse(JSON.stringify(v)); const isO=v=>!!v&&typeof v==='object'&&!Array.isArray(v);\n"
        "function mergeS(a, b){ const o=Object.assign({}, a); for(const k of Object.keys(b)){ const v=b[k]; o[k]=(isO(v)&&isO(o[k]))?mergeS(o[k], v):v; } return o; }\n"
        "const has=p=>Object.prototype.hasOwnProperty.call(store, p);\n"
        "const db={doc(p){ return {get:async()=>({exists:has(p), data:()=>clone(store[p])}), set:async d=>{ store[p]=clone(d); },\n"
        "  update:async d=>{ if(!has(p)) throw Object.assign(new Error('no such document'), {code:'invalid_argument'}); store[p]=mergeS(store[p], clone(d)); },\n"
        "  delete:async()=>{ delete store[p]; }}; }};\n"
        "const withRetry=fn=>fn(); const CHART=/^\\d{4,}$/; const chartSibs=()=>[]; const sibsLine=()=>'';\n"
        + m_coll.group(0) + m_same.group(0) + m_apply.group(0) + m1.group(0) + m2.group(0)[:-len("\n  function render(){")] +
        "\nconst probe=JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));\n"
        "(async()=>{ const out=[];\n"
        "  for(const s of probe.steps){\n"
        "    if(s.seed){ store[s.seed]=clone(s.row); continue; }\n"
        "    let err='', ret=null; try{ ret=(await applyOp(s.op, s.now, s.created))||null; }catch(e){ err=String(e&&e.message||e); }\n"
        "    const row=store['items/'+s.op.id]||null;\n"
        "    out.push({err, ret, updated:row&&row.updated, chargefac:row&&row.chargefac, facility:row&&row.facility, need:row&&row.need, badge:row?facBadge(row):''});\n"
        "  }\n"
        "  process.stdout.write(JSON.stringify({out, guard:facInfo({chargefac:probe.guard}), fromid:facBadge({chargefac:probe.fromid}), rank:CF_RANK, guess:CF_GUESS}));\n"
        "})();\n")
    # x1 is on chart 1 - the chart HOME_CF (card-a's badge) was worked out on; third review: a badge from a chart the card does not have is never written
    STEPS = [{"seed": "items/x1", "row": {"id": "x1", "status": "done", "amdid": ch(1), "updated": "2026-11-10T09:00:00Z", "chargefac": HOSP_CF}},
             {"op": {"op": "update", "collection": "items", "id": "x1", "set": {"chargefac": HOME_CF}}, "now": "2026-11-12T16:00:00Z", "created": "2026-11-12T15:00:00Z"},
             {"op": {"op": "upsert", "collection": "items", "id": "x1", "set": {"need": "Asked again."}}, "now": "2026-11-12T16:05:00Z", "created": "2026-11-12T16:04:00Z"},
             {"op": {"op": "update", "collection": "items", "id": "x1", "set": {"chargefac": HOME_CF}, "append": NOTE("Badge looked at.")}, "now": "2026-11-12T16:10:00Z", "created": "2026-11-12T16:09:00Z"}]
    GUARD = {"name": "Invented Nursing and Rehabilitation Center", "kind": "SNF", "res": {"name": "Invented Gardens ALF", "kind": "ALF", "thru": "8/26"}, "also": []}
    IN2 = os.path.join(TMP, "probe_apply.json"); json.dump({"steps": STEPS, "guard": GUARD, "fromid": xres["fromid-9700021"][0]}, open(IN2, "w"))
    pr = subprocess.run([NODE, JS2, IN2], capture_output=True, text=True, timeout=60)
    try: o2 = json.loads(pr.stdout)
    except ValueError: o2 = {"out": [{}] * 3, "guard": {}, "fromid": ""}
    check("7b node ran the page's applyOp against the stand-in store", pr.returncode == 0 and len(o2["out"]) == 3 and not any(x.get("err") for x in o2["out"]), (pr.stderr[-400:], o2["out"]))
    a1, a2, a3 = (o2["out"] + [{}, {}, {}])[:3]
    check("7b an op that only sets chargefac leaves the row's `updated` alone (a done card keeps its done date; a later run file is not made stale)",
          a1.get("updated") == "2026-11-10T09:00:00Z", a1.get("updated"))
    check("7b ... and the nursing-home badge written over the hospital one shows no 'resident at' / 'also billed at' left over from it",
          "Invented Nursing and Rehabilitation Center" in a1.get("badge", "") and "resident at" not in a1.get("badge", "") and "also billed at" not in a1.get("badge", "")
          and (a1.get("chargefac") or {}).get("res") is None and (a1.get("chargefac") or {}).get("also") == [], (a1.get("badge"), a1.get("chargefac")))
    check("7b any other op still stamps `updated` (a set of need; a chargefac set that comes with an appended note)",
          a2.get("updated") == "2026-11-12T16:05:00Z" and a3.get("updated") == "2026-11-12T16:10:00Z", (a2.get("updated"), a3.get("updated")))
    check("7b page: a home's own badge never shows 'resident at' (a res left on it is ignored)", isinstance(o2["guard"], dict) and o2["guard"].get("src") == "charge" and o2["guard"].get("res") is None, o2["guard"])
    check("7b page: a badge whose chart number came from the card's id says so in its tooltip", "read from the end of this card" in o2["fromid"] and "Invented Gardens ALF" in o2["fromid"], o2["fromid"])

    # ---- 7c. (second review 11/12, blocking) applyOp keeps a stronger stored badge whatever the file holds - unless the chart was corrected
    T0 = "2026-11-10T09:00:00Z"
    DOS_1 = B.compute([{"id": "probe-dos", "amdid": ch(1), "facility": "SNF (99233 10/20/2026)"}], select, now="2026-11-01T00:00:00Z")[0][1]
    FROMID_VISIT = B.compute([{"id": "x-9700021", "need": "Visit v19999210 denied."}], select, now="2026-11-01T00:00:00Z")[0][1]
    FROMID_GUESS = xres["fromid-9700021"][0]
    def step(i, s, kind="update"): return {"op": {"op": kind, "collection": "items", "id": i, "set": s}, "now": "2026-11-12T16:00:00Z", "created": "2026-11-12T15:00:00Z"}
    def seed(i, **row): return {"seed": "items/" + i, "row": dict(row, id=i, status="claude", updated=T0)}
    S2 = [seed("keep-2", **KEEP2), step("keep-2", {"chargefac": WHAT_OLD_STAMP_WROTE}),                                          # 0 the blocking case
          step("keep-2", {"chargefac": GUESS_1, "facility": "Invented Nursing and Rehabilitation Center"}, kind="upsert"),         # 1 a guess + a change
          seed("moved-3", amdid=ch(1), chargefac=VISIT_1), step("moved-3", {"amdid": ch(6), "chargefac": GUESS_6}, kind="upsert"),   # 2 chart corrected now
          seed("moved-4", amdid=ch(6), chargefac=VISIT_1), step("moved-4", {"chargefac": GUESS_6}),                                 # 3 chart corrected before
          seed("up-1", amdid=ch(1), chargefac=GUESS_1), step("up-1", {"chargefac": VISIT_1}),                                       # 4 a match over a guess
          seed("up-2", amdid=ch(1), chargefac=VISIT_1), step("up-2", {"chargefac": DOS_1}),                                         # 5 dos over visit
          seed("rep-1", amdid=ch(1), chargefac=VISIT_1),
          {"op": {"op": "replace", "collection": "items", "id": "rep-1", "data": {"amdid": ch(1), "status": "claude", "need": "Rewritten.", "chargefac": GUESS_1}},
           "now": "2026-11-12T16:00:00Z", "created": "2026-11-12T15:00:00Z"},                                                     # 6 a replace
          seed("x-9700021", chargefac=FROMID_VISIT), step("x-9700021", {"chargefac": FROMID_GUESS}),                               # 7 no chart field
          seed("legacy-1", amdid=ch(1), chargefac={k: v for k, v in VISIT_1.items() if k != "chart"}), step("legacy-1", {"chargefac": GUESS_1})]   # 8
    # third review 11/12 - blocking: a correction file moves the card to a chart with no badge (no new badge with it)
    S2 += [seed("fix-1", amdid=ch(1), facility="SNF", chargefac=VISIT_1), step("fix-1", {"amdid": ch(42), "facility": "SNF"}, kind="upsert")]   # 9
    # third review 11/12 - an incoming badge worked out on a chart the card does not have is never written (merge and replace, a new row too)
    DOS_6 = B.compute([{"id": "probe-dos6", "amdid": ch(6), "facility": "SNF (99349 6/1/2026)"}], select, now="2026-11-01T00:00:00Z")[0][1]
    S2 += [seed("in-1", amdid=ch(1), chargefac=VISIT_1), step("in-1", {"chargefac": DOS_6}),                                     # 10 a dos badge on chart 6
           seed("in-2", amdid=ch(1), chargefac=GUESS_1), step("in-2", {"chargefac": GUESS_6}),                                   # 11 a guess on chart 6 over a guess
           seed("in-3", amdid=ch(1), chargefac=VISIT_1),
           {"op": {"op": "replace", "collection": "items", "id": "in-3", "data": {"amdid": ch(1), "status": "claude", "need": "Rewritten.", "chargefac": DOS_6}},
            "now": "2026-11-12T16:00:00Z", "created": "2026-11-12T15:00:00Z"},                                                  # 12 replace: the stored badge is carried over
           step("in-4", {"amdid": ch(1), "facility": "SNF", "chargefac": GUESS_6}, kind="upsert"),                               # 13 a new row
           seed("in-5", amdid=ch(1), chargefac=VISIT_1),
           {"op": {"op": "replace", "collection": "items", "id": "in-5", "data": {"amdid": ch(42), "status": "claude", "need": "Rewritten.", "chargefac": GUESS_6}},
            "now": "2026-11-12T16:00:00Z", "created": "2026-11-12T15:00:00Z"}]                                                  # 14 replace: neither badge fits
    # third review 11/12 - the helper's clear (chargefac null): it removes another chart's badge, never one the card's chart still supports
    S2 += [seed("clr-1", amdid=ch(42), chargefac=VISIT_1), step("clr-1", {"chargefac": None}),                                   # 15 a badge on another chart
           seed("clr-2", amdid=ch(1), chargefac=VISIT_1), step("clr-2", {"chargefac": None})]                                    # 16 a file from an older copy
    NS2 = sum(1 for s in S2 if "op" in s)
    IN3 = os.path.join(TMP, "probe_guard.json"); json.dump({"steps": S2, "guard": {}, "fromid": {}}, open(IN3, "w"))
    pr = subprocess.run([NODE, JS2, IN3], capture_output=True, text=True, timeout=60)
    try: o3 = json.loads(pr.stdout)
    except ValueError: o3 = {"out": []}
    c = (o3["out"] + [{}] * NS2)[:NS2]
    check("7c node ran the page's applyOp with the badge guard", pr.returncode == 0 and len(o3["out"]) == NS2 and not any(x.get("err") for x in o3["out"]), (pr.stderr[-400:], o3["out"][:2]))
    check("7c page: the guess a stamp wrote for a card it could not see (the blocking case) leaves the card's visit badge - nothing written, `updated` unchanged",
          c[0].get("ret") == "kept" and (c[0].get("chargefac") or {}).get("how") == "visit" and c[0].get("updated") == T0, c[0])
    check("7c page: a guess that comes with a real change - the visit badge stays, the change lands and `updated` moves",
          (c[1].get("chargefac") or {}).get("how") == "visit" and c[1].get("facility") == "Invented Nursing and Rehabilitation Center" and c[1].get("updated") == "2026-11-12T16:00:00Z", c[1])
    check("7c page: the op corrects the chart number - the new chart's badge replaces the old chart's visit badge",
          (c[2].get("chargefac") or {}).get("how") == "newest charge" and c[2]["chargefac"].get("chart") == ch(6), c[2])
    check("7c page: the chart was corrected earlier (the badge still the old chart's visit) - the new chart's badge replaces it",
          (c[3].get("chargefac") or {}).get("how") == "newest charge" and c[3]["chargefac"].get("chart") == ch(6), c[3])
    check("7c page: a visit match replaces a guess, and a date-of-service match replaces a visit match (a charge the card names is never held back)",
          (c[4].get("chargefac") or {}).get("how") == "visit" and (c[5].get("chargefac") or {}).get("how") == "dos", (c[4].get("chargefac"), c[5].get("chargefac")))
    check("7c page: a replace over a row with a stronger badge carries that badge into the new row",
          (c[6].get("chargefac") or {}).get("how") == "visit" and c[6].get("need") == "Rewritten.", c[6])
    check("7c page: a card with no chart number of its own (matched through its id) keeps its visit badge against a guess on that chart",
          c[7].get("ret") == "kept" and (c[7].get("chargefac") or {}).get("how") == "visit", c[7])
    check("7c page: a badge that does not say its chart is not protected", (c[8].get("chargefac") or {}).get("how") == "newest charge", c[8])
    check("7c page (third review, blocking): an op moves the card to a chart with no badge - the old chart's visit badge no longer shows (the card's own facility text does, as a guess)",
          "Invented Nursing and Rehabilitation Center" not in c[9].get("badge", "") and "19999001" not in c[9].get("badge", "") and "facbadge unknown" in c[9].get("badge", ""), c[9])
    check("7c page (third review): a date-of-service badge worked out on another chart is not written over the card's visit badge ('kept', `updated` unchanged)",
          c[10].get("ret") == "kept" and (c[10].get("chargefac") or {}).get("how") == "visit" and c[10]["chargefac"].get("chart") == ch(1) and c[10].get("updated") == T0, c[10])
    check("7c page (third review): a guess worked out on another chart does not replace the card's own guess",
          c[11].get("ret") == "kept" and (c[11].get("chargefac") or {}).get("chart") == ch(1) and c[11].get("updated") == T0, c[11])
    check("7c page (third review): a replace whose badge was worked out on another chart carries the card's own badge over instead",
          (c[12].get("chargefac") or {}).get("how") == "visit" and c[12]["chargefac"].get("chart") == ch(1) and c[12].get("need") == "Rewritten.", c[12])
    check("7c page (third review): a new row gets no badge worked out on a chart it does not have", not c[13].get("err") and c[13].get("chargefac") in (None, {}), c[13])
    check("7c page (third review): a replace onto a chart neither badge was worked out on writes no badge", c[14].get("chargefac") is None and c[14].get("need") == "Rewritten.", c[14])
    check("7c page (third review): the helper's clear removes a badge worked out on a chart the card no longer has, and leaves `updated` alone",
          c[15].get("chargefac") is None and c[15].get("ret") != "kept" and c[15].get("updated") == T0, c[15])
    check("7c page (third review): a clear from a file made on an older copy never wipes a badge the card's chart still supports ('kept')",
          c[16].get("ret") == "kept" and (c[16].get("chargefac") or {}).get("how") == "visit" and c[16].get("updated") == T0, c[16])
    check("7c the page's rule table equals the helper's (RANK, GUESS) - the two checks stay in step",
          o3.get("rank") == B.RANK and o3.get("guess") == list(getattr(B, "GUESS", ())), (o3.get("rank"), o3.get("guess")))

    # ---- 7d. (third review 11/12) the page's runSync, against a stand-in Drive inbox and store: an op the page kept is not a change
    m_sync = re.search(r"\n  const INBOX_ID=[\s\S]*?\n  async function runSync\(reason\)\{[\s\S]*?\n  \}\n(?=  window\.__ehpaRefresh=)", page)
    check("7d the page's Drive sync code is where the test expects it", bool(m_sync))
    if m_sync:
        JS4 = os.path.join(TMP, "sync.js")
        open(JS4, "w", encoding="utf-8").write(
            "const store={}; const clone=v=>JSON.parse(JSON.stringify(v)); const isO=v=>!!v&&typeof v==='object'&&!Array.isArray(v);\n"
            "function mergeS(a, b){ const o=Object.assign({}, a); for(const k of Object.keys(b)){ const v=b[k]; o[k]=(isO(v)&&isO(o[k]))?mergeS(o[k], v):v; } return o; }\n"
            "const has=p=>Object.prototype.hasOwnProperty.call(store, p);\n"
            "const db={doc(p){ return {get:async()=>({exists:has(p), data:()=>clone(store[p])}), set:async d=>{ store[p]=clone(d); },\n"
            "  update:async d=>{ if(!has(p)) throw Object.assign(new Error('no such document'), {code:'invalid_argument'}); store[p]=mergeS(store[p], clone(d)); },\n"
            "  delete:async()=>{ delete store[p]; }, acquire:async()=>({acquired:true})}; }};\n"
            "const withRetry=fn=>fn(); const CHART=/^\\d{4,}$/; const chartSibs=()=>[]; const sibsLine=()=>''; const when=v=>String(v||'');\n"
            "const els={}; const $=s=>els[s]||(els[s]={textContent:'', innerHTML:'', className:'', disabled:false, addEventListener(){}});\n"
            + m1.group(0) + m2.group(0)[:-len("\n  function render(){")] + m_sync.group(0) +
            "\nconst probe=JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));\n"
            "(async()=>{\n"
            "  for(const [p, row] of probe.seed) store[p]=clone(row);\n"
            "  mcp={callTool:async(server, tool)=>{\n"
            "    if(tool==='search_files') return {payload:{files:[{id:'f-badge', title:'board_updates_2026-11-12T1500Z.json', createdTime:new Date().toISOString()}]}};\n"
            "    if(tool==='download_file_content') return {payload:{content:Buffer.from(JSON.stringify(probe.file), 'utf8').toString('base64')}};\n"
            "    throw Object.assign(new Error('unexpected tool '+tool), {code:'tool_error'}); }};\n"
            "  await runSync('test');\n"
            "  const reg=store['meta/drive_sync']||{};\n"
            "  process.stdout.write(JSON.stringify({entry:(reg.applied||{})['f-badge']||null, log:$('#sync-log').innerHTML, status:$('#sync-st').textContent,\n"
            "    rows:probe.seed.map(([p])=>store[p])}));\n"
            "  process.exit(0);\n"
            "})();\n")
        SEED = [["items/sync-1", dict(KEEP2, id="sync-1", updated=T0)], ["items/sync-2", dict(KEEP2, id="sync-2", updated=T0)],
                ["items/sync-3", {"id": "sync-3", "amdid": ch(1), "status": "claude", "need": "Pending.", "updated": T0}]]
        FILE = {"schema": "irb-board-updates/1", "source": "tools/db/board_chargefac.py build 2026-11-12T1500Z (read-only on Neon)", "created": "2026-11-12T15:00:00Z",
                "ops": [{"op": "update", "collection": "items", "id": "sync-1", "set": {"chargefac": GUESS_1}},
                        {"op": "update", "collection": "items", "id": "sync-2", "set": {"chargefac": GUESS_6}},
                        {"op": "update", "collection": "items", "id": "sync-3", "set": {"need": "Asked again."}}]}
        IN4 = os.path.join(TMP, "probe_sync.json"); json.dump({"seed": SEED, "file": FILE}, open(IN4, "w"))
        pr = subprocess.run([NODE, JS4, IN4], capture_output=True, text=True, timeout=60)
        try: o4 = json.loads(pr.stdout)
        except ValueError: o4 = {"entry": None, "log": "", "status": "", "rows": []}
        e4 = o4.get("entry") or {}
        check("7d node ran the page's runSync: the file was applied (the real change landed, both badges stayed)",
              pr.returncode == 0 and e4.get("failed") == 0 and [((r or {}).get("chargefac") or {}).get("how") for r in o4["rows"][:2]] == ["visit", "visit"]
              and (o4["rows"][2:] or [{}])[0].get("need") == "Asked again.", (pr.stderr[-400:], o4))
        check("7d the registry counts only the op that wrote something as a change; the two kept badges are counted as kept",
              e4.get("ops") == 1 and e4.get("kept") == 2, e4)
        check("7d the Applied files list and the sync line say '1 change' and '2 kept' - never '3 changes'",
              "1 change" in o4["log"] and "2 kept" in o4["log"] and "3 change" not in o4["log"] and "— 1 change" in o4["status"] and "2 kept" in o4["status"], (o4["log"], o4["status"]))

# ---- 8. what it did not touch
check("8 every statement sent to the database was a SELECT", all(re.match(r"^\s*(select|with)\b", s, re.I) for s in SQL) and len(SQL) > 10)
check("8 no module that talks to AdvancedMD was loaded", all(m not in sys.modules for m in ("amd", "txh", "resave", "void_tx", "era_clear")))
shutil.rmtree(TMP, ignore_errors=True)
AFTER = snapshot()
check("8 nothing was written in the repository while the test ran", AFTER == BEFORE, sorted(set(AFTER.items()) ^ set(BEFORE.items()))[:5])
print("\ntest_board_chargefac: %d checks, %d failed%s" % (RAN[0], len(FAILS), "" if not FAILS else " - " + "; ".join(FAILS)[:1200]))
sys.exit(1 if FAILS else 0)
