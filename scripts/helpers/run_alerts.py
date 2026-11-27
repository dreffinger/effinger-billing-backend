#!/usr/bin/env python3
# PLAIN ENGLISH (Run Alerts and the Payer Tracker - William 11/27/2026, from AdvancedMD's Claims Center 'Run Alerts' tab: "i like that as
#   an outline integrate that into ... the billing and cascade runs and posting success on the ehpa database site as a meaningful metric
#   because they should all be green showing paid claims it flags if no payment from the payer in a while"; then "if a payer hasnt paid in
#   some time it needs to go on the credentialing priority list ... all the payers listed, they should all be green soon and a warning says
#   go fix that credentialing payer because something went wrong"; then "run through all the era files to collect all the run reports and
#   era files ... all the data on that in the database for usefull questions ... like which payer hasnt paid since when")
# Decides: NOTHING in AdvancedMD. READ-ONLY there - the Run Alerts 'Complete' button (markclaimrunstatus) is never pressed.
# Reads, with AdvancedMD's own Run Alerts calls (class claimsreports, the three panes of that tab):
#   getclaimrunstatus   every open claim run: date, claims sent, dollars, excluded, dropped to paper, PAID (AdvancedMD's green check) and the
#                       alert ids it sets (2/3 no payment to the run / to one of its payers in 45+ days, 4 >= 5% excluded, 5 >= 7% to paper)
#   getclaimruncarriers the payer pane of one run: each payer's claims, dollars, paid or alert 6 'No insurance payment made by carrier in 45
#                       or more days' (claimrunuid = the run id)
#   getclaimrunhistory  the claim pane: per claim, 'Claim acknowledgement received', rejections and 'Payment received' with its date and who
#                       entered it (claimrunfid = run id, carrierfid = the payer pane row id, 0 = every payer)
#   and the ERA Center's unposted checks (GET /api/era/checks) and dismissed checks (GET /api/era/checks/dismiss?DismissedDateBegin=).
# Writes: the practice database (Neon, HIPAA): amd.claim_runs, amd.claim_run_payers, amd.claim_run_events, amd.era_checks - and the views
#   ehpa.payer_last_paid ("which payer has not paid since when") and ehpa.payer_tracker (one row per payer: GREEN paying / WARNING no
#   payment in 45+ days on claims that are due / NEVER PAID / WAITING, the reason, and whether it belongs on the credentialing priority
#   list). The workspace keeps the raw answers (runalerts/) so a night that is cut off resumes where it stopped.
# Rules it uses: AdvancedMD's own 45-day line; a payer is a WARNING only when claims sent to it 45+ days ago are unpaid AND nothing from it
#   has been paid (a 'Payment received' event, an ERA check, a posted payment) in the last 45 days - a payer that pays but left an older
#   run unpaid stays GREEN (those claims are the work queue's, not credentialing's). Revenue totals never go into the public repository:
#   the register it writes there (registers/payer_tracker_latest.json) holds payer codes, counts, dates and statuses only.
# Never touches: claims, payments, charts, the boards (the run hands the credentialing rows to board_ops like every other board change).
# ---
"""Usage (from the workspace, amd.py beside it or in scripts/helpers):
  python3 run_alerts.py pull  --ws <dir> [--full] [--max-calls N]   live read (resumable); --full = every run's history, not only what changed
  python3 run_alerts.py load  --ws <dir>                            parse runalerts/ and upsert into Neon (NEON_DATABASE_URL)
  python3 run_alerts.py tracker [--json <file>] [--register <file>] [--cred-ops <file> --board-rows cred_board_rows.json]
                                                                    the payer tracker from Neon; --cred-ops = Credentialing Board ops
  python3 run_alerts.py selftest"""
import collections, datetime, glob, json, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
A = sys.argv[1:]
def opt(n, d=None): return A[A.index(n) + 1] if n in A and A.index(n) + 1 < len(A) else d
def flag(n): return n in A

DUE_DAYS = 45                      # AdvancedMD's Run Alerts line: no payment in 45 or more days
ATTR = re.compile(r'(\w+)="([^"]*)"')


def attrs(tag): return dict(ATTR.findall(tag))
def tags(xml, name): return [attrs(t) for t in re.findall(r"<%s [^>]*>" % name, xml or "")]
def num(x):
    try: return float(x or 0)
    except (TypeError, ValueError): return 0.0
