#!/usr/bin/env python3
# PLAIN ENGLISH (Working Denials refresh - the "Refresh from AMD" button on the Working Denials board, William 10/13/2026)
# Decides: nothing. Reads the live chart (gettxhistory) for every patient on the unpaid list and every patient already on the
#   Working Denials board, finds every posted $0 payment line that carries a denial reason (CARC), triages each visit with the
#   same CARC table the board uses (DENIAL_RULES in boards/working_denials.py), and works out the visit's live status:
#   RESOLVED (a real payment posted since), WRITTEN-OFF (balance gone to a write-off), RESUBMITTED (the charge's last bill date is
#   after the denial posted), OPEN (still carries a balance, nothing sent since). Writes working_denials_latest.json with chart and
#   visit ids only - no names - so the Billing Button runner can commit it to GitHub and the board can pull it.
# Rules it uses: read-only calls only (massrebillsearch, gettxhistory). Contractual / informational reasons (45, 23, 253, 94) and
#   the PR cost-sharing codes (1, 2, 3) are kept as rows but never counted as actionable, exactly as the board does.
# 11/26/2026 (William's answers - the work queue): it also reads the queue actor's registers (registers/work_queue_act_*.jsonl), reads the
#   charts of the visits the queue worked, writes `paid_since` per worked visit (insurance payments dated after the queue's first action) and a
#   'recovered' block (work_queue.recovered_block): "Recovered this week: $X on N claims (insurance payments posted Mon-Sun on claims the
#   queue worked, after the action); re-sent $Y; written off $Z by code", with the baseline of registers/work_queue_baseline.json - the 507
#   rebills of registers/rebill_log.jsonl joined to the payments after them, read once with --baseline (it reads one visit per rebill).
# Never touches: AMD writes, balances, claims, the board's command queue.
"""Usage: python3 denials_refresh.py [--prior working_denials_latest.json] [--out working_denials_latest.json] [--threads 3] [--max N]
                                  [--registers registers] [--baseline]"""
import json, sys, os, re, datetime, collections, threading, queue, time
import amd, txh, era_post, requests

a = sys.argv[1:]
def opt(n, d=None): return a[a.index(n) + 1] if n in a else d
PRIOR = opt("--prior", "working_denials_latest.json"); OUT = opt("--out", "working_denials_latest.json")
NT = int(opt("--threads", 3)); MX = int(opt("--max", 10**9)); TODAY = datetime.date.today()
REGS = opt("--registers", "registers"); BASELINE = "--baseline" in a

# the board's CARC table lives in boards/working_denials.py (repo) or the workspace copy
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "boards"))
try:
    from working_denials import DENIAL_RULES, DISPO_ORDER, ACTIONABLE, norm, triage
    try:
        from working_denials import triage_line          # CPT/modifier-aware (CCM + GV / B9 -> WRITEOFF, 10/15/2026)
    except ImportError:
        def triage_line(c, cpt="", mods=""): return triage(c)
except ImportError:
    DENIAL_RULES = {}; DISPO_ORDER = ["FIX", "COB", "TIMELY", "CRED", "REVIEW", "PATIENT", "DUPLICATE", "CONTRACTUAL", "INFO", "UNCLASSIFIED"]
    ACTIONABLE = {"FIX", "COB", "TIMELY", "CRED", "REVIEW"}
    def norm(c):
        c = str(c or "").strip().upper()
        for g in ("CO", "OA", "PR", "PI", "CR"):
            if c.startswith(g) and len(c) > len(g): return c[len(g):]
        return c
    def triage(c): return ("UNCLASSIFIED", "No rule yet for CARC %s" % norm(c))
    def triage_line(c, cpt="", mods=""): return triage(c)
NOACTION = {"45", "23", "253", "94"}
# 11/26/2026: the work queue (scripts/helpers/work_queue.py) - the visits it worked and the recovered block
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "scripts", "helpers"))
try:
    import work_queue as _wq
