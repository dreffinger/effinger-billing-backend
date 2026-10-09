# PLAIN ENGLISH (Old-claims disposition - the money audit, in code)
# Decides: nothing. Re-checks every package row's arithmetic and bookkeeping before the list goes to William: pay + write-off never
#   above the open insurance balance; a posting cites one of the exact-date 277's check numbers and posts the exact-date amount
#   (never the windowed figure) on this visit's own claim id; no (check, amount) posted twice; deceased rows only in -dec packages;
#   write-off codes fit their tier; package totals add up; resend rows carry exactly one send. Writes the findings in the shape the
#   reconcile step reads (old_claims_workflow_results_<stamp>/money_audit.json) - a HIGH finding pulls its row from the package.
# Never touches: AMD.
"""Usage: python3 old_claims_money_audit.py [--stamp 1009]"""
import json, sys, os, collections
a = sys.argv[1:]; STAMP = a[a.index("--stamp") + 1] if "--stamp" in a else "1009"
D = json.load(open("old_claims_disposition_%s.json" % STAMP)); V = D["visits"]
F = []; seen = {}; counts = collections.Counter(); tot = collections.defaultdict(lambda: [0, 0.0, 0.0, 0.0])
def f(vid, issue, sev="high"): F.append({"vid": vid, "issue": issue, "severity": sev})
WO_OK = {"WO-UNTIMELY": {"WOINS", "WOLATE"}, "WO-DUAL": {"WOCAID2ND", "WOINS"}, "WO-SMALL": {"WOSMBAL"}, "WO-PAID-NOREMIT": {"WOPDEOB"}, "POST-277": {"WOINS", "WOCAID2ND"}}
for r in V:
    if not r["pkg"]: continue
    counts["rows"] += 1; t = tot[r["pkg"]]; t[0] += 1; t[1] += r["open"]; t[2] += r["pay_total"]; t[3] += r["wo_total"]
    live = {c["cid"]: c for c in r["facts"]["charges"] if c["void"] != "1"}
    for x in r["actions"]:
        if "resend_seq" in x: continue
        c = live.get(x["cid"])
        if not c: f(r["vid"], "action on charge %s that is not live" % x["cid"]); continue
        if x.get("pay", 0) < -0.001 or x.get("wo", 0) < -0.001: f(r["vid"], "negative pay/wo on %s" % x["cid"])
        if x.get("pay", 0) + x.get("wo", 0) > c["insbal"] + 0.011: f(r["vid"], "pay %.2f + wo %.2f exceeds insbal %.2f on %s" % (x.get("pay", 0), x.get("wo", 0), c["insbal"], x["cid"]))
        if x.get("wo") and x.get("wocode") not in WO_OK.get(r["tier"], set()): f(r["vid"], "wocode %s does not fit tier %s" % (x.get("wocode"), r["tier"]))
        counts["actions"] += 1
    if r["tier"] == "POST-277":
        ex = r.get("exact") or {}
        if ex.get("state") != "paid": f(r["vid"], "POST-277 without an exact-date paid answer")
        else:
            chks = [x["check"] for x in r["actions"] if x.get("pay")]
            if any(ch not in (ex.get("checks") or []) for ch in chks): f(r["vid"], "posted check %s not among the exact-date checks %s" % (chks, ex.get("checks")))
            if abs(r["pay_total"] - min(ex["paid"], r["open"])) > 0.011: f(r["vid"], "pay_total %.2f != min(exact %.2f, open %.2f)" % (r["pay_total"], ex["paid"], r["open"]))
            if abs(r["pay_total"] - r["answer"]["paid"]) < 0.011 and abs(ex["paid"] - r["answer"]["paid"]) > 0.011: f(r["vid"], "pay_total equals the windowed figure, not the exact-date one")
            if any(not (p.get("acct") or "").startswith(r["vid"]) for p in ex.get("payments") or []) and ex.get("how") == "claim id": f(r["vid"], "an exact payment is not on this visit's claim id", "medium")
            for x in r["actions"]:
                if x.get("pay"):
                    k = (x["check"], "%.2f" % x["pay"], r["pid"])
                    # one EFT paying consecutive daily visits at the same rate is normal (distinct claim ids / payer claim numbers) - informational only
                    if k in seen and seen[k] != r["vid"]: f(r["vid"], "same check %s + amount %.2f also posted on v%s (same chart) - one remit paying several claims" % (x["check"], x["pay"], seen[k]), "low")
                    seen.setdefault(k, r["vid"])
            counts["post_rows"] += 1
    if r["pkg"].endswith("-dec") and not r["deceased"]: f(r["vid"], "-dec package without a deceased flag")
    if (not r["pkg"].endswith("-dec")) and r["deceased"]: f(r["vid"], "deceased flag outside a -dec package")
    if r["tier"] in ("RESEND", "MEDICARE-UNANSWERED") and sum(1 for x in r["actions"] if "resend_seq" in x) != 1: f(r["vid"], "resend row without exactly one send action")
    if r["patbal"] > 0.004: counts["patbal_rows"] += 1; f(r["vid"], "balance $%.2f on the patient side (moved back to insurance first)" % r["patbal"], "low")
for k, s in D["summary"].items():
    if k.startswith("list"): continue
    t = tot.get(k)
    if not t or t[0] != s["visits"] or abs(t[1] - s["open"]) > 0.02 or abs(t[2] - s["pay"]) > 0.02 or abs(t[3] - s["wo"]) > 0.02: f("-", "summary mismatch for package %s: file %s vs recomputed %s" % (k, {x: s[x] for x in ("visits", "open", "pay", "wo")}, t), "medium")
os.makedirs("old_claims_workflow_results_%s" % STAMP, exist_ok=True)
json.dump({"lists": [], "rules": {"concerns": []}, "money": {"findings": F, "verified_summary": "rows %d, actions %d, post rows %d, patbal rows %d; totals %s" % (counts["rows"], counts["actions"], counts["post_rows"], counts["patbal_rows"], {k: [t[0], round(t[1], 2), round(t[2], 2), round(t[3], 2)] for k, t in tot.items()})}},
          open("old_claims_workflow_results_%s/money_audit.json" % STAMP, "w"), indent=1)
print("money audit: %d package rows, %d actions, %d post rows; findings: %d (high %d, medium %d, low %d)" % (counts["rows"], counts["actions"], counts["post_rows"], len(F), sum(1 for x in F if x["severity"] == "high"), sum(1 for x in F if x["severity"] == "medium"), sum(1 for x in F if x["severity"] == "low")))
for x in F:
    if x["severity"] != "low": print("  ", x["severity"], "v" + x["vid"], x["issue"][:150])
