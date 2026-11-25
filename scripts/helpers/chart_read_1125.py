# PLAIN ENGLISH (read-only chart state for the board cards answered 11/25/2026)
# Decides: nothing. Prints, per chart: dob, ssn-present, insorder, every insplan (id, carrier, subscriber number MASKED to its
#   last 4, begin/end, sequence), every referral plan (id, ismain, preauth) and every live charge of the visits named
#   (visit, charge, DOS, CPT, fee, carrier last billed, billdate, insbalance, patbalance, payments non-void).
# Never touches: AMD writes. Usage: python3 chart_read_1125.py <pid>[:vid,vid...] [...]
import amd, txh, re, sys, json
amd.login_cached()
def mask(s):
    s = s or ""; return ("*" * max(0, len(s) - 4)) + s[-4:] if s else ""
for arg in sys.argv[1:]:
    pid, _, vids = arg.partition(":"); vids = set(v for v in vids.split(",") if v)
    t = amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"}), timeout=120)
    pat = re.search(r'<patient [^>]*>', t); pa = dict(re.findall(r'(\w+)="([^"]*)"', pat.group(0))) if pat else {}
    print("=== pat%s dob=%s ssn=%s insorder=%s chart=%s name=%s" % (pid, pa.get("dob"), "yes" if pa.get("ssn") else "no", pa.get("insorder"), pa.get("chartnumber"), pa.get("name")))
    for x in re.findall(r'<insplan [^>]*/?>', t):
        a = dict(re.findall(r'(\w+)="([^"]*)"', x))
        print("  plan %s car=%s %s sub=%s begin=%s end=%s seq=%s elig=%s" % (a.get("id"), a.get("carrier"), a.get("carriercode") or a.get("carriername", ""), mask(a.get("subscribernum")), a.get("begindate"), a.get("enddate"), a.get("sequence"), a.get("eligibilitystatus", "")))
    for x in re.findall(r'<refplan [^>]*/?>', t):
        a = dict(re.findall(r'(\w+)="([^"]*)"', x))
        print("  refplan %s ismain=%s preauth=%s begin=%s" % (a.get("id"), a.get("ismain"), a.get("preauth"), a.get("begindate")))
    try:
        root = txh.fetch(pid)
    except Exception as e:
        print("  txh error", e); continue
    for c in root.iter("charge"):
        a = c.attrib
        if a.get("void") == "1": continue
        vid = str(a.get("visitid") or a.get("visit") or "").replace("visit", "")
        if vids and vid not in vids: continue
        pays = [(p.get("amount"), p.get("checknumber"), p.get("void")) for p in c.iter("payment") if p.get("void") != "1"]
        wos = [(w.get("amount"), w.get("code") or w.get("writeoffcode"), w.get("void")) for w in c.iter("writeoff") if w.get("void") != "1"]
        print("  v%s chg%s %s %s amt=%s car=%s bill=%s insbal=%s patbal=%s pays=%s wos=%s" % (vid, a.get("id"), a.get("dos") or a.get("dateofservice"), a.get("proccode"), a.get("amount"), a.get("carrier") or a.get("carriercode"), a.get("billdate"), a.get("insbalance"), a.get("patbalance"), pays, wos))
