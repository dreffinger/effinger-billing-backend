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
#       sweep, rule (f) after a refusal of our provider number, and the price table's coordination-of-benefits sentence say what the code does;
#     - (11/10/2026 second re-check) every text that describes the CS_OFF proposal (STEP 2, the sweep's header and its line, the rules'
#       header and propose_off) names its look-back - no usable answer from any claim of the payer from 7 days before the first of the four
#       tries until now - and none promises that a payer that answers its other claims is never named;
#     - (11/25/2026, the date-of-death check before any approval) both live prompts start death_check_review.py in step 1 with the same
#       clause - a BLOCKED charge never approved and voided; exit 2, a Python error or a count that differs = the guard applied by the run
#       itself, nothing approved unchecked - and keep every other word of the step; the rulebook's new bullet holds William's order word for
#       word, the answer to his question (the vendor is never free - AdvancedMD's check is) and the price table's prices; the Charge Review
#       skill and the lessons file name the helper; the privacy gate leaves the helper, its self-test and every new sentence alone;
#     - (review fix of 11/25/2026) the clause, the rulebook's bullet, the skill's sentence, the lessons line and the helper's header put the
#       helper before ANY save of the Charge Review step - the two gates fix a visit with a full-visit save that carries approval 1 and
#       asks no guard (read from recode.py, mod25_addon.py and dx_primary_fix.py), so no gate fix on a visit with a BLOCKED or NOT CHECKED
#       charge - and name the number a run compares with its own listing: the charges LISTED, never the charges checked (smaller by every
#       NOT CHECKED charge); a NOT CHECKED charge stays unapproved whatever a guard call of the run's own answers.
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
          lambda: not any("answered nothing" in t for t in (STEP2, lits, _header(SRC["claim_status_sweep.py"]))) and "only on evidence about the payer itself" in _header(SRC["claim_status_sweep.py"])
          and "cs_rules.propose_off(" in SRC["claim_status_sweep.py"] and "def propose_off(" in SRC["cs_rules.py"])
    # the second re-check (R2-1): the proposal looks back to 7 days before the first of the four tries; every text that describes it says so
    def _flat(t): return " ".join(str(t).split())
    po = _flat(SRC["cs_rules.py"].split("def propose_off(", 1)[1].split('"""')[1]) if SRC["cs_rules.py"].count("def propose_off(") == 1 else ""
    hs, hc = _header(SRC["claim_status_sweep.py"]), _header(SRC["cs_rules.py"])
    promise = re.compile(r"answers its other claims (is|while)[^.]{0,90}never (named|proposed)|never proposed because one claim")
    said = {"STEP 2": "none of that payer's claims has had a usable answer from 7 days before the first of those four until now" in STEP2
                      and "on the Sunday before the first of the four or on any night since is never named" in STEP2,
            "the sweep's line": "no claim of this payer has had a usable answer from %d days before the first of those four until now (in weekly runs: from the Sunday before)" in lits
                                and "cs_rules.PROPOSE_BEFORE_DAYS))" in SRC["claim_status_sweep.py"],
            "the sweep's header": "no claim of that payer has had a usable answer from 7 days before the first of those four answers until now" in hs,
            "the rules' header": "none of its claims has had a usable answer from 7 days before the first of those four until now" in hc,
            "propose_off": "from PROPOSE_BEFORE_DAYS (7) days before the first of those four until now" in po,
            "no false promise": not any(promise.search(t) for t in (STEP2, lits, hs, hc, po))}
    check("review texts: every text that describes the CS_OFF proposal says what propose_off checks - no usable answer from any claim of the payer from 7 days before the first of the four tries until now (the Sunday before, in weekly runs) - and none promises that 'a payer that answers its other claims is never named' (second re-check R2-1)",
          lambda: all(said.values()) and CS.PROPOSE_BEFORE_DAYS == CS.WAITS["no usable answer"] == 7, said)
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

# ==== 7. 11/25/2026 - the date-of-death check before any approval (William: "... verify date of death first ... is stedi able to do that for free?") ====
W1125 = ("add into the billing codes routines when billing any ccm codes to straight medicare to do a stedi or advanced md check to see can you do a "
         "check to verify date of death first so as not to bill any after the date of death to straight medicare is stedi able to do that for free? and "
         "check before submitting stedi does that for free right")      # William's order, word for word
