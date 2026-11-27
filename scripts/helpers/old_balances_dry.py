#!/usr/bin/env python3
# PLAIN ENGLISH (old insurance balances nobody works - William 11/27/2026: "an open claim for chp from 3 years ago is way to long to be on
#   the ar list, it should have been rerouted and correected and rebilled or written off likely"; asked how the fix should go in, he chose
#   "Dry list first": the first run lists every line with the code his rules give it and totals by payer; the runs act after he has seen it)
# Decides: NOTHING in AdvancedMD. READ-ONLY. It lists every open insurance balance more than 12 months past its date of service that the
#   nightly work queue does not hold (registers/work_queue.json) - the leftovers after a partial payment never appear on AdvancedMD's
#   unpaid list (massrebillsearch), so aging_refresh.py and the work queue never saw them - and files each line under the rule that
#   decides it, the same rules the aging engine uses (practices/ehpa/rules.md 9/7, 9/11, 10/13-10/15, 11/2 and 11/25/2026):
#     * FCC (FLO99) balances and visits on the timely-filing watch: left alone (his rules)
#     * a home or assisted-living visit at Capital Health Plan: WONCS (11/25/2026)
#     * nothing ever paid, primary past 12 months: WOINS untimely, never adjudicated (the aging engine's rule; WOLATE when CO-29 answered)
#     * paid by another payer first, balance now at a secondary: timely from the PRIMARY'S payment - inside 12 months = bill the secondary
#       (no write-off), past 12 months = WOCAID2ND for a Medicaid-family secondary, else WOCLTREQ (cost-share, secondary window closed)
#     * paid in part by the payer that holds it (a settled primary): the patient's share past 12 months = WOCLTREQ, the rest = WOINS
#       (contractual never written off)
# Source: the practice database's copy of the AdvancedMD charges (Neon amd.charge_outcomes, refreshed by the billing runs) - the live pass
#   re-reads every visit in AdvancedMD before it writes anything. Output: one CSV row per line (chart, visit and charge ids, DOS, CPT,
#   payer, balance, code, rule - never a name) and totals by payer and code. Revenue totals stay out of this public repository.
# ---
"""Usage: python3 scripts/helpers/old_balances_dry.py --out <dir> [--repo <clone>] [--months 12]
Needs NEON_DATABASE_URL. Reads registers/work_queue.json and registers/tf_writeoff_watch.json from the clone (default: this checkout)."""
import collections, csv, datetime, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
A = sys.argv[1:]
def opt(n, d=None): return A[A.index(n) + 1] if n in A and A.index(n) + 1 < len(A) else d

HOME_CPT = {"99341", "99342", "99344", "99345", "99347", "99348", "99349", "99350"}
MEDICAID_WORDS = re.compile(r"MEDICAID|SIMPLY|SUNSHINE|STAYWELL|WELLCARE|COMMUNITY CARE|MOLINA|PRESTIGE|AMERIGROUP|LTC", re.I)


def db():
    sys.path.insert(0, os.path.join(REPO, "credentialing"))
    saved = sys.argv[:]; sys.argv = sys.argv[:1]
    try:
        import cred_vault
    finally:
        sys.argv = saved
    return cred_vault.DB()


def register(repo, name):
    p = os.path.join(repo, "practices", "ehpa", "registers", name)
    if os.path.exists(p): return open(p).read()
    r = subprocess.run(["git", "-C", repo, "show", "origin/main:practices/ehpa/registers/" + name], capture_output=True, text=True)
    return r.stdout


def visit_ids(text):
    return set(re.findall(r'"visit(?:id|_id)?"\s*:\s*"?(\d+)"?', text or ""))


def num(x):
    try: return float(x or 0)
    except (TypeError, ValueError): return 0.0


