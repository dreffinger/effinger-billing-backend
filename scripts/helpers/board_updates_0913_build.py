# PLAIN ENGLISH (Insurance Refresh Board answers for the 5am ET 9/15 run - inbox file builder)
# Decides: Nothing. Writes board_updates_2026-09-15T0913Z.json with this run's results (AET12 still held on run
#   1700193, the 11 unbalanced-posting Unbilled rows still held, ERA step numbers, Availity status) as update ops
#   (never set on status/need) with appends keyed by src+when so a re-applied file cannot duplicate them.
# Never touches: the board database directly (the page ingests this file from the Drive board inbox).
import json, os, datetime, collections, sys
S = "2026-09-15T0913Z"; NOW = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
SRC = "5am ET 9/15 columns run (ehpa cloud)"; W = "9/15"
AVAIL = sys.argv[1] if len(sys.argv) > 1 else "No Availity PDF or Check/EFT export newer than the 0310Z pass in 'bht Optum era downloads' / 'treasury payments' (newest PDF 03:30Z) - nothing new to parse or reconcile."
def chk(ok, result, src=SRC): return {"ok": ok, "result": result, "src": src, "when": W}
def note(text): return {"at": NOW, "text": text, "who": "Claude"}
ops = []
def row(id, notes=None, checks=None, api=None, status=None, need=None, extra=None):
    op = {"op": "update", "collection": "items", "id": id, "append": {}}
    if notes: op["append"]["notes"] = notes
    if checks: op["append"]["checks"] = checks
    if api: op["append"]["api"] = api
    d = {}
    if status: d["status"] = status
    if need: d["need"] = need
    if extra: d.update(extra)
    if d: op["set"] = d
    ops.append(op)
def load(p):
    try: return json.load(open(p))
    except Exception: return None
def f(x):
    try: return float(x or 0)
    except Exception: return 0.0
eb = load("era_checks_before_%s.json" % S) or []; ea = load("era_checks_after_%s.json" % S) or []
nb, ab = len(eb), round(sum(f(c.get("unpostedamount")) for c in eb), 2)
na, aa = len(ea), round(sum(f(c.get("unpostedamount")) for c in ea), 2)
pay = round(sum(f(c.get("paymentamount")) for c in eb), 2)
fb = load("registers/era_fallback_%s_live.json" % S) or []
fo = collections.Counter(("residual (charge already $0 in AMD)" if str(r.get("outcome", "")).startswith("residual") else (r.get("outcome") or "?")) for r in fb) if isinstance(fb, list) else {}
fposted = round(sum(f(r.get("pay")) for r in fb if r.get("outcome") == "posted"), 2) if isinstance(fb, list) else 0
av = load("registers/aet12_verify_%s.json" % S) or []
aet_bal = round(sum(f(c.get("insbal")) for c in av), 2) if isinstance(av, list) else 0

row("aet12-carrier-cpid",
    checks=[chk("no", "Still the same 59 AET12 PREF0288/PREF0264 rows on run 1700193 (15 charts; 68 AET12 charges re-read via gettxhistory: billdate 09/14/2026, no AET12 payment, insurance balance $%.2f open, none at $0). No new claim run since 1700193. Held, not rebilled, not completed - waiting on the carrier-record change you named (suppress the provider loop / Box 33B REF*EI), then 'rebill'." % aet_bal, SRC + " - claim run 1700193")])
row("unbilled-unbalanced-postings-0915",
    checks=[chk("no", "Still 11 Unbilled rows 'Payment reason codes are missing or do not balance' ($2,422.58; Rylance, Kinross, Cogswell, Delmar, Simcoe x4, Rowantree N x2, Carrow) - held, not released; no captured call edits a posted payment's reason codes. Needs the remit CARCs re-posted in Payment Entry or your word to release.")])
era_line = ("ERA step 5 (%s, run %s): %d unposted checks / $%.2f before -> %d / $%.2f after (paymentamount $%.2f); no new 835s in the Optum folder; locks release-expired sent; era_details cache 38/38; era_post --all-unposted on 33 money-bearing checks posted 0 visits (reversal 'does not match any payments', 'procedure codes do not match'); manual fallback dry + live %s, fallback posted $%.2f (residual-zero lines disregarded per your 9/13 rule); 0 addpayments faults; era_clear looked at 38, 0 dismissed, 38 held (85 unvalidated money lines $7,793 / 169 money already on the visit $4,720 / 1245 denial-with-write-off lines / 4 unrecorded reversal $304); 0 new checks arrived."
            % (SRC, S, nb, ab, na, aa, pay, ", ".join("%s %d" % (k, v) for k, v in fo.most_common()), fposted))
row("era-manual-post-0912", checks=[chk("na", era_line, SRC + " - ERA step 5")])
row("availity-remits-backlog", checks=[chk("na", AVAIL, SRC + " - ERA step 5(g)")])
out = {"schema": "irb-board-updates/1", "source": "backend billing run %s" % S, "created": NOW, "ops": ops}
json.dump(out, open("board_updates_%s.json" % S, "w"), indent=1)
print("wrote board_updates_%s.json" % S, len(ops), "ops"); print(era_line)
