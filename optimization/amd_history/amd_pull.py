#!/usr/bin/env python3
# PLAIN ENGLISH (AdvancedMD history pull, William 11/10/2026: "pull all the data going back from advanced md back two years and upload it
#   all to the data base").
# Decides: nothing about billing. READS ONLY. Two AdvancedMD calls, both already in the registry (docs/captured_calls.md):
#     lookuppatient (class api, name="%", paged 50 per page)  -> the list of chart ids (ONLY the id is kept; names, SSN, birth dates,
#                                                                 addresses and phone numbers in the answer are never written anywhere)
#     gettxhistory  (class demographics, the txh.fetch shape, every page) -> each chart's charges, payments with reason codes, write-offs
#   and writes one PHI-light JSON document per chart for the practice database (raw.documents, source amd_history, collection txhistory).
#   A document carries the chart id, dates of service, codes, amounts, payer codes, building, provider code, check numbers - never a
#   patient or responsible-party name: attributes are copied by ALLOW-LIST, anything not listed is dropped.
# Rules it uses: ONE AMD login per session, made by amd.login_cached() BEFORE this script (it never logs in: a dead session stops it with
#   exit 3 so a person decides when to log in again). HTTP 429 / 5xx = wait and retry the same call, then stop with exit 4. Calls are paced.
# Never touches: any write action. No charge, visit, payment, plan or patient is changed.
# Usage:  amd_pull.py enumerate                      list every chart id -> state/patients.txt
#         amd_pull.py pull [--workers 2] [--pace 0.5] [--limit N] [--until HH:MM (UTC)] [--only-first FILE]
#         amd_pull.py status
import os, sys, re, json, time, threading, queue, datetime, collections
import xml.etree.ElementTree as ET
S = os.environ.get("AMDPULL_HOME", "/tmp/claude-0/-home-user/5aaa27c8-6973-50aa-bba1-4b473bbc3aa7/scratchpad/amdpull")
HELPERS = os.environ.get("AMDPULL_HELPERS", "/tmp/claude-0/-home-user/5aaa27c8-6973-50aa-bba1-4b473bbc3aa7/scratchpad/billing-main/scripts/helpers")
sys.path.insert(0, HELPERS)
import requests, amd
STATE = os.path.join(S, "state"); DOCS = os.path.join(S, "docs"); LOG = os.path.join(S, "pull.log")
PATIENTS = os.path.join(STATE, "patients.txt"); PROGRESS = os.path.join(STATE, "progress.jsonl"); ERRORS = os.path.join(STATE, "errors.jsonl")
STOPFILE = os.path.join(STATE, "STOP")
BUCKET = 500                                          # documents per folder, so the loader never holds more than one folder in memory
a = sys.argv[1:]; CMD = a[0] if a else "status"
def opt(name, default=None): return a[a.index(name) + 1] if name in a and a.index(name) + 1 < len(a) else default
PACE = float(opt("--pace", "0.5")); WORKERS = int(opt("--workers", "2")); LIMIT = int(opt("--limit", "0")); UNTIL = opt("--until")
def utc(): return datetime.datetime.now(datetime.timezone.utc)
def iso(): return utc().strftime("%Y-%m-%dT%H:%M:%SZ")
_loglock = threading.Lock()
def log(*parts):
    line = "%s %s" % (utc().strftime("%H:%M:%S"), " ".join(str(p) for p in parts))
    with _loglock:
        with open(LOG, "a") as f: f.write(line + "\n")
    print(line, flush=True)

class SessionExpired(Exception): pass
class Throttled(Exception): pass
_pacelock = threading.Lock(); _last = [0.0]; _stop = threading.Event(); _why = [""]
def pace():
    with _pacelock:
        wait = PACE - (time.time() - _last[0])
        if wait > 0: time.sleep(wait)
        _last[0] = time.time()
def stop(why):
    if not _stop.is_set(): _why[0] = why; _stop.set(); log("STOPPING:", why)
WEB, TOK = None, None
def session_open():
    """The token an EARLIER amd.login_cached() left in the cache. This script never performs a login."""
    global WEB, TOK
    if not os.path.exists(amd.CACHE): sys.exit("no AdvancedMD session cache - log in once with amd.login_cached() first; this script never logs in")
    c = json.load(open(amd.CACHE)); WEB, TOK = c["web"], c["token"]
