# PLAIN ENGLISH (read-only facts for the 11 PM ET 10/3 run, 2026-10-04T0310Z): William answered many Insurance Refresh Board rows
#   between 02:28Z and 03:19Z. Before any write this script reads the LIVE chart state those answers touch: plans (getdemographic),
#   charges/payments (gettxhistory), AMD eligibility (free 271) where a plan is in question, lookuppatient for charts not yet found,
#   lookupcarrier for payers not yet on file. Output: registers/reads_2026-10-04T0310Z.json + a printed summary.
# Never touches: AMD writes (no resave, no payments, no plans).
import amd, elig_amd, re, json, time, sys, datetime
import xml.etree.ElementTree as ET
amd.login_cached()
STAMP = "2026-10-04T0310Z"
out = {"stamp": STAMP, "charts": {}, "lookup": {}, "carriers": {}, "elig": {}}
def P(*a): print(*a, flush=True)
def demo(pid):
    d = amd.post(amd.msg("getdemographic", "demographics", {"patientid": str(pid), "nocookie": "1"}), timeout=120)
    pa = dict(re.findall(r'(\w+)="([^"]*)"', re.search(r'<patient [^>]*>', d).group(0))) if re.search(r'<patient [^>]*>', d) else {}
    plans = [dict(re.findall(r'(\w+)="([^"]*)"', x)) for x in re.findall(r'<insplan [^>]*/?>', d)]
    return {"name": pa.get("name"), "dob": pa.get("dob"), "insorder": pa.get("insorder"), "plans": [{k: p.get(k) for k in ("id", "sequence", "carrier", "subscribernum", "begindate", "enddate")} for p in plans]}
def hist(pid):
    t = amd.post(amd.msg("gettxhistory", "demographics", {"patientid": str(pid), "filterhistory": "0", "pagenumber": "1", "typefilter": "1", "sortbypayment": "false", "groupbyvisit": "0", "sortdescending": "1", "visitid": "0", "getmemo": "false", "nocookie": "1"}), timeout=120)
    rows = []
    for m in re.finditer(r'<charge [^>]*/?>', t):
        a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(0)))
        rows.append({k: a.get(k) for k in ("id", "visit", "dos", "proccode", "fee", "insbal", "patbal", "paid", "carrier", "billdate", "void", "insbilled", "modifiers", "facname")})
    return rows
CHARTS = {
 "17476868": "pat17476868 admission 9/30", "17477183": "pat17477183 bill patient + WOBAD", "23617": "awv WONCS", "21885": "awv WONCS + CO151",
 "17474613": "pat17474613 WOLATE v19422927", "23159": "pat23159 void v19456297", "17471977": "pat17471977 BCBS GA plan", "17473431": "pat17473431 MBI check",
 "17476603": "pat17476603 lantern", "17474611": "pat17474611 send to UHC", "24039": "pat24039 FCC WOCAID2ND", "17468923": "pat17468923 WONCS v19442292",
 "17477549": "pat17477549 new MBI", "17475632": "pat17475632 UHC student", "45668": "pat45668 void v19455691", "17477850": "pat17477850 CHP id",
 "17476036": "pat17476036 add 99487 v19456171", "46673": "CO151 ccm", "17473343": "CO151 ccm", "17472553": "CO151 ccm", "17472517": "CO151 ccm",
 "17474713": "pat17474713", "17476534": "pat17476534 auth NR",
}
for pid, why in CHARTS.items():
    try:
        dm = demo(pid); hs = hist(pid)
    except Exception as e:
        P("pat%s ERROR %s" % (pid, e)); out["charts"][pid] = {"error": str(e)}; continue
    openrows = [r for r in hs if r["void"] != "1" and (float(r["insbal"] or 0) > 0 or float(r["patbal"] or 0) > 0)]
    out["charts"][pid] = {"why": why, "demo": dm, "open": openrows, "all": hs}
    P("\npat%s %s | %s dob %s insorder %s" % (pid, why, dm["name"], dm["dob"], dm["insorder"]))
    for p in dm["plans"]: P("   plan %s seq %s %s %s %s-%s" % (p["id"], p["sequence"], p["carrier"], p["subscribernum"], p["begindate"], p["enddate"]))
    for r in openrows: P("   OPEN c%s v%s %s %s fee %s ins %s pat %s paid %s %s billed %s mods %s" % (r["id"], r["visit"], r["dos"], r["proccode"], r["fee"], r["insbal"], r["patbal"], r["paid"], r["carrier"], r["billdate"], r["modifiers"]))
    if pid in ("23159", "45668", "17476036", "46673", "17473343", "17472553", "21885", "17472517", "17474611", "17471977"):
        for r in hs:
            if r["void"] != "1" and (r["proccode"] in ("99487", "99489") or r["visit"] in ("19456297", "19456050", "19455691", "19456171") or (pid == "17474611" and (r["dos"] or "").endswith("2025")) or pid == "17471977"):
                P("   chg c%s v%s %s %s fee %s ins %s pat %s paid %s %s billed %s" % (r["id"], r["visit"], r["dos"], r["proccode"], r["fee"], r["insbal"], r["patbal"], r["paid"], r["carrier"], r["billdate"]))
    time.sleep(0.3)
# AMD 271 on the plans in question
for pid, label in [("17473431", "pat17473431"), ("17477549", "pat17477549"), ("17476868", "pat17476868")]:
    try:
        pa, pl = elig_amd.plans(pid)
        for p in pl:
            if p.get("enddate"): continue
            s = elig_amd.run_plan(pid, p["id"].replace("ins", ""), True)
            line = elig_amd.one_line(s); out["elig"]["%s %s" % (pid, p["id"])] = line
            P("271 pat%s %s seq %s %s -> %s" % (pid, p["id"], p.get("sequence"), p.get("carrier"), line[:220])); time.sleep(0.3)
    except Exception as e: P("271 pat%s ERROR %s" % (pid, e))
for nm in ("pat17475906 PAXTON,N%", "pat17475906,N%", "PAXTON,N%", "CHRISTENSEN,[first]%", "WILBOURNE,%", "THORNEY,[first]%", "TRENT,[first]%", "HARLOW,%"):
    try:
        r = amd.post(amd.msg("lookuppatient", "lookup", {"name": nm, "nocookie": "1"}))
        pats = [dict(re.findall(r'(\w+)="([^"]*)"', x)) for x in re.findall(r'<patient [^>]*/?>', r)]
        out["lookup"][nm] = [{k: p.get(k) for k in ("id", "name", "chart", "dob")} for p in pats]
        P("lookup %s -> %s" % (nm, [(p.get("id"), p.get("name"), p.get("dob")) for p in pats]))
    except Exception as e: P("lookup %s ERROR %s" % (nm, e))
    time.sleep(0.3)
for code in ("%STUDENT%", "%LANTERN%", "%SURGERY%", "%UHC%"):
    try:
        r = amd.post(amd.msg("lookupcarrier", "lookup", {"code": code, "nocookie": "1"}))
        cars = [dict(re.findall(r'(\w+)="([^"]*)"', x)) for x in re.findall(r'<carrier [^>]*/?>', r)]
        out["carriers"][code] = cars[:20]; P("carrier %s -> %s" % (code, [(c.get("id"), c.get("code"), c.get("name")) for c in cars][:12]))
    except Exception as e: P("carrier %s ERROR %s" % (code, e))
    time.sleep(0.3)
json.dump(out, open("registers/reads_%s.json" % STAMP, "w"), indent=1)
P("saved registers/reads_%s.json" % STAMP)
