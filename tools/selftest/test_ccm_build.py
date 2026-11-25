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
#   - (William 11/12/2026: the ICD-10 diagnoses on every note) reads each CCM line's ICD-10 codes from the AdvancedMD history (chargedetail,
#     whose charge id carries the prefix "charge"), puts them on a new note with the CMS descriptions (the 99487 line first, then 99489,
#     each code once) and flags a month with fewer than two; a SIGNED note keeps the fields he signed; writes the ICD-10 reference document
#     from the CMS code files (newest year first, a retired code keeps its last words, only the codes on a charge);
#   - writes one dated diagnosis ADDENDUM per signed note (never for an addendum already signed, never for a note signed with its
#     diagnoses), flags one with fewer than two diagnoses (with the chart's whole diagnosis list) or a charge missing from the history, and
#     cuts the hub page's documents under 200 KB; a SIGNED addendum keeps on the hub page exactly the fields he signed (its recorded
#     document), even after the charge's codes and a CMS description change and addenda runs again; records an addendum signing only
#     when it matches the stored draft (a changed addendum, a forged hash, one that carries a statement, one dated before its note, one
#     with no draft are refused; one already signed is skipped).
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
# each CCM line's ICD-10 codes as the AdvancedMD history holds them (chargedetail: the id carries the prefix "charge"); ch(4) carries one only
DXC = {"c11": ["E11.9", "I10", "N18.30"], "c12": ["I10", "F03.90", "E11.9"], "c13": ["J44.9", "I10"], "c21": ["I10", "E78.5"], "c22": ["E78.5", "I10"],
       "c31": ["I50.9", "N18.30"], "c32": ["N18.30", "I50.9", "Z99.89"], "c41": ["I10"], "c51": ["E11.9", "I10"]}
DXC.update({"cx%d" % i: ["I10", "E11.9"] for i in range(320)})
CHARGEDETAIL = [[r[0], "charge" + r[1], json.dumps(DXC[r[1]])] for r in LINES]
DESC = {"E11.9": ["Invented diabetes words", 2027], "I10": ["Invented hypertension words", 2027], "N18.30": ["Invented kidney words", 2026],
        "F03.90": ["Invented memory words", 2027], "J44.9": ["Invented lung words", 2027], "E78.5": ["Invented lipid words", 2025],
        "I50.9": ["Invented heart words", 2027], "Z99.89": ["Invented device words", 2027]}
REF = [{"title": "test", "codes": DESC}]
STORED = {}; NOTES_SIGNED = []; ADD_SIGNED = {}; ADD_DRAFTS = {}      # ADD_SIGNED: a signed addendum's id -> its recorded fields
SIGNED = set(); DRAFTS = {}; SQL = []
CCM_LINES = {}; NEON_PATIENTS = {}; LOADED_SHAS = {}      # the monthly add-on (11/25/2026): visits read back after the history pull, names in Neon, loaded drafts
def select(sql, params=()):
    SQL.append(sql)
    if not re.match(r"^\s*(select|with)\b", sql, re.I): raise AssertionError("not a SELECT: " + sql[:60])
    if "from amd.charges c" in sql: return [list(r) for r in LINES]
    if "from amd.chart_plans" in sql: return [list(r) for r in PLANS]
    if "collection = 'icd10cm'" in sql: return [[json.dumps(b)] for b in REF]
    if "collection = 'chargedetail'" in sql and "d.doc_id = any(" in sql: return [[r[0], "08/%02d/2026" % (1 + n % 28), r[2]] for n, r in enumerate(CHARGEDETAIL) if r[0] in params[0].split(",")]
    if "collection = 'chargedetail'" in sql and "select distinct x.code" in sql: return [[c] for c in sorted({c for r in CHARGEDETAIL for c in json.loads(r[2])} | {"Q99.99"})]
    if "collection = 'chargedetail'" in sql: return [list(r) for r in CHARGEDETAIL]
    if "collection = 'lines'" in sql: return [[k, json.dumps(v)] for k, v in sorted(CCM_LINES.items())]
    if "collection = 'patients'" in sql: return [[k, json.dumps(v)] for k, v in sorted(NEON_PATIENTS.items())]
    if "collection = 'months' and source" in sql: return [[k, v] for k, v in sorted(LOADED_SHAS.items())]
    if "collection = 'months' and doc_id in (select" in sql: return [[i, json.dumps(STORED[i])] for i in sorted(SIGNED) if i in STORED]
    if "collection = 'addenda_signed'" in sql: return [[x, json.dumps(ADD_SIGNED[x])] if "body->'fields'" in sql else [x] for x in sorted(ADD_SIGNED)]
    if "collection = 'addenda'" in sql: return [[i, json.dumps(ADD_DRAFTS[i])] for i in params[0].split(",") if i in ADD_DRAFTS]
    if "body->>'sha' from raw.documents where source = 'ccm' and collection = 'signed'" in sql: return [[i, json.dumps(f), sha] for i, f, sha in NOTES_SIGNED]
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
check("2 a new note lists the ICD-10 codes on the month's CCM lines with the CMS words: the 99487 line first, then 99489, each code once, AdvancedMD's order",
      r1["fields"]["diagnoses"] == [["E11.9", "Invented diabetes words"], ["I10", "Invented hypertension words"], ["N18.30", "Invented kidney words"], ["F03.90", "Invented memory words"]], r1["fields"]["diagnoses"])
