# PLAIN ENGLISH (9/7 Unbilled column pass - 160 visits)
# Decides: (1) 135 "payment from the prior payor is required" rows: these appeared because the 9/6 ERA clearing posted the old payer's $0 denials / re-posted 2023-24 payments, and AMD then tried to bill the NEXT plan. The 2023-2024 ones (primary paid years ago, coinsurance left for a secondary that is now 2+ years past filing) are written off as untimely secondary balances (William 9/7 rule: over 12 months = write off). The 2025-2026 ones are Medicare claims sent 9/4-9/5 that Medicare has not answered yet - nothing to bill until the Medicare remit posts, so they are released from the column (they come back on their own if the secondary still needs work). (2) "charges have errors" / "unresolved Claim Inspector" rows: the inspector was cleared earlier today - released. Pope Katharine (2024, Medicare paid twice on two ICNs; AARP secondary 2 years old) - remaining balance written off, released. (3) "Insurance order is missing": Felix -> Medicare only; Jackson -> Medicare then FCC; Tillman and Busby (Pam 9/1) -> FL Medicaid fee-for-service (Stedi 9/7: Full Medicaid active, Sunshine inactive, FCC is LTC-custodial only); Johnson David D (new, no plan on file, nothing on Stedi) -> Insurance Refresh Board.
# Rules it uses: manual_post WOINS with a dated note; full-visit echo for insorder; hideunbillablevisits only after the data is fixed or the row is truly waiting on a payer. Resumable via unbilled_0907.log.
# Never touches: Paid charges, Johnson's visit, anything not on today's list.
# ---
"""Usage: python3 unbilled_0907.py [--dry]"""
import amd, resave, txh, manual_post, json, sys, re, time, os, datetime, collections
amd.login_cached(); dry = "--dry" in sys.argv; today = datetime.date(2026, 9, 7)
S = json.load(open("unbilled_0907_scan.json")); LOGF = "unbilled_0907.log"
done = set(l.split()[1] for l in open(LOGF) if l.startswith(("WO ", "REL ", "ORDER "))) if os.path.exists(LOGF) else set(); LOG = open(LOGF, "a")
def L(m): print(m, flush=True); LOG.write(m + "\n"); LOG.flush()
def set_order(vid, order, cid):
    vis, pat, allc = resave.visit_charges(cid); chg = ''
    for c in allc:
        a = {'id': c.get('id')}
        for f in resave.CHG_FIELDS:
            v = c.get(f)
            if v is not None: a[f] = v
        chg += '<charge %s/>' % ' '.join('%s="%s"' % (k, v) for k, v in a.items())
    va = dict(vis.attrib); va['force'] = '1'; va['insorder'] = order
    r = amd.post(amd.msg('updvisitwithcharges', 'chargeentry', {'patientid': pat.get('id'), 'episodeid': vis.get('episode'), 'approval': '1', 'inspectorenabled': '1', 'getfinancials': '-1', 'customclaimfieldsavailable': '1', 'nocookie': '1'}, '<visit %s><chargelist>%s</chargelist></visit>' % (' '.join('%s="%s"' % (k, v) for k, v in va.items()), chg)))
    return 'ok' if 'Fault' not in r else 'FAULT ' + re.sub(r'\s+', ' ', r[100:260])
def release(vids):
    if not vids: return True
    r = amd.post(amd.msg('hideunbillablevisits', 'claimsreports', {'nocookie': '1', 'hide': '-1'}, '<visitlist>%s</visitlist>' % ''.join('<visit id="%s"/>' % v for v in vids)))
    return 'Fault' not in r
def writeoff(s, note, carrier):
    tot = 0.0
    for c in s["charges"]:
        if c["id"] in done: continue
        x = resave.detail(c["id"]); m = re.search(r'<charge [^>]*>', x).group(0); bal = float(re.search(r'insbalance="([^"]*)"', m).group(1) or 0)
        if bal <= 0: continue
        if dry: L("DRY WO %s %s %s $%.2f" % (c["id"], s["pt"], s["dos"], bal)); tot += bal; continue
        ok, msg = manual_post.post(c["id"], carrier, 0.0, bal, "WOINS", note=note)
        L("%s %s %s %s %s $%.2f %s" % ("WO" if ok else "FAIL", c["id"], s["pt"], carrier, s["dos"], bal, "" if ok else msg[:80])); tot += bal if ok else 0; time.sleep(0.3)
    return tot
def old(s): return (today - datetime.datetime.strptime(s["dos"], "%m/%d/%Y").date()).days > 365
def first_carrier(s):
    fc = (s["insorder"] or "").split(",")[0]; return {p[0]: p[1] for p in s["plans"]}.get(fc, "")
CAR = {"car6085": "FLO02", "car6113": "MCAD", "car6404": "UNI20", "car302853": "UHCMA", "car6872": "TRI00", "car6194": "SUN01", "car42008": "FCC01"}
ORDER = {"20379": "1", "24039": "1,3", "22858": "3", "23161": "3"}   # Felix, Jackson, Tillman, Busby
rel = []; held = []; wo = 0.0; cat = collections.Counter()
for s in S:
    vid = s["vid"]; err = s["err"]; pid = s["pid"]
    if vid in done: continue
    if err.startswith("A payment"):
        if old(s):
            wo += writeoff(s, "untimely - secondary balance over 12 months after the primary paid (9/7 William)", CAR.get(first_carrier(s), "UNI20")); rel.append(vid); cat["old secondary written off"] += 1
        else: rel.append(vid); cat["waiting on Medicare remit (sent 9/4-9/5) - released"] += 1
    elif s["pt"].startswith("POPE"):
        wo += writeoff(s, "untimely - AARP secondary balance over 12 months after Medicare paid (9/7 William)", "FLO02"); rel.append(vid); cat["Pope written off"] += 1
    elif err.startswith(("One or more charges", "Unresolved Claim Inspector")): rel.append(vid); cat["inspector cleared - released"] += 1
    elif err.startswith("Insurance order"):
        if pid not in ORDER: held.append((s["pt"], vid, "no plan on file; nothing on Stedi - board")); cat["held"] += 1; continue
        if dry: L("DRY ORDER %s %s -> %s" % (s["pt"], vid, ORDER[pid])); rel.append(vid); continue
        res = set_order(vid, ORDER[pid], s["charges"][0]["id"]); L("ORDER %s %s %s -> %s %s" % (vid, s["pt"], s["dos"], ORDER[pid], res)); time.sleep(0.5)
        if res == "ok": rel.append(vid); cat["order set - released"] += 1
        else: held.append((s["pt"], vid, res))
    else: held.append((s["pt"], vid, err))
if dry: L("DRY release %d; held %s; wo $%.2f; %s" % (len(rel), held, wo, dict(cat)))
else:
    for i in range(0, len(rel), 40):
        ok = release(rel[i:i + 40]); L("release %d-%d -> %s" % (i, i + len(rel[i:i + 40]), ok))
        if ok:
            for v in rel[i:i + 40]: L("REL %s" % v)
    L("=== done: released %d, written off $%.2f, held %s, %s ===" % (len(rel), wo, held, dict(cat)))
