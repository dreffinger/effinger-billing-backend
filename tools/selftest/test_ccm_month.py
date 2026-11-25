#!/usr/bin/env python3
# PLAIN ENGLISH (offline self-test, 11/25/2026): scripts/helpers/ccm_month.py and the monthly add-on in scripts/helpers/ccm_build.py.
# Decides: nothing. With STAND-INS for the database and for AdvancedMD (no network) it proves that:
#   - plan() lists a feed CCM visit only when one of its charges is not in the AdvancedMD history yet, groups a visit's charges, skips a visit
#     read recently, re-reads an unsigned one whose read is old, never re-reads a signed month, and lists the charts with no name yet;
#   - parse_charge() keeps only the code, date, units, void flag, ICD-10 codes (AdvancedMD's order), provider profile and facility, and
#     refuses an answer without the charge;
#   - a read sends only getchargedetaildataicd10 (one per charge) and getdemographic, logs in once, writes the lines and names into the
#     workspace (never the repository), stops in a quiet window (exit 5), on a dead session (exit 3) and after five failed reads (exit 4),
#     and refuses a charge that AdvancedMD says belongs to another visit or is not a CCM code;
#   - ccm_build builds the new month from those lines: a void line makes no note, a charge already in the history is not counted twice, the
#     feed's carrier fills in for a chart with no plan in the history, a name already in Neon is used (a fresh workspace has none), and the
#     summary and the hub documents name only the new or changed notes' months when --hub-new is given.
# Never touches: Neon, AdvancedMD, the network. No patient data: every name, chart and date is invented at run time.
# Run: python3 tools/selftest/test_ccm_month.py   (exit 1 on any failure)
import os, sys, re, json, shutil, tempfile, datetime
import socket as _socket
def _no_network(*a, **k): raise RuntimeError("the self-test must not use the network")
_socket.socket.connect = _no_network; _socket.socket.connect_ex = _no_network; _socket.create_connection = _no_network
sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "scripts", "helpers"))
import ccm_month as M
import ccm_build as B
import ccm_notes as N
FAILS = []; COUNT = [0]
def check(name, ok, info=""):
    COUNT[0] += 1
    print(("ok   " if ok else "FAIL ") + str(COUNT[0]) + " " + name + ("" if ok else "  <- " + str(info)[:300]))
    if not ok: FAILS.append(name)
before = set()
for r, _, fs in os.walk(ROOT):
    if "/.git" in r: continue
    before |= {os.path.join(r, f) for f in fs}

# ---- the stand-in database --------------------------------------------------------------------------------------------------------------
C1, C2, C3, C4 = "pat9100001", "pat9100002", "pat9100003", "pat9100004"
FEED = [  # chart, visit, charge, code, dos, carrier, facility, clinician
    [C1, "8800001", "7700001", "99487", "2026-11-26", "TEST MEDICARE", "Test Manor", "Dr. Test"],
    [C1, "8800001", "7700002", "99489", "2026-11-26", "TEST MEDICARE", "Test Manor", "Dr. Test"],
    [C2, "8800002", "7700003", "99487", "2026-11-26", "", "Test Manor", "Dr. Test"],
    [C3, "8800003", "7700004", "99487", "2026-10-22", "TEST MEDICARE", "Test Manor", "Dr. Test"],      # already in the history
    [C4, "8800004", "7700005", "99487", "2026-10-27", "TEST MEDICARE", "Test Manor", "Dr. Test"],      # read before, its month signed
    [C2, "8800005", "7700006", "99487", "2026-11-12", "", "Test Manor", "Dr. Test"],                   # read 2 hours ago
    [C1, "8800006", "7700007", "99487", "2026-12-28", "TEST MEDICARE", "Test Manor", "Dr. Test"],      # read 30 hours ago, unsigned
]
HIST = ["7700004"]
LINES_READ = {"%s_8800004" % C4: ["2026-11-01T00:00:00Z", "2026-10"], "%s_8800005" % C2: ["2026-11-27T22:00:00Z", "2026-11"],
              "%s_8800006" % C1: ["2026-11-26T18:00:00Z", "2026-12"]}