check("2 a month whose charge carries fewer than two diagnoses is flagged (Medicare looks first for two or more chronic conditions); two or more is not",
      "fewer than two diagnoses on the CCM charge (1)" in R["%s_2026-08" % ch(4)]["flag"] and "check the chart's diagnosis list" in R["%s_2026-08" % ch(4)]["flag"] and "diagnoses" not in r1["flag"], R["%s_2026-08" % ch(4)]["flag"])

# ---- 3. the files
SIGNED.add("%s_2026-09" % ch(1))
OLD_F = {k: v for k, v in R["%s_2026-09" % ch(1)]["fields"].items() if k != "diagnoses"}; OLD_F["insurance"] = "INVENTED PLAN AS SIGNED"
STORED["%s_2026-09" % ch(1)] = OLD_F      # a note signed before 11/12/2026: its stored draft has no diagnoses
REF.clear()
check("3 build refuses without the ICD-10 descriptions (a new note lists its diagnoses with them), and writes nothing", B.main(["build", "--out", OUT], select=select) == 2 and not os.path.exists(OUT))
REF.append({"title": "test", "codes": DESC})
check("3 build writes the database documents and the hub documents", B.main(["build", "--out", OUT], select=select) == 0)
months = os.listdir(os.path.join(OUT, "neon", "months")); pts = os.listdir(os.path.join(OUT, "neon", "patients"))
check("3 a signed month is final: its record is not written again", "%s_2026-09.json" % ch(1) not in months and len(months) == 325, len(months))
check("3 patient documents only for charts whose name was read", sorted(pts) == sorted("%s.json" % ch(n) for n in (1, 2, 3, 4)), pts)
md = json.load(open(os.path.join(OUT, "neon", "months", "%s_2026-08.json" % ch(1))))
check("3 a month document carries the charge lines, codes, statement, flag, insurance, the note's fields and their hash", md["codes"] == ["99487", "99489"] and len(md["charges"]) == 2 and md["fields_sha"] == N.hashlib.sha256(N.canon(md["fields"]).encode("utf-8")).hexdigest() and md["_written"])
check("3 each charge line of a month document carries its ICD-10 codes, and the note's fields carry the diagnoses", md["charges"][0]["dx"] == DXC["c11"] and md["charges"][1]["dx"] == DXC["c12"] and len(md["fields"]["diagnoses"]) == 4)
hub = {}
for dp, _, fn in os.walk(os.path.join(OUT, "hub")):
    for f in fn: hub[os.path.relpath(os.path.join(dp, f), os.path.join(OUT, "hub"))] = os.path.getsize(os.path.join(dp, f))
