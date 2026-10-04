# PLAIN ENGLISH (read-only facts for the 1 AM ET 10/4 run, 2026-10-04T0510Z): William answered more Insurance Refresh Board rows
#   03:20-03:47Z 10/4 and the Claims Center scan shows new HCA charts in the inspector/unbilled. Before any write this script reads
#   the LIVE chart state: plans (getdemographic), charges/payments (gettxhistory), AMD 271 where a plan is in question, Stedi MBI
#   lookup for the hospice chart (Scrivener) and the new no-insurance chart (Zane), lookupcarrier for Lantern.
#   Output: registers/reads_2026-10-04T0510Z.json + a printed summary. Never touches: AMD writes.
import amd, elig_amd, stedi, re, json, time, sys, datetime
amd.login_cached()
STAMP = "2026-10-04T0510Z"
out = {"stamp": STAMP, "charts": {}, "lookup": {}, "carriers": {}, "elig": {}, "stedi": {}}
def P(*a): print(*a, flush=True)
def demo(pid):
    d = amd.post(amd.msg("getdemographic", "demographics", {"patientid": str(pid), "nocookie": "1"}), timeout=120)
    pa = dict(re.findall(r'(\w+)="([^"]*)"', re.search(r'<patient [^>]*>', d).group(0))) if re.search(r'<patient [^>]*>', d) else {}
    plans = [dict(re.findall(r'(\w+)="([^"]*)"', x)) for x in re.findall(r'<insplan [^>]*/?>', d)]
    rp = [dict(re.findall(r'(\w+)="([^"]*)"', x)) for x in re.findall(r'<refplan [^>]*/?>', d)]
    return {"name": pa.get("name"), "dob": pa.get("dob"), "sex": pa.get("sex"), "insorder": pa.get("insorder"), "address1": pa.get("address1"), "zip": pa.get("zip"),
            "plans": [{k: p.get(k) for k in ("id", "sequence", "carrier", "subscribernum", "begindate", "enddate", "relationship")} for p in plans],
            "refplans": [{k: p.get(k) for k in ("id", "ismain", "preauth", "status", "refprov")} for p in rp]}
def hist(pid):
    t = amd.post(amd.msg("gettxhistory", "demographics", {"patientid": str(pid), "filterhistory": "0", "pagenumber": "1", "typefilter": "1", "sortbypayment": "false", "groupbyvisit": "0", "sortdescending": "1", "visitid": "0", "getmemo": "false", "nocookie": "1"}), timeout=120)
    rows = []
    for m in re.finditer(r'<charge [^>]*/?>', t):
        a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(0)))
        rows.append({k: a.get(k) for k in ("id", "visit", "dos", "proccode", "fee", "insbal", "patbal", "paid", "carrier", "billdate", "void", "insbilled", "modifiers", "facname", "profile")})
    pays = [dict(re.findall(r'(\w+)="([^"]*)"', x)) for x in re.findall(r'<payment [^>]*/?>', t)]
    return rows, [{k: p.get(k) for k in ("id", "charge", "amount", "void", "carrier", "checknumber", "date")} for p in pays]