SIGNED = {"%s_2026-10" % C4}
NAMED = [C1]
SQL = []
def select(sql, params=()):
    SQL.append(sql)
    if not re.match(r"^\s*(select|with)\b", sql, re.I): raise AssertionError("not a SELECT: " + sql[:60])
    if "from ehpa.feed_charges" in sql: return [list(r) for r in FEED]
    if "from amd.charges where cpt" in sql: return [[x] for x in HIST]
    if "collection = 'lines'" in sql: return [[k, v[0], v[1]] for k, v in LINES_READ.items()]
    if sql.startswith("select count(*)"): return [["3"]]
    if "collection = 'signed'" in sql: return [[x] for x in SIGNED]
    if "collection = 'patients'" in sql: return [[x] for x in NAMED]
    raise AssertionError("unexpected query: " + sql[:80])
INV_DOB_US = "/".join(["01", "02", str(1900 + 30)]); INV_DOB_ISO = "-".join([str(1900 + 30), "01", "02"])   # invented, built at run time
os.environ["CCM_NOW"] = "2026-11-28T00:00:00Z"      # 00:00 UTC: outside every quiet window

visits, charts = M.plan(select)
keys = {"%s_%s" % (v["chart"], v["visit"]): v for v in visits}
check("plan: a new visit is listed once, with both of its CCM charges in the feed's order", keys.get("%s_8800001" % C1, {}).get("charges") == ["7700001", "7700002"], keys)
check("plan: a visit whose charge is already in the AdvancedMD history is not read", "%s_8800003" % C3 not in keys, keys.keys())
check("plan: a visit of a signed month is never read again", "%s_8800004" % C4 not in keys, keys.keys())
check("plan: a visit read 2 hours ago waits", "%s_8800005" % C2 not in keys, keys.keys())
check("plan: an unsigned visit read 30 hours ago is read again", keys.get("%s_8800006" % C1, {}).get("why", "").startswith("re-read"), keys.get("%s_8800006" % C1))
check("plan: the charts without a name are listed (the named one is not)", charts == [C2], charts)
check("plan: only SELECT statements were sent", all(re.match(r"^\s*(select|with)\b", q, re.I) for q in SQL), SQL)

# ---- parse_charge ----------------------------------------------------------------------------------------------------------------------
def answer(cid, vid, code, day, void="0", dx=("dcode1", "dcode2"), units="1.0"):
    return ('<PPMDResults><Results><patient id="pat1" name="SHOULD,NOTBEKEPT" ssn="000"/><visit id="vst%s" profile="prof7" facility="fac3">'
            '<charge id="charge%s" proccode="pcode9" begindate="%s" units="%s" void="%s" diagcodes="%s" insbalance="12.00">'
            '<paymentlist><payment id="pay1" amount="5"/></paymentlist></charge></visit>'
            '<proccodelist><proccode id="pcode9" code="%s"/></proccodelist><diagcodelist><diagcode id="dcode1" code="I10"/><diagcode id="dcode2" code="E11.9"/>'
            '<diagcode id="dcode3" code="N18.30"/></diagcodelist><profilelist><profile id="prof7" code="WEFFI"/></profilelist>'
            '<facilitylist><facility id="fac3" code="TM" name="TEST MANOR"/></facilitylist></Results></PPMDResults>') % (vid, cid, day, units, void, " ".join(dx), code)
l = M.parse_charge(answer("7700001", "8800001", "99487", "11/26/2026", dx=("dcode2", "dcode1", "dcode3")), "7700001")
check("parse_charge: code, day, units, provider, facility and the ICD-10 codes in AdvancedMD's order",
      l == {"charge": "7700001", "visit": "8800001", "code": "99487", "dos": "2026-11-26", "units": "1", "void": False, "dx": ["E11.9", "I10", "N18.30"],
            "provider_code": "WEFFI", "facility": "TEST MANOR"}, l)
