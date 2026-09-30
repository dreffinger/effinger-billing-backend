# PLAIN ENGLISH (Admission dates found by the 9/30/2026 hold research - run 2026-09-30T1310Z; MANDATORY APPROVAL ids A-2026-09-30T1310Z-A4 / -A5 / -A6)
# Decides: nothing new - applies the standing rule 'admission = the most recent 99223 on/before the DOS within 45 days' where the research found the
#   anchor the earlier passes missed (their history read used gettxhistory typefilter=1, which hides fully-paid 99223 rows; typefilter=0 shows them):
#   A4 pat17477640 v19456267 (chg 23367891, 99233 09/23/2026) + v19456252 (chg 23367876, 99233 09/24/2026): 99223 chg 23364607 DOS 09/02/2026 -> admission 09/02/2026
#      (the billed 09/03-09/22 visits of the same stay already carry 09/02/2026).
#   A5 pat17472703 v19456270 (chg 23367894, 99233 09/23/2026) + v19456253 (chg 23367877, 99233 09/24/2026): 99223 chg 23364783 DOS 09/05/2026 -> admission 09/05/2026
#      (the billed 09/06-09/22 visits already carry 09/05/2026).
#   A6 pat20863 exclusion v19445850 (chg 23354719, 99232 06/23/2026, FLO99 'PDTP0303 missing related admission date', $14.38 coinsurance): 99223 chg 23354305
#      DOS 06/18/2026 -> admission 06/18/2026; then chargerebill on sequence 2 (FLO99, the carrier the excluded claim was last billed to) and complete the exclusion.
# Writes, per visit: updextrainsinfo hospitalizationfrom ONLY (never hospitalizationto, no blank/1900 date attrs), then for A4/A5 the full-visit resave with onhcfa=1
#   (updvisitwithnewcharges, EVERY live charge echoed - resave.visit_charges; each of these visits has exactly one, the helper aborts if not), re-list the batch and
#   bypass only advisory patterns with fresh ids; for A6 no resave (insorder 1,2 and balances untouched) - readback, amd.rebill_charge(cid, 2) -> 204, hideexclusions.
# Rules it uses: the void trap (full echo), never bypass missing data, deceased guard inside amd.rebill_charge, one AMD login (cached).
# Never touches: the 15 Tillman visits (no anchor - William), payments, write-offs, insurance plans.
#   python3 admits_1310.py          # dry: re-read every anchor and charge live, list what it would write
#   python3 admits_1310.py --live   # apply; register registers/admits_2026-09-30T1310Z.json
import amd, resave, txh, era_post, json, sys, re, time, datetime
LIVE = "--live" in sys.argv; STAMP = "2026-09-30T1310Z"
ADMITS = {  # vid: (pid, cid, cpt, admission date, anchor charge id, mode)
    "19456267": ("17477640", "23367891", "99233", "09/02/2026", "23364607", "inspector"),
    "19456252": ("17477640", "23367876", "99233", "09/02/2026", "23364607", "inspector"),
    "19456270": ("17472703", "23367894", "99233", "09/05/2026", "23364783", "inspector"),
    "19456253": ("17472703", "23367877", "99233", "09/05/2026", "23364783", "inspector"),
    "19445850": ("20863", "23354719", "99232", "06/18/2026", "23354305", "exclusion"),
}
ADVISORY = ("Pattern 23400", "Pattern 4426", "Pattern 4310", "Pattern 4311", "Pattern 35790", "Pattern 24078")
amd.login_cached(); out = []
def anchor_ok(pid, anchor_cid, admit, dos):
    """the 99223 anchor must still be live on the chart with that DOS, within 45 days on/before the DOS (typefilter=0 read)"""
    root = txh.fetch(pid)
    for c in root.iter("charge"):
        if re.sub(r"\D", "", c.get("id") or "") == anchor_cid and c.get("void") != "1" and c.get("proccode") == "99223" and c.get("dos") == admit:
            d1 = datetime.datetime.strptime(admit, "%m/%d/%Y"); d2 = datetime.datetime.strptime(dos, "%m/%d/%Y")
            return 0 <= (d2 - d1).days <= 45
    return False
def set_date(vid, code, admit, extra=None):
    attrs = {"txtChargeCode": code, "hospitalizationfrom": admit, "patsignature": "1", "emergency": "0", "epsdt": "0", "payprov": "1", "employment": "0", "autoaccident": "0", "otheraccident": "0", "pregnant": "0", "outsidelab": "0"}
    attrs.update(extra or {})
    return amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": "vst%s" % vid, "nocookie": "1"}, "<extins %s/>" % " ".join('%s="%s"' % (k, v) for k, v in attrs.items())))
def full_resave(cid, batch, over=None):
    vis, pat, allc = resave.visit_charges(cid); chg = ""
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f] = c.get(f)
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    va = dict(vis.attrib); va["force"] = "1"; va.update(over or {})
    vs = " ".join('%s="%s"' % (k, v) for k, v in va.items())
    r = amd.post(amd.msg("updvisitwithnewcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "batchid": str(batch), "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
        "<visit %s><chargelist>%s</chargelist></visit>" % (vs, chg)))
    time.sleep(0.8); v2, p2, c2 = resave.visit_charges(cid); ex = v2.find("extins")
    return ("FAULT " + re.sub(r"\s+", " ", r[:160])) if "Fault" in r else "saved live=%d/%d onhcfa=%s hospfrom=%s" % (len(c2), len(allc), v2.get("onhcfa"), ex.get("hospitalizationfrom") if ex is not None else None)