def day(s):
    s = (s or "")[:10]
    return datetime.date.fromisoformat(s) if re.match(r"^\d{4}-\d{2}-\d{2}$", s) else None


# ---------------------------------------------------------------- parsing (pure: the selftest feeds it fixtures)
def parse_status(xml):
    """getclaimrunstatus -> (alert definitions {id: text}, [run dicts])."""
    alerts = {a["id"]: a.get("description", "") for a in tags(xml, "alert")}
    runs = []
    for r in tags(xml, "claimrun"):
        runs.append({"run_id": int(r["id"]), "run_at": r.get("date"), "submitter": r.get("submittercode") or r.get("templatename"),
                     "run_type": r.get("runtype"), "amount": num(r.get("totalamount")), "sent": int(num(r.get("totalsent"))),
                     "paid": r.get("paymentcomplete") == "1", "alert_paid": r.get("alertpaymentcomplete") or None,
                     "excluded": int(num(r.get("totalexclusions"))), "alert_excluded": r.get("alerttotalexclusions") or None,
                     "to_paper": int(num(r.get("totaldroppedtopaper"))), "alert_paper": r.get("alerttotaldroppedtopaper") or None,
                     "exclusion_report": r.get("exclusionreportid") or None, "paper_report": r.get("droppedtopaperreportid") or None})
    return alerts, runs


def parse_carriers(run_id, xml):
    """getclaimruncarriers -> one dict per payer in the run (pane row id = carrier_fid, the history call's carrierfid)."""
    out = []
    for c in tags(xml, "alertinfo"):
        out.append({"run_id": run_id, "carrier_fid": int(c["id"]), "carrier_code": (c.get("carriercode") or "").strip(),
                    "carrier_name": c.get("carriername"), "amount": num(c.get("totalamount")), "sent": int(num(c.get("totalsent"))),
                    "paid": c.get("paymentmade") == "1", "alert_paid": c.get("alertpaymentcomplete") or None,
                    "excluded": int(num(c.get("totalexclusions"))), "to_paper": int(num(c.get("totaldroppedtopaper")))})
    return out


def parse_history(run_id, carrier_code, xml):
    """getclaimrunhistory -> one dict per tracking event. claimid = visit id + claim letter (A = first claim of the visit)."""
    out = []
    for e in tags(xml, "trackingevent"):
        m = re.match(r"^(\d+)([A-Z]*)$", e.get("claimid") or "")
        out.append({"event_uid": int(e["id"]), "run_id": run_id, "carrier_code": carrier_code, "claim_id": e.get("claimid"),
                    "visit_id": int(m.group(1)) if m else None, "claim_seq": (m.group(2) if m else None) or None,
                    "event_type": int(num(e.get("eventid"))), "description": e.get("eventdescription"), "event_at": e.get("eventdate"),
                    "report_id": e.get("reportid") or None, "is_problem": (e.get("isproblem") or "0") != "0", "note": e.get("note") or None})
    return out


def parse_era(unposted, dismissed):
    """ERA Center lists -> one dict per check (unposted ones carry the AdvancedMD payer code; dismissed ones only the ERA payer name)."""
    out = {}
    for c in dismissed or []:
        out[c["id"]] = {"check_id": c["id"], "status": "dismissed", "received_at": c.get("datereceived"), "check_date": (c.get("checkoreftdate") or "")[:10] or None,
                        "era_payer": c.get("carriername"), "carrier_code": None, "payment_number": c.get("paymentnumber"),
                        "payment_code": c.get("paymentcode"), "amount": num(c.get("checkoreftamount")), "claims_paid": num(c.get("claimpaymentamountsum")),
                        "unposted": None, "claim_count": c.get("claimcount"), "dismissed_at": c.get("dismissedat"), "changed_by": c.get("changedby")}
    for c in unposted or []:
        out[c["id"]] = {"check_id": c["id"], "status": "unposted", "received_at": c.get("receiveddate"), "check_date": (c.get("depositdate") or "")[:10] or None,
                        "era_payer": c.get("eracarriername"), "carrier_code": c.get("systemcarriercode"), "payment_number": c.get("paymentnumber"),
                        "payment_code": c.get("paymentcode"), "amount": num(c.get("paymentamount")), "claims_paid": num(c.get("calculatedamount")),
                        "unposted": num(c.get("unpostedamount")), "claim_count": None, "dismissed_at": None, "changed_by": None}
    return list(out.values())


