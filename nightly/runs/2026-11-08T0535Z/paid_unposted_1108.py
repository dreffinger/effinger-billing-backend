"""Nightly cascade 2026-11-08T0535Z (Sunday sweep): PAID-but-unposted rows -> Paid_but_unposted_2026-11-08.csv for William (no rebill)."""
import json, csv, re
rows = json.load(open("claimstatus_20261108.json"))
paid = [r for r in rows if r["action"].startswith("PAID")]
with open("Paid_but_unposted_2026-11-08.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["patientid", "patient", "carrier", "dos", "visitid", "balance", "paid_per_277", "check_numbers", "icn", "status_note"])
    tot = 0.0
    for r in sorted(paid, key=lambda r: (r["carrier"], r["patient"], r["dos"])):
        m = re.search(r"PAID \$([\d.]+).*?check ([^)]+)\)", r["action"]); paidamt = m.group(1) if m else ""; chk = m.group(2) if m else ""
        st = (r.get("status") or [{}])[0]; note = st.get("codev") or st.get("statusCodeValue") or ""
        w.writerow([r["patientid"], r["patient"], r["carrier"], r["dos"], r.get("visitid"), "%.2f" % r["balance"], paidamt, chk, r.get("icn") or st.get("payerClaimNumber") or "", note[:80]]); tot += r["balance"]
print("paid-but-unposted rows", len(paid), "open balance $%.2f" % tot)
print(open("Paid_but_unposted_2026-11-08.csv").read()[:1500])
