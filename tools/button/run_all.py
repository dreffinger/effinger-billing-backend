#!/usr/bin/env python3
# PLAIN ENGLISH (the Billing Button engine - William 10/11/2026: "package all the billing routines and the nightly cascade in an
#   automatic run as they are written in GitHub, with a dashboard where I press one button, no mandatory-approval blocks")
# Decides: nothing new. It runs the helpers this repository already carries, in the standing order of the 2-hourly backend billing
#   run and the nightly insurance cascade, from a fresh workspace built out of this repository - and it writes ONE report
#   (reports/button/<stamp>.json + latest.json) in the shape the "ehpa Billing Button" page and the desktop app render.
#   No permission classifier sits in this path: pressing the button IS the approval. Everything the helpers can decide by
#   William's standing rules is done; everything that needs a judgement (a chart fix after a Stedi answer, a dx cascade on a
#   named chart, a hand-post) is counted and listed under "waiting" for a chat session or William.
# Steps (--steps): columns (Claims Center scan -> inspector advisory bypasses -> Unbilled repairs -> ERA-linked reason-code
#   re-posts -> duplicate / crossover exclusion completions -> rescan), era (835 inbox upload -> list -> Post button ->
#   era_clear -> list), cascade (void-on-arrival rules -> Stedi pre-claim check), sweep (UNI20/BCBS pre-5/1/2026 277 pass),
#   packages (approved Mandatory Approvals cards: dry first, then live, then recorded done), cred (NPPES / revalidation / LEIE),
#   money (payments scan when the universe file is present, ledger rebuild). "all" = every step except sweep and money unless named.
# Modes: --mode dry reads everything and writes nothing in AdvancedMD (every helper gets its dry form); --mode live writes.
# Rules it uses: ONE AMD login per run (amd.login_cached; a tripped .amd_login_lock stops the run before any helper runs);
#   every helper is ONE plain command run from the workspace; a helper that fails never stops the others; no patient name,
#   member id, MBI or DOB reaches the report - chart ids, visit ids, check ids and dollars only (phi_gate checks the report
#   before it is written; helper output goes to log files, never to the console).
# Never touches: the helpers themselves (they run exactly as committed), .claude/settings.json, any permission setting.
#   python3 tools/button/run_all.py --mode dry --steps all                       # the default button press
#   python3 tools/button/run_all.py --mode live --steps columns,era,packages      # the 2-hourly profile
#   python3 tools/button/run_all.py --mode live --profile cascade                 # the nightly profile
#   python3 tools/button/run_all.py --mode live --steps packages --packages A-2026-10-11T0510Z-A
# Environment: AMD_PSW (the POI0712 password; amd._stored_psw reads it), STEDI_API_KEY (optional - the Authorization header
#   value; without it the Stedi steps are skipped), EHPA_PYTHON_ARGV (optional JSON list: the interpreter prefix the frozen
#   desktop app uses to run the helpers, e.g. ["C:\\...\\ehpa-billing-button.exe", "--py"]).
import argparse, datetime, glob, json, os, re, shutil, subprocess, sys, time, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
CANON_WS = "/home/claude/unbilled"          # the workspace path every helper was written for (amd.py keeps its session cache here)
SCHEMA = "button-run/1"
PROFILES = {
    "all": ["columns", "era", "cascade", "packages", "cred", "outstanding", "denials", "aging"],
    "columns": ["columns", "era", "packages", "outstanding", "denials"],                 # the 2-hourly backend billing run
    "cascade": ["cascade", "era", "packages", "cred", "money", "outstanding", "denials", "aging"],  # the nightly insurance cascade
    "denials": ["denials"],                                                     # the Working Denials board's Refresh button
    "aging": ["aging"],                                                         # the AR Aging page's Refresh button (10/15/2026)
}
STEP_TITLES = {"columns": "Claims Center columns", "era": "ERA posting", "cascade": "Insurance cascade",
               "sweep": "Claim-status sweep (277)", "packages": "Approval packages", "cred": "Credentialing check",
               "money": "Money ledger data", "outstanding": "Outstanding claims summary", "denials": "Working Denials refresh", "aging": "AR aging refresh"}
ADVISORY_ERR_PATTERNS = ("20657", "11256", "33799", "35790", "7011", "3429", "35777", "4426", "4310", "27261")


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


def iso(dt=None):
    return (dt or utcnow()).strftime("%Y-%m-%dT%H:%M:%SZ")


def stamp_now():
    return utcnow().strftime("%Y-%m-%dT%H%MZ")


def money(x):
    try:
        return round(float(x or 0), 2)
    except (TypeError, ValueError):
        return 0.0