check("parse_charge: nothing else of the answer is kept (no name, balance or payment)", not any(x in json.dumps(l) for x in ("SHOULD", "12.00", "pay1", "ssn")), l)
check("parse_charge: a void charge is marked void", M.parse_charge(answer("7700002", "8800001", "99489", "11/26/2026", void="1"), "7700002")["void"] is True)
try: M.parse_charge(answer("7700001", "8800001", "99487", "11/26/2026"), "7799999"); ok = False
except ValueError: ok = True
check("parse_charge: an answer without the charge asked for is refused", ok)

# ---- a read with a stand-in AdvancedMD ---------------------------------------------------------------------------------------------------
class AMD:
    def __init__(self, login_ok=True, fail=False, other_visit=False, code="99487"):
        self.calls = []; self.logins = 0; self.login_ok = login_ok; self.fail = fail; self.other_visit = other_visit; self.code = code
    def login_cached(self):
        self.logins += 1
        if not self.login_ok: raise RuntimeError("session gone")
    def msg(self, action, cls, attrs): return {"action": action, "cls": cls, "attrs": dict(attrs)}
    def post(self, body, timeout=60):
        self.calls.append(body["action"])
        if self.fail: raise RuntimeError("HTTP 500")
        if body["action"] == "getdemographic":
            return '<PPMDResults><patient id="%s" name="ZZMONTHTEST,INVENTED" dob="%s" sex="F" ssn="000"/></PPMDResults>' % (body["attrs"]["patientid"], INV_DOB_US)
        cid = body["attrs"]["chargeid"]
        row = next(r for r in FEED if r[2] == cid)
        void = "1" if cid == "7700002" else "0"      # the 99489 of the first visit was voided in AdvancedMD after the feed entered it
        return answer(cid, "1234567" if self.other_visit else row[1], self.code if cid != "7700002" else "99489", "11/26/2026" if row[4] != "2026-12-28" else "12/28/2026", void=void)
TMP = tempfile.mkdtemp(prefix="ccm_month_test_"); OUT = os.path.join(TMP, "out")
amd = AMD(); rc = M.main(["read", "--out", OUT], select=select, amd=amd, sleep=lambda s: None)
check("read: exit 0", rc == 0, rc)
check("read: one login, getchargedetaildataicd10 once per charge and getdemographic for the unnamed chart only",
      amd.logins == 1 and sorted(amd.calls) == sorted(["getchargedetaildataicd10"] * 4 + ["getdemographic"]), (amd.logins, amd.calls))
