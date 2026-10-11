#!/usr/bin/env python3
# PLAIN ENGLISH (the ehpa Billing Button desktop app - William 10/11/2026: "a dashboard app separate from Claude, an app button
#   on the desktop, Midnight theme, I press the manual bill button and it runs all the scripts - the columns and the nightly
#   cascade - without approval buttons")
# What it is: a small program installed on the PC. It opens a window (the dashboard, desktop/ui.html), downloads the newest
#   copy of this repository from GitHub, and when the Manual Bill button is pressed runs tools/button/run_all.py - the same
#   engine the GitHub Actions workflow and the artifacts' Run buttons use - right here on the PC with the password typed into
#   its settings. The report appears in the window; every report is kept under the app's data folder.
# Two other jobs of the same program: (1) `ehpa-billing-button.exe --py <script> [args]` runs a helper script with the Python
#   bundled inside the app (so the PC needs no Python install) - that is how run_all.py runs the helpers; (2) a link of the form
#   ehpa-billing://run?mode=dry|live (the Run button on the billing artifacts) opens the app and starts that run.
# Decides: nothing about billing - the engine and the helpers do, by the standing rules in the repository.
# Never touches: the repository (it only downloads it), the Claude routines, any file outside its data folder and the
#   workspace folder the helpers expect (C:\home\claude\unbilled on Windows).
import http.server, json, os, platform, re, shutil, socket, subprocess, sys, threading, time, urllib.parse, urllib.request, webbrowser, zipfile

APP = "ehpa Billing Button"
OWNER, REPO_NAME = "dreffinger", "effinger-billing-backend"
WORKFLOW = "billing-button.yml"
FROZEN = getattr(sys, "frozen", False)
HERE = os.path.dirname(os.path.abspath(sys.executable if FROZEN else __file__))
RES = getattr(sys, "_MEIPASS", HERE)                      # where PyInstaller unpacks ui.html
DATA = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "ehpa-billing") if platform.system() == "Windows" \
    else os.path.join(os.path.expanduser("~"), ".ehpa-billing")
REPO = os.path.join(DATA, "repo")
REPORTS = os.path.join(DATA, "reports")
SETTINGS = os.path.join(DATA, "settings.json")
STATE = {"running": False, "mode": None, "started": None, "log": [], "last_rc": None, "last_report": None, "heartbeat": 0.0, "update": ""}
LOCK = threading.Lock()


# ----------------------------------------------------------------------------- interpreter mode: run a helper with the bundled Python
def run_as_python(argv):
    """`app --py script.py args...` - behave like `python3 script.py args...` for the helpers (flat imports from the script's folder)."""
    import runpy
    script = argv[0]
    sys.argv = [script] + argv[1:]
    d = os.path.dirname(os.path.abspath(script))
    if d not in sys.path:
        sys.path.insert(0, d)
    if os.getcwd() not in sys.path:
        sys.path.insert(0, os.getcwd())
    # a windowed PyInstaller build turns an uncaught exception into a modal dialog that waits for a click - the engine would
    # sit on the helper until its timeout. Print the traceback where the engine's log file can see it and exit non-zero instead.
    try:
        runpy.run_path(script, run_name="__main__")
    except SystemExit:
        raise
    except BaseException:
        import traceback
        if sys.stderr is not None:
            traceback.print_exc()
        sys.exit(1)


