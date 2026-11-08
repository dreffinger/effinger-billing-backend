"""Sunday sweep 2026-11-08: all open-looking charges (no payment filter) + visit insorder/insbalance for the action charts."""
import amd, txh, resave, re, json
amd.login_cached()
PIDS = {"46678": "gillespie", "17477572": "stafford", "17475407": "moore-marisa", "17477267": "waldron", "21021": "moore-bettina",
        "17475362": "brozyna", "17476438": "burwell", "17476544": "conn", "17476503": "salamy", "23083": "lisle", "17476912": "camacho", "17474798": "annika"}
TARGET_VISITS = {"19442338", "19455611", "19452574", "19448386", "19453098", "19453097", "19453099", "19431787", "19431884",
                 "19372463", "19372311", "19442543", "19441388", "19452451", "19452690", "19453362", "19452691", "19453821", "19444049", "19452589", "19443011", "19445941", "19459520"}
for pid, who in PIDS.items():
    r = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "pat%s" % pid, "nocookie": "1"}))
    p = re.search(r'<patient [^>]*>', r); a = dict(re.findall(r'(\w+)="([^"]*)"', p.group(0))) if p else {}
    plans = [dict(re.findall(r'(\w+)="([^"]*)"', m)) for m in re.findall(r'<insplan ([^>]*)>', r)]
    print("\n== %s pid %s %s dob %s insorder=%s plans %s" % (who, pid, a.get("name"), a.get("dob"), a.get("insorder"), [(d.get("sequence"), d.get("carrier"), d.get("enddate")) for d in plans]))
    root = txh.fetch(pid); n = 0
    for ch in root.iter("charge"):
        c = ch.attrib
        if c.get("void") == "1": continue
        vid = (c.get("visitid") or c.get("visit") or "").replace("vst", "")
        d = c.get("date") or c.get("dos") or ""
        if d[-4:] < "2026" and vid not in TARGET_VISITS: continue
        pays = [(pm.attrib.get("date"), pm.attrib.get("amount"), pm.attrib.get("carrier")) for pm in ch.iter("payment") if pm.attrib.get("void") != "1" and pm.attrib.get("amount") not in ("0.00", "0")]
        extra = ""
        if vid in TARGET_VISITS:
            try:
                x = resave.detail(c.get("id").replace("charge", ""))
                v = re.search(r'<visit ([^>]*)>', x); va = dict(re.findall(r'(\w+)="([^"]*)"', v.group(1))) if v else {}
                cm = re.search(r'<charge id="%s"[^>]*>' % c.get("id"), x) or re.search(r'<charge ([^>]*)>', x)
                ca = dict(re.findall(r'(\w+)="([^"]*)"', cm.group(0))) if cm else {}
                extra = " | visit insorder=%s insbal=%s patbal=%s insbilled=%s dx=%s" % (va.get("insorder"), ca.get("insbalance"), ca.get("patbalance"), ca.get("insbilled"), (ca.get("diagcodes") or "")[:60])
            except Exception as e:
                extra = " | detail ERR %s" % e
        print("   CHG %s %s %s %s bill %s amt %s v%s pays %s%s" % (c.get("id"), d, c.get("proccode") or c.get("cpt"), c.get("carrier"), c.get("billdate"), c.get("amount") or c.get("fee"), vid, pays[:2], extra))
        n += 1
        if n > 40: print("   ..."); break
