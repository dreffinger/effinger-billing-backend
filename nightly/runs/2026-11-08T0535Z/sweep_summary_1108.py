"""Nightly cascade 2026-11-08T0535Z (Sunday): summarise claimstatus_20261108.json by action, with the lists each STEP 2 rule needs."""
import json, collections
rows = json.load(open("claimstatus_20261108.json"))
print("rows", len(rows)); c = collections.Counter(r["action"] for r in rows)
for k, n in c.most_common(): print("  %3d  %s  $%.2f" % (n, k, sum(r["balance"] for r in rows if r["action"] == k)))
print("keys", sorted(rows[0].keys()))
def grp(act):
    g = collections.defaultdict(list)
    for r in rows:
        if r["action"].startswith(act): g[(r["patientid"], r["patient"], r["carrier"])].append(r)
    return g
print("\n== PAID - find/post the ERA ==")
for k, rs in sorted(grp("PAID").items()):
    for r in rs: print("  pid %s %-24s %s %s $%.2f vst %s -> %s" % (k[0], k[1][:24], k[2], r["dos"], r["balance"], r.get("visitid"), r["action"][:90]))
print("\n== NOT ON FILE / rejected - resend as original ==")
for k, rs in sorted(grp("NOT ON FILE").items()):
    print("  pid %s %-24s %s  %d visits $%.2f  %s" % (k[0], k[1][:24], k[2], len(rs), sum(r["balance"] for r in rs), "; ".join("%s v%s %s" % (r["dos"], r.get("visitid"), ((r.get("errors") or [""])[0] or (r.get("status") or [{}])[0].get("codev", ""))[:60]) for r in rs)[:400]))
print("\n== FINALIZED $0 / DENIED - cascade ==")
for k, rs in sorted(list(grp("FINALIZED").items()) + list(grp("DENIED").items())):
    print("  pid %s %-24s %s  %d visits $%.2f  %s" % (k[0], k[1][:24], k[2], len(rs), sum(r["balance"] for r in rs), "; ".join("%s v%s" % (r["dos"], r.get("visitid")) for r in rs)[:200]))
