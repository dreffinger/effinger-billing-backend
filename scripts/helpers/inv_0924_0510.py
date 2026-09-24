# PLAIN ENGLISH (read-only inventory, 1am ET 9/24/2026 run 2026-09-24T0510Z): for every Unbilled row and every exclusion row of
#   claim run 1700236, read the chart's plans (getdemographic), AMD's free 271 on each open plan (cached per day in patient_db/),
#   and the visit's current insorder/onhcfa/extins (getchargedetaildataicd10 by charge id). Writes inv_0510.json + a table.
# Decides: nothing. Never touches: AMD writes.
import amd, elig_amd, resave, re, json, time, sys, collections
import xml.etree.ElementTree as ET
amd.login_cached()
sb = json.load(open("scan_0912/summary_before.json"))
rows = sb["unbilled"]
ex = ET.fromstring(open("scan_0912/excl_1700236_before.xml").read())
exrows = []
for v in ex.iter("visit"):
    exrows.append({"id": v.get("id"), "claimid": v.get("claimid"), "patientid": v.get("patientid"), "patientname": v.get("patientname"), "carriercode": v.get("carriercodeshort"),
                   "_errs": [e.get("name") for e in v.iter("error")], "_chgs": [dict(c.attrib) for c in v.iter("charge")], "_excl": True})
HOLD = {"17472874"}
pats = collections.OrderedDict()
for r in rows + exrows:
    pats.setdefault(r["patientid"], []).append(r)
inv = {}
def L(m): print(m, flush=True)
for pid, vs in pats.items():
    pa, pl = elig_amd.plans(pid)
    plans = []
    for p in pl:
        rec = {"id": p.get("id"), "carrier": p.get("carrier"), "seq": p.get("sequence"), "begin": p.get("begindate"), "end": p.get("enddate"), "num": (p.get("subscribernum") or "")[:4] + "..", "fin": p.get("finclasscode")}
        if not p.get("enddate") and pid not in HOLD:
            try:
                s = elig_amd.run_plan(pid, p["id"].replace("ins", ""))
                rec["elig"] = elig_amd.one_line(s)[:400]
            except Exception as e:
                rec["elig"] = "ERR %s" % str(e)[:100]
            time.sleep(0.4)
        plans.append(rec)
    time.sleep(0.3)
    inv[pid] = {"name": pa.get("name"), "dob": pa.get("dob"), "insorder": pa.get("insorder"), "plans": plans, "visits": []}
    L("== pat%s %s dob %s patient insorder=%s" % (pid, pa.get("name"), pa.get("dob"), pa.get("insorder")))
    for p in plans: L("   plan %s %s seq %s %s-%s %s | %s" % (p["id"], p["carrier"], p["seq"], p["begin"], p["end"], p["num"], p.get("elig", "(ended/hold)")))
    for r in vs:
        vrec = {"vid": r["id"], "errs": r["_errs"], "excl": r.get("_excl", False), "carrier": r.get("carriercode"), "chgs": [(c.get("chgcode"), c.get("dos", "").strip(), c.get("fee"), c.get("finclassdescrip")) for c in r["_chgs"]]}
        if pid in HOLD:
            vrec["note"] = "standing hold"; inv[pid]["visits"].append(vrec); continue
        cid = r["_chgs"][0].get("id") if r["_chgs"] else None
        if cid:
            try:
                x = resave.detail(cid); vm = re.search(r'<visit [^>]*>', x)
                va = dict(re.findall(r'(\w+)="([^"]*)"', vm.group(0))) if vm else {}
                ex_ = re.search(r'<extins [^>]*>', x); ea = dict(re.findall(r'(\w+)="([^"]*)"', ex_.group(0))) if ex_ else {}
                vrec.update({"v_insorder": va.get("insorder"), "onhcfa": va.get("onhcfa"), "facility": va.get("facility"), "refplan": va.get("refplan"), "preauth": va.get("preauth"), "hospfrom": ea.get("hospitalizationfrom"),
                             "insbilled": re.findall(r'insbilled="([^"]*)"', x)[:3], "insbal": re.findall(r'insbalance="([^"]*)"', x)[:3], "patbal": re.findall(r'patbalance="([^"]*)"', x)[:3], "lastbilled": re.findall(r'lastbilledcarrier="([^"]*)"', x)[:2]})
            except Exception as e:
                vrec["detail_err"] = str(e)[:100]
            time.sleep(0.3)
        inv[pid]["visits"].append(vrec)
        L("   v%s %s %s | %s | insorder=%s onhcfa=%s fac=%s hosp=%s insbilled=%s insbal=%s patbal=%s lastb=%s" % (r["id"], "EXCL" if vrec["excl"] else "UNB", vrec["chgs"], "; ".join(r["_errs"])[:90], vrec.get("v_insorder"), vrec.get("onhcfa"), vrec.get("facility"), vrec.get("hospfrom"), vrec.get("insbilled"), vrec.get("insbal"), vrec.get("patbal"), vrec.get("lastbilled")))
json.dump(inv, open("inv_0510.json", "w"), indent=1)
L("DONE %d patients" % len(inv))
