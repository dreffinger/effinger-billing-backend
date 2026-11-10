# PLAIN ENGLISH (Weekly claim-status check BY NEED - rewritten 11/10/2026, look-ups part A step 2)
# Decides: which unpaid claims get a paid Stedi claim-status check (276/277) tonight - ONLY the claims that are due by the rules in
#   cs_rules.py, read from tonight's ageing file (aging_latest.json, written by aging_refresh.py) and the shared ledger
#   (registers/claim_status_ledger.json) - and how each answer is read. It records the payer's answer; it never acts on it.
# Rules it uses: cs_rules.py - due by need (nothing posted for the payer, last sent 45+ days ago / 60 for a secondary balance, under a
#   year old, a working route, and the ledger says neither wait nor stop); the waits; two unusable or three 'pending' answers in a row =
#   stop and hand off; payers whose claim status does not work are never sent; 150 checks or $25 a run, 400 checks or $100 a month; a
#   final answer only when it names this claim or was asked with the exact date (a 3-day-window answer that does not name the claim, or a
#   'not matched' answer, gets ONE check with the exact date). A live run needs the word --go: without it the helper prints what it WOULD
#   ask and makes no call of any kind (10/6 and 10/17/2026: a probe for the usage text started the old helper and bought up to 100
#   checks). --help prints and exits; an unknown word is an error and nothing is asked. A missing or stale ageing file, or a missing or
#   unreadable ledger, ends the run with an error and no call - never a fall-back to the largest balances. Every check goes through the
#   vendor client's door (stedi._post), so it leaves its line in the usage log (look-ups part A, step 1).
#   The runbook acts on the answers as before (paid -> post or write off as paid-not-posted, denied -> denial work, not found -> resend);
#   a 'not eligible' answer is no longer a resend candidate - it goes to the insurance check.
# Never touches: AMD writes, balances, claims. Writes claimstatus_<date>.json (chart and visit ids, no names), the ledger, an unusable raw
#   reply under patient_db/claimstatus_raw/ (never in git), and prints the run report: what was asked and answered, the hand-off list
#   with age and dollars, the insurance-check list, payers left out, wordings the rules do not know, the caps, and the claims silent 60+ days.
# ---
"""Usage: python3 claim_status_sweep.py [--go] [--aging aging_latest.json] [--ledger PATH] [--new-ledger] [--carriers A,B] [--max N]
Reads tonight's ageing file and the claim-status ledger and lists the claims that are DUE for a claim-status check (cs_rules.py).
Without --go it prints that list and makes no call. With --go it asks them, within the caps, and records every answer."""
import amd, stedi, json, re, sys, os, time, datetime, argparse, collections
import cs_rules
from precheck import CAR2STEDI, CARRIERS, plans
STEDI_CS = stedi.API + "/change/medicalnetwork/claimstatus/v2"
WHO = "claim-status sweep"

def request_body(payer, first, last, dob, member, dos, amount, exact=False):
    """The 276 request: the group billing provider, the chart's member id, the date of service plus and minus 3 days (or the exact date)."""
    d = datetime.datetime.strptime(dos, "%Y%m%d").date(); w = datetime.timedelta(days=0 if exact else 3)
    return {"tradingPartnerServiceId": payer, "providers": [{"npi": stedi.PROV["npi"], "organizationName": stedi.PROV["organizationName"], "providerType": "BillingProvider"}],
            "subscriber": {"firstName": first, "lastName": last, "dateOfBirth": dob, "memberId": member},
            "encounter": {"beginningDateOfService": (d - w).strftime("%Y%m%d"), "endDateOfService": (d + w).strftime("%Y%m%d"), "submittedAmount": "%.2f" % amount}}
def status(payer, first, last, dob, member, dos, amount, exact=False, pid=None, who=None):
    """ONE paid claim-status check through the vendor client's door (one usage-log line) -> (reply code, answer). An HTTP error comes back
    with whatever answer was sent (the vendor does not bill it); a time-out or an unreadable reply raises."""
    body = request_body(payer, first, last, dob, member, dos, amount, exact)
    with stedi._asking(pid, who or stedi.WHO):
        try: return 200, stedi._post(STEDI_CS, body)
        except Exception as e:
            resp = getattr(e, "response", None); code = getattr(resp, "status_code", None)
            if not code: raise
            try: j = resp.json()
            except Exception: j = None
            return code, j
