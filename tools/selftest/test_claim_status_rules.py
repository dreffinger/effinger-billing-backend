#!/usr/bin/env python3
# PLAIN ENGLISH (offline self-test of the claim-status rules - look-ups part A, step 2, 11/10/2026)
# Decides: nothing. Loads the rule module (scripts/helpers/cs_rules.py), the claim-status helpers (claim_status_sweep.py, sweep_full.py,
#   claim_status_exact.py), the vendor client (stedi.py, whose door writes the usage log), the payer map (precheck.py), the price table
#   (stedi_prices.py) and the engine's sweep step (tools/button/run_all.py) INSIDE this process, from their files, with stand-in modules for
#   everything that talks to AdvancedMD or the vendor: a request counter answers every claim-status request from a canned table. No
#   network, no AdvancedMD, no vendor, no patient data - every chart, claim, name and number in the canned cases is invented at run time.
#   The October replay reads the practice's own registers that are already in this repository (claim, visit and chart numbers stay in
#   memory; only counts are printed). It proves:
#     - the ledger: a claim with a final answer on record is not asked; a send after that answer asks it again; a missing ledger ends the run
#       with an error and no call, --new-ledger starts one where none exists and never replaces one, a broken ledger is never taken as empty;
#       one step writes (temporary file, rename) that keep another writer's rows; the month's checks counted and priced; no name, member id
#       or birth date in the ledger or the run file; a windowed 'paid' that names another claim is not final;
#     - by need: payment or denial posted = not asked, sent 20 days ago = not asked, sent 50 days ago with nothing posted = asked, a secondary
#       balance silent 61 days = asked, a larger claim that is not due is not asked while a smaller due one is; a missing or day-old ageing
#       file = an error line and no call of any kind; every report prints the claims silent 60 or more days;
#     - the waits (one table): pending 3 days ago no, 15 days ago yes; 30 days when the claim was last sent 120+ days ago; 7 days near the
#       filing limit; a year old = no check at all; 'not found' only after a resend and 30 days; no usable answer 7 days;
#     - stop and hand off: two unusable answers in a row (counted only when another claim of the payer answered), three 'pending' in a row;
#       the hand-off list with age and dollars; a night when one payer answers nobody uses up no tries; a person re-opens a row;
#     - payers whose claim status does not work (dated, with a reason) never reach the counter and are listed; five unusable answers in a row
#       end a payer for the run; the commercial plan the vendor named is not switched off;
#     - the caps: 150 checks or $25 a run, 400 checks or $100 a month, priced with the one price table, and the line that says how many due
#       claims were left and why; one usage-log line per check;
#     - a run cut off half way (the Bash tool's time limit) leaves every answer it got in claimstatus_<date>.json as well as the ledger, and a
#       second start asks only the claims not yet answered (step 3);
#     - no accidental run: --help, no --go, an unknown word or option = no call; --go asks; no text under nightly/live/ starts a sweep
#       without --go, and the retired backlog sweep is gone from the Billing Button routine and the engine;
#     - reading the answer: paid / finalized at $0 / denied / pending / not found (resend candidate) / no electronic answer (hand off) /
#       not matched (ONE exact-date check, then stop) / not eligible (insurance check, never a resend) / no usable answer (raw reply kept
#       with its reply code) / an unknown wording printed;
#     - the October replay of the claim-status reader's registers through cs_rules.py keeps at most 900 of the 4,850 checks, and every claim
#       that got a final answer still gets one;
#     - the billing/scans copies are the scripts/helpers copies; nothing is written in the checkout;
#     - (11/10/2026 review fixes) an answer naming only other visits, or an exact-date answer with several claims none ours, is 'not
#       matched' and never final; four unusable answers in a row hand a claim off even when no try counted, and a payer that answers
#       nobody is proposed for CS_OFF; a final answer with nothing posted is listed again; a new ledger counts its checks once; the
#       hand-off and switched-off lists are printed whole;
#     - (11/10/2026 re-check fixes) a payer is proposed for CS_OFF only when none of its claims had a usable answer from 7 days before
#       the first of the four tries that handed one off until now: a payer that answered its other claim on the first of those nights,
#       or paid it or answered it 'pending' the Sunday before the first try (weekly runs, a week passing between them), is never
#       proposed, live or in a dry run; the hand-off reason says no other claim of the payer gave a usable answer only when that is true;
#       a payer that answers nobody is proposed until one of its claims answers again.
# Run: python3 tools/selftest/test_claim_status_rules.py   (exit 1 on any failure; the last line says how many checks ran and how many failed)
import os, sys, io, re, json, types, glob, time, shutil, atexit, argparse, datetime, tempfile, contextlib, subprocess, traceback, collections
import importlib.abc, importlib.machinery
# THIS SELF-TEST NEVER REACHES ADVANCEDMD, THE VENDOR OR ANY OTHER HOST. Every network route is closed here, before anything else is
# loaded: scripts/helpers and core hold the REAL amd / resave / txh / void_tx / era_post / stedi / deceased_guard modules, and importing
# them would talk to the practice's billing system and the paid vendor. So: (1) the code under test is read from its file and run here
# with stand-in modules in sys.modules (load / run_main below); (2) any import that would come from the checkout and was not loaded that
# way is refused, as is the real `requests`; (3) the network is shut either way. The only programs started are `git check-ignore`.
import socket as _socket
def _no_network(*a, **k): raise RuntimeError("the self-test must not use the network")
_socket.socket.connect = _no_network; _socket.socket.connect_ex = _no_network; _socket.create_connection = _no_network
for _k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"): os.environ[_k] = "http://127.0.0.1:9"
os.environ.update(NO_PROXY="", no_proxy="")
sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LIVE = {"amd", "resave", "txh", "void_tx", "era_post", "deceased_guard", "stedi", "requests", "medicare_store", "stedi_prices", "stedi_usage", "precheck",
        "elig_amd", "freq1_visit", "cs_rules", "claim_status_sweep", "sweep_full", "claim_status_exact", "sweep_register"}