_tls = threading.local()
def http():
    if not hasattr(_tls, "s"): _tls.s = requests.Session()
    return _tls.s
def xml_call(body, timeout=150):
    """POST one read message. Returns the response text. Never logs in; raises SessionExpired / Throttled."""
    url = WEB + "/xmlrpc/processrequest.aspx"; waits = [20, 60, 180, 300]
    for attempt in range(len(waits) + 1):
        if _stop.is_set(): raise Throttled("stopping")
        pace()
        try:
            r = http().post(url, data=amd._inject(body, TOK).encode("utf-8"), headers={"Content-Type": "text/xml"}, cookies={"token": TOK}, timeout=timeout)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            if attempt == len(waits): raise Throttled("network: " + type(e).__name__)
            log("network error (%s) - waiting %d s" % (type(e).__name__, waits[attempt])); time.sleep(waits[attempt]); continue
        if r.status_code in (429, 500, 502, 503, 504):
            if attempt == len(waits): raise Throttled("http %d" % r.status_code)
            log("HTTP %d from AdvancedMD - waiting %d s (never logging in again)" % (r.status_code, waits[attempt])); time.sleep(waits[attempt]); continue
        if r.status_code != 200: raise Throttled("http %d" % r.status_code)
        if amd._expired(r.text): raise SessionExpired()
        return r.text
    raise Throttled("retries used up")

# ---- what is copied (ALLOW-LISTS: an attribute that is not named here is dropped, so a name can never ride along) ---------------------
RESULT_KEEP = ("itemcount", "pagecount", "maxunfiltereddate", "oldestcharge", "newestcharge", "sumpatcharges", "suminscharges", "sumpatpayments",
               "suminspayments", "sumpatwriteoffs", "suminswriteoffs", "sumpatbal", "suminsbal", "totalbal", "historycarriercode")
CHARGE_KEEP = ("id", "visit", "dos", "proccode", "proccodetype", "modifiers", "fee", "paid", "patbal", "insbal", "totbal", "carrier", "subcarriercode",
               "billdate", "agingdate", "createtime", "provcode", "npi", "faccode", "facname", "totalvisitcharge", "void", "approvedat", "isinstitutional", "payerinfo")
PAYMENT_KEEP = ("id", "date", "checknumber", "paycode", "source", "void", "voidoffset", "createtime", "provcode", "amount", "carrier")
WRITEOFF_KEEP = ("id", "date", "wocode", "source", "void", "voidoffset", "createtime", "provcode", "amount")
REASON_KEEP = ("code", "amount", "units")
def keep(el, names): return {k: el.attrib[k] for k in names if k in el.attrib}
def payment_doc(p):
    d = keep(p, PAYMENT_KEEP); rs = [keep(r, REASON_KEEP) for r in p.iter("payreason")]
    if rs: d["reasons"] = rs
    return d
def parse_page(text):
    """One gettxhistory page -> (results attrs, [charge docs], [unapplied payment docs], [unapplied write-off docs]). Raises ValueError on a fault."""
    root = ET.fromstring(text)
    res = root.find(".//Results")
    if res is None or root.find(".//chargelist") is None:
        err = " ".join((e.text or "") for e in root.iter("Error"))[:160] or " ".join((e.text or "")[:80] for e in root.iter() if e.tag.lower() in ("fault", "faultstring", "description"))[:160]
        raise ValueError("no Results/chargelist in the answer: " + (err or "unknown shape"))
    charges = []
    for c in root.find(".//chargelist").findall("charge"):
        d = keep(c, CHARGE_KEEP)
        pl = c.find("paymentlist"); wl = c.find("writeofflist")
        d["payments"] = [payment_doc(p) for p in (pl.findall("payment") if pl is not None else [])]
        d["writeoffs"] = [keep(w, WRITEOFF_KEEP) for w in (wl.findall("writeoff") if wl is not None else [])]
        charges.append(d)
    up = root.find(".//unappliedpaymentlist"); uw = root.find(".//unappliedwriteofflist")
    upay = [payment_doc(p) for p in (list(up) if up is not None else [])]
    uwo = [keep(w, WRITEOFF_KEEP) for w in (list(uw) if uw is not None else [])]
    return dict(res.attrib), charges, upay, uwo
