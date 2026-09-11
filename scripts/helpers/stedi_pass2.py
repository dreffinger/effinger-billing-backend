# PLAIN ENGLISH (Second Stedi pass on the board candidates - before anything goes to William)
# Decides: For the denial-cascade patients that were parked for William, asks Stedi everything that is live today: (MA) eligibility at the Advantage payer Medicare named, using the MBI as the member id - most MA payers hand back their own member id; (NO) MBI lookup with the chart SSN and Florida Medicaid with the SSN for patients CMS could not find by name/DOB; (MCD) Florida Medicaid eligibility for the in-window Medicaid 'not on file' claims, to get the HIC / SMMC plan.
# Rules it uses: read-only - prints a verdict per patient to stedi_pass2_<date>.json; the acting is done afterwards with the proven helpers (add_ins / move_to_ins / freq1_visit). Never prints an SSN.
# Never touches: AMD charts or claims.
# ---
import amd, stedi, json, re, glob, datetime, collections, sys
from precheck import CAR2STEDI, CARRIERS
amd.login_cached(); today = datetime.date.today(); stamp = today.strftime("%Y%m%d"); CUT = (today - datetime.timedelta(days=365)).isoformat()
which = set(sys.argv[1].split(",")) if len(sys.argv) > 1 else {"MA", "NO", "MCD"}
c = [json.loads(l) for l in open(sorted(glob.glob("denial_cascade2_*.jsonl"))[-1])]
sweep = [json.loads(l) for l in open(sorted(glob.glob("claimstatus_full_*.jsonl"))[-1])]
MA_PAYER = [("PREFERRED CARE", "87726", "car6404"), ("UNITEDHEALTH", "87726", "car6404"), ("AARP", "87726", "car6404"), ("AETNA", "60054", "car6047"), ("SUNSHINE", "68069", "car6194"), ("WELLCARE", "68069", "car6174"), ("CAPITAL HEALTH", "95112", "car41826"), ("BCBS OF MICHIGAN", "00710", "car6062"), ("HUMANA", "61101", "car6285"), ("CIGNA", "63092", "car42014"), ("SIMPLY", "SMPLY", "car42019"), ("FLORIDA COMMUNITY", None, "car42008")]
def demo(pid):
    r = amd.post('<ppmdmsg action="getdemographic" class="demographics" msgtime="%s" patientid="pat%s" nocookie="1"/>' % (amd._msgtime(), pid))
    m = re.search(r'<patient [^>]*>', r).group(0); a = dict(re.findall(r'(\w+)="([^"]*)"', m))
    pl = re.findall(r'<insplan id="(ins\d+)" carrier="(car\d+)" begindate="([^"]*)" enddate="([^"]*)"[^>]*subscribernum="([^"]*)"[^>]*sequence="(\d+)"', r)
    return a, pl