# ---------------------------------------------------------------- live read
def _amd():
    sys.path.insert(0, HERE); sys.path.insert(0, os.getcwd())
    import amd
    return amd


def pull(ws, full=False, max_calls=600):
    amd = _amd(); d = os.path.join(ws, "runalerts"); os.makedirs(d, exist_ok=True)
    calls = [0]
    def post(action, at):
        if calls[0] >= max_calls: raise RuntimeError("call cap reached")
        calls[0] += 1
        t = amd.post(amd.msg(action, "claimsreports", at), timeout=25); time.sleep(0.4)
        if "<PPMDResults" not in t or "<Error" in t[:600]: raise RuntimeError("%s answered: %s" % (action, t[:300]))
        return t
    st = post("getclaimrunstatus", {"nocookie": "1"})
    _, runs = parse_status(st)
    if not runs: raise SystemExit("getclaimrunstatus listed no claim run - nothing changed on disk")
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H%MZ")
    open(os.path.join(d, "status_%s.xml" % stamp), "w").write(st)
    prev = {}
    pp = os.path.join(d, "panes_seen.json")
    if os.path.exists(pp): prev = json.load(open(pp))
    seen, todo, skipped = {}, [], 0
    today = datetime.datetime.now(datetime.timezone.utc).date()
    for r in runs:
        rid = r["run_id"]; f = os.path.join(d, "carriers_%d.xml" % rid)
        fresh = full or not os.path.exists(f) or not r["paid"] or (today - day(r["run_at"])).days <= 60
        try:
            x = post("getclaimruncarriers", {"claimrunuid": rid}) if fresh else open(f, encoding="latin-1").read()
        except Exception as e:
            print("  run %d payer pane: %s" % (rid, e)); skipped += 1; continue
        if fresh: open(f, "w").write(x)
        for c in parse_carriers(rid, x):
            key = "%d:%d" % (rid, c["carrier_fid"]); seen[key] = c["paid"]
            h = os.path.join(d, "history_%d_%d.xml" % (rid, c["carrier_fid"]))
            changed = prev.get(key) is None or prev.get(key) != c["paid"]
            stale = not os.path.exists(h) or (time.time() - os.path.getmtime(h)) > 7 * 86400
            if full and not os.path.exists(h) or changed or (not c["paid"] and stale):
                todo.append((rid, c["carrier_fid"], h))
    for rid, cfid, h in todo:
        try:
            open(h, "w").write(post("getclaimrunhistory", {"claimrunfid": rid, "carrierfid": cfid}))
        except Exception as e:
            print("  run %d payer %d history: %s" % (rid, cfid, e)); skipped += 1
            if "call cap" in str(e): break
    if full:
        for r in runs:
            h = os.path.join(d, "history_%d_0.xml" % r["run_id"])
            if os.path.exists(h): continue
            try: open(h, "w").write(post("getclaimrunhistory", {"claimrunfid": r["run_id"], "carrierfid": 0}))
            except Exception as e:
                print("  run %d history: %s" % (r["run_id"], e)); skipped += 1
                if "call cap" in str(e): break
    json.dump(seen, open(pp, "w"))
    # the ERA Center: unposted now, dismissed since 2023 (a dismissed check never comes back to the unposted list)
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "billing", "era"))
        import era_post, requests
        json.dump(era_post.checks(), open(os.path.join(d, "era_unposted.json"), "w"))
        r_ = requests.get(era_post.API + "/era/checks/dismiss?DismissedDateBegin=2023-01-01", headers=era_post.H(), timeout=180); r_.raise_for_status()
        json.dump(r_.json(), open(os.path.join(d, "era_dismissed.json"), "w"))
    except Exception as e:
        print("  ERA Center lists: %s" % e); skipped += 1
    print("run alerts pull %s: %d runs, %d payer histories asked, %d calls, %d skipped (run it again to finish)" % (stamp, len(runs), len(todo), calls[0], skipped))


