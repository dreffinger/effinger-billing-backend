#!/usr/bin/env python3
# PLAIN ENGLISH (offline self-test: the routines' texts against the code - look-ups part A, step 3, 11/10/2026)
# Decides: nothing. A scheduled routine reads its text in nightly/live/ within hours of a delivery and does what it says, so every
#   command, option, file and quoted word in it must be true of the code. This test reads the live texts, the look-up skill
#   (skills/billing-insurance-lookup-stedi/SKILL.md), the registry row for vendor eligibility (docs/captured_calls.md), the Billing Button
#   page texts and the engine's documentation, and the code they point at - AS TEXT. No helper is started or imported; only the two pure
#   tables (stedi_prices.py, cs_rules.py - no link to AdvancedMD or the vendor) and the privacy gate's text transform (phi_gate.py) are
#   loaded from their files. No network. It proves:
#     - every helper a live text starts is in the repository, where the workspace builders copy it from;
#     - every option a live text or the skill passes to a helper is read by that helper; every `python3 stedi.py <word>` and every
#       stedi.<function> a text names exists in the vendor client;
#     - no text starts a claim-status helper without --go, or with --new-ledger;
#     - the pre-claim check's result words, the Sunday step's action words and report lines (STOPPED, NOT ASKED, the hand-off lists), its run
#       file, ledger, caps, waits, stop rule and payers switched off are the code's;
#     - rule (f) buys no plain Medicare check by hand any more and no text says the plain check answers AAA 41; the error codes, the name
#       suffixes, the report line of a refused plain check and the prices the texts state are the code's;
#     - the usage log is where the texts say, the nightly routine never restores patient_db/ (so its log is the night's), the state bundle
#       carries it for the Billing Button;
#     - the Billing Button page, the desktop app and the engine's documentation no longer say the engine's sweep buys checks;
#     - (11/10/2026 review fixes) no text says the look-up is bought 'only when' the chart lacks a number; the provider-number refusals,
#       the aging_refresh.py timeout, the exact-date sentence, the new hand-off reason and report lines, the STEP 6 ledger copy, rule (f)
#       of the Button and the price table's limits are stated as the code has them;
#     - (11/10/2026 re-check fixes) the guard paragraph of the skill, the CS_OFF proposal and the fourth hand-off reason in STEP 2 and the
#       sweep, rule (f) after a refusal of our provider number, and the price table's coordination-of-benefits sentence say what the code does.
# Run: python3 tools/selftest/test_lookup_texts.py   (exit 1 on any failure; the last line says how many checks ran and how many failed)
import os, sys, re, json, glob, types, datetime
import importlib.abc, importlib.machinery
# THIS SELF-TEST NEVER REACHES ADVANCEDMD, THE VENDOR OR ANY OTHER HOST. Every network route is closed here, before anything else is
# loaded: scripts/helpers and core hold the REAL amd / resave / txh / void_tx / era_post / stedi / deceased_guard modules, and importing
# them would talk to the practice's billing system and the paid vendor. So: (1) the code is read as text; the two pure tables are run
# from their files (load below) and refused when they would load anything live; (2) any import that would come from the checkout and was
# not loaded that way is refused, as is the real `requests`; (3) the network is shut either way. No program is started.
import socket as _socket
def _no_network(*a, **k): raise RuntimeError("the self-test must not use the network")
_socket.socket.connect = _no_network; _socket.socket.connect_ex = _no_network; _socket.create_connection = _no_network
for _k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"): os.environ[_k] = "http://127.0.0.1:9"
os.environ.update(NO_PROXY="", no_proxy="")
for _k in ("CLAIM_STATUS_LEDGER", "STEDI_USAGE_LOG", "MEDICARE_STORE"): os.environ.pop(_k, None)      # the defaults the texts describe
sys.dont_write_bytecode = True
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LIVE = {"amd", "resave", "txh", "void_tx", "era_post", "deceased_guard", "stedi", "requests", "medicare_store", "stedi_usage",
        "precheck", "elig_amd", "add_ins", "ins_update", "freq1_visit", "move_to_ins", "claim_status_sweep"}
