# PLAIN ENGLISH (Pam admit emails, 3 PM ET 10/8/2026 run 2026-10-08T1910Z): READ-ONLY pass for new facility admits.
# Decides: nothing. For every admit spec in the JSON file given as argv[1] (kept in inbox/, never mirrored - it carries names,
#   DOBs and member ids from the facesheet): (1) lookuppatient LAST,FIR% -> which AMD charts exist and their DOB;
#   (2) getdemographic on every chart found -> default insurance order + plans (carrier, member id, dates, sequence);
#   (3) AMD's own free 271 on every active plan (elig_amd.run_plan, cached per day); (4) the Stedi checks the spec names
#   (CMS 271 by MBI, CMS MBI lookup by name/DOB, FL Medicaid 77027, a payer 271 by member id) so the insurance order can be
#   decided per William's lookup order (patient_db -> AMD 271 -> Stedi -> facesheet -> William).
# Writes: registers/admit_lookup_<stamp>.json (chart ids + what each source said; no SSN). No AMD write.
# Never touches: insurance plans, visits, claims. Usage: python3 admit_reads_1910.py inbox/pam/admits_1910.json
import amd, elig_amd, stedi, re, json, sys, time, datetime
STAMP = "2026-10-08T1910Z"; amd.login_cached()
spec = json.load(open(sys.argv[1])); out = {"stamp": STAMP, "admits": []}
def attrs(x): return dict(re.findall(r'(\w+)="([^"]*)"', x))
for a in spec:
    rec = {"label": a["label"], "lookup": [], "charts": {}, "stedi": {}}
    r = amd.post(amd.msg("lookuppatient", "lookup", {"name": a["lookup"], "nocookie": "1"}))
    pats = [attrs(x) for x in re.findall(r'<patient [^>]*/?>', r)]
    rec["lookup"] = [{"id": p.get("id"), "dob": p.get("dob"), "chart": p.get("chart")} for p in pats]
    print("lookup", a["label"], [(p.get("id"), p.get("dob")) for p in pats]); time.sleep(0.3)
    for p in pats:
        pid = re.sub(r"\D", "", p.get("id") or "")
        if not pid or p.get("dob", "").strip() != a["dob_amd"]: print("  skip", p.get("id"), p.get("dob"), "(dob differs)"); continue
        pa, plans = elig_amd.plans(pid)
        rec["charts"][pid] = {"insorder": pa.get("insorder"), "plans": [{k: pl.get(k) for k in ("id", "sequence", "carrier", "subscribernum", "begindate", "enddate", "finclass")} for pl in plans], "elig": {}}
        print("  pat%s insorder=%s plans=%s" % (pid, pa.get("insorder"), [(pl.get("id"), pl.get("sequence"), pl.get("carrier"), pl.get("begindate"), pl.get("enddate")) for pl in plans]))
        for pl in plans:
            if pl.get("enddate"): continue
            try:
                s = elig_amd.run_plan(pid, pl["id"].replace("ins", ""))
                rec["charts"][pid]["elig"][pl["id"]] = elig_amd.one_line(s); print("    271", pl["id"], pl.get("carrier"), elig_amd.one_line(s)[:200])
            except Exception as e: rec["charts"][pid]["elig"][pl["id"]] = "ERR %s" % e; print("    271", pl["id"], "ERR", e)
            time.sleep(0.4)
    for chk in a.get("stedi", []):
        kind = chk["kind"]; pid = next(iter(rec["charts"]), None)
        try:
            if kind == "mbi": j = stedi.mbi(a["first"], a["last"], a["dob"], state="FL", dos=a["dos"], pid=pid); s = stedi.med_summ(j)
            elif kind == "elig": j = stedi.elig(chk["payer"], a["first"], a["last"], a["dob"], chk["member"], a["dos"], pid=pid); s = stedi.med_summ(j) if chk["payer"] == "CMS" else {"errors": j.get("errors"), "plans": [(b.get("code"), b.get("planCoverageDescription"), b.get("insuranceTypeCode"), b.get("serviceTypeCodes")) for b in j.get("benefitsInformation", [])[:12] if b.get("code") in ("1", "6", "7", "8")], "planDates": j.get("planDateInformation"), "planStatus": j.get("planStatus")}
            elif kind == "disc": j = stedi.disc(a["first"], a["last"], a["dob"], dos=a["dos"]); s = stedi.disc_summ(j)
            else: continue
            rec["stedi"][kind + ":" + chk.get("payer", "")] = s; print("  stedi", kind, chk.get("payer", ""), json.dumps(s)[:600])
        except Exception as e: rec["stedi"][kind + ":" + chk.get("payer", "")] = "ERR %s" % e; print("  stedi", kind, "ERR", e)
        time.sleep(0.5)
    out["admits"].append(rec)
json.dump(out, open("registers/admit_lookup_%s.json" % STAMP, "w"), indent=1)
print("saved registers/admit_lookup_%s.json" % STAMP)