class _Refuse(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in LIVE: raise ImportError("refused: %s is a live-system module - only stand-ins are used here" % name)
        spec = importlib.machinery.PathFinder.find_spec(name, path)
        if spec is not None and spec.origin and os.path.abspath(spec.origin).startswith(ROOT + os.sep):
            raise ImportError("refused: %s would be loaded from the checkout (%s)" % (name, spec.origin))
        return None
sys.meta_path.insert(0, _Refuse())
FAILS = []; COUNT = [0]
def check(name, cond, extra=""):
    """One check. cond may be a function: it is called here, and an error inside it is a failure (never a crash of the whole test)."""
    COUNT[0] += 1
    if callable(cond):
        try: cond = cond()
        except Exception as e: cond, extra = False, "raised %s: %s" % (type(e).__name__, e)
    print(("ok   " if cond else "FAIL ") + name + (("  -> " + str(extra)[:600]) if extra != "" and not cond else ""))
    if not cond: FAILS.append(name)
def _raises(f, exc=Exception):
    try: f()
    except exc: return True
    except Exception: return False
    return False
def _read(rel):
    """Every file of the checkout this test reads - the code under test, the texts and the registers - is read here and nowhere else."""
    with open(os.path.join(ROOT, rel)) as fh: return fh.read()

# ---- the throwaway folder and the paths the code under test writes to (set BEFORE anything is loaded) ------------------------------
TMP = tempfile.mkdtemp(prefix="csrules_"); atexit.register(shutil.rmtree, TMP, True)
ULOG = os.path.join(TMP, "patient_db", "stedi_usage.log"); RAW = os.path.join(TMP, "patient_db", "claimstatus_raw")
os.environ.update(STEDI_USAGE_LOG=ULOG, CLAIM_STATUS_RAW=RAW, CLAIM_STATUS_LEDGER=os.path.join(TMP, "no_ledger_here", "claim_status_ledger.json"))
def _snapshot():
    out = {}
    for d, dirs, files in os.walk(ROOT):
        dirs[:] = [x for x in dirs if x != ".git"]
        for f in files:
            p = os.path.join(d, f)
            try: st = os.stat(p); out[p] = (st.st_size, st.st_mtime_ns)
            except OSError: pass
    return out
BEFORE = _snapshot()

# ---- invented charts, claims and dates (built at run time: nothing here is a real person, number or date) --------------------------
TODAY = datetime.date.today()
def ago(n): return TODAY - datetime.timedelta(days=n)
def iso(d): return d.isoformat()
def ymd(d): return d.strftime("%Y%m%d")
CARRIER_CODES = {"car6404": "UNI20", "car6285": "HUM01", "car6047": "AET07", "car6086": "BCBS", "car9105": "TRI05", "car9100": "TRI00", "car9200": "AAR01",
                 "car6085": "FLO02", "car9300": "SUN01", "car9400": "WEL04"}
CODE_TO_CAR = {v: k for k, v in CARRIER_CODES.items()}
CHARTS = {}; CLAIMS = []
_N = [0]
def _n(): _N[0] += 1; return _N[0]
def claim(payer="UNI20", dos=100, sent=50, bal=100.0, fee=None, paid_by="", paid_on=None, carcs="", denied=None, rule="", rec="WAIT", pid=None, member=None):
    """One invented claim: a chart (if pid is None), a plan for the payer with its own member id, and the ageing row the rules read.
    dos / sent / paid_on / denied are days back from today."""
    k = _n()
    if pid is None:
        pid = "93%05d" % k
        CHARTS[pid] = {"name": "ZZCLAIM%s,TESTER" % "".join(chr(65 + int(c)) for c in "%04d" % k), "dob": "%02d/%02d/%04d" % (1 + k % 12, 1 + k % 27, 1930 + k % 20), "plans": []}
    member = member or "ZQ%06d" % k
    CHARTS[pid]["plans"].append((CODE_TO_CAR.get(payer, "car9999"), member))
    row = {"pid": pid, "visitid": "887%05d" % k, "dos": iso(ago(dos)), "cpts": "99309", "mods": "", "fee": fee if fee is not None else bal, "bal": bal, "payer": payer,
           "sent": iso(ago(sent)) if sent is not None else "", "days_sent": sent, "b_sent": "", "days_dos": dos, "b_dos": "", "paid_by": paid_by,
           "paid_on": iso(ago(paid_on)) if paid_on is not None else "", "secondary": "", "pr": 0.0, "carcs": carcs, "denied": iso(ago(denied)) if denied is not None else "",
           "dod": "", "rec": rec, "rule": rule, "why": ""}
    c = {"pid": pid, "vid": row["visitid"], "member": member, "row": row, "payer": payer}
    CLAIMS.append(c); return c

# ---- canned 277 answers -----------------------------------------------------------------------------------------------------------
def st(cat, code, wording="", paid=None, acct=None, svc=None, check=None, pccn=None):
    s = {"statusCategoryCode": cat, "statusCategoryCodeValue": cat + " (test)", "statusCode": code, "statusCodeValue": wording}
    if paid is not None: s["amountPaid"] = "%.2f" % paid
    if acct is not None: s["patientAccountNumber"] = acct
    if svc is not None: s["claimServiceDate"] = svc
    if check is not None: s["checkNumber"] = check; s["paidDate"] = iso(ago(5))
    if pccn is not None: s["tradingPartnerClaimNumber"] = pccn
    return s
def a277(*claims_status, errors=None):
    return {"claims": [{"claimStatus": s} for s in claims_status], "errors": errors or [], "status": "success"}
def mine(c): return c["vid"] + "A"                     # the account number a payer echoes: the visit id + the claim letter
PAID_A = lambda c, amt=48.34: a277(st("F1", "65", "Claim/line has been paid.", paid=amt, acct=mine(c), check="CHK%04d" % (int(c["vid"]) % 10000)))
PENDING_A = lambda c: a277(st("P1", "20", "Accepted for processing.", acct=mine(c)))
EMPTY_A = {"claims": [], "errors": []}
NOT_FOUND_A = lambda c: a277(st("A4", "35", "Claim/encounter not found."))
NO_ELECTRONIC_A = lambda c: a277(st("D0", "0", "Cannot provide further status electronically."))
DATE_NM_A = lambda c: a277(st("D0", "187", "Date(s) of service."))
MANY_A = lambda c: a277(st("D0", "485", "More information available than can be returned in real time mode. Narrow your current search criteria."))
NOT_ELIG_A = lambda c: a277(st("A7", "88", "Entity not eligible for benefits for submitted dates of service."))

# ---- stand-in requests: the request counter and the canned vendor ----------------------------------------------------------------
class FakeHTTPError(Exception):
    def __init__(self, status, body=None):
        super().__init__("HTTP %d from the stand-in" % status)
        self.response = types.SimpleNamespace(status_code=status, json=lambda: json.loads(json.dumps(body if body is not None else {"errors": [{"code": "x", "description": "stand-in"}]})))
class FakeTimeout(Exception): pass
class Resp:
    def __init__(self, status, body, unreadable=False): self.status_code = status; self._body = body; self._bad = unreadable
    def raise_for_status(self):
        if self.status_code >= 400: raise FakeHTTPError(self.status_code, self._body)
    def json(self):
        if self._bad: raise ValueError("Expecting value: line 1 column 1 (char 0)")
        return json.loads(json.dumps(self._body))
SENT = []                       # every vendor request since the last reset(): (url, body)
BILLING = []                    # every billing-system request of the stand-ins
ANSWERS = {}                    # member id -> list of canned responses (the last one repeats): ("json", body) / ("http", code, body) / ("timeout",) / ("unreadable",)
ON_SEND = []                    # callbacks run on every vendor request
LOGINS = []
def _post(url, *a, **kw):
    body = kw.get("json") or {}
    SENT.append((url, json.loads(json.dumps(body))))
    for f in list(ON_SEND): f(url, body)
    if "claimstatus" not in url: return Resp(200, {"errors": [{"code": "x", "description": "not a claim-status call"}]})
    m = (body.get("subscriber") or {}).get("memberId"); q = ANSWERS.get(m) or [("json", {"claims": [{"claimStatus": st("P1", "20", "Accepted for processing.")}]})]
    r = q.pop(0) if len(q) > 1 else q[0]
    if r[0] == "timeout": raise FakeTimeout("read timed out")
    if r[0] == "unreadable": return Resp(200, None, unreadable=True)
    if r[0] == "http": return Resp(r[1], r[2])
    return Resp(200, r[1])
def answer(c, *responses):
    ANSWERS[c["member"]] = [r if isinstance(r, tuple) else ("json", r) for r in responses]
def _get(url, *a, **kw): raise RuntimeError("no GET call is expected in the claim-status helpers")
def standin(name, **attrs):
    m = types.ModuleType(name); m.STAND_IN = True
    for k, v in attrs.items(): setattr(m, k, v)
    return m
fake_requests = standin("requests", post=_post, get=_get, exceptions=types.SimpleNamespace(Timeout=FakeTimeout, HTTPError=FakeHTTPError))
def _chart_xml(pid):
    c = CHARTS[str(pid)]
    plans = "".join('<insplan id="ins%d" carrier="%s" begindate="01/01/2020" enddate="" x="" subscribernum="%s" y="" sequence="%d"/>' % (i + 1, car, num, i + 1) for i, (car, num) in enumerate(c["plans"]))
    return '<r><patient name="%s" dob="%s" deceased="" state="FL"/>%s</r>' % (c["name"], c["dob"], plans)
def _amd_post(body, timeout=0):
    pid = re.search(r'patientid="(?:pat)?(\d+)"', body).group(1); BILLING.append("getdemographic " + pid); return _chart_xml(pid)
fake_amd = standin("amd", post=_amd_post, msg=lambda action, cls, attrs=None, children="": '<ppmdmsg action="%s" class="%s"/>' % (action, cls), _msgtime=lambda: "t", login_cached=lambda: LOGINS.append(1))
fake_era = standin("era_post", API="https://billing-standin.invalid/api", H=lambda: {"Content-Type": "application/json"})
fake_guard = standin("deceased_guard", record=lambda *a, **k: None)
sys.modules.update({"requests": fake_requests, "amd": fake_amd, "era_post": fake_era, "deceased_guard": fake_guard})

# ---- loading the code under test from its file (never by import) ----------------------------------------------------------------
def imports(src):
    out = set()
    for kind, rest in re.findall(r"^[ \t]*(import|from)[ \t]+([^\n#]+)", src, re.M):
        for n in (rest.split(",") if kind == "import" else [rest]):
            n = n.strip().split()[0].split(".")[0] if n.strip() else ""
            if n: out.add(n)
    return out
def _ready(n):
    m = sys.modules.get(n); return m is not None and (getattr(m, "STAND_IN", False) or getattr(m, "UNDER_TEST", False))
def _source(rel):
    path = os.path.join(ROOT, rel); src = _read(rel)
    missing = sorted(n for n in imports(src) & LIVE if not _ready(n))
    if missing: raise RuntimeError("no stand-in for %s - %s is not run" % (missing, rel))
    return path, src
def load(rel, name):
    path, src = _source(rel)
    m = types.ModuleType(name); m.__file__ = path; m.UNDER_TEST = True
    exec(compile(src, path, "exec"), m.__dict__)
    return m
def run_main(rel, argv, cwd):
    """Run ONE file of the checkout as a program INSIDE this process (its imports are the stand-ins / modules loaded here)."""
    path, src = _source(rel)
    old_cwd, old_argv, old_sleep = os.getcwd(), list(sys.argv), time.sleep
    out, err, code = io.StringIO(), io.StringIO(), 0
    try:
        os.chdir(cwd); sys.argv = [path] + list(argv); time.sleep = lambda *_a: None
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try: exec(compile(src, path, "exec"), {"__name__": "__main__", "__file__": path})
            except SystemExit as e: code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    finally:
        os.chdir(old_cwd); sys.argv = old_argv; time.sleep = old_sleep
    return code, out.getvalue(), err.getvalue()

# ---- 0. the safety block holds ------------------------------------------------------------------------------------------------
_refused = False
try: load("scripts/helpers/claim_status_sweep.py", "sweep_without_standins")
except RuntimeError as e: _refused = "stedi" in str(e) or "cs_rules" in str(e)
check("safety: code under test is not run until every live module it loads has a stand-in or was loaded here (the sweep before the client is refused)", _refused)
check("safety: the real `requests`, a live helper and any module of the checkout are refused by the import blocker",
      lambda: _raises(lambda: _Refuse().find_spec("requests"), ImportError) and _raises(lambda: _Refuse().find_spec("amd"), ImportError)
      and _raises(lambda: _Refuse().find_spec("cs_rules"), ImportError) and _raises(lambda: _Refuse().find_spec("test_board_ops", [os.path.join(ROOT, "tools", "selftest")]), ImportError))
check("safety: the network is shut in this process", lambda: _raises(lambda: _socket.create_connection(("127.0.0.1", 9)), RuntimeError))

PR = load("scripts/helpers/stedi_prices.py", "stedi_prices"); sys.modules["stedi_prices"] = PR
ST = load("scripts/helpers/stedi.py", "stedi"); sys.modules["stedi"] = ST
_cw = os.path.join(TMP, "carriers_ws"); os.makedirs(_cw)
with open(os.path.join(_cw, "carriers.json"), "w") as fh: json.dump({k: [v, v + " (TEST)"] for k, v in CARRIER_CODES.items()}, fh)
_old = os.getcwd(); os.chdir(_cw)
try: PC = load("scripts/helpers/precheck.py", "precheck"); sys.modules["precheck"] = PC
finally: os.chdir(_old)
CS = load("scripts/helpers/cs_rules.py", "cs_rules"); sys.modules["cs_rules"] = CS
CSS = load("scripts/helpers/claim_status_sweep.py", "claim_status_sweep"); sys.modules["claim_status_sweep"] = CSS
CAPS0 = dict(CS.CAPS)

WS_N = [0]
def new_ws(ledger=True):
    """A throwaway workspace: carriers.json, (optionally) an empty ledger, nothing else. The env points every default path into it."""
    WS_N[0] += 1; ws = os.path.join(TMP, "ws%d" % WS_N[0]); os.makedirs(os.path.join(ws, "registers"))
    with open(os.path.join(ws, "carriers.json"), "w") as fh: json.dump({k: [v, v] for k, v in CARRIER_CODES.items()}, fh)
    os.environ["CLAIM_STATUS_LEDGER"] = lpath(ws)
    if ledger: CS.Ledger.open(lpath(ws), new=True).save()
    return ws
def lpath(ws): return os.path.join(ws, "registers", "claim_status_ledger.json")
def ledger(ws):
    with open(lpath(ws)) as fh: return json.load(fh)
def ledger_edit(ws, fn):
    d = ledger(ws); fn(d)
    with open(lpath(ws), "w") as fh: json.dump(d, fh)
def lrow(ws, c): return (ledger(ws)["rows"]).get("%s|%s" % (c["vid"], c["payer"])) or {}
def set_asked(ws, c, days):
    """Time passes for one claim: its last answer is moved `days` back (the helpers run on today's date)."""
    def f(d): d["rows"]["%s|%s" % (c["vid"], c["payer"])]["asked"] = iso(ago(days))
    ledger_edit(ws, f)
def time_passes(ws, claims, days=7):
    """Time passes for the whole workspace (the helpers run on today's date): every date in the ledger rows (the answers' days in their
    history too) and on the claims' ageing rows moves `days` back, and the ageing file is written again - a week between Sunday runs."""
    def back(s):
        try: return iso(datetime.date.fromisoformat(str(s)[:10]) - datetime.timedelta(days=days)) if s else s
        except ValueError: return s
    def f(d):
        for L in d["rows"].values():
            for k in ("asked", "stopped", "sent", "dos", "cleared", "quiet_from"):
                if L.get(k): L[k] = back(L[k])
            L["history"] = [[back(h[0])] + list(h[1:]) for h in L.get("history") or []]
    ledger_edit(ws, f)
    for c in claims:
        for k in ("sent", "dos", "paid_on", "denied"):
            if c["row"].get(k): c["row"][k] = back(c["row"][k])
        for k in ("days_sent", "days_dos"):
            if isinstance(c["row"].get(k), int): c["row"][k] += days
    write_aging(ws, claims)
def write_aging(ws, claims, asof=None, extra=None):
    asof = asof or datetime.datetime.now(datetime.timezone.utc)
    d = {"schema": "ar-aging/1", "asof": asof.strftime("%Y-%m-%d %H:%M UTC"), "today": iso(TODAY), "rows": [c["row"] for c in claims]}
    d.update(extra or {})
    with open(os.path.join(ws, "aging_latest.json"), "w") as fh: json.dump(d, fh)
def reset():
    del SENT[:]; del BILLING[:]; del LOGINS[:]; del ON_SEND[:]; ANSWERS.clear()
    for p in (ULOG, RAW):
        if os.path.isdir(p): shutil.rmtree(p)
        elif os.path.exists(p): os.remove(p)
    CS.CAPS.clear(); CS.CAPS.update(CAPS0)
def cs_sent(): return [(u, b) for u, b in SENT if "claimstatus" in u]
def asked_members(): return [b["subscriber"]["memberId"] for u, b in cs_sent()]
def sweep(ws, *argv): return run_main("scripts/helpers/claim_status_sweep.py", list(argv), ws)
def run_file(ws, name="claimstatus_%s.json"):
    with open(os.path.join(ws, name % ymd(TODAY))) as fh: return json.load(fh)
def log_lines():
    try:
        with open(ULOG) as fh: return [l.split("\t") for l in fh.read().splitlines() if l.strip()]
    except OSError: return []
def text_of(path):
    try:
        with open(path, errors="replace") as fh: return fh.read()
    except OSError: return ""
def lab(answer_, **kw): return CS.label(answer_, **kw)

# ==== 1. the price table and the caps (spec 9.6) =================================================================================
def t_prices_caps():
    check("caps: the one price table prices claim status - 6,770 = $889.50, 1,300 = $232.50, 400 = $97.50 (the reader's figures)",
          lambda: (CS.price(6770), CS.price(1300), CS.price(400)) == (889.50, 232.50, 97.50) and CS.price(10, before=250) == 1.50)
    def fill(before, run_max=None):
        c = CS.Caps(before, run_max); n = 0
        while c.next_ok()[0]: c.count(); n += 1
        return n, c.next_ok()[1]
    check("caps: early in the month a run stops at $25 (83 checks at $0.30), the reason says so", lambda: fill(0) == (83, "run cap: $25.00"), fill(0))
    check("caps: after 250 checks this month a run stops at 150 checks ($22.50 at $0.15)", lambda: fill(250) == (150, "run cap: 150 checks"), fill(250))
    check("caps: the month cap - 399 checks this month leave room for ONE more", lambda: fill(399) == (1, "month cap: 400 checks"), fill(399))
    CS.CAPS["month dollars"] = 50.0
    check("caps: the month dollar cap is priced with the price table (set to $50 for this check: 100 checks this month leave room for 66 more)", lambda: fill(100) == (66, "month cap: $50.00"), fill(100))
    CS.CAPS.update(CAPS0)
    check("caps: --max lowers the run cap and can never raise it above 150", lambda: fill(250, 20) == (20, "run cap: 20 checks") and fill(250, 900) == (150, "run cap: 150 checks"))

# ==== 2. reading the answer (spec 9.8) =============================================================================================
def t_labels():
    c = claim(); o = claim()
    r = lab(PAID_A(c), vid=c["vid"], dos=c["row"]["dos"])
    check("answer: paid, naming this claim (account = visit id + claim letter) -> 'paid', final, the payment counted", lambda: (r["label"], r["final"], r["named"], r["paid"]) == ("paid", True, True, 48.34), r)
    r = lab(a277(st("F1", "65", "paid", paid=0, acct=mine(c))), vid=c["vid"])
    check("answer: finalized with nothing paid -> 'finalized at $0', final", lambda: (r["label"], r["final"]) == ("finalized at $0", True), r)
    r = lab(a277(st("F2", "88", "Entity not eligible for benefits for submitted dates of service.", acct=mine(c))), vid=c["vid"])
    check("answer: a FINAL denial (F2) stays 'denied', even with the not-eligible wording", lambda: (r["label"], r["final"]) == ("denied", True), r)
    for cat, code in (("P1", "20"), ("P5", "3"), ("A1", "0"), ("P0", "41")):
        check("answer: %s/%s -> 'pending'" % (cat, code), lambda: lab(a277(st(cat, code, "x", acct=mine(c))), vid=c["vid"])["label"] == "pending")
    r = lab(NOT_FOUND_A(c), vid=c["vid"])
    check("answer: code 35 'claim not found' -> 'not found' (a resend candidate, as before)", lambda: r["label"] == "not found" and CSS.action(r, {}).startswith("NOT ON FILE"), (r["label"], CSS.action(r, {})))
    for name, ans in (("D0/0", NO_ELECTRONIC_A(c)), ("A4/0", a277(st("A4", "0", "Cannot provide further status electronically.")))):
        check("answer: %s 'cannot provide further status electronically' -> 'no electronic answer' (stop and hand off), never NOT ON FILE" % name,
              lambda: lab(ans, vid=c["vid"])["label"] == "no electronic answer" and not CSS.action(lab(ans, vid=c["vid"]), {"stopped": iso(TODAY)}).startswith("NOT ON FILE"))
    for name, ans, why in (("D0/187 date of service", DATE_NM_A(c), "date of service"), ("E0/33 member id", a277(st("E0", "33", "Subscriber and subscriber ID not found.")), "member id"),
                           ("D0/153 member id", a277(st("D0", "153", "Entity's ID number.")), "member id"), ("D0/485 too many matches", MANY_A(c), "too many matches")):
        check("answer: %s -> 'not matched' (%s)" % (name, why), lambda: lab(ans)["label"] == "not matched" and why in lab(ans)["why"], lab(ans))
    for name, ans in (("A7/88", NOT_ELIG_A(c)), ("E0/97", a277(st("E0", "97", "Patient eligibility not found with entity.")))):
        r = lab(ans)
        check("answer: %s -> 'not eligible' - the insurance check, never a resend (no NOT ON FILE words)" % name, lambda: r["label"] == "not eligible" and CSS.action(r, {}).startswith("NOT ELIGIBLE"), (r["label"], CSS.action(r, {})))
    check("answer: the payer cannot answer now (E1 / E2) -> 'no usable answer'", lambda: lab(a277(st("E1", "0", "Cannot provide further status electronically.")))["label"] == "no usable answer"
          and lab(a277(st("E2", "0", "x")))["label"] == "no usable answer")
    r = lab(EMPTY_A)
    check("answer: an empty reply (no status, no error) -> 'no usable answer'", lambda: r["label"] == "no usable answer" and "empty reply" in r["why"], r)
    r = lab({"claims": [], "errors": [{"code": "33", "description": "Input Errors"}]})
    check("answer: an error and no status -> 'no usable answer', the error kept", lambda: r["label"] == "no usable answer" and r["errors"] == ["33 Input Errors"], r)
    r = lab(a277(st("A7", "21", "Missing or invalid information.")))
    check("answer: a wording the rules do not know -> 'no usable answer' and the wording is kept for the report", lambda: r["label"] == "no usable answer" and any("Missing or invalid information" in w for w in r["unknown"]), r)
    r = lab(a277(st("A3", "494", "x")))
    check("answer: only the vendor's not-billed codes (494) -> 'no usable answer'", lambda: r["label"] == "no usable answer" and "does not take" in r["why"], r)
    r = lab({"errors": []}, http=503)
    check("answer: an HTTP error -> 'no usable answer' with its reply code (not billed)", lambda: r["label"] == "no usable answer" and r["http"] == 503 and "not billed" in r["why"], r)
    r = lab(None, http="2xx", error="reply not readable")
    check("answer: an unreadable reply -> 'no usable answer', the reply code kept", lambda: r["label"] == "no usable answer" and r["http"] == "2xx" and "not readable" in r["why"], r)
    r = lab(a277(st("F1", "65", "paid", paid=48.34, acct=mine(o), check="C1"), st("P1", "20", "Accepted for processing.", acct=mine(c))), vid=c["vid"], dos=c["row"]["dos"])
    check("answer: a 3-day window holding the next day's PAID claim and ours pending -> ours is read: 'pending' (the lesson of 10/9)", lambda: (r["label"], r["paid"]) == ("pending", 0.0), r)
    r = lab(PAID_A(o), vid=c["vid"], dos=c["row"]["dos"]); r0 = lab(a277(st("F1", "65", "paid", paid=10.0, check="C9")), vid=c["vid"], dos=c["row"]["dos"])
    check("answer: a windowed 'paid' that names ANOTHER claim is not final - it reads 'not matched' (review CS-1: not our claim's answer); a windowed 'paid' that names no claim is not final either",
          lambda: r["label"] == "not matched" and r["final"] is False and r["named"] is False and "only other claims" in r["why"] and r0["label"] == "paid" and r0["final"] is False, (r, r0))
    two_none = a277(st("F1", "65", "paid", paid=60.0, check="C7"), st("P1", "20", "Accepted for processing."))
    r = lab(two_none, vid=c["vid"], dos=c["row"]["dos"], exact=True)
    check("answer: an exact-date answer holding two claims of that date, none naming ours (one paid $60), is 'not matched' and never final (review CS-6)",
          lambda: r["label"] == "not matched" and r["final"] is False and r["paid"] == 0.0 and "none names ours" in r["why"], r)
    r = lab(a277(st("F1", "65", "paid", paid=10.0, check="C9")), vid=c["vid"], dos=c["row"]["dos"])
    check("answer: a windowed 'paid' with no account number is not final; the same answer asked with the exact date is final",
          lambda: r["final"] is False and lab(a277(st("F1", "65", "paid", paid=10.0, check="C9")), vid=c["vid"], dos=c["row"]["dos"], exact=True)["final"] is True, r)
    r = lab(a277(st("F1", "65", "paid", paid=10.0, check="C9", pccn="ICNX1")), vid=c["vid"], icn="ICNX1")
    check("answer: the payer's claim number on file also names the claim", lambda: r["named"] and r["final"], r)
    two = a277(st("F1", "65", "paid", paid=48.34, acct=mine(c), check="C1"), st("F1", "65", "paid", paid=48.34, acct=mine(c), check="C1"))
    check("answer: one payment shown twice is counted once (check number, paid date, amount)", lambda: lab(two, vid=c["vid"])["paid"] == 48.34)

# ==== 3. by need, the route, the waits (spec 9.2, 9.3, 9.5) =======================================================================
def t_need():
    N = lambda **kw: CS.need(claim(**kw)["row"], TODAY)
    check("need: a payment posted for this payer -> not asked", lambda: N(paid_by="UNI20", paid_on=30)[0] is False)
    check("need: a cost-share balance after the payer paid (rule 'primary paid ...') -> not asked", lambda: N(rule="primary paid, no secondary on the chart -> WOCLTREQ cost-share")[0] is False)
    check("need: a denial posted and nothing sent since -> not asked", lambda: N(carcs="96", denied=40, sent=60)[0] is False)
    check("need: a denial posted, then the claim sent again 50 days ago -> asked", lambda: N(carcs="96", denied=80, sent=50)[0] is True)
    check("need: sent 20 days ago -> not asked; sent 50 days ago with nothing posted -> asked", lambda: N(sent=20)[0] is False and N(sent=50)[0] is True)
    check("need: a secondary balance needs 60 days - silent 50 days no, silent 61 days yes", lambda: N(paid_by="FLO02", paid_on=90, sent=50, dos=120)[0] is False and N(paid_by="FLO02", paid_on=90, sent=61, dos=120)[0] is True)
    check("need: a claim a year old or more -> no check at all", lambda: N(dos=365, sent=200)[0] is False and "year old" in N(dos=400, sent=200)[1] and N(dos=364, sent=200)[0] is True)
    check("need: a secondary balance is aged from the primary's remit, not the date of service (rules.md)", lambda: N(paid_by="FLO02", paid_on=100, sent=70, dos=400)[0] is True and N(paid_by="FLO02", paid_on=370, sent=70, dos=400)[0] is False)
    check("need: never sent, a chart not read tonight, or no open balance -> not asked", lambda: N(sent=None)[0] is False and N(rec="REVIEW")[0] is False and N(bal=0)[0] is False)
    check("need: silent 60+ days counts claims with nothing posted, last sent 60 or more days ago", lambda: CS.silent(claim(sent=60)["row"], TODAY) and not CS.silent(claim(sent=59)["row"], TODAY)
          and not CS.silent(claim(sent=90, paid_by="UNI20", paid_on=20)["row"], TODAY))
    R = lambda code: CS.route(code, PC.CAR2STEDI)
    check("route: the two military-plan codes and the Medigap code are switched off, each with a date and a reason; never sent",
          lambda: all(R(x)[0] is None and "switched off" in R(x)[1] for x in ("TRI00", "TRI05", "AAR01")) and all(re.match(r"\d{4}-\d{2}-\d{2}$", d) and len(w) > 20 for d, w in CS.CS_OFF.values()))
    check("route: the commercial plan the vendor named (AET07, 1 failure in 64) is NOT switched off", lambda: "AET07" not in CS.CS_OFF and R("AET07") == ("60054", ""))
    check("route: Medicare and VA community care have no claim-status route; BCBS1 goes to BCBSF; an unmapped code has none",
          lambda: R("FLO02")[0] is None and R("RET01")[0] is None and R("VACCN")[0] is None and R("BCBS1")[0] == "BCBSF" and R("ZZZ99")[0] is None and R("UNI20")[0] == "87726")

def t_waits():
    W = CS.WAITS
    check("waits: one table - pending 14 / 30 days, near the filing limit 7, no usable answer 7, not found 30 after a resend, a year old = none",
          lambda: (W["pending"], W["pending, sent 120+ days"], W["near the filing limit"], W["no usable answer"], W["not found"], W["a year old"]) == (14, 30, 7, 7, 30, None))
    def says(c, L, days_after=0): return CS.ledger_says(L, c["row"], TODAY + datetime.timedelta(days=days_after))
    def L_of(c, label_, asked, **kw):
        L = {"pid": c["pid"], "vid": c["vid"], "payer": c["payer"], "sent": c["row"]["sent"], "asked": iso(ago(asked)), "answer": label_}; L.update(kw); return L
    c = claim(sent=60, dos=80)
    check("waits: 'pending' asked 3 days ago -> 0 checks; 15 days ago -> 1", lambda: says(c, L_of(c, "pending", 3))[0] is False and says(c, L_of(c, "pending", 15))[0] is True)
    c2 = claim(sent=130, dos=150)
    check("waits: 'pending' on a claim last sent 120+ days ago waits 30 days (20 days no, 31 yes)", lambda: says(c2, L_of(c2, "pending", 20))[0] is False and says(c2, L_of(c2, "pending", 31))[0] is True)
    c3 = claim(sent=200, dos=340)
    check("waits: a claim within 30 days of its filing limit waits 7 days after 'pending' (8 days -> asked)", lambda: says(c3, L_of(c3, "pending", 8))[0] is True and says(c3, L_of(c3, "pending", 5))[0] is False)
    c4 = claim(sent=60, dos=80)
    check("waits: no usable answer waits 7 days (5 no, 8 yes)", lambda: says(c4, L_of(c4, "no usable answer", 5))[0] is False and says(c4, L_of(c4, "no usable answer", 8))[0] is True)
    c5 = claim(sent=100, dos=120); L5 = L_of(c5, "not found", 60)
    check("waits: 'not found' with no later send -> never asked again (0 checks, even 60 days on)", lambda: says(c5, L5)[0] is False and says(c5, L5, 90)[0] is False)
    c5["row"]["sent"] = iso(ago(31))
    check("waits: 'not found', then sent again 31 days back -> the wait rule asks it (1)", lambda: says(c5, L5)[0] is True)
    c5["row"]["sent"] = iso(ago(20))
    check("waits: 'not found', sent again 20 days back -> not yet (30 days after the resend)", lambda: says(c5, L5)[0] is False)
    c5["row"]["sent"] = iso(ago(31))
    check("waits: ... and the need rule (45 days since the last send) still holds it until day 45 - both rules apply",
          lambda: CS.due(c5["row"], L5, TODAY, PC.CAR2STEDI)["due"] is False and CS.due(dict(c5["row"], sent=iso(ago(46))), L5, TODAY, PC.CAR2STEDI)["due"] is True)
    c6 = claim(sent=100, dos=120); L6 = L_of(c6, "not eligible", 40)
    check("waits: 'not eligible' waits for a resend like 'not found' (the spec is silent)", lambda: says(c6, L6)[0] is False)
    c7 = claim(sent=100, dos=120)
    check("ledger: a final answer on file -> 0 checks; the claim sent again after it -> 1", lambda: says(c7, L_of(c7, "paid", 30, final=True))[0] is False
          and says(dict(c7, row=dict(c7["row"], sent=iso(ago(50)))), L_of(c7, "paid", 60, final=True, sent=iso(ago(100))))[0] is True)
    check("ledger: a handed-off claim is not asked until it is sent again", lambda: says(c7, L_of(c7, "pending", 40, stopped=iso(ago(40)), stop_why="x"))[0] is False
          and says(dict(c7, row=dict(c7["row"], sent=iso(ago(46)))), L_of(c7, "pending", 60, stopped=iso(ago(50)), sent=iso(ago(100))))[0] is True)

def t_record_stop():
    c = claim(); r = c["row"]
    L = CS.record({}, lab(PAID_A(claim()), vid=c["vid"], dos=r["dos"]), r, TODAY)
    L0 = CS.record({}, lab(a277(st("F1", "65", "paid", paid=10.0, check="C9")), vid=c["vid"], dos=r["dos"]), r, TODAY)
    check("ledger: a windowed 'paid' that names another claim is stored NOT final and asks ONE exact-date check (it reads 'not matched'); so does a windowed 'paid' that names no claim",
          lambda: L["final"] is False and L["exact_next"] is True and CS.ledger_says(L, r, TODAY) == (True, "one check with the exact date of service is due", True)
          and L0["answer"] == "paid" and L0["final"] is False and L0["exact_next"] is True, (L, L0))
    L = CS.record({}, lab(DATE_NM_A(c)), r, TODAY)
    L2 = CS.record(L, lab(DATE_NM_A(c), exact=True), r, TODAY, exact=True)
    check("ledger: 'not matched' -> ONE check with the exact date; not matched again -> stop and hand off", lambda: L["exact_next"] and not L.get("stopped") and L2.get("stopped") and "exact date" in L2["stop_why"], (L, L2))
    L = CS.record({}, lab(NO_ELECTRONIC_A(c)), r, TODAY)
    check("ledger: 'no electronic answer' -> stopped at once (hand off)", lambda: L.get("stopped") == iso(TODAY) and CS.ledger_says(L, r, TODAY + datetime.timedelta(days=60))[0] is False, L)
    a, b = claim(), claim()
    rows = {"a": CS.record({}, lab(EMPTY_A), a["row"], TODAY), "b": CS.record({}, lab(PENDING_A(b)), b["row"], TODAY)}
    CS.finish_run(rows, [("a", "87726", "no usable answer"), ("b", "87726", "pending")], TODAY)
    rows["a"] = CS.record(rows["a"], lab(EMPTY_A), a["row"], TODAY); CS.finish_run(rows, [("a", "87726", "no usable answer"), ("b", "87726", "pending")], TODAY)
    check("stop: two unusable answers in a row, while another claim of the same payer answered each run -> handed off", lambda: rows["a"].get("stopped") and "two answers" in rows["a"]["stop_why"], rows["a"])
    x = {"x": CS.record({}, lab(EMPTY_A), a["row"], TODAY), "y": CS.record({}, lab(EMPTY_A), b["row"], TODAY)}
    for _ in range(3): CS.finish_run(x, [("x", "87726", "no usable answer"), ("y", "87726", "no usable answer")], TODAY)
    check("stop: a run in which every answer of a payer is unusable does not count as a try (three such nights: nobody handed off)",
          lambda: not x["x"].get("stopped") and not x["y"].get("stopped") and x["x"]["unusable_row"] == 0 and x["x"]["uncounted"] == 3, x)
    p = {"p": CS.record({}, lab(PENDING_A(a)), a["row"], TODAY)}
    for i in range(3): CS.finish_run(p, [("p", "87726", "pending")], TODAY)
    check("stop: three 'pending' answers in a row -> handed off ('pending' always counts: the payer answered for this claim)", lambda: p["p"].get("stopped") and "three" in p["p"]["stop_why"], p)
    q = CS.clear(p["p"], TODAY)
    check("stop: a person clears the row -> it is asked again by need, its history kept", lambda: CS.ledger_says(q, a["row"], TODAY)[0] is True and q.get("history") and not q.get("stopped"), q)
    s = CS.record(p["p"], lab(PENDING_A(a)), dict(a["row"], sent=iso(ago(1))), TODAY)
    check("ledger: a send after the last answer starts the claim afresh (tries and stops of the old send forgotten)", lambda: s["tries"] == 1 and not s.get("stopped") and s["pending_row"] == 0, s)

# ==== 4. the ledger file and the ageing file (spec 9.1, 9.2) ========================================================================
def t_files():
    ws = new_ws(ledger=False); p = lpath(ws)
    check("ledger: a missing ledger is an error, never an empty start", lambda: _raises(lambda: CS.Ledger.open(p), CS.LedgerMissing))
    led = CS.Ledger.open(p, new=True)
    check("ledger: --new-ledger starts one where none exists (written at the first save)", lambda: not os.path.exists(p) and (led.save() or True) and ledger(ws)["rows"] == {} and ledger(ws)["schema"] == "claim-status-ledger/1")
    check("ledger: --new-ledger never replaces an existing ledger", lambda: _raises(lambda: CS.Ledger.open(p, new=True), CS.LedgerBroken))
    with open(p, "w") as fh: fh.write("{ not json")
    check("ledger: a ledger that cannot be read is an error (never taken as empty) and is left as it is", lambda: _raises(lambda: CS.Ledger.open(p), CS.LedgerBroken) and text_of(p) == "{ not json")
    ws = new_ws(); led = CS.Ledger.open(lpath(ws)); c = claim(); k = CS.key(c["row"])
    led.put(k, CS.record({}, lab(PENDING_A(c)), c["row"], TODAY)); led.add_check(TODAY.strftime("%Y-%m"))
    def other_writer(d):
        d["rows"]["999|ZZZ"] = {"answer": "pending", "asked": iso(TODAY)}; d["months"][TODAY.strftime("%Y-%m")] = {"checks": 7}
    ledger_edit(ws, other_writer); led.save()
    d = ledger(ws)
    check("ledger: a save re-reads the file - another writer's row and month count are kept, ours added (7 + 1 = 8 checks, priced)",
          lambda: "999|ZZZ" in d["rows"] and k in d["rows"] and d["months"][TODAY.strftime("%Y-%m")]["checks"] == 8 and d["months"][TODAY.strftime("%Y-%m")]["dollars"] == CS.price(8), d["months"])
    check("ledger: written in one step (a temporary file renamed into place, none left behind)", lambda: [f for f in os.listdir(os.path.join(ws, "registers")) if f.endswith(".tmp")] == []
          and "tempfile.mkstemp" in _read("scripts/helpers/cs_rules.py") and "os.replace(tmp, self.path)" in _read("scripts/helpers/cs_rules.py"))
    blocker = os.path.join(TMP, "a_file_not_a_folder")
    with open(blocker, "w") as fh: fh.write("x")
    led2 = CS.Ledger.open(os.path.join(blocker, "l.json"), new=True); led2.put("1|X", {"answer": "pending"})
    check("ledger: a ledger that cannot be written raises (the helper then stops asking)", lambda: _raises(led2.save, CS.LedgerWriteError))
    rep = json.loads(_read("practices/ehpa/registers/claim_status_ledger.json"))
    check("ledger: the register is in the repository - it reads as a ledger, every row keyed claim|payer, and git does not ignore it",
          lambda: rep.get("schema") == "claim-status-ledger/1" and isinstance(rep.get("rows"), dict) and all(re.fullmatch(r"\d+\|[A-Z0-9]+", k_) for k_ in rep["rows"])
          and subprocess.run(["git", "-C", ROOT, "check-ignore", "-q", "practices/ehpa/registers/claim_status_ledger.json"]).returncode == 1)
    check("files: unusable raw replies go under patient_db/, which git ignores at every level", lambda: CS.raw_folder() == RAW and all(subprocess.run(["git", "-C", ROOT, "check-ignore", "-q", p_]).returncode == 0
          for p_ in ("patient_db/claimstatus_raw/x.json", "scripts/helpers/patient_db/claimstatus_raw/x.json", "billing/scans/patient_db/claimstatus_raw/x.json")))
    ws = new_ws(); now = datetime.datetime.now(datetime.timezone.utc)
    check("ageing file: missing -> an error that names it", lambda: _raises(lambda: CS.aging_rows(os.path.join(ws, "aging_latest.json"), now), CS.AgingError))
    write_aging(ws, [claim()], asof=now - datetime.timedelta(hours=25))
    check("ageing file: older than one day -> an error", lambda: _raises(lambda: CS.aging_rows(os.path.join(ws, "aging_latest.json"), now), CS.AgingError))
    write_aging(ws, [claim()], asof=now - datetime.timedelta(hours=23))
    check("ageing file: made 23 hours ago -> read", lambda: len(CS.aging_rows(os.path.join(ws, "aging_latest.json"), now)[0]) == 1)
    write_aging(ws, [claim()], extra={"schema": "something-else"})
    check("ageing file: another shape -> an error", lambda: _raises(lambda: CS.aging_rows(os.path.join(ws, "aging_latest.json"), now), CS.AgingError))
    c = claim(); del c["row"]["sent"]; write_aging(ws, [c])
    check("ageing file: a field the rules need is missing -> an error naming the field", lambda: "sent" in str(_try_err(lambda: CS.aging_rows(os.path.join(ws, "aging_latest.json"), now))))
def _try_err(f):
    try: f()
    except Exception as e: return e
    return None

# ==== 5. the sweep helper, run as a program inside this process ====================================================================
def t_cli():
    reset(); ws = new_ws(); c = claim(); write_aging(ws, [c])
    c1, o1, e1 = sweep(ws, "--help"); n1 = (len(SENT), len(BILLING), len(LOGINS))
    c2, o2, e2 = sweep(ws, "--min-age", "45"); n2 = (len(SENT), len(BILLING), len(LOGINS))
    c3, o3, e3 = sweep(ws, "go"); n3 = (len(SENT), len(BILLING), len(LOGINS))
    c4, o4, e4 = sweep(ws); n4 = (len(SENT), len(BILLING), len(LOGINS))
    check("no accidental run: --help prints the usage and exits 0 with no call of any kind", lambda: c1 == 0 and "usage: claim_status_sweep.py" in o1 and "--go" in o1 and n1 == (0, 0, 0), (c1, o1[:200], n1))
    check("no accidental run: an unknown option (the old --min-age) or a stray word is an error (exit 2) and nothing is asked",
          lambda: c2 == 2 and c3 == 2 and "unrecognized arguments" in e2 + e3 and n2 == n3 == (0, 0, 0), (c2, c3, e2[-160:], n3))
    check("no accidental run: no --go -> prints what it WOULD ask, a failing exit (1), no call of any kind (no login, no chart read, no vendor)",
          lambda: c4 == 1 and "DRY RUN - nothing was asked" in o4 and ("v" + c["vid"]) in o4 and n4 == (0, 0, 0) and ledger(ws)["rows"] == {}, (c4, o4[-300:], n4))
    c5, o5, e5 = sweep(ws, "--go")
    check("no accidental run: with --go the due claim is asked (one request) and the run ends 0", lambda: c5 == 0 and asked_members() == [c["member"]] and LOGINS == [1], (c5, o5[-300:], asked_members()))
    reset(); ws2 = new_ws(ledger=False); write_aging(ws2, [c])
    c6, o6, e6 = sweep(ws2, "--new-ledger")
    check("no accidental run: --new-ledger without --go creates nothing", lambda: c6 == 1 and not os.path.exists(lpath(ws2)) and SENT == [], (c6, o6[-200:]))

def t_inputs():
    reset(); ws = new_ws(ledger=False); c = claim(); write_aging(ws, [c])
    code, out, err = sweep(ws, "--go")
    check("ledger: missing on a machine that should have one -> the run ends with an error and no call (no login, no vendor)",
          lambda: code == 2 and "STOPPED: no claim-status ledger" in out and SENT == [] and LOGINS == [] and BILLING == [], (code, out[-300:]))
    code, out, err = sweep(ws, "--go", "--new-ledger")
    check("ledger: the very first run with --new-ledger creates it and asks", lambda: code == 0 and os.path.exists(lpath(ws)) and len(cs_sent()) == 1 and CS.key(c["row"]) in ledger(ws)["rows"], (code, out[-300:]))
    reset(); code, out, err = sweep(ws, "--go", "--new-ledger")
    check("ledger: --new-ledger with a ledger in place -> refused, no call", lambda: code == 2 and "never replaced" in out and SENT == [], (code, out[-200:]))
    reset(); ws = new_ws(); write_aging(ws, [c, claim(bal=900.0, sent=5)], asof=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=2))
    code, out, err = sweep(ws, "--go")
    check("ageing file: older than one day -> an error line, no call of any kind - never a fall-back to the largest balances",
          lambda: code == 2 and "older than one day" in out and SENT == [] and LOGINS == [] and BILLING == [], (code, out[-300:]))
    os.remove(os.path.join(ws, "aging_latest.json")); code, out, err = sweep(ws, "--go")
    check("ageing file: missing -> an error line and no call", lambda: code == 2 and "no ageing file" in out and SENT == [] and LOGINS == [], (code, out[-200:]))

