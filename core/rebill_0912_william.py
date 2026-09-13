# PLAIN ENGLISH (freq-1 rebills William asked for on 9/12: all AET12, Allen's 9/4 stay with the new VA auth, Lepore on HIG06)
# Decides: which open insurance lines still need to go out, then resets each visit to an original claim and rebills its plan sequence.
# Rules it uses: skip any visit already billed today (a parallel copy may have sent it); skip visits with a posted payment;
#   Allen: rebill only visits whose referral plan now carries the 12-byte auth William supplied (VA9011001288).
# Never touches: balances, plans, codes; the Working Denials charts.
import amd, txh, resave, freq1_visit, json, re, sys, time, collections
import xml.etree.ElementTree as ET
DRY = "--dry" in sys.argv
TODAY = time.strftime("%m/%d/%Y")
LOG = open("rebill_0912_william.log", "a")
def L(m): print(m, flush=True); LOG.write("%s %s\n" % (time.strftime("%H:%M:%S"), m)); LOG.flush()
amd.login_cached()
out = collections.defaultdict(list)

def plans(pid):
    root = ET.fromstring(amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"}), timeout=60))
    return [(i.get("id"), i.get("carrier"), i.get("sequence"), i.get("enddate")) for i in root.iter("insplan")], {r.get("id"): r.get("preauth") for r in root.iter("refplan")}

def open_visits(pid, carrier):
    vs = {}
    for c in txh.fetch(pid).iter("charge"):
        a = c.attrib
        if a.get("void") == "1" or a.get("carrier") != carrier or float(a.get("insbal") or 0) <= 0: continue
        paid = any(p.get("void") != "1" and float(p.get("amount") or 0) != 0 and p.get("carrier") == carrier for p in c.iter("payment"))  # only THIS carrier's payment settles the line; a primary's payment is expected on a secondary rebill
        vs.setdefault(a.get("visit"), []).append({"cid": a.get("id"), "dos": a.get("dos"), "bal": float(a.get("insbal")), "billdate": a.get("billdate") or "", "paid": paid})
    return vs

def rebill(pid, vid, lines, seq, tag):
    if any(x["billdate"] == TODAY for x in lines): L("  skip v%s already billed today" % vid); out[tag + "_skipped_today"].append(vid); return
    if any(x["paid"] for x in lines): L("  skip v%s has a posted payment" % vid); out[tag + "_skipped_paid"].append(vid); return
    amt = sum(x["bal"] for x in lines)
    if DRY: L("  DRY v%s seq %s $%.2f %s" % (vid, seq, amt, lines[0]["dos"])); out[tag + "_dry"].append(vid); return
    r = freq1_visit.run(vid, lines[0]["cid"], seq); L("  v%s %s $%.2f seq %s -> %s" % (vid, lines[0]["dos"], amt, seq, r))
    (out[tag + "_sent"] if "204" in r else out[tag + "_failed"]).append((vid, amt, r[:80])); time.sleep(0.4)

what = [a for a in sys.argv[1:] if not a.startswith("--")]
if "aet12" in what:
    aet = ['12233544', '17473520', '17475139', '17474208', '17476909', '17473853', '17471138', '17476419', '17473362', '17473442', '17475771', '17476506', '17476533', '17476788', '17473518']
    for pid in aet:
        pl, _ = plans(pid); seq = [p[2] for p in pl if p[1] == "car42009" and not p[3]] or [p[2] for p in pl if p[1] == "car42009"]
        if not seq: L("%s: no AET12 plan" % pid); continue
        vs = open_visits(pid, "AET12"); L("AET12 %s: %d open visits, seq %s" % (pid, len(vs), seq[0]))
        for vid, lines in vs.items(): rebill(pid, vid, lines, seq[0], "aet12")
if "allen" in what:
    pid = "17475970"; pl, ref = plans(pid); seq = [p[2] for p in pl if p[1] == "car42025"][0]
    vs = open_visits(pid, "VACCN"); L("Allen: %d open VACCN visits, refplans %s" % (len(vs), ref))
    for vid, lines in vs.items():
        det = ET.fromstring(resave.detail(re.sub(r"\D", "", lines[0]["cid"]))); vis = det.find(".//visit")
        rp = vis.get("refplan"); auth = ref.get(rp, ""); L("  v%s %s refplan %s auth %s" % (vid, lines[0]["dos"], rp, auth))
        if auth == "VA9011001288": rebill(pid, vid, lines, seq, "allen")
        else: out["allen_held"].append((vid, lines[0]["dos"], rp, auth))
if "lepore" in what:
    pid = "17476115"; pl, _ = plans(pid); seq = [p[2] for p in pl if p[1] == "car307793"][0]
    vs = open_visits(pid, "HIG06"); L("Lepore: %d open HIG06 visits, seq %s" % (len(vs), seq))
    for vid, lines in vs.items():
        det = ET.fromstring(resave.detail(re.sub(r"\D", "", lines[0]["cid"]))); vis = det.find(".//visit")
        L("  v%s insorder=%s" % (vid, vis.get("insorder")))
        if (vis.get("insorder") or "").split(",")[0] == seq: rebill(pid, vid, lines, seq, "lepore")
        else: out["lepore_held"].append((vid, vis.get("insorder")))
json.dump(out, open("rebill_0912_william_%s.json" % time.strftime("%H%M"), "w"), indent=1)
L("=== %s ===" % json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in out.items()}))