# ---------------------------------------------------------------- the practice database (Neon)
DDL = [
    """create table if not exists amd.claim_runs (run_id bigint primary key, run_at timestamp, submitter text, run_type text,
         amount numeric(12,2), sent int, paid boolean, alert_paid text, excluded int, alert_excluded text, to_paper int, alert_paper text,
         exclusion_report text, paper_report text, open boolean default true, first_seen timestamptz default now(), last_seen timestamptz default now())""",
    """create table if not exists amd.claim_run_payers (run_id bigint, carrier_fid bigint, carrier_code text, carrier_name text,
         amount numeric(12,2), sent int, paid boolean, alert_paid text, excluded int, to_paper int, paid_seen_at timestamptz,
         first_seen timestamptz default now(), last_seen timestamptz default now(), primary key (run_id, carrier_fid))""",
    """create table if not exists amd.claim_run_events (event_uid bigint primary key, run_id bigint, carrier_code text, claim_id text,
         visit_id bigint, claim_seq text, event_type int, description text, event_at timestamp, report_id text, is_problem boolean,
         note text, loaded_at timestamptz default now())""",
    "create index if not exists claim_run_events_visit on amd.claim_run_events (visit_id)",
    "create index if not exists claim_run_events_payer on amd.claim_run_events (carrier_code, event_type, event_at)",
    """create table if not exists amd.era_checks (check_id bigint primary key, status text, received_at timestamp, check_date date,
         era_payer text, carrier_code text, payment_number text, payment_code text, amount numeric(12,2), claims_paid numeric(12,2),
         unposted numeric(12,2), claim_count int, dismissed_at timestamp, changed_by text, first_seen timestamptz default now(),
         last_seen timestamptz default now())""",
    "create table if not exists amd.era_payer_map (era_payer text primary key, carrier_code text, checks int, source text)",
    # which payer has not paid since when: the newest of a 'Payment received' on a claim run, an ERA check with money, a posted payment
    """create or replace view amd.payer_last_paid as
       with ev as (select carrier_code, max(event_at)::date last_payment_event from amd.claim_run_events
                   where event_type = 7 and carrier_code is not null group by 1),
            era as (select coalesce(e.carrier_code, m.carrier_code) carrier_code, max(e.check_date) last_era_check,
                           count(*) filter (where e.check_date >= current_date - 90) era_checks_90d
                    from amd.era_checks e left join amd.era_payer_map m on m.era_payer = e.era_payer
                    where e.amount > 0 group by 1),
            posted as (select carrier carrier_code, max(payment_date) last_posted_payment from amd.v_payments
                       where not coalesce(void, false) and paid > 0 and source = '2' group by 1),
            codes as (select carrier_code from ev union select carrier_code from era union select carrier_code from posted
                      union select carrier_code from amd.claim_run_payers)
       select c.carrier_code, ev.last_payment_event, era.last_era_check, era.era_checks_90d, posted.last_posted_payment,
              case when greatest(ev.last_payment_event, era.last_era_check, posted.last_posted_payment) is not null      -- LEAST skips nulls: never-paid stays null
                   then least(greatest(ev.last_payment_event, era.last_era_check, posted.last_posted_payment), current_date) end last_paid,
              current_date - least(greatest(ev.last_payment_event, era.last_era_check, posted.last_posted_payment), current_date) days_since_paid
       from codes c left join ev using (carrier_code) left join era using (carrier_code) left join posted using (carrier_code)
       where c.carrier_code is not null and c.carrier_code <> ''""",
    # one row per payer on the open claim runs: AdvancedMD's 45-day line, and the credentialing flag (William 11/27/2026)
    """create or replace view amd.payer_tracker as
       with pa as (select p.carrier_code, max(p.carrier_name) carrier_name, count(*) runs, sum(p.sent) claims_sent, sum(p.amount) billed,
                          count(*) filter (where p.paid) runs_paid,
                          count(*) filter (where not p.paid and r.run_at::date <= current_date - 45) runs_unpaid_due,
                          sum(p.amount) filter (where not p.paid and r.run_at::date <= current_date - 45) unpaid_due_billed,
                          min(r.run_at::date) filter (where not p.paid and r.run_at::date <= current_date - 45) oldest_unpaid_due,
                          count(*) filter (where not p.paid and r.run_at::date > current_date - 45) runs_waiting,
                          max(r.run_at::date) newest_run, max(r.run_at::date) filter (where p.paid) newest_paid_run
                   from amd.claim_run_payers p join amd.claim_runs r using (run_id) where r.open group by 1)
       select pa.*, l.last_paid, l.days_since_paid, l.last_payment_event, l.last_era_check, l.last_posted_payment,
              case when coalesce(pa.runs_unpaid_due, 0) = 0
                        then case when pa.runs_paid = 0 and l.last_paid is null then 'WAITING' else 'GREEN' end
                   when l.last_paid >= current_date - 45 then 'GREEN'
                   when l.last_paid is null then 'NEVER PAID'
                   else 'WARNING' end status,
              case when coalesce(pa.runs_unpaid_due, 0) = 0 then case when pa.runs_paid = 0 and l.last_paid is null
                        then 'claims sent less than 45 days ago, no payment yet' else 'paying' end
                   when l.last_paid >= current_date - 45 then 'paying (last paid ' || l.last_paid || '); ' || pa.runs_unpaid_due
                        || ' older run(s) unpaid - the work queue''s'
                   when l.last_paid is null then 'no payment on record; claims unpaid since ' || pa.oldest_unpaid_due
                   else 'no payment since ' || l.last_paid || '; claims unpaid since ' || pa.oldest_unpaid_due end reason
       from pa left join amd.payer_last_paid l using (carrier_code)""",
]


