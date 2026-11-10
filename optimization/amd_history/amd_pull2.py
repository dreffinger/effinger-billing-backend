#!/usr/bin/env python3
# PLAIN ENGLISH (AdvancedMD pull, layers 2 and 3 - William 11/10/2026: "pull all data from advanced md not just back 2 years and update
#   it all to the database").
# Decides: nothing about billing. READS ONLY, two calls that are already in the registry (docs/captured_calls.md):
#     getdemographic            (one call per chart)  -> insurance plans (payer, dates, order), sex, birth YEAR (1936 = 1936 or earlier), state,
#                                                        deceased / inactive flags, account ageing buckets -> collection chartfacts
#                                                        (11/10/2026 privacy review: no ZIP code, no city, no marital status - a chart is not to
#                                                        be singled out by sex + birth year + ZIP; this layer is still PATIENT-LEVEL data)
#     getchargedetaildataicd10  (one call per charge) -> place of service as billed, units, diagnoses, modifiers, allowed and expected
#                                                        amounts, claim numbers, billing history -> collection chargedetail
#   Documents are keyed by the chart id. Copied by ALLOW-LIST ONLY (every element; an attribute that is not on a list is left out and its
#   NAME is counted in the log): no patient or responsible-party name, no SSN, no full birth date, no street address, ZIP, city, phone,
#   e-mail, member id, group number or free-text note is ever written.
# Rules: never logs in (uses the session an earlier amd.login_cached() left; a dead session stops it, exit 3); HTTP 429 / 5xx = wait and
#   retry, then stop (exit 4); paced; resumable (state/progress_<layer>.jsonl); a STOP file in state/ ends it cleanly.
# Survives a lost machine: documents are written into staging folders of 200 charts in the order they finish (docs_<layer>/sNNNNN/), the
#   loader puts every full folder into the database at once, and with --from-db a later session starts from what the DATABASE holds:
#   the charts already loaded are skipped and the charge ids come from amd.charges (no local copy of the first layer is needed).
# Usage: amd_pull2.py demog|detail [--workers 2] [--pace 0.5] [--limit N] [--until HH:MM] [--from-db] [--folder 200]      amd_pull2.py status
import os, sys, re, json, time, threading, queue, datetime, collections, glob, io, contextlib, importlib.util
import xml.etree.ElementTree as ET
S = "/tmp/claude-0/-home-user/5aaa27c8-6973-50aa-bba1-4b473bbc3aa7/scratchpad/amdpull"
_argv = sys.argv[:]; sys.argv = ["amd_pull.py", "status-quiet"]
_spec = importlib.util.spec_from_file_location("amd_pull", S + "/amd_pull.py"); base = importlib.util.module_from_spec(_spec)
with contextlib.redirect_stdout(io.StringIO()): _spec.loader.exec_module(base)
sys.argv = _argv
a = sys.argv[1:]; CMD = a[0] if a else "status"
def opt(name, default=None): return a[a.index(name) + 1] if name in a and a.index(name) + 1 < len(a) else default
base.PACE = float(opt("--pace", "0.5")); WORKERS = int(opt("--workers", "2")); LIMIT = int(opt("--limit", "0")); UNTIL = opt("--until")
FROM_DB = "--from-db" in a; FOLDER = int(opt("--folder", "200"))
def db_rows(sql):
    """Rows of one read query on the production practice database (the same HTTPS route the loader uses; the connection string is never printed)."""
    sp = importlib.util.spec_from_file_location("neon_exec", S + "/neon_exec.py"); ne = importlib.util.module_from_spec(sp); sp.loader.exec_module(ne)
    url, host = ne.url_for("prod"); return ne.run(url, host, sql).get("rows", [])
# quiet windows (UTC): the scheduled billing runs use AdvancedMD then (columns 01:19 / 07:19 / 13:19 / 19:19, feed 01:34, cascade 05:35) -
# the pull sleeps through them so it never competes with billing. "--quiet none" turns them off.
QUIET = opt("--quiet", "01:10-02:40,05:30-06:40,07:10-08:15,13:10-14:15,19:10-20:15")
def _mins(hhmm): h, m = hhmm.split(":"); return int(h) * 60 + int(m)
QUIET_WINDOWS = [] if QUIET in ("", "none") else [tuple(_mins(x) for x in w.split("-")) for w in QUIET.split(",")]
def wait_quiet():
    """Sleep while the clock is inside a quiet window; True if the pull should go on, False if it was told to stop."""
    said = False
    while True:
        now = utc(); m = now.hour * 60 + now.minute
        if not any(a <= m < b for a, b in QUIET_WINDOWS): return True
        if base._stop.is_set() or os.path.exists(os.path.join(STATE, "STOP")): return False
        if not said: log("quiet window (scheduled billing run) - the pull is sleeping"); said = True
        # one light read every ten minutes keeps the session from idling out (the pull never logs in again); it matches no patient
        if time.time() - _alive[0] > 600:
            with _alock:
                if time.time() - _alive[0] > 600:
                    _alive[0] = time.time()
                    try: xml_call('<ppmdmsg action="lookuppatient" class="api" msgtime="%s" name="ZZQXJ%%" exactmatch="0" page="1"/>' % amd._msgtime())
                    except base.SessionExpired: base.stop("AdvancedMD session expired during a quiet window - NOT logging in again from here"); return False
                    except Exception: pass
        time.sleep(30)