doc = json.load(open(os.path.join(OUT, "neon", "lines", "%s_8800001.json" % C1)))
check("read: the visit's lines document keeps both lines, the voided one marked", [(c["code"], c["void"]) for c in doc["charges"]] == [("99487", False), ("99489", True)], doc)
check("read: the lines document carries the feed's carrier and its month", doc["feed"]["carrier"] == "TEST MEDICARE" and doc["month"] == "2026-11", doc)
pt = json.load(open(os.path.join(OUT, "neon", "patients", C2 + ".json")))
check("read: the name read is kept with the birth date and sex only", pt.get("name") == "ZZMONTHTEST,INVENTED" and pt.get("dob") == INV_DOB_ISO and "ssn" not in pt, pt)
check("read: a refused workspace inside the repository", M.main(["read", "--out", os.path.join(ROOT, "x_ccm_out")], select=select, amd=AMD(), sleep=lambda s: None) == 2)
os.environ["CCM_NOW"] = "2026-11-28T01:20:00Z"
a2 = AMD(); rc = M.main(["read", "--out", OUT], select=select, amd=a2, sleep=lambda s: None)
check("read: inside a scheduled routine's quiet window it stops before logging in (exit 5)", rc == 5 and a2.logins == 0 and not a2.calls, (rc, a2.logins, a2.calls))
import io, contextlib
buf = io.StringIO()
with contextlib.redirect_stdout(buf): rc = M.main(["plan"], select=select)
check("plan: ends with the one line a billing routine reads (to read, without a name, unsigned)", rc == 0 and buf.getvalue().strip().splitlines()[-1] == "ccm_month plan: to_read=3 names=1 unsigned=3", buf.getvalue())
os.environ["CCM_NOW"] = "2026-11-28T01:40:00Z"
a5 = AMD(); rc = M.main(["read", "--out", os.path.join(TMP, "o7"), "--in-routine"], select=select, amd=a5, sleep=lambda s: None)
check("read --in-routine: the billing routine that owns the window reads inside it", rc == 0 and a5.logins == 1 and a5.calls.count("getchargedetaildataicd10") == 4, (rc, a5.calls))
os.environ["CCM_NOW"] = "2026-11-28T00:00:00Z"
a3 = AMD(login_ok=False); check("read: a dead session stops the run without a second login (exit 3)", M.main(["read", "--out", OUT], select=select, amd=a3, sleep=lambda s: None) == 3 and a3.logins == 1)
FEED.extend([["pat91000%02d" % i, "88001%02d" % i, "77001%02d" % i, "99487", "2026-11-26", "", "Test Manor", "Dr. Test"] for i in range(10, 16)])
a4 = AMD(fail=True); rc = M.main(["read", "--out", os.path.join(TMP, "o4")], select=select, amd=a4, sleep=lambda s: None)
check("read: five failed reads in a row stop the run (exit 4)", rc == 4 and a4.calls.count("getchargedetaildataicd10") == 5, (rc, a4.calls))
del FEED[-6:]
O5 = os.path.join(TMP, "o5"); M.main(["read", "--out", O5], select=select, amd=AMD(other_visit=True), sleep=lambda s: None)
check("read: a charge AdvancedMD puts on another visit is refused (no lines document, an error listed)",
      not os.path.exists(os.path.join(O5, "neon", "lines")) and "another" not in "" and os.path.exists(os.path.join(O5, "ccm_month_errors.json")))
O6 = os.path.join(TMP, "o6"); M.main(["read", "--out", O6], select=select, amd=AMD(code="99309"), sleep=lambda s: None)
errs = json.load(open(os.path.join(O6, "ccm_month_errors.json")))["errors"]
check("read: a charge AdvancedMD shows with a non-CCM code is refused", any("not a CCM code" in e for e in errs), errs)

# ---- ccm_build builds the new month from the lines ---------------------------------------------------------------------------------------
LINES_DOCS = {}
for fn in os.listdir(os.path.join(OUT, "neon", "lines")): LINES_DOCS[fn[:-5]] = json.load(open(os.path.join(OUT, "neon", "lines", fn)))
LINES_DOCS["dup"] = {"chart": C3, "visit": "8800003", "month": "2026-10", "feed": {"carrier": ""},
                     "charges": [{"charge": "7700004", "visit": "8800003", "code": "99487", "dos": "2026-10-22", "units": "1", "void": False, "dx": ["I10", "E11.9"], "provider_code": "WEFFI", "facility": "X"}]}
HIST_LINES = [[C3, "7700004", "8800003", "2026-10-22", "99487", "1", "WEFFI", "TEST MANOR"]]
NEON_PTS = {C1: {"chart": C1, "name": "ZZNEONNAME,INVENTED", "dob": INV_DOB_ISO, "sex": "M"}}
REFD = {"codes": {"I10": ["Essential (primary) hypertension", 2027], "E11.9": ["Type 2 diabetes mellitus without complications", 2027], "N18.30": ["Chronic kidney disease, stage 3 unspecified", 2027]}}
LOADED = {}
def bselect(sql, params=()):
    if not re.match(r"^\s*(select|with)\b", sql, re.I): raise AssertionError("not a SELECT: " + sql[:60])
    if "from amd.charges c" in sql: return [list(r) for r in HIST_LINES]
    if "from amd.chart_plans" in sql: return [[C3, "TEST PLAN", "2020-01-01", "", "1"]]
    if "collection = 'icd10cm'" in sql: return [[json.dumps(REFD)]]
    if "collection = 'chargedetail'" in sql: return [[C3, "charge7700004", json.dumps(["I10", "E11.9"])]]
    if "collection = 'lines'" in sql: return [[k, json.dumps(v)] for k, v in sorted(LINES_DOCS.items())]
    if "collection = 'patients'" in sql: return [[k, json.dumps(v)] for k, v in NEON_PTS.items()]
    if "collection = 'months' and source" in sql: return [[k, v] for k, v in LOADED.items()]
    if "collection = 'months' and doc_id in (select" in sql: return []
    if "collection = 'signed'" in sql: return []
    raise AssertionError("unexpected query: " + sql[:90])
