#!/usr/bin/env python3
# PLAIN ENGLISH (offline self-test, 11/11/2026): scripts/helpers/ccm_patients.py - the read of each CCM patient's name, birth date and sex.
# Decides: nothing. Proves, with a STAND-IN amd module and the network shut, that the helper:
#   - makes no login and no call unless --live is given, and not while a scheduled billing routine uses AdvancedMD (quiet windows);
#   - logs in exactly once and sends getdemographic only, nothing that writes;
#   - keeps exactly chart / name / dob / sex / read_at - not the address, SSN, member id or plans the answer also carries;
#   - converts the birth date to YYYY-MM-DD (the 1900-01-01 placeholder becomes empty) and shows a name with an apostrophe as written;
#   - is resumable (a chart read once is not read again, a failed one is tried again), honours --limit and a STOP file, stops after five
#     failed reads in a row (exit 4), stops when the session cannot be opened (exit 3) and when a quiet window starts mid-run (exit 5);
#   - refuses a workspace inside the repository, and writes nothing outside its workspace.
# Never touches: AdvancedMD (the real amd is never imported - a stand-in sits in sys.modules), Neon, the network. Nothing is started as a
#   program. No patient data: every name and date here is invented and put together at run time.
# Run: python3 tools/selftest/test_ccm_patients.py   (exit 1 on any failure)
import os, sys, re, json, types, shutil, tempfile, datetime, importlib.util
import socket as _socket
def _no_network(*a, **k): raise RuntimeError("the self-test must not use the network")
_socket.socket.connect = _no_network; _socket.socket.connect_ex = _no_network; _socket.create_connection = _no_network
sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PATH = os.path.join(ROOT, "scripts", "helpers", "ccm_patients.py")
FAILS = []; RAN = [0]
def check(name, cond, extra=""):
    RAN[0] += 1
    print(("ok   " if cond else "FAIL ") + name + ("" if cond else "  -> " + str(extra)[:600]))
    if not cond: FAILS.append(name)
src = open(PATH, encoding="utf-8").read() if os.path.exists(PATH) else ""
top = {m.split()[0].split(".")[0] for k, r in re.findall(r"^(import|from)[ \t]+([^\n#;]+)", src, re.M) for m in (r.split(",") if k == "import" else [r]) if m.strip()}
check("the helper is there; at load it imports the standard library only - AdvancedMD's module only inside a live run", src != "" and top <= {"os", "sys", "re", "json", "time", "html", "datetime"} and re.search(r"^\s+import amd\b", src, re.M) is not None, sorted(top))
if FAILS: print("\ntest_ccm_patients: %d checks, %d failed - the helper is not there" % (RAN[0], len(FAILS))); sys.exit(1)

def snapshot():
    out = {}
    for dp, dn, fn in os.walk(ROOT):
        dn[:] = [x for x in dn if x != ".git"]
        for f in fn:
            p = os.path.join(dp, f)
            try: out[p] = os.stat(p).st_mtime_ns
            except OSError: pass
    return out
BEFORE = snapshot()

# ---- the stand-in AdvancedMD module: records everything, answers getdemographic with invented charts
class StandIn:
    def __init__(self): self.reset()
    def reset(self, fail=(), login_fails=False, quiet_after=None):
        self.logins = 0; self.posts = []; self.fail = set(fail); self.login_fails = login_fails; self.quiet_after = quiet_after
AM = StandIn()
amd = types.ModuleType("amd")
def _login_cached(psw=None):
    AM.logins += 1
    if AM.login_fails: raise RuntimeError("LOGIN STEP2 FAILED (stand-in)")
    return "https://stand-in.invalid", "token"
def _msg(action, cls, attrs=None, children=""):
    return '<ppmdmsg action="%s" class="%s" msgtime="1" %s>%s</ppmdmsg>' % (action, cls, " ".join('%s="%s"' % kv for kv in (attrs or {}).items()), children)
