# PLAIN ENGLISH (Clear 01/01/1900 dates)
# Decides: Finds claim fields set to 01/01/1900 on visits touched today and clears them.
# Rules it uses: Resumable.
# Never touches: Real dates.
# ---
"""Scan visits touched today for 01/01/1900 claim-field dates and clear them (omit the attrs on updextrainsinfo).
Resumable via clean_1900.log."""
import amd, resave, json, re, time
LOG = open("clean_1900.log", "a")
def L(m): print(m, flush=True); LOG.write(m + "\n"); LOG.flush()
unp = json.load(open("unpaid_20260903.json")); byv = {r["visitid"]: r["chargedetailids"].split(",")[0] for r in unp}
vids = []
for f, pat in (("fix_admit_dates.log", r"OK visit (\d+)"), ("batch_refresh.log", r"visit (\d+) "), ("wrongpayer_rebill.log", r"visit (\d+) "), ("reset_freq_rebill.log", r"DONE visit (\d+)"), ("fix_freq7.log", r"DONE visit (\d+)")):
    for line in open(f):
        m = re.search(pat, line)
        if m: vids.append(int(m.group(1)))
try:
    for x in json.load(open("excl_admit_live.json")): vids.append(int(x["vid"]))
except Exception: pass
seen = set(); order = [v for v in vids if not (v in seen or seen.add(v))]
done = {int(m.group(1)) for l in open("clean_1900.log") for m in [re.search(r"(?:CLEAN|OK|SKIP) visit (\d+)", l)] if m}
L("=== clean_1900 %s: %d visits, %d done" % (time.ctime(), len(order), len(done)))
for vid in order:
    if vid in done: continue
    cid = byv.get(vid)
    try:
        if not cid:
            L("SKIP visit %s no charge" % vid); continue
        x = resave.detail(cid); e = re.search(r'<extins[^>]*/?>', x)
        if not e or "1900" not in e.group(0):
            L("OK visit %s" % vid); continue
        vis, pat, allc = resave.visit_charges(cid); ex = vis.find("extins"); base = dict(ex.attrib) if ex is not None else {}; base.pop("id", None)
        base = resave.clean_extins(base); base.setdefault("resubmissioncode", "1"); base["origrefnum"] = ""
        for pc in sorted({c.get("proccode") for c in allc}):
            base["txtChargeCode"] = pc
            r = amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": str(vid), "nocookie": "1"}, "<extins %s/>" % " ".join('%s="%s"' % (k, v) for k, v in base.items())))
            if "Fault" in r: raise RuntimeError(re.sub(r"\s+", " ", r[100:260]))
        time.sleep(0.6); x2 = resave.detail(cid); e2 = re.search(r'<extins[^>]*/?>', x2).group(0)
        seq = (vis.get("insorder") or "1").split(",")[0]; code, _ = amd.rebill_charge(allc[0].get("id"), seq)
        L("CLEAN visit %s -> %s rebill %s" % (vid, "still 1900!" if "1900" in e2 else "cleared", code))
    except Exception as ex_:
        L("ERR visit %s: %s" % (vid, str(ex_)[:120])); time.sleep(2)
    time.sleep(0.2)
L("=== done %s" % time.ctime())
