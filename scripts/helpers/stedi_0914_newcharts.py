# PLAIN ENGLISH (insurance cascade step 3-5 for the new HCA charts with no plan, 9/14/2026 0420UTC run)
# Decides: nothing in AMD. Runs the Stedi Medicare MBI lookup (name + DOB + state) for each chart id given on the
#   command line, then insurance discovery when the MBI lookup finds nothing; saves raw answers under patient_db/<pid>/
#   and prints a one-line summary per chart (MBI, Part A/B, MA plan + COB dates, Part D, QMB, death).
# Never touches: AMD writes, keys (the proxy adds the Stedi credential).
"""Usage: python3 stedi_0914_newcharts.py <pid>=<LAST>,<FIRST>,<yyyymmdd>,<ST>[,<dos yyyymmdd>] ..."""
import stedi, json, sys, os, time
for arg in sys.argv[1:]:
    pid, rest = arg.split("=", 1); last, first, dob, st = rest.split(",")[:4]
    dos = rest.split(",")[4] if len(rest.split(",")) > 4 else "20260911"
    os.makedirs("patient_db/%s" % pid, exist_ok=True)
    try:
        j = stedi.mbi(first, last, dob, st, dos)
        json.dump(j, open("patient_db/%s/stedi_mbi_%s.json" % (pid, dos), "w"), indent=1)
        s = stedi.med_summ(j)
        print("MBI  %s %s,%s %s: %s" % (pid, last, first, dob, s), flush=True)
        found = bool(j.get("subscriber", {}).get("memberId")) and not j.get("errors")
    except Exception as e:
        print("MBI  %s ERR %s" % (pid, str(e)[:200]), flush=True); found = False
    if not found:
        try:
            d = stedi.disc(first, last, dob, st, dos)
            json.dump(d, open("patient_db/%s/stedi_disc_%s.json" % (pid, dos), "w"), indent=1)
            print("DISC %s: %s" % (pid, stedi.disc_summ(d)), flush=True)
        except Exception as e:
            print("DISC %s ERR %s" % (pid, str(e)[:200]), flush=True)
    time.sleep(0.5)