def txh_body(pid, page):
    return amd.msg('gettxhistory', 'demographics', {'patientid': pid, 'filterhistory': '0', 'pagenumber': str(page), 'typefilter': '0', 'sortbypayment': 'false',
                   'groupbyvisit': '0', 'sortdescending': '1', 'visitid': '0', 'profileid': '', 'getmemo': 'false', 'nocookie': '1'})
def pull_chart(pid):
    """Every page of one chart -> the document. pid = digits only."""
    res, charges, upay, uwo = parse_page(xml_call(txh_body(pid, 1)))
    pages = max(1, int(res.get("pagecount") or 1)); seen = {c.get("id") for c in charges}
    seen_up = {p.get("id") for p in upay}; seen_uw = {w.get("id") for w in uwo}
    for page in range(2, min(pages, 60) + 1):
        _, more, more_up, more_uw = parse_page(xml_call(txh_body(pid, page)))
        for c in more:
            if c.get("id") not in seen: seen.add(c.get("id")); charges.append(c)
        for p in more_up:                                   # unapplied credits are paged with the charges (AdvancedMD's item count covers both)
            if p.get("id") not in seen_up: seen_up.add(p.get("id")); upay.append(p)
        for w in more_uw:
            if w.get("id") not in seen_uw: seen_uw.add(w.get("id")); uwo.append(w)
    return {"_written": iso(), "chart": "pat" + pid, "source": "AdvancedMD gettxhistory", "pages": pages, "pages_read": min(pages, 60),
            "summary": {k: res[k] for k in RESULT_KEEP if k in res}, "charges": charges, "unapplied_payments": upay, "unapplied_writeoffs": uwo}

def read_progress():
    done = {}
    if os.path.exists(PROGRESS):
        for line in open(PROGRESS):
            try: r = json.loads(line); done[r["id"]] = r
            except Exception: pass
    return done
_proglock = threading.Lock()
def note(path, rec):
    with _proglock:
        with open(path, "a") as f: f.write(json.dumps(rec) + "\n")

if CMD == "enumerate":
    session_open(); os.makedirs(STATE, exist_ok=True)
    ids = set(); page = 1; pages = None; total = None
    while True:
        x = xml_call('<ppmdmsg action="lookuppatient" class="api" msgtime="%s" name="%%" exactmatch="0" page="%d"/>' % (amd._msgtime(), page))
        root = ET.fromstring(x); pl = root.find(".//patientlist")
        if pl is None: sys.exit("lookuppatient: no patientlist on page %d" % page)
        pages = int(pl.get("pagecount") or 1); total = int(pl.get("itemcount") or 0)
        for p in pl.findall("patient"):                                  # ONLY the id leaves this loop
            m = re.match(r"^(?:pat)?(\d+)$", p.get("id") or "")
            if m: ids.add(m.group(1))
        del x, root, pl
        if page % 25 == 0 or page == pages: log("enumerate: page %d of %d, %d chart ids so far (AdvancedMD says %d charts)" % (page, pages, len(ids), total))
        if page >= pages: break
        page += 1
    with open(PATIENTS, "w") as f: f.write("\n".join(sorted(ids, key=lambda s: -int(s))) + "\n")
    os.chmod(PATIENTS, 0o600)
    log("enumerate DONE: %d chart ids written (AdvancedMD reported %d)" % (len(ids), total))

