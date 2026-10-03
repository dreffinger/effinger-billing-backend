# PLAIN ENGLISH (Claim Inspector, 5 AM ET 10/3 slot, run 2026-10-03T0910Z): the two pat17477774 visits re-routed to UMR this run
#   (v19456273, v19456257) came back in batch 127793 with the advisory 'The Source of Payment you have chosen is not typical for this
#   carrier' - the same UMR (car303242, finclass CC) advisory bypassed on 9/19 (registry line 1243) and on HIG07 for pat17476115. It is a
#   soft edit on the carrier record's payment-source code, not missing data, so it is bypassed with the FRESH error ids read from the
#   batch list this run (ids change on every re-inspection), then the batch is re-listed to confirm the rows are gone.
# Decides: nothing beyond the bypass. --dry (default) only re-lists and prints; --live bypasses.
# Never touches: charges, diagnoses, plans, the other 21 standing holds.
import amd, re, sys, time
def bypass(vid, errids):
    r = amd.post(amd.msg("bypassclaimedits", "chargeentry", {"nocookie": "1"}, '<visitlist><visit id="%s"><claimeditlist>%s</claimeditlist></visit></visitlist>' % (vid, "".join('<claimedit id="%s"/>' % e for e in errids))))
    return "Fault" not in r
LIVE = "--live" in sys.argv; BATCH = "127793"; VISITS = {"19456273": "395582", "19456257": "395583"}
amd.login_cached()
def rows():
    r = amd.call('action="getclaiminspectorcharges" class="chargeentry" batchid="%s" nocookie="1"' % BATCH)
    out = {}
    for m in re.finditer(r'<visit [^>]*id="(?:vst)?(\d+)"[^>]*>(.*?)</visit>', r, re.S):
        errs = re.findall(r'<claimedit [^>]*id="(\d+)"[^>]*(?:number="([^"]*)")?[^>]*text="([^"]*)"', m.group(2)) or re.findall(r'id="(\d+)"[^>]*text="([^"]{0,80})', m.group(2))
        out[m.group(1)] = errs
    return out, r
before, raw = rows()
for v in VISITS: print("before", v, before.get(v, "not listed"))
if not LIVE: print("DRY - no bypass"); sys.exit(0)
for v, eid in VISITS.items():
    live_ids = [e[0] for e in before.get(v, [])]
    ids = live_ids or [eid]
    print("bypass", v, ids, bypass(v, ids)); time.sleep(0.6)
time.sleep(2); after, _ = rows()
for v in VISITS: print("after", v, after.get(v, "not listed (clear)"))