def nm_split(nm): return nm.split(",")[-1].strip().split(" ")[0], nm.split(",")[0].strip()
def dobc(d): return d[6:] + d[:2] + d[3:5]
out = []
for rec in c:
    v = rec["verdict"]; pid = rec["pid"]; nm = rec["patient"]; first, last = nm_split(nm); a, pl = demo(pid); db = dobc(a.get("dob", rec["dob"])); dos = rec["last"].replace("-", "")
    o = {"pid": pid, "patient": nm, "claims": rec["claims"], "balance": rec["balance"], "group": None, "tries": [], "verdict": None}
    if v.startswith("billed plan INACTIVE; Medicare names") and "MA" in which:
        o["group"] = "MA"; mbi = rec["cms"]["mbi"]
        j = stedi.mbi(first, last, db, "FL", dos); m = stedi.med_summ(j)
        o["cms_other"] = [{"code": x["code"], "type": x["type"], "typeName": x["typeName"], "plan": x["plan"], "dates": x["dates"], "entity": x["entity"]} for x in m["other"]]
        o["partA"], o["partB"] = m["partA"], m["partB"]
        ent = (rec["cms"]["ma"][0][0] or "").upper(); hit = next((h for h in MA_PAYER if h[0] in ent), None)
        o["ma_entity"] = ent; o["ma_car"] = hit[2] if hit else None
        typ = next((x["type"] for x in m["other"] if any(ent in (e[0] or "").upper() for e in x["entity"])), None)
        if typ in ("PR", "PS"): o["verdict"] = "SUPPLEMENT/PDP only (%s) -> original Medicare is primary: bill Medicare first" % typ
        elif hit and hit[1]:
            try:
                e = stedi.elig(hit[1], first, last, db, mbi, dos); st = [(s.get("status"), (s.get("planDetails") or "")[:40]) for s in e.get("planStatus") or []]
                sub = e.get("subscriber") or {}; mem = sub.get("memberId"); errs = ["%s %s" % (x.get("code"), (x.get("description") or "")[:50]) for x in e.get("errors") or []]
                o["tries"].append({"payer": hit[1], "with": "MBI", "status": st, "member": mem, "dates": e.get("planDateInformation"), "errors": errs, "eid": e.get("id")})
                act = any(s[0] == "Active Coverage" for s in st)
                if act and mem: o["verdict"] = "MA ACTIVE at %s member %s -> add %s + rebill" % (hit[1], mem, hit[2])
                elif act: o["verdict"] = "MA ACTIVE at %s but no member id returned -> board (needs plan card)" % hit[1]
                else: o["verdict"] = "MA payer %s: %s -> board" % (hit[1], errs or st)
            except Exception as ex: o["verdict"] = "MA elig error %s" % str(ex)[:80]
        else: o["verdict"] = "MA payer not mapped (%s) -> board" % ent
    elif (v.startswith("billed plan INACTIVE on DOS and no") or v.startswith("could not verify")) and "NO" in which:
        o["group"] = "NO"; ssn = re.sub(r"\D", "", a.get("ssn", "")); o["has_ssn"] = len(ssn) == 9
        # 1. MBI with SSN
        if len(ssn) == 9:
            j = stedi.mbi(first, last, db, "FL", dos, ssn=ssn); m = stedi.med_summ(j)
            o["tries"].append({"payer": "MBILU(ssn)", "mbi": m["mbi"], "partA": m["partA"], "partB": m["partB"], "death": m["death"], "errors": m["errors"], "other": [(x["typeName"], x["entity"], x["dates"]) for x in m["other"]]})
            # 2. Medicaid with SSN
            try:
                e = stedi.elig("77027", first, last, db, ssn, dos); b = e.get("benefitsInformation") or []
                mco = [(x.get("planCoverage"), (x.get("benefitsRelatedEntity") or {}).get("entityName")) for x in b if x.get("code") == "MC" and x.get("name") == "Managed Care Coordinator"]
                hic = (e.get("planInformation") or {}).get("hicNumber") if isinstance(e.get("planInformation"), dict) else None
                act = any(x.get("code") == "1" and x.get("insuranceTypeCode") == "MC" for x in b)
                o["tries"].append({"payer": "77027(ssn)", "active": act, "hic": hic, "mco": mco, "member": (e.get("subscriber") or {}).get("memberId"), "errors": ["%s %s" % (x.get("code"), (x.get("description") or "")[:50]) for x in e.get("errors") or []]})
            except Exception as ex: o["tries"].append({"payer": "77027(ssn)", "error": str(ex)[:80]})
        # 3. other plans on the chart (open, not the billed one), by their own member id
        billed = CARRIERS.get(list(rec["carriers"])[0])
        for p in pl:
            if p[1] == billed or p[3] or not p[4]: continue
            code = next((k for k, cv in CARRIERS.items() if cv == p[1]), None); sp = CAR2STEDI.get(code)
            if not sp: continue
            try:
                e = stedi.elig(sp, first, last, db, p[4], dos) if sp != "MEDICARE" else stedi.elig("CMS", first, last, db, p[4], dos)
                st = [(s.get("status"), (s.get("planDetails") or "")[:40]) for s in e.get("planStatus") or []]
                o["tries"].append({"payer": sp, "with": "%s seq %s" % (code, p[5]), "status": st, "dates": e.get("planDateInformation"), "errors": ["%s %s" % (x.get("code"), (x.get("description") or "")[:50]) for x in e.get("errors") or []]})
            except Exception as ex: o["tries"].append({"payer": sp, "error": str(ex)[:80]})
        # 4. re-try the billed plan with a dependent-style search: subscriber id + no name (some BCBS ids belong to the spouse)
        t = o["tries"]; mb = next((x for x in t if x["payer"].startswith("MBILU") and x.get("mbi")), None); md = next((x for x in t if x["payer"].startswith("77027") and (x.get("hic") or x.get("mco") or x.get("active"))), None)
        oth = [x for x in t if x.get("status") and any(s[0] == "Active Coverage" for s in x["status"])]
        if mb and md and md.get("mco"): o["verdict"] = "Medicare %s + SMMC %s -> Medicare first, plan second" % (mb["mbi"], md["mco"])
        elif mb and md: o["verdict"] = "Medicare %s + straight Medicaid -> Medicare first, Medicaid second" % mb["mbi"]
        elif mb: o["verdict"] = "Medicare %s found by SSN -> add Medicare, rebill" % mb["mbi"]
        elif md and md.get("mco"): o["verdict"] = "Medicaid SMMC %s (no Medicare) -> add plan, rebill" % md["mco"]
        elif md: o["verdict"] = "straight Medicaid ACTIVE (no Medicare) -> add Medicaid, rebill"
        elif oth: o["verdict"] = "other chart plan ACTIVE: %s -> point visits there" % oth[0]["with"]
        else: o["verdict"] = "nothing live at Stedi (%s) -> facesheet / discovery when live" % ("no SSN on chart" if len(ssn) != 9 else "SSN tried")
    else: continue
    out.append(o); print("%-24s %-3s %2d $%-7.0f %s" % (nm[:24], o["group"], o["claims"], o["balance"], o["verdict"][:120]), flush=True)