def db():
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "credentialing")); sys.path.insert(0, HERE)
    saved = sys.argv[:]; sys.argv = sys.argv[:1]
    try:
        import cred_vault
    finally:
        sys.argv = saved
    return cred_vault.DB()


def _bulk(d, table, cols, key, rows, update, chunk=1500):
    """Upsert rows (dicts) in chunks through jsonb_to_recordset - one statement per chunk."""
    types = {"run_id": "bigint", "carrier_fid": "bigint", "event_uid": "bigint", "visit_id": "bigint", "check_id": "bigint", "sent": "int",
             "excluded": "int", "to_paper": "int", "event_type": "int", "claim_count": "int", "amount": "numeric", "claims_paid": "numeric",
             "unposted": "numeric", "paid": "boolean", "is_problem": "boolean", "run_at": "timestamp", "event_at": "timestamp",
             "received_at": "timestamp", "dismissed_at": "timestamp", "check_date": "date"}
    spec = ", ".join("%s %s" % (c, types.get(c, "text")) for c in cols)
    sets = ", ".join("%s = excluded.%s" % (c, c) for c in update)
    for i in range(0, len(rows), chunk):
        part = [{c: r.get(c) for c in cols} for r in rows[i:i + chunk]]
        d.q("insert into %s (%s) select %s from jsonb_to_recordset(%%s::jsonb) as x(%s) on conflict (%s) do update set %s%s"
            % (table, ", ".join(cols), ", ".join(cols), spec, key, sets, ", last_seen = now()" if table != "amd.claim_run_events" else ""),
            [json.dumps(part)])