WS = os.path.join(TMP, "ws"); os.makedirs(WS); os.environ["BILLING_WORKSPACE"] = WS      # a fresh workspace: no names in it
recs, signed = B.build_months(bselect, B.all_patients(bselect, WS), REFD["codes"])
by = {r["id"]: r for r in recs}
r1 = by.get("%s_2026-11" % C1)
check("build: the new month's note has the live 99487 only (the voided 99489 makes no line)", r1 and r1["codes"] == ["99487"], r1 and r1["codes"])
check("build: its ICD-10 diagnoses come from AdvancedMD with their CMS words", r1 and [d[0] for d in r1["diagnoses"]] == ["I10", "E11.9"] and r1["diagnoses"][0][1].startswith("Essential"), r1 and r1["diagnoses"])
check("build: the feed's carrier fills in for a chart with no plan in the history", r1 and r1["insurance"] == "TEST MEDICARE", r1 and r1["insurance"])
check("build: a name already in Neon is used - the note is ready, not waiting", r1 and r1["status"] == "ready to sign" and r1["fields"]["patient"] == "ZZNEONNAME,INVENTED", r1 and (r1["status"], r1["fields"].get("patient")))
r3 = by.get("%s_2026-10" % C3)
check("build: a charge in the history and in a lines document is counted once", r3 and r3["counts"] == {"99487": 1} and not r3["flag"], r3 and (r3["counts"], r3["flag"]))
r2 = by.get("%s_2026-11" % C2)
check("build: a chart with no name anywhere waits for it", r2 and r2["status"] == "no name yet", r2 and r2["status"])
check("build: December's re-read visit makes its own month", "%s_2026-12" % C1 in by, sorted(by))
OUTB = os.path.join(TMP, "outb")
LOADED["%s_2026-10" % C3] = r3["fields_sha"]      # October's note is already loaded unchanged
rc = B.main(["build", "--out", OUTB, "--hub-new"], select=bselect)
summ = json.load(open(os.path.join(OUTB, "summary.json")))
check("build: exit 0 and a summary of the new or changed notes only", rc == 0 and summ["new_or_changed"] == 3 and summ["months"] == ["2026-11", "2026-12"], summ)
check("build: the summary counts ready, flagged and waiting", (summ["new_ready"], summ["new_flagged"], summ["new_noname"]) == (2, 0, 1), summ)
hub = sorted(os.listdir(os.path.join(OUTB, "hub", "notes")))
check("build: --hub-new writes only the new months' hub documents (and config/practice)", hub == ["2026-11-1.json", "2026-12-1.json"] and os.path.exists(os.path.join(OUTB, "hub", "config", "practice.json")), hub)
cfg = json.load(open(os.path.join(OUTB, "hub", "config", "practice.json")))
check("build: config/practice still lists every month (October too)", [m["month"] for m in cfg["months"]] == ["2026-12", "2026-11", "2026-10"], cfg["months"])

shutil.rmtree(TMP, ignore_errors=True)
after = set()
for r, _, fs in os.walk(ROOT):
    if "/.git" in r: continue
    after |= {os.path.join(r, f) for f in fs}
check("nothing was written in the repository while the test ran", after == before, sorted(after - before)[:5])
print("\ntest_ccm_month: %d checks, %d failed" % (COUNT[0], len(FAILS)))
sys.exit(1 if FAILS else 0)