cfg = json.load(open(os.path.join(OUT, "hub", "config", "practice.json")))
check("3 the hub documents: one per 150 notes of a month, each well under the page database's 256 KiB limit", all(s < 200 * 1024 for s in hub.values()) and "notes/2026-07-1.json" in hub and "notes/2026-07-3.json" in hub and "notes/2026-07-4.json" not in hub, hub)
n07 = json.load(open(os.path.join(OUT, "hub", "notes", "2026-07-1.json")))
check("3 the statement is stored once per document and every note points to it; the note's other fields are complete",
      set(n07["statements"]) == {"60"} and all(x["m"] == "60" and "statement" not in x["f"] and set(x["f"]) == set(N.FIELD_KEYS) - {"statement"} for x in n07["notes"]))
n09 = [x for f in os.listdir(os.path.join(OUT, "hub", "notes")) if f.startswith("2026-09") for x in json.load(open(os.path.join(OUT, "hub", "notes", f)))["notes"]]
check("3 a SIGNED note keeps on the hub page exactly the fields he signed (its stored draft - no diagnoses added, nothing recomputed)",
      len(n09) == 1 and n09[0]["status"] == "signed" and n09[0]["f"] == {k: v for k, v in OLD_F.items() if k != "statement"} and "diagnoses" not in n09[0]["f"], n09[:1])
check("3 a new note on the hub page carries its diagnoses", any(x["f"].get("diagnoses") == [["I10", "Invented hypertension words"], ["E11.9", "Invented diabetes words"]] for x in n07["notes"]))
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

