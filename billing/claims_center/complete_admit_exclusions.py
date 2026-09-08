# PLAIN ENGLISH (Complete fixed admission exclusions)
# Decides: Marks 'missing admission date' exclusions completed once fix_admit_dates has repaired the visit.
# Rules it uses: Only exclusions whose visit shows an OK line in the fix log.
# Never touches: Unfixed visits.
# ---
"""Complete (hideexclusions) every 'PDTP0303 MISSING RELATED ADMISSION DATE' exclusion whose visit has already been
re-dated + rebilled by fix_admit_dates.py (OK lines).  Re-runnable.  Logs to complete_admit_exclusions.log"""
import amd, re, json, time, collections
fixed = {m.group(1) for l in open("fix_admit_dates.log") for m in [re.search(r"OK visit (\d+)", l)] if m}
log = open("complete_admit_exclusions.log", "a")
def L(m): print(m, flush=True); log.write(m + "\n"); log.flush()
s = amd.post(amd.msg("getclaimrunstatus", "claimsreports", {"nocookie": "1"}), timeout=90)
runs = [dict(re.findall(r'(\w+)="([^"]*)"', m)) for m in re.findall(r'<claimrun [^>]*>', s)]
tot = 0; left = collections.Counter(); other = collections.Counter()
for r in [r for r in runs if int(r.get("totalexclusions") or 0) > 0]:
    x = amd.post(amd.msg("getclaimexclusioncharges", "claimsreports", {"claimrunid": r["id"], "clearinghouse": "1", "payer": "1", "nocookie": "1"}), timeout=120)
    items = []
    for m in re.finditer(r'<visit ([^>]*)>(.*?)</visit>', x, re.S):
        a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1))); errs = re.findall(r'<error id="\d+" name="([^"]*)"', m.group(2))
        if all("PDTP0303" in e for e in errs):
            if a["id"] in fixed: items.append(a)
            else: left[r["id"]] += 1
        else: other[errs[0][:60] if errs else "?"] += 1
    if items:
        child = "<visitlist>" + "".join('<visit id="%s" claimid="%s"/>' % (a["id"], a["claimid"]) for a in items) + "</visitlist>"
        rr = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": r["id"], "hide": "-1", "nocookie": "1"}, child), timeout=120)
        ok = "Fault" not in rr; tot += len(items) if ok else 0
        L("run %s: completed %d admission-date exclusions -> %s" % (r["id"], len(items), "OK" if ok else re.sub(r"\s+", " ", rr[100:300])))
    time.sleep(0.4)
L("=== %s completed %d; still waiting on the fixer: %d; other exclusion types: %s" % (time.ctime(), tot, sum(left.values()), dict(other)))