except Exception:
    _wq = None
_act = _wq.act_lines([REGS]) if _wq else []
worked = _wq.worked_visits(_act) if _wq else {}

def f(x):
    try: return float(x or 0)
    except Exception: return 0.0
def ago(d):
    try: return (TODAY - datetime.date.fromisoformat(str(d)[:10])).days
    except Exception: return None
def mdy(s):
    """AMD dates come as mm/dd/yyyy or yyyy-mm-dd; return ISO yyyy-mm-dd or ''."""
    s = str(s or "").strip()
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m: return "%s-%02d-%02d" % (m.group(3), int(m.group(1)), int(m.group(2)))
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    return m.group(0) if m else ""

# ---- posted_last_7d (the Monday scorecard - William's choice of 11/26/2026): a block of its own, apart from every other field of this output ----
# Totals only. Of the chart histories this refresh reads anyway (no extra AdvancedMD read): every payment line whose POSTING date (createtime,
# else date) falls in the 7 full days before today - insurance vs patient (AdvancedMD marks a patient line source 1; with no source, a line with
# no carrier; a line that carries a reason code is the payer's - the pos61_monitor.patient_line test), net of take-backs (negative lines),
# insurance by carrier - and the $0 denial lines posted in those days (a reason code that is not cost-share 1/2/3 and not contractual or
# informational 45/23/253/94/246), counted by visit, the wrong-payer ones (27/26/200/31) among them. A MINIMUM: a chart with no open balance and
# no board row is not read. scripts/helpers/weekly_scorecard.py reads it for the scorecard's 'collected' and 'denials'.
WK_FROM, WK_TO = (TODAY - datetime.timedelta(days=7)).isoformat(), (TODAY - datetime.timedelta(days=1)).isoformat()
WK_SKIP = {"1", "2", "3", "45", "23", "253", "94", "246"}; WK_WRONG = {"27", "26", "200", "31"}
week = []
def week_lines(root):
    """this chart's payment lines posted inside the window: (kind ins|pat|den|zero, carrier, dollars, visit, wrong payer?)"""
    out = []
    for c in root.iter("charge"):
        if c.get("void") == "1": continue
        vid = str(c.get("visit") or c.get("visitid") or "")
        for p in c.iter("payment"):
            if p.get("void") == "1": continue
            d = mdy(p.get("createtime")) or mdy(p.get("date"))
            if not (WK_FROM <= d <= WK_TO): continue
            codes = [x for x in ((norm(r.get("code", "")), abs(f(r.get("amount")))) for r in p.iter("payreason")) if x[0]]
            amt = f(p.get("amount")); car = (p.get("carrier") or "").strip(); src = str(p.get("source") or "").strip()
            if abs(amt) > 0.005:
                out.append(("pat" if not codes and (src == "1" if src else not car) else "ins", car, amt, vid, False))
            else:
                den = [x for x in codes if x[0] not in WK_SKIP]
                if den: out.append(("den", car, sum(x[1] for x in den), vid, any(x[0] in WK_WRONG for x in den)))
                elif codes: out.append(("zero", car, 0.0, vid, False))
    return out
def week_summary(rows):
    ins = [r for r in rows if r[0] == "ins"]; pat = [r for r in rows if r[0] == "pat"]; den = [r for r in rows if r[0] == "den"]
    bycar = collections.defaultdict(float)
    for r in ins: bycar[r[1] or "NONE"] += r[2]
    return {"from": WK_FROM, "to": WK_TO, "basis": "payment lines by posting date (createtime, else date) on the charts this refresh read - a minimum; totals only",
            "insurance": round(sum(r[2] for r in ins), 2), "patient": round(sum(r[2] for r in pat), 2), "takebacks": round(-sum(r[2] for r in ins + pat if r[2] < 0), 2),
            "insurance_lines": len(ins), "patient_lines": len(pat), "adjudicated_lines": len(ins) + len(den) + sum(1 for r in rows if r[0] == "zero"),
            "by_carrier": {k: round(v, 2) for k, v in sorted(bycar.items(), key=lambda kv: -kv[1])},
            "denials": {"visits": len({r[3] for r in den}), "lines": len(den), "dollars": round(sum(r[2] for r in den), 2), "wrong_payer_visits": len({r[3] for r in den if r[4]})}}
