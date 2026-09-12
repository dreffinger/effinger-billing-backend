# PLAIN ENGLISH (inspector bypass, 9/12 7am ET run): every visit in the Claim Inspector carries only advisories
# (Pattern 20657 timely-filing >12 months = William's standing bypass+submit rule; Pattern 11256 unspecified laterality =
# bypass + log). Bypass them with the ids from the listing made minutes ago, then re-list every batch and report.
# Never touches: charges, dx, balances. Never bypasses a missing-DATA error (anything not 20657/11256 is left alone).
import amd, re, json, time
def bypass(vid, ids):
    return amd.post(amd.msg("bypassclaimedits", "chargeentry", {"nocookie": "1"},
        '<visitlist><visit id="%s"><claimeditlist>%s</claimeditlist></visit></visitlist>' % (vid, "".join('<claimedit id="%s"/>' % e for e in ids))))
s = json.load(open("scan_0912/summary_before.json"))
ALLOW = ("Pattern 20657", "Pattern 11256")
lat = []
for bid, vs in s["inspector"].items():
    for v in vs:
        ids = [e[0] for e in v["errs"] if e[1].startswith(ALLOW)]
        skip = [e for e in v["errs"] if not e[1].startswith(ALLOW)]
        if skip: print("SKIP non-advisory", v["vid"], skip)
        if not ids: continue
        r = bypass(v["vid"], ids)
        print("bypass v%s ids=%s ->" % (v["vid"], ids), "ok" if "Fault" not in r and 'success="1"' in r else re.sub(r"\s+", " ", r[:220]))
        for e in v["errs"]:
            if e[1].startswith("Pattern 11256"): lat.append((v["pid"], v["vid"], e[1][:120]))
        time.sleep(0.4)
if lat:
    with open("laterality_flag_log.md", "a") as f:
        for pid, vid, txt in lat:
            f.write("- 2026-09-12 12:0x UTC (7am ET run): pat%s visit %s - %s -> advisory bypassed, dx left as coded (M75.00 adhesive capsulitis, unspecified shoulder; no laterality correction captured) - William to confirm side.\n" % (pid, vid, txt))
time.sleep(2)
ib = amd.call('action="getclaiminspectorbatches" class="chargeentry" nocookie="1"')
bids = re.findall(r'<batch id="([^"]+)"', ib)
print("AFTER batches:", bids)
left = 0
for bid in bids:
    t = amd.post(amd.msg("getclaiminspectorcharges", "chargeentry", {"batchid": bid, "nocookie": "1"}), timeout=120)
    vs = re.findall(r'<visit id="(\d+)"[^>]*claimstatus="([^"]*)"', t)
    errs = re.findall(r'<error id="(\d+)"[^>]*>([^<]{0,90})', t)
    print("  batch", bid, "visits", vs, "errs", errs[:6]); left += len(vs)
print("INSPECTOR visits left:", left)
