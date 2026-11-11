#!/usr/bin/env python3
# PLAIN ENGLISH (offline self-test, 11/11/2026): scripts/helpers/ccm_build.py - every CCM note built from the practice's Neon database.
# Decides: nothing. With a STAND-IN for the database (no network) it proves that the builder:
#   - only ever sends SELECT statements (anything else is refused before it leaves);
#   - lists the charts with a CCM charge for ccm_patients.py, into the workspace, never into the repository;
#   - builds one record per patient per calendar month from the charge lines, with the flags of ccm_notes.py (a duplicate 99487, a second
#     99489, a line billed under another clinician), the insurance in force that month (lowest billing sequence), and the patient's name
#     and birth date from ccm_patients.py - a month without them waits ("no name yet");
#   - writes the database documents (patients, months) for neon_db.py load-docs and the hub page's documents (config, notes - each well
#     under the page database's 256 KiB limit, the statement stored once per document) and leaves a SIGNED month exactly as it was;
#   - records a signing from the hub page only when it matches the stored draft (hash, day written, who, when): a changed note, a forged
#     hash, a month with no draft and a month already signed are refused or skipped, each with its reason.
# Never touches: Neon, AdvancedMD, the network (the stand-in answers the queries). Nothing is started as a program. No patient data:
#   every name and date is invented and put together at run time.
# Run: python3 tools/selftest/test_ccm_build.py   (exit 1 on any failure)
import os, sys, re, json, shutil, tempfile, datetime, importlib.util
import socket as _socket
def _no_network(*a, **k): raise RuntimeError("the self-test must not use the network")
_socket.socket.connect = _no_network; _socket.socket.connect_ex = _no_network; _socket.create_connection = _no_network
sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PATH = os.path.join(ROOT, "scripts", "helpers", "ccm_build.py")
FAILS = []; RAN = [0]
def check(name, cond, extra=""):
    RAN[0] += 1
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else "  -> " + str(extra)[:600]))
    if not cond: FAILS.append(name)
src = open(PATH, encoding="utf-8").read() if os.path.exists(PATH) else ""
names = {m.split()[0].split(".")[0] for k, r in re.findall(r"^(import|from)[ \t]+([^\n#;]+)", src, re.M) for m in (r.split(",") if k == "import" else [r]) if m.strip()}
check("the helper is there and loads the standard library and ccm_notes only (nothing that talks to AdvancedMD)", src != "" and names <= {"os", "sys", "re", "json", "hashlib", "datetime", "collections", "urllib", "ccm_notes"}, sorted(names))
if FAILS: print("\ntest_ccm_build: %d checks, %d failed" % (RAN[0], len(FAILS))); sys.exit(1)
def snapshot():
    out = {}
    for dp, dn, fn in os.walk(ROOT):
        dn[:] = [x for x in dn if x != ".git"]
        for f in fn:
            try: out[os.path.join(dp, f)] = os.stat(os.path.join(dp, f)).st_mtime_ns
            except OSError: pass
    return out
BEFORE = snapshot()
spec = importlib.util.spec_from_file_location("ccm_build_t", PATH); B = importlib.util.module_from_spec(spec); spec.loader.exec_module(B)
N = B.N