_alive = [time.time()]; _alock = threading.Lock()
STATE = os.path.join(S, "state"); LOG = os.path.join(S, "pull2.log")
base.LOG = LOG
log = base.log; xml_call = base.xml_call; iso = base.iso; utc = base.utc; amd = base.amd
def keep(el, names): return {k: el.attrib[k] for k in names if k in el.attrib and el.attrib[k] != ""}
LEFT_OUT = {}      # element kind -> {attribute name: times seen} of what the allow-lists left out (names only, for the log)
def allow(el, names, kind):
    """The listed attributes of one element; every other attribute is left out and its NAME counted (11/10/2026 privacy review: an allow-list
    for every element - a list of forbidden words would let a new attribute such as a birth date or a member number through)."""
    out = {}
    for k, v in el.attrib.items():
        if v == "": continue
        if k in names: out[k] = v
        else: LEFT_OUT.setdefault(kind, {}); LEFT_OUT[kind][k] = LEFT_OUT[kind].get(k, 0) + 1
    return out
EXTINS_KEEP = ("id", "hospitalizationfrom", "hospitalizationto", "emergency", "employment", "autoaccident", "otheraccident", "accidentstate", "outsidelab", "payprov", "patsignature",
               "epsdt", "resubmissioncode", "dateofinjury", "datesimilarsymptom", "datelastseen", "unabletoworkfrom", "unabletoworkto", "pregnant")
REBILL_KEEP = ("id", "date", "billeddate", "rebilldate", "carrier", "carrierfid", "sequence", "claimid", "claimrun", "paperedi", "type", "status", "demand")
STMT_KEEP = ("id", "date", "statementdate", "amount", "type", "batch", "status")

# ---- layer 3: chart facts (getdemographic) ---------------------------------------------------------------------------------------
PAT_KEEP = ("id", "inactive", "inactivestatus", "respparty", "profile", "insorder", "sex", "finclasscode", "relationship", "hipaarelationship", "isinvoiceentity")      # no raw deceased value (it could be a date), no marital status
PLAN_KEEP = ("id", "carrier", "begindate", "enddate", "copay", "copaytype", "coverage", "relationship", "hipaarelationship", "sequence", "mspcode", "payerid", "deductible", "deductiblemet",
             "yearendmonth", "eligibilitystatusid", "eligibilitychangedat", "eligibilitycreatedat", "eligibilityresponsedate", "claimcount", "eligibilitystc", "finclasscode")
RESP_KEEP = ("id", "accttype", "sendstmt", "stmtrestart", "holdreasoncode", "billcycle", "fincharge", "stmtformat", "balancefwd", "lastpmtdate", "lastpmtamount", "laststmtdate", "laststmtamount", "paymentplanbalance", "ispaperless")
REFPLAN_KEEP = ("id", "refprov", "type", "refplanstatus", "facility", "begindate", "enddate", "maxvisits", "usedvisits", "status", "sequence", "ismain")
BUCKET_KEEP = ("buckettype", "current", "past30", "past60", "past90", "past120", "unapplied", "total")
OLDEST_YEAR = 1936      # a birth year of 1936 or earlier (age 90 and over in 2026) is stored as 1936, with birth_year_capped = 1
def birth_year(dob):
    m = re.search(r"(19|20)\d{2}", dob or ""); return (str(max(int(m.group(0)), OLDEST_YEAR)) if m else "")
def birth_capped(dob):
    m = re.search(r"(19|20)\d{2}", dob or ""); return "1" if (m and int(m.group(0)) <= OLDEST_YEAR) else "0"