# ----------------------------------------------------------------------------- settings
def load_settings():
    try:
        return json.load(open(SETTINGS, encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_settings(s):
    os.makedirs(DATA, exist_ok=True)
    json.dump(s, open(SETTINGS, "w", encoding="utf-8"), indent=1)
    try:
        os.chmod(SETTINGS, 0o600)
    except OSError:
        pass


# ----------------------------------------------------------------------------- GitHub
def gh(path, token, method="GET", body=None, raw=False):
    req = urllib.request.Request("https://api.github.com" + path, method=method,
                                 headers={"Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
                                          "X-GitHub-Api-Version": "2022-11-28", "User-Agent": APP})
    if body is not None:
        req.data = json.dumps(body).encode()
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
        return data if raw else (json.loads(data) if data else None)


def update_repo(token):
    """Download main as a zip and unpack it into DATA/repo (the previous copy is replaced only after the download succeeded)."""
    if not token:
        raise RuntimeError("no GitHub token saved - open Settings")
    os.makedirs(DATA, exist_ok=True)
    z = os.path.join(DATA, "main.zip")
    open(z, "wb").write(gh("/repos/%s/%s/zipball/main" % (OWNER, REPO_NAME), token, raw=True))
    tmp = os.path.join(DATA, "repo_new")
    shutil.rmtree(tmp, ignore_errors=True)
    with zipfile.ZipFile(z) as zf:
        zf.extractall(tmp)
    inner = [d for d in os.listdir(tmp) if os.path.isdir(os.path.join(tmp, d))]
    if not inner:
        raise RuntimeError("the zip was empty")
    src = os.path.join(tmp, inner[0])
    keep = os.path.join(REPO, "practices", "ehpa", "registers", "approvals_pending.json")
    kept = open(keep, encoding="utf-8").read() if os.path.exists(keep) else None
    shutil.rmtree(REPO, ignore_errors=True)
    shutil.move(src, REPO)
    shutil.rmtree(tmp, ignore_errors=True)
    os.remove(z)
    head = gh("/repos/%s/%s/commits/main" % (OWNER, REPO_NAME), token)
    note = "%s %s" % (head["sha"][:7], (head["commit"]["message"].splitlines() or [""])[0][:100])
    open(os.path.join(REPO, ".button_head"), "w", encoding="utf-8").write(note)
    return note


def repo_head():
    p = os.path.join(REPO, ".button_head")
    return open(p, encoding="utf-8").read().strip() if os.path.exists(p) else ""


# ----------------------------------------------------------------------------- the run
def log(line):
    with LOCK:
        STATE["log"].append("[%s] %s" % (time.strftime("%H:%M:%S"), line))
        STATE["log"] = STATE["log"][-400:]


def engine_cmd(mode, steps, packages):
    eng = os.path.join(REPO, "tools", "button", "run_all.py")
    if not os.path.exists(eng):
        raise RuntimeError("tools/button/run_all.py is not in the downloaded repository - press 'Update scripts' first")
    base = [sys.executable, "--py"] if FROZEN else [sys.executable]
    argv = base + [eng, "--mode", mode, "--steps", steps or "all", "--out", REPORTS, "--note", "desktop app"]
    if packages:
        argv += ["--packages", packages]
    return argv, base


def run_engine(mode, steps, packages):
    s = load_settings()
    with LOCK:
        STATE.update(running=True, mode=mode, started=time.time(), log=[], last_rc=None)
    try:
        if not s.get("amd_psw"):
            raise RuntimeError("no AdvancedMD password saved - open Settings")
        if s.get("auto_update", True) and s.get("token"):
            log("updating the scripts from GitHub main ...")
            log("main is at " + update_repo(s["token"]))
        argv, base = engine_cmd(mode, steps, packages)
        env = dict(os.environ)
        env["AMD_PSW"] = s["amd_psw"]
        if s.get("stedi_key"):
            env["STEDI_API_KEY"] = s["stedi_key"]
        env["EHPA_PYTHON_ARGV"] = json.dumps(base)
        env["PYTHONIOENCODING"] = "utf-8"
        os.makedirs(REPORTS, exist_ok=True)
        log("%s run: %s" % (mode, " ".join(os.path.basename(a) if i == 0 else a for i, a in enumerate(argv))))
        flags = {"creationflags": 0x08000000} if platform.system() == "Windows" else {}   # CREATE_NO_WINDOW
        p = subprocess.Popen(argv, cwd=REPO, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                             encoding="utf-8", errors="replace", **flags)
        for line in p.stdout:
            log(line.rstrip())
        rc = p.wait()
        with LOCK:
            STATE["last_rc"] = rc
        log("engine finished with exit code %s" % rc)
        latest = os.path.join(REPORTS, "latest.json")
        if os.path.exists(latest):
            with LOCK:
                STATE["last_report"] = json.load(open(latest, encoding="utf-8"))
    except Exception as ex:
        log("ERROR: %s" % ex)
        with LOCK:
            STATE["last_rc"] = 1
    finally:
        with LOCK:
            STATE["running"] = False


def start_run(mode, steps, packages):
    with LOCK:
        if STATE["running"]:
            return False
    threading.Thread(target=run_engine, args=(mode, steps, packages), daemon=True).start()
    return True


# ----------------------------------------------------------------------------- cloud run (the same engine on GitHub Actions)
def cloud_dispatch(mode, steps, packages, note):
    s = load_settings()
    if not s.get("token"):
        raise RuntimeError("no GitHub token saved - open Settings")
    gh("/repos/%s/%s/actions/workflows/%s/dispatches" % (OWNER, REPO_NAME, WORKFLOW), s["token"], method="POST",
       body={"ref": "main", "inputs": {"mode": mode, "steps": steps or "all", "packages": packages or "", "note": note or "desktop app"}})
    return True


def cloud_runs():
    s = load_settings()
    if not s.get("token"):
        return []
    j = gh("/repos/%s/%s/actions/workflows/%s/runs?per_page=8" % (OWNER, REPO_NAME, WORKFLOW), s["token"])
    return [{"id": r["id"], "status": r["status"], "conclusion": r.get("conclusion"), "title": r.get("display_title") or r.get("name"),
             "started": r.get("run_started_at") or r.get("created_at"), "updated": r.get("updated_at"), "url": r.get("html_url")} for r in (j.get("workflow_runs") or [])]


def cloud_latest_report():
    s = load_settings()
    if not s.get("token"):
        return None
    try:
        raw = gh("/repos/%s/%s/contents/reports/button/latest.json?ref=main" % (OWNER, REPO_NAME), s["token"])
    except Exception:
        return None
    if raw and raw.get("encoding") == "base64":
        import base64
        return json.loads(base64.b64decode(raw["content"]).decode("utf-8"))
    return None


# ----------------------------------------------------------------------------- the local web server behind the window
class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):   # quiet
        pass

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype + ("; charset=utf-8" if ctype.startswith("text") else ""))
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}") if n else {}

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        if u.path == "/":
            return self._send(200, open(os.path.join(RES, "ui.html"), "rb").read(), "text/html")
        if u.path == "/api/settings":
            s = load_settings()
            return self._send(200, {"token": bool(s.get("token")), "amd_psw": bool(s.get("amd_psw")), "stedi_key": bool(s.get("stedi_key")),
                                    "auto_update": s.get("auto_update", True), "data": DATA, "repo_head": repo_head(), "frozen": FROZEN,
                                    "version": VERSION, "autorun": AUTORUN})
        if u.path == "/api/status":
            with LOCK:
                STATE["heartbeat"] = time.time()
                return self._send(200, {"running": STATE["running"], "mode": STATE["mode"], "started": STATE["started"],
                                        "log": STATE["log"][-int(q.get("n", ["60"])[0]):], "last_rc": STATE["last_rc"], "update": STATE["update"]})
        if u.path == "/api/report":
            p = os.path.join(REPORTS, q.get("stamp", ["latest"])[0] + ".json")
            if not os.path.exists(p):
                return self._send(404, {"error": "no report yet"})
            return self._send(200, open(p, "rb").read())
        if u.path == "/api/history":
            os.makedirs(REPORTS, exist_ok=True)
            out = []
            for f in sorted(os.listdir(REPORTS), reverse=True):
                if re.match(r"^\d{4}-\d{2}-\d{2}T\d{4}Z\.json$", f):
                    try:
                        r = json.load(open(os.path.join(REPORTS, f), encoding="utf-8"))
                        out.append({"stamp": r.get("stamp"), "mode": r.get("mode"), "status": r.get("status"), "headline": r.get("headline"),
                                    "pay": ((r.get("summary") or {}).get("posted") or {}).get("pay", 0)})
                    except (OSError, ValueError):
                        pass
                if len(out) >= 20:
                    break
            return self._send(200, out)
        if u.path == "/api/cloud/runs":
            try:
                return self._send(200, {"runs": cloud_runs(), "report": cloud_latest_report()})
            except Exception as ex:
                return self._send(500, {"error": str(ex)})
        if u.path == "/api/heartbeat":
            with LOCK:
                STATE["heartbeat"] = time.time()
            return self._send(200, {"ok": True})
        return self._send(404, {"error": "no such page"})

    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        b = self._body()
        try:
            if u.path == "/api/settings":
                s = load_settings()
                for k in ("token", "amd_psw", "stedi_key"):
                    if b.get(k):
                        s[k] = b[k].strip()
                    elif b.get("clear_" + k):
                        s.pop(k, None)
                if "auto_update" in b:
                    s["auto_update"] = bool(b["auto_update"])
                save_settings(s)
                return self._send(200, {"ok": True})
            if u.path == "/api/test":
                s = load_settings()
                me = gh("/user", s.get("token", ""))
                r = gh("/repos/%s/%s" % (OWNER, REPO_NAME), s.get("token", ""))
                return self._send(200, {"ok": True, "login": me.get("login"), "repo": r.get("full_name"), "push": bool((r.get("permissions") or {}).get("push"))})
            if u.path == "/api/update":
                s = load_settings()
                with LOCK:
                    STATE["update"] = "downloading main ..."
                note = update_repo(s.get("token", ""))
                with LOCK:
                    STATE["update"] = ""
                return self._send(200, {"ok": True, "head": note})
            if u.path == "/api/run":
                mode = "live" if b.get("mode") == "live" else "dry"
                ok = start_run(mode, b.get("steps") or "all", b.get("packages") or "")
                return self._send(200 if ok else 409, {"ok": ok, "error": None if ok else "a run is already going"})
            if u.path == "/api/cloud/run":
                cloud_dispatch("live" if b.get("mode") == "live" else "dry", b.get("steps") or "all", b.get("packages") or "", b.get("note"))
                return self._send(200, {"ok": True})
            if u.path == "/api/open":
                what = b.get("what")
                target = {"data": DATA, "reports": REPORTS, "repo": REPO, "workspace": "/home/claude/unbilled"}.get(what, DATA)
                if platform.system() == "Windows":
                    os.startfile(target)  # noqa
                else:
                    subprocess.Popen(["xdg-open", target])
                return self._send(200, {"ok": True})
            if u.path == "/api/quit":
                threading.Thread(target=lambda: (time.sleep(0.3), os._exit(0)), daemon=True).start()
                return self._send(200, {"ok": True})
        except Exception as ex:
            with LOCK:
                STATE["update"] = ""
            return self._send(500, {"error": str(ex)})
        return self._send(404, {"error": "no such action"})