def load(ws):
    d = db(); r_ = os.path.join(ws, "runalerts")
    for s in DDL: d.q(s)
    sts = sorted(glob.glob(os.path.join(r_, "status_*.xml")))
    if not sts: sys.exit("no status_*.xml in %s - run pull first" % r_)
    _, runs = parse_status(open(sts[-1], encoding="latin-1").read())
    _bulk(d, "amd.claim_runs", ["run_id", "run_at", "submitter", "run_type", "amount", "sent", "paid", "alert_paid", "excluded",
                               "alert_excluded", "to_paper", "alert_paper", "exclusion_report", "paper_report"], "run_id", runs,
          ["run_at", "submitter", "run_type", "amount", "sent", "paid", "alert_paid", "excluded", "alert_excluded", "to_paper",
           "alert_paper", "exclusion_report", "paper_report"])
    ids = [r["run_id"] for r in runs]
    d.q("update amd.claim_runs set open = (run_id = any(%s::bigint[]))", ["{%s}" % ",".join(map(str, ids))])
    panes, code_of, events = [], {}, {}
    for rid in ids:
        f = os.path.join(r_, "carriers_%d.xml" % rid)
        if not os.path.exists(f): continue
        for c in parse_carriers(rid, open(f, encoding="latin-1").read()):
            panes.append(c); code_of[(rid, c["carrier_fid"])] = c["carrier_code"]
    _bulk(d, "amd.claim_run_payers", ["run_id", "carrier_fid", "carrier_code", "carrier_name", "amount", "sent", "paid", "alert_paid",
                                      "excluded", "to_paper"], "run_id, carrier_fid", panes,
          ["carrier_code", "carrier_name", "amount", "sent", "paid", "alert_paid", "excluded", "to_paper"])
    d.q("update amd.claim_run_payers set paid_seen_at = now() where paid and paid_seen_at is null")
    claim_payer = {}
    for f in sorted(glob.glob(os.path.join(r_, "history_*_*.xml"))):
        m = re.search(r"history_(\d+)_(\d+)\.xml$", f); rid, cfid = int(m.group(1)), int(m.group(2))
        code = code_of.get((rid, cfid)) if cfid else None
        for e in parse_history(rid, code, open(f, encoding="latin-1").read()):
            if code: claim_payer[(rid, e["claim_id"])] = code
            if e["event_uid"] not in events or code: events[e["event_uid"]] = e
    for e in events.values():                      # the run-wide pane names no payer: the claim's payer from its payer pane
        if not e["carrier_code"]: e["carrier_code"] = claim_payer.get((e["run_id"], e["claim_id"]))
    _bulk(d, "amd.claim_run_events", ["event_uid", "run_id", "carrier_code", "claim_id", "visit_id", "claim_seq", "event_type",
                                      "description", "event_at", "report_id", "is_problem", "note"], "event_uid", list(events.values()),
          ["carrier_code", "description", "event_at", "report_id", "is_problem", "note"])
    up = os.path.join(r_, "era_unposted.json"); dm = os.path.join(r_, "era_dismissed.json")
    era = parse_era(json.load(open(up)) if os.path.exists(up) else [], json.load(open(dm)) if os.path.exists(dm) else [])
    _bulk(d, "amd.era_checks", ["check_id", "status", "received_at", "check_date", "era_payer", "carrier_code", "payment_number",
                                "payment_code", "amount", "claims_paid", "unposted", "claim_count", "dismissed_at", "changed_by"], "check_id", era,
          ["status", "received_at", "check_date", "era_payer", "carrier_code", "payment_number", "payment_code", "amount", "claims_paid",
           "unposted", "claim_count", "dismissed_at", "changed_by"])
    # an ERA payer name -> AdvancedMD payer code: the unposted list names both; a dismissed check by its payment number posted in AdvancedMD
    d.q("""insert into amd.era_payer_map (era_payer, carrier_code, checks, source)
           select distinct on (era_payer) era_payer, carrier_code, n, src from (
             select era_payer, carrier_code, count(*) n, 'era center' src, 0 pri
             from amd.era_checks where carrier_code is not null and era_payer is not null group by 1, 2
             union all
             select e.era_payer, v.carrier, count(*), 'posted check number', 1
             from amd.era_checks e join (select distinct check_number, carrier from amd.v_payments where carrier is not null and check_number <> '') v
               on v.check_number = e.payment_number where e.era_payer is not null group by 1, 2) x
           order by era_payer, pri, n desc on conflict (era_payer) do update set carrier_code = excluded.carrier_code, checks = excluded.checks, source = excluded.source""")
    print("loaded: %d open runs, %d payer panes, %d claim events, %d ERA checks" % (len(runs), len(panes), len(events), len(era)))


def tracker(js=None, register=None):
    d = db()
    rows = d.q("""select carrier_code, carrier_name, status, reason, last_paid, days_since_paid, runs, runs_paid, runs_unpaid_due,
                         runs_waiting, claims_sent, unpaid_due_billed, oldest_unpaid_due, newest_run
                  from amd.payer_tracker order by case status when 'NEVER PAID' then 0 when 'WARNING' then 1 when 'WAITING' then 2 else 3 end,
                           unpaid_due_billed desc nulls last""")
    cols = ["carrier_code", "carrier_name", "status", "reason", "last_paid", "days_since_paid", "runs", "runs_paid", "runs_unpaid_due",
            "runs_waiting", "claims_sent", "unpaid_due_billed", "oldest_unpaid_due", "newest_run"]
    out = [dict(zip(cols, r)) for r in rows]
    for o in out:
        print("%-10s %-11s %-34s last paid %-10s %s" % (o["carrier_code"], o["status"], (o["carrier_name"] or "")[:34], o["last_paid"] or "never", o["reason"]))
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if js: json.dump({"schema": "payer-tracker/1", "at": now, "payers": out}, open(js, "w"), indent=1, default=str)
    if register:      # the public repository: codes, counts, dates and statuses - never a dollar
        safe = [{k: o[k] for k in cols if k not in ("unpaid_due_billed",)} for o in out]
        json.dump({"schema": "payer-tracker/1", "at": now, "rule": "WARNING = claims 45+ days old unpaid and nothing from the payer paid in 45 days",
                   "payers": safe}, open(register, "w"), indent=1, default=str)
    c = collections.Counter(o["status"] for o in out)
    print("payers: %s" % ", ".join("%d %s" % (v, k) for k, v in c.most_common()))
    return out