def action(res, L):
    """The run file's action words. The runbook and the dated follow-up helpers read the start: PAID / FINALIZED / DENIED / PENDING /
    NOT ON FILE as before; everything else (HAND OFF, NOT MATCHED, NOT ELIGIBLE, NO USABLE ANSWER, UNCONFIRMED) is listed, never resent."""
    lab = res["label"]; stopped = bool(L.get("stopped"))
    if lab in cs_rules.FINAL and not res.get("final"):
        return "UNCONFIRMED %s - the 3-day window did not name this claim; one check with the exact date is due" % ("PAID $%.2f" % res["paid"] if lab == cs_rules.PAID else lab.upper())
    if lab == cs_rules.PAID: return "PAID $%.2f - find/post the ERA (check %s)" % (res["paid"], ",".join(sorted({p["check"] for p in res["payments"] if p.get("check")})[:3]))
    if lab == cs_rules.FINAL0: return "FINALIZED $0 - denial, run the cascade"
    if lab == cs_rules.DENIED: return "DENIED/REVISED - run the denial cascade"
    if stopped: return "HAND OFF - %s: ask the payer by portal or phone" % (L.get("stop_why") or res["why"])
    if lab == cs_rules.PENDING: return "PENDING at payer - wait"
    if lab == cs_rules.NOT_FOUND: return "NOT ON FILE - claim not found at the payer - resend as original"
    if lab == cs_rules.NOT_MATCHED: return "NOT MATCHED (%s) - one check with the exact date of service is next" % res["why"]
    if lab == cs_rules.NOT_ELIGIBLE: return "NOT ELIGIBLE on the date of service - insurance check (the STEP 1 cascade), never a resend"
    return "NO USABLE ANSWER (%s) - asked again in %d days" % (res["why"], cs_rules.WAITS["no usable answer"])
def _who_line(r, today):
    return "pat%s v%s %s DOS %s - %s" % (r.get("pid"), r.get("visitid"), r.get("payer"), str(r.get("dos"))[:10], cs_rules.age_and_dollars(r, today))

def parse(argv, prog, doc, exact_helper=False):
    ap = argparse.ArgumentParser(prog=prog, description=doc, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False)
    if exact_helper:
        g = ap.add_mutually_exclusive_group(required=True)
        g.add_argument("--vids", help="the visit ids to ask, comma separated")
        g.add_argument("--from-disposition", metavar="STAMP", help="the visits of old_claims_disposition_<STAMP>.json in the --tiers")
        ap.add_argument("--tiers", default="POST-277,WO-PAID-NOREMIT", help="tiers taken from the disposition file (default POST-277,WO-PAID-NOREMIT)")
        ap.add_argument("--out", default=None, help="the output file (default claimstatus_exact_<stamp>.json)")
    ap.add_argument("--go", action="store_true", help="make the paid checks; without it the helper only prints what it would ask (no call of any kind)")
    ap.add_argument("--aging", default="aging_latest.json", help="tonight's ageing file from aging_refresh.py (default aging_latest.json here); older than one day = nothing is asked")
    ap.add_argument("--ledger", default=None, help="the claim-status ledger (default $CLAIM_STATUS_LEDGER or registers/claim_status_ledger.json beside this helper)")
    ap.add_argument("--new-ledger", action="store_true", help="the very first run only: start the ledger where none exists (an existing ledger is never replaced)")
    if not exact_helper: ap.add_argument("--carriers", default="", help="only claims of these payer codes, comma separated (default: every payer with a claim-status route)")
    ap.add_argument("--max", type=int, default=None, help="at most N checks this run (never more than the run cap of %d)" % cs_rules.CAPS["run checks"])
    return ap.parse_args(argv)