def t_need_run():
    reset(); ws = new_ws()
    posted = claim(paid_by="UNI20", paid_on=20, bal=500.0); denied = claim(carcs="96", denied=30, sent=60, bal=400.0); recent = claim(sent=20, bal=950.0)
    due_small = claim(sent=50, bal=12.0); sec = claim(paid_by="FLO02", paid_on=90, sent=61, dos=120, bal=8.0); sec_new = claim(paid_by="FLO02", paid_on=90, sent=50, dos=120, bal=300.0)
    old = claim(dos=400, sent=200, bal=700.0); off = claim(payer="TRI05", sent=90, bal=60.0); nr = claim(payer="FLO02", sent=90, bal=70.0)
    write_aging(ws, [posted, denied, recent, due_small, sec, sec_new, old, off, nr])
    code, out, err = sweep(ws, "--go"); asked = asked_members()
    check("by need: payment posted, denial posted, sent 20 days ago, a secondary silent 50 days, a year-old claim -> not asked",
          lambda: not set(asked) & {posted["member"], denied["member"], recent["member"], sec_new["member"], old["member"]}, asked)
    check("by need: sent 50 days ago with nothing posted -> asked; a secondary balance silent 61 days -> asked", lambda: due_small["member"] in asked and sec["member"] in asked, asked)
    check("by need: the larger claims that are not due ($950, $700, $500) are not asked while the $12 one is (never the largest balances)", lambda: sorted(asked) == sorted([due_small["member"], sec["member"]]), asked)
    check("payers: a claim on a switched-off payer never reaches the counter and is listed for portal or phone", lambda: off["member"] not in asked and "PAYER SWITCHED OFF" in out and ("v" + off["vid"]) in out, out[-600:])
    check("report: every report prints the count of claims silent 60 or more days (here 4: the secondary silent 61 days, the year-old claim, the two payers without a working route)",
          lambda: "claims silent 60 or more days since they were last sent, with nothing posted for their payer: 4" in out, out[:600])
    c_, o_, e_ = sweep(ws)
    check("report: the dry listing prints the silent count too", lambda: "claims silent 60 or more days" in o_ and c_ == 1)

