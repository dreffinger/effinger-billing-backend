# PLAIN ENGLISH (Sunday sweep report, nightly cascade 10/11/2026): READ-ONLY on AMD/Stedi.
# Decides: nothing. Splits claimstatus_<today>.json into the PAID-unposted CSV for William and counts the other buckets.
import json, csv, glob, collections, datetime
f = sorted(glob.glob("claimstatus_2026*.json"))[-1]; d = json.load(open(f)); t = datetime.date.today().strftime("%Y%m%d")
paid = [r for r in d if r["action"].startswith("PAID")]
with open("Paid_but_unposted_%s.csv" % t, "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["patient", "carrier", "dos", "visitid", "balance", "action"])
    for r in paid: w.writerow([r["patient"], r["carrier"], r["dos"], r["visitid"], r["balance"], r["action"]])
c = collections.Counter(r["action"].split(" - ")[0].split(" $")[0] for r in d)
print(f, len(d), dict(c), "paid rows", len(paid), "paid $ on file", sum(float(r["action"].split("$")[1].split(" ")[0]) for r in paid))
bk = [r for r in d if r["carrier"] in ("UNI20", "BCBS") and r["dos"] < "2026-05-01"]
print("UNI20/BCBS pre-5/1 backlog rows (not touched):", len(bk))
for k in ("NOT ON FILE", "DENIED/REVISED", "FINALIZED"):
    rows = [r for r in d if r["action"].startswith(k) and r not in bk]
    print(k, "non-backlog:", len(rows), "$%.2f" % sum(r["balance"] for r in rows), collections.Counter(r["carrier"] for r in rows))