# ---- the stand-in database
def ch(n): return "pat%d" % (9700000 + n)
LINES = [  # chart, charge, visit, dos, cpt, units, provider, facility
    (ch(1), "c11", "v11", "2026-08-20", "99487", "1", "WEFFI", "Invented Nursing Center"), (ch(1), "c12", "v11", "2026-08-20", "99489", "1", "WEFFI", "Invented Nursing Center"),
    (ch(1), "c13", "v13", "2026-09-17", "99487", "1", "WEFFI", "Invented Nursing Center"),
    (ch(2), "c21", "v21", "2026-08-25", "99487", "1", "WEFFI", "Invented ALF"), (ch(2), "c22", "v22", "2026-08-27", "99487", "1", "WEFFI", "Invented ALF"),
    (ch(3), "c31", "v31", "2026-08-20", "99487", "1", "WEFFI", "Invented ALF"), (ch(3), "c32", "v31", "2026-08-20", "99489", "2", "WEFFI", "Invented ALF"),
    (ch(4), "c41", "v41", "2026-08-20", "99487", "1", "GARCIA", "Invented ALF"),
    (ch(5), "c51", "v51", "2026-08-22", "99487", "1", "WEFFI", "Invented ALF"),
]
LINES += [(ch(10 + i), "cx%d" % i, "vx%d" % i, "2026-07-%02d" % (1 + i % 28), "99487", "1", "WEFFI", "Invented Nursing Center") for i in range(320)]
PLANS = [(ch(1), "INVENTED MEDICARE", "2020-01-01", "", "1"), (ch(1), "INVENTED SUPPLEMENT", "2020-01-01", "", "2"),
         (ch(2), "OLD PLAN", "2019-01-01", "2026-07-31", "1"), (ch(2), "NEW PLAN", "2026-08-01", "", "2")]
SIGNED = set(); DRAFTS = {}; SQL = []
def select(sql, params=()):
    SQL.append(sql)
    if not re.match(r"^\s*(select|with)\b", sql, re.I): raise AssertionError("not a SELECT: " + sql[:60])
    if "from amd.charges c" in sql: return [list(r) for r in LINES]
    if "from amd.chart_plans" in sql: return [list(r) for r in PLANS]
    if "collection = 'signed'" in sql: return [[x] for x in sorted(SIGNED)]
    if "collection = 'months'" in sql: return [[i, json.dumps(DRAFTS[i])] for i in params[0].split(",") if i in DRAFTS]
    if "select distinct chart_id" in sql: return [[c] for c in sorted({r[0] for r in LINES})]
    raise AssertionError("unexpected query: " + sql[:80])
def shown(n): return "ZZ" + "BUILDTEST" + chr(65 + n) + "," + "INVENTED" + chr(65 + n)
TMP = tempfile.mkdtemp(prefix="ccm_build_test_"); WS = os.path.join(TMP, "ws"); OUT = os.path.join(TMP, "out")
os.environ["BILLING_WORKSPACE"] = WS
os.makedirs(os.path.join(WS, "ccm"))
with open(os.path.join(WS, "ccm", "ccm_patients.jsonl"), "w") as f:
    for n in (1, 2, 3, 4):
        f.write(json.dumps({"chart": ch(n), "name": shown(n), "dob": (datetime.date(1935, 1, 1) + datetime.timedelta(days=200 * n)).isoformat(), "sex": "F", "read_at": "2026-11-11T09:00:00Z"}) + "\n")
    f.write(json.dumps({"chart": ch(5), "error": "HTTP 500", "read_at": "2026-11-11T09:00:00Z"}) + "\n")

# ---- 1. reads only
try: B.neon_select("update raw.documents set body = '{}'"); refused = ""
except ValueError as e: refused = str(e)
check("1 anything but one SELECT is refused before it leaves (the builder never writes to the database itself)", "reads only" in refused, refused)
check("1 charts: the charts with a CCM charge are listed in the workspace for ccm_patients.py", B.main(["charts"], select=select) == 0 and len(json.load(open(os.path.join(WS, "ccm", "ccm_charts.json")))["charts"]) == 325)
os.environ["BILLING_WORKSPACE"] = os.path.join(ROOT, "tmp_never"); r = B.main(["charts"], select=select); os.environ["BILLING_WORKSPACE"] = WS
check("1 a workspace inside the repository is refused", r == 2 and not os.path.exists(os.path.join(ROOT, "tmp_never")))