DCR = "death_check_review.py"
DCR_HEAD = "DEATH CHECK BEFORE ANY APPROVAL"
DCR_BLOCK = "date of death before the date of service - do NOT approve; void (William 10/4 and 11/25/2026)"
DCR_UNCHECKED = "could not be checked - do not approve this charge on this run"
CR_SKILL = "skills/billing-easy-task-charge-review-and-claim-inspector-columns/SKILL.md"
def step1(text):
    """The Charge Review step of a live prompt: the line that starts '1. CHARGE REVIEW:'."""
    return next((l for l in text.splitlines() if l.startswith("1. CHARGE REVIEW:")), "")
def t_death_check():
    s1 = {"billing_button.txt": step1(BB), "columns.txt": step1(LIVE_TXT.get("columns.txt", ""))}
    clause = {n: (l[l.find(DCR_HEAD):] if DCR_HEAD in l else "") for n, l in s1.items()}
    hsrc = _read(H + DCR) if _exists(H + DCR) else ""; gsrc = _read(H + "deceased_guard.py")
    check("death check: the helper the Charge Review step starts, death_check_review.py, is in the repository where the workspace builders copy helpers from, and both live prompts start it in step 1 - before approvecharges, with no option",
          lambda: where(DCR) == H + DCR and all("before approvecharges run `python3 death_check_review.py`" in c for c in clause.values())
          and sorted((tn, a.strip()) for tn, h, a in CMDS if os.path.basename(h) == DCR) == [("billing_button.txt", ""), ("columns.txt", "")], (where(DCR), [(tn, a) for tn, h, a in CMDS if os.path.basename(h) == DCR]))
    old = "1. CHARGE REVIEW: getreviewcharges class=chargeentry per batch id from getclaiminspectorbatches. CCM / modifier-25 gate (99487 never carries 25; the add-on 99489 and 99497-with-99223/99306 get modifier 25 = mcode7"
    check("death check: every other word of the two step-1 lines is kept - the clause stands at the END of each line, behind the line's old last sentence, and is the SAME clause in both prompts",
          lambda: all(l.startswith(old) and "then approvecharges for a clean batch; flag anything that fails the gate. PRIMARY-DX GATE" in l and "the F02.8x -> F03.90 inspector swap still applies where the inspector raises it." in l for l in s1.values())
          and "The deceased guard runs before every approval. " + DCR_HEAD in s1["billing_button.txt"] and "- catch it here, before the claim goes out. " + DCR_HEAD in s1["columns.txt"]
          and clause["billing_button.txt"] == clause["columns.txt"] != "" and all(l.count(DCR_HEAD) == 1 for l in s1.values()), {n: l[-260:] for n, l in s1.items()})
    c = clause["columns.txt"]
    check("death check: the clause says what a run does with the helper's lines - a BLOCKED charge is never approved and is voided (rules.md 10/4 and 11/25/2026), a NOT CHECKED charge is not approved on this run - and that exit 3 is an answer, not a failure of the helper",
          lambda: "a charge it lists as BLOCKED is never approved" in c and "and is voided (rules.md 10/4 and 11/25/2026)" in c and "a charge it lists as NOT CHECKED is not approved on this run" in c
          and "exit 0 = every charge checked and none blocked; exit 3 = an answer too, not a failure: at least one charge BLOCKED or NOT CHECKED" in c and "an UNVERIFIED line is no block" in c, c)
    check("death check: ... and what it does when the helper itself fails - exit 2 or a Python error: said at the top of the report, the guard applied to every charge by the run itself as before (deceased_guard.check with the claim's first carrier and the code - the call the runs' own code made - or deceased_guard.check_charge), nothing approved unchecked",
          lambda: "exit 2" in c and "a Python error" in c and "say so at the top of the report" in c and "approve nothing this run" in c and "`deceased_guard.check_charge(<charge id>, <first number of the visit's insorder>)`" in c
          and "as before (`deceased_guard.check(<chart>, <date of service>, <the carrier the claim goes to first>, <the code>)` for each charge, or `deceased_guard.check_charge(" in c
          and c.rstrip().endswith("the helper is a faster, tested way to do the same check, never a reason to approve unchecked."), c[-640:])
    # review fix of 11/25/2026: the texts first told a run to compare the number of charges CHECKED with its own listing. That number is smaller
    # by every NOT CHECKED charge, so every answer with one tripped the rule and sent the run to guard calls of its own - and
    # deceased_guard.check_charge answers 'not blocked' when it has nothing to compare. The number to compare is the number LISTED.
    check("death check: ... and that the number of charges the helper's summary line says it LISTED - the line's first number, as the helper prints it - must equal the number of charges in the run's own listing of Charge Review, taken before any save; never the number checked, which is smaller by every NOT CHECKED charge - if the two differ, the same",
          lambda: "the number of charges its summary line says it listed - the line's FIRST number; the number checked is smaller by every NOT CHECKED charge and is not the one to compare - must equal the number of charges in your own listing of Charge Review, taken before any save" in c
          and "says it checked must equal" not in c and "the same when the two numbers differ" in c and '"DEATH CHECK - Charge Review: %d charge(s) on %d visit(s) listed, %d checked; ' in hsrc, c)
    # review fix of 11/25/2026: the texts first said only "before approvecharges". The step's two gates save before that: they fix a visit with
    # a full-visit save that carries approval 1 and asks no guard; a visit saved that way may leave Charge Review approved, and the helper
    # lists only what is still there.
    gates = {n: _read(H + n) for n in ("recode.py", "mod25_addon.py", "dx_primary_fix.py")}
    def body(src, name):
        """The text of one top-level function of a helper, up to the next top-level def."""
        m = re.search(r"^def %s\(.*?(?=^def |\Z)" % re.escape(name), src, re.S | re.M); return m.group(0) if m else ""
    check("death check, review fix of 11/25/2026: the clause puts the helper before ANY save of the step - before either gate saves its fix, not only before approvecharges - and says why; the code bears it out: the modifier-25 fix (mod25_addon.py -> recode._save) and the primary-dx fix (dx_primary_fix.save_visit_dx) are full-visit saves (updvisitwithcharges) that carry approval 1, and none of the three files asks the deceased guard",
          lambda: "IT COMES BEFORE ANY SAVE IN THIS STEP - before either gate above saves its fix, not only before approvecharges: the modifier-25 fix and the primary-dx fix are full-visit saves that carry approval=1 and ask no guard, so treat each as an approval, and the helper lists only what is still waiting in Charge Review - a visit such a save has taken out of Charge Review is never put through it." in c
          and 0 < c.find("IT COMES BEFORE ANY SAVE IN THIS STEP") < c.find("Its last line is the summary line")
          and all("updvisitwithcharges" in b_ and re.search(r'"approval"\s*:\s*"1"', b_) is not None for b_ in (body(gates["recode.py"], "_save"), body(gates["dx_primary_fix.py"], "save_visit_dx")))
          and "recode._save(" in gates["mod25_addon.py"] and not any("deceased_guard" in s for s in gates.values()), c[:900])
    # What these two sentences say of deceased_guard.check_charge is shown with the REAL guard, not read from its text: tools/selftest/test_death_check_review.py 10x3 and 10x4.
    check("death check, review fix of 11/25/2026: the visit of a BLOCKED or a NOT CHECKED charge gets no gate fix and stays out of approvecharges; a NOT CHECKED charge stays unapproved whatever a guard call of the run's own answers for it (the guard's check_charge raises nothing when it has nothing to compare)",
          lambda: "a charge it lists as BLOCKED is never approved - its visit gets no gate fix and stays out of approvecharges - and is voided (rules.md 10/4 and 11/25/2026)" in c
          and "a charge it lists as NOT CHECKED is not approved on this run - its visit gets no gate fix and stays out of approvecharges too, whatever a guard call of your own answers for it (deceased_guard.check_charge raises nothing when it has nothing to compare: it answers 'not blocked')" in c, c)
    check("death check, review fix of 11/25/2026: when the run has to apply the guard itself, the call to use is deceased_guard.check with the claim's own carrier and code; check_charge only where the charge's own detail shows a plan element with its carrier at that sequence and the code is no care-management code - and no gate fix is saved on a visit before the guard has answered for its charges",
          lambda: "`deceased_guard.check_charge(<charge id>, <first number of the visit's insorder>)` - that one only where the charge's own detail shows a plan element with its carrier at that sequence and the code is no care-management code: with less to go on it may ask Medicare nothing), with no gate fix saved on a visit before the guard has answered for its charges, and the same when the two numbers differ" in c, c[-900:])
    check("death check, review fix of 11/25/2026: the helper's own header names the same number - N, the charges LISTED, never K, the charges checked - and the same order: before approvecharges and before any save of a Charge Review visit",
          lambda: "N - the charges LISTED, the line's first number - is the number a run compares with its own listing" in _header(hsrc) and "K is NOT that number" in _header(hsrc) and "K is the number a run compares" not in _header(hsrc)
          and "BEFORE approvecharges AND BEFORE ANY SAVE of a Charge Review visit" in _header(hsrc), _header(hsrc)[:700])
    check("death check: the words the texts rely on are the helper's own - its BLOCKED and NOT CHECKED lines with the fixed words, the summary line, the three exit codes, --dry, the register's name, its two questions to the guard (check_charge at sequence 1 for every charge; check with the first plan's carrier and the code) - and both guard calls exist as the texts write them",
          lambda: all(x in hsrc for x in ('"%s"' % DCR_BLOCK, '"%s"' % DCR_UNCHECKED, '"BLOCKED: pat%s visit %s charge %s DOS %s code %s - "', '"NOT CHECKED: pat%s visit %s charge %s (%s) - "', '"DEATH CHECK - Charge Review: ', '"--dry"',
                                           '"death_check_review_%s%s.json"', "return 2", "3 if ", "G.check_charge(cid, 1, allow_lookup=False) if dry else G.check_charge(cid, 1)", 'G.check(w["chart"], w["dos"], carrier, w["cpt"] or w["proc"] or None, allow_lookup=not dry)'))
          and "EXIT: 0 =" in _header(hsrc) and re.search(r"^def check_charge\(chargeid, sequencenumber=None, allow_lookup=True", gsrc, re.M) is not None
          and re.search(r"^def check\(pid, dos, carrier=None, proc=None, allow_lookup=True", gsrc, re.M) is not None, hsrc[:200])
    rb = _read("practices/ehpa/rules.md").splitlines()
    i = next((k for k, l in enumerate(rb) if l.startswith("- (11/25/2026, William in chat, STANDING for the charge feed) CCM AFTER A PATIENT HAS PASSED AWAY")), -1)
    b = rb[i + 1] if 0 <= i < len(rb) - 1 else ""
    check("rulebook: ONE new bullet right behind 'CCM AFTER A PATIENT HAS PASSED AWAY' holds William's order of 11/25/2026 word for word and his question's answer - the vendor is never free, AdvancedMD's check is",
          lambda: b.startswith("- (11/25/2026, William in chat, STANDING for every billing task) ") and ('"%s"' % W1125) in b and "the vendor is never free - AdvancedMD's check is" in b
          and sum(1 for l in rb if W1125 in l) == 1, b[:300])
    check("rulebook: the bullet says what is in force - the check runs before a CCM charge is entered from the feed, before any charge is approved in Charge Review (death_check_review.py) and before any rebill; the free check first, a vendor answer only when the free one cannot answer; a failed check blocks nothing and is said",
          lambda: "before a CCM charge is entered from the feed" in b and "before any charge is approved in Charge Review - death_check_review.py" in b and "and before any rebill" in b
          and "it asks AdvancedMD's free check" in b and "first and buys a vendor answer only when the free one cannot answer" in b
          and "A failed check blocks nothing - only a date on Medicare's record does" in b and "and is said" in b, b[-900:])
    check("rulebook, review fix of 11/25/2026: the bullet says the helper is started before approvecharges AND before either Charge Review gate saves its fix (those fixes are full-visit saves that carry approval 1 and ask no guard), that the visit of a BLOCKED or NOT CHECKED charge gets no gate fix, and that a NOT CHECKED charge stays unapproved whatever a guard call of the run's own answers",
          lambda: "the standing read-only helper a run starts before approvecharges and before either Charge Review gate saves its fix (the modifier-25 fix and the primary-dx fix are full-visit saves that carry approval 1 and ask no guard: each is treated as an approval)" in b
          and "not approved on that run, whatever a guard call of the run's own answers for it; the visit of a BLOCKED or NOT CHECKED charge gets no gate fix" in b
          and "as before (deceased_guard.check with the claim's first carrier and the code; deceased_guard.check_charge only where the charge's own detail shows that plan's carrier and the code is no care-management code), saves no gate fix on a visit before the guard has answered for its charges, and approves nothing it has not checked" in b, b[-1300:])
    L = PR.LADDERS
    check("rulebook: the prices the bullet states are stedi_prices.py's (a plain Medicare check $0.30 for the month's first 250, then $0.15; the look-up by name $1.00 for the first 100, then $0.75)",
          lambda: L["eligibility"][:2] == [(250, 0.30), (3500, 0.15)] and PR.ladder_of("plain Medicare") == "eligibility" and L["look-up without SSN"][:2] == [(100, 1.00), (750, 0.75)]
          and "stedi_prices.py: a plain Medicare check $0.30 each for the month's first 250, then $0.15; the look-up by name $1.00 each for the first 100, then $0.75" in b, b[:700])
    sk = _read(CR_SKILL); guard_sec = sk.split("## Deceased-patient guard", 1)[1] if "## Deceased-patient guard" in sk else ""
    check("skill: the Charge Review skill's 'Deceased-patient guard' section names the helper in one sentence - started before approvecharges, read-only, and never a reason to approve unchecked",
          lambda: guard_sec.count("death_check_review.py") == 1 and "Before approvecharges run the standing helper `python3 death_check_review.py`" in guard_sec and "approve nothing you have not checked" in guard_sec, guard_sec[-500:])
    check("skill, review fix of 11/25/2026: the sentence says the helper runs before any save of a Charge Review visit too (the gates' fixes are saves that carry approval 1 and ask no guard; no such fix on a visit with a BLOCKED or NOT CHECKED charge), that a NOT CHECKED charge stays unapproved whatever a guard call of the run's own answers, and that the count to compare with the run's own listing is the count LISTED - never the count checked",
          lambda: 'run it before any save of a Charge Review visit too - the modifier-25 fix and the primary-dx fix are full-visit saves that carry approval="1" and ask no guard, so each is treated as an approval, and a visit with a BLOCKED or NOT CHECKED charge gets no such fix' in guard_sec
          and "(not approved on this run, whatever a guard call of your own answers for it)" in guard_sec
          and "a last summary line whose count of charges LISTED (its first number - not the count checked, which is smaller by every NOT CHECKED charge) must equal the number of charges in your own listing of Charge Review" in guard_sec
          and "count of charges checked must equal" not in guard_sec, guard_sec[-1700:])
    ls = [l for l in _read("docs/SHARED_LESSONS.md").splitlines() if l.startswith("- 2026-11-25T0800Z | chat (William: date-of-death check before CCM to Medicare; is the vendor free?) | FIX | ")]
    check("lessons: ONE dated line (kind FIX, five fields) records the change for every other routine - the free check first, the standing helper, its exit codes and the fallback",
          lambda: len(ls) == 1 and ls[0].count(" | ") == 4 and all(x in ls[0] for x in ("death_check_review.py", "the vendor is never free", "exit 0", "3 =", "2 =", "deceased_guard.check_charge")), ls[:1])
    check("lessons, review fix of 11/25/2026: that line says the helper is started before approvecharges AND before any save of a Charge Review visit, names the trap of the step's order (the gates fix a visit with a full-visit save that carries approval 1 and asks no guard), the count LISTED as the number to compare with the run's own listing - never the count checked - and that a NOT CHECKED charge stays unapproved whatever a guard call of the run's own answers",
          lambda: len(ls) == 1 and all(x in ls[0] for x in ("Before approvecharges AND BEFORE ANY SAVE OF A CHARGE REVIEW VISIT a run starts `python3 death_check_review.py`", "a count of charges LISTED - the summary line's first number; never the count checked, which is smaller by every NOT CHECKED charge, the helper working as designed - that differs from the run's own listing (taken before any save)",
                                                             "TRAP of the step's order", "full-visit save that carries approval 1 and asks no guard", "a visit such a save has taken out of Charge Review is never listed by the helper",
                                                             "(not approved on that run, whatever a guard call of the run's own answers for it)", "as before (deceased_guard.check with the claim's first carrier and the code - not deceased_guard.check_charge alone: the trap below)"))
          and "a count of charges checked that differs" not in ls[0], [x[-1500:] for x in ls[:1]])
    GATE = load("tools/mirror/phi_gate.py", "phi_gate_under_test_2")                  # the gate's text transform only: pure, no file, no network
    code = ("tools/selftest/test_death_check_review.py", H + DCR)
    moved = [n for n in code if not _exists(n) or GATE.redact(_read(n), {}, code=True) != _read(n)]
    prose = {"billing_button.txt step 1": s1["billing_button.txt"], "columns.txt step 1": s1["columns.txt"], "rules.md bullet": b, "the skill's guard section": guard_sec, "the lessons line": (ls or [""])[0]}
    moved += [n for n, t in prose.items() if not t or GATE.redact(t, {}, code=False) != t]
    check("death check: the privacy gate's tree rules leave the helper, its self-test and every new sentence exactly as they are (a date written right behind the word death would be rewritten - none is)", lambda: moved == [], moved)

for t in (t_commands, t_precheck, t_claim_status, t_usage_and_prices, t_skill_and_docs, t_review_texts, t_death_check):
    try: t()
    except Exception as e:
        import traceback
        check("%s ran to its end" % t.__name__, False, traceback.format_exc()[-700:])
print("test_lookup_texts: %d checks, %d failed%s" % (COUNT[0], len(FAILS), "" if not FAILS else " - " + "; ".join(FAILS)[:300]))
sys.exit(1 if FAILS else 0)
