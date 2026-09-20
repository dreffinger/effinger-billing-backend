# PLAIN ENGLISH (Unbilled 'prior payor' fix + release, 5am ET 9/20/2026 run 2026-09-20T0910Z)
# Decides: two kinds of 'A payment from the prior payor is required' rows.
#  (1) RE-CREATED MEDICAID VISITS (the 9/10 Garland-G->Effinger profile swap re-created 19 Jan-Feb 2026 SNF visits as new visit ids;
#      charge carrier blank, never billed, insbilled 0): their visit insorder still reads the chart default (Medicare first), so
#      every chargerebill on Medicaid's sequence queued a SECONDARY claim that AMD holds for the primary's payment - releasing them
#      (9/11, 9/16, 9/17, 9/20 0510Z) never sent them. Fix = the skill's 'bill a non-primary plan without reordering' rule:
#      full-visit resave with insorder = Medicaid's OWN sequence (move_to_ins.move, car6113 plan, never insorder[0]), then
#      freq1_visit.run on that sequence (resubmissioncode 1, chargerebill 204), then release.
#  (2) WAITING ON THE PRIMARY (primary billed 9/5-9/13, $0 or no answer yet; the secondary is queued): William's 9/8 rule - release
#      (they re-queue on their own when the primary posts). v19441047 (pat17470743 MCAD $16.93, primary reversed 5/26) stays held.
# Register: registers/unbilled_fix_2026-09-20T0910Z.json. Never touches: 'Payment reason codes' rows (9/15 rule), payments, plans.
import amd, resave, move_to_ins, freq1_visit, json, re, sys, time
DRY = "--dry" in sys.argv
S = "2026-09-20T0910Z"
CAR = json.load(open("carriers.json")); MCAD = CAR["MCAD"]
amd.login_cached()
rows = json.load(open("registers/unbilled_prior_%s.json" % S))
HOLD = {"19441047"}
def L(m): print(m, flush=True)
reg = {"stamp": S, "fixed": [], "released": [], "held": [], "errors": []}
byv = {}
for o in rows: byv.setdefault(o["visit"], []).append(o)
_pc = {}
def medicaid_seq(pid):
    if pid in _pc: return _pc[pid]
    t = amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"}), timeout=60)
    act = []
    for m in re.finditer(r'<insplan [^>]*>', t):
        a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(0)))
        if a.get("carrier") == MCAD: act.append((a.get("sequence"), a.get("enddate") or ""))
    seq = None
    for s, e in act:
        if not e: seq = s; break
    if seq is None and act: seq = act[0][0]
    _pc[pid] = seq; return seq
recreated = [v for v, cs in byv.items() if all((c.get("carrier") or "") == "" and not (c.get("datebilled") or c.get("billdate")) for c in cs) and v not in HOLD]
waiting = [v for v in byv if v not in recreated and v not in HOLD]
L("recreated %d waiting %d held %d" % (len(recreated), len(waiting), len(HOLD)))
for v in recreated:
    cs = byv[v]; pid = cs[0]["patientid"]; cid = cs[0]["id"]
    seq = medicaid_seq(pid)
    rec = {"vid": v, "pid": pid, "cid": cid, "mcad_seq": seq, "insbal": sum(float(c.get("insbal") or 0) for c in cs)}
    if not seq:
        rec["why"] = "no Medicaid (car6113) plan on the chart - not rebilled"; reg["errors"].append(rec); L("NO MCAD v%s pat%s" % (v, pid)); continue
    d = resave.detail(cid); vis = re.search(r'<visit [^>]*>', d).group(0)
    rec["insorder_before"] = re.search(r'insorder="([^"]*)"', vis).group(1)
    if DRY:
        rec["dry"] = "would set insorder=%s and freq1 rebill seq %s" % (seq, seq); reg["fixed"].append(rec); L("DRY v%s pat%s %s" % (v, pid, rec["dry"])); continue
    try:
        r1 = move_to_ins.move(cid, seq=seq, rebill_seq=seq); rec["move"] = r1; time.sleep(0.6)
        r2 = freq1_visit.run(v, cid, seq); rec["freq1"] = r2; time.sleep(0.6)
        d2 = resave.detail(cid); rec["insorder_after"] = re.search(r'insorder="([^"]*)"', d2).group(1)
        rec["live_charges"] = len([1 for m in re.finditer(r'<charge [^>]*>', d2) if 'void="1"' not in m.group(0)])
        L("FIXED v%s pat%s order %s -> %s | %s | %s" % (v, pid, rec["insorder_before"], rec["insorder_after"], r1, r2))
        reg["fixed"].append(rec)
    except Exception as e:
        rec["error"] = str(e)[:200]; reg["errors"].append(rec); L("ERR v%s %s" % (v, rec["error"]))
for v in list(HOLD):
    cs = byv.get(v, []); reg["held"].append({"vid": v, "pid": cs[0]["patientid"] if cs else "", "why": "MCAD crossover $16.93 behind a reversed Medicare payment (5/26/2026) - held for the report since 0510Z"})
rel = [v for v in recreated + waiting if not any(e["vid"] == v for e in reg["errors"])]
for i in range(0, len(rel), 10):
    chunk = rel[i:i + 10]
    if DRY: L("DRY release %s" % chunk); continue
    xml = amd.call('action="hideunbillablevisits" class="claimsreports" hide="-1" nocookie="1"', "<visitlist>%s</visitlist>" % "".join('<visit id="%s"/>' % c for c in chunk))
    ok = 'success="1"' in xml or '<Error/>' in xml or '<Error />' in xml
    reg["released"].extend([{"vid": c, "ok": ok} for c in chunk]); L("release %d ok=%s %s" % (len(chunk), ok, re.sub(r"\s+", " ", xml)[:120])); time.sleep(0.6)
json.dump(reg, open("registers/unbilled_fix_%s%s.json" % (S, "_dry" if DRY else ""), "w"), indent=1)
L("=== done: fixed %d released %d held %d errors %d" % (len(reg["fixed"]), len(reg["released"]), len(reg["held"]), len(reg["errors"])))