elif CMD == "pull":
    session_open(); os.makedirs(DOCS, exist_ok=True)
    allids = [l.strip() for l in open(PATIENTS) if l.strip().isdigit()]
    first = []
    if opt("--only-first") or os.path.exists(os.path.join(STATE, "priority.txt")):
        pf = opt("--only-first") or os.path.join(STATE, "priority.txt")
        known = set(allids); first = [l.strip() for l in open(pf) if l.strip().isdigit() and l.strip() in known]
    order = list(dict.fromkeys(first + allids)); index = {pid: i for i, pid in enumerate(sorted(allids, key=int))}
    done = read_progress(); todo = [p for p in order if p not in done or not done[p].get("ok")]
    if LIMIT: todo = todo[:LIMIT]
    until = None
    if UNTIL:
        h, m = UNTIL.split(":"); until = utc().replace(hour=int(h), minute=int(m), second=0, microsecond=0)
        if until < utc(): until += datetime.timedelta(days=1)
    log("pull START: %d charts in the list, %d already done, %d to do now; workers %d, pace %.2f s%s" % (len(allids), len(done), len(todo), WORKERS, PACE, (", stopping at %s UTC" % UNTIL) if until else ""))
    q = queue.Queue()
    for p in todo: q.put(p)
    stats = collections.Counter(); t0 = time.time(); fails = collections.deque(maxlen=20)
    def worker():
        while not _stop.is_set():
            try: pid = q.get_nowait()
            except queue.Empty: return
            if os.path.exists(STOPFILE): stop("STOP file present"); return
            if until and utc() >= until: stop("reached --until %s" % UNTIL); return
            try:
                doc = pull_chart(pid)
                d = os.path.join(DOCS, "b%03d" % (index[pid] // BUCKET), "txhistory"); os.makedirs(d, exist_ok=True)
                tmp = os.path.join(d, "pat%s.json.tmp" % pid)
                with open(tmp, "w") as f: json.dump(doc, f, separators=(",", ":"))
                os.replace(tmp, os.path.join(d, "pat%s.json" % pid))
                npay = sum(len(c["payments"]) for c in doc["charges"]); nwo = sum(len(c["writeoffs"]) for c in doc["charges"])
                note(PROGRESS, {"id": pid, "ok": True, "pages": doc["pages"], "charges": len(doc["charges"]), "payments": npay, "writeoffs": nwo,
                                "newest": doc["summary"].get("newestcharge", "")[:10], "oldest": doc["summary"].get("oldestcharge", "")[:10], "at": iso()})
                stats["charts"] += 1; stats["charges"] += len(doc["charges"]); stats["payments"] += npay; stats["writeoffs"] += nwo; stats["pages"] += doc["pages_read"]; fails.append(0)
                if doc["pages"] > 60: note(ERRORS, {"id": pid, "err": "more than 60 pages (%d) - first 60 read" % doc["pages"], "at": iso()})
            except SessionExpired:
                stop("AdvancedMD session expired - NOT logging in again from here"); return
            except Throttled as e:
                stop("AdvancedMD throttled or unreachable (%s)" % e); return
            except Exception as e:
                note(ERRORS, {"id": pid, "err": (type(e).__name__ + ": " + str(e))[:200], "at": iso()}); stats["errors"] += 1; fails.append(1)
                if len(fails) == fails.maxlen and sum(fails) >= 15: stop("15 of the last 20 charts failed - something is wrong"); return
            n = stats["charts"] + stats["errors"]
            if n and n % 200 == 0:
                el = time.time() - t0; left = q.qsize()
                log("progress: %d charts (%d errors), %d charges, %d payments, %d write-offs | %.2f charts/s | about %d min left" % (stats["charts"], stats["errors"], stats["charges"], stats["payments"], stats["writeoffs"], n / el, left / max(n / el, 0.01) / 60))
    threads = [threading.Thread(target=worker, daemon=True) for _ in range(WORKERS)]
    for t in threads: t.start()
    for t in threads: t.join()
    left = q.qsize()
    log("pull %s: %d charts this run (%d errors), %d charges, %d payments, %d write-offs, %d pages in %.0f min; %d charts still to do%s" % (
        "DONE" if not _stop.is_set() and left == 0 else "STOPPED", stats["charts"], stats["errors"], stats["charges"], stats["payments"], stats["writeoffs"], stats["pages"], (time.time() - t0) / 60, left, (" - " + _why[0]) if _why[0] else ""))
    sys.exit(0 if (not _stop.is_set() and left == 0) else (3 if "expired" in _why[0] else 4 if _stop.is_set() else 0))

else:
    n = sum(1 for l in open(PATIENTS)) if os.path.exists(PATIENTS) else 0; done = read_progress()
    ok = [r for r in done.values() if r.get("ok")]
    print("charts listed %d | pulled %d | charges %d | payments %d | write-offs %d | error lines %d" % (n, len(ok), sum(r["charges"] for r in ok), sum(r["payments"] for r in ok), sum(r["writeoffs"] for r in ok), sum(1 for _ in open(ERRORS)) if os.path.exists(ERRORS) else 0))
    yrs = collections.Counter((r.get("newest") or "none")[:4] for r in ok)
    print("charts by year of newest charge:", dict(sorted(yrs.items())))