def run(o, prog, vids=None, force_exact=False, keep_every_raw=False):
    """The shared run of the claim-status helpers -> (exit code, run rows, report lines). No call before the ageing file and the ledger
    are read and found good; with o.go False no call of any kind (no AdvancedMD login, no vendor check)."""
    stedi.WHO = WHO if prog == "claim_status_sweep.py" else prog.replace(".py", "").replace("_", " ")
    today = datetime.date.today(); now = datetime.datetime.now(datetime.timezone.utc); stamp = now.strftime("%Y-%m-%dT%H%MZ"); month = today.strftime("%Y-%m")
    say = []
    def p(line=""): say.append(line); print(line, flush=True)
    try: rows, asof = cs_rules.aging_rows(o.aging, now)
    except cs_rules.AgingError as e: p("STOPPED: %s" % e); return 2, [], say
    try: led = cs_rules.Ledger.open(o.ledger, new=o.new_ledger)
    except (cs_rules.LedgerMissing, cs_rules.LedgerBroken) as e: p("STOPPED: %s" % e); return 2, [], say
    carriers = [c.strip() for c in (getattr(o, "carriers", "") or "").split(",") if c.strip()]
    pl = cs_rules.plan(rows, led.rows(), today, CAR2STEDI, carriers=carriers, vids=vids)
    due = pl["due"]; caps = cs_rules.Caps(led.month_checks(month), o.max)
    p("%s - claim-status check by need, %s (ageing file of %s: %d unpaid claims; ledger %s)" % (prog, today.isoformat(), asof.strftime("%Y-%m-%d %H:%M UTC"), pl["rows"], led.path))
    p("  claims silent 60 or more days since they were last sent, with nothing posted for their payer: %d" % pl["silent60"])
    p("  due tonight: %d; not due: %s" % (len(due), ", ".join("%s %d" % kv for kv in pl["waits"].most_common()) or "none") + ("; rows lacking a field: %d" % pl["skipped"] if pl["skipped"] else ""))
    p("  this month before tonight: %d checks, $%.2f at list price (caps: %d checks or $%.2f a run, %d checks or $%.2f a month)" % (caps.before, cs_rules.price(caps.before),
      caps.run_cap, cs_rules.CAPS["run dollars"], cs_rules.CAPS["month checks"], cs_rules.CAPS["month dollars"]))
    if pl["payer_off"]:
        p("  PAYER SWITCHED OFF - their claim status does not work; ask by portal or phone (%d):" % len(pl["payer_off"]))
        for d in pl["payer_off"][:40]: p("    " + _who_line(d["row"], today) + " - " + d["why"].split(" - ")[0])
    for d in pl["not_due"]: p("  not asked: " + _who_line(d["row"], today) + " - " + d["why"])
    for v in sorted(set(re.sub(r"\D", "", str(v)) for v in (vids or [])) - pl["found"]): p("  not asked: v%s - not on tonight's ageing file" % v)
    if pl["handed_off"]:
        p("  STILL ON THE HAND-OFF LIST - ask the payer by portal or phone (%d):" % len(pl["handed_off"]))
        for d in pl["handed_off"][:60]: p("    " + _who_line(d["row"], today) + " - handed off %s: %s" % (d["ledger"].get("stopped"), d["ledger"].get("stop_why")))
    if not o.go:
        sim = cs_rules.Caps(caps.before, o.max); fit = 0
        while fit < len(due) and sim.next_ok()[0]: sim.count(); fit += 1
        p("DRY RUN - nothing was asked and no call was made (add --go to ask). %d claim(s) are due; the caps would let %d be asked tonight%s:" % (len(due), fit, "" if fit == len(due) else " (%s)" % sim.next_ok()[1]))
        for d in due[:80]: p("    " + _who_line(d["row"], today) + " - %s%s" % (d["why"], " [exact date]" if d["exact"] or force_exact else ""))
        if len(due) > 80: p("    ... and %d more" % (len(due) - 80))
        return 1, [], say
    amd.login_cached()
    out = []; answers = []; left = collections.Counter(); bad = collections.Counter(); stopped_payers = {}; cache = {}; tally = collections.Counter(); unknown = collections.Counter()
    exact_made = 0; finals = 0; no_member = []; code = 0
    def ask(d, r, payer_id, exact):
        pid = str(r.get("pid") or ""); vid = str(r.get("visitid") or "")
        if pid not in cache:
            try: cache[pid] = plans(pid)
            except Exception as e: cache[pid] = None
        if not cache[pid]: return None, "chart record not read"
        pa, chart_plans = cache[pid]; nm_ = pa.get("name") or ""
        last, first = nm_.split(",")[0].strip(), nm_.split(",")[-1].strip().split(" ")[0]
        dob = pa.get("dob", ""); dobc = dob[6:] + dob[:2] + dob[3:5] if dob else ""
        mine = [x for x in chart_plans if x[1] == CARRIERS.get(str(r.get("payer") or "").strip())]; member = mine[0][4] if mine else ""
        if not (member and last and first and dobc): return None, "no plan for this payer on the chart (no member id)" if not member else "no name or birth date on the chart"
        try: http, j = status(payer_id, first, last, dobc, member, str(r.get("dos"))[:10].replace("-", ""), cs_rules._money(r.get("fee")) or cs_rules._money(r.get("bal")), exact, pid)
        except Exception as e:                                   # no answer: a time-out, a refused connection, or a reply that came (2xx) but cannot be read
            unreadable = isinstance(e, ValueError)
            err = "time-out" if "timeout" in type(e).__name__.lower() else "reply not readable" if unreadable else type(e).__name__
            return cs_rules.label(None, http="2xx" if unreadable else None, error=err, vid=vid, dos=r.get("dos"), exact=exact), None
        return cs_rules.label(j, http=http, vid=vid, dos=r.get("dos"), exact=exact), j
    for d in due:
        r = d["row"]; k = d["key"]; payer_id = d["payer_id"]; exact = bool(d["exact"] or force_exact)
        rec = {"visitid": str(r.get("visitid")), "patientid": str(r.get("pid")), "carrier": str(r.get("payer")), "payer": payer_id, "dos": str(r.get("dos"))[:10], "balance": cs_rules._money(r.get("bal")),
               "sent": str(r.get("sent") or "")[:10], "why": d["why"], "asked": stamp}
        if payer_id in stopped_payers:
            why = "%s gave %d unusable answers in a row tonight" % (payer_id, cs_rules.PAYER_RUN_STOP); left[why] += 1; rec["action"] = "NOT ASKED - " + why; out.append(rec); continue
        ok, why = caps.next_ok()
        if not ok: left[why] += 1; rec["action"] = "NOT ASKED - " + why; out.append(rec); continue
        for attempt in (1, 2):                                       # the second attempt is the ONE check with the exact date (spec 9.8)
            res, raw = ask(d, r, payer_id, exact)
            if res is None:
                if attempt == 1: no_member.append((r, raw)); rec["action"] = "NOT ASKED - %s" % raw; out.append(rec)
                break
            caps.count(); led.add_check(month); tally[res["label"]] += 1
            L = cs_rules.record(led.row(k), res, r, today, exact); led.put(k, L); answers.append((k, payer_id, res["label"]))
            if exact and attempt == 2: exact_made += 1
            if res["final"]: finals += 1
            for w in res["unknown"]: unknown[w] += 1
            if res["label"] == cs_rules.UNUSABLE:
                rec["raw"] = cs_rules.keep_raw(raw, res["http"], r.get("visitid"), payer_id, stamp) and "kept under patient_db/claimstatus_raw"
                bad[payer_id] += 1
                if bad[payer_id] >= cs_rules.PAYER_RUN_STOP: stopped_payers[payer_id] = True
            else: bad[payer_id] = 0
            if keep_every_raw and raw is not None and res["label"] != cs_rules.UNUSABLE: cs_rules.keep_raw(raw, res["http"], r.get("visitid"), payer_id, stamp + "_exact")
            rec.update({"label": res["label"], "final": res["final"], "named": res["named"], "exact": exact, "http": res["http"], "status": res["lines"], "errors": res["errors"],
                        "payments": res["payments"], "action": action(res, L), "answer_why": res["why"]})
            if attempt == 1 and L.get("exact_next") and not L.get("stopped") and payer_id not in stopped_payers and caps.next_ok()[0]:
                rec["first_answer"] = rec["action"]; exact = True; continue
            break
        if "label" in rec: out.append(rec)
        try: led.save()
        except cs_rules.LedgerWriteError as e: p("STOPPED: %s - no further check is made tonight" % e); code = 3; break
    handed = cs_rules.finish_run(led.changed, answers, today)
    for rec in out:
        L = led.changed.get("%s|%s" % (rec["visitid"], rec["carrier"]))
        if L and L.get("stopped") == today.isoformat() and rec.get("label") and not str(rec.get("action", "")).startswith(("PAID", "FINALIZED", "DENIED")):
            rec["action"] = "HAND OFF - %s: ask the payer by portal or phone" % L.get("stop_why")
    try: led.save()
    except cs_rules.LedgerWriteError as e: p("STOPPED: %s" % e); code = 3
    p("  asked: %d check(s), $%.2f at list price tonight; this month now %d checks, $%.2f" % (caps.run, caps.run_dollars(), caps.before + caps.run, caps.month_dollars()))
    p("  answers: %s; final answers recorded: %d; checks with the exact date of service: %d" % (", ".join("%s %d" % kv for kv in tally.most_common()) or "none", finals, exact_made))
    for why, n in left.most_common(): p("  NOT ASKED: %d due claim(s) - %s" % (n, why))
    if no_member: p("  NOT ASKED: %d due claim(s) - %s" % (len(no_member), "; ".join(sorted({w for _, w in no_member}))))
    hand = [rec for rec in out if str(rec.get("action", "")).startswith("HAND OFF")]
    if hand:
        p("  HAND OFF TONIGHT - ask the payer by portal or phone (%d):" % len(hand))
        rows_by = {cs_rules.key(r): r for r in rows}
        for rec in hand: p("    " + _who_line(rows_by.get("%s|%s" % (rec["visitid"], rec["carrier"]), {"pid": rec["patientid"], "visitid": rec["visitid"], "payer": rec["carrier"], "dos": rec["dos"], "bal": rec["balance"]}), today) + " - " + rec["action"][len("HAND OFF - "):])
    ins = [rec for rec in out if rec.get("label") == cs_rules.NOT_ELIGIBLE]
    if ins:
        p("  INSURANCE CHECK - not eligible on the date of service (a coverage problem, never a resend) (%d):" % len(ins))
        for rec in ins: p("    pat%s v%s %s DOS %s $%.2f" % (rec["patientid"], rec["visitid"], rec["carrier"], rec["dos"], rec["balance"]))
    if stopped_payers: p("  payers stopped for the rest of tonight (%d unusable answers in a row): %s" % (cs_rules.PAYER_RUN_STOP, ", ".join(sorted(stopped_payers))))
    if unknown:
        p("  WORDINGS THE RULES DO NOT KNOW (read as 'no usable answer' - add them to cs_rules.py when they are understood):")
        for w, n in unknown.most_common(20): p("    %3d  %s" % (n, w[:120]))
    return code, out, say

def write_rows(out, name):
    """claimstatus_<date>.json: one row per claim asked tonight; a second run the same day replaces its claims' rows and keeps the others."""
    old = []
    if os.path.exists(name):
        try:
            with open(name) as fh: old = [r for r in json.load(fh) if isinstance(r, dict)]
        except Exception: old = []
    mine = {(r["visitid"], r["carrier"]) for r in out}
    rows = [r for r in old if (str(r.get("visitid")), str(r.get("carrier"))) not in mine] + out
    with open(name, "w") as fh: json.dump(rows, fh, indent=1)
    return len(rows)

def main(argv=None, prog="claim_status_sweep.py", out_name="claimstatus_%s.json", doc=None):
    o = parse(sys.argv[1:] if argv is None else argv, prog, doc or __doc__)   # --help prints and exits; an unknown word is an error - before any call
    code, out, say = run(o, prog)
    if o.go and code != 2:
        name = out_name % datetime.date.today().strftime("%Y%m%d"); n = write_rows(out, name)
        print("  wrote %s (%d rows: chart and visit ids, no names)" % (name, n))
    return code
if __name__ == "__main__": sys.exit(main())
