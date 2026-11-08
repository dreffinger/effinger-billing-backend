# PLAIN ENGLISH (Reverse write-offs and post the payer's money)
# Decides: For every visit in wo_reversal_<date>.json - a remit that PAID a visit whose charges were instead written off (the 5/31/2026 WOINSBANK bulk write-off and similar) - voids the write-offs so the balance returns to insurance, then posts the ERA check so the payment lands.
# Rules it uses: Only visits with no payment ever posted and a remit line > $0. Voids are logged with the write-off ids so they can be traced. Posting is era_post.post_check on the same check afterwards (it only posts visits with an open balance).
# Never touches: Visits that already have a payment, write-offs on visits the remit did not pay, or any check not in the scan file.
# ---
"""Usage: python3 wo_reversal_post.py [--file wo_reversal_<stamp>.json] [--max N] [--dry]   (default file: the last wo_reversal_*.json by name)"""
import amd, era_post, void_tx, txh, json, sys, time, datetime, collections, glob
amd.login_cached(); stamp = datetime.datetime.utcnow().strftime('%Y%m%d')   # 11/7/2026: UTC like era_clear and the engine
SRC = sys.argv[sys.argv.index('--file') + 1] if '--file' in sys.argv else sorted(glob.glob('wo_reversal_*.json'))[-1]   # 11/7/2026: the engine names its own file
recs = json.load(open(SRC)); mx = int(sys.argv[sys.argv.index('--max') + 1]) if '--max' in sys.argv else 10**9; dry = '--dry' in sys.argv
LOG = open('wo_reversal_post.log', 'a'); REG = open('Writeoff_reversal_register_%s.csv' % stamp, 'a')
def L(m): print(m, flush=True); LOG.write(m + '\n'); LOG.flush()
done = set(l.split()[1] for l in open('wo_reversal_post.log') if l.startswith('VOIDED ')) if glob.glob('wo_reversal_post.log') else set()
bych = collections.defaultdict(list)
for r in recs: bych[r['checkid']].append(r)
n = 0; tot_void = 0.0; posted_total = 0.0
for cid, rs in sorted(bych.items(), key=lambda kv: -sum(r['era_pay'] for r in kv[1])):
    if n >= mx: break
    touched = 0; touched_visits = []; blocked = 0   # 11/7/2026: a row that could not be voided or was skipped unreadable blocks the forced Post for the whole check (9/21 SWEEP RULE)
    for r in rs:
        key = '%s' % r['visitid']
        if key in done: continue
        if dry: L('DRY %s %s %s era %.2f wos %s' % (r['patient'], r['dos'], r['visitid'], r['era_pay'], [(w[2], w[3]) for w in r['writeoffs']])); continue
        try:   # 11/7/2026: read the visit again right before the void - the rows were built minutes ago and another engine may have posted since
            fresh = [p for ch in txh.fetch_visit(r['patientid'], r['visitid']).iter('charge') if ch.get('void') != '1' for p in ch.iter('payment') if p.get('void') != '1' and float(p.get('amount') or 0) != 0]
        except Exception as e:
            L('SKIP %s history unreadable: %s' % (key, str(e)[:80])); blocked += 1; continue
        if fresh: L('SKIP %s payment present (%s)' % (key, ', '.join(sorted(set((p.get('checknumber') or '?') for p in fresh))[:3]))); continue
        ok_all = True
        for chg, woid, code, amt, date in r['writeoffs']:
            ok, msg = void_tx.void_writeoff(r['patientid'], chg, woid); ok_all &= ok
            REG.write('%s,%s,%s,%s,%s,%s,%s,%s,%s\n' % (stamp, r['check'], r['patient'].replace(',', ' '), r['dos'], chg, woid, code, amt, 'voided' if ok else 'FAILED ' + msg[:60])); REG.flush()
            if not ok: L('  void FAIL %s %s wo %s: %s' % (r['patient'], r['dos'], woid, msg)); time.sleep(0.3)
            else: tot_void += abs(float(amt or 0))
        if ok_all: L('VOIDED %s %s %s era %.2f wos %d ok=True' % (key, r['patient'], r['dos'], r['era_pay'], len(r['writeoffs']))); touched += 1; touched_visits.append(int(r['visitid']))
        else: L('VOIDFAIL %s era %.2f wos %d - not forced, retried by the next era_clear round' % (key, r['era_pay'], len(r['writeoffs']))); blocked += 1   # 11/7/2026: a failed void is no VOIDED (resume) line and no forced Post
        time.sleep(0.3)
    n += 1
    if touched and blocked and not dry:
        L('NOT POSTED check %s - a written-off visit of this check could not be voided or read (SWEEP RULE); the voided visits are open again and the fallback posts their lines ERA-linked' % cid)
    elif touched and not dry:
        chk = next((c for c in era_post.checks() if str(c['id']) == str(cid)), None)   # 9/20: ids come back numeric; str-compare or the post step silently skips
        if chk:
            # The ERA remit stores each visit's insurancebalance as of remit-load time (0, because the
            # WOINSBANK write-off had already zeroed it). post_check's postable() gate needs balance>0, so
            # it skips these even though the void just reopened the real balance. Force the just-voided
            # visits so the payment + contractual adjustment post; then clear the override (proven 9/10).
            era_post.FORCE_VISITS.update(touched_visits)
            try: nv, amt = era_post.post_check(chk); posted_total += amt; L('POSTED check %s %s: %d visits $%.2f' % (cid, chk['paymentnumber'], nv, amt))
            except Exception as e: L('POST ERROR check %s: %s' % (cid, str(e)[:120]))
            finally: era_post.FORCE_VISITS.difference_update(touched_visits)
L('=== done: checks %d, write-offs voided $%.2f, posted $%.2f ===' % (n, tot_void, posted_total))