# ---- end of posted_last_7d's definitions

prior = {}
if os.path.exists(PRIOR):
    try: prior = json.load(open(PRIOR))
    except Exception: prior = {}
prior_rows = {str(v["visitid"]): v for v in prior.get("visits", [])}
amd.login_cached()
unp = requests.post(era_post.API + "/claim/massrebillsearch", headers=era_post.H(), json={}, timeout=180).json()
pids = sorted({str(v["patientid"]) for v in unp} | {str(v["pid"]) for v in prior.get("visits", []) if v.get("pid")}
              | {str(w["pid"]) for w in worked.values() if str(w.get("pid") or "").isdigit()}, key=int)      # 11/26/2026: the charts the queue worked
pids = pids[:MX]
print("refresh: %d patients (%d on the unpaid list, %d board rows carried in)" % (len(pids), len({str(v["patientid"]) for v in unp}), len(prior_rows)), flush=True)
unp_by_visit = {str(v["visitid"]): v for v in unp}

lock = threading.Lock(); lines = []; status = {}; errors = []
def scan(pid):
    root = None
    for i in range(3):
        try: root = txh.fetch(pid); break
        except Exception as e:
            if i == 2: raise
            time.sleep(2 * (i + 1))
    seen = set()
    out_lines = []; vstat = {}
    for c in root.iter("charge"):
        if c.get("void") == "1": continue
        vid = str(c.get("visit") or c.get("visitid") or ""); seen.add(vid)
        s = vstat.setdefault(vid, {"pays": 0, "paid": 0.0, "wos": 0, "bal": 0.0, "billdate": "", "carrier": c.get("carrier", ""), "denied_on": ""})
        s["bal"] += f(c.get("insbal") or c.get("insbalance")) + f(c.get("patbal") or c.get("patbalance"))
        bd = mdy(c.get("billdate"))
        if bd > s["billdate"]: s["billdate"] = bd
        for p in c.iter("payment"):
            if p.get("void") == "1": continue
            amt = abs(f(p.get("amount")))
            if amt > 0:
                s["pays"] += 1; s["paid"] += amt
                if p.get("carrier") or "carrier" not in p.attrib: s.setdefault("paylist", []).append((mdy(p.get("date")), amt))   # insurance money, dated (11/26/2026)
                continue
            reasons = [(r.get("code", ""), f(r.get("amount")), r.get("description", "") or r.get("reasontext", "")) for r in p.iter("payreason")]
            for code, ramt, desc in reasons:
                carc = norm(code); grp = str(code or "")[:2].upper() if str(code or "")[:2].upper() in ("CO", "PR", "OA", "PI", "CR") else ""
                if not carc: continue
                pd = mdy(p.get("date"))
                if pd > s["denied_on"]: s["denied_on"] = pd
                out_lines.append({"pid": pid, "visitid": vid, "carrier": p.get("carrier") or c.get("carrier", ""), "dos": mdy(c.get("dos") or c.get("dateofservice")),
                                  "cpt": (c.get("proccode") or "").strip(), "mods": (c.get("modcodes") or c.get("modifiers") or "").strip(), "billed": f(c.get("fee") or c.get("amount")), "group": grp, "carc": carc, "reason": desc,
                                  "check": p.get("checknumber", ""), "amt": abs(ramt), "paid_on": pd})
        for w in c.iter("writeoff"):
            if w.get("void") != "1" and f(w.get("amount")) != 0: s["wos"] += 1
    wk = week_lines(root)                     # posted_last_7d: this chart's lines posted in the window - the same history, no extra read
    with lock: week.extend(wk)
    # board visits this chart's page-1 history did not show (long charts): read them one by one
    for vid, row in list(prior_rows.items()) + [(k, w) for k, w in worked.items() if k not in prior_rows]:      # + the visits the queue worked (11/26/2026)
        if str(row.get("pid")) == pid and vid not in seen:
            try:
                r2 = txh.fetch_visit(pid, vid)
                for c in r2.iter("charge"):
                    if c.get("void") == "1" or str(c.get("visit") or "") != vid: continue
                    s = vstat.setdefault(vid, {"pays": 0, "paid": 0.0, "wos": 0, "bal": 0.0, "billdate": "", "carrier": c.get("carrier", ""), "denied_on": ""})
                    s["bal"] += f(c.get("insbal") or c.get("insbalance")) + f(c.get("patbal") or c.get("patbalance"))
                    bd = mdy(c.get("billdate")); s["billdate"] = max(s["billdate"], bd)
                    for p in c.iter("payment"):
                        if p.get("void") == "1": continue
                        amt = abs(f(p.get("amount")))
                        if amt > 0:
                            s["pays"] += 1; s["paid"] += amt
                            if p.get("carrier") or "carrier" not in p.attrib: s.setdefault("paylist", []).append((mdy(p.get("date")), amt))
                        else:
                            for r in p.iter("payreason"):
                                carc = norm(r.get("code", ""))
                                if carc: s["denied_on"] = max(s["denied_on"], mdy(p.get("date")))
                    for w in c.iter("writeoff"):
                        if w.get("void") != "1" and f(w.get("amount")) != 0: s["wos"] += 1
            except Exception as e:
                errors.append("v%s pat%s: %s" % (vid, pid, str(e)[:80]))
    with lock:
        lines.extend(out_lines); status.update({(pid, k): v for k, v in vstat.items()})

