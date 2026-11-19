# PLAIN ENGLISH (read-only): list every open Exclusions row the way the 11/11 run learned to - getclaimexclusionclaimruns (William's own
# EFFINGER-user claim runs included) then getclaimexclusioncharges per run with exclusions. Writes registers/excl_list_<stamp>.json. No AMD write.
import re, json, sys, time, amd
STAMP = "2026-11-19T1240Z"; amd.login_cached()
def post(msg, tries=2):
    for i in range(tries):
        try: return amd.post(msg, timeout=150)
        except Exception as e:
            print("  read error", repr(e)[:120], "- one more read" if i + 1 < tries else "- giving up"); time.sleep(20)
    return ""
x = post(amd.msg("getclaimexclusionclaimruns", "claimsreports", {"nocookie": "1"}))
res = re.search(r'<Results[^>]*>', x); print("Results:", res.group(0)[:300] if res else x[:300])
runs = [dict(re.findall(r'(\w+)="([^"]*)"', m)) for m in re.findall(r'<claimrun [^>]*/?>', x)]
runs = [r for r in runs if int(r.get("claimcount") or r.get("exclusioncount") or 0) > 0] if runs and ("claimcount" in runs[0] or "exclusioncount" in runs[0]) else runs
print("runs with exclusions:", [(r.get("id"), r.get("claimcount") or r.get("exclusioncount"), r.get("user") or r.get("username", "")) for r in runs][:40])
out = {"stamp": STAMP, "runs": runs, "rows": []}
for r in runs:
    rid = r.get("id")
    y = post(amd.msg("getclaimexclusioncharges", "claimsreports", {"claimrunid": rid, "clearinghouse": "1", "payer": "1", "nocookie": "1"}))
    for m in re.finditer(r'<visit [^>]*>(.*?)</visit>', y, re.S):
        a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(0).split(">")[0] + ">"))
        errs = re.findall(r'<error[^>]*(?:text|description)="([^"]*)"', m.group(1)) or re.findall(r'<[^>]*text="([^"]*)"', m.group(1))
        row = {"run": rid, "visit": a.get("id"), "claimid": a.get("claimid"), "pid": a.get("patientid"), "carrier": a.get("carriercode"), "dos": a.get("dos") or a.get("dateofservice"), "amount": a.get("amount") or a.get("totalamount"), "errors": errs[:4]}
        out["rows"].append(row); print(" ", rid, row["visit"], row["claimid"], "pat" + str(row["pid"]), row["carrier"], row["dos"], row["amount"], "|", " || ".join(errs)[:200])
    if not out["rows"] or out["rows"][-1]["run"] != rid: print("  run", rid, ": no rows listed (len %d)" % len(y))
json.dump(out, open("registers/excl_list_%s.json" % STAMP, "w"), indent=1)
print("rows total:", len(out["rows"]))