def classify(r, months, today, medicaid_codes):
    car, paid_by = r["carrier"], [c for c in (r["paying"] or "").replace(" ", "").split(",") if c]
    cpt1 = (r["cpt"] or "").split(" ")[0]
    old = r["dos"] < today - datetime.timedelta(days=round(30.44 * months))
    if car == "FLO99": return "LEAVE", "FCC balances are never worked by the runs (rules: FLO99)"
    if car == "CAP07" and cpt1 in HOME_CPT: return "WONCS", "home / assisted-living visit at Capital Health Plan (11/25/2026)"
    others = [c for c in paid_by if c != car]
    if not paid_by:
        if "29" in (r["denials"] or ""): return "WOLATE", "CO-29 timely filing, never paid"
        return "WOINS", "primary unpaid past 12 months from DOS, never adjudicated (untimely, dated note)"
    if others and car not in paid_by:
        first = r["first_paid"]
        if first and first >= today - datetime.timedelta(days=365):
            return "BILL-SECONDARY", "secondary timely from the primary's payment (%s) - bill it, no write-off" % first
        return ("WOCAID2ND" if car in medicaid_codes else "WOCLTREQ"), "secondary window closed (primary paid %s)" % (first or "?")
    # the payer holding the balance paid part of it: a settled primary
    pr = num(r["pr"]); bal = num(r["bal"])
    if pr > 0 and pr >= bal - 0.005: return "WOCLTREQ", "settled primary: the leftover is the patient's share, past 12 months"
    return "WOINS", "settled primary: contractual never written off"


def main():
    out = opt("--out") or sys.exit(__doc__)
    repo = opt("--repo", REPO); months = int(opt("--months", "12")); os.makedirs(out, exist_ok=True)
    today = datetime.date.today()
    d = db()
    medicaid_codes = {c for c, n in d.q("select carrier_code, carrier_name from ehpa.carriers") if MEDICAID_WORDS.search(n or "")}
    queued = visit_ids(register(repo, "work_queue.json")); watch = visit_ids(register(repo, "tf_writeoff_watch.json"))
    asof = d.q("select max(entered_at)::date from amd.v_charges")[0][0]
    rows = d.q("""select chart_id, visit_id, charge_id, dos, cpt, provider, setting, current_carrier, insurance_balance, coalesce(insurance_paid,0),
                         coalesce(paying_carriers,''), first_insurance_payment, coalesce(patient_responsibility,0), coalesce(denial_codes,''), bill_date
                  from amd.charge_outcomes where coalesce(insurance_balance,0) > 0 and dos < current_date - (%s * 30.44)::int
                  order by current_carrier, dos""", [months])
    lines, tot = [], collections.defaultdict(lambda: [0, 0.0])
    for chart, vid, chg, dos, cpt, prov, setting, car, bal, paid, paying, first, pr, den, billed in rows:
        vid = str(vid)
        if vid in queued: continue
        r = {"carrier": car or "?", "paying": paying, "cpt": cpt, "dos": datetime.date.fromisoformat(str(dos)[:10]),
             "first_paid": datetime.date.fromisoformat(str(first)[:10]) if first else None, "pr": pr, "bal": bal, "denials": den}
        code, why = ("LEAVE", "on the timely-filing watch") if vid in watch else classify(r, months, today, medicaid_codes)
        lines.append([chart, vid, chg, str(dos)[:10], cpt, prov, setting, car, "%.2f" % num(bal), paying, str(first or "")[:10], den, str(billed or "")[:10], code, why])
        tot[(car, code)][0] += 1; tot[(car, code)][1] += num(bal)
    stamp = today.isoformat()
    with open(os.path.join(out, "old_balances_dry_%s.csv" % stamp), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["chart", "visit", "charge", "dos", "cpt", "provider", "setting", "payer", "balance", "paid_by", "primary_paid", "denials", "last_billed", "code", "rule"])
        w.writerows(lines)
    by_code = collections.defaultdict(lambda: [0, 0.0]); by_payer = collections.defaultdict(lambda: [0, 0.0])
    for (car, code), (n, s) in tot.items():
        by_code[code][0] += n; by_code[code][1] += s; by_payer[car][0] += n; by_payer[car][1] += s
    summ = {"as_of_copy": str(asof), "today": stamp, "lines": len(lines), "dollars": round(sum(num(l[8]) for l in lines), 2),
            "by_code": {k: [v[0], round(v[1], 2)] for k, v in sorted(by_code.items(), key=lambda x: -x[1][1])},
            "by_payer": {k: [v[0], round(v[1], 2)] for k, v in sorted(by_payer.items(), key=lambda x: -x[1][1])},
            "by_payer_code": {"%s %s" % k: [v[0], round(v[1], 2)] for k, v in sorted(tot.items(), key=lambda x: -x[1][1])}}
    json.dump(summ, open(os.path.join(out, "old_balances_dry_%s_summary.json" % stamp), "w"), indent=1)
    print("copy of AdvancedMD data as of %s; %d lines, $%.2f not held by the work queue" % (asof, summ["lines"], summ["dollars"]))
    for k, v in summ["by_code"].items(): print("  %-15s %5d lines  $%10.2f" % (k, v[0], v[1]))


if __name__ == "__main__":
    main()