class Run:
    def __init__(self, a):
        self.a = a
        self.mode = a.mode
        self.live = a.mode == "live"
        self.stamp = a.stamp or stamp_now()
        self.ws = a.ws or CANON_WS
        self.out = os.path.abspath(a.out)
        self.logdir = os.path.join(self.out, "logs_" + self.stamp)
        self.steps = []
        self.errors = []
        self.waiting = []
        self.pkg_rows = []
        self.summary = {"columns": {"before": {}, "after": {}}, "era": {"before": {}, "after": {}},
                        "posted": {"pay": 0.0, "woins": 0.0, "wocaid2nd": 0.0, "wolate": 0.0},
                        "resent": {"visits": 0, "dollars": 0.0}, "written_off": {"count": 0, "dollars": 0.0},
                        "packages": {"applied": 0, "refused": 0, "skipped": 0}}
        self.py = self._python_argv()
        self.stedi = bool(os.environ.get("STEDI_API_KEY")) or a.stedi_proxy
        os.makedirs(self.logdir, exist_ok=True)

    # ------------------------------------------------------------------ plumbing
    def _python_argv(self):
        env = os.environ.get("EHPA_PYTHON_ARGV")
        if env:
            try:
                v = json.loads(env)
                if isinstance(v, list) and v:
                    return [str(x) for x in v]
            except ValueError:
                pass
        if self.a.python:
            return [self.a.python]
        return [sys.executable]

    def say(self, msg):
        print("[%s] %s" % (utcnow().strftime("%H:%M:%S"), msg), flush=True)

    def helper(self, name, argv, timeout=1800, env=None, cwd=None):
        """Run ONE helper as one plain command from the workspace. Output goes to a log file, never to the console."""
        cmd = self.py + [name] + [str(x) for x in argv]
        logname = re.sub(r"[^A-Za-z0-9_.-]+", "_", name + "_" + "_".join(str(x) for x in argv))[:120]
        log = os.path.join(self.logdir, "%02d_%s.log" % (len(os.listdir(self.logdir)) + 1, logname))
        e = dict(os.environ)
        e["PYTHONIOENCODING"] = "utf-8"
        e["PYTHONUNBUFFERED"] = "1"
        if env:
            e.update(env)
        t0 = time.time()
        with open(log, "w", encoding="utf-8", errors="replace") as fh:
            fh.write("$ %s\n(cwd %s, %s)\n\n" % (" ".join(cmd), cwd or self.ws, iso()))
            fh.flush()
            try:
                p = subprocess.run(cmd, cwd=cwd or self.ws, env=e, stdout=fh, stderr=subprocess.STDOUT, timeout=timeout)
                rc = p.returncode
            except subprocess.TimeoutExpired:
                fh.write("\n[run_all] TIMEOUT after %ds\n" % timeout)
                rc = -9
            except OSError as ex:
                fh.write("\n[run_all] could not start: %s\n" % ex)
                rc = -1
        text = open(log, encoding="utf-8", errors="replace").read()
        self.say("%s %s -> rc %s (%.0fs)" % (name, " ".join(str(x) for x in argv)[:60], rc, time.time() - t0))
        return rc, text, log

    def exists(self, name):
        return os.path.isfile(os.path.join(self.ws, name))

    def login_locked(self):
        return os.path.exists(os.path.join(self.ws, ".amd_login_lock"))

    def step(self, name, title=None):
        s = {"name": name, "title": title or STEP_TITLES.get(name, name), "status": "ok", "summary": "",
             "counts": {}, "dollars": {}, "lines": [], "errors": [], "started": iso(), "ended": None}
        self.steps.append(s)
        return s

    def fail(self, s, msg):
        s["status"] = "failed"
        s["errors"].append(msg)
        self.errors.append("%s: %s" % (s["name"], msg))

    def warn(self, s, msg):
        if s["status"] == "ok":
            s["status"] = "warn"
        s["errors"].append(msg)

    @staticmethod
    def tail(text, n=12):
        lines = [l for l in text.strip().splitlines() if l.strip() and not l.startswith("$ ") and not l.startswith("(cwd ")]   # skip the log header
        return "\n".join(lines[-n:])

    # ------------------------------------------------------------------ workspace
    def bootstrap(self):
        s = self.step("bootstrap", "Workspace from the repository")
        ws = self.ws
        try:
            os.makedirs(ws, exist_ok=True)
        except OSError as ex:
            alt = os.path.join(os.path.expanduser("~"), "ehpa-billing", "unbilled")
            self.warn(s, "cannot create %s (%s) - using %s and re-pointing amd.py's cache paths" % (ws, ex, alt))
            os.makedirs(alt, exist_ok=True)
            self.ws = ws = alt
        for d in ("registers", "secrets", "patient_db", "era_details", "outbox", "inbox", "inbox/era"):
            os.makedirs(os.path.join(ws, d), exist_ok=True)
        n = 0
        groups = ["core", "billing/claims_center", "billing/era", "billing/rebill", "billing/writeoff", "billing/scans",
                  "eligibility", "credentialing", "boards", "claimocity", "scripts/helpers"]
        for g in groups:
            for f in sorted(glob.glob(os.path.join(REPO, g, "*.py"))):
                shutil.copy2(f, os.path.join(ws, os.path.basename(f)))
                n += 1
        for f in glob.glob(os.path.join(REPO, "boards", "templates", "*.html")):
            shutil.copy2(f, os.path.join(ws, os.path.basename(f)))
        for f in glob.glob(os.path.join(HERE, "*.py")):          # the button's own read-only helpers (outstanding_claims.py)
            if os.path.basename(f) != "run_all.py":
                shutil.copy2(f, os.path.join(ws, os.path.basename(f)))
        pe = os.path.join(REPO, "practices", "ehpa")
        for f in ("carriers.json", "facilities.json", "practice.json", "rules.md"):
            if os.path.exists(os.path.join(pe, f)):
                shutil.copy2(os.path.join(pe, f), os.path.join(ws, "registers", f))
        if os.path.exists(os.path.join(pe, "carriers.json")):
            shutil.copy2(os.path.join(pe, "carriers.json"), os.path.join(ws, "carriers.json"))
        regs = 0
        for f in glob.glob(os.path.join(pe, "registers", "*")):
            if os.path.isfile(f):
                dst = os.path.join(ws, "registers", os.path.basename(f))
                if not os.path.exists(dst) or os.path.getmtime(f) >= os.path.getmtime(dst):
                    shutil.copy2(f, dst)
                    regs += 1
        if os.path.exists(os.path.join(REPO, "docs", "captured_calls.md")):
            shutil.copy2(os.path.join(REPO, "docs", "captured_calls.md"), os.path.join(ws, "captured_calls.md"))
        # the helpers expect their session cache at the canonical path; when that path could not be made, re-point ONLY
        # the three path constants of the workspace copy of amd.py (the helper logic is untouched)
        if ws != CANON_WS:
            p = os.path.join(ws, "amd.py")
            t = open(p, encoding="utf-8").read().replace('"%s/' % CANON_WS, '"%s/' % ws.replace("\\", "/"))
            open(p, "w", encoding="utf-8").write(t)
        key = os.environ.get("STEDI_API_KEY")
        if key:
            kp = os.path.join(ws, "secrets", "stedi_live.key")
            open(kp, "w").write(key.strip() + "\n")
            try:
                os.chmod(kp, 0o600)
            except OSError:
                pass
        s["counts"] = {"helpers copied": n, "registers": regs, "python": " ".join(self.py)}
        s["summary"] = "%d helpers into %s" % (n, ws)
        if not os.environ.get("AMD_PSW") and not os.path.exists(os.path.join(ws, ".amd_cred.json")):
            self.fail(s, "AMD_PSW is not set and no .amd_cred.json exists - nothing can log in to AdvancedMD")
        if self.login_locked():
            self.fail(s, ".amd_login_lock exists - a prior login failed; a human must check the password and remove the lock")
        if not self.stedi:
            self.warn(s, "no STEDI_API_KEY - the Stedi steps (precheck, sweep) are skipped")
        s["ended"] = iso()
        return s["status"] != "failed"

    # ------------------------------------------------------------------ Claims Center columns
    def scan(self, tag):
        d = "scan_%s" % self.stamp
        rc, text, log = self.helper("columns_scan.py", [tag, d], timeout=1500)
        p = os.path.join(self.ws, d, "summary_%s.json" % tag)
        summ = json.load(open(p)) if os.path.exists(p) else None
        return rc, text, summ, d

    @staticmethod
    def counts_of(summ):
        if not summ:
            return {}
        insp = summ.get("inspector") or {}
        excl = summ.get("exclusions") or {}
        return {"charge_review": len(summ.get("chargereview") or []),
                "claim_inspector": sum(len(v) for v in insp.values()),
                "unbilled": len(summ.get("unbilled") or []),
                "exclusions": sum(len(v) for v in excl.values())}

    def columns(self):
        s = self.step("columns")
        rc, text, before, scandir = self.scan("before")
        if before is None:
            self.fail(s, "columns_scan before failed (rc %s): %s" % (rc, self.tail(text, 4)))
            if self.login_locked():
                self.fail(s, "the AMD login failed and tripped .amd_login_lock - no further AMD helper runs this run")
            s["ended"] = iso()
            return
        cb = self.counts_of(before)
        self.summary["columns"]["before"] = cb
        s["counts"].update({"charge review": cb["charge_review"], "claim inspector": cb["claim_inspector"],
                            "unbilled": cb["unbilled"], "exclusions": cb["exclusions"]})
        # what the inspector holds are (ids only) - advisories are bypassed by the helper, the rest is listed
        held = {}
        for bid, vs in (before.get("inspector") or {}).items():
            for v in vs:
                errs = v.get("errs") or []
                kinds = sorted({(e[2] or e[0] or "?") for e in errs})
                adv = all(any(pat in (e[2] or "") or pat in (e[1] or "") for pat in ADVISORY_ERR_PATTERNS) for e in errs) if errs else False
                held.setdefault("advisory" if adv else "missing data / dx", []).append("v%s" % v.get("vid"))
        for k, vids in held.items():
            s["lines"].append({"column": "claim inspector", "kind": k, "visits": len(vids), "ids": " ".join(vids[:25])})
        # Unbilled rows by error text, Exclusions by (carrier, error) - chart / visit ids only
        ub = {}
        for r in before.get("unbilled") or []:
            e = (r.get("_errs") or ["?"])[0][:70]
            ub.setdefault(e, []).append("v%s" % r.get("id"))
        for e, vids in sorted(ub.items(), key=lambda kv: -len(kv[1])):
            s["lines"].append({"column": "unbilled", "kind": e, "visits": len(vids), "ids": " ".join(vids[:25])})
        runs = []
        for rid, rows in (before.get("exclusions") or {}).items():
            if not rows:
                continue
            runs.append(rid)
            ex = {}
            for r in rows:
                car = (r.get("carriercode") or "?").split()[0]
                err = ((r.get("_errs") or [{}])[0].get("name") or (r.get("_errs") or [{}])[0].get("text") or "?")[:60]
                ex.setdefault((car, err), []).append("v%s" % r.get("id"))
            for (car, err), vids in sorted(ex.items(), key=lambda kv: -len(kv[1])):
                s["lines"].append({"column": "exclusions run %s" % rid, "kind": "%s %s" % (car, err), "visits": len(vids), "ids": " ".join(vids[:25])})
        # 2. Claim Inspector advisories (standing rule: bypass only when every error on the visit is an advisory)
        if self.exists("insp_bypass_advisories.py"):
            rc, text, log = self.helper("insp_bypass_advisories.py", [os.path.join(scandir, "summary_before.json")] + (["--live"] if self.live else []))
            m = re.search(r"plan: (\d+) visits? to bypass, (\d+) held", text)
            d_ = re.search(r"done=(\d+) failed=(\d+)", text)
            s["counts"]["inspector advisories to bypass"] = int(m.group(1)) if m else 0
            s["counts"]["inspector held (not advisory)"] = int(m.group(2)) if m else 0
            if self.live and d_:
                s["counts"]["inspector bypasses sent"] = int(d_.group(1))
                if int(d_.group(2)):
                    self.warn(s, "%s inspector bypass(es) failed" % d_.group(2))
            if rc != 0:
                self.warn(s, "insp_bypass_advisories rc %s: %s" % (rc, self.tail(text, 3)))
        else:
            self.warn(s, "insp_bypass_advisories.py missing - inspector advisories left as they are")
        # 3. Unbilled: the two row types the standing rules allow without new data, then the ERA-linked re-posts
        if self.exists("unbilled_repair.py"):
            rc, text, log = self.helper("unbilled_repair.py", ["--live"] if self.live else [])
            rows = []
            for l in text.splitlines():
                if l.startswith("{"):
                    try:
                        rows.append(json.loads(l))
                    except ValueError:
                        pass
            m = re.search(r"SUMMARY reason rows (\d+), prior rows (\d+), left alone (\d+)", text)
            if m:
                s["counts"]["unbilled reason-code rows"] = int(m.group(1))
                s["counts"]["unbilled prior-payor rows"] = int(m.group(2))
                s["counts"]["unbilled rows left alone"] = int(m.group(3))
            s["counts"]["unbilled released" if self.live else "unbilled releasable"] = sum(
                1 for r in rows if "releas" in str(r.get("outcome", "")).lower() and "held" not in str(r.get("outcome", "")).lower())
            held_money = sum(1 for r in rows if "held" in str(r.get("outcome", "")).lower())
            if held_money:
                self.waiting.append("Unbilled: %d reason-code row(s) whose code-less payment carries money - the ERA-linked re-post needs the era_details cache line" % held_money)
            if rc != 0:
                self.warn(s, "unbilled_repair rc %s: %s" % (rc, self.tail(text, 3)))
        if self.exists("payreasons.py"):
            rc, text, log = self.helper("payreasons.py", ["--unbilled", "--live"] if self.live else ["--list"])
            if rc != 0:
                self.warn(s, "payreasons rc %s: %s" % (rc, self.tail(text, 3)))
            else:
                m = re.search(r"SUMMARY: \{(.*)\}", text)
                if m:
                    for k, v in re.findall(r"'([^']+)':\s*(\d+)", m.group(1)):
                        s["counts"]["payreasons %s" % k] = int(v)
        # 4. Exclusions: duplicate-claim completions and the Florida Blue Medigap crossover rule, per claim run
        for rid in runs:
            for helper in ("excl_dup_complete.py", "excl_crossover_complete.py"):
                if not self.exists(helper):
                    continue
                rc, text, log = self.helper(helper, ["--scan", scandir, "--run", rid] + (["--live"] if self.live else []))
                k = "%s run %s" % (helper.replace("_complete.py", "").replace("excl_", "exclusions "), rid)
                m = re.search(r"run \S+: (\d+) duplicate-claim exclusion rows", text)
                done = len(re.findall(r"(?mi)^\s*(?:COMPLETE|COMPLETED|hideexclusions)\b", text))
                s["counts"][k] = done if done else (int(m.group(1)) if m else ("nothing to complete" if "nothing to complete" in text else "see log"))
                if rc != 0 and "nothing to complete" not in text:
                    self.warn(s, "%s run %s rc %s: %s" % (helper, rid, rc, self.tail(text, 3)))
        # 5. rescan
        rc, text, after, _ = self.scan("after")
        ca = self.counts_of(after) if after else dict(cb)
        self.summary["columns"]["after"] = ca
        s["summary"] = "CR %s->%s, CI %s->%s, Unbilled %s->%s, Exclusions %s->%s" % (
            cb["charge_review"], ca["charge_review"], cb["claim_inspector"], ca["claim_inspector"],
            cb["unbilled"], ca["unbilled"], cb["exclusions"], ca["exclusions"])
        if cb["charge_review"]:
            self.waiting.append("Charge Review: %d visit(s) - the CCM / modifier-25 gate and approvecharges are a chat-session step" % cb["charge_review"])
        if held.get("missing data / dx"):
            self.waiting.append("Claim Inspector: %d visit(s) with missing-data / diagnosis holds (admission date, dx order, CCI) - chat session or William" % len(held["missing data / dx"]))
        s["ended"] = iso()

    # ------------------------------------------------------------------ ERA
    def era_list(self, tag):
        rc, text, log = self.helper("era_list.py", [tag, self.stamp], timeout=1500)
        p = os.path.join(self.ws, "registers", "era_checks_%s_%s.json" % (tag, self.stamp))
        rows = []
        if os.path.exists(p):
            try:
                j = json.load(open(p))
                rows = j if isinstance(j, list) else (j.get("erachecks") or j.get("checks") or j.get("data") or j.get("rows") or [])
            except ValueError:
                rows = []
        if not rows and rc == 0:
            # fall back to the printed lines
            for m in re.finditer(r"check (\S+)\s+payer=([^/]*) / ([^ ]*)\s+checknumber=(\S+).*?amount=([\d.]+)\s+unposted=(\S+)", text):
                rows.append({"id": m.group(1), "eracarriername": m.group(2).strip(), "systemcarriername": m.group(3), "checknumber": m.group(4),
                             "checkamount": float(m.group(5)), "unpostedamount": None if m.group(6) == "None" else float(m.group(6))})
        tot = sum(money(c.get("unpostedamount") if c.get("unpostedamount") is not None else c.get("checkamount") or c.get("amount")) for c in rows)
        return rc, text, rows, {"checks": len(rows), "unposted": round(tot, 2)}

    def era(self):
        s = self.step("era")
        # (a) 835 files dropped in the workspace inbox (the desktop app's folder; the cloud runner has none)
        files = [f for f in glob.glob(os.path.join(self.ws, "inbox", "era", "*")) if os.path.isfile(f)]
        if files and self.exists("era_upload.py"):
            rc, text, log = self.helper("era_upload.py", [os.path.join(self.ws, "inbox", "era")], env={"ERA_DRY": "" if self.live else "1"})
            s["counts"]["835 files in inbox"] = len(files)
            if rc != 0:
                self.warn(s, "era_upload rc %s: %s" % (rc, self.tail(text, 3)))
        rc, text, before, cb = self.era_list("before")
        if rc != 0 and not before:
            self.fail(s, "era_list before failed (rc %s): %s" % (rc, self.tail(text, 4)))
            s["ended"] = iso()
            return
        self.summary["era"]["before"] = cb
        for c in before:
            s["lines"].append({"check": c.get("id"), "payer": (c.get("systemcarriername") or c.get("eracarriername") or "")[:30],
                               "checknumber": c.get("checknumber") or c.get("paymentnumber"), "amount": money(c.get("checkamount") or c.get("amount")),
                               "unposted": money(c.get("unpostedamount")), "stage": "before"})
        # (c) the Post button over every check with money, (e) era_clear: $0 process-accepted lines, dismiss settled checks, hold money
        if self.exists("era_post.py"):
            rc, text, log = self.helper("era_post.py", ["--all-unposted"] + ([] if self.live else ["--dry"]), timeout=3000)
            posted = re.findall(r"(?i)posted[^\n$]*\$?\s*([\d,]+\.\d\d)", text)
            s["counts"]["era_post lines"] = len(re.findall(r"(?m)^\s*(?:POST|posted|OK)\b", text))
            if rc != 0:
                self.warn(s, "era_post rc %s: %s" % (rc, self.tail(text, 3)))
        if self.exists("era_clear.py"):
            rc, text, log = self.helper("era_clear.py", [] if self.live else ["--dry"], timeout=3000)
            s["counts"]["checks dismissed"] = len(re.findall(r"(?m)^\s*DISMISS\b", text))
            s["counts"]["checks held"] = len(re.findall(r"(?m)^\s*HOLD\b", text))
            for m in re.finditer(r"(?m)^\s*HOLD (\S+)(.*)$", text):
                self.waiting.append("ERA check %s held by era_clear:%s" % (m.group(1), m.group(2)[:90]))
            if rc != 0:
                self.warn(s, "era_clear rc %s: %s" % (rc, self.tail(text, 3)))
            rev = sorted(glob.glob(os.path.join(self.ws, "era_clear_reversal_*.json")))
            if rev:
                self.waiting.append("era_clear wrote %s - write-offs to reverse before the payer's money can post (wo_reversal_post.py)" % os.path.basename(rev[-1]))
        rc, text, after, ca = self.era_list("after")
        if not after and rc != 0:
            ca = dict(cb)
        self.summary["era"]["after"] = ca
        pay = round(max(0.0, cb["unposted"] - ca["unposted"]), 2) if self.live else 0.0
        self.summary["posted"]["pay"] = pay
        s["dollars"] = {"unposted before": cb["unposted"], "unposted after": ca["unposted"], "posted this run": pay}
        s["summary"] = "%d checks / $%.2f -> %d checks / $%.2f%s" % (cb["checks"], cb["unposted"], ca["checks"], ca["unposted"], "" if self.live else " (dry - nothing posted)")
        s["ended"] = iso()

    # ------------------------------------------------------------------ cascade
    def cascade(self):
        s = self.step("cascade")
        if self.exists("void_rules.py"):
            if os.path.exists(os.path.join(self.ws, "void_rules.json")):
                rc, text, log = self.helper("void_rules.py", [] if self.live else ["--dry"])
                s["counts"]["void-on-arrival matches"] = len(re.findall(r"(?m)^VOID ", text))
                if rc != 0:
                    self.warn(s, "void_rules rc %s: %s" % (rc, self.tail(text, 3)))
            else:
                s["counts"]["void rules"] = "void_rules.json not in this workspace (Drive 'workspace mirror') - skipped"
        if not self.stedi:
            self.warn(s, "no Stedi key - precheck skipped")
        elif self.exists("precheck.py"):
            rc, text, log = self.helper("precheck.py", ["--days", "3", "--max", "120"], timeout=2400)
            today = datetime.date.today().strftime("%Y%m%d")
            p = os.path.join(self.ws, "precheck_%s.json" % today)
            flags = {}
            if os.path.exists(p):
                try:
                    j = json.load(open(p))
                    rows = j if isinstance(j, list) else (j.get("rows") or j.get("flags") or j.get("results") or [])
                    for r in rows:
                        if not isinstance(r, dict):
                            continue
                        f = str(r.get("flag") or r.get("verdict") or r.get("status") or "")[:40]
                        if not f or f.upper().startswith(("ACTIVE", "OK")):
                            continue
                        flags.setdefault(f, []).append("pat%s" % r.get("patientid", r.get("pid", "?")))
                except ValueError:
                    pass
            s["counts"]["precheck flagged charts"] = sum(len(v) for v in flags.values())
            for f, pids in flags.items():
                s["lines"].append({"flag": f, "charts": len(pids), "ids": " ".join(sorted(set(pids))[:20])})
                self.waiting.append("precheck '%s' on %d chart(s) - the chart fix is a chat-session step (cascade rule)" % (f, len(set(pids))))
            if rc != 0:
                self.warn(s, "precheck rc %s: %s" % (rc, self.tail(text, 3)))
        s["summary"] = "; ".join("%s: %s" % kv for kv in s["counts"].items()) or "nothing to do"
        s["ended"] = iso()

    # ------------------------------------------------------------------ sweep
    def sweep(self):
        s = self.step("sweep")
        if not self.stedi:
            self.warn(s, "no Stedi key - sweep skipped")
            s["status"] = "skipped"
            s["ended"] = iso()
            return
        minage = (datetime.date.today() - datetime.date(2026, 5, 1)).days
        rc, text, log = self.helper("claim_status_sweep.py", ["--min-age", str(minage), "--max", "60", "--carriers", "UNI20,BCBS"], timeout=2400)
        today = datetime.date.today().strftime("%Y%m%d")
        p = os.path.join(self.ws, "claimstatus_%s.json" % today)
        if os.path.exists(p):
            try:
                rows = json.load(open(p))
                acts = {}
                for r in rows if isinstance(rows, list) else []:
                    acts.setdefault(str(r.get("action", "?"))[:40], []).append("v%s" % r.get("visitid"))
                for a_, vids in acts.items():
                    s["counts"][a_] = len(vids)
                    s["lines"].append({"action": a_, "visits": len(vids), "ids": " ".join(vids[:25])})
                if self.exists("sweep_register.py"):
                    self.helper("sweep_register.py", [p, self.stamp, "button"])
            except ValueError:
                self.warn(s, "claimstatus file unreadable")
        if rc != 0:
            self.warn(s, "claim_status_sweep rc %s: %s" % (rc, self.tail(text, 3)))
        s["summary"] = "; ".join("%s: %s" % kv for kv in s["counts"].items()) or "no answers"
        s["ended"] = iso()

    # ------------------------------------------------------------------ approval packages
    def packages(self):
        s = self.step("packages")
        reg_repo = os.path.join(REPO, "practices", "ehpa", "registers", "approvals_pending.json")
        reg_ws = os.path.join(self.ws, "registers", "approvals_pending.json")
        try:
            d = json.load(open(reg_repo))
        except (OSError, ValueError) as ex:
            self.fail(s, "approvals register unreadable: %s" % ex)
            s["ended"] = iso()
            return
        items = d["items"] if isinstance(d, dict) else d
        want = set(x for x in (self.a.packages or "").split(",") if x)
        chosen = [i for i in items if (i.get("id") in want) or (not want and i.get("status") == "approved")]
        # the page marks a card approved in its own store; the register copy may still say waiting - --packages names them explicitly
        if not chosen:
            s["summary"] = "no approved package in the register%s" % (" (none of %s found)" % ",".join(sorted(want)) if want else "")
            s["ended"] = iso()
            return
        changed = False
        for it in chosen:
            pid = it.get("id")
            cmd = str(it.get("cmd") or "")
            rec = {"id": pid, "status": it.get("status"), "dollars": it.get("dollars", ""), "result": ""}
            self.pkg_rows.append(rec)
            if it.get("status") == "done":
                rec["result"] = "already done - skipped"
                self.summary["packages"]["skipped"] += 1
                continue
            if it.get("status") == "declined":
                rec["result"] = "declined on the page - skipped"
                self.summary["packages"]["skipped"] += 1
                continue
            m = re.search(r"python3?\s+(\S+\.py)(.*)$", cmd)
            if not m:
                rec["result"] = "no python command in the card"
                self.summary["packages"]["skipped"] += 1
                continue
            script, rest = m.group(1), m.group(2).strip()
            argv = rest.split()
            if not self.exists(script):
                rec["result"] = "script %s is not in the repository - cannot run (the card's session never committed it)" % script
                self.summary["packages"]["refused"] += 1
                self.waiting.append("package %s: %s missing" % (pid, script))
                continue
            dry_argv = [("--dry" if x == "--live" else x) for x in argv]
            if "--live" not in argv and "--dry" not in dry_argv:
                dry_argv = dry_argv + ["--dry"]
            rc, text, log = self.helper(script, dry_argv, timeout=1800)
            if rc != 0:
                rec["result"] = "dry run failed (rc %s): %s" % (rc, self.tail(text, 2)[:160])
                self.summary["packages"]["refused"] += 1
                continue
            if not self.live:
                rec["result"] = "dry run ok - not applied (dry mode)"
                self.summary["packages"]["skipped"] += 1
                continue
            it["note"] = "applying %s (billing button)" % self.stamp
            rc, text, log = self.helper(script, argv, timeout=2400)
            if rc == 0:
                it["status"] = "done"
                it["answer"] = "%s applied by the billing button run %s (dry run first, then live; log %s)" % (iso(), self.stamp, os.path.basename(log))
                it["note"] = "applied %s (billing button)" % self.stamp
                rec["status"] = "done"
                rec["result"] = "applied"
                self.summary["packages"]["applied"] += 1
            else:
                it["note"] = "%s: billing button run failed rc %s - left approved" % (self.stamp, rc)
                rec["result"] = "live run failed (rc %s): %s" % (rc, self.tail(text, 2)[:160])
                self.summary["packages"]["refused"] += 1
            changed = True
        if changed:
            for p in (reg_repo, reg_ws):
                try:
                    json.dump(d, open(p, "w"), indent=1)
                except OSError:
                    pass
        s["counts"] = dict(self.summary["packages"])
        s["summary"] = "%d applied, %d refused / failed, %d skipped" % (self.summary["packages"]["applied"], self.summary["packages"]["refused"], self.summary["packages"]["skipped"])
        if self.summary["packages"]["refused"]:
            s["status"] = "warn"
        s["ended"] = iso()

    # ------------------------------------------------------------------ credentialing + money
    def cred(self):
        s = self.step("cred")
        if not self.exists("cred_check.py"):
            s["status"] = "skipped"
            s["ended"] = iso()
            return
        rc, text, log = self.helper("cred_check.py", [], timeout=900)
        s["summary"] = self.tail(text, 4).replace("\n", " | ")[:300]
        if rc != 0:
            self.warn(s, "cred_check rc %s: %s" % (rc, self.tail(text, 3)))
        s["ended"] = iso()

    def money_step(self):
        s = self.step("money")
        if os.path.exists(os.path.join(self.ws, "patient_universe_0907.json")) and self.exists("pay_scan.py"):
            rc, text, log = self.helper("pay_scan.py", [], timeout=5400)
            if rc != 0:
                self.warn(s, "pay_scan rc %s: %s" % (rc, self.tail(text, 3)))
        else:
            s["counts"]["payments scan"] = "patient_universe_0907.json not in this workspace - skipped"
        if self.exists("build_money.py"):
            rc, text, log = self.helper("build_money.py", [], timeout=1800)
            s["summary"] = self.tail(text, 1)[:200]
            if rc != 0:
                self.warn(s, "build_money rc %s: %s" % (rc, self.tail(text, 3)))
            else:
                p = os.path.join(self.ws, "money_data.json")
                if os.path.exists(p):
                    try:
                        j = json.load(open(p))
                        s["dollars"] = {"unpaid total": money(j.get("unpaid_total")), "era paid": money((j.get("era") or {}).get("paid"))}
                    except ValueError:
                        pass
                    shutil.copy2(os.path.join(self.ws, "money_ledger.html"), os.path.join(self.out, "money_ledger_%s.html" % self.stamp)) if os.path.exists(os.path.join(self.ws, "money_ledger.html")) else None
        s["ended"] = iso()

    def outstanding(self):
        """Read-only: the whole unpaid list summed up (ids and dollars only) -> reports/button/outstanding_latest.json."""
        s = self.step("outstanding")
        rc, text, log = self.helper("outstanding_claims.py", ["--out", "outstanding_claims.json"], timeout=900)
        p = os.path.join(self.ws, "outstanding_claims.json")
        if rc != 0 or not os.path.exists(p):
            self.fail(s, "outstanding_claims rc %s: %s" % (rc, self.tail(text, 3)))
            s["ended"] = iso()
            return
        j = json.load(open(p))
        s["dollars"] = {"open insurance balance": j.get("total", 0), "over 365 days": (j.get("over_365") or {}).get("dollars", 0)}
        s["counts"] = {"visits": j.get("visits"), "charts": j.get("charts"), "over 365 days": (j.get("over_365") or {}).get("n")}
        for c in (j.get("by_carrier") or [])[:12]:
            s["lines"].append({"carrier": c["carrier"], "name": c.get("name", "")[:28], "visits": c["n"], "dollars": c["dollars"], "oldest_days": c.get("oldest_days")})
        s["summary"] = "%s visits on %s charts, $%.2f open; %s over a year ($%.2f)" % (j.get("visits"), j.get("charts"), j.get("total", 0), (j.get("over_365") or {}).get("n"), (j.get("over_365") or {}).get("dollars", 0))
        self.summary["outstanding"] = {"total": j.get("total", 0), "visits": j.get("visits"), "charts": j.get("charts"), "over_365": j.get("over_365")}
        os.makedirs(self.out, exist_ok=True)
        shutil.copy2(p, os.path.join(self.out, "outstanding_latest.json"))
        s["ended"] = iso()

    def aging(self):
        """Read-only: A/R aging by payer and days-since-sent with William's standing recommendation per visit (chart + visit ids only)
        -> reports/button/aging_latest.json. William 10/15/2026: the AR Aging page's Refresh button runs this step and pulls the file back."""
        s = self.step("aging")
        rc, text, log = self.helper("aging_refresh.py", ["--out", "aging_latest.json", "--threads", "4"], timeout=3000)
        p = os.path.join(self.ws, "aging_latest.json")
        if rc != 0 or not os.path.exists(p):
            self.fail(s, "aging_refresh rc %s: %s" % (rc, self.tail(text, 3)))
            s["ended"] = iso()
            return
        j = json.load(open(p))
        s["counts"] = {"visits": j.get("visits"), "patients": j.get("patients"), "charts read": j.get("charts_read")}
        s["counts"].update({"sent " + k: v.get("n") for k, v in (j.get("by_bucket_sent") or {}).items() if v.get("n")})
        s["dollars"] = {"open insurance balance": j.get("total", 0)}
        s["dollars"].update({k: v.get("amt", 0) for k, v in (j.get("by_rec") or {}).items() if v.get("n")})
        for k, v in list((j.get("by_payer") or {}).items())[:12]:
            s["lines"].append({"payer": k, "visits": v.get("n"), "dollars": v.get("amt"), "over_120": (v.get("b") or {}).get("over 120", [0, 0])[1]})
        if j.get("errors"):
            self.warn(s, "%d chart reads failed (see the log)" % len(j["errors"]))
        br = j.get("by_rec") or {}
        s["summary"] = "%s visits / %s charts, $%.2f open: WAIT $%.2f, CORRECT & RESEND $%.2f, WRITE OFF $%.2f" % (
            j.get("visits"), j.get("patients"), j.get("total", 0), (br.get("WAIT") or {}).get("amt", 0), (br.get("CORRECT & RESEND") or {}).get("amt", 0), (br.get("WRITE OFF") or {}).get("amt", 0))
        self.summary["aging"] = {"total": j.get("total", 0), "visits": j.get("visits"), "asof": j.get("asof"), "by_rec": br}
        os.makedirs(self.out, exist_ok=True)
        shutil.copy2(p, os.path.join(self.out, "aging_latest.json"))
        s["ended"] = iso()

    def denials(self):
        """Read-only: the Working Denials board's live rebuild (chart + visit ids only) -> reports/button/working_denials_latest.json.
        William 10/13/2026: the board's Refresh button runs this step and pulls the file back."""
        s = self.step("denials")
        prior = os.path.join(self.out, "working_denials_latest.json")      # the last snapshot carries the board's visit list forward
        argv = ["--out", "working_denials_latest.json"] + (["--prior", prior] if os.path.exists(prior) else [])
        rc, text, log = self.helper("denials_refresh.py", argv, timeout=2400)
        p = os.path.join(self.ws, "working_denials_latest.json")
        if rc != 0 or not os.path.exists(p):
            self.fail(s, "denials_refresh rc %s: %s" % (rc, self.tail(text, 3)))
            s["ended"] = iso()
            return
        j = json.load(open(p))
        s["counts"] = {"charts read": j.get("charts_read"), "denial lines": j.get("total_lines"), "visits": j.get("total_visits"),
                       "actionable": j.get("actionable_visits"), "inside 12 months": j.get("timely_visits")}
        s["counts"].update({"status " + k: v for k, v in (j.get("bystatus") or {}).items()})
        s["dollars"] = {"actionable": j.get("actionable_amt", 0), "inside 12 months": j.get("timely_amt", 0), "resubmitted": j.get("resub_amt", 0), "resolved since": j.get("resolved_amt", 0)}
        for k, v in sorted((j.get("summary") or {}).items(), key=lambda kv: -kv[1].get("amt", 0)):
            s["lines"].append({"disposition": k, "visits": v.get("visits"), "dollars": v.get("amt"), "patients": v.get("patients")})
        if j.get("errors"):
            self.warn(s, "%d chart reads failed (see the log)" % len(j["errors"]))
        s["summary"] = "%s denied visits on %s charts; %s actionable $%.2f (%s inside 12 months $%.2f); %s" % (
            j.get("total_visits"), j.get("charts_read"), j.get("actionable_visits"), j.get("actionable_amt", 0), j.get("timely_visits"), j.get("timely_amt", 0),
            ", ".join("%s %s" % (k, v) for k, v in (j.get("bystatus") or {}).items()))
        self.summary["denials"] = {"visits": j.get("total_visits"), "actionable": j.get("actionable_visits"), "actionable_amt": j.get("actionable_amt"), "asof": j.get("asof")}
        os.makedirs(self.out, exist_ok=True)
        gate = os.path.join(REPO, "tools", "mirror", "phi_gate.py")
        dst = os.path.join(self.out, "working_denials_latest.json")
        if os.path.exists(gate):
            g = subprocess.run([sys.executable, gate, p, dst], capture_output=True, text=True, cwd=REPO)
            open(os.path.join(self.logdir, "phi_gate_denials.log"), "w").write(g.stdout + g.stderr)
            if g.returncode != 0 or not os.path.exists(dst):
                self.fail(s, "phi_gate refused the denials snapshot (rc %s) - not published" % g.returncode)
                s["ended"] = iso()
                return
        else:
            shutil.copy2(p, dst)
        s["ended"] = iso()

    # ------------------------------------------------------------------ report
    def report(self, status, headline):
        rep = {"schema": SCHEMA, "stamp": self.stamp, "mode": self.mode, "status": status, "headline": headline,
               "note": self.a.note or "", "run_url": self.a.run_url or "", "started": self.started, "ended": iso(),
               "summary": self.summary, "steps": self.steps, "packages": self.pkg_rows, "waiting": self.waiting, "errors": self.errors}
        os.makedirs(self.out, exist_ok=True)
        raw = os.path.join(self.logdir, "report_raw.json")
        json.dump(rep, open(raw, "w"), indent=1, default=str)
        final = os.path.join(self.out, "%s.json" % self.stamp)
        gate = os.path.join(REPO, "tools", "mirror", "phi_gate.py")
        ok = False
        if os.path.exists(gate):
            p = subprocess.run([sys.executable, gate, raw, final], capture_output=True, text=True, cwd=REPO)
            open(os.path.join(self.logdir, "phi_gate.log"), "w").write(p.stdout + p.stderr)
            ok = p.returncode == 0 and os.path.exists(final)
            if not ok:
                self.say("phi_gate blocked the full report (rc %s) - writing a counts-only report" % p.returncode)
        if not ok:
            slim = dict(rep)
            slim["steps"] = [{k: v for k, v in st.items() if k != "lines"} for st in self.steps]
            slim["waiting"] = ["%d item(s) - see the run log" % len(self.waiting)] if self.waiting else []
            slim["errors"] = ["%d error(s) - see the run log" % len(self.errors)] if self.errors else []
            slim["note"] = (slim["note"] + " | " if slim["note"] else "") + "detail lines withheld by the privacy gate"
            json.dump(slim, open(final, "w"), indent=1, default=str)
        shutil.copy2(final, os.path.join(self.out, "latest.json"))
        self.say("report -> %s" % final)
        return final

    # ------------------------------------------------------------------ main
    def main(self):
        self.started = iso()
        steps = self.a.steps
        if self.a.profile:
            want = PROFILES[self.a.profile]
        elif not steps or steps == "all":
            want = PROFILES["all"]
        else:
            want = [x.strip() for x in steps.split(",") if x.strip()]
        self.say("billing button run %s - mode %s - steps %s" % (self.stamp, self.mode, ",".join(want)))
        if not self.bootstrap():
            return self.report("failed", "workspace bootstrap failed: " + "; ".join(self.errors))
        order = ["columns", "era", "cascade", "sweep", "packages", "cred", "money", "outstanding", "denials", "aging"]
        for name in order:
            if name not in want:
                continue
            if name in ("columns", "era", "cascade", "sweep", "packages", "money", "outstanding", "denials", "aging") and self.login_locked():
                s = self.step(name)
                self.fail(s, "skipped - the AMD login lock is tripped")
                s["ended"] = iso()
                continue
            try:
                getattr(self, "money_step" if name == "money" else name)()
            except Exception as ex:  # a step crash never stops the others
                s = self.steps[-1] if self.steps and self.steps[-1]["name"] == name else self.step(name)
                self.fail(s, "crashed: %s" % ex)
                open(os.path.join(self.logdir, "crash_%s.log" % name), "w").write(traceback.format_exc())
                s["ended"] = iso()
        failed = [s for s in self.steps if s["status"] == "failed"]
        status = "failed" if failed and len(failed) == len([s for s in self.steps if s["name"] != "bootstrap"]) else ("warn" if failed or any(s["status"] == "warn" for s in self.steps) else "ok")
        c = self.summary["columns"]
        e = self.summary["era"]
        parts = []
        if c["before"]:
            parts.append("Columns %s/%s/%s/%s -> %s/%s/%s/%s" % (c["before"].get("charge_review", "-"), c["before"].get("claim_inspector", "-"), c["before"].get("unbilled", "-"), c["before"].get("exclusions", "-"),
                                                                   c["after"].get("charge_review", "-"), c["after"].get("claim_inspector", "-"), c["after"].get("unbilled", "-"), c["after"].get("exclusions", "-")))
        if e["before"]:
            parts.append("ERA %s checks $%.2f -> %s checks $%.2f" % (e["before"].get("checks", "-"), e["before"].get("unposted", 0), e["after"].get("checks", "-"), e["after"].get("unposted", 0)))
        pk = self.summary["packages"]
        if pk["applied"] or pk["refused"] or pk["skipped"]:
            parts.append("packages %d applied / %d refused / %d skipped" % (pk["applied"], pk["refused"], pk["skipped"]))
        ag = self.summary.get("aging") or {}
        if ag.get("visits"):
            br = ag.get("by_rec") or {}
            parts.append("Aging %s visits $%.2f open: wait $%.2f / resend $%.2f / write off $%.2f" % (ag["visits"], ag.get("total", 0),
                         (br.get("WAIT") or {}).get("amt", 0), (br.get("CORRECT & RESEND") or {}).get("amt", 0), (br.get("WRITE OFF") or {}).get("amt", 0)))
        headline = ("; ".join(parts) or "nothing ran") + ("" if self.live else " (dry run - nothing written)")
        return self.report(status, headline)


