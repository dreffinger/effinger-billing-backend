# PLAIN ENGLISH (insurance-cascade lookups for the 10/14/2026 chat pass) - reads only (Stedi + AMD's free 271).
# Decides: nothing by itself. For each chart it (1) runs AMD's free 271 on every plan whose eligibility was never checked,
#   (2) runs the Stedi Medicare lookup (MBILU with the chart SSN when AMD holds one, else MBILUNOSSN by name/DOB/FL) at the
#   date of service in question, (3) optionally a payer eligibility call on a named plan. Results go to patient_db/<pid>/
#   and a one-line summary per chart (MBI masked, no SSN ever printed).
# Never touches: AMD writes.
import amd, stedi, json, os, re, sys, time, datetime
amd.login_cached()
os.makedirs("patient_db", exist_ok=True)

def demo(pid):
    r = amd.post('<ppmdmsg action="getdemographic" class="demographics" msgtime="%s" patientid="%s" nocookie="1"/>' % (amd._msgtime(), pid))
    pat = dict(re.findall(r'(\w+)="([^"]*)"', re.search(r'<patient [^>]*>', r).group(0)))
    plans = [dict(re.findall(r'(\w+)="([^"]*)"', t)) for t in re.findall(r'<insplan [^>]*>', r)]
    plans = [p for p in plans if p.get("id")]
    return pat, plans

def ymd(mdy):
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", mdy or ""); return "%s%s%s" % (m.group(3), m.group(1), m.group(2)) if m else None

def mask(s): s = str(s or ""); return "*" * max(0, len(s) - 4) + s[-4:]

def amd271(pid, plans):
    out = []
    for p in plans:
        try:
            code, body = amd.check_eligibility(p["id"].replace("ins", ""))
            txt = json.dumps(body) if not isinstance(body, str) else body
            aaa = re.findall(r"AAA\*[^~]*", txt)[:3]
            active = ("AAA" not in txt) and code == 200
            inactive = bool(re.search(r'"code":\s*"6"', txt)) or "Inactive" in txt or "INACTIVE" in txt
            out.append({"ins": p["id"], "carrier": p.get("carrier"), "http": code, "active_guess": active and not inactive, "aaa": aaa, "len": len(txt)})
            open("patient_db/%s/amd271_%s.json" % (pid, p["id"]), "w").write(txt)
        except Exception as e:
            out.append({"ins": p["id"], "carrier": p.get("carrier"), "error": str(e)[:160]})
        time.sleep(0.4)
    return out

jobs = json.loads(sys.argv[1])   # [{"pid":..., "dos":"YYYYMMDD", "mbi":true, "elig":[["95112","<member>"], ...]}]
summary = {}
for j in jobs:
    pid = str(j["pid"]); os.makedirs("patient_db/%s" % pid, exist_ok=True)
    pat, plans = demo(pid)
    last, first = (pat.get("name", "").split(",") + [""])[:2]
    first = first.strip().split(" ")[0]; last = last.strip()
    suffix = ""
    m = re.match(r"(.*?)\s+(JR|SR|II|III|IV)\.?$", last, re.I)
    dob = ymd(pat.get("dob")); ssn = (pat.get("ssn") or "").replace("-", "")
    rec = {"pid": pid, "dob": pat.get("dob"), "sex": pat.get("sex"), "deceased": pat.get("deceased"), "plans": [(p.get("id"), p.get("carrier"), p.get("sequence"), p.get("begindate"), p.get("enddate"), mask(p.get("subscribernum"))) for p in plans]}
    unchecked = [p for p in plans if not p.get("eligibilitystatusid")] if j.get("amd271") == "unchecked" else (plans if j.get("amd271") == "all" else [])
    if unchecked: rec["amd271"] = amd271(pid, unchecked)
    if j.get("mbi"):
        try:
            r = stedi.mbi(first, last, dob, state="FL", dos=j.get("dos"), ssn=ssn or None, pid=pid)
            json.dump(r, open("patient_db/%s/stedi_mbi_%s.json" % (pid, j.get("dos")), "w"))
            s = stedi.med_summ(r); s["mbi"] = mask(s.get("mbi")); s.pop("address", None); s["name"] = "<chart>"
            rec["mbi_lookup"] = {"mode": "MBILU" if ssn else "MBILUNOSSN", "dos": j.get("dos"), "summary": s}
        except Exception as e:
            rec["mbi_lookup"] = {"error": str(e)[:300]}
        time.sleep(0.5)
    for payer, member, dos in j.get("elig", []):
        if str(member).startswith("ins"):   # an insplan id -> its subscriber number from the chart
            member = next((p.get("subscribernum") for p in plans if p.get("id") == member), member)
        try:
            r = stedi.elig(payer, first, last, dob, member, dos, pid=pid)
            json.dump(r, open("patient_db/%s/stedi_elig_%s_%s.json" % (pid, payer, dos), "w"))
            errs = ["%s %s" % (e.get("code"), (e.get("description") or "")[:80]) for e in r.get("errors") or []]
            b = r.get("benefitsInformation") or []
            act = [x for x in b if x.get("code") == "1"]
            inact = [x for x in b if x.get("code") == "6"]
            pdi = r.get("planDateInformation") or {}
            pl = [(x.get("insuranceTypeCode"), x.get("planCoverage"), (x.get("benefitsDateInformation") or {})) for x in act][:3]
            ent = sorted({(e.get("entityName")) for x in b for e in (x.get("benefitsRelatedEntities") or []) if e.get("entityName")})[:6]
            rec.setdefault("elig", []).append({"payer": payer, "member": mask(member), "dos": dos, "errors": errs, "active_n": len(act), "inactive_n": len(inact), "planDates": pdi, "active_plans": pl, "entities": ent})
        except Exception as e:
            rec.setdefault("elig", []).append({"payer": payer, "dos": dos, "error": str(e)[:300]})
        time.sleep(0.5)
    if j.get("disc"):
        try:
            r = stedi.disc(first, last, dob, "FL", dos=j.get("dos"))
            json.dump(r, open("patient_db/%s/stedi_disc_%s.json" % (pid, j.get("dos")), "w"))
            items = []
            for it in r.get("items") or []:
                items.append({"payer": (it.get("payer") or {}).get("name"), "payerId": (it.get("payer") or {}).get("payerId"), "member": mask((it.get("subscriber") or {}).get("memberId")), "dates": it.get("planDateInformation")})
            rec["discovery"] = {"coveragesFound": r.get("coveragesFound"), "items": items, "errors": [e.get("description") for e in r.get("errors") or []][:3]}
        except Exception as e:
            rec["discovery"] = {"error": str(e)[:300]}
    summary[pid] = rec
    print(json.dumps(rec, default=str))
json.dump(summary, open("cascade_lookups_1014.json", "w"), indent=1, default=str)
