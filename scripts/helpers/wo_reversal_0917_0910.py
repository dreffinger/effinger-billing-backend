# PLAIN ENGLISH (write-off reversal for ERA check 1051693, 5am ET 9/17/2026 run - ehpa cloud run 2026-09-17T0910Z)
# Decides: for every line of check 1051693 (FLO02 819803392) that era_clear held as 'unrecorded payment (reversal pipeline)' -
#   a remit that PAYS a visit our 9/7-9/10 write-offs had zeroed (a $0 FLO02 denial posted with a full WOINS write-off, now
#   re-adjudicated and paid by Florida Blue) - voids the write-offs so the balance returns to insurance, then posts the
#   check for exactly those visits with era_post.post_check + era_post.FORCE_VISITS (the remit's stored insurancebalance is
#   0, so postable() would otherwise skip them - the 9/10 lesson in captured_calls.md).
# Rules it uses: only visits with no non-void payment > $0 and an ERA paid line > 0 (era_clear's recorded() gate already
#   selected them); voids logged with write-off ids in Writeoff_reversal_register_<date>.csv; --dry lists and touches nothing.
# Never touches: visits with a real payment, write-offs on visits the remit did not pay, any other check.
import amd, era_post, void_tx, json, sys, time, datetime
CHECK = "1051693"; dry = "--dry" in sys.argv
stamp = datetime.date.today().strftime("%Y%m%d")
recs = [r for r in json.load(open("era_clear_reversal_%s.json" % stamp)) if str(r.get("checkid")) == CHECK]
LOG = open("wo_reversal_post.log", "a"); REG = open("Writeoff_reversal_register_%s.csv" % stamp, "a")
def L(m): print(m, flush=True); LOG.write(m + "\n"); LOG.flush()
done = set()
try: done = set(l.split()[1] for l in open("wo_reversal_post.log") if l.startswith("VOIDED "))
except Exception: pass
amd.login_cached()
voided_visits = set(); tot_void = 0.0
for r in recs:
    key = str(r["visitid"])
    if key in done: voided_visits.add(int(r["visitid"])); continue
    if dry: L("DRY pat%s %s v%s era %.2f wos %s" % (r["patientid"], r["dos"], r["visitid"], r["era_pay"], [(w[2], w[3], w[4]) for w in r["writeoffs"]])); continue
    ok_all = True
    for chg, woid, code, amt, date in r["writeoffs"]:
        ok, msg = void_tx.void_writeoff(r["patientid"], chg, woid); ok_all &= ok
        REG.write("%s,%s,pat%s,%s,%s,%s,%s,%s,%s\n" % (stamp, r["check"], r["patientid"], r["dos"], chg, woid, code, amt, "voided" if ok else "FAILED " + msg[:60])); REG.flush()
        if not ok: L("  void FAIL pat%s %s wo %s: %s" % (r["patientid"], r["dos"], woid, msg))
        else: tot_void += abs(float(amt or 0))
        time.sleep(0.3)
    L("VOIDED %s pat%s %s era %.2f wos %d ok=%s" % (key, r["patientid"], r["dos"], r["era_pay"], len(r["writeoffs"]), ok_all))
    if ok_all: voided_visits.add(int(r["visitid"]))
L("write-offs voided this run $%.2f on %d visits (%s)" % (tot_void, len(voided_visits), "dry" if dry else "live"))
if not dry and voided_visits:
    chk = next((c for c in era_post.checks() if str(c["id"]) == CHECK), None)
    if not chk: L("check %s no longer on the unposted list - nothing posted" % CHECK)
    else:
        era_post.FORCE_VISITS.clear(); era_post.FORCE_VISITS.update(voided_visits)
        L("FORCE_VISITS %s" % sorted(era_post.FORCE_VISITS))
        try:
            nv, amt = era_post.post_check(chk); L("POSTED check %s %s: %d visits $%.2f" % (CHECK, chk["paymentnumber"], nv, amt))
        except Exception as e: L("POST ERROR check %s: %s" % (CHECK, str(e)[:200]))
        era_post.FORCE_VISITS.clear()
