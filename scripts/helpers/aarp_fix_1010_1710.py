# PLAIN ENGLISH (AARP Medigap filed under UNI20 - carrier fix + one rebill per visit + exclusion complete; 1 PM ET 10/10/2026 slot,
#   run 2026-10-10T1710Z). Claim run 1700286 rejected two Medicare-SECONDARY 99233 claims (claim letter B) on chart 17474911 -
#   v19456254 (9/24/2026, charge 23367878) and v19456271 (9/23/2026, charge 23367895), $21.80 Medicare coinsurance each - with
#   'SUBSCRIBER AND SUBSCRIBER ID NOT FOUND' + 'PA MEMBER PICK REJECT' from UNITED HEALTHCARE (carrier UNI20, CPID 3429 = UHC commercial/MA).
# Decides: nothing new - it applies the fix proven 9/22/2026 (pat17471365) and 10/6/2026 (claim 19455208B): the chart's seq-2 plan
#   (ins9516404, member id on file) is an AARP MEDICARE SUPPLEMENT PLAN F - AMD's own 271 on it names 'AARP SUPPLEMENTAL PLANS INS BY
#   UNITEDHEALTHCARE' and Stedi payer 36273 answers Active Coverage, planBegin 20260101 - so it belongs on carrier AAR01 (car6600,
#   AARP Medigap), not UNI20. Steps, in order: (1) ins_update.update(pid, insid, carrier="car6600") = updateinsurance with AMD's
#   original-value echo (the chart's patient insurance order is re-read and restored by the helper if the edit wipes it);
#   (2) per visit ONE re-route = freq1_visit.reroute(vid, cid, "1,2", 2): no-rebill full-visit echo setting the visit order
#   Medicare first / Medigap second, then ONE frequency-1 reset + ONE chargerebill at sequence 2 (William 10/6: one rebill per visit;
#   the visit is a secondary that the payer never adjudicated - frequency 1 is right); (3) hideexclusions on claim run 1700286 for the
#   two rejected claims (19456254B, 19456271B) once both rebills answered 204 (step 4 rule: complete every exclusion whose visit was
#   re-sent this run). The Medicare primary payments (check 819948282, 10/9/2026) are never touched. No group number is written.
# Rules it uses: lookup order (patient_db -> AMD 271 -> Stedi) done before this script; ONE REBILL PER VISIT; no group numbers;
#   writes only through the named helpers ins_update / freq1_visit / amd.post(hideexclusions) with --dry first.
# Never touches: payments, write-offs, balances, the Medicare plan, any other chart or visit, the UNI20 plan's dates or member id.
# Usage: cd /home/claude/unbilled && python3 aarp_fix_1010_1710.py [--live]      (default = dry run, nothing written)
# Register: registers/aarp_fix_2026-10-10T1710Z[_dry].json
import sys, json, time, re
import amd, ins_update, freq1_visit
LIVE = "--live" in sys.argv
S = "2026-10-10T1710Z"
PID = "17474911"; INSID = "9516404"; NEWCAR = "car6600"; OLDCAR = "car6404"
VISITS = [("19456254", "23367878", "19456254B"), ("19456271", "23367895", "19456271B")]
RUN = "1700286"
REG = "registers/aarp_fix_%s%s.json" % (S, "" if LIVE else "_dry")
rec = {"stamp": S, "live": LIVE, "pid": PID, "insid": INSID, "carrier_from": OLDCAR, "carrier_to": NEWCAR, "steps": []}
def L(m): print(m, flush=True); rec["steps"].append(m)
amd.login_cached()
_, plans, order = ins_update._plans(PID)
summ = [(k, v.get("carrier"), v.get("sequence"), v.get("enddate")) for k, v in plans.items()]
L("chart %s plans before: %s | patient insorder %r" % (PID, summ, order))
cur = plans.get("ins" + INSID)
if not cur:
    L("ABORT - plan ins%s not on the chart" % INSID); json.dump(rec, open(REG, "w"), indent=1); sys.exit(2)
if cur.get("carrier") == NEWCAR:
    L("plan ins%s already carries %s - carrier step skipped" % (INSID, NEWCAR)); carrier_ok = True
elif cur.get("carrier") != OLDCAR:
    L("ABORT - plan ins%s carries %s, expected %s" % (INSID, cur.get("carrier"), OLDCAR)); json.dump(rec, open(REG, "w"), indent=1); sys.exit(2)
elif LIVE:
    ok, msg = ins_update.update(PID, INSID, carrier=NEWCAR)
    L("updateinsurance carrier -> %s: ok=%s %s" % (NEWCAR, ok, msg))
    carrier_ok = ok
    time.sleep(0.5)
    _, plans2, order2 = ins_update._plans(PID)
    L("chart plans after: %s | patient insorder %r" % ([(k, v.get("carrier"), v.get("sequence")) for k, v in plans2.items()], order2))
    carrier_ok = carrier_ok and plans2.get("ins" + INSID, {}).get("carrier") == NEWCAR
else:
    L("DRY updateinsurance ins%s carrier %s -> %s (original-value echo)" % (INSID, OLDCAR, NEWCAR)); carrier_ok = True
if not carrier_ok:
    L("STOP - carrier not changed, nothing rebilled"); json.dump(rec, open(REG, "w"), indent=1); sys.exit(1)
rebilled = []
for vid, cid, claim in VISITS:
    r = freq1_visit.reroute(vid, cid, "1,2", 2, dry=not LIVE)
    L("visit %s charge %s reroute 1,2 seq 2 -> %s" % (vid, cid, r))
    if LIVE and ("204" in str(r) or "SKIPPED - already rebilled" in str(r)): rebilled.append((vid, claim))
    time.sleep(0.5)
if LIVE and rebilled:
    child = "<visitlist>" + "".join('<visit id="%s" claimid="%s"/>' % (v, c) for v, c in rebilled) + "</visitlist>"
    rr = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": RUN, "hide": "-1", "nocookie": "1"}, child), timeout=120)
    ok = "Fault" not in rr and 'success="1"' in rr
    L("hideexclusions run %s %s -> %s %s" % (RUN, [c for _, c in rebilled], "OK" if ok else "NOT OK", re.sub(r"\s+", " ", rr[100:300])))
elif not LIVE:
    L("DRY hideexclusions run %s for %s after the rebills" % (RUN, [c for _, _, c in VISITS]))
json.dump(rec, open(REG, "w"), indent=1)
print("register", REG)
