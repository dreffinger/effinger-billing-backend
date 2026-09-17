# PLAIN ENGLISH (Reverse write-offs and post the payer's money)
# Decides: For every visit in wo_reversal_<date>.json - a remit that PAID a visit whose charges were instead written off (the 5/31/2026 WOINSBANK bulk write-off and similar) - voids the write-offs so the balance returns to insurance, then posts the ERA check so the payment lands.
# Rules it uses: Only visits with no payment ever posted and a remit line > $0. Voids are logged with the write-off ids so they can be traced. Posting is era_post.post_check on the same check afterwards (it only posts visits with an open balance).
# Never touches: Visits that already have a payment, write-offs on visits the remit did not pay, or any check not in the scan file.
# ---
"""Usage: python3 wo_reversal_post.py [--max N] [--dry]"""
import amd, era_post, void_tx, json, sys, time, datetime, collections, glob
amd.login_cached(); stamp = datetime.date.today().strftime('%Y%m%d')
recs = json.load(open(sorted(glob.glob('wo_reversal_*.json'))[-1])); mx = int(sys.argv[sys.argv.index('--max') + 1]) if '--max' in sys.argv else 10**9; dry = '--dry' in sys.argv
LOG = open('wo_reversal_post.log', 'a'); REG = open('Writeoff_reversal_register_%s.csv' % stamp, 'a')
def L(m): print(m, flush=True); LOG.write(m + '\n'); LOG.flush()
done = set(l.split()[1] for l in open('wo_reversal_post.log') if l.startswith('VOIDED ')) if glob.glob('wo_reversal_post.log') else set()
bych = collections.defaultdict(list)
for r in recs: bych[r['checkid']].append(r)
n = 0; tot_void = 0.0; posted_total = 0.0
for cid, rs in sorted(bych.items(), key=lambda kv: -sum(r['era_pay'] for r in kv[1])):
    if n >= mx: break
    touched = 0
    for r in rs:
        key = '%s' % r['visitid']
        if key in done: continue
        if dry: L('DRY %s %s %s era %.2f wos %s' % (r['patient'], r['dos'], r['visitid'], r['era_pay'], [(w[2], w[3]) for w in r['writeoffs']])); continue
        ok_all = True
        for chg, woid, code, amt, date in r['writeoffs']:
            ok, msg = void_tx.void_writeoff(r['patientid'], chg, woid); ok_all &= ok
            REG.write('%s,%s,%s,%s,%s,%s,%s,%s,%s\n' % (stamp, r['check'], r['patient'].replace(',', ' '), r['dos'], chg, woid, code, amt, 'voided' if ok else 'FAILED ' + msg[:60])); REG.flush()
            if not ok: L('  void FAIL %s %s wo %s: %s' % (r['patient'], r['dos'], woid, msg)); time.sleep(0.3)
            else: tot_void += abs(float(amt or 0))
        L('VOIDED %s %s %s era %.2f wos %d ok=%s' % (key, r['patient'], r['dos'], r['era_pay'], len(r['writeoffs']), ok_all)); touched += 1; time.sleep(0.3)
    n += 1
    if touched and not dry:
        chk = next((c for c in era_post.checks() if str(c['id']) == str(cid)), None)
        if chk:
            # 9/10 lesson (captured_calls.md), applied to the helper 9/17: the remit stores each visit's insurancebalance as
            # of load time (0 after the write-off), so postable() skips the just-voided visits unless they are in FORCE_VISITS.
            era_post.FORCE_VISITS.clear(); era_post.FORCE_VISITS.update(int(r['visitid']) for r in rs)
            try: nv, amt = era_post.post_check(chk); posted_total += amt; L('POSTED check %s %s: %d visits $%.2f (FORCE_VISITS %d)' % (cid, chk['paymentnumber'], nv, amt, len(era_post.FORCE_VISITS)))
            except Exception as e: L('POST ERROR check %s: %s' % (cid, str(e)[:120]))
            era_post.FORCE_VISITS.clear()
L('=== done: checks %d, write-offs voided $%.2f, posted $%.2f ===' % (n, tot_void, posted_total))