def parse():
    ap = argparse.ArgumentParser(description="ehpa Billing Button engine")
    ap.add_argument("--mode", choices=["dry", "live"], default="dry")
    ap.add_argument("--steps", default="all", help="comma list of columns,era,cascade,sweep,packages,cred,money,outstanding or 'all'")
    ap.add_argument("--profile", choices=sorted(PROFILES), help="a named step set (overrides --steps)")
    ap.add_argument("--packages", default="", help="comma list of approval package ids to apply (default: every approved one)")
    ap.add_argument("--out", default=os.path.join(REPO, "reports", "button"))
    ap.add_argument("--ws", default=None, help="workspace path (default %s)" % CANON_WS)
    ap.add_argument("--stamp", default=None)
    ap.add_argument("--note", default="")
    ap.add_argument("--run-url", default="")
    ap.add_argument("--python", default=None, help="interpreter for the helpers (default: this one)")
    ap.add_argument("--stedi-proxy", action="store_true", help="the environment injects the Stedi key at a proxy (no key file needed)")
    return ap.parse_args()


if __name__ == "__main__":
    a = parse()
    r = Run(a)
    final = r.main()
    rep = json.load(open(final))
    print(json.dumps({"stamp": rep["stamp"], "mode": rep["mode"], "status": rep["status"], "headline": rep["headline"], "report": final}))
    sys.exit(0 if rep["status"] != "failed" else 1)
