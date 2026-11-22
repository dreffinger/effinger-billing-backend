# PLAIN ENGLISH (one-off, nightly cascade 2026-11-22T0535Z): READ-ONLY. For each <patientid>:<visitid> pair, prints the visit's
# live charges (CPT, fee, last-billed carrier, billdate, balances, visit insorder) with every non-void payment / adjustment
# line (amount, carrier, check number, codes). Also lists the chart's insurance plans (carrier code, sequence, dates).
# Never writes anything to AMD. Usage: python3 visits_1122.py <pid>:<vid> [<pid>:<vid> ...]
import amd, txh, resave, re, sys
amd.login_cached()
seen = set()
for pair in sys.argv[1:]:
    pid, vid = pair.split(":")
    root = txh.fetch(pid)
    if pid not in seen:
        seen.add(pid)
        print("== chart", pid)
        for ip in root.iter("insplan"):
            a = ip.attrib
            print("   plan %s car %s seq %s begin %s end %s" % (a.get("id"), a.get("carriercode") or a.get("carrier"), a.get("sequence") or a.get("seq"), a.get("begindate"), a.get("enddate")))
    for c in root.iter("charge"):
        a = c.attrib
        if a.get("visit") != vid or a.get("void") == "1": continue
        x = resave.detail(a.get("id")); m = re.search(r'<charge [^>]*>', x)
        ch = m.group(0) if m else ""
        g = lambda k, s=ch: (re.search(k + r'="([^"]*)"', s) or [None, ""])[1]
        vm = re.search(r'<visit [^>]*>', x); vs = vm.group(0) if vm else ""
        print("  v%s c%s %s %s fee %s car %s billdate %s insbal %s patbal %s | insorder %s" % (vid, a.get("id"), a.get("dos"), a.get("proccode"),
              a.get("fee"), a.get("carrier"), a.get("billdate"), g("insbalance"), g("patbalance"), g("insorder", vs)))
        for p in c:
            if p.get("void") == "1": continue
            pa = p.attrib
            if p.tag in ("payment", "writeoff", "adjustment", "transaction", "tx"):
                print("      %s %s" % (p.tag, {k: v for k, v in pa.items() if k in ("amount", "carrier", "checknumber", "checknum", "code", "reason", "reasoncode", "date", "paymentdate", "type", "memo", "note")}))