def cred_ops(out, board_rows=None, today=None):
    """William 11/27/2026: "if a payer hasnt paid in some time it needs to go on the credentialing priority list ... a warning says go fix that
    credentialing payer". -> Credentialing Board ops (collection cred, the BOARD ACCESS RULE's op format): one card per WARNING / NEVER PAID
    payer, id pay-alert-<code>, on William's turn, due in 7 days, with the reason; a payer back to GREEN whose card is still open gets a
    'paying again' note and turn done. board_rows: the cred collection as the run read it (cred_board_rows.json: [{id, turn, ...}])."""
    today = today or datetime.date.today(); at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    open_cards = {r.get("id"): r for r in (board_rows or []) if str(r.get("id") or "").startswith("pay-alert-") and r.get("turn") != "done"}
    ops = []
    for o in out:
        cid = "pay-alert-" + re.sub(r"[^a-z0-9]", "", str(o["carrier_code"]).lower())
        if o["status"] in ("WARNING", "NEVER PAID"):
            if cid in open_cards: continue                       # already on his list - one card per payer, no repeat note every night
            ops.append({"op": "upsert", "collection": "cred", "id": cid,
                        "set": {"name": "%s (%s) - %s" % (o["carrier_name"] or o["carrier_code"], o["carrier_code"],
                                                          "never paid" if o["status"] == "NEVER PAID" else "no payment in 45+ days"),
                                "turn": "william", "due": (today + datetime.timedelta(days=7)).isoformat(),
                                "need": "%s. Check: is the group/clinician enrolled and in network with this payer, is its ERA/EFT set up "
                                        "to this practice, and why its claims go unpaid (claim status)." % o["reason"]},
                        "append": {"notes": [{"who": "Claude", "at": at, "text": "Run alerts %s: %s - %d claim run(s) unpaid 45+ days, oldest %s "
                                              "(AdvancedMD Claims Center > Run Alerts)." % (today.isoformat(), o["reason"], int(float(o["runs_unpaid_due"] or 0)),
                                                                                          o["oldest_unpaid_due"])}]}})
        elif cid in open_cards and o["status"] == "GREEN":
            ops.append({"op": "update", "collection": "cred", "id": cid, "set": {"turn": "done"},
                        "append": {"notes": [{"who": "Claude", "at": at, "text": "Paying again: last paid %s (run alerts %s)." % (o["last_paid"], today.isoformat())}]}})
    return {"schema": "cred-board-updates/1", "source": "run_alerts.py tracker %s" % at, "ops": ops}