# ---- 2. the records
recs, _ = B.build_months(select, B.read_patients(WS)); R = {r["id"]: r for r in recs}
check("2 one record per patient per calendar month (325 charts; one chart has two months)", len(recs) == 326 and "%s_2026-09" % ch(1) in R and "%s_2026-08" % ch(1) in R, len(recs))
r1 = R["%s_2026-08" % ch(1)]
check("2 99487 with one 99489 is ready to sign: 90-minute statement, his name on the provider line, the patient's name and birth date on the note",
      r1["status"] == "ready to sign" and r1["minutes"] == 90 and r1["fields"]["provider"] == "EFFINGER, WILLIAM" and r1["fields"]["patient"] == shown(1) and r1["fields"]["dob"] != "", r1["fields"])
check("2 the insurance is the plan in force that month with the lowest billing sequence; an ended plan is not used", r1["insurance"] == "INVENTED MEDICARE" and R["%s_2026-08" % ch(2)]["insurance"] == "NEW PLAN", (r1["insurance"], R["%s_2026-08" % ch(2)]["insurance"]))
check("2 a duplicate 99487, a second unit of 99489 and a line billed under another clinician are flagged for his own eyes",
      "duplicate" in R["%s_2026-08" % ch(2)]["flag"] and R["%s_2026-08" % ch(3)]["statement"] is None and "billed under GARCIA" in R["%s_2026-08" % ch(4)]["flag"] and all(R["%s_2026-08" % ch(n)]["status"] == "flagged" for n in (2, 3, 4)))
check("2 a month whose patient's name was not read (a failed read) waits: no name yet", R["%s_2026-08" % ch(5)]["status"] == "no name yet" and R["%s_2026-07" % ch(10)]["status"] == "no name yet")

# ---- 3. the files
SIGNED.add("%s_2026-09" % ch(1))
check("3 build writes the database documents and the hub documents", B.main(["build", "--out", OUT], select=select) == 0)
months = os.listdir(os.path.join(OUT, "neon", "months")); pts = os.listdir(os.path.join(OUT, "neon", "patients"))
check("3 a signed month is final: its record is not written again", "%s_2026-09.json" % ch(1) not in months and len(months) == 325, len(months))
check("3 patient documents only for charts whose name was read", sorted(pts) == sorted("%s.json" % ch(n) for n in (1, 2, 3, 4)), pts)
md = json.load(open(os.path.join(OUT, "neon", "months", "%s_2026-08.json" % ch(1))))
check("3 a month document carries the charge lines, codes, statement, flag, insurance, the note's fields and their hash", md["codes"] == ["99487", "99489"] and len(md["charges"]) == 2 and md["fields_sha"] == N.hashlib.sha256(N.canon(md["fields"]).encode("utf-8")).hexdigest() and md["_written"])
hub = {}
for dp, _, fn in os.walk(os.path.join(OUT, "hub")):
    for f in fn: hub[os.path.relpath(os.path.join(dp, f), os.path.join(OUT, "hub"))] = os.path.getsize(os.path.join(dp, f))
cfg = json.load(open(os.path.join(OUT, "hub", "config", "practice.json")))
check("3 the hub documents: one per 150 notes of a month, each well under the page database's 256 KiB limit", all(s < 200 * 1024 for s in hub.values()) and "notes/2026-07-1.json" in hub and "notes/2026-07-3.json" in hub and "notes/2026-07-4.json" not in hub, hub)
n07 = json.load(open(os.path.join(OUT, "hub", "notes", "2026-07-1.json")))
check("3 the statement is stored once per document and every note points to it; the note's other fields are complete",
      set(n07["statements"]) == {"60"} and all(x["m"] == "60" and "statement" not in x["f"] and set(x["f"]) == set(N.FIELD_KEYS) - {"statement"} for x in n07["notes"]))
check("3 the page's practice document: letterhead, signer, and the counts by status (the signed month counted as signed)",
      cfg["practice"] == "North Florida Senior Care" and cfg["signer"] == "EFFINGER, WILLIAM" and cfg["counts"] == {"notes": 326, "ready": 1, "flagged": 3, "noname": 321, "signed": 1}, cfg["counts"])
os.environ["BILLING_WORKSPACE"] = WS
check("3 an output folder inside the repository is refused", B.main(["build", "--out", os.path.join(ROOT, "tmp_never2")], select=select) == 2 and not os.path.exists(os.path.join(ROOT, "tmp_never2")))