def demog_doc(pid):
    root = ET.fromstring(xml_call('<ppmdmsg action="getdemographic" class="demographics" msgtime="%s" patientid="%s" nocookie="1"/>' % (amd._msgtime(), pid)))
    p = root.find(".//patientlist/patient")
    if p is None: raise ValueError("no patient in the answer: " + " ".join((e.text or "")[:80] for e in root.iter("Error"))[:160])
    d = {"_written": iso(), "chart": "pat" + pid, "source": "AdvancedMD getdemographic", "patient": keep(p, PAT_KEEP)}
    d["patient"]["birth_year"] = birth_year(p.get("dob")); d["patient"]["birth_year_capped"] = birth_capped(p.get("dob")); d["patient"]["deceased_flag"] = "1" if (p.get("deceased") or "") not in ("", "0") else "0"
    ad = p.find("address")
    if ad is not None: d["patient"]["state"] = ad.get("state") or ""      # the state only: no ZIP code, no city
    d["plans"] = [keep(x, PLAN_KEEP) for x in p.findall("insplanlist/insplan")]
    d["referral_plans"] = [keep(x, REFPLAN_KEEP) for x in p.findall("refplanlist/refplan")]
    d["ageing"] = [keep(x, BUCKET_KEEP) for x in p.findall("arbucketlist/arbucket")]
    rp = root.find(".//resppartylist/respparty")
    if rp is not None:
        d["account"] = keep(rp, RESP_KEEP); d["account"]["ageing"] = [keep(x, BUCKET_KEEP) for x in rp.findall("arbucketlist/arbucket")]
    d["carriers"] = {c.get("id"): {"code": c.get("code"), "name": c.get("name")} for c in root.findall(".//carrierlist/carrier") if c.get("id")}
    return d

# ---- layer 2: charge detail (getchargedetaildataicd10) -----------------------------------------------------------------------------
VISIT_KEEP = ("id", "seq", "date", "isappt", "profile", "refplan", "episode", "insorder", "onhcfa", "acceptassign", "forcepaper", "approvedat", "facility", "providercodeset")
CHG_KEEP = ("id", "createtime", "begindate", "enddate", "proccode", "authcount", "fee", "units", "netfee", "duration", "aging", "pos", "tos", "allowed", "expected", "patportion", "insportion",
            "patbalance", "insbalance", "billins", "insbilled", "batchnumber", "void", "protected", "lastbilledcarrier", "datebilled", "voideddate", "totalvisitcharges", "finclasscode", "entered",
            "dayclosed", "periodclosed", "paymentplan", "diagcodes", "modcodes", "cobcode", "asstprovider")
PAY_KEEP = ("id", "createtime", "source", "paymentcode", "date", "amount", "checknumber", "status", "paymenttype", "void", "carrierfid", "origrefnum")
WO_KEEP = ("id", "createtime", "source", "Writeoffcode", "writeoffcode", "date", "amount", "void")
BILL_KEEP = ("carriername", "billeddate", "paperedi", "isrollup", "demand", "IsAMDSystem", "claimrun", "billprofile", "submitter", "partner", "billgroup", "claimid", "begindateofservice")
def detail_one(cid):
    """One charge -> (charge doc, visit doc). cid = digits."""
    root = ET.fromstring(xml_call(amd.msg("getchargedetaildataicd10", "demographics", {"chargeid": cid, "nocookie": "1"})))
    v = root.find(".//visit"); c = next((e for e in root.iter("charge") if re.sub(r"\D", "", e.get("id") or "") == cid), None)
    if v is None or c is None: raise ValueError("no charge in the answer: " + " ".join((e.text or "")[:80] for e in root.iter("Error"))[:160])
    look = lambda path: {x.get("id"): x.get("code") for x in root.findall(path) if x.get("id")}
    proc = look(".//proccodelist/proccode"); dx = look(".//diagcodelist/diagcode"); mods = look(".//modcodelist/modcode"); cars = look(".//carrierlist/carrier"); facs = look(".//facilitylist/facility"); profs = look(".//profilelist/profile")
    d = keep(c, CHG_KEEP)
    d["cpt"] = proc.get(c.get("proccode"), ""); d["dx"] = [dx.get(x, x) for x in (c.get("diagcodes") or "").split()]; d["mods"] = [mods.get(x, x) for x in (c.get("modcodes") or "").split()]
    d["lastbilledcarrier_code"] = cars.get(c.get("lastbilledcarrier"), "")
    d["payments"] = [keep(p, PAY_KEEP) for p in c.findall("paymentlist/payment")]
    d["writeoffs"] = [keep(w, WO_KEEP) for w in c.findall("writeofflist/writeoff")]
    d["insbills"] = [keep(b, BILL_KEEP) for b in c.findall("insbilllist/insbill")]
    d["rebills"] = [allow(r, REBILL_KEEP, "rebill") for r in (c.find("rebilllist") if c.find("rebilllist") is not None else [])]
    d["statements"] = [allow(s, STMT_KEEP, "statement") for s in (c.find("statementlist") if c.find("statementlist") is not None else [])]
    vd = keep(v, VISIT_KEEP); vd["facility_code"] = facs.get(v.get("facility"), ""); vd["profile_code"] = profs.get(v.get("profile"), "")
    ex = v.find("extins")
    if ex is not None and ex.attrib: vd["extins"] = allow(ex, EXTINS_KEEP, "extins")
    vd["insurance_order"] = [{"carrier": o.get("carrier"), "carrier_code": cars.get(o.get("carrier"), ""), "sequence": o.get("sequence"), "ordinal": o.get("ordinal")} for o in v.findall("insuranceorderlist/insuranceorder")]
    d["visit_id"] = vd.get("id", "")
    return d, vd