if "MCD" in which:
    old = collections.defaultdict(list)
    for r in sweep:
        if r["carrier"] == "MCAD" and r["action"].startswith("NOT ON FILE") and r["dos"] >= CUT and r["balance"] > 0: old[r["patientid"]].append(r)
    for pid, cl in old.items():
        a, pl = demo(pid); nm = a.get("name") or cl[0]["patient"]; first, last = nm_split(nm); db = dobc(a.get("dob", "")); dos = max(r["dos"] for r in cl).replace("-", "")
        mid = next((p[4] for p in pl if p[1] == "car6113"), cl[0].get("member")); o = {"pid": pid, "patient": nm, "group": "MCD", "claims": len(cl), "balance": round(sum(r["balance"] for r in cl), 2), "codes": sorted({s.get("code") for r in cl for s in r["status"]}), "tries": [], "chart": [(p[1], p[4], p[2], p[3], p[5]) for p in pl]}
        try:
            e = stedi.elig("77027", first, last, db, mid, dos); b = e.get("benefitsInformation") or []
            mco = [(x.get("planCoverage"), (x.get("benefitsRelatedEntity") or {}).get("entityName")) for x in b if x.get("code") == "MC" and x.get("name") == "Managed Care Coordinator"]
            hic = (e.get("planInformation") or {}).get("hicNumber") if isinstance(e.get("planInformation"), dict) else None
            act = any(x.get("code") == "1" and x.get("insuranceTypeCode") == "MC" for x in b)
            o["tries"].append({"payer": "77027", "active": act, "hic": hic, "mco": mco, "errors": ["%s %s" % (x.get("code"), (x.get("description") or "")[:50]) for x in e.get("errors") or []]})
            has_med = any(p[1] == "car6085" for p in pl)
            if hic and not has_med: o["verdict"] = "MEDICARE PRIMARY HIC %s missing on chart -> add Medicare, bill Medicare first" % hic
            elif mco and any(("MMA" in (m[0] or "")) or ("LTC" in (m[0] or "")) for m in mco): o["verdict"] = "SMMC PLAN %s -> add plan, rebill" % [m for m in mco if m[1]]
            elif act: o["verdict"] = "Medicaid ACTIVE straight%s -> resend original" % (" (Medicare on chart first)" if has_med else "")
            else: o["verdict"] = "Medicaid not active (%s) -> board" % o["tries"][0]["errors"]
        except Exception as ex: o["verdict"] = "elig error " + str(ex)[:80]
        out.append(o); print("%-24s %-3s %2d $%-7.0f %s" % (nm[:24], "MCD", o["claims"], o["balance"], o["verdict"][:120]), flush=True)
json.dump(out, open("stedi_pass2_%s.json" % stamp, "w"), indent=1, default=str)
print("done", len(out))
