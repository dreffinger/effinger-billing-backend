# PLAIN ENGLISH (chart plan check, 5 PM ET 10/9/2026 run 2026-10-09T2110Z): READ-ONLY.
# Decides: nothing. For each chart id on the command line it reads the demographic record (amdw.plans) and prints how many
#   insurance plans the chart carries and their carrier codes + sequence - so the run can tell whether William (or a facesheet)
#   has added insurance to the Unbilled charts since the last run. No AMD write of any kind. Chart ids only, no names.
import amdw, sys, json, amd
amd.login_cached()
for pid in sys.argv[1:]:
    try:
        p = amdw.plans(pid)[0]
        print(pid, "plans:", len(p), [(x.get("carriercode") or x.get("carrier"), x.get("seq"), x.get("end")) for x in p])
    except Exception as e:
        print(pid, "ERROR", repr(e)[:200])
