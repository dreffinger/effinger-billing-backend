#!/usr/bin/env python3
# PLAIN ENGLISH (release Unbilled rows whose cause was repaired first - generic form of the dated unbilled_release_<mmdd>_<hhmm>.py
#   helpers; written by the ehpa Billing Button run 2026-10-29T0501Z)
# Decides: nothing. Releases (hideunbillablevisits hide=-1, NUMERIC visit id) the Unbilled rows named on the command line - used
#   only for visits whose cause was repaired earlier in the same run (a write-off that took the balance to $0, an insurance order
#   written by another named helper, a payment-reason repair). Before releasing, the visit's live charges are read (payreasons.visit_state)
#   and the insurance + patient balance is printed so the register shows what was released and at what balance.
# Rules it uses: a release only hides the row - never run it on a visit whose data is still broken. Run --dry first, then --live.
# Never touches: charges, payments, write-offs, plans, claims. Register registers/unbilled_release_<run stamp>.json (one JSON file per run, appended).
# Usage: python3 unbilled_release.py <patientid>:<visitid> [<patientid>:<visitid> ...] [--stamp <run stamp>] [--live]
import amd, payreasons, json, re, sys, os, datetime
a = sys.argv[1:]
LIVE = "--live" in a
stamp = a[a.index("--stamp") + 1] if "--stamp" in a else datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H%MZ")
pairs = [x for x in a if ":" in x and not x.startswith("--")]
os.makedirs("registers", exist_ok=True)
path = "registers/unbilled_release_%s%s.json" % (stamp, "" if LIVE else "_dry")
reg = json.load(open(path)) if os.path.exists(path) else {"stamp": stamp, "live": LIVE, "rows": []}
amd.login_cached()
for p in pairs:
    pid, vid = [re.sub(r"\D", "", x) for x in p.split(":", 1)]
    st = payreasons.visit_state(pid, vid)
    bal = [(c["cid"], c["cpt"], c["insbalance"], c["patbalance"]) for c in st]
    row = {"pid": pid, "vid": vid, "balances": bal, "at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    child = '<visitlist><visit id="%s"/></visitlist>' % vid
    if not LIVE:
        row["resp"] = "dry: would hideunbillablevisits hide=-1"; print(json.dumps(row)); reg["rows"].append(row); continue
    r = amd.post(amd.msg("hideunbillablevisits", "claimsreports", {"hide": "-1", "nocookie": "1"}, child))
    row["ok"] = ('success="1"' in r and "<Fault" not in r); row["resp"] = re.sub(r"\s+", " ", r)[:160]
    print(json.dumps(row)); reg["rows"].append(row)
json.dump(reg, open(path, "w"), indent=1)