def selftest():
    st = ('<Results><alertlist><alert id="2" description="No insurance payment made to claim run in 45 or more days" /></alertlist><claimrunlist>'
          '<claimrun id="1700001" date="2026-08-01T21:00:00.000" submittercode="MCKGRP" runtype="E" totalamount="100.50" totalsent="3" '
          'paymentcomplete="0" totaldroppedtopaper="0" totalexclusions="1" alertpaymentcomplete="3" alerttotaldroppedtopaper="" '
          'alerttotalexclusions="4" droppedtopaperreportid="" exclusionreportid="77" /></claimrunlist></Results>')
    alerts, runs = parse_status(st)
    assert alerts == {"2": "No insurance payment made to claim run in 45 or more days"}
    assert runs[0]["run_id"] == 1700001 and runs[0]["paid"] is False and runs[0]["alert_paid"] == "3" and runs[0]["amount"] == 100.5
    assert runs[0]["alert_excluded"] == "4" and runs[0]["alert_paper"] is None and runs[0]["exclusion_report"] == "77"
    ca = parse_carriers(1700001, '<alertlistinfo><alertinfo id="6085" carriercode="FLO02 " carriername="FLORIDA MEDICARE" totalamount="9" '
                                 'totalsent="2" paymentmade="1" totaldroppedtopaper="0" totalexclusions="0" alertpaymentcomplete="" /></alertlistinfo>')
    assert ca[0]["carrier_code"] == "FLO02" and ca[0]["paid"] is True and ca[0]["alert_paid"] is None and ca[0]["carrier_fid"] == 6085
    hi = parse_history(1700001, "FLO02", '<trackingevent eventdate="2026-11-25T10:54:26.143" id="5" claimid="19461428A" eventid="7" '
                                         'eventdescription="Payment received" reportid="" isproblem="0" note="PAYMENT ENTERED BY X"/>')
    assert hi[0]["visit_id"] == 19461428 and hi[0]["claim_seq"] == "A" and hi[0]["event_type"] == 7 and hi[0]["report_id"] is None
    er = parse_era([{"id": 1, "receiveddate": "2026-11-25T17:03:10", "depositdate": "2026-11-24T00:00:00", "eracarriername": "HUMANA INC.",
                     "systemcarriercode": "HUM01", "paymentnumber": "9", "paymentamount": 171.41, "unpostedamount": 88.28}],
                   [{"id": 1, "checkoreftdate": "2026-01-02T00:00:00", "carriername": "OLD"}, {"id": 2, "checkoreftdate": "2025-05-22T00:00:00",
                     "carriername": "STATE OF FLORIDA MEDICAID", "checkoreftamount": 0.0, "claimcount": 163}])
    by = {e["check_id"]: e for e in er}
    assert by[1]["status"] == "unposted" and by[1]["carrier_code"] == "HUM01" and by[1]["check_date"] == "2026-11-24"   # unposted wins
    assert by[2]["status"] == "dismissed" and by[2]["carrier_code"] is None and by[2]["claim_count"] == 163
    for s in DDL: assert "drop " not in s.lower() and "delete " not in s.lower()
    t = datetime.date(2026, 11, 27)
    rows = [{"carrier_code": "CIG09", "carrier_name": "CIGNA", "status": "WARNING", "reason": "no payment since 2026-09-04", "runs_unpaid_due": 15,
             "oldest_unpaid_due": "2026-07-20", "last_paid": "2026-09-04"},
            {"carrier_code": "BCBS", "carrier_name": "FLORIDA BLUE", "status": "GREEN", "reason": "paying", "runs_unpaid_due": 0, "oldest_unpaid_due": None,
             "last_paid": "2026-11-20"},
            {"carrier_code": "GEH04", "carrier_name": "GEHA", "status": "NEVER PAID", "reason": "no payment on record", "runs_unpaid_due": 2,
             "oldest_unpaid_due": "2026-09-01", "last_paid": None}]
    doc = cred_ops(rows, [{"id": "pay-alert-bcbs", "turn": "william"}, {"id": "pay-alert-geh04", "turn": "william"}], t)
    ids = [(o["op"], o["id"]) for o in doc["ops"]]
    assert ids == [("upsert", "pay-alert-cig09"), ("update", "pay-alert-bcbs")], ids          # GEHA already on his list: no repeat
    assert doc["ops"][0]["set"]["turn"] == "william" and doc["ops"][0]["set"]["due"] == "2026-12-04" and doc["ops"][1]["set"] == {"turn": "done"}
    print("run_alerts selftest: ok")


if __name__ == "__main__":
    cmd = A[0] if A else "help"
    if cmd == "pull": pull(opt("--ws", "/home/claude/unbilled"), flag("--full"), int(opt("--max-calls", "600")))
    elif cmd == "load": load(opt("--ws", "/home/claude/unbilled"))
    elif cmd == "tracker":
        out = tracker(opt("--json"), opt("--register"))
        if opt("--cred-ops"):
            rows = json.load(open(opt("--board-rows"))) if opt("--board-rows") and os.path.exists(opt("--board-rows")) else []
            doc = cred_ops(out, rows); json.dump(doc, open(opt("--cred-ops"), "w"), indent=1, default=str)
            print("credentialing board: %d op(s) -> %s" % (len(doc["ops"]), opt("--cred-ops")))
    elif cmd == "selftest": selftest()
    else: sys.exit(__doc__)
