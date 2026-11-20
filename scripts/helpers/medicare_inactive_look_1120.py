# PLAIN ENGLISH (Why does Medicare answer INACTIVE on these charts? 11/20/2026) - READ ONLY, no paid call.
# Decides: Nothing. Re-reads the saved free eligibility answer of each chart the scan found INACTIVE and prints what it says: a date
#          of death, the Part A / Part B dates, and the open Medicare visits newer / older than the end of coverage.
import amd, elig_amd, ins_update, txh, json, re, datetime, collections
amd.login_cached(); o = [x for x in json.load(open("medicare_number_scan_1120.json")) if x["status"] == "INACTIVE"]
tally = collections.Counter()
for x in o:
    s = elig_amd.run_plan(x["pid"], x["ins"].replace("ins", ""), False)
    dos = sorted({c.get("dos")[6:] + c.get("dos")[:2] + c.get("dos")[3:5] for c in txh.fetch(x["pid"]).iter("charge") if c.get("void") != "1" and c.get("carrier") == "FLO02" and float(c.get("insbal") or 0) > 0.005})
    k = "date of death on Medicare's record" if s.get("date_of_death") else "no death on record"
    tally[k] += 1
    print("pat%s $%.2f %d visits | %s %s | plan dates %s A %s B %s | open Medicare visits %s .. %s" % (x["pid"], x["amt"], x["n"], k, s.get("date_of_death") or "", s.get("plan_dates"), s.get("partA"), s.get("partB"), dos[:1], dos[-1:]))
print(dict(tally))