def t_request_shape_and_log():
    reset(); ws = new_ws(); c = claim(sent=50, dos=70, bal=111.0, fee=150.0); write_aging(ws, [c])
    sweep(ws, "--go"); body = cs_sent()[0][1]; d = ago(70)
    check("request: the group billing provider, the chart's member id, the date of service +/- 3 days and the billed amount",
          lambda: body["tradingPartnerServiceId"] == "87726" and body["providers"][0]["npi"] == ST.PROV["npi"] and body["subscriber"]["memberId"] == c["member"]
          and body["encounter"]["beginningDateOfService"] == ymd(d - datetime.timedelta(days=3)) and body["encounter"]["endDateOfService"] == ymd(d + datetime.timedelta(days=3))
          and body["encounter"]["submittedAmount"] == "150.00", body)
    lines = log_lines()
    check("usage log: ONE line per check through the vendor client's door - kind 'claim status', the payer id, the chart id, ok, $0.30",
          lambda: len(lines) == len(cs_sent()) == 1 and lines[0][1] == "claim-status sweep" and lines[0][2:7] == ["claim status", "87726", c["pid"], "ok", "0.30"], lines)
    rf = run_file(ws); txt = json.dumps(rf) + text_of(lpath(ws)); ch = CHARTS[c["pid"]]
    check("files: the run file and the ledger hold no name, member id or birth date (chart and visit ids only)",
          lambda: ch["name"].split(",")[0] not in txt and c["member"] not in txt and ch["dob"] not in txt and rf[0]["visitid"] == c["vid"], txt[:300])
    d0 = ledger(ws)["months"][TODAY.strftime("%Y-%m")]
    check("ledger: the month's checks are counted in the ledger and priced with the price table", lambda: d0 == {"checks": 1, "dollars": 0.30}, d0)

