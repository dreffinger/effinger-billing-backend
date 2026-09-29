# PLAIN ENGLISH (read-only inventory + lookups, 7pm ET 9/28/2026 run 2026-09-28T2310Z): for the ten charts the Claimocity HCA feed created
#   9/22-9/24 with no insurance plan (Unbilled 'Insurance order is missing'), pat17477850 (standing CHP hold, 2 new visits) and pat21489
#   (SUN01 'MBR NOT VALID AT DOS' exclusions x2 on run 1700243): chart plans (getdemographic), AMD's free 271 on each open plan, the visit's
#   live state (getchargedetaildataicd10), the chart address (REST GET), then the Stedi cascade (MBI lookup by name/DOB/FL at the DOS ->
#   insurance discovery when Medicare knows nothing). Also lookuppatient for the seven Pam admit facesheets received 9/28 (chart ids only).
# Decides: nothing (writes inv_2310.json). Never touches: AMD writes, the board.
import amd, elig_amd, resave, stedi, patient_patch, re, json, time, sys, collections
import xml.etree.ElementTree as ET
amd.login_cached()
sb = json.load(open("scan_0912/summary_before.json"))
NEW = ["17477892","17477893","17477894","17477895","17477896","17477897","17477898","17477899","17477900","17477901","17477850","21489"]
rows = [r for r in sb["unbilled"] if r["patientid"] in NEW]
for run, rs in sb["exclusions"].items():
    for r in rs:
        if r["patientid"] in NEW: r2 = dict(r); r2["_excl"] = run; r2["_errs"] = [(e.get("name") or e.get("text") or "") for e in r["_errs"]]; rows.append(r2)
