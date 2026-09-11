# PLAIN ENGLISH (Restore hospital admission dates)
# Decides: For hospital (POS 21) visits whose admission date was lost in the frequency reset, puts it back and rebills.
# Rules it uses: Admission date = the most recent 99223 on or before the visit.
# Never touches: Non-hospital visits.
# ---
"""9/4/2026: the freq-1 reset wrote extins WITHOUT hospitalizationfrom, so hospital (POS 21) claims now reject
'PDTP0303 MISSING RELATED ADMISSION DATE'.  For every visit touched (reset_freq_rebill + fix_freq7 + tonight's
exclusions): if any charge is POS 21 / hospital E&M, set hospitalizationfrom = most recent 99223 on/before DOS
(William's rule; fallback = first day of the consecutive hospital-day run; logged), echoing all extins attrs and
resubmissioncode=1, then rebill.  Resumable via fix_admit_dates.log."""
import amd, resave, json, re, time, datetime, collections
import xml.etree.ElementTree as ET
HOSP = re.compile(r"^(9922\d|9923\d|99238|99239|9925\d|9928\d|9929\d|99291|99292)$")
LOG = open("fix_admit_dates.log", "a")
def L(m): print(m, flush=True); LOG.write(m + "\n"); LOG.flush()
def d(s): return datetime.datetime.strptime(s.strip()[:10], "%m/%d/%Y").date()
unp = json.load(open("unpaid_20260903.json")); byv = {r["visitid"]: r for r in unp}
vids = []
for f in ("reset_freq_rebill.log", "fix_freq7.log"):
    for line in open(f):
        m = re.search(r"DONE visit (\d+)", line)
        if m: vids.append(int(m.group(1)))
excl = json.load(open("exclusions_0904.json"))
try: live = json.load(open("excl_admit_live.json"))
except Exception: live = []
for x in live: excl.append({"vid": x["vid"], "pid": x["pid"], "charges": [{"id": x["cid"]}]})
pri = [int(x["vid"]) for x in live]   # currently-excluded visits first
for x in excl: vids.append(int(x["vid"]))
seen = set(); order = [v for v in pri + vids if not (v in seen or seen.add(v))]
done = {int(m.group(1)) for l in open("fix_admit_dates.log") for m in [re.search(r"(?:OK|SKIP|NOHOSP) visit (\d+)", l)] if m}
hist = {}
def history(pid):
    if pid not in hist:
        root = ET.fromstring(amd.post(amd.msg('gettxhistory', 'demographics', {'patientid': str(pid), 'filterhistory': '0', 'pagenumber': '1', 'typefilter': '0', 'sortbypayment': 'false', 'groupbyvisit': '0', 'sortdescending': '1', 'visitid': '0', 'profileid': '', 'getmemo': 'false', 'nocookie': '1'}), timeout=120))
        hist[pid] = [(d(c.get("dos")), c.get("proccode")) for c in root.iter("charge") if c.get("void") != "1" and not (c.get("fee") or "").startswith("-") and c.get("dos")]
    return hist[pid]
def admit_for(pid, dos):
    h = history(pid)
    adm = [x for x, p in h if p == "99223" and x <= dos]
    if adm: return max(adm), "99223"
    days = sorted({x for x, p in h if HOSP.match(p or "") and x <= dos})
    cur = dos
    while (cur - datetime.timedelta(days=1)) in days: cur -= datetime.timedelta(days=1)
    return cur, "run-start"
L("=== fix_admit_dates %s: %d visits, %d done ===" % (time.ctime(), len(order), len(done)))
stats = collections.Counter()
for vid in order:
    if vid in done: continue
    r = byv.get(vid); cid = r["chargedetailids"].split(",")[0] if r else ([x["charges"][0]["id"] for x in excl if int(x["vid"]) == vid] or [None])[0]
    if not cid: L("SKIP visit %s: no charge id" % vid); continue
    try:
        x = resave.detail(cid); root = ET.fromstring(x); vis = root.find(".//visit"); pat = root.find(".//patient")
        charges = [c for c in root.iter("charge") if c.get("void") != "1"]
        # need ALL charges of the visit for proccodes/pos
        vis2, pat2, allc = resave.visit_charges(cid)
        hosp = [c for c in allc if c.get("pos") == "21" or HOSP.match((c.get("proccode") or ""))]
        if not hosp: L("NOHOSP visit %s" % vid); stats["nohosp"] += 1; continue
        e = vis2.find("extins"); cur = (e.get("hospitalizationfrom") if e is not None else None) or ""
        pid = re.sub(r"\D", "", pat2.get("id")); dos = d(hosp[0].get("begindate"))
        adm, how = admit_for(pid, dos)
        base = dict(e.attrib) if e is not None else {}
        base.pop("id", None)
        base.update({"hospitalizationfrom": adm.strftime("%m/%d/%Y"), "resubmissioncode": "1", "origrefnum": ""})
        for k, v in {"patsignature": "1", "emergency": "0", "epsdt": "0", "payprov": "1", "employment": "0", "autoaccident": "0", "otheraccident": "0", "pregnant": "0", "outsidelab": "0"}.items(): base.setdefault(k, v)
        ok = True
        base = resave.clean_extins(base)
        for pc in sorted({c.get("proccode") for c in allc}):
            base["txtChargeCode"] = pc
            rr = amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": str(vid), "nocookie": "1"}, "<extins %s/>" % " ".join('%s="%s"' % (k, v) for k, v in base.items())))
            if "Fault" in rr: ok = False; L("ERR visit %s extins: %s" % (vid, re.sub(r"\s+", " ", rr[100:300]))); break
        if not ok: stats["err"] += 1; continue
        seq = (vis2.get("insorder") or "1").split(",")[0]
        code, _ = amd.rebill_charge(allc[0].get("id"), seq)
        L("OK visit %s %s dos %s admit %s (%s) was '%s' rebill %s" % (vid, pat2.get("name"), dos, adm, how, cur, code)); stats["ok"] += 1
    except Exception as e:
        L("ERR visit %s: %s" % (vid, str(e)[:150])); stats["err"] += 1; time.sleep(3)
    time.sleep(0.3)
L("=== done %s %s" % (time.ctime(), dict(stats)))
