# PLAIN ENGLISH (3 PM ET 10/2 run): bypass the two NEW Pattern 11256 unspecified-laterality advisories (billing advisories, never missing data)
# on batch 127860 and log them to laterality_flag_log.md for William; then re-list the batch to confirm it cleared. Never touches: dx, charges, other batches.
import amd, re, time, sys
amd.login_cached()
STAMP = "2026-10-02T1910Z"
todo = [("19456746", "395568", "17477843", "H91.90 (unspecified hearing loss)"), ("19456751", "395569", "17477851", "M25.569 (pain in unspecified knee)")]
log = open("laterality_flag_log.md", "a")
for vid, err, pid, dx in todo:
    r = amd.post(amd.msg("bypassclaimedits", "chargeentry", {"nocookie": "1"}, '<visitlist><visit id="%s"><claimeditlist><claimedit id="%s"/></claimeditlist></visit></visitlist>' % (vid, err)))
    ok = "Fault" not in r
    print("bypass", vid, err, "ok" if ok else r[:300])
    if ok:
        log.write("- %s run %s: pat%s visit %s - Pattern 11256 %s bypassed as advisory; documentation may support a laterality code (William)\n" % (time.strftime("%Y-%m-%d %H:%MZ", time.gmtime()), STAMP, pid, vid, dx))
    time.sleep(0.5)
log.close()
r = amd.call('action="getclaiminspectorcharges" class="chargeentry" batchid="127860" nocookie="1"')
print("batch 127860 after:", re.findall(r'<visit [^>]*id="(\d+)"[^>]*claimstatus="(\w+)"', r)[:10], "| errors:", len(re.findall(r'<claimedit ', r)))