def rebill_baseline(path, pay_by_visit, pid_of, prior_rows):
    """The baseline before the queue (11/26/2026): every rebill in registers/rebill_log.jsonl joined to the insurance payments of its visit dated
    after it. A visit whose chart this refresh did not read is read here (its chart from the unpaid list, the board rows, else its charge detail)."""
    rows = []
    for l in (open(path).read().splitlines() if os.path.exists(path) else []):
        try: e = json.loads(l)
        except ValueError: continue
        if e.get("visit"): rows.append(e)
    first = {}
    for e in rows:
        v = str(e["visit"]); d = str(e.get("at") or "")[:10]
        if v not in first or d < first[v][0]: first[v] = (d, str(e.get("charge") or ""))
    pays = {}; unread = 0
    for v, (d, cid) in first.items():
        if v in pay_by_visit: pays[v] = pay_by_visit[v]; continue
        pid = pid_of.get(v) or str((prior_rows.get(v) or {}).get("pid") or "")
        try:
            if not pid and cid:
                m = re.search(r'<patient\s(?:[^>]*?\s)?id="(?:pat)?(\d+)"', amd.post(amd.msg("getchargedetaildataicd10", "demographics", {"chargeid": cid, "nocookie": "1"})))
                pid = m.group(1) if m else ""
            if not pid: unread += 1; continue
            got = []
            for c in txh.fetch_visit(pid, v).iter("charge"):
                if c.get("void") == "1" or str(c.get("visit") or "") != v: continue
                for p in c.iter("payment"):
                    amt = abs(f(p.get("amount")))
                    if p.get("void") != "1" and amt > 0 and (p.get("carrier") or "carrier" not in p.attrib): got.append((mdy(p.get("date")), amt))
            pays[v] = got; time.sleep(0.2)
        except Exception:
            unread += 1
    after = {v: _wq.paid_since(pays.get(v, []), first[v][0]) for v in pays}
    return {"what": "baseline before the work queue (11/26/2026): the rebills of registers/rebill_log.jsonl joined to the insurance payments of their visits dated after the rebill - visit ids and dollars only",
            "asof": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "rebills": len(rows), "visits": len(first),
            "since": min((d for d, _ in first.values()), default=""), "until": max((d for d, _ in first.values()), default=""), "read": len(pays), "unread": unread,
            "paid_visits": sum(1 for x in after.values() if x > 0), "paid_after": round(sum(after.values()), 2)}

