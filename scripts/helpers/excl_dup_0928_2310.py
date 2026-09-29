# PLAIN ENGLISH (7pm ET 9/28/2026 run 2026-09-28T2310Z): claim run 1700243 carries six PAYER duplicate-claim rejections - WEL04 x5
# ("THIS SEEMS TO BE A DUPLICATE OF A CLAIM SUBMITTED 06/26 / 08/31 / 09/24/2026": pat17476912 v19445941, pat17477375 v19451378/86, v19451481,
# v19455316) and UNI20 x1 (pat17475777 v19447314 SMARTEDIT UDCP3 duplicate of claim FX95619592). Standing rule (step 4): duplicate-claim
# rejections -> hideexclusions, NO rebill. Reads each chart's tx history first (balance/payment state for the report), completes the rows,
# re-lists the run. Never touches: rebills, payments, charges. Adapted from excl_dup_0924_1310.py.
import amd, re, json, time
S = "2026-09-28T2310Z"; RUN = "1700243"
s = json.load(open("scan_0912/summary_before.json"))
rows = [r for r in s["exclusions"].get(RUN, []) if "DUPLICATE" in " ".join((e.get("name") or e.get("text") or "") for e in (r.get("_errs") or [])).upper()]
print("rows", len(rows), [(r["id"], r["claimid"], r["patientid"]) for r in rows])
reg = {"run": RUN, "stamp": S, "rows": [], "charges": []}
for r in rows:
    pid = r["patientid"]
    t = amd.post(amd.msg("gettxhistory", "demographics", {"patientid": pid, "filterhistory": "0", "pagenumber": "1", "typefilter": "1", "sortbypayment": "false", "groupbyvisit": "0", "sortdescending": "1", "visitid": "0", "getmemo": "false", "nocookie": "1"}), timeout=120)
    for m in re.finditer(r'<charge [^>]*/?>', t):
        a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(0)))
        if a.get("visit") == r["id"]:
            c = {k: a.get(k) for k in ("id", "visit", "proccode", "dos", "carrier", "billdate", "insbilled", "insbal", "patbal", "paid", "insorder", "payerinfo")}
            c["pid"] = pid; reg["charges"].append(c); print(" ", c)
    reg["rows"].append({"visit": r["id"], "claimid": r["claimid"], "pid": pid, "dos": (r["_chgs"] or [{}])[0].get("dos", "").strip(), "err": (r["_errs"] or [{}])[0].get("name", "")[:140]})
    time.sleep(0.5)
lst = "".join('<visit id="%s" claimid="%s"/>' % (r["id"], r["claimid"]) for r in rows)
x = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": RUN, "hide": "-1", "nocookie": "1"}, "<visitlist>%s</visitlist>" % lst), timeout=120)
reg["hide_result"] = re.sub(r"\s+", " ", x[:300]); print("hideexclusions ->", reg["hide_result"])
time.sleep(1)
y = amd.post(amd.msg("getclaimexclusioncharges", "claimsreports", {"claimrunid": RUN, "clearinghouse": "1", "payer": "1", "nocookie": "1"}), timeout=120)
reg["relist_visits"] = re.findall(r'<visit id="(\d+)"', y); print("re-list run %s visits:" % RUN, reg["relist_visits"])
json.dump(reg, open("registers/excl_dup_%s_%s.json" % (RUN, S), "w"), indent=1)