batch = era_post.batch() if LIVE else None
for vid, (pid, cid, cpt, admit, anchor, mode) in ADMITS.items():
    rec = {"vid": vid, "pid": pid, "cid": cid, "admit": admit, "mode": mode}
    vis, pat, allc = resave.visit_charges(cid)
    rec["live_charges"] = [(c.get("id"), c.get("proccode")) for c in allc]
    det = resave.detail(cid); ex = re.search(r'<extins [^>]*>', det)
    rec["hospfrom_before"] = (re.search(r'hospitalizationfrom="([^"]*)"', ex.group(0)).group(1) if ex and 'hospitalizationfrom=' in ex.group(0) else "")
    rec["dos"] = dict(re.findall(r'(\w+)="([^"]*)"', re.search(r'<charge [^>]*>', det).group(0))).get("begindate", "")
    rec["anchor_ok"] = anchor_ok(pid, anchor, admit, rec["dos"])
    if len(allc) != 1 or not rec["anchor_ok"]:
        rec["action"] = "HELD: %s" % ("more than one live charge - resave needs a hand check" if len(allc) != 1 else "anchor no longer matches (99223 %s on %s)" % (anchor, admit))
        out.append(rec); print(json.dumps(rec), flush=True); continue
    if not LIVE:
        rec["action"] = "dry: would write hospitalizationfrom=%s%s" % (admit, ", full resave onhcfa=1, re-list + advisory bypass" if mode == "inspector" else ", then rebill seq 2 + hideexclusions")
        out.append(rec); print(json.dumps(rec), flush=True); continue
    if mode == "inspector":
        r = set_date(vid, cpt, admit); rec["updextrainsinfo"] = "ok" if "Fault" not in r else re.sub(r"\s+", " ", r[:160])
        rec["resave"] = full_resave(cid, batch, {"onhcfa": "1"}); time.sleep(0.5)
    else:
        # A6: keep the existing extins values (resubmissioncode 1, origrefnum blank) - only the admission date is added; no resave, no balance touch
        cur = dict(re.findall(r'(\w+)="([^"]*)"', ex.group(0))) if ex else {}
        keep = {k: cur[k] for k in ("resubmissioncode", "origrefnum") if k in cur}
        r = set_date(vid, cpt, admit, keep); rec["updextrainsinfo"] = "ok" if "Fault" not in r else re.sub(r"\s+", " ", r[:160])
        det2 = resave.detail(cid); m2 = re.search(r'hospitalizationfrom="([^"]*)"', det2); rec["hospfrom_after"] = m2.group(1) if m2 else ""
        if rec["hospfrom_after"] == admit:
            rec["rebill"] = str(amd.rebill_charge(cid, 2))[:200]; time.sleep(0.5)
            rs = amd.post(amd.msg("getclaimrunstatus", "claimsreports", {"nocookie": "1"}), timeout=120)
            done = []
            for a in [dict(re.findall(r'(\w+)="([^"]*)"', m)) for m in re.findall(r'<claimrun [^>]*>', rs)]:
                if int(a.get("totalexclusions") or 0) == 0: continue
                x = amd.post(amd.msg("getclaimexclusioncharges", "claimsreports", {"claimrunid": a["id"], "clearinghouse": "1", "payer": "1", "nocookie": "1"}), timeout=120)
                for m in re.findall(r'<visit [^>]*>', x):
                    va = dict(re.findall(r'(\w+)="([^"]*)"', m))
                    if va.get("id") == vid:
                        h = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": a["id"], "hide": "-1", "nocookie": "1"}, '<visitlist><visit id="%s" claimid="%s"/></visitlist>' % (vid, va.get("claimid", ""))))
                        done.append((a["id"], va.get("claimid"), "Fault" not in h))
                time.sleep(0.3)
            rec["hideexclusions"] = done
    rec["action"] = "applied"; out.append(rec); print(json.dumps(rec), flush=True)
if LIVE:
    time.sleep(3); left = []
    ib = amd.call('action="getclaiminspectorbatches" class="chargeentry" nocookie="1"'); bids = re.findall(r'<batch id="([^"]+)"', ib)
    want = {v for v, a in ADMITS.items() if a[5] == "inspector"}
    for bid in bids:
        t = amd.post(amd.msg("getclaiminspectorcharges", "chargeentry", {"batchid": bid, "nocookie": "1"}), timeout=120)
        for v in re.findall(r'<visit id="(\d+)"[^>]*>(.*?)</visit>', t, re.S):
            if v[0] not in want: continue
            errs = re.findall(r'<error id="(\d+)"[^>]*>([^<]{0,90})', v[1])
            adv = [e[0] for e in errs if e[1].startswith(ADVISORY)]
            if adv and len(adv) == len(errs):
                r = amd.post(amd.msg("bypassclaimedits", "chargeentry", {"nocookie": "1"}, '<visitlist><visit id="%s"><claimeditlist>%s</claimeditlist></visit></visitlist>' % (v[0], "".join('<claimedit id="%s"/>' % e for e in adv))))
                left.append((bid, v[0], "bypassed", adv, "Fault" not in r))
            elif errs: left.append((bid, v[0], "left", errs))
    out.append({"inspector_after": left}); print(json.dumps(left))
json.dump({"stamp": STAMP, "live": LIVE, "rows": out}, open("registers/admits_%s%s.json" % (STAMP, "" if LIVE else "_dry"), "w"), indent=1, default=str)
print("SUMMARY", [(r.get("vid"), (r.get("action") or "")[:40]) for r in out if "vid" in r])