def detail_doc(pid, charge_ids):
    charges = []; visits = {}; errs = []
    for cid in charge_ids:
        if base._stop.is_set(): raise base.Throttled("stopping")
        if not wait_quiet(): raise base.Throttled("stopping")
        try:
            d, vd = detail_one(cid); charges.append(d)
            if vd.get("id"): visits[vd["id"]] = vd
        except (base.SessionExpired, base.Throttled): raise
        except Exception as e: errs.append({"charge": cid, "err": (type(e).__name__ + ": " + str(e))[:160]})
    return {"_written": iso(), "chart": "pat" + pid, "source": "AdvancedMD getchargedetaildataicd10", "charges": charges, "visits": visits, "errors": errs}

# ---- driver ------------------------------------------------------------------------------------------------------------------------------
DBCH = {}       # chart digits -> [charge id digits, newest date of service first], filled from amd.charges with --from-db
def order():
    pfile = os.path.join(STATE, "patients.txt")
    if not os.path.exists(pfile) and FROM_DB:      # a new machine: the list of charts comes from the database, most recently active first
        ids = [re.sub(r"\D", "", r[0]) for r in db_rows("select chart_id from amd.charts order by newest_charge desc nulls last, chart_id")]
        os.makedirs(STATE, exist_ok=True); open(pfile, "w").write("\n".join(ids) + "\n"); open(os.path.join(STATE, "priority.txt"), "w").write("\n".join(ids) + "\n")
    allids = [l.strip() for l in open(pfile) if l.strip().isdigit()]; known = set(allids)
    pf = os.path.join(STATE, "priority.txt"); first = [l.strip() for l in open(pf) if l.strip() in known] if os.path.exists(pf) else []
    return list(dict.fromkeys(first + allids)), {pid: i for i, pid in enumerate(sorted(allids, key=int))}
def read_progress(path):
    done = {}
    if os.path.exists(path):
        for line in open(path):
            try: r = json.loads(line); done[r["id"]] = r
            except Exception: pass
    return done