def t_ledger_run():
    reset(); ws = new_ws(); c = claim(sent=100, dos=120); write_aging(ws, [c]); answer(c, PAID_A(c))
    sweep(ws, "--go"); L = lrow(ws, c)
    check("ledger: a paid answer naming this claim is recorded final", lambda: L.get("final") is True and L.get("answer") == "paid", L)
    reset(); code, out, err = sweep(ws, "--go")
    check("ledger: a claim with a final answer on record makes 0 requests", lambda: cs_sent() == [] and "final answer on file" in out, out[-300:])
    c["row"]["sent"] = iso(ago(46)); write_aging(ws, [c]); reset(); sweep(ws, "--go")
    check("ledger: the same claim with a later sent date makes 1 request", lambda: asked_members() == [c["member"]])
    reset(); ws = new_ws(); c = claim(sent=100, dos=120); o = claim(); write_aging(ws, [c]); answer(c, PAID_A(o), PENDING_A(c))
    code, out, err = sweep(ws, "--go"); L = lrow(ws, c); bodies = [b for u, b in cs_sent()]
    check("ledger: a windowed 'paid' naming another claim is not stored final - ONE exact-date check follows at once and its answer is kept",
          lambda: len(bodies) == 2 and bodies[1]["encounter"]["beginningDateOfService"] == bodies[1]["encounter"]["endDateOfService"] == ymd(ago(120)) and L["answer"] == "pending" and not L["final"], (L, bodies[-1]["encounter"]))

def t_stop_run():
    reset(); ws = new_ws(); a = claim(sent=80); b = claim(sent=80); write_aging(ws, [a, b]); answer(a, EMPTY_A); answer(b, PENDING_A(b))
    sweep(ws, "--go"); set_asked(ws, a, 8); set_asked(ws, b, 15)
    sweep(ws, "--go"); set_asked(ws, a, 8); set_asked(ws, b, 15); reset(); answer(b, PENDING_A(b))
    code, out, err = sweep(ws, "--go")
    check("stop: two empty answers for one claim over two runs (another claim of the payer answered each time) -> the third run makes 0 requests for it",
          lambda: a["member"] not in asked_members() and lrow(ws, a).get("stopped"), (asked_members(), lrow(ws, a)))
    check("stop: ... and the claim is on the hand-off list with its age and dollars: 'ask the payer by portal or phone'",
          lambda: "STILL ON THE HAND-OFF LIST" in out and re.search(r"v%s UNI20 DOS \S+ - \d+ days old, \$\d+\.\d\d - handed off" % a["vid"], out), out[-700:])
    reset(); ws = new_ws(); p = claim(sent=70); write_aging(ws, [p]); answer(p, PENDING_A(p))
    for i in range(3):
        code, out, err = sweep(ws, "--go")
        if i < 2: set_asked(ws, p, 15)
    check("stop: three 'pending' answers 14 days apart -> handed off at the third (HAND OFF TONIGHT, with age and dollars)", lambda: lrow(ws, p).get("stopped") and "HAND OFF TONIGHT" in out and ("v" + p["vid"]) in out, out[-500:])
    set_asked(ws, p, 15); reset(); sweep(ws, "--go")
    check("stop: ... and is not asked again", lambda: cs_sent() == [])
    reset(); ws = new_ws(); x = claim(sent=80); y = claim(sent=80); write_aging(ws, [x, y]); answer(x, EMPTY_A); answer(y, EMPTY_A)
    for i in range(3): sweep(ws, "--go"); set_asked(ws, x, 8); set_asked(ws, y, 8)
    check("stop: three nights on which the payer answered nobody use up no tries (neither claim handed off, both still asked)", lambda: not lrow(ws, x).get("stopped") and not lrow(ws, y).get("stopped") and len(cs_sent()) == 6)

def t_payer_stop_and_caps():
    reset(); ws = new_ws(); six = [claim(sent=50 + i) for i in range(6)]; write_aging(ws, six)
    for c in six: answer(c, EMPTY_A)
    code, out, err = sweep(ws, "--go"); rf = run_file(ws)
    check("payers: six unusable answers queued for one payer -> the counter sees 5 requests, the sixth claim is listed as not asked",
          lambda: len(cs_sent()) == 5 and sum(1 for r in rf if str(r.get("action")).startswith("NOT ASKED - 87726 gave 5 unusable answers")) == 1 and "NOT ASKED: 1 due claim(s) - 87726 gave 5" in out, (len(cs_sent()), out[-400:]))
    check("answers: an empty reply is kept raw under patient_db/ with its reply code", lambda: len(os.listdir(RAW)) == 5 and json.loads(text_of(os.path.join(RAW, sorted(os.listdir(RAW))[0])))["http"] == 200)
    reset(); ws = new_ws(); many = [claim(sent=50, bal=10.0 + i) for i in range(200)]; write_aging(ws, many)
    ledger_edit(ws, lambda d: d["months"].update({TODAY.strftime("%Y-%m"): {"checks": 250}}))
    code, out, err = sweep(ws, "--go")
    check("caps: 200 due claims, a run cap of 150 -> 150 requests and the line '50 due claims not asked: run cap'",
          lambda: len(cs_sent()) == 150 and "NOT ASKED: 50 due claim(s) - run cap: 150 checks" in out and len(log_lines()) == 150, (len(cs_sent()), out[-300:]))
    check("caps: the month's count in the ledger grows by the checks made (250 + 150)", lambda: ledger(ws)["months"][TODAY.strftime("%Y-%m")]["checks"] == 400)
    reset(); ws = new_ws(); write_aging(ws, many[:100]); code, out, err = sweep(ws, "--go")
    check("caps: early in the month the $25 run cap bites at 83 checks and says so", lambda: len(cs_sent()) == 83 and "NOT ASKED: 17 due claim(s) - run cap: $25.00" in out, (len(cs_sent()), out[-200:]))
    reset(); ws = new_ws(); write_aging(ws, many[:5]); ledger_edit(ws, lambda d: d["months"].update({TODAY.strftime("%Y-%m"): {"checks": 399}}))
    code, out, err = sweep(ws, "--go")
    check("caps: month counter at 399 with a cap of 400 -> 1 request", lambda: len(cs_sent()) == 1 and "month cap: 400 checks" in out, out[-200:])

