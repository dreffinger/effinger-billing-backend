# PLAIN ENGLISH (read-only context for chart 17473661 after UHC 1053227 PR-27, run 2026-10-20T2110Z): prints the chart's
# insurance plans (ids, carriers, dates - no names, no member ids), the live state of its other 2026 visits that carry a
# Medicare PR coinsurance, and asks Stedi (insurance discovery + UHC 87726 eligibility at DOS 9/18/2026) whether any plan
# other than Medicare was in force. Decides nothing, writes nothing in AMD. Names and member ids are never printed.
import json, re, glob, txh, ins_update, stedi
pid = "17473661"; DOS = "20260918"
raw, plans, order = ins_update._plans(pid)
print("patient insorder:", order)
uhc = None
for i, p in plans.items():
    print("plan", i, {k: p.get(k) for k in ("carrier", "sequence", "begindate", "enddate", "coverage")})
    if p.get("carrier") == "car6404": uhc = p
for vid in ("19455745", "19453814"):
    root = txh.fetch_visit(pid, vid)
    for c in root.iter("charge"):
        if c.get("void") == "1" or c.get("visit") != vid: continue
        print(vid, c.get("id"), c.get("proccode"), c.get("begindate"), "fee", c.get("fee"), "ins", c.get("insbal"), "pat", c.get("patbal"), "carrier", c.get("carrier"), "billdate", c.get("billdate"),
              [(w.get("amount"), (w.get("code") or "").strip(), w.get("void")) for w in c.iter("writeoff")],
              [((p.get("checknumber") or "").strip(), p.get("amount"), p.get("carrier"), p.get("void")) for p in c.iter("payment")])
m = re.search(r'patientname="([^"]+)"', open(sorted(glob.glob("patient_db/%s/*.xml" % pid))[0]).read())
name = m.group(1) if m else ""; last, first = (name.split(",") + [""])[:2]; first = first.strip().split(" ")[0].strip(); last = last.strip()
dob = json.load(open(sorted(glob.glob("patient_db/%s/*.json" % pid))[0])).get("dob")
print("demographics for Stedi:", bool(first), bool(last), bool(dob))
try:
    d = stedi.disc(first, last, dob, "FL", DOS, pid=pid) if "pid" in stedi.disc.__code__.co_varnames else stedi.disc(first, last, dob, "FL", DOS)
    json.dump(d, open("patient_db/%s/stedi_disc_%s.json" % (pid, DOS), "w"))
    print("DISCOVERY:", stedi.disc_summ(d) if hasattr(stedi, "disc_summ") else json.dumps(d)[:600])
except Exception as e: print("discovery error:", str(e)[:300])
if uhc and uhc.get("subscribernum"):
    try:
        e = stedi.elig("87726", first, last, dob, uhc["subscribernum"], DOS, pid=pid)
        json.dump(e, open("patient_db/%s/stedi_elig_87726_%s.json" % (pid, DOS), "w"))
        s = json.dumps(e); print("UHC 87726 at DOS:", [x for x in re.findall(r'"(planStatus|planDateInformation|statusCode|code|description|planBegin|planEnd|eligibilityBegin|eligibilityEnd|followupAction)": ?"?([^",}]+)', s)][:30])
    except Exception as ex: print("uhc elig error:", str(ex)[:300])
