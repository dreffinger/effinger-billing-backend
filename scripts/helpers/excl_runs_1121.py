# PLAIN ENGLISH (read only, 12:40Z 11/21 run): lists every claim run getclaimexclusionclaimruns returns and the exclusion
# visits on each (getclaimexclusioncharges clearinghouse=1 payer=1) - the engine's scan reads getclaimrunstatus and can miss
# William's own (EFFINGER-user) claim runs. Prints run, visit, carrier, error text. Writes nothing to AMD.
import amd, re
amd.login_cached()
r = amd.post(amd.msg("getclaimexclusionclaimruns", "claimsreports", {"nocookie": "1"}))
runs = sorted(set(re.findall(r'<claimrun [^>]*\bid="(\d+)"', r)) | set(re.findall(r'claimrunid="(\d+)"', r)))
print("runs:", runs, "| raw head:", r[:300].replace("\n", " "))
for run in runs:
    x = amd.post(amd.msg("getclaimexclusioncharges", "claimsreports", {"claimrunid": run, "clearinghouse": "1", "payer": "1", "nocookie": "1"}), timeout=120)
    for m in re.finditer(r'<visit [^>]*>.*?</visit>', x, re.S):
        a = dict(re.findall(r'(\w+)="([^"]*)"', re.match(r'<visit [^>]*>', m.group(0)).group(0)))
        errs = re.findall(r'<(?:error|exclusion)[^>]*(?:message|name|text|description)="([^"]*)"', m.group(0))
        print(run, a.get("id"), a.get("patientid"), a.get("carriercode"), a.get("dos", ""), a.get("totalfee", a.get("fee", "")), "|", "; ".join(errs)[:300])
