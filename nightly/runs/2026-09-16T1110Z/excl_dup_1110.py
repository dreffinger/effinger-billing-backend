# PLAIN ENGLISH (7am ET 9/16/2026 run): 18 HUM01 rows on claim run 1700192 (one chart, pat44953) are payer
# duplicate-claim rejections ("DUPLICATE OF A PREVIOUSLY PROCESSED CLAIM"). Standing rule (step 4): duplicate-claim
# rejections -> hideexclusions, NO rebill. Reads the chart's tx history first (records balance/payment state for the
# report), then completes the 18 exclusion rows and re-lists the run. Never touches: rebills, payments, charges.
import amd, re, json, time
s = json.load(open("scan_0912/summary_before.json"))
rows = [r for r in s["exclusions"].get("1700192", []) if r.get("patientid") == "44953"]
print("rows", len(rows))
t = amd.post(amd.msg("gettxhistory","demographics",{"patientid":"44953","filterhistory":"0","pagenumber":"1","typefilter":"1","sortbypayment":"false","groupbyvisit":"0","sortdescending":"1","visitid":"0","getmemo":"false","nocookie":"1"}),timeout=120)
vids = {r["id"] for r in rows}
chg = []
for m in re.finditer(r'<charge [^>]*/?>', t):
    a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(0)))
    if a.get("visit") in vids:
        chg.append({k: a.get(k) for k in ("id","visit","proccode","dos","carrier","lastbilledcarrier","datebilled","billdate","insbilled","insbal","patbal","paid","insorder","payerinfo")})
for c in chg: print(c)
reg = {"run": "1700192", "pid": "44953", "rows": [{"visit": r["id"], "claimid": r["claimid"], "dos": (r["_chgs"] or [{}])[0].get("dos","").strip(), "err": (r["_errs"] or [{}])[0].get("name","")[:120]} for r in rows], "charges": chg}
lst = "".join('<visit id="%s" claimid="%s"/>' % (r["id"], r["claimid"]) for r in rows)
x = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": "1700192", "hide": "-1", "nocookie": "1"}, "<visitlist>%s</visitlist>" % lst), timeout=120)
reg["hide_result"] = re.sub(r"\s+", " ", x[:300])
print("hideexclusions ->", reg["hide_result"])
time.sleep(1)
y = amd.post(amd.msg("getclaimexclusioncharges", "claimsreports", {"claimrunid": "1700192", "clearinghouse": "1", "payer": "1", "nocookie": "1"}), timeout=120)
left = re.findall(r'<visit id="(\d+)"', y)
reg["relist_visits"] = left
print("re-list run 1700192 visits:", len(left))
json.dump(reg, open("registers/excl_dup_1700192_2026-09-16T1110Z.json", "w"), indent=1)