# ---- 4. signings from the hub page
DRAFTS.update({i: json.load(open(os.path.join(OUT, "neon", "months", i + ".json"))) for i in ("%s_2026-08" % ch(1), "%s_2026-08" % ch(2), "%s_2026-08" % ch(3))})
F1 = DRAFTS["%s_2026-08" % ch(1)]["fields"]; W = datetime.date(2026, 11, 12)
good = {"written": "11/12/2026", "at": "2026-11-12T15:30:00Z", "by": "EFFINGER, WILLIAM", "by_id": "u_invented", "sha": N.signing_sha(F1, W)}
F3 = DRAFTS["%s_2026-08" % ch(3)]["fields"]; OWN = "Greater than 120 minutes spent on this patient's care in August 2026."
own = {"written": "11/12/2026", "at": "2026-11-12T15:31:00Z", "by": "EFFINGER, WILLIAM", "statement": OWN, "sha": N.signing_sha(dict(F3, statement=OWN), W)}
PAGE = os.path.join(TMP, "page", "signatures"); os.makedirs(PAGE)
json.dump({"month": "2026-08", "sigs": {ch(1): good, ch(3): own, ch(2): dict(good, sha="0" * 64), ch(9): good}}, open(os.path.join(PAGE, "2026-08.json"), "w"))
json.dump({"id": "2026-09", "version": 3, "data": {"month": "2026-09", "sigs": {ch(1): good}}}, open(os.path.join(PAGE, "2026-09.json"), "w"))
S_OUT = os.path.join(TMP, "signed_out")
check("4 signatures: runs, reading the page's documents whether or not they are wrapped with their version", B.main(["signatures", "--page", os.path.join(TMP, "page"), "--out", S_OUT, "--via", "https://claude.ai/artifact/x"], select=select) == 0)
got = sorted(os.listdir(os.path.join(S_OUT, "signed")))
check("4 a signing that matches the stored draft is recorded - and a flagged month he wrote his own statement for", got == ["%s_2026-08.json" % ch(1), "%s_2026-08.json" % ch(3)], got)
s1 = json.load(open(os.path.join(S_OUT, "signed", "%s_2026-08.json" % ch(1))))
check("4 the recorded note carries the day written, who and when, the hash, the page it was signed on and its final fields", s1["written"] == "11/12/2026" and s1["by"] == "EFFINGER, WILLIAM" and s1["fields"]["written"] == "11/12/2026" and s1["via"] == "https://claude.ai/artifact/x" and s1["sha"] == good["sha"])
rej = {r["id"]: r["why"] for r in json.load(open(os.path.join(S_OUT, "signature_rejects.json")))["rejects"]}
check("4 a forged hash and a month with no draft are refused with the reason; a month already signed is skipped",
      "changed after it was shown" in rej.get("%s_2026-08" % ch(2), "") and "no draft" in rej.get("%s_2026-08" % ch(9), "") and "%s_2026-09" % ch(1) not in rej and not os.path.exists(os.path.join(S_OUT, "signed", "%s_2026-09.json" % ch(1))), rej)

# ---- 5. what it did not touch
check("5 every statement sent to the database was a SELECT", all(re.match(r"^\s*(select|with)\b", s, re.I) for s in SQL) and len(SQL) > 5)
check("5 no module that talks to AdvancedMD was loaded", all(m not in sys.modules for m in ("amd", "txh", "resave", "void_tx", "era_clear")))
AFTER = snapshot()
check("5 nothing was written in the repository while the test ran", AFTER == BEFORE, sorted(set(AFTER.items()) ^ set(BEFORE.items()))[:5])
shutil.rmtree(TMP, ignore_errors=True)
print("\ntest_ccm_build: %d checks, %d failed%s" % (RAN[0], len(FAILS), "" if not FAILS else " - " + "; ".join(FAILS)[:1200]))
sys.exit(1 if FAILS else 0)
