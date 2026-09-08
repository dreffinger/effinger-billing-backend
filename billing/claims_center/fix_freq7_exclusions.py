# PLAIN ENGLISH (Clear frequency-7 exclusions)
# Decides: Which excluded claims are failing only because of the corrected-claim flag, fixes the flag, rebills, completes the exclusion.
# Rules it uses: Frequency 1 + blank original reference number.
# Never touches: Exclusions with other reasons.
# ---
"""Clear the 9/2 'PREF0201 MISSING ORIGINAL REF NUMBER' / 'PCLM0500 INVALID CLAIM FREQUENCY CODE 7'
exclusions: these visits carry the 6/9/2026 'corrected claim' flag, so every rebill goes out as
frequency 7 without a payer ICN.  Fix per visit: extins resubmissioncode=1 + origrefnum blank
(updextrainsinfo), rebill to the first active insurance sequence, then hide the exclusion.
Resumable via fix_freq7.log.  Skips UNI20/UHCMA visits for PR27 (coverage-terminated) patients.
Usage: python3 fix_freq7_exclusions.py [--dry] [--limit N]"""
import amd, resave, json, re, sys, time, collections
import xml.etree.ElementTree as ET

SKIP_PATIENTS_UNI = {"[name]", "ENDERBY,MICAH", "BRACKLEY,[first]"}   # PR27 list: wait for new insurance
LOG = open("fix_freq7.log", "a")
def L(m): print(m); LOG.write(m + "\n"); LOG.flush()

done = set()
try:
    for line in open("fix_freq7.log"):
        m = re.search(r"DONE visit (\d+)", line)
        if m: done.add(m.group(1))
except FileNotFoundError:
    pass

vis = json.load(open("exclusions_0903.json"))
dry = "--dry" in sys.argv
limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 10**9
L("=== freq7 fix %s: %d visits, %d already done, dry=%s ===" % (time.ctime(), len(vis), len(done), dry))

byrun = collections.defaultdict(list)
n = 0
for v in vis:
    if v["vid"] in done or n >= limit:
        continue
    if v["car"] in ("UNI20", "UHCMA") and v["name"].upper() in SKIP_PATIENTS_UNI:
        L("SKIP visit %s %s %s (PR27 patient - needs new insurance first)" % (v["vid"], v["name"], v["car"])); continue
    try:
        d = resave.detail(v["cid"]); root = ET.fromstring(d)
        vv = root.find(".//visit"); charges = list(root.iter("charge"))
        if vv is None or not charges:
            L("ERR visit %s: no detail" % v["vid"]); continue
        seq = (vv.get("insorder") or "1").split(",")[0]
        if dry:
            L("DRY visit %s %s %s seq %s charges %s" % (v["vid"], v["name"], v["car"], seq, [c.get("id") for c in charges])); n += 1; continue
        ok_all = True
        for c in charges:
            if c.get("void") == "1":
                continue
            ext = ('<extins txtChargeCode="%s" resubmissioncode="1" origrefnum="" patsignature="1" emergency="0" epsdt="0" '
                   'payprov="1" employment="0" autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>') % c.get("proccode")
            r = amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": v["vid"], "nocookie": "1"}, ext))
            if "Fault" in r:
                L("ERR extins visit %s charge %s: %s" % (v["vid"], c.get("id"), re.sub(r"\s+", " ", r[:200]))); ok_all = False; break
            code, txt = amd.rebill_charge(c.get("id"), seq)
            if code != 204:
                L("ERR rebill visit %s charge %s: %s %s" % (v["vid"], c.get("id"), code, txt[:150])); ok_all = False; break
        if ok_all:
            byrun[v["run"]].append(v)
            L("DONE visit %s %s %s seq %s (%d charges)" % (v["vid"], v["name"], v["car"], seq, len(charges)))
            n += 1
    except Exception as e:
        L("ERR visit %s: %s" % (v["vid"], str(e)[:150]))
    time.sleep(0.6)

# hide the exclusions for everything fixed in this pass (per claim run)
for run, items in byrun.items():
    child = "<visitlist>" + "".join('<visit id="%s" claimid="%s"/>' % (x["vid"], x["claimid"]) for x in items) + "</visitlist>"
    r = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": run, "hide": "-1", "nocookie": "1"}, child))
    L("hideexclusions run %s (%d visits) -> %s" % (run, len(items), "OK" if "Fault" not in r else re.sub(r"\s+", " ", r[:200])))
L("=== done: %d fixed this pass ===" % n)