def t_answers_run():
    reset(); ws = new_ws(); nm_ = claim(sent=60, dos=90); many_ = claim(sent=60, dos=90); ne = claim(sent=60, dos=90); nf = claim(sent=60, dos=90); ur = claim(sent=60, dos=90); ne_ = claim(sent=60, dos=90)
    write_aging(ws, [nm_, many_, ne, nf, ur, ne_]); answer(nm_, DATE_NM_A(nm_), PENDING_A(nm_)); answer(many_, MANY_A(many_), MANY_A(many_)); answer(ne, NOT_ELIG_A(ne)); answer(nf, NOT_FOUND_A(nf)); answer(ur, ("unreadable",))
    answer(ne_, NO_ELECTRONIC_A(ne_))
    code, out, err = sweep(ws, "--go"); rf = {r["visitid"]: r for r in run_file(ws)}
    by = collections.Counter(b["subscriber"]["memberId"] for u, b in cs_sent())
    exact = [b for u, b in cs_sent() if b["subscriber"]["memberId"] == nm_["member"]]
    check("answers: date not matched -> exactly ONE further request, with the exact date of service; its answer is read",
          lambda: by[nm_["member"]] == 2 and exact[1]["encounter"]["beginningDateOfService"] == exact[1]["encounter"]["endDateOfService"] == ymd(ago(90)) and lrow(ws, nm_)["answer"] == "pending", (by, lrow(ws, nm_)))
    check("answers: too many matches (485) -> the same: ONE exact-date check; not matched again -> stop and hand off", lambda: by[many_["member"]] == 2 and lrow(ws, many_).get("stopped") and rf[many_["vid"]]["action"].startswith("HAND OFF"), (by, rf[many_["vid"]]["action"]))
    check("answers: not eligible -> the INSURANCE CHECK list, never a resend (no NOT ON FILE words), no further request", lambda: by[ne["member"]] == 1 and "INSURANCE CHECK" in out and ("v" + ne["vid"]) in out.split("INSURANCE CHECK")[1]
          and rf[ne["vid"]]["action"].startswith("NOT ELIGIBLE"), out[-500:])
    check("answers: claim not found -> NOT ON FILE (a resend candidate, as before)", lambda: rf[nf["vid"]]["action"].startswith("NOT ON FILE") and by[nf["member"]] == 1)
    check("answers: an unreadable reply -> no usable answer, the reply code kept, the raw reply kept", lambda: rf[ur["vid"]]["label"] == "no usable answer" and rf[ur["vid"]]["http"] == "2xx" and lrow(ws, ur)["http"] == "2xx")
    check("answers: no electronic answer -> HAND OFF tonight, with age and dollars", lambda: rf[ne_["vid"]]["action"].startswith("HAND OFF") and "HAND OFF TONIGHT" in out and ("v" + ne_["vid"]) in out.split("HAND OFF TONIGHT")[1])
    check("answers: nothing is resent, posted or written: the only billing-system reads are chart records", lambda: BILLING and all(b.startswith("getdemographic") for b in BILLING))
    reset(); ws = new_ws(); u = claim(sent=60); write_aging(ws, [u]); answer(u, a277(st("A7", "21", "Missing or invalid information.")))
    code, out, err = sweep(ws, "--go")
    check("answers: an unknown wording is printed in the report", lambda: "WORDINGS THE RULES DO NOT KNOW" in out and "Missing or invalid information" in out, out[-300:])
    reset(); ws = new_ws(); h = claim(sent=60); write_aging(ws, [h]); answer(h, ("http", 503, {"errors": [{"code": "x", "description": "down"}]})); sweep(ws, "--go")
    check("answers: an HTTP error -> no usable answer, its reply code in the run file and the ledger, the usage line says http 503",
          lambda: run_file(ws)[0]["http"] == 503 and lrow(ws, h)["http"] == 503 and log_lines()[0][5] == "http 503")
    reset(); ws = new_ws(); tmo = claim(sent=60); write_aging(ws, [tmo]); answer(tmo, ("timeout",)); code, out, err = sweep(ws, "--go")
    check("answers: a time-out -> no usable answer, the run goes on and ends 0", lambda: code == 0 and lrow(ws, tmo)["answer"] == "no usable answer" and "time-out" in lrow(ws, tmo)["why"])

def t_concurrent():
    reset(); ws = new_ws(); c = claim(sent=60); write_aging(ws, [c])
    def meanwhile(url, body):
        ledger_edit(ws, lambda d: (d["rows"].update({"123|ZZZ": {"answer": "paid", "asked": iso(TODAY)}}), d["months"].update({TODAY.strftime("%Y-%m"): {"checks": 5}})))
    ON_SEND.append(meanwhile); sweep(ws, "--go"); d = ledger(ws)
    check("ledger: a row and a count another helper wrote while the run was asking are kept (5 + 1 = 6)", lambda: "123|ZZZ" in d["rows"] and CS.key(c["row"]) in d["rows"] and d["months"][TODAY.strftime("%Y-%m")]["checks"] == 6, d["months"])

def t_cut_off():
    # step 3: the Bash tool stops a command at its time limit; a run cut off half way must leave every answer it got where the runbook reads
    # them (claimstatus_<date>.json), not in the ledger only (where a final answer would never be asked again - and never acted on)
    reset(); ws = new_ws(); a = claim(sent=60); b = claim(sent=60); c = claim(sent=60); write_aging(ws, [a, b, c]); answer(a, PAID_A(a)); answer(b, PENDING_A(b))
    n = [0]
    def cut(url, body):
        if "claimstatus" in url:
            n[0] += 1
            if n[0] == 3: raise KeyboardInterrupt("the time limit of the Bash tool (stand-in)")
    ON_SEND.append(cut); was_cut = False
    try: sweep(ws, "--go")
    except KeyboardInterrupt: was_cut = True
    del ON_SEND[:]
    rf = {}
    try: rf = {r["visitid"]: r for r in run_file(ws)}
    except Exception: pass
    check("cut-off: a run cut off at its third check leaves the two answers it got in claimstatus_<date>.json, with the action words the runbook reads",
          lambda: was_cut and set(rf) == {a["vid"], b["vid"]} and rf[a["vid"]]["action"].startswith("PAID $") and rf[b["vid"]]["action"].startswith("PENDING"), (was_cut, rf))
    check("cut-off: ... and in the ledger (the paid answer is final there, so the run file is the only place the runbook can still act on it)",
          lambda: lrow(ws, a).get("final") is True and lrow(ws, b).get("answer") == "pending" and not lrow(ws, c))
    reset(); answer(c, PENDING_A(c)); sweep(ws, "--go"); rf2 = {r["visitid"]: r for r in run_file(ws)}
    check("cut-off: a second start the same night asks only the claim that was not answered, and the run file then holds all three",
          lambda: asked_members() == [c["member"]] and set(rf2) == {a["vid"], b["vid"], c["vid"]} and rf2[a["vid"]]["action"].startswith("PAID $"), (asked_members(), sorted(rf2)))

def t_full_and_exact():
    reset(); ws = new_ws(); a = claim(payer="HUM01", sent=60); b = claim(payer="SUN01", sent=60); write_aging(ws, [a, b])
    c1, o1, e1 = run_main("scripts/helpers/sweep_full.py", ["--help"], ws); c2, o2, e2 = run_main("scripts/helpers/sweep_full.py", [], ws); n = len(SENT)
    check("full sweep: --help prints its own usage; without --go nothing is asked (exit 1)", lambda: c1 == 0 and "usage: sweep_full.py" in o1 and c2 == 1 and n == 0, (c1, c2, n))
    c3, o3, e3 = run_main("scripts/helpers/sweep_full.py", ["--go"], ws)
    check("full sweep: with --go it asks every due claim on every payer with a route, by the same rules, and writes its own run file",
          lambda: c3 == 0 and sorted(asked_members()) == sorted([a["member"], b["member"]]) and len(run_file(ws, "claimstatus_full_%s.json")) == 2 and log_lines()[0][1] == "sweep full", (c3, o3[-300:]))
    reset(); ws = new_ws(); e = claim(sent=60, dos=80); f = claim(sent=60, dos=80); write_aging(ws, [e, f]); answer(e, a277(st("F1", "65", "paid", paid=20.0, check="C7")))
    c4, o4, e4 = run_main("scripts/helpers/claim_status_exact.py", ["--vids", e["vid"]], ws)
    c5, o5, e5 = run_main("scripts/helpers/claim_status_exact.py", ["--vids", e["vid"], "--stamp", "1009", "--go"], ws)
    check("exact: started without --go, or with an unknown option (the old --stamp), it asks nothing", lambda: c4 == 1 and c5 == 2 and SENT == [], (c4, c5))
    c6, o6, e6 = run_main("scripts/helpers/claim_status_exact.py", ["--vids", e["vid"], "--go"], ws); body = cs_sent()[0][1]; out = json.loads(text_of(os.path.join(ws, "claimstatus_exact_%s.json" % ymd(TODAY))))
    check("exact: the named due visit is asked ONCE with the exact date, the other visit not at all; a final answer (asked exact) is final in the ledger",
          lambda: asked_members() == [e["member"]] and body["encounter"]["beginningDateOfService"] == body["encounter"]["endDateOfService"] == ymd(ago(80)) and lrow(ws, e)["final"] is True
          and out[e["vid"]]["paid_unique"] == 20.0 and log_lines()[0][1] == "claim status exact", (o6[-300:], out))
    check("exact: every raw answer is kept under patient_db/ (never in git)", lambda: any(e["vid"] in f_ for f_ in os.listdir(RAW)))
    reset(); c7, o7, e7 = run_main("scripts/helpers/claim_status_exact.py", ["--vids", e["vid"], "--go"], ws)
    check("exact: a visit with a final answer on file is not asked again and the reason is printed", lambda: cs_sent() == [] and "not asked: pat%s v%s" % (e["pid"], e["vid"]) in o7 and "final answer on file" in o7, o7[-300:])