CHARTS = {
 "17476534": "bellingham WONCS $731 (5/11-5/13/2026 HCA)", "17471681": "powell void v19455606", "17474541": "rodway restore 99487 c23336997 (v19430630)",
 "17477375": "screws Medicare+GV (8/11-8/13/2026)", "17477892": "pignone CAP07 CIO50078852 + admit 9/23", "17477640": "reeve admission 09/02/2026 v19456252/v19456267",
 "20729": "rossiter add SUN01 7415004647 seq2", "12180329": "scott Medicare [MBI] + FB spouse XJJH62710650", "17474290": "short FB VMYH57761517",
 "17477842": "jarvis placeholder chart", "17472416": "jarvis real chart", "17477972": "herring inspector admit", "17477975": "singer inspector admit",
 "17477974": "tisdale pending", "17477933": "smith myrtle F02.80", "17477973": "zane no insurance", "17477777": "lazenby refplan", "17469007": "jacobsen norcott 'mine' 6/23 CCM",
 "17476603": "king lantern",
}
for pid, why in CHARTS.items():
    try:
        dm = demo(pid); hs, pays = hist(pid)
    except Exception as e:
        P("pat%s ERROR %s" % (pid, e)); out["charts"][pid] = {"error": str(e)}; continue
    openrows = [r for r in hs if r["void"] != "1" and (float(r["insbal"] or 0) > 0 or float(r["patbal"] or 0) > 0)]
    out["charts"][pid] = {"why": why, "demo": dm, "open": openrows, "all": hs, "payments": pays}
    P("\npat%s %s | %s dob %s sex %s insorder %s addr1 %r" % (pid, why, dm["name"], dm["dob"], dm["sex"], dm["insorder"], dm["address1"]))
    for p in dm["plans"]: P("   plan %s seq %s %s %s %s-%s rel %s" % (p["id"], p["sequence"], p["carrier"], p["subscribernum"], p["begindate"], p["enddate"], p["relationship"]))
    for p in dm["refplans"]: P("   refplan %s main %s preauth %r status %s" % (p["id"], p["ismain"], p["preauth"], p["status"]))
    for r in hs:
        if r["void"] == "1": continue
        if r in openrows or pid in ("17474541", "17477972", "17477975", "17477974", "17477933", "17477973", "17477640", "17477892", "17477842", "17469007", "17471681"):
            P("   %s c%s v%s %s %s fee %s ins %s pat %s paid %s %s billed %s mods %s prof %s" % ("OPEN" if r in openrows else "chg", r["id"], r["visit"], r["dos"], r["proccode"], r["fee"], r["insbal"], r["patbal"], r["paid"], r["carrier"], r["billdate"], r["modifiers"], r["profile"]))
    if pid == "17474541":
        for r in hs:
            if r["visit"] == "19430630": P("   v19430630 c%s %s void=%s fee %s ins %s pat %s" % (r["id"], r["proccode"], r["void"], r["fee"], r["insbal"], r["patbal"]))
    time.sleep(0.3)
for pid in ("12180329", "17474290", "20729", "17477375", "17472416"):
    try:
        pa, pl = elig_amd.plans(pid)
        for p in pl:
            if p.get("enddate"): continue
            s = elig_amd.run_plan(pid, p["id"].replace("ins", ""), True)
            line = elig_amd.one_line(s); out["elig"]["%s %s" % (pid, p["id"])] = line
            P("271 pat%s %s seq %s %s -> %s" % (pid, p["id"], p.get("sequence"), p.get("carrier"), line[:220])); time.sleep(0.3)
    except Exception as e: P("271 pat%s ERROR %s" % (pid, e))
# Stedi MBI lookups: Scrivener (hospice, Medicare needed), Zane (new chart)
for pid in ("17477375", "17477973"):
    dm = out["charts"].get(pid, {}).get("demo") or {}
    try:
        last, first = (dm.get("name") or ",").split(",")[:2]; first = first.strip().split(" ")[0]
        dob = dm.get("dob") or ""; m = re.match(r"(\d\d)/(\d\d)/(\d{4})", dob); dob8 = m.group(3) + m.group(1) + m.group(2) if m else dob
        j = stedi.mbi(first, last.strip(), dob8, state="FL", pid=pid); s = stedi.med_summ(j); out["stedi"][pid] = s; P("stedi mbi pat%s -> %s" % (pid, str(s)[:400]))
        if pid == "17477973":
            j2 = stedi.disc(first, last.strip(), dob8, state="FL"); s2 = stedi.disc_summ(j2); out["stedi"][pid + "_disc"] = s2; P("stedi disc pat%s -> %s" % (pid, str(s2)[:500]))
    except Exception as e: P("stedi pat%s ERROR %s" % (pid, e))
for code in ("%LAN%",):
    try:
        r = amd.post(amd.msg("lookupcarrier", "lookup", {"code": code, "nocookie": "1"}))
        cars = [dict(re.findall(r'(\w+)="([^"]*)"', x)) for x in re.findall(r'<carrier [^>]*/?>', r)]
        out["carriers"][code] = cars[:20]; P("carrier %s -> %s" % (code, [(c.get("id"), c.get("code"), c.get("name")) for c in cars][:12]))
    except Exception as e: P("carrier %s ERROR %s" % (code, e))
json.dump(out, open("registers/reads_%s.json" % STAMP, "w"), indent=1)
P("saved registers/reads_%s.json" % STAMP)