q = queue.Queue(); [q.put(p) for p in pids]; n = [0]
def worker():
    while True:
        try: pid = q.get_nowait()
        except queue.Empty: return
        try: scan(pid)
        except Exception as e:
            with lock: errors.append("pat%s: %s" % (pid, str(e)[:80]))
        with lock:
            n[0] += 1
            if n[0] % 50 == 0: print("  %d charts read, %d denial lines, %d errors" % (n[0], len(lines), len(errors)), flush=True)
        time.sleep(0.2)
ts = [threading.Thread(target=worker, daemon=True) for _ in range(NT)]; [t.start() for t in ts]; [t.join() for t in ts]

# roll up to one row per visit: the most actionable line wins, every code listed
byv = {}
for r in lines:
    dispo, action = triage_line(r["carc"], r.get("cpt"), r.get("mods")); rank = DISPO_ORDER.index(dispo) if dispo in DISPO_ORDER else len(DISPO_ORDER)
    if norm(r["carc"]) == "58" and dispo == "REVIEW": rank = -1      # Medicare's place-of-service answer always leads its visit (rules.md 11/10/2026 part 7; the board's own roll-up does the same)
    key = (r["pid"], r["visitid"]); rec = byv.get(key)
    if rec is None or rank < rec["_rank"]:
        byv[key] = {"_rank": rank, "pid": r["pid"], "visitid": r["visitid"], "carrier": r["carrier"], "dos": r["dos"], "cpt": r["cpt"], "billed": r["billed"],
                    "dispo": dispo, "action": action, "carc": r["carc"], "reason": r["reason"], "check": r["check"], "amt": r["amt"],
                    "codes": (rec["codes"] if rec else set()), "rarc": (rec["rarc"] if rec else set()), "age": ago(r["dos"]), "timely": (ago(r["dos"]) or 9999) <= 365, "denied_on": r["paid_on"]}      # a more actionable line keeps the codes already seen
    byv[key]["codes"].add("%s/%s%s" % (r["group"] or "??", r["group"], r["carc"]) if r["group"] else r["carc"])
# carry prior rows whose chart was read but whose $0 line is gone (voided / re-posted): keep them with the live status
for vid, row in prior_rows.items():
    key = (str(row.get("pid")), vid)
    if key not in byv and key in status:
        byv[key] = dict(row, _rank=DISPO_ORDER.index(row.get("dispo")) if row.get("dispo") in DISPO_ORDER else 99, codes=set(row.get("codes") or []), rarc=set(row.get("rarc") or []))
        byv[key].pop("patient", None)
visits = []
for (pid, vid), v in byv.items():
    v["codes"] = sorted(v.pop("codes")); v["rarc"] = sorted(v.pop("rarc")); v.pop("_rank", None)
    s = status.get((pid, vid))
    if not s: v["status"] = "UNMATCHED"
    elif s["pays"]: v["status"] = "RESOLVED"
    elif s["wos"] and s["bal"] <= 0: v["status"] = "WRITTEN-OFF"
    elif s["billdate"] and s.get("denied_on") and s["billdate"] > s["denied_on"]: v["status"] = "RESUBMITTED"; v["resubmitted"] = s["billdate"]
    elif s["bal"] <= 0: v["status"] = "RESOLVED"
    else: v["status"] = "OPEN"
    if s: v["open_balance"] = round(s["bal"], 2); v["last_billed"] = s["billdate"]
    visits.append(v)
