# PLAIN ENGLISH (Stedi insurance discovery, 11 AM ET 10/16/2026 run 2026-10-16T1510Z) - READ ONLY.
# Decides: nothing. For each pid:YYYYMMDD it reads the chart name/DOB from getdemographic, runs stedi.disc (insurance
#   discovery, $1.50) at that date of service, saves the raw answer to patient_db/<pid>/stedi_disc_<dos>.json and prints
#   the masked summary (payer, plan, dates, member id masked). No AMD write, no SSN printed.
# Usage: python3 disc_lookup_1016_1510.py <pid>:<YYYYMMDD> ...
import sys, json, os, re, amd, stedi
amd.login_cached()
def mask(s): s = str(s or ""); return "*" * max(0, len(s) - 4) + s[-4:]
for arg in sys.argv[1:]:
    pid, dos = arg.split(":")
    r = amd.post('<ppmdmsg action="getdemographic" class="demographics" msgtime="%s" patientid="%s" nocookie="1"/>' % (amd._msgtime(), pid))
    pat = dict(re.findall(r'(\w+)="([^"]*)"', re.search(r'<patient [^>]*>', r).group(0)))
    name = pat.get("name", ""); last, first = (name.split(",") + [""])[:2]; first = first.strip().split(" ")[0]
    m = re.search(r'(\d{2})/(\d{2})/(\d{4})', pat.get("dob", "")); dob = m.group(3) + m.group(1) + m.group(2) if m else ""
    try: j = stedi.disc(first.strip(), last.strip(), dob, "FL", dos)
    except Exception as e: print(pid, dos, "disc ERR", str(e)[:160]); continue
    os.makedirs("patient_db/%s" % pid, exist_ok=True); json.dump(j, open("patient_db/%s/stedi_disc_%s.json" % (pid, dos), "w"), indent=1)
    items = j.get("items") or []
    print("== pid %s dos %s coveragesFound %s errors %s" % (pid, dos, j.get("coveragesFound"), [e.get("description") or e for e in (j.get("errors") or [])][:2]))
    for it in items:
        p = it.get("payer") or {}; s = it.get("subscriber") or {}; pdi = it.get("planDateInformation") or {}
        bi = it.get("benefitsInformation") or []
        st = sorted({(b.get("code"), b.get("name"), (b.get("planCoverage") or "")[:40]) for b in bi if b.get("code") in ("1", "6", "U", "R", "OT")})
        print("   payer %s (%s) member %s planBegin %s planEnd %s dod %s status %s" % (p.get("name"), p.get("payorIdentification") or p.get("id"), mask(s.get("memberId")), pdi.get("planBegin"), pdi.get("planEnd"), pdi.get("dateOfDeath"), st[:4]))