def shown(n): return "ZZ" + "CCMTEST" + chr(65 + n) + "," + "INVENTED" + chr(65 + n)
def born(n): return (datetime.date(1931, 3, 1) + datetime.timedelta(days=97 * n)).strftime("%m/%d/%Y")
ADDR, SSN, MEMBER = "1 Invented " + "Street", "9" * 3 + "-" + "0" * 2 + "-" + "1" * 4, "XQ" + "77" + "1234"
def _post(xml, timeout=180):
    AM.posts.append(xml)
    if AM.quiet_after is not None and len(AM.posts) >= AM.quiet_after: os.environ["CCM_NOW"] = "2026-11-11T13:15:00Z"
    m = re.search(r'patientid="(pat(\d+))"', xml); c, n = m.group(1), int(m.group(2)) % 10
    if c in AM.fail: raise RuntimeError("HTTP 500 (stand-in)")
    nm = shown(n).replace("INVENTEDB", "O&apos;INVENTEDB") if n == 1 else shown(n)
    day = "/".join(("01", "01", "19" + "00")) if n == 5 else born(n)      # n 5: AdvancedMD's placeholder day
    return ('<PPMDResults><Results><patientlist><patient id="%s" name="%s" dob="%s" sex="F" address1="%s" ssn="%s" respparty="resp%d" insorder="1">'
            '<insplanlist><insplan id="ins%d" carrier="car7" subscribernum="%s" sequence="1"/></insplanlist></patient></patientlist></Results></PPMDResults>') % (c, nm, day, ADDR, SSN, n, n, MEMBER)
amd.login_cached = _login_cached; amd.msg = _msg; amd.post = _post; amd._msgtime = lambda: "1"
sys.modules["amd"] = amd

spec = importlib.util.spec_from_file_location("ccm_patients_t", PATH); P = importlib.util.module_from_spec(spec); spec.loader.exec_module(P)
TMP = tempfile.mkdtemp(prefix="ccm_patients_test_")
def ws(name, charts=None):
    w = os.path.join(TMP, name); os.makedirs(os.path.join(w, "ccm"), exist_ok=True)
    if charts is not None: json.dump({"charts": charts}, open(os.path.join(w, "ccm", "ccm_charts.json"), "w"))
    os.environ["BILLING_WORKSPACE"] = w; return w
def run(*argv, now="2026-11-11T09:00:00Z"):
    os.environ["CCM_NOW"] = now
    return P.main(list(argv), sleep=lambda s: None)
def rows(w):
    p = os.path.join(w, "ccm", "ccm_patients.jsonl")
    return [json.loads(l) for l in open(p, encoding="utf-8")] if os.path.exists(p) else []
CH = ["pat%d" % (9600000 + i) for i in range(6)]

# ---- 1. nothing happens without --live, outside the windows, with a usable input
w0 = ws("none"); AM.reset()
check("1 no chart list: it says how to write one and reads nothing", run("--live") == 2 and AM.logins == 0 and AM.posts == [])
os.environ["BILLING_WORKSPACE"] = os.path.join(ROOT, "tmp_ccm_never"); AM.reset()
check("1 a workspace inside the repository is refused - patient data never goes there", run("--live") == 2 and AM.logins == 0 and not os.path.exists(os.path.join(ROOT, "tmp_ccm_never")))
w1 = ws("main", CH + ["pat9600001", "not-a-chart"]); AM.reset()
check("1 without --live it only prints the plan: no login, no call, nothing written", run() == 0 and AM.logins == 0 and AM.posts == [] and rows(w1) == [])
for t, label in (("2026-11-11T07:30:00Z", "07:10-08:15"), ("2026-11-11T01:15:00Z", "01:10-02:40"), ("2026-11-11T19:45:00Z", "19:10-20:15")):
    AM.reset(); r = run("--live", now=t)
    check("1 inside a scheduled routine's window (%s UTC) a live run reads nothing and says when to run again" % label, r == 5 and AM.logins == 0 and AM.posts == [])