pats = collections.OrderedDict()
for r in rows: pats.setdefault(r["patientid"], []).append(r)
inv = {}
def L(m): print(m, flush=True)
for pid, vs in pats.items():
    pa, pl = elig_amd.plans(pid); plans = []
    for p in pl:
        rec = {"id": p.get("id"), "carrier": p.get("carrier"), "seq": p.get("sequence"), "begin": p.get("begindate"), "end": p.get("enddate"), "num": (p.get("subscribernum") or "")[:4] + "..", "fin": p.get("finclasscode")}
        if not p.get("enddate"):
            try: rec["elig"] = elig_amd.one_line(elig_amd.run_plan(pid, p["id"].replace("ins", "")))[:400]
            except Exception as e: rec["elig"] = "ERR %s" % str(e)[:100]
            time.sleep(0.4)
        plans.append(rec)
    inv[pid] = {"name": pa.get("name"), "dob": pa.get("dob"), "insorder": pa.get("insorder"), "plans": plans, "visits": []}
    L("== pat%s %s dob %s patient insorder=%s" % (pid, pa.get("name"), pa.get("dob"), pa.get("insorder")))
    for p in plans: L("   plan %s %s seq %s %s-%s %s | %s" % (p["id"], p["carrier"], p["seq"], p["begin"], p["end"], p["num"], p.get("elig", "(ended)")))
    try:
        fl = patient_patch.flatten(patient_patch.get(pid)); inv[pid]["address"] = {k: fl.get(k) for k in ("address1", "address2", "city", "state", "zipcode", "email", "homephone")}
        L("   address %s" % inv[pid]["address"])
    except Exception as e: inv[pid]["address"] = "ERR %s" % str(e)[:100]
    for r in vs:
        vrec = {"vid": r["id"], "errs": r["_errs"], "excl": r.get("_excl"), "carrier": r.get("carriercode"), "chgs": [(c.get("chgcode") or c.get("proccode"), (c.get("dos") or "").strip(), c.get("fee")) for c in r["_chgs"]]}
        cid = r["_chgs"][0].get("id") if r["_chgs"] else None
        if cid:
            try:
                x = resave.detail(cid); vm = re.search(r'<visit [^>]*>', x); va = dict(re.findall(r'(\w+)="([^"]*)"', vm.group(0))) if vm else {}
                ex_ = re.search(r'<extins [^>]*>', x); ea = dict(re.findall(r'(\w+)="([^"]*)"', ex_.group(0))) if ex_ else {}
                pm = dict(re.findall(r'<proccode id="(pcode\d+)"[^>]*?\bcode="([^"]*)"', x)); dm = dict(re.findall(r'<diagcode id="(dcode\d+)"[^>]*?\bcode="([^"]*)"', x))
                cm = re.search(r'<charge [^>]*>', x); ca = dict(re.findall(r'(\w+)="([^"]*)"', cm.group(0))) if cm else {}
                vrec.update({"cid": cid, "v_insorder": va.get("insorder"), "onhcfa": va.get("onhcfa"), "facility": va.get("facility"), "pos": ca.get("pos"), "cpt": pm.get(ca.get("proccode"), ca.get("proccode")), "dx": [dm.get(d, d) for d in (ca.get("diagcodes") or "").split()], "hospfrom": ea.get("hospitalizationfrom"), "insbal": re.findall(r'insbalance="([^"]*)"', x)[:2], "patbal": re.findall(r'patbalance="([^"]*)"', x)[:2], "payments": re.findall(r'<payment [^>]*amount="([^"]*)"', x)[:4]})
            except Exception as e: vrec["detail_err"] = str(e)[:100]
            time.sleep(0.3)
        inv[pid]["visits"].append(vrec); L("   v%s %s | %s | %s" % (r["id"], vrec["chgs"], "; ".join(vrec["errs"])[:80], {k: vrec.get(k) for k in ("cid","v_insorder","onhcfa","facility","pos","cpt","dx","hospfrom","insbal","patbal","payments")}))
    # Stedi cascade when no open ACTIVE plan
    active = [p for p in plans if not p["end"] and "ACTIVE" in (p.get("elig") or "").upper() and "INACTIVE" not in (p.get("elig") or "").upper()]
    if not active:
        name = pa.get("name") or ""; dob = pa.get("dob") or ""; last, first = (name.split(",") + [""])[:2]; first = first.strip().split(" ")[0]; last = last.strip()
        m = re.match(r"(\d\d)/(\d\d)/(\d{4})", dob); dob8 = "%s%s%s" % (m.group(3), m.group(1), m.group(2)) if m else None
        dos = sorted([c[1] for v in inv[pid]["visits"] for c in v["chgs"] if c[1]])[0] if inv[pid]["visits"] else "09/22/2026"
        dos8 = dos[6:10] + dos[0:2] + dos[3:5]
        if dob8:
            try:
                j = stedi.mbi(first, last, dob8, "FL", dos8, pid=pid); s = stedi.med_summ(j); inv[pid]["mbi"] = s
                L("   MBI lookup: mbi=%s A=%s B=%s death=%s errors=%s other=%s" % (s.get("mbi"), s.get("partA"), s.get("partB"), s.get("death"), s.get("errors"), [(o.get("type"), o.get("typeName"), o.get("plan"), o.get("entity"), o.get("dates")) for o in (s.get("other") or [])][:5]))
            except Exception as e: inv[pid]["mbi"] = {"errors": ["EXC %s" % str(e)[:160]]}; L("   MBI EXC %s" % str(e)[:160])
            time.sleep(1.0)
            s = inv[pid]["mbi"]
            if not (isinstance(s, dict) and s.get("mbi") and not s.get("errors")):
                try: d = stedi.disc(first, last, dob8, "FL", dos8); inv[pid]["disc"] = stedi.disc_summ(d); L("   discovery: %s" % json.dumps(inv[pid]["disc"])[:700])
                except Exception as e: inv[pid]["disc"] = {"errors": ["EXC %s" % str(e)[:160]]}; L("   disc EXC %s" % str(e)[:160])
                time.sleep(1.0)
        else: L("   no DOB on chart - no lookup")
    time.sleep(0.3)
# Pam admits 9/28 - chart lookup only
look = {}
for q in ["FORBES,DIA%", "FORD,SAM%", "HATCHETT,DAI%", "ROSS,MAR%", "BERGER,VIC%", "POWLETTE,SAN%", "CHRISTOPHER,CHR%"]:
    try:
        lp = amd.post(amd.msg("lookuppatient", "lookup", {"name": q, "nocookie": "1"})); root = ET.fromstring(lp.encode("latin-1", "ignore"))
        look[q] = [{"id": x.get("id"), "name": x.get("name"), "chart": x.get("chart"), "dob": x.get("dob")} for x in root.iter("patient")]
    except Exception as e: look[q] = "ERR %s" % str(e)[:100]
    L("lookup %s -> %s" % (q, look[q])); time.sleep(0.3)
inv["_lookups"] = look
json.dump(inv, open("inv_2310.json", "w"), indent=1, default=str)
L("DONE %d patients" % (len(inv) - 1))