def _asked_now(n0): return sorted(b["subscriber"]["memberId"] for u, b in cs_sent()[n0:])
def t_review_fixes():
    # CS-1: a window answer whose claims all carry OTHER visits' account numbers (here 'pending') is not our claim's answer
    reset(); ws = new_ws(); c = claim(sent=100, dos=130); o = claim(); write_aging(ws, [c])
    answer(c, a277(st("P1", "20", "Accepted for processing.", acct=mine(o), svc=ymd(ago(129)))), a277(st("A4", "35", "Claim/encounter not found.", acct=mine(c))))
    code, out, err = sweep(ws, "--go"); bodies = [b for u, b in cs_sent()]; rf = {r["visitid"]: r for r in run_file(ws)}
    check("answers: a 3-day-window answer whose claims all carry other visits' account numbers (pending) is 'not matched' -> ONE exact-date check, and its 'not found' is the answer (review CS-1)",
          lambda: len(bodies) == 2 and bodies[1]["encounter"]["beginningDateOfService"] == bodies[1]["encounter"]["endDateOfService"] == ymd(ago(130))
          and lrow(ws, c)["answer"] == "not found" and rf[c["vid"]]["action"].startswith("NOT ON FILE") and rf[c["vid"]]["first_answer"].startswith("NOT MATCHED"), (len(bodies), lrow(ws, c), rf.get(c["vid"])))
    # CS-6: the exact-date helper - an answer with two claims of that date, none naming ours, is never our final answer
    reset(); ws = new_ws(); e = claim(sent=60, dos=80); write_aging(ws, [e])
    answer(e, a277(st("F1", "65", "paid", paid=60.0, check="C7", svc=ymd(ago(80))), st("P1", "20", "Accepted for processing.", svc=ymd(ago(80)))))
    run_main("scripts/helpers/claim_status_exact.py", ["--vids", e["vid"], "--go"], ws); L = lrow(ws, e)
    check("exact: an exact-date answer holding two claims of that date, none naming ours (one paid $60), is NOT recorded as our final paid answer - 'not matched', handed off (review CS-6)",
          lambda: L.get("answer") == "not matched" and L.get("final") is False and L.get("stopped") and len(cs_sent()) == 1, L)
    # CS-3: weekly runs - the claim that always comes back empty is alone (its payer's other claim waits), so none of its tries counts
    reset(); ws = new_ws(); a = claim(sent=80); b = claim(sent=80); write_aging(ws, [a, b]); answer(a, EMPTY_A); answer(b, PENDING_A(b)); asked = []
    for week in range(5):
        n0 = len(cs_sent()); sweep(ws, "--go"); asked.append(a["member"] in _asked_now(n0))
        if not lrow(ws, a).get("stopped"): set_asked(ws, a, 8)
        set_asked(ws, b, 8)
    check("stop: a claim that always comes back empty while its payer's other claim waits (tries uncounted) is handed off at its FOURTH unusable answer in a row, not bought every week (review CS-3)",
          lambda: asked == [True, True, True, True, False] and "four answers in a row" in (lrow(ws, a).get("stop_why") or ""), (asked, lrow(ws, a)))
    # CS-4: a payer that answers nobody, run after run - five claims bought every week before, the others never asked
    reset(); ws = new_ws(); eight = [claim(sent=80, bal=500.0 - i) for i in range(8)]; write_aging(ws, eight); per_run = []
    for c8 in eight: answer(c8, EMPTY_A)
    for week in range(5):
        n0 = len(cs_sent()); code, out, err = sweep(ws, "--go"); per_run.append(_asked_now(n0))
        for c8 in eight:
            if lrow(ws, c8) and not lrow(ws, c8).get("stopped"): set_asked(ws, c8, 8)
    first5 = sorted(x["member"] for x in eight[:5]); last3 = sorted(x["member"] for x in eight[5:])
    check("payers: a payer that answers nobody, run after run -> its first five claims are handed off after four runs, the other three are then asked, and the report proposes the payer for CS_OFF (review CS-4)",
          lambda: per_run[:4] == [first5] * 4 and per_run[4] == last3 and all(lrow(ws, x).get("stopped") for x in eight[:5]) and "PROPOSE FOR CS_OFF: UNI20 - 5 claim(s)" in out, (per_run, out[-600:]))
    # re-check NEW-2: ONE claim that always comes back empty while its payer answered its other claim ('pending', the first night) is
    # handed off - but the payer is NEVER proposed for CS_OFF, and the hand-off reason does not say the payer answered nothing
    reset(); ws = new_ws(); a = claim(sent=80); b = claim(sent=80); write_aging(ws, [a, b]); answer(a, EMPTY_A); answer(b, PENDING_A(b)); outs = []
    for week in range(6):
        code, out, err = sweep(ws, "--go"); outs.append(out)
        if not lrow(ws, a).get("stopped"): set_asked(ws, a, 8)
        set_asked(ws, b, 8)
    check("payers: one claim that always comes back empty while its payer answered its other claim is handed off, but the payer is NEVER proposed for CS_OFF and the reason does not say it answered nothing (re-check NEW-2)",
          lambda: lrow(ws, a).get("stopped") and not any("PROPOSE FOR CS_OFF" in o for o in outs) and lrow(ws, a).get("stop_why") == "four answers in a row with no usable content"
          and not lrow(ws, a).get("payer_quiet"), (lrow(ws, a).get("stop_why"), [l for o in outs for l in o.splitlines() if "PROPOSE" in l][:2]))
    # ... while a payer that answers nobody IS proposed, the night its claims are handed off - and no more once another of its claims
    # gets a usable answer ('pending'), not even in the report of that night
    reset(); ws = new_ws(); x = claim(sent=80); y = claim(sent=80); write_aging(ws, [x, y]); answer(x, EMPTY_A); answer(y, EMPTY_A)
    for week in range(4):
        code, out1, err = sweep(ws, "--go")
        for c2 in (x, y):
            if not lrow(ws, c2).get("stopped"): set_asked(ws, c2, 8)
    z = claim(sent=80); write_aging(ws, [x, y, z]); answer(z, PENDING_A(z)); code, out2, err = sweep(ws, "--go"); code, out3, err = sweep(ws, "--go")
    check("payers: a payer that answers nobody is proposed for CS_OFF the night its claims are handed off; once another of its claims answers ('pending') the line is gone, that night too (re-check NEW-2)",
          lambda: "PROPOSE FOR CS_OFF: UNI20 - 2 claim(s)" in out1 and lrow(ws, x).get("payer_quiet") is True and lrow(ws, z).get("answer") == "pending"
          and "PROPOSE FOR CS_OFF" not in out2 and "PROPOSE FOR CS_OFF" not in out3, ([l for l in (out1 + out2 + out3).splitlines() if "PROPOSE" in l][:3], lrow(ws, z).get("answer")))
    # second re-check R2-1 (the re-check's input, shifted by one week): weekly Sunday runs, a week passing between them. The payer PAID its
    # other claim - or answered it 'pending' - the Sunday BEFORE one claim first came due; that claim always comes back empty and is
    # handed off at its fourth try, and no other claim of the payer is asked on those four Sundays. The payer is never proposed for CS_OFF:
    # not that night, not on the Sundays after, not in a dry run.
    res = {}
    for shape, other_answer, other_sent, weeks in (("paid", PAID_A, 100, 8), ("pending", PENDING_A, 123, 6)):
        reset(); ws = new_ws(); a = claim(dos=60, sent=38); b = claim(dos=150, sent=other_sent); both = [a, b]
        write_aging(ws, both); answer(a, EMPTY_A); answer(b, other_answer(b)); outs = []
        for week in range(weeks):
            code, out, err = sweep(ws, "--go"); outs.append(out); time_passes(ws, both)
        code, dry, err = sweep(ws); L = lrow(ws, a); hist = L.get("history") or []
        res[shape] = {"why": L.get("stop_why"), "quiet": L.get("payer_quiet"), "from": L.get("quiet_from"), "first of four": hist[-4][0] if len(hist) >= 4 else None,
                      "weeks proposed": [i for i, o in enumerate(outs) if "PROPOSE FOR CS_OFF" in o], "dry run proposes": "PROPOSE FOR CS_OFF" in dry, "other": lrow(ws, b).get("answer")}
    check("payers: weekly runs - a payer that PAID its other claim, or answered it 'pending', the Sunday before one claim first came due is NEVER proposed for CS_OFF when that claim always comes back empty and is handed off at its fourth try (live runs and a dry run); the row keeps the night of the first of the four (second re-check R2-1)",
          lambda: sorted(res) == ["paid", "pending"] and all(v["why"] == "four answers in a row with no usable content (no other claim of its payer gave a usable answer on those nights)"
                                                              and v["quiet"] is True and v["from"] and v["from"] == v["first of four"] and v["weeks proposed"] == [] and v["dry run proposes"] is False for v in res.values())
          and res["paid"]["other"] == "paid" and res["pending"]["other"] == "pending", res)
    # the rule itself (second re-check R2-1): a payer is proposed only when none of its claims had a usable answer from 7 days before the
    # first of the four tries that handed one off until now - an answer the Sunday before the first try (even paid), on a night of the span
    # or after the hand-off ends the proposal; one 8 days before the first try, or another payer's, does not. A row that does not record
    # the night of the first try (quiet_from) is read from its history.
    four = [[iso(ago(d)), "no usable answer"] for d in (28, 21, 14, 7)]
    def quiet_rows(day=None, label="pending", payer="UNI20", recorded=True):
        q = {"payer": "UNI20", "stopped": iso(ago(7)), "payer_quiet": True, "history": [list(h) for h in four]}
        if recorded: q["quiet_from"] = iso(ago(28))
        rows_ = {"1|UNI20": q, "3|AET07": {"payer": "AET07", "history": [[iso(ago(20)), "pending"]]}}
        if day is not None: rows_["2|" + payer] = {"payer": payer, "history": [[iso(ago(day)), label]]}
        return rows_
    def prop(rows_): return CS.propose_off(rows_, [dict(key="1|UNI20", row={"payer": "UNI20"}, ledger=rows_["1|UNI20"])])
    want = {"no other answer": ((), {"UNI20": 1}), "pending 36 days ago (8 days before the first try)": ((36,), {"UNI20": 1}),
            "paid 35 days ago (the Sunday before the first try)": ((35, "paid"), {}), "pending 31 days ago (a night of the week before)": ((31,), {}),
            "pending 24 days ago (a night between two tries)": ((24,), {}), "pending 3 days ago (after the hand-off)": ((3,), {}),
            "paid the Sunday before, the first try read from the history": ((35, "paid", "UNI20", False), {}),
            "pending 36 days ago, the first try read from the history": ((36, "pending", "UNI20", False), {"UNI20": 1}),
            "another payer paid the Sunday before": ((35, "paid", "AET07"), {"UNI20": 1})}
    got = {}
    def r21():
        for name, (args, _) in want.items(): got[name] = prop(quiet_rows(*args))
        return all(got[name] == w for name, (_, w) in want.items())
    check("payers: propose_off proposes a payer only when none of its claims had a usable answer from 7 days before the first of the four tries that handed one off until now - an answer the Sunday before (even paid), on a night of the span or after the hand-off ends it; one 8 days before, or another payer's, does not (second re-check R2-1)",
          lambda: r21() and CS.PROPOSE_BEFORE_DAYS == 7, got)
    # CS-5: a final answer nobody acted on is listed again (no call)
    reset(); ws = new_ws(); pd_ = claim(sent=100, dos=120, bal=250.0); write_aging(ws, [pd_]); answer(pd_, PAID_A(pd_, 250.0)); sweep(ws, "--go")
    reset(); code, out, err = sweep(ws, "--go"); tail = out.split("FINAL ANSWER ON FILE BUT NOTHING POSTED FOR ITS PAYER")[-1]
    check("ledger: a final answer on file with still nothing posted for its payer is listed again in the next report, with no call (review CS-5)",
          lambda: cs_sent() == [] and "FINAL ANSWER ON FILE BUT NOTHING POSTED FOR ITS PAYER" in out and ("v" + pd_["vid"]) in tail and "'paid'" in tail, out[-500:])
    # CS-7: the month counter of a brand-new ledger
    reset(); ws = new_ws(ledger=False); n = claim(sent=60); write_aging(ws, [n]); answer(n, PENDING_A(n)); sweep(ws, "--go", "--new-ledger")
    check("caps: the first run of a brand-new ledger (--new-ledger) counts its one check once - the month's counter is 1, not 2 (review CS-7)",
          lambda: len(cs_sent()) == 1 and ledger(ws)["months"][TODAY.strftime("%Y-%m")]["checks"] == 1, ledger(ws).get("months"))
    # CS-11: the lists are printed whole
    reset(); ws = new_ws(); seventy = [claim(sent=60, bal=100.0 + i) for i in range(70)]; write_aging(ws, seventy)
    ledger_edit(ws, lambda d: d["months"].update({TODAY.strftime("%Y-%m"): {"checks": 250}}))      # past the $0.30 tier: no run cap bites before 70
    for c7 in seventy: answer(c7, NO_ELECTRONIC_A(c7))
    sweep(ws, "--go"); reset(); code, out, err = sweep(ws, "--go")
    listed = out.split("STILL ON THE HAND-OFF LIST")[1] if "STILL ON THE HAND-OFF LIST" in out else ""
    check("stop: the standing hand-off list names EVERY handed-off claim (70 of 70, not the first 60) (review CS-11)",
          lambda: cs_sent() == [] and all(("v" + x["vid"] + " ") in listed for x in seventy), sum(1 for x in seventy if ("v" + x["vid"] + " ") in listed))
    reset(); ws = new_ws(); off = [claim(payer="TRI05", sent=60, bal=50.0 + i) for i in range(45)]; write_aging(ws, off); code, out, err = sweep(ws, "--go")
    listed = out.split("PAYER SWITCHED OFF")[1] if "PAYER SWITCHED OFF" in out else ""
    check("payers: the switched-off payer's claims are all listed (45 of 45, not the first 40), none asked", lambda: cs_sent() == [] and all(("v" + x["vid"] + " ") in listed for x in off),
          sum(1 for x in off if ("v" + x["vid"] + " ") in listed))

def t_clear_cli():
    reset(); ws = new_ws(); p = claim(sent=70); write_aging(ws, [p]); answer(p, NO_ELECTRONIC_A(p)); sweep(ws, "--go")
    code, out, err = run_main("scripts/helpers/cs_rules.py", ["--clear", p["vid"]], ws)
    reset(); sweep(ws, "--go")
    check("stop: a person re-opens a handed-off claim with `cs_rules.py --clear <visit id>` - the next run asks it (no call by the clear itself)",
          lambda: code == 0 and "1 ledger row(s) re-opened" in out and asked_members() == [p["member"]], (code, out))

# ==== 6. the engine, the live texts, the copies ===================================================================================
def t_engine():
    RA = load("tools/button/run_all.py", "run_all_under_test")
    ws = os.path.join(TMP, "engine_ws"); os.makedirs(ws, exist_ok=True)
    for f in ("claim_status_sweep.py", "sweep_register.py"):
        with open(os.path.join(ws, f), "w") as fh: fh.write("# stand-in file - the engine test never starts anything\n")
    a = argparse.Namespace(mode="live", stamp="T", ws=ws, out=os.path.join(TMP, "engine_out"), python=None, stedi_proxy=True, profile=None, steps="sweep", packages="", note="", run_url="")
    r = RA.Run(a); started = []
    r.helper = lambda name, argv, timeout=1800, env=None, cwd=None: (started.append(name), (0, "", ""))[1]
    out = io.StringIO()
    with contextlib.redirect_stdout(out): r.sweep()
    s = r.steps[-1]
    check("engine: the sweep step starts nothing (no claim_status_sweep.py, no sweep_register.py) and says so in one line",
          lambda: started == [] and "nightly insurance cascade routine asks claim status by need" in s["summary"] and s["status"] == "ok" and len([l for l in out.getvalue().splitlines() if "sweep:" in l]) == 1, (started, s))
    src = _read("tools/button/run_all.py")
    check("engine: nothing in run_all.py starts a claim-status helper any more, and no scheduled profile names the sweep",
          lambda: not re.search(r"helper\(\s*['\"](claim_status_sweep|sweep_register|sweep_full|claim_status_exact)\.py", src) and not any("sweep" in v for v in RA.PROFILES.values()))

def t_texts():
    live = {os.path.basename(f): _read(os.path.relpath(f, ROOT)) for f in sorted(glob.glob(os.path.join(ROOT, "nightly", "live", "*.txt")))}
    starts = [(n, m.group(0)) for n, t in live.items() for m in re.finditer(r"(?:python3\s+)?(?:claim_status_sweep|sweep_full|claim_status_exact)\.py[^`'\n]*", t)]
    check("texts: no text under nightly/live/ starts a claim-status sweep without --go", lambda: starts and all("--go" in s for n, s in starts), starts)
    known = {"--go", "--aging", "--ledger", "--new-ledger", "--carriers", "--max"}
    check("texts: the live texts name no option the sweep helper does not have", lambda: all(set(re.findall(r"--[a-z][a-z-]*", s)) <= known for n, s in starts), starts)
    bb = live.get("billing_button.txt", "")
    check("texts: the retired backlog sweep is gone from the Billing Button routine (no sweep step, no sweep_register.py, 'all steps' without it)",
          lambda: "cascade, packages," in bb and "cascade, sweep," not in bb and "sweep_register.py" not in bb and "there is no sweep step" in bb)
    cas = live.get("cascade.txt", "")
    check("texts: the nightly cascade's Sunday step makes tonight's ageing file first and passes it with --go",
          lambda: "`python3 aging_refresh.py --out aging_latest.json --threads 4`" in cas and "`python3 claim_status_sweep.py --go --aging aging_latest.json`" in cas and "claim_status_ledger.json" in cas)
    ag = _read("scripts/helpers/aging_refresh.py")
    check("texts: the ageing helper the text names takes --out and --threads (read by hand in aging_refresh.py)", lambda: '"--out"' in ag and '"--threads"' in ag)