def open_window(url):
    """A plain app window: Edge or Chrome in --app mode when present, else the default browser."""
    cands = []
    if platform.system() == "Windows":
        for base in (os.environ.get("ProgramFiles(x86)", ""), os.environ.get("ProgramFiles", ""), os.environ.get("LOCALAPPDATA", "")):
            cands += [os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe"), os.path.join(base, "Google", "Chrome", "Application", "chrome.exe")]
    else:
        cands += ["/usr/bin/microsoft-edge", "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser"]
    for c in cands:
        if c and os.path.exists(c):
            try:
                subprocess.Popen([c, "--app=" + url, "--window-size=1180,920", "--user-data-dir=" + os.path.join(DATA, "window")])
                return
            except OSError:
                pass
    webbrowser.open(url)


def watchdog():
    """Quit when the window has been closed for a while and no run is going (the page pings every few seconds)."""
    first = time.time()
    while True:
        time.sleep(15)
        with LOCK:
            hb, running = STATE["heartbeat"], STATE["running"]
        if running:
            continue
        if hb and time.time() - hb > 120:
            os._exit(0)
        if not hb and time.time() - first > 600:
            os._exit(0)


VERSION = "1.0.0"
AUTORUN = None


def main():
    global AUTORUN
    if len(sys.argv) >= 3 and sys.argv[1] == "--py":
        return run_as_python(sys.argv[2:])
    for a in sys.argv[1:]:
        if a.startswith("ehpa-billing://"):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(a).query)
            AUTORUN = {"mode": "live" if q.get("mode", ["dry"])[0] == "live" else "dry", "steps": q.get("steps", ["all"])[0]}
    os.makedirs(DATA, exist_ok=True)
    os.makedirs(REPORTS, exist_ok=True)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    port = srv.server_address[1]
    url = "http://127.0.0.1:%d/" % port
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    threading.Thread(target=watchdog, daemon=True).start()
    open_window(url)
    print(APP, url, flush=True)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