# ---- 5. the ICD-10 reference document from the CMS code files (invented words; code, spaces, words - as CMS writes them)
CMS = os.path.join(TMP, "cms"); os.makedirs(os.path.join(CMS, "x2026")); os.makedirs(os.path.join(CMS, "x2027", "Code Descriptions"))
def cms_file(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as f: f.write("".join("%-8s%s\r\n" % r for r in rows))
cms_file(os.path.join(CMS, "x2026", "icd10cm_codes_2026.txt"), [("E119", "Old diabetes words"), ("I10", "Invented hypertension words"), ("N1830", "Invented kidney words"), ("Z9989", "Retired device words")])
cms_file(os.path.join(CMS, "x2027", "Code Descriptions", "icd10cm_codes_2027.txt"), [("E119", "Invented diabetes words"), ("I10", "Invented hypertension words"), ("F0390", "Invented memory words"),
         ("J449", "Invented lung words"), ("E785", "Invented lipid words"), ("I509", "Invented heart words"), ("A000", "A code on no charge")])
cms_file(os.path.join(CMS, "x2027", "Code Descriptions", "icd10cm_codes_addenda_2027.txt"), [("Q9999", "not a code file")])
REF_OUT = os.path.join(TMP, "ref")
check("5 icd10: runs on the CMS code files", B.main(["icd10", "--cms", CMS, "--out", REF_OUT], select=select) == 0)
ref = json.load(open(os.path.join(REF_OUT, "icd10cm", "descriptions.json")))
check("5 the newest fiscal year's words win, a code retired since keeps its last words, and each code says which year its words are from",
      ref["codes"]["E11.9"] == ["Invented diabetes words", 2027] and ref["codes"]["Z99.89"] == ["Retired device words", 2026] and ref["codes"]["N18.30"] == ["Invented kidney words", 2026] and ref["years"] == [2027, 2026], ref["codes"])
check("5 only the codes on a charge are kept (with the dot, as AdvancedMD writes them); a code on a charge with no CMS words is listed as missing",
      "A00.0" not in ref["codes"] and set(ref["codes"]) == set(DESC) and ref["missing"] == ["Q99.99"] and ref["codes_on_charges"] == 9, (sorted(ref["codes"]), ref["missing"]))
check("5 icd10 refuses an output folder inside the repository and a folder without CMS files", B.main(["icd10", "--cms", CMS, "--out", os.path.join(ROOT, "tmp_never3")], select=select) == 2
      and B.main(["icd10", "--cms", WS, "--out", REF_OUT + "2"], select=select) == 2 and not os.path.exists(os.path.join(ROOT, "tmp_never3")))

# ---- 6. one dated diagnosis addendum per signed note
def note_signed(chart, ym, charges, written="11/11/2026", **kw):
    f = dict({"practice": "North Florida Senior Care", "chart": chart, "month": ym, "patient": shown(7), "dob": N.us(datetime.date(1930, 2, 3)), "insurance": "INVENTED MEDICARE",
              "location": "Invented ALF", "provider": "EFFINGER, WILLIAM", "codes": sorted({c[1] for c in charges}), "charges": charges,
              "late_entry": "LATE ENTRY for the charge dated x, for the month of y (z).", "statement": "Greater than 60 minutes ...", "evidence": []}, **kw)
    f["written"] = written; return f
NOTES_SIGNED[:] = [
    ("%s_2026-08" % ch(1), note_signed(ch(1), "2026-08", [["08/20/2026", "99487", "v11", "c11"], ["08/20/2026", "99489", "v11", "c12"]]), "a" * 64),
    ("%s_2026-08" % ch(4), note_signed(ch(4), "2026-08", [["08/20/2026", "99487", "v41", "c41"]]), "b" * 64),       # one diagnosis: flagged
    ("%s_2026-08" % ch(5), note_signed(ch(5), "2026-08", [["08/22/2026", "99487", "v51", "c51"]]), "c" * 64),       # its addendum is already signed
    ("%s_2026-08" % ch(3), note_signed(ch(3), "2026-08", [["08/20/2026", "99487", "v31", "c31"]], diagnoses=[["I50.9", "x"]]), "d" * 64),   # signed with its diagnoses
    ("%s_2026-08" % ch(2), note_signed(ch(2), "2026-08", [["08/25/2026", "99487", "v21", "c21"], ["08/27/2026", "99487", "v29", "c29"]]), "e" * 64)]   # c29: not in the history
NOTES_SIGNED += [("%s_2026-07" % ch(10 + i), note_signed(ch(10 + i), "2026-07", [["07/%02d/2026" % (1 + i % 28), "99487", "vx%d" % i, "cx%d" % i]]), "f" * 64) for i in range(320)]
N5 = NOTES_SIGNED[2][1]      # ch(5)'s addendum is signed: its recorded document holds the fields he signed, with the day written
SF5 = dict(N.addendum_fields(N5, "c" * 64, {"c51": DXC["c51"]}, DESC), written="11/12/2026"); SIGNED5 = {k: v for k, v in SF5.items() if k != "written"}
ADD_SIGNED["%s_2026-08_dx" % ch(5)] = SF5
A_OUT = os.path.join(TMP, "addenda_out")
REF.clear()
check("6 addenda refuses without the ICD-10 descriptions and writes nothing", B.main(["addenda", "--out", A_OUT], select=select) == 2 and not os.path.exists(A_OUT))
check("6 addenda runs with the descriptions from the file icd10 wrote", B.main(["addenda", "--out", A_OUT, "--descriptions", os.path.join(REF_OUT, "icd10cm", "descriptions.json")], select=select) == 0)
REF.append({"title": "test", "codes": DESC})
drafts = sorted(os.listdir(os.path.join(A_OUT, "neon", "addenda")))
check("6 one draft per signed note, named <chart>_<YYYY-MM>_dx - none for an addendum already signed (final) and none for a note signed with its diagnoses",
      len(drafts) == 323 and "%s_2026-08_dx.json" % ch(1) in drafts and "%s_2026-08_dx.json" % ch(5) not in drafts and "%s_2026-08_dx.json" % ch(3) not in drafts, len(drafts))
a1 = json.load(open(os.path.join(A_OUT, "neon", "addenda", "%s_2026-08_dx.json" % ch(1))))
check("6 the addendum names its note (id, day written, the hash he signed) and lists the diagnoses on the note's own charge lines with the CMS words, the 99487 line first",
      a1["note"] == "%s_2026-08" % ch(1) and a1["fields"]["note_written"] == "11/11/2026" and a1["fields"]["note_sha"] == "a" * 64 and a1["note_sha"] == "a" * 64
      and a1["fields"]["diagnoses"] == [["E11.9", "Invented diabetes words"], ["I10", "Invented hypertension words"], ["N18.30", "Invented kidney words"], ["F03.90", "Invented memory words"]]
      and a1["fields"]["addendum_to"] == "the late entry for the charge dated 08/20/2026, for the month of August 2026" and a1["flag"] == "" and set(a1["fields"]) == set(N.ADDENDUM_KEYS), a1)
check("6 the draft carries the hash of its fields (what a signing is checked against)", a1["fields_sha"] == N.hashlib.sha256(N.canon(a1["fields"]).encode("utf-8")).hexdigest())
a4 = json.load(open(os.path.join(A_OUT, "neon", "addenda", "%s_2026-08_dx.json" % ch(4))))
a2 = json.load(open(os.path.join(A_OUT, "neon", "addenda", "%s_2026-08_dx.json" % ch(2))))
check("6 fewer than two diagnoses on the charge is flagged, and so is a charge missing from the AdvancedMD history",
      "fewer than two diagnoses on the CCM charge (1)" in a4["flag"] and "Medicare looks first for two or more qualifying chronic conditions" in a4["flag"] and "charge c29 not found" in a2["flag"], (a4["flag"], a2["flag"]))
AH = {}
for dp, _, fn in os.walk(os.path.join(A_OUT, "hub")):
    for f in fn: AH[os.path.relpath(os.path.join(dp, f), os.path.join(A_OUT, "hub"))] = os.path.getsize(os.path.join(dp, f))
acfg = json.load(open(os.path.join(A_OUT, "hub", "config", "addenda.json")))
check("6 the hub page's addenda documents: each under 200 KB, one month cut in parts, and the counts by status (the signed one counted, the flagged ones apart)",
      all(v < 200 * 1024 for v in AH.values()) and "addenda/2026-07-1.json" in AH and "addenda/2026-07-3.json" in AH and acfg["counts"] == {"addenda": 324, "ready": 321, "flagged": 2, "signed": 1}, (AH, acfg["counts"]))
h08 = json.load(open(os.path.join(A_OUT, "hub", "addenda", "2026-08-1.json")))["addenda"]; H = {x["id"]: x for x in h08}
check("6 on the page an addendum carries its note's id, its fields, its flag and status; a flagged one carries the chart's whole diagnosis list to check",
      H["%s_2026-08_dx" % ch(1)]["note"] == "%s_2026-08" % ch(1) and H["%s_2026-08_dx" % ch(1)]["f"] == a1["fields"] and H["%s_2026-08_dx" % ch(5)]["status"] == "signed"
      and H["%s_2026-08_dx" % ch(4)]["status"] == "flagged" and H["%s_2026-08_dx" % ch(4)]["chart_dx"][0][:2] == ["I10", "Invented hypertension words"] and "chart_dx" not in H["%s_2026-08_dx" % ch(1)], H["%s_2026-08_dx" % ch(4)])
check("6 addenda refuses an output folder inside the repository", B.main(["addenda", "--out", os.path.join(ROOT, "tmp_never4")], select=select) == 2 and not os.path.exists(os.path.join(ROOT, "tmp_never4")))
# after the signing, the charge's codes in the AdvancedMD history and a CMS description change (a history refresh, a new fiscal year) and addenda runs again
I51 = [i for i, r in enumerate(CHARGEDETAIL) if r[1] == "chargec51"][0]; OLD51 = CHARGEDETAIL[I51]
CHARGEDETAIL[I51] = [OLD51[0], OLD51[1], json.dumps(["I10", "E78.5"])]
DESC2 = dict(DESC, **{"E11.9": ["Invented diabetes words of a later year", 2028]}); REF[:] = [{"title": "test", "codes": DESC2}]
A_OUT2 = os.path.join(TMP, "addenda_out2"); r6 = B.main(["addenda", "--out", A_OUT2], select=select)
CHARGEDETAIL[I51] = OLD51; REF[:] = [{"title": "test", "codes": DESC}]
H2 = {x["id"]: x for x in json.load(open(os.path.join(A_OUT2, "hub", "addenda", "2026-08-1.json")))["addenda"]}
REBUILT5 = N.addendum_fields(N5, "c" * 64, {"c51": ["I10", "E78.5"]}, DESC2)      # what it would show if it were rebuilt from today's history
check("6 a SIGNED addendum keeps on the hub page exactly the fields he signed (its recorded document, without the day written): the charge's codes and a CMS "
      "description changed and addenda ran again - its item did not move, no draft is written for it, and an unsigned addendum did take the new words",
      r6 == 0 and REBUILT5["diagnoses"] != SIGNED5["diagnoses"] and H2["%s_2026-08_dx" % ch(5)]["f"] == SIGNED5 and H2["%s_2026-08_dx" % ch(5)]["status"] == "signed"
      and H2["%s_2026-08_dx" % ch(5)]["flag"] == "" and not os.path.exists(os.path.join(A_OUT2, "neon", "addenda", "%s_2026-08_dx.json" % ch(5)))
      and H2["%s_2026-08_dx" % ch(1)]["f"]["diagnoses"][0] == ["E11.9", "Invented diabetes words of a later year"], (H2.get("%s_2026-08_dx" % ch(5), {}).get("f"), SIGNED5))

# ---- 7. addendum signings from the hub page
ADD_DRAFTS.update({d[:-5]: json.load(open(os.path.join(A_OUT, "neon", "addenda", d))) for d in drafts})
AF1 = ADD_DRAFTS["%s_2026-08_dx" % ch(1)]["fields"]; AF4 = ADD_DRAFTS["%s_2026-08_dx" % ch(4)]["fields"]; AF2 = ADD_DRAFTS["%s_2026-08_dx" % ch(2)]["fields"]
W = datetime.date(2026, 11, 13)
ag = {"written": "11/13/2026", "at": "2026-11-13T15:30:00Z", "by": "EFFINGER, WILLIAM", "by_id": "u_invented", "sha": N.signing_sha(AF1, W), "kind": "ready"}
ADD_DRAFTS["%s_2026-08_dx" % ch(2)] = dict(ADD_DRAFTS["%s_2026-08_dx" % ch(2)], fields=dict(AF2, diagnoses=AF2["diagnoses"] + [["Z99.89", "added later"]]))   # the draft changed after it was shown
AF10 = ADD_DRAFTS["%s_2026-07_dx" % ch(10)]["fields"]
APAGE = os.path.join(TMP, "apage", "addendum_signatures"); os.makedirs(APAGE)
json.dump({"month": "2026-08", "sigs": {"%s_2026-08_dx" % ch(1): ag, "%s_2026-08_dx" % ch(4): dict(ag, sha=N.signing_sha(AF4, W), kind="flagged"),
           "%s_2026-08_dx" % ch(2): dict(ag, sha=N.signing_sha(AF2, W)), "%s_2026-08_dx" % ch(5): ag, "%s_2026-08_dx" % ch(9): ag}}, open(os.path.join(APAGE, "2026-08.json"), "w"))
json.dump({"id": "2026-07", "version": 2, "data": {"month": "2026-07", "sigs": {"%s_2026-07_dx" % ch(10): dict(ag, sha="0" * 64), "%s_2026-07_dx" % ch(11): dict(ag, statement="Greater than 60 minutes.", sha=N.signing_sha(ADD_DRAFTS["%s_2026-07_dx" % ch(11)]["fields"], W)),
           "%s_2026-07_dx" % ch(12): dict(ag, written="11/10/2026", at="2026-11-10T15:00:00Z", sha=N.signing_sha(ADD_DRAFTS["%s_2026-07_dx" % ch(12)]["fields"], datetime.date(2026, 11, 10))),
           ch(13): dict(ag, sha=N.signing_sha(ADD_DRAFTS["%s_2026-07_dx" % ch(13)]["fields"], W))}}}, open(os.path.join(APAGE, "2026-07.json"), "w"))
AS_OUT = os.path.join(TMP, "asigned_out")
check("7 signatures --kind addenda runs on the page's addendum_signatures (wrapped with its version or not)", B.main(["signatures", "--kind", "addenda", "--page", os.path.join(TMP, "apage"), "--out", AS_OUT, "--via", "https://claude.ai/artifact/x"], select=select) == 0)
agot = sorted(os.listdir(os.path.join(AS_OUT, "addenda_signed")))
check("7 an addendum signing that matches the stored draft is recorded - a flagged one he opened and signed too, and one keyed by its chart",
      agot == sorted(["%s_2026-08_dx.json" % ch(1), "%s_2026-08_dx.json" % ch(4), "%s_2026-07_dx.json" % ch(13)]), agot)
s1 = json.load(open(os.path.join(AS_OUT, "addenda_signed", "%s_2026-08_dx.json" % ch(1))))
check("7 the recorded addendum carries its note, the day written, who and when, the hash, the page and its final fields",
      s1["note"] == "%s_2026-08" % ch(1) and s1["kind"] == "diagnoses" and s1["written"] == "11/13/2026" and s1["fields"]["written"] == "11/13/2026" and s1["sha"] == ag["sha"] and s1["via"] == "https://claude.ai/artifact/x" and "statement" not in s1["fields"])
arej = {r["id"]: r["why"] for r in json.load(open(os.path.join(AS_OUT, "addendum_signature_rejects.json")))["rejects"]}
check("7 a changed addendum, a forged hash, a signing that brings a statement, one dated before its note and one with no draft are refused; one already signed is skipped",
      "addendum changed after it was shown" in arej.get("%s_2026-08_dx" % ch(2), "") and "changed after it was shown" in arej.get("%s_2026-07_dx" % ch(10), "")
      and "carries no statement" in arej.get("%s_2026-07_dx" % ch(11), "") and "written after the note it adds to" in arej.get("%s_2026-07_dx" % ch(12), "")
      and "no draft" in arej.get("%s_2026-08_dx" % ch(9), "") and "%s_2026-08_dx" % ch(5) not in arej and not os.path.exists(os.path.join(AS_OUT, "addenda_signed", "%s_2026-08_dx.json" % ch(5))), arej)
check("7 signatures --kind takes notes or addenda only", B.main(["signatures", "--kind", "other", "--page", os.path.join(TMP, "apage"), "--out", AS_OUT + "x"], select=select) == 2)

# ---- 8. what it did not touch
check("8 every statement sent to the database was a SELECT", all(re.match(r"^\s*(select|with)\b", s, re.I) for s in SQL) and len(SQL) > 5)
check("8 no module that talks to AdvancedMD was loaded", all(m not in sys.modules for m in ("amd", "txh", "resave", "void_tx", "era_clear")))
AFTER = snapshot()
check("8 nothing was written in the repository while the test ran", AFTER == BEFORE, sorted(set(AFTER.items()) ^ set(BEFORE.items()))[:5])
shutil.rmtree(TMP, ignore_errors=True)
print("\ntest_ccm_build: %d checks, %d failed%s" % (RAN[0], len(FAILS), "" if not FAILS else " - " + "; ".join(FAILS)[:1200]))
sys.exit(1 if FAILS else 0)
