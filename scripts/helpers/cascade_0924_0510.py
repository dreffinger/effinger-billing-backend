# PLAIN ENGLISH (insurance cascade - LOOKUPS ONLY, 1am ET 9/24/2026 run 2026-09-24T0510Z): the 11 charts the Claimocity feed created
#   with no insurance plan (7 HCA admissions 9/21-9/22, 3 nursing-home/ALF CCM charts, 1 SNF admit), plus pat45049 (Medicare 271 AAA 72)
#   and pat17472874 (UNI20 now INACTIVE). Per chart: no facesheet in the Drive folders / Pam Gmail / board drops (checked this run) ->
#   Stedi MBI lookup by name+DOB+FL at the DOS (Part A/B, MA entity, Part D, death) -> insurance discovery when Medicare knows nothing.
#   Also reads the chart address (REST GET) so the apply step can fill a blank line 1, and lookuppatient for the placeholder-DOB chart.
# Decides: nothing (writes cascade_0510.json). Never touches: AMD writes, the board.
import amd, stedi, patient_patch, json, re, sys, time, datetime
import xml.etree.ElementTree as ET
amd.login_cached()
inv = json.load(open("inv_0510.json"))
NEW = ["17477639", "17477842", "17477843", "17477844", "17477845", "17477846", "17477847", "17477848", "17477849", "17477850", "17477851", "45049", "17472874"]
DOS = {"17477845": "20260921", "17477846": "20260921", "17477847": "20260921", "17477848": "20260921", "17477849": "20260921", "17477850": "20260921", "17477851": "20260917", "45049": "20260105", "17472874": "20260920"}
out = {}
def L(m): print(m, flush=True)
for pid in NEW:
    rec = inv.get(pid, {}); name = rec.get("name", ""); dob = rec.get("dob", "")
    last, first = (name.split(",") + [""])[:2]; first = first.strip().split(" ")[0]; last = last.strip()
    m = re.match(r"(\d\d)/(\d\d)/(\d{4})", dob or ""); dob8 = "%s%s%s" % (m.group(3), m.group(1), m.group(2)) if m else None
    r = {"name": name, "dob": dob, "dos": DOS.get(pid, "20260920"), "plans": rec.get("plans"), "visits": [(v["vid"], v["chgs"], v.get("facility")) for v in rec.get("visits", [])]}
    L("== pat%s %s dob %s" % (pid, name, dob))
    try:
        p = patient_patch.get(pid); fl = patient_patch.flatten(p)
        r["address"] = {k: fl.get(k) for k in ("address1", "address2", "city", "state", "zipcode", "email", "homephone")}
        L("   address %s" % r["address"])
    except Exception as e:
        r["address"] = "ERR %s" % str(e)[:100]
    if pid == "17477842":
        try:
            lp = amd.post(amd.msg("lookuppatient", "lookup", {"name": "JARVIS,[first]%", "nocookie": "1"}))
            root = ET.fromstring(lp.encode("latin-1", "ignore"))
            r["lookup"] = [{"id": x.get("id"), "name": x.get("name"), "chart": x.get("chart"), "dob": x.get("dob")} for x in root.iter("patient")]
            L("   lookuppatient JARVIS,[first]%%: %s" % r["lookup"])
        except Exception as e:
            r["lookup"] = "ERR %s" % str(e)[:100]
    if not dob8: r["mbi"] = "no dob"; out[pid] = r; continue
    try:
        j = stedi.mbi(first, last, dob8, "FL", r["dos"], pid=pid); s = stedi.med_summ(j); r["mbi"] = s
        L("   MBI lookup: mbi=%s A=%s B=%s death=%s errors=%s other=%s" % (s.get("mbi"), s.get("partA"), s.get("partB"), s.get("death"), s.get("errors"), [(o.get("type"), o.get("typeName"), o.get("plan"), o.get("entity"), o.get("dates")) for o in s.get("other")][:4]))
    except Exception as e:
        r["mbi"] = {"errors": ["EXC %s" % str(e)[:160]]}; L("   MBI EXC %s" % str(e)[:160])
    time.sleep(1.0)
    mbi_ok = isinstance(r["mbi"], dict) and r["mbi"].get("mbi") and not r["mbi"].get("errors")
    if not mbi_ok:
        try:
            d = stedi.disc(first, last, dob8, "FL", r["dos"]); r["disc"] = stedi.disc_summ(d)
            L("   discovery: %s" % json.dumps(r["disc"])[:600])
        except Exception as e:
            r["disc"] = {"errors": ["EXC %s" % str(e)[:160]]}; L("   disc EXC %s" % str(e)[:160])
        time.sleep(1.0)
    out[pid] = r
json.dump(out, open("cascade_0510.json", "w"), indent=1, default=str)
L("DONE")