def live_charge_ids(pid, index):
    """The charge ids of one chart from the history document already pulled: live lines only, newest date of service first."""
    f = os.path.join(S, "docs", "b%03d" % (index[pid] // 500), "txhistory", "pat%s.json" % pid)
    if not os.path.exists(f): return DBCH.get(pid) if FROM_DB else None
    d = json.load(open(f)); rows = []
    for c in d["charges"]:
        if c.get("void") == "1" or (c.get("fee") or "").startswith("-"): continue
        cid = re.sub(r"\D", "", c.get("id") or "")
        if cid: rows.append(((c.get("dos") or "")[-4:] + (c.get("dos") or "")[:5], cid))
    return [cid for _, cid in sorted(rows, reverse=True)]
if CMD in ("demog", "detail"):
    base.session_open(); layer = "chartfacts" if CMD == "demog" else "chargedetail"
    PROG = os.path.join(STATE, "progress_%s.jsonl" % layer); ERRS = os.path.join(STATE, "errors_%s.jsonl" % layer); OUT = os.path.join(S, "docs_" + layer)
    ids, index = order(); done = read_progress(PROG)
    if FROM_DB:
        indb = {re.sub(r"\D", "", r[0]) for r in db_rows("select doc_id from raw.documents where source = 'amd_history' and collection = '%s'" % layer)}
        for p in indb: done.setdefault(p, {"id": p, "ok": True, "n": 0, "at": "in the database"})
        log("%s: %d charts already in the database for this layer" % (CMD, len(indb)))
        if CMD == "detail":
            for ch, cid in db_rows("select chart_id, charge_id from amd.charges where live order by chart_id, dos desc nulls last"):
                DBCH.setdefault(re.sub(r"\D", "", ch), []).append(re.sub(r"\D", "", cid))
            for p in ids: DBCH.setdefault(p, [])          # a chart with no live charge still gets its (empty) document
            log("detail: live charge ids of %d charts read from the database" % len(DBCH))
    todo = [p for p in ids if p not in done or not done[p].get("ok")]
    if LIMIT: todo = todo[:LIMIT]
    seq = [len(glob.glob(os.path.join(OUT, "s*", layer, "pat*.json")))]      # documents on this machine so far: the next one goes into folder seq // FOLDER
    until = None
    if UNTIL:
        h, mm = UNTIL.split(":"); until = utc().replace(hour=int(h), minute=int(mm), second=0, microsecond=0)
        if until < utc(): until += datetime.timedelta(days=1)
    log("%s START: %d charts listed, %d already done, %d to do now; workers %d, pace %.2f s" % (CMD, len(ids), len(done), len(todo), WORKERS, base.PACE))
    q = queue.Queue(); [q.put(p) for p in todo]; stats = collections.Counter(); t0 = time.time(); lock = threading.Lock(); fails = collections.deque(maxlen=20)
    def note(path, rec):
        with lock:
            with open(path, "a") as f: f.write(json.dumps(rec) + "\n")
    def worker():
        while not base._stop.is_set():
            try: pid = q.get_nowait()
            except queue.Empty: return
            if os.path.exists(os.path.join(STATE, "STOP")): base.stop("STOP file present"); return
            if until and utc() >= until: base.stop("reached --until %s" % UNTIL); return
            if not wait_quiet(): base.stop("stopped during a quiet window"); return
            try:
                if CMD == "demog": doc = demog_doc(pid); n = len(doc.get("plans") or [])
                else:
                    cids = live_charge_ids(pid, index)
                    if cids is None: note(ERRS, {"id": pid, "err": "no history document yet", "at": iso()}); stats["skipped"] += 1; continue
                    doc = detail_doc(pid, cids); n = len(doc["charges"]); stats["charge errors"] += len(doc["errors"])
                with lock: k_ = seq[0]; seq[0] += 1
                d = os.path.join(OUT, "s%05d" % (k_ // FOLDER), layer); os.makedirs(d, exist_ok=True)
                tmp = os.path.join(d, "pat%s.json.tmp" % pid)
                with open(tmp, "w") as f: json.dump(doc, f, separators=(",", ":"))
                os.replace(tmp, os.path.join(d, "pat%s.json" % pid))
                note(PROG, {"id": pid, "ok": True, "n": n, "at": iso()}); stats["charts"] += 1; stats["items"] += n; fails.append(0)
            except base.SessionExpired: base.stop("AdvancedMD session expired - NOT logging in again from here"); return
            except base.Throttled as e: base.stop("AdvancedMD throttled or unreachable (%s)" % e); return
            except Exception as e:
                note(ERRS, {"id": pid, "err": (type(e).__name__ + ": " + str(e))[:200], "at": iso()}); stats["errors"] += 1; fails.append(1)
                if len(fails) == fails.maxlen and sum(fails) >= 15: base.stop("15 of the last 20 charts failed - something is wrong"); return
            k = stats["charts"] + stats["errors"]
            if k and k % (200 if CMD == "demog" else 50) == 0:
                el = time.time() - t0
                log("%s progress: %d charts (%d errors), %d %s | %.2f charts/s, %.2f calls/s | %d charts left" % (CMD, stats["charts"], stats["errors"], stats["items"], "plans" if CMD == "demog" else "charges", k / el, (stats["items"] if CMD == "detail" else k) / el, q.qsize()))
    ts = [threading.Thread(target=worker, daemon=True) for _ in range(WORKERS)]
    [t.start() for t in ts]; [t.join() for t in ts]
    left = q.qsize()
    log("%s %s: %d charts this run (%d errors), %d items in %.0f min; %d charts still to do%s" % (CMD, "DONE" if not base._stop.is_set() and left == 0 else "STOPPED", stats["charts"], stats["errors"], stats["items"], (time.time() - t0) / 60, left, (" - " + base._why[0]) if base._why[0] else ""))
    if LEFT_OUT: log("attributes the allow-lists left out (names and counts only): %s" % json.dumps(LEFT_OUT, sort_keys=True)[:900])
    sys.exit(0 if (not base._stop.is_set() and left == 0) else (3 if "expired" in base._why[0] else 4))
else:
    for layer in ("chartfacts", "chargedetail"):
        done = read_progress(os.path.join(STATE, "progress_%s.jsonl" % layer)); ok = [r for r in done.values() if r.get("ok")]
        print("%s: charts done %d, items %d" % (layer, len(ok), sum(r.get("n", 0) for r in ok)))
