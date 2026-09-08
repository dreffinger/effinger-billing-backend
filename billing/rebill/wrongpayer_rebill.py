# PLAIN ENGLISH (Rebill after a refresh)
# Decides: After a chart's insurance is corrected, which other unpaid visits are still pointed at the ended plan, and re-sends them under the new order.
# Rules it uses: Medicare first if present, else the MA plan; Medicaid/LTC last. Frequency-1 before every rebill.
# Never touches: Paid visits, or visits already on the new plan.
# ---
"""After an insurance refresh: every OTHER unpaid visit of the patient still pointed at the ended plan gets the new
insorder + freq-1 reset + rebill (the freq-1 sweep skipped these as wrong-payer).  Uses the patient's current
active plans: Medicare first if present, else the MA plan (WEL04/HUM MA), then the Medicaid plan."""
import amd, resave, move_to_ins, json, re, time, datetime
CAR = json.load(open("carriers.json")); MC = "car6085"; MCD = {"car42008", "car6113", "car6285", "car6194", "car42019"}; MA = {"car6174"}
pids = {}
for line in open("batch_refresh.log"):
    m = re.match(r"== (\S+) pid (\d+)", line)
    if m: pids[m.group(1)] = int(m.group(2))
pids["ENFINGER,MICHAEL"] = 17471174; pids["PEARSON,PEGGY"] = 17473065; pids["BRINSON,ETTA"] = 17477128
unp = json.load(open("unpaid_20260903.json")); log = open("wrongpayer_rebill.log", "a")
def L(m): print(m, flush=True); log.write(m + "\n"); log.flush()
done = {m.group(1) for l in open("wrongpayer_rebill.log") for m in [re.search(r"OK visit (\d+)", l)] if m}
for key, pid in pids.items():
    r = amd.post('<ppmdmsg action="getdemographic" class="demographics" msgtime="%s" patientid="%s" nocookie="1"/>' % (amd._msgtime(), pid))
    pl = [dict(re.findall(r'(\w+)="([^"]*)"', m)) for m in re.findall(r'<insplan [^>]*>', r)]
    ended = {p["carrier"]: p["enddate"] for p in pl if p.get("enddate")}
    active = [p for p in pl if not p.get("enddate")]
    order = [p["sequence"] for p in active if p["carrier"] == MC] or [p["sequence"] for p in active if p["carrier"] in MA]
    order += [p["sequence"] for p in active if p["carrier"] in MCD]
    if not order: L("%s: no active order" % key); continue
    seq = ",".join(order)
    rows = [x for x in unp if x["patientid"] == pid]
    byv = {}
    for x in rows: byv.setdefault(x["visitid"], x)
    for vid, x in sorted(byv.items(), key=lambda kv: kv[1]["dateofservice"]):
        if str(vid) in done: continue
        car = x["carriercode"].strip(); carid = {v[0]: k for k, v in CAR.items()}.get(car)
        if carid not in ended: continue   # visit already on a live plan
        dos = datetime.datetime.strptime(x["dateofservice"][:10], "%Y-%m-%d")
        if dos <= datetime.datetime.strptime(ended[carid], "%m/%d/%Y"): continue   # before the plan ended -> old payer still right
        cid = x["chargedetailids"].split(",")[0]
        try:
            vis_, pat_, allc_ = resave.visit_charges(cid); e_ = vis_.find("extins"); base_ = resave.clean_extins(dict(e_.attrib) if e_ is not None else {}); base_.pop("id", None)
            base_.update({"resubmissioncode": "1", "origrefnum": ""})
            for k_, v_ in {"patsignature": "1", "emergency": "0", "epsdt": "0", "payprov": "1", "employment": "0", "autoaccident": "0", "otheraccident": "0", "pregnant": "0", "outsidelab": "0"}.items(): base_.setdefault(k_, v_)
            for pc in sorted({c.get("proccode") for c in allc_}):
                base_["txtChargeCode"] = pc
                amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": str(vid), "nocookie": "1"}, "<extins %s/>" % " ".join('%s="%s"' % (k, v) for k, v in base_.items())))
            res = move_to_ins.move(cid, seq)
        except Exception as e: res = "EXC " + str(e)[:100]
        L("%s visit %s %s %s $%.2f -> %s%s" % (key, vid, x["dateofservice"][:10], car, x["insbalance"], "OK " if res.startswith("moved") else "", res)); time.sleep(0.7)
L("=== done %s" % time.ctime())
