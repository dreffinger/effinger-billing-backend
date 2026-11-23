# PLAIN ENGLISH (one-off, nightly cascade 2026-11-22T0535Z): READ-ONLY. Lists the recent charges of the charts given
# (visit, charge, DOS, CPT, fee, last-billed carrier, billdate, balances, payments, visit insorder, diagnosis codes).
# Never writes anything to AMD. Usage: python3 open_visits_1122.py <since mm/dd/yyyy> <patientid> [<patientid> ...]
import amd, txh, resave, re, sys, datetime
amd.login_cached()
since = datetime.datetime.strptime(sys.argv[1], "%m/%d/%Y").date()
for pid in sys.argv[2:]:
    root = txh.fetch(pid)
    print("== chart", pid)
    for c in root.iter("charge"):
        a = c.attrib
        if a.get("void") == "1" or (a.get("fee") or "").startswith("-") or not a.get("dos"): continue
        d = datetime.datetime.strptime(a["dos"], "%m/%d/%Y").date()
        if d < since: continue
        pays = [(p.get("amount"), p.get("checknumber") or p.get("checknum")) for p in c.iter("payment") if p.get("void") != "1"]
        x = resave.detail(a.get("id")); m = re.search(r'<charge [^>]*>', x) or re.search(r'<charge[^>]*>', x)
        ch = m.group(0) if m else ""
        g = lambda k, s=ch: (re.search(k + r'="([^"]*)"', s) or [None, ""])[1]
        vm = re.search(r'<visit [^>]*>', x); vs = vm.group(0) if vm else ""
        print("  v%s c%s %s %s fee %s car %s billdate %s insbal %s patbal %s insbilled %s | visit insorder %s | dx %s | pays %s" % (
            a.get("visit"), a.get("id"), a["dos"], a.get("proccode") or g("proccode"), a.get("fee"), a.get("carrier"), a.get("billdate"),
            g("insbalance"), g("patbalance"), g("insbilled"), g("insorder", vs), g("diagcodes") or a.get("diagcodes"), pays))
