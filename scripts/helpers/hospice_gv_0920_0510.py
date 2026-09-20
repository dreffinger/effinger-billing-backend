# PLAIN ENGLISH (1am ET 9/20/2026 run, 2026-09-20T0510Z): William's board note 04:54Z on row medicare-hospice-b9-denials-0919 -
#   "modifier and rebill" + the NEW STANDING RULE: a hospice denial (Medicare CO-B9 / PR-B9) = add the GV modifier and rebill the claim,
#   in every billing task and the insurance cascade.
# Decides: reads the 5 CO-B9 lines of the dismissed $0 Medicare check 349974158 (ERA Center entry 1051716: reversedismiss -> checkdetails ->
#   dismiss again, the 9/19 recipe), then for each visit: skip if a non-void payment > 0 is on the charge; add GV (mcode713) to every live
#   charge of the visit (full-visit echo, gv_rebill.add_gv); frequency 1 + chargerebill to the chart's Medicare sequence.
#   Register: registers/hospice_gv_register.json (appended).
# Never touches: visits with a posted payment, any other chart.
import amd, era_post, gv_rebill, freq1_visit, txh, json, re, time, sys, os, requests
DRY = "--dry" in sys.argv
amd.login_cached()
STAMP = "2026-09-20T0510Z"; CID = 1051716
def L(m): print(m, flush=True)
det = era_post.details(CID); vs = det.get("eracheckdetails") or []
if not vs:
    r = requests.get(era_post.API + "/era/checks/dismiss", headers=era_post.H(), params={"DismissedDateBegin": "2026-09-18"}, timeout=60)
    dl = r.json() if r.status_code == 200 else []
    L("dismissed list: HTTP %s %d entries" % (r.status_code, len(dl) if isinstance(dl, list) else -1))
    me = [d for d in dl if str(d.get("id")) == str(CID)] if isinstance(dl, list) else []
    if me:
        body = [{"id": CID, "dismissedat": me[0].get("dismissedat")}]
        r2 = requests.post(era_post.API + "/era/checks/reversedismiss", headers=era_post.H(), data=json.dumps(body), timeout=60)
        L("reversedismiss -> HTTP %s %s" % (r2.status_code, r2.text[:120])); time.sleep(1)
        det = era_post.details(CID); vs = det.get("eracheckdetails") or []
        json.dump(det, open("era_details/%s.json" % CID, "w"))
        r3 = requests.post(era_post.API + "/era/checks/dismiss", headers=era_post.H(), data=json.dumps(str(CID)), timeout=60); L("dismiss again -> HTTP %s %s" % (r3.status_code, r3.text[:80]))
    else: L("check %s not in the dismissed list - cannot read its lines" % CID)
L("lines on 1051716: %d" % len(vs))
reg = json.load(open("registers/hospice_gv_register.json")) if os.path.exists("registers/hospice_gv_register.json") else []
seqcache = {}
def medicare_seq(pid):
    if pid not in seqcache:
        t = amd.post(amd.msg("getdemographic", "demographics", {"patientid": str(pid), "nocookie": "1"}), timeout=120)
        plans = [dict(re.findall(r'(carrier|sequence|enddate)="([^"]*)"', p)) for p in re.findall(r'<insplan [^>]*/?>', t)]
        med = [p for p in plans if p.get("carrier") == "car6085" and not p.get("enddate")]
        seqcache[pid] = (med[0]["sequence"] if med else None, plans)
    return seqcache[pid]
for v in vs:
    vid = str(v.get("visitid")); pid = str(v.get("patientid")); dos = str(v.get("dos"))[:10]
    carcs = sorted({(r.get("reasoncode") or r.get("code") or "") for c in v.get("charges") or [] for r in (c.get("reasons") or c.get("reasonlist") or []) if isinstance(r, dict)})
    rec = {"stamp": STAMP, "checkid": CID, "visitid": vid, "patientid": pid, "dos": dos, "carcs": carcs, "insurancebalance": v.get("insurancebalance"), "steps": []}
    def S(m): rec["steps"].append(m); L("v%s pat%s %s" % (vid, pid, m))
    chs = [c for c in txh.fetch("pat" + pid).iter("charge") if c.get("visit") == vid and c.get("void") != "1" and not (c.get("fee") or "").startswith("-")]
    if not chs: S("no live charge on the visit - skipped"); reg.append(rec); continue
    paid = [(p.get("id"), p.get("amount")) for c in chs for p in c.iter("payment") if p.get("void") != "1" and float(p.get("amount") or 0) != 0]
    if paid: S("payment posted %s - not rebilled (never rebill a paid visit)" % paid); rec["outcome"] = "skip-paid"; reg.append(rec); continue
    seq, plans = medicare_seq(pid)
    S("charges %s; Medicare seq %s; plans %s" % ([(c.get("id"), c.get("proccode"), c.get("insbal"), c.get("modifiers") or c.get("modcodes")) for c in chs], seq, plans))
    if not seq: S("no live Medicare plan on the chart - HOLD"); rec["outcome"] = "hold-no-medicare"; reg.append(rec); continue
    if DRY: rec["outcome"] = "DRY"; reg.append(rec); continue
    g = gv_rebill.add_gv(chs[0].get("id")); S("add GV -> %s" % g)
    if g.startswith("FAULT"): rec["outcome"] = "fault-gv"; reg.append(rec); continue
    time.sleep(0.6)
    f = freq1_visit.run(vid, chs[0].get("id"), seq); S("rebill -> %s" % f)
    rec["outcome"] = "gv-rebilled" if "204" in f else "rebill-" + f[:40]
    reg.append(rec); time.sleep(0.5)
json.dump(reg, open("registers/hospice_gv_register.json", "w"), indent=1)
L("=== hospice GV done: %s" % [(r["visitid"], r.get("outcome")) for r in reg if r.get("stamp") == STAMP])