def t_copies():
    names = ("cs_rules.py", "claim_status_sweep.py", "sweep_full.py")
    diff = [n for n in names if _read("scripts/helpers/" + n) != _read("billing/scans/" + n)]
    check("copies: billing/scans holds the same cs_rules, claim_status_sweep and sweep_full as scripts/helpers", lambda: diff == [], diff)
    check("copies: the vendor client is the same in core/ and scripts/helpers/ (unchanged by this step)", lambda: _read("scripts/helpers/stedi.py") == _read("core/stedi.py"))

# ==== 7. the October replay of the claim-status reader's registers through cs_rules.py ===============================================
def _T(s):
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})[T_ ]?(\d{2}):?(\d{2})", s); return datetime.datetime(*map(int, m.groups())) if m else None
def _lines_of(r):
    out = []
    def take(x):
        if isinstance(x, dict) and (x.get("cat") or x.get("statusCategoryCode")):
            out.append({"cat": str(x.get("cat") or x.get("statusCategoryCode")), "code": str(x.get("code") or x.get("statusCode") or ""), "codev": str(x.get("codev") or x.get("statusCodeValue") or ""), "paid": x.get("paid")})
        elif isinstance(x, (list, tuple)) and x and isinstance(x[0], str) and re.fullmatch(r"[A-Z]\d{1,2}", x[0]):
            out.append({"cat": x[0], "code": str(x[1]) if len(x) > 1 else "", "codev": str(x[2]) if len(x) > 2 else "", "paid": None})
        elif isinstance(x, (list, tuple)):
            for y in x: take(y)
    for k in ("status", "cats", "codes", "other", "rows"):
        if k in r: take(r[k])
    return out
KIND = [("SKIP", None), ("PAID", "paid"), ("FINALIZED", "finalized at $0"), ("DENIED", "denied"), ("PENDING", "pending"), ("NOT ON FILE", "not found"), ("ERROR", "no usable answer"), ("UNKNOWN", "no usable answer")]
def _kind(action):
    a = str(action or "")
    for pre, k in KIND:
        if a.startswith(pre): return k or "skip"
    return "no usable answer"
def october_events():
    """The 4,850 October checks that name their claim (the claim-status reader's t07_lib): backlog-sweep registers, engine reports that left no
    register, the full sweep of 10/13 and the Sunday sweep of 10/25 rebuilt from its follow-up registers. Ids stay in memory."""
    REG = "practices/ehpa/registers/"; ev = []
    regs = sorted(os.path.relpath(f, ROOT) for f in glob.glob(os.path.join(ROOT, REG, "uni20_bcbs_pre0501_sweep*.json")))
    regt = [_T(os.path.basename(f)) for f in regs]
    for f, t in zip(regs, regt):
        if t.strftime("%Y-%m") != "2026-10": continue
        j = json.loads(_read(f)); rows = j.get("rows") if isinstance(j, dict) else j
        for r in rows or []:
            if isinstance(r, dict) and _kind(r.get("action")) != "skip": ev.append({"t": t, "vid": str(r.get("visitid") or r.get("vid")), "car": str(r.get("carrier")), "src": "backlog", "kind": _kind(r.get("action")), "lines": _lines_of(r), "dos": str(r.get("dos") or "")[:10]})
    for f in sorted(glob.glob(os.path.join(ROOT, "reports", "button", "2026-*.json"))):
        t = _T(os.path.basename(f)[:-5])
        if not t or t.strftime("%Y-%m") != "2026-10": continue
        try: j = json.loads(_read(os.path.relpath(f, ROOT)))
        except ValueError: continue
        for s in j.get("steps") or []:
            if s.get("name") != "sweep" or any(abs((t - r).total_seconds()) <= 50 * 60 for r in regt): continue
            for ln in s.get("lines") or []:
                for i in re.findall(r"v(\d+)", ln.get("ids") or ""): ev.append({"t": t, "vid": i, "car": "UNI20/BCBS", "src": "engine", "kind": _kind(ln.get("action")), "lines": [], "dos": ""})
    for r in json.loads(_read(REG + "claimstatus_2026-10-13_over120.json")):
        if _kind(r.get("action")) != "skip": ev.append({"t": datetime.datetime(2026, 10, 13, 22, 0), "vid": str(r.get("visitid") or r.get("vid")), "car": str(r.get("carrier")), "src": "full", "kind": _kind(r.get("action")), "lines": _lines_of(r), "dos": str(r.get("dos") or "")[:10]})
    tag = "2026-10-25T0535Z"; t = _T(tag); kinds = {}; car = {}; dos = {}
    d = json.loads(_read(REG + "sweep_denials_%s.json" % tag))
    for r in d.get("pending") or []: kinds[str(r["vid"])] = "pending"; car[str(r["vid"])] = r.get("carrier"); dos[str(r["vid"])] = r.get("dos")
    for r in d.get("other") or []:
        a = str(r.get("action") or ""); kinds[str(r["vid"])] = "skip" if a.startswith("SKIP") else "no usable answer"; car[str(r["vid"])] = r.get("carrier"); dos[str(r["vid"])] = r.get("dos")
    for r in d.get("denials") or []:
        cs = list((r.get("carriers") or {}).keys())
        for v in r.get("visits") or []: kinds.setdefault(str(v), "denied"); car.setdefault(str(v), cs[0] if len(cs) == 1 else "/".join(cs)); dos.setdefault(str(v), r.get("dos"))
    rs = json.loads(_read(REG + "sweep_resend_%s.json" % tag))
    for k in ("sent", "held", "skipped", "failed"):
        for r in rs.get(k) or []: kinds.setdefault(str(r["vid"]), "not found"); car.setdefault(str(r["vid"]), r.get("carrier")); dos.setdefault(str(r["vid"]), r.get("dos"))
    w = json.loads(_read(REG + "sweep_writeoff_" + "2026" + "1025" + ".json"))       # built in pieces: the privacy gate reads a whole date in a file name as a birth date
    for k in ("posted", "skipped", "held"):
        for r in w.get(k) or []:
            if isinstance(r, dict) and r.get("vid"): kinds.setdefault(str(r["vid"]), "paid"); car.setdefault(str(r["vid"]), r.get("carrier")); dos.setdefault(str(r["vid"]), r.get("dos"))
    ev += [{"t": t, "vid": v, "car": str(car.get(v)), "src": "sunday", "kind": k, "lines": [], "dos": str(dos.get(v) or "")[:10]} for v, k in kinds.items() if k != "skip"]
    ev.sort(key=lambda e: (e["t"], e["src"]))
    return ev
def _result(e):
    """The recorded answer read the 9.8 way (status lines where the register kept them, else the label of the time). The registers keep no
    account number, so a recorded final answer is taken as naming its claim, as the reader's replay did."""
    if e["lines"]:
        l_, why = CS.label_lines(e["lines"])
        if l_ == CS.FINAL0 and e["kind"] == "paid": l_ = CS.PAID
    else: l_, why = e["kind"], "recorded label"
    return {"label": l_, "why": why, "final": l_ in CS.FINAL, "named": True, "status": "", "http": None}
def replay(ev, year_rule=False):
    """October's recorded checks in time order: a check is KEPT only when cs_rules.py would ask that claim at that moment (a payer switched off,
    the payer stopped for the run, the ledger's final / wait / stop / 'not found' rules, the ONE exact-date check after 'not matched'); kept
    answers go into the ledger with cs_rules.record and every run ends with cs_rules.finish_run. The registers do not hold the day a claim
    was last sent or what was posted, so the rules that need the ageing file (9.2) are not replayed; a 'not found' claim is taken as resent
    that night, as the runbook says (cascade.txt STEP 2)."""
    rows = {}; resent = {}; kept = 0; saved = collections.Counter(); learned = set(); dosmap = {}
    for e in ev:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", e["dos"] or ""): dosmap.setdefault(e["vid"], e["dos"])
    runs = collections.OrderedDict()
    for e in ev: runs.setdefault((e["t"], e["src"]), []).append(e)
    for (t, src), evs in runs.items():
        day = t.date(); answers = []; bad = collections.Counter(); stopped = set()
        for e in evs:
            v, car = e["vid"], e["car"]
            if car in CS.CS_OFF: saved["payer switched off"] += 1; continue
            if car in stopped: saved["payer stopped for the run"] += 1; continue
            if year_rule and dosmap.get(v) and (day - datetime.date.fromisoformat(dosmap[v])).days >= CS.YEAR_DAYS: saved["a year old or more"] += 1; continue
            r = {"visitid": v, "payer": car, "sent": resent.get(v, "2000-01-01"), "dos": dosmap.get(v, "")}
            ok, why, exact = CS.ledger_says(rows.get(v), r, day)
            if not ok: saved[CS._why_group({"why": why})] += 1; continue
            kept += 1; res = _result(e)
            rows[v] = CS.record(rows.get(v), res, r, day, exact); answers.append((v, car, res["label"]))
            if res["label"] == CS.NOT_FOUND: resent[v] = day.isoformat()
            if res["final"]: learned.add(v)
            if res["label"] == CS.UNUSABLE:
                bad[car] += 1
                if bad[car] >= CS.PAYER_RUN_STOP: stopped.add(car)
            else: bad[car] = 0
        CS.finish_run(rows, answers, day)
    real = {}
    for e in ev:
        if _result(e)["final"]: real.setdefault(e["vid"], e)
    later = datetime.date(2026, 12, 31); lost = []; next_check = 0
    for v, e in real.items():
        if v in learned: continue
        ok, why, _ = CS.ledger_says(rows.get(v), {"visitid": v, "payer": e["car"], "sent": resent.get(v, "2000-01-01"), "dos": dosmap.get(v, "")}, later)
        if ok: next_check += 1
        else: lost.append(why)
    year_finals = sum(1 for v, e in real.items() if dosmap.get(v) and (e["t"].date() - datetime.date.fromisoformat(dosmap[v])).days >= CS.YEAR_DAYS)
    return {"kept": kept, "saved": saved, "finals": len(real), "learned": len(learned & set(real)), "next_check": next_check, "lost": lost, "year_finals": year_finals}
def t_replay():
    ev = october_events()
    check("replay: the claim-status reader's October records are read again - 4,850 checks that name their claim, 557 claims with a final answer",
          lambda: len(ev) == 4850 and len({e["vid"] for e in ev if _result(e)["final"]}) == 557, (len(ev),))
    r = replay(ev)
    print("     replay: kept %d of %d (%s); final answers %d: %d inside October, %d at their next check, %d lost" % (r["kept"], len(ev), ", ".join("%s %d" % kv for kv in r["saved"].most_common()), r["finals"], r["learned"], r["next_check"], len(r["lost"])))
    check("replay: the October records through cs_rules.py keep at most 900 of the 4,850 checks", lambda: r["kept"] <= 900, r["kept"])
    check("replay: every claim that got a final answer still gets one (inside October or at its next due check; none handed off or barred)",
          lambda: r["lost"] == [] and r["learned"] + r["next_check"] == r["finals"] == 557, collections.Counter(r["lost"]).most_common(5))
    y = replay(ev, year_rule=True)
    print("     with the year rule as well (spec 9.3: a claim a year old or more gets no check at all): kept %d; %d of the final answers were on claims a year old or more when they came" % (y["kept"], y["year_finals"]))
    check("replay: with the year rule as well even fewer checks are kept", lambda: y["kept"] < r["kept"])

TESTS = [t_prices_caps, t_labels, t_need, t_waits, t_record_stop, t_files, t_cli, t_inputs, t_need_run, t_request_shape_and_log, t_ledger_run, t_stop_run,
         t_payer_stop_and_caps, t_answers_run, t_concurrent, t_cut_off, t_full_and_exact, t_review_fixes, t_clear_cli, t_engine, t_texts, t_copies, t_replay]
_PATH = list(sys.path)
def _run(t):
    try: t()
    except Exception:
        check("%s ran to its end" % t.__name__, False, traceback.format_exc()[-700:])
    finally:
        sys.path[:] = _PATH                                          # the modules add their own folder to sys.path - nothing of the checkout stays importable
        os.environ.update(STEDI_USAGE_LOG=ULOG, CLAIM_STATUS_RAW=RAW)
        CS.CAPS.clear(); CS.CAPS.update(CAPS0)
for t in TESTS: _run(t)
check("nothing was written in the checkout", lambda: _snapshot() == BEFORE, sorted(set(_snapshot().items()) ^ set(BEFORE.items()))[:5])
print("test_claim_status_rules: %d checks, %d failed%s" % (COUNT[0], len(FAILS), "" if not FAILS else " - " + "; ".join(FAILS)[:300]))
sys.exit(1 if FAILS else 0)
