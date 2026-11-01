# PLAIN ENGLISH (Charges dated after a Medicare date of death, nightly cascade 2026-11-01)
# Decides: Nothing. Lists every live charge on a chart whose date of service is on/after the date of death the Medicare 271 /
# Stedi MBI lookup returned, with its open insurance and patient balance and any non-void payment, so the run can apply
# William's rule (e): write off post-death charges (WOINS, dated note) and put the chart on his turn to confirm/void.
# Never touches: AMD writes.
"""Usage: python3 post_death_1101.py <patientid> <death yyyymmdd>"""
import txh, sys, datetime
pid, death = sys.argv[1], sys.argv[2]
d0 = datetime.date(int(death[:4]), int(death[4:6]), int(death[6:]))
root = txh.fetch(pid); n = 0; tot = 0.0
for c in root.iter("charge"):
    if c.get("void") == "1": continue
    a = c.attrib; dos = a.get("dos") or ""
    try: d = datetime.datetime.strptime(dos[:10], "%m/%d/%Y").date()
    except Exception: continue
    ins = float(a.get("insbal") or 0); pat = float(a.get("patbal") or 0)
    if d < d0 and ins <= 0 and pat <= 0: continue
    pays = ["%s %s %.2f" % (p.get("carrier") or "PAT", p.get("date") or "", abs(float(p.get("amount") or 0))) for p in c.iter("payment") if p.get("void") != "1" and abs(float(p.get("amount") or 0)) > 0.004]
    flag = "POST-DEATH" if d >= d0 else "open"
    if flag == "POST-DEATH": n += 1; tot += ins + pat
    print(flag, "cid", a.get("id"), "visit", a.get("visitid") or a.get("visit"), dos, a.get("proccode"), "fee", a.get("fee"), "carrier", a.get("carrier"), "insbal %.2f patbal %.2f" % (ins, pat), "billed", a.get("billdate"), "| pays:", "; ".join(pays)[:120])
print("post-death charges: %d, open balance $%.2f (death %s)" % (n, tot, d0.isoformat()))