# ---- 2. a live run: one login, getdemographic only, exactly the fields kept
AM.reset(fail={"pat9600003"})
r = run("--live", "--limit", "4")
R = rows(w1)
check("2 a live run logs in exactly once and sends getdemographic only (nothing that writes)", r == 0 and AM.logins == 1 and len(AM.posts) == 4 and all('action="getdemographic" class="demographics"' in x for x in AM.posts), (r, AM.logins, [x[:60] for x in AM.posts]))
check("2 --limit 4 reads four charts, each chart once, in the listed order (the duplicate and the bad id are dropped)", [x["chart"] for x in R] == CH[:4], [x["chart"] for x in R])
good = [x for x in R if not x.get("error")]
check("2 each line keeps exactly chart, name, dob, sex and read_at", all(sorted(x) == ["chart", "dob", "name", "read_at", "sex"] for x in good) and len(good) == 3, [sorted(x) for x in R])
text = open(os.path.join(w1, "ccm", "ccm_patients.jsonl"), encoding="utf-8").read()
check("2 nothing else from the answer is kept: not the address, the SSN, the member id, the responsible party or the plans", all(s not in text for s in (ADDR, SSN, MEMBER, "resp", "car7", "ins")), text[:300])
check("2 the birth date becomes YYYY-MM-DD and a name with an apostrophe reads as written", good[0]["dob"] == datetime.datetime.strptime(born(0), "%m/%d/%Y").date().isoformat() and good[1]["name"] == shown(1).replace("INVENTEDB", "O'INVENTEDB"), good[:2])
check("2 a chart whose read failed gets an error line and the run goes on", R[3]["chart"] == "pat9600003" and "error" in R[3] and "name" not in R[3], R[3])

# ---- 3. resumable
AM.reset()
r = run("--live")
R2 = rows(w1)
check("3 the next run reads only what is left - the failed chart again, never a chart already read", r == 0 and AM.logins == 1 and sorted(re.search(r'patientid="(\w+)"', x).group(1) for x in AM.posts) == sorted(["pat9600003", "pat9600004", "pat9600005"]), [x[:70] for x in AM.posts])
check("3 the 1900-01-01 placeholder birth date becomes empty, not a date", [x for x in R2 if x["chart"] == "pat9600005"][-1]["dob"] == "")
AM.reset()
check("3 with everything read a live run logs in to nothing", run("--live") == 0 and AM.logins == 0 and AM.posts == [])

# ---- 4. stops
w2 = ws("stops", CH); AM.reset(login_fails=True)
check("4 a session that cannot be opened stops the run (exit 3) - no read, no second login", run("--live") == 3 and AM.logins == 1 and AM.posts == [] and rows(w2) == [])
AM.reset(fail=set(CH))
check("4 five failed reads in a row stop the run (exit 4)", run("--live") == 4 and len(AM.posts) == 5 and len(rows(w2)) == 5)
w3 = ws("stopfile", CH); open(os.path.join(w3, "ccm", "STOP"), "w").close(); AM.reset()
check("4 a STOP file ends the run before the next chart (exit 5)", run("--live") == 5 and AM.posts == [] and rows(w3) == [])
w4 = ws("window", CH); AM.reset(quiet_after=2)
check("4 when a routine's window starts during the run it stops after the chart in hand (exit 5) and keeps what it read", run("--live") == 5 and len(AM.posts) == 2 and len(rows(w4)) == 2)

# ---- 5. what it did not touch
check("5 no module that talks to AdvancedMD was loaded besides the stand-in", all(m not in sys.modules for m in ("txh", "resave", "void_tx", "era_clear")) and sys.modules.get("amd") is amd)
AFTER = snapshot()
check("5 nothing was written in the repository while the test ran", AFTER == BEFORE, sorted(set(AFTER.items()) ^ set(BEFORE.items()))[:5])
shutil.rmtree(TMP, ignore_errors=True)
print("\ntest_ccm_patients: %d checks, %d failed%s" % (RAN[0], len(FAILS), "" if not FAILS else " - " + "; ".join(FAILS)[:1200]))
sys.exit(1 if FAILS else 0)