class _Refuse(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in LIVE: raise ImportError("refused: %s is a live-system module - nothing live is loaded here" % name)
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
    """Every file of the checkout this test reads - the texts and the code - is read here and nowhere else."""
    with open(os.path.join(ROOT, rel)) as fh: return fh.read()
def _exists(rel):
    return os.path.isfile(os.path.join(ROOT, rel))
def imports(src):
    out = set()
    for kind, rest in re.findall(r"^[ \t]*(import|from)[ \t]+([^\n#]+)", src, re.M):
        for n in (rest.split(",") if kind == "import" else [rest]):
            n = n.strip().split()[0].split(".")[0] if n.strip() else ""
            if n: out.add(n)
    return out
def load(rel, name):
    """Run ONE pure file of the checkout (a table with no link to the live systems) as module `name`; refused when it would load a live module."""
    src = _read(rel); live = sorted((imports(src) & LIVE) - {n for n in LIVE if getattr(sys.modules.get(n), "UNDER_TEST", False)})
    if live: raise RuntimeError("%s loads %s - not run here" % (rel, live))
    m = types.ModuleType(name); m.__file__ = os.path.join(ROOT, rel); m.UNDER_TEST = True
    exec(compile(src, m.__file__, "exec"), m.__dict__); return m

# ---- 0. the safety block holds ------------------------------------------------------------------------------------------------
check("safety: the real `requests`, a live helper and any module of the checkout are refused by the import blocker",
      lambda: _raises(lambda: _Refuse().find_spec("requests"), ImportError) and _raises(lambda: _Refuse().find_spec("stedi"), ImportError)
      and _raises(lambda: _Refuse().find_spec("test_board_ops", [os.path.join(ROOT, "tools", "selftest")]), ImportError))
check("safety: the network is shut in this process", lambda: _raises(lambda: _socket.create_connection(("127.0.0.1", 9)), RuntimeError))
check("safety: a file that loads a live module is not run here (the pre-claim check)", lambda: _raises(lambda: load("scripts/helpers/precheck.py", "x"), RuntimeError))
PR = load("scripts/helpers/stedi_prices.py", "stedi_prices"); sys.modules["stedi_prices"] = PR
CS = load("scripts/helpers/cs_rules.py", "cs_rules")
sys.path[:] = [p for p in sys.path if not os.path.abspath(p or ".").startswith(ROOT + os.sep)]      # cs_rules adds its folder - nothing of the checkout stays importable

# ---- the texts and the code, as text --------------------------------------------------------------------------------------------
LIVE_TXT = {os.path.basename(f): _read(os.path.relpath(f, ROOT)) for f in sorted(glob.glob(os.path.join(ROOT, "nightly", "live", "*.txt")))}
SKILL = _read("skills/billing-insurance-lookup-stedi/SKILL.md")
TEXTS = dict(LIVE_TXT); TEXTS["SKILL.md"] = SKILL
CAS, BB = LIVE_TXT.get("cascade.txt", ""), LIVE_TXT.get("billing_button.txt", "")
H = "scripts/helpers/"
SRC = {n: _read(H + n) for n in ("stedi.py", "precheck.py", "claim_status_sweep.py", "cs_rules.py", "stedi_usage.py", "stedi_prices.py")}
STEP = lambda text, head, nxt: (text.split(head, 1)[1].split(nxt, 1)[0] if head in text else "")
STEP1, STEP2, STEP4 = STEP(CAS, "STEP 1 - ", "\nSTEP 2 - "), STEP(CAS, "STEP 2 - ", "\nSTEP 2b - "), STEP(CAS, "STEP 4 - ", "\nSTEP 4b - ")
BB6 = STEP(BB, "6. CASCADE PRE-CHECK", "\n7. ")
def rule(text, letter):
    """The text of one lettered rule of a pre-check step: '(f) ...' up to '(g)'."""
    m = re.search(r"\(%s\) (.*?)(?= \(%s\) )" % (letter, chr(ord(letter) + 1)), text, re.S); return m.group(1) if m else ""

# where the workspace builders copy helpers from (tools/nightly_bootstrap.sh; tools/bootstrap/bootstrap_workspace.sh layout)
FOLDERS = ["scripts/helpers", "core", "eligibility", "credentialing", "boards", "nightly/helpers"] + sorted(os.path.relpath(d, ROOT) for d in glob.glob(os.path.join(ROOT, "billing", "*")) if os.path.isdir(d))
def where(name):
    """The repository file a text's `python3 <name>` runs, or None."""
    n = name
    for pre, to in (("/home/claude/effinger-billing-backend/", ""), ("/home/user/effinger-billing-backend/", "")):
        if n.startswith(pre): n = to + n[len(pre):]
    if n.startswith("/home/claude/unbilled/"): n = n[len("/home/claude/unbilled/"):]
    if "/" in n:
        if _exists(n): return n
        if n.startswith("tools/") and _exists("tools/bootstrap/" + os.path.basename(n)): return "tools/bootstrap/" + os.path.basename(n)   # the workspace tools/ = tools/bootstrap/*
        return None
    for f in FOLDERS:
        if _exists(f + "/" + n): return f + "/" + n
    return None
def commands():
    """Every `python3 <helper>.py <args>` inside a code span of a live text or the skill -> [(text, helper as written, args)]."""
    out = []
    for tn, t in TEXTS.items():
        for span in re.findall(r"`([^`]+)`", t):
            for part in re.split(r"&&|;|\|", span):
                m = re.search(r"python3 (?:-I )?(\S+\.py)\b(.*)", part.strip())
                if m and "<" not in m.group(1): out.append((tn, m.group(1), m.group(2)))     # '<helper>.py' is the text's placeholder, not a helper
    return out
CMDS = commands()
def opts(args): return re.findall(r"(?<![\w-])(--[a-z][a-z0-9-]*)", args)

# ==== 1. the commands of the texts exist ===========================================================================================
def t_commands():
    missing = sorted({(tn, h) for tn, h, a in CMDS if not where(h)})
    check("commands: the texts start at least the helpers of this change (pre-claim check, claim-status sweep, ageing file, usage reader, ledger clear)",
          lambda: {"precheck.py", "claim_status_sweep.py", "aging_refresh.py", "stedi_usage.py", "cs_rules.py", "stedi.py"} <= {os.path.basename(h) for tn, h, a in CMDS}, sorted({os.path.basename(h) for tn, h, a in CMDS}))
    check("commands: every helper a live text or the skill starts is in the repository, in a folder the workspace builders copy (or at the repository path it names)",
          lambda: missing == [], missing)
    known_exception = {("payreasons.py", "--list")}   # payreasons.py reads no --list word: without --live its default branch lists the rows read-only, which is what the text asks
    bad = []
    for tn, h, a in CMDS:
        p = where(h)
        if not p: continue
        src = _read(p)
        for o in opts(a):
            if (os.path.basename(h), o) in known_exception: continue
            if ('"%s"' % o) not in src and ("'%s'" % o) not in src: bad.append((tn, os.path.basename(h), o))
    check("commands: every option a live text or the skill passes to a helper is read by that helper (its argument reader holds the word)", lambda: bad == [], bad)
    words = {re.match(r"\s*(\w+)", a).group(1) for tn, h, a in CMDS if os.path.basename(h) == "stedi.py" and re.match(r"\s*(\w+)", a)}
    cli = set(re.findall(r'a\[0\] == "(\w+)"', SRC["stedi.py"]))
    check("commands: every `python3 stedi.py <word>` a text names is a command of the vendor client (medicare among them)", lambda: words and words <= cli and "medicare" in words, (words, cli))
    names = {n for t in TEXTS.values() for n in re.findall(r"(?<![\w.])stedi\.([a-z][a-z_]*)\b", t)} - {"py", "com"}
    defined = set(re.findall(r"^def (\w+)", SRC["stedi.py"], re.M))
    check("commands: every stedi.<function> a text names exists in the vendor client (no summarize_elig)", lambda: names and names <= defined and "summarize_elig" not in names, sorted(names - defined))
    cs_starts = [(tn, os.path.basename(h), a) for tn, h, a in CMDS if os.path.basename(h) in ("claim_status_sweep.py", "sweep_full.py", "claim_status_exact.py")]
    check("commands: no text starts a claim-status helper without --go, and none with --new-ledger (the ledger lives in the repository)",
          lambda: cs_starts and all("--go" in opts(a) and "--new-ledger" not in opts(a) for tn, h, a in cs_starts), cs_starts)

# ==== 2. the pre-claim check: STEP 1 and the Button's step 6 ======================================================================
def t_precheck():
    words = ["ADVANTAGE PLAN on DOS", "INACTIVE on DOS", "MBI MISMATCH", "DATE OF DEATH", "not found on Medicare", "OK straight Medicare"]
    lits = re.findall(r'"([^"\n]*)"', SRC["precheck.py"])
    check("pre-claim: every result word STEP 1 quotes is a word precheck.py writes ('ADVANTAGE PLAN on DOS', 'INACTIVE on DOS', 'MBI MISMATCH', 'DATE OF DEATH', 'not found on Medicare', 'OK straight Medicare')",
          lambda: all(w in STEP1 for w in words if w != "OK straight Medicare") and all(any(l.startswith(w) for l in lits) for w in words), [w for w in words if not any(l.startswith(w) for l in lits)])
    check("pre-claim: the file STEP 1 reads, precheck_<today>.json, is the file precheck.py writes (YYYYMMDD)",
          lambda: "precheck_<today>.json" in STEP1 and '"precheck_%s.json" % stamp' in SRC["precheck.py"] and 'stamp = today.strftime("%Y%m%d")' in SRC["precheck.py"])
    check("pre-claim: STEP 1 says Medicare is asked by ONE Medicare answer (a plain check with the chart's number, the look-up only when needed), as precheck.py does",
          lambda: "ONE Medicare answer" in STEP1 and "plain Medicare check" in STEP1 and "Medicare via MBI lookup" not in CAS and "stedi.medicare(" in SRC["precheck.py"])
    for name, text in (("cascade.txt STEP 1", STEP1), ("billing_button.txt step 6", BB6)):
        f = rule(text, "f")
        check("rule (f) of %s buys NO further Medicare check by hand (the plain check is inside precheck.py now) and names no `stedi.py elig CMS`" % name,
              lambda: "buy NO further Medicare check by hand" in f and "stedi.py elig CMS" not in text and "AAA 41" not in f and "not live yet" not in f, f[:300])
    down = set(re.search(r'MEDICARE_DOWN = \{([^}]*)\}', SRC["stedi.py"]).group(1).replace('"', "").replace(" ", "").split(","))
    nf = set(re.search(r'MEDICARE_NOT_FOUND = \{([^}]*)\}', SRC["stedi.py"]).group(1).replace('"', "").replace(" ", "").split(","))
    def codes_in(pattern, text):
        m = re.search(pattern, text); return set(re.findall(r"\d+", m.group(1))) if m else set()
    fc = codes_in(r"Codes ([\d, or]+) = Medicare or Stedi could not answer", STEP1)
    bc = codes_in(r"codes ([\d /]+) = Medicare or Stedi could not answer", BB6)
    check("rule (f): the 'could not answer' codes it names (42, 79, 80) are the client's MEDICARE_DOWN codes", lambda: fc == down == bc == {"42", "79", "80"}, (fc, bc, down))
    sk_nf = codes_in(r"the plain check answers ([\d /]+) \(", SKILL); sk_dn = codes_in(r"ERR ([\d /]+) on a Medicare call", SKILL)
    check("skill: the 'not found' codes of step 3 (72 / 73 / 75 / 76 / 58) and the 'cannot answer' codes (42 / 79 / 80) are the client's", lambda: sk_nf == nf and sk_dn == down, (sk_nf, nf, sk_dn, down))
    m = re.search(r"_SUFFIX = re\.compile\(.*?\(\?:([A-Z|]+)\)", SRC["stedi.py"]); suf = set(m.group(1).split("|")) if m else set()
    check("texts: the name suffixes the texts list (JR / SR / II / III / IV) are the ones the client takes off",
          lambda: suf == {"JR", "SR", "II", "III", "IV"} and "JR/SR/II/III/IV" in STEP1 and "JR / SR / II / III / IV" in SKILL, suf)
    note = "Medicare refused the plain check (%s) - the look-up was bought instead"
    check("texts: the report line of a refused plain check that the texts quote is the one the client prints ('stedi.medicare: pat<id>: Medicare refused the plain check (...) - the look-up was bought instead')",
          lambda: note in SRC["stedi.py"] and 'print("stedi.medicare: " + line' in SRC["stedi.py"] and "'stedi.medicare: pat<id>: Medicare refused the plain check (...) - the look-up was bought instead'" in STEP1
          and "'Medicare refused the plain check (...)'" in BB6 and '"Medicare refused the plain check (41) - the look-up was bought instead"' in SKILL)

# ==== 3. the Sunday step: claim status by need =====================================================================================
def t_claim_status():
    src = SRC["claim_status_sweep.py"]; lits = " | ".join(re.findall(r'"([^"\n]*)"', src))
    words = ["PAID $", "find/post the ERA", "FINALIZED $0", "DENIED/REVISED", "NOT ON FILE", "NOT ELIGIBLE on the date of service", "HAND OFF", "PENDING", "UNCONFIRMED",
             "NOT MATCHED", "NO USABLE ANSWER", "NOT ASKED", "HAND OFF TONIGHT", "STILL ON THE HAND-OFF LIST", "PAYER SWITCHED OFF", "WORDINGS THE RULES DO NOT KNOW",
             "STOPPED", "claims silent 60 or more days since they were last sent"]
    check("claim status: every action word and report line STEP 2 quotes is one claim_status_sweep.py prints (PAID / FINALIZED / DENIED/REVISED / NOT ON FILE / NOT ELIGIBLE / HAND OFF / PENDING / UNCONFIRMED / NOT MATCHED / NO USABLE ANSWER / NOT ASKED / STOPPED ...)",
          lambda: all(w in STEP2 for w in words) and all(w in lits for w in words), [w for w in words if w not in STEP2 or w not in lits])
    check("claim status: the 'NOT ASKED: N due claim(s) - <cap>' line STEP 2 quotes is the helper's", lambda: "'NOT ASKED: N due claim(s) - <run or month cap>'" in STEP2
          and 'for why, n in left.most_common(): p("  NOT ASKED: %d due claim(s) - %s" % (n, why))' in src
          and '"run cap: %d checks"' in SRC["cs_rules.py"] and '"month cap: %d checks"' in SRC["cs_rules.py"])
    check("claim status: the run file STEP 2 reads, claimstatus_<today>.json, is the file the helper writes (YYYYMMDD), and it is written again after every claim",
          lambda: "claimstatus_<today>.json" in STEP2 and 'out_name="claimstatus_%s.json"' in src and 'name = out_name % datetime.date.today().strftime("%Y%m%d")' in src
          and "after_claim=(lambda rows: write_rows(rows, name)) if o.go" in src and re.search(r"except cs_rules\.LedgerWriteError.*\n\s+if after_claim:\n\s+try: after_claim\(out\)", src)
          and "after every claim" in STEP2)
    check("claim status: the caps STEP 2 states (150 checks or $25 a run, 400 checks or $100 a calendar month) are cs_rules.CAPS",
          lambda: CS.CAPS == {"run checks": 150, "run dollars": 25.0, "month checks": 400, "month dollars": 100.0} and "150 checks or $25 tonight, 400 checks or $100 this calendar month" in STEP2, CS.CAPS)
    W = CS.WAITS
    check("claim status: the waits STEP 2 states are the one table at the top of cs_rules.py (pending 14 / 30 after 120 days / 7 near the 12-month limit, no usable answer 7, 'not found' and 'not eligible' 30 days after a resend)",
          lambda: (W["pending"], W["pending, sent 120+ days"], W["near the filing limit"], W["no usable answer"], W["not found"], W["not eligible"]) == (14, 30, 7, 7, 30, 30)
          and CS.OLD_PENDING_DAYS == 120 and CS.NEAR_LIMIT_DAYS == 30 and CS.FILING_LIMIT_DAYS["default"] == 365
          and "'pending' 14 days (30 when the claim was last sent 120+ days ago, 7 when its 12-month filing limit is within 30 days); no usable answer 7 days; 'not found' and 'not eligible' only after the claim is sent again and 30 more days pass" in STEP2, W)
    check("claim status: 'due' as STEP 2 states it is cs_rules (45 days since sent, 60 for a secondary balance, under a year old)",
          lambda: CS.NEED_DAYS == {"primary": 45, "secondary": 60} and CS.YEAR_DAYS == 365 and "last sent 45 or more days ago (60 for a secondary balance), less than a year old" in STEP2)
    check("claim status: the stop rule STEP 2 states (two unusable or three 'pending' answers in a row) is cs_rules.STOP_AFTER",
          lambda: CS.STOP_AFTER == {"no usable answer": 2, "pending": 3} and "two unusable answers or three 'pending' answers in a row" in STEP2)
    check("claim status: the payers STEP 2 says are switched off (TRI00, TRI05, AAR01) and without a route (Medicare, VA community care) are cs_rules'",
          lambda: set(CS.CS_OFF) == {"TRI00", "TRI05", "AAR01"} and set(CS.CS_NO_ROUTE) == {"FLO02", "RET01", "VACCN"} and "never TRI00, TRI05 or AAR01" in STEP2 and "Medicare and VA community care have no route" in STEP2)
    lp = CS.ledger_path()
    check("claim status: the ledger STEP 2 names is the helper's default (registers/claim_status_ledger.json beside it), the repository holds a readable one, and the nightly bootstrap copies the registers there",
          lambda: lp.endswith(os.path.join("scripts", "helpers", "registers", "claim_status_ledger.json")) and "registers/claim_status_ledger.json over practices/ehpa/registers/claim_status_ledger.json" in STEP2
          and isinstance(CS.Ledger.open(os.path.join(ROOT, "practices/ehpa/registers/claim_status_ledger.json")).rows(), dict)
          and 'cp -r "$R"/practices/ehpa/registers/. "$W/registers/"' in _read("tools/nightly_bootstrap.sh"), lp)
    check("claim status: STEP 2 says what a STOPPED line before any check means (nothing asked, no run file) - the helper returns 2 there and writes no run file",
          lambda: "nothing was asked and no claimstatus file was written" in STEP2 and "if o.go and code != 2:" in src and 'p("STOPPED: %s" % e); return 2, [], say' in src)
    check("claim status: 'not eligible' is a coverage problem, never a resend, in the text and in the helper's words",
          lambda: "'NOT ELIGIBLE on the date of service' rows: a coverage problem - run the STEP 1 insurance cascade on that patient, never a resend" in STEP2
          and any(l.startswith("NOT ELIGIBLE on the date of service") and "never a resend" in l for l in re.findall(r'"([^"\n]*)"', src)))

# ==== 4. the usage log and the prices ==============================================================================================
def t_usage_and_prices():
    L = PR.LADDERS
    check("prices: the prices the texts state are stedi_prices.py's (eligibility and a plain Medicare check $0.30 for the month's first 250 then $0.15; look-up $1.00 for 100 then $0.75; discovery $1.50 then $1.00; claim status $0.30 then $0.15)",
          lambda: L["eligibility"][:2] == [(250, 0.30), (3500, 0.15)] and PR.ladder_of("plain Medicare") == "eligibility" and L["claim status"][:2] == [(250, 0.30), (3500, 0.15)]
          and L["look-up without SSN"][:2] == L["look-up with SSN"][:2] == [(100, 1.00), (750, 0.75)] and L["discovery"][:2] == [(100, 1.50), (750, 1.00)]
          and "plain Medicare check and payer eligibility $0.30 for the month's first 250, then $0.15; MBI look-up $1.00 for the first 100, then $0.75" in STEP4
          and "discovery $1.50, then $1.00; claim status $0.30, then $0.15" in STEP4 and "$0.30 for the month's first 250, then $0.15) against $1.00 / $0.75 for a look-up" in SKILL
          and "($0.30, then $0.15 after the month's 250th)" in STEP2)
    check("prices: no live text still prices by hand at '$0.30 eligibility / $1.00 MBI / $1.50 discovery'", lambda: not any("$1.00 MBI / $1.50 discovery" in t for t in LIVE_TXT.values()))
    check("usage log: the log the texts name (patient_db/stedi_usage.log, read by `python3 stedi_usage.py`) is where stedi.py writes and stedi_usage.py reads",
          lambda: 'os.path.join(HERE, "patient_db", "stedi_usage.log")' in SRC["stedi.py"] and 'os.path.join(HERE, "patient_db", "stedi_usage.log")' in SRC["stedi_usage.py"]
          and "patient_db/stedi_usage.log" in STEP4 and "`python3 stedi_usage.py`" in STEP4 and "patient_db/stedi_usage.log" in BB6 and "`python3 stedi_usage.py`" in BB6)
    check("usage log: 'this routine never restores patient_db/' is true - the nightly cascade unpacks no state bundle and its bootstrap creates no patient_db/",
          lambda: "never restores patient_db/" in STEP4 and "unpack" not in CAS and "patient_db" not in _read("tools/nightly_bootstrap.sh") and "patient_db" not in CAS.split("WORKSPACE BOOTSTRAP", 1)[1].split("\n", 1)[0])
    check("usage log: 'it travels in the state bundle with patient_db/' (Billing Button) is true - the bundle packs patient_db/ and the Button unpacks it",
          lambda: "travels in the state bundle with patient_db/" in BB6 and "'patient_db'" in _read("tools/bootstrap/ws_bundle.py").split("DIRS =", 1)[1].split("\n", 1)[0] and "ws_bundle.py unpack inbox" in BB)

# ==== 5. the skill, the registry row, the pages =====================================================================================
def t_skill_and_docs():
    payer = next((l for l in SKILL.splitlines() if l.startswith("- Payer ids that work:")), "")
    check("skill: the payer-id line says the plain Medicare check (CMS) is live for the group provider number - no more 'AAA 41 until the attestation propagates'",
          lambda: "PLAIN Medicare check `CMS`" in payer and "AAA 41 until" not in payer.replace('"AAA 41 until the HEET attestation propagates" is history', "") and "10/8/2026" in payer, payer[:300])
    s3 = next((l for l in SKILL.splitlines() if l.startswith("3. ")), "")
    check("skill: step 3 is ONE Medicare answer - plain check first when the chart holds a Medicare number, the look-up when it does not or Medicare does not know the number",
          lambda: "One Medicare answer" in s3 and "Plain check first when the chart holds a Medicare number" in s3 and "The look-up when it does not, or when Medicare does not know the number" in s3
          and "`python3 stedi.py medicare FIRST LAST YYYYMMDD" in s3 and "Only a look-up returns Medicare's own MBI" in s3, s3[:200])
    tax = next((l for l in SKILL.splitlines() if "**Error taxonomy" in l), "")
    check("skill: error 72 is given its two meanings (a plain check: that number is not valid; a look-up: no record by name, birth date and state)",
          lambda: "ERR 72 means two different things on the two Medicare calls" in tax and "On a PLAIN check (`CMS`) it means Medicare does not know THAT NUMBER" in tax and "On a LOOK-UP" in tax)
    reg = next((l for l in _read("docs/captured_calls.md").splitlines() if l.startswith("| Stedi eligibility |")), "")
    check("registry: the vendor-eligibility row describes the plain Medicare check (CMS), its answer shape and the two answers of 10/8/2026, and names stedi.medicare",
          lambda: "CMS = the PLAIN Medicare check" in reg and "CMS = AAA 41 until HEET propagates)" not in reg and "10/8/2026" in reg and "`stedi.medicare`" in reg
          and "subscriber.memberId is only the number that was sent" in reg and _exists("practices/ehpa/registers/admit_lookup_2026-10-08T1910Z.json"), reg[:200])
    pages = {}
    for rel in ("tools/button/billing_button_page.html", "desktop/ui.html"):
        m = re.search(r'<label for="s-sweep">(.*?)</label>', _read(rel), re.S); pages[rel] = m.group(1) if m else ""
    check("pages: the Billing Button page and the desktop app no longer say the sweep box buys a Stedi 277 per claim (the engine's sweep step starts nothing)",
          lambda: all(t and "costs a Stedi 277" not in t and "starts nothing" in t for t in pages.values()) and "the cascade and the sweep need it" not in _read("desktop/ui.html"), pages)
    doc = _read("docs/BILLING_BUTTON.md"); row = next((l for l in doc.splitlines() if l.startswith("| `sweep` |")), "")
    check("docs: the engine's documentation says the sweep step starts nothing and no longer promises Stedi steps it does not run",
          lambda: "nothing is started" in row and "--min-age" not in row and "the Stedi steps (precheck, sweep) are skipped" not in doc, row)

# ==== 6. the review fixes of 11/10/2026: the sentences the three reviews found untrue, and the words of the new rules ================
def _header(src):
    """A helper's PLAIN ENGLISH header: the comment lines at the top, up to the first line that is not a comment."""
    out = []
    for l in src.splitlines():
        if not l.startswith("#"): break
        out.append(l.lstrip("# "))
    return " ".join(out)
def t_review_texts():
    G = {n: _header(_read(n)) for n in ("scripts/helpers/stedi.py", "scripts/helpers/deceased_guard.py", "scripts/helpers/precheck.py")}
    reg = next((l for l in _read("docs/captured_calls.md").splitlines() if l.startswith("| Stedi eligibility |")), "")
    guard_par = next((l for l in SKILL.splitlines() if l.startswith("DECEASED GUARD")), "")
    places = dict(G, **{"cascade.txt STEP 1": STEP1, "SKILL.md deceased guard": guard_par, "captured_calls.md row": reg})
    bad = [n for n, t in places.items() if re.search(r"look-?up[^.;]{0,60}only when the chart has no", t, re.I) or not re.search(r"refuses the plain check for another reason", t)]
    check("review texts: no text says the look-up is bought 'only when' the chart has no number or Medicare does not know it - each names a refused plain check too (ops S2)", lambda: bad == [], bad)
    m = re.search(r'PROVIDER_REFUSED = \{([^}]*)\}', SRC["stedi.py"]); off = set(m.group(1).replace('"', "").replace(" ", "").split(",")) if m else set()
    def codes_after(t):
        m = re.search(r"our own provider number \(([\d, or]+)\)", t); return set(re.findall(r"\d+", m.group(1))) if m else set()
    check("review texts: the provider-number refusals the texts name (41, 43, 50, 51, 97) are the client's PROVIDER_REFUSED, and they say the rest of the run sends no plain check (guard S5)",
          lambda: off == {"41", "43", "50", "51", "97"} and codes_after(STEP1) == codes_after(SKILL) == codes_after(reg) == off and "the rest of that run sends no plain check" in STEP1
          and "the rest of that run sends no plain check" in SKILL and "the rest of that run sends no plain check" in reg and "_PLAIN_OFF" in SRC["stedi.py"], (off, codes_after(STEP1), codes_after(SKILL), codes_after(reg)))
    check("review texts: STEP 2 runs aging_refresh.py as ONE Bash call with the longest timeout - cut off at the 2-minute default it writes no ageing file and the sweep asks nothing (ops B1, claim-status CS-2)",
          lambda: "`python3 aging_refresh.py --out aging_latest.json --threads 4` as ONE Bash call with the longest timeout (10 minutes" in STEP2 and "run it once more the same way before the sweep" in STEP2)
    check("review texts: the exact-date sentence is true of cs_rules.label (a paid, denied or $0 window answer not naming the claim, an answer naming only other visits, a 'not matched' answer) - in STEP 2 and the sweep's header (claim-status CS-1)",
          lambda: "a 3-day-window answer that does not name our claim, and a 'not matched' answer, get ONE check" not in STEP2
          and "a paid, denied or $0 answer from the 3-day window that does not name our claim, an answer whose claims all carry other visits' account numbers, and a 'not matched' answer get ONE check with the exact date" in STEP2
          and "an answer whose claims all carry other visits' account numbers" in _header(SRC["claim_status_sweep.py"]) and "the answer names only other claims" in SRC["cs_rules.py"])
    lits = " | ".join(re.findall(r'"([^"\n]*)"', SRC["claim_status_sweep.py"]))
    check("review texts: STEP 2 names the fourth hand-off reason, the 'PROPOSE FOR CS_OFF' line and the 'FINAL ANSWER ON FILE BUT NOTHING POSTED FOR ITS PAYER' lines - all printed by the helper, with cs_rules.STOP_AFTER_ANY = 4 (claim-status CS-3, CS-4, CS-5)",
          lambda: CS.STOP_AFTER_ANY == 4 and "four unusable answers in a row whether or not the payer answered another claim those nights" in STEP2 and "PROPOSE FOR CS_OFF" in STEP2 and "PROPOSE FOR CS_OFF" in lits
          and "FINAL ANSWER ON FILE BUT NOTHING POSTED FOR ITS PAYER" in STEP2 and "FINAL ANSWER ON FILE BUT NOTHING POSTED FOR ITS PAYER" in lits and "four answers in a row with no usable content" in SRC["cs_rules.py"])
    check("review texts: STEP 2, the sweep's header and its PROPOSE FOR CS_OFF line name a payer only on evidence about the payer itself - none says a payer 'answered nothing on four runs in a row' (re-check NEW-2)",
          lambda: not any("answered nothing" in t for t in (STEP2, lits, _header(SRC["claim_status_sweep.py"]))) and "a payer that answers its other claims is never named" in STEP2
          and "the payer answered none of its claims, and it has answered none since" in lits and "cs_rules.propose_off(" in SRC["claim_status_sweep.py"] and "def propose_off(" in SRC["cs_rules.py"])
    STEP6 = STEP(CAS, "STEP 6 - ", "\nREPORT:")
    check("review texts: STEP 6 copies the Sunday ledger back where the mirror is done, and a person's clear is made in the repository's ledger (ops N8)",
          lambda: "(on Sundays registers/claim_status_ledger.json over practices/ehpa/registers/claim_status_ledger.json" in STEP6
          and "`python3 cs_rules.py --clear <visit id> --ledger /home/claude/effinger-billing-backend/practices/ehpa/registers/claim_status_ledger.json`" in STEP2 and 'ap.add_argument("--ledger"' in SRC["cs_rules.py"])
    f = rule(BB6, "f")
    check("review texts: Billing Button rule (f) says the plain check is made only when the chart has a number of the Medicare shape, and the Button page no longer says the flags are listed for a chat session (ops N6)",
          lambda: "with the chart's Medicare number when it has one of the Medicare shape" in f and "listed for a chat session" not in _read("tools/button/billing_button_page.html"), f[:200])
    check("review texts: the price table and STEP 4 say what the table does not price (the coordination-of-benefits check, the payer pass-through fee) (ops N1)",
          lambda: "coordination-of-benefits" in _header(SRC["stedi_prices.py"]) and "pass-through fee" in _header(SRC["stedi_prices.py"]) and "pass-through fee" in STEP4
          and "made through stedi.py" in _header(SRC["stedi_prices.py"]))
    s3 = next((l for l in SKILL.splitlines() if l.startswith("3. ")), "")
    check("review texts: the skill says the look-up goes with the chart's own last name (suffix and all), and that a shared answer serves the guard only when asked on or after the claim's date of service (guard B1, S1)",
          lambda: "sent with the chart's own last name, suffix and all" in s3 and "asked on or after the claim's date of service" in guard_par and "chart_last" in SRC["stedi.py"])
    row = next((l for l in _read("docs/captured_calls.md").splitlines() if l.startswith("| Unpaid list / visits by last-billed carrier")), "")
    check("review texts: the registry's unpaid-list row no longer names the claim-status sweep as a user - it reads tonight's aging_latest.json (claim-status CS-13 d)",
          lambda: "`build_money.py` (`claim_status_sweep.py` read it until 11/10/2026" in row and "massrebillsearch" not in SRC["claim_status_sweep.py"], row[:200])
    GATE = load("tools/mirror/phi_gate.py", "phi_gate_under_test")                  # the gate's text transform only: pure, no file, no network
    tests = ("tools/selftest/test_lookup_rules.py", "tools/selftest/test_claim_status_rules.py")
    moved = [n for n in tests if GATE.redact(_read(n), {}, code=True) != _read(n)]
    check("review texts: the privacy gate's tree rules (what mirror.py runs on changed files) leave the two rule self-tests unchanged - their invented literals are built gate-safe (ops N3)",
          lambda: moved == [], moved)
    # the re-check of 11/10/2026: the new findings' words
    check("review texts: the skill's guard paragraph says an answer that already shows a date of death is used as it is, and a death a kept answer shows still blocks when a call fails - as deceased_guard.py does (re-check NEW-1)",
          lambda: "unless that answer already shows a date of death: a death is never undone" in guard_par and "unless a Medicare answer already kept in medicare_store.py shows the date of death: that death still blocks" in guard_par
          and "def death(" in _read("scripts/helpers/medicare_store.py") and "_stored_death(pid)" in _read("scripts/helpers/deceased_guard.py") and "not dod_from_271(j) and _asked_before(" in _read("scripts/helpers/deceased_guard.py"), guard_par[-400:])
    fs, fb = rule(STEP1, "f"), rule(BB6, "f")
    check("review texts: rule (f) in STEP 1 and in the Billing Button says only the look-up is asked once Medicare has refused our provider number earlier in the run (the client's _PLAIN_OFF) (re-check NEW-5)",
          lambda: "Medicare had refused our provider number earlier in that run" in fs and "Medicare has not refused our provider number earlier in that run" in fb and "if _PLAIN_OFF: number = None" in SRC["stedi.py"], (fs[:400], fb[:400]))
    check("review texts: the price table's header says no committed helper makes a coordination-of-benefits check - not where September's came from (re-check NEW-7)",
          lambda: "one-off scripts" not in _header(SRC["stedi_prices.py"]) and "no committed helper makes one" in _header(SRC["stedi_prices.py"]), _header(SRC["stedi_prices.py"])[-500:])

for t in (t_commands, t_precheck, t_claim_status, t_usage_and_prices, t_skill_and_docs, t_review_texts):
    try: t()
    except Exception as e:
        import traceback
        check("%s ran to its end" % t.__name__, False, traceback.format_exc()[-700:])
print("test_lookup_texts: %d checks, %d failed%s" % (COUNT[0], len(FAILS), "" if not FAILS else " - " + "; ".join(FAILS)[:300]))
sys.exit(1 if FAILS else 0)
