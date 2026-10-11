# PLAIN ENGLISH (read-only insurance cascade for the Claimocity-feed charts with no plan - 1 AM ET 10/11 run 2026-10-11T0510Z)
# Decides: nothing in AMD. For each chart id given: reads the chart's name / DOB from AMD (kept in patient_db/<pid>/, never printed),
#   runs the Stedi Medicare MBI lookup (name + DOB + FL) and, when that finds nothing, Stedi insurance discovery; saves the raw
#   answers under patient_db/<pid>/ and prints one line per chart with the chart id and the plan summary only.
# Never touches: AMD writes, keys (the proxy adds the Stedi credential).
"""Usage: python3 nc_lookup_1011.py <pid> [<pid> ...] [--dos yyyymmdd]"""
import amd, stedi, json, sys, os, re, time
import xml.etree.ElementTree as ET
a = sys.argv[1:]; dos = a[a.index("--dos") + 1] if "--dos" in a else "20261006"
pids = [x for x in a if x.isdigit() and x != dos]
amd.login_cached()
for pid in pids:
    r = amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"}), timeout=120)
    rt = ET.fromstring(r.encode("latin-1", "ignore")) if isinstance(r, str) else ET.fromstring(r)
    pat = next(rt.iter("patient"), None)
    if pat is None: print("CHART", pid, "no patient element"); continue
    at = pat.attrib
    name = at.get("name") or ""
    last = at.get("lastname") or (name.split(",")[0].strip() if "," in name else "")
    first = at.get("firstname") or (name.split(",")[1].strip().split()[0] if "," in name and name.split(",")[1].strip() else "")
    dob = at.get("dob") or at.get("birthdate") or at.get("dateofbirth") or ""
    m = re.match(r"(\d\d)/(\d\d)/(\d{4})", dob); dob8 = "%s%s%s" % (m.group(3), m.group(1), m.group(2)) if m else dob
    plans = [p.get("carrier") for p in rt.iter("insplan")]
    os.makedirs("patient_db/%s" % pid, exist_ok=True)
    json.dump({"pid": pid, "last": last, "first": first, "dob": dob, "sex": at.get("sex"), "zip": at.get("zip"), "plans": plans, "attrs": sorted(at.keys())}, open("patient_db/%s/demographics_%s.json" % (pid, dos), "w"), indent=1)
    print("CHART", pid, "plans", plans, "name/dob present:", bool(last and first and len(dob8) == 8))
    if not (last and first and len(dob8) == 8): continue
    found = False
    try:
        j = stedi.mbi(first, last, dob8, "FL", dos)
        json.dump(j, open("patient_db/%s/stedi_mbi_%s.json" % (pid, dos), "w"), indent=1)
        print("MBI ", pid, str(stedi.med_summ(j))[:400])
        found = bool(j.get("subscriber", {}).get("memberId")) and not j.get("errors")
    except Exception as e:
        print("MBI ", pid, "ERR", str(e)[:200])
    if not found:
        try:
            d = stedi.disc(first, last, dob8, "FL", dos)
            json.dump(d, open("patient_db/%s/stedi_disc_%s.json" % (pid, dos), "w"), indent=1)
            print("DISC", pid, str(stedi.disc_summ(d))[:500])
        except Exception as e:
            print("DISC", pid, "ERR", str(e)[:200])
    time.sleep(0.5)