bydispo = collections.defaultdict(lambda: {"visits": 0, "amt": 0.0, "patients": set()})
for v in visits:
    d = bydispo[v["dispo"]]; d["visits"] += 1; d["amt"] += v["amt"]; d["patients"].add(v["pid"])
summary = {k: {"visits": x["visits"], "amt": round(x["amt"], 2), "patients": len(x["patients"])} for k, x in bydispo.items()}
act = [v for v in visits if v["dispo"] in ACTIONABLE and v.get("status") not in ("RESOLVED", "RESUBMITTED", "WRITTEN-OFF")]
timely = [v for v in act if v.get("timely")]
bystatus = collections.Counter(v.get("status") or "n/a" for v in visits)
out = {"schema": "working-denials-snapshot/1", "asof": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "source": "AMD live chart (gettxhistory) - Billing Button denials step",
       "charts_read": n[0], "total_lines": len(lines), "total_visits": len(visits), "actionable_visits": len(act), "actionable_amt": round(sum(v["amt"] for v in act), 2),
       "timely_visits": len(timely), "timely_amt": round(sum(v["amt"] for v in timely), 2), "bystatus": dict(bystatus),
       "resub_amt": round(sum(v["amt"] for v in visits if v.get("status") == "RESUBMITTED"), 2), "resolved_amt": round(sum(v["amt"] for v in visits if v.get("status") == "RESOLVED"), 2),
       "summary": summary, "capped": {}, "errors": errors[:50],
       "visits": sorted(visits, key=lambda v: (DISPO_ORDER.index(v["dispo"]) if v["dispo"] in DISPO_ORDER else 99, -v["amt"]))}
out["posted_last_7d"] = week_summary(week)    # the Monday scorecard's block (11/26/2026) - totals only, apart from every other field
# 11/26/2026 (B4): what the work queue recovered - paid_since per worked visit, the week's line, the baseline of the rebills before the queue
pay_by_visit = {vid: s.get("paylist", []) for (pid_, vid), s in status.items()}
if _wq:
    for v in out["visits"]:
        w = worked.get(str(v["visitid"]))
        if w: v["paid_since"] = _wq.paid_since(pay_by_visit.get(str(v["visitid"]), []), w["at"])
    out["worked"] = [{"visitid": k, "pid": w.get("pid"), "at": w["at"], "actions": w["actions"], "paid_since": _wq.paid_since(pay_by_visit.get(k, []), w["at"])}
                     for k, w in sorted(worked.items())]
    bpath = os.path.join(REGS, "work_queue_baseline.json"); baseline = None
    if BASELINE:
        baseline = rebill_baseline(os.path.join(REGS, "rebill_log.jsonl"), pay_by_visit, {str(v["visitid"]): str(v["patientid"]) for v in unp}, prior_rows)
        os.makedirs(REGS, exist_ok=True); json.dump(baseline, open(bpath, "w"), indent=1)
    elif os.path.exists(bpath):
        try: baseline = json.load(open(bpath))
        except ValueError: baseline = None
    out["recovered"] = _wq.recovered_block(worked, pay_by_visit, _act, TODAY, {k: baseline.get(k) for k in ("rebills", "visits", "since", "until", "paid_visits", "paid_after", "unread")} if baseline else None)
for v in out["visits"]:   # keep the file small: the board shortens the reason text anyway
    if v.get("reason"): v["reason"] = str(v["reason"])[:160]
json.dump(out, open(OUT, "w"), separators=(",", ":"))
print("done: %d charts, %d denial lines, %d visits (%d actionable $%.2f; %d inside 12 months $%.2f); status %s; %d errors -> %s" % (
    n[0], len(lines), len(visits), len(act), out["actionable_amt"], len(timely), out["timely_amt"], dict(bystatus), len(errors), OUT), flush=True)
if out.get("recovered"): print(out["recovered"]["line"], flush=True)
