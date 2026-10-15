# PLAIN ENGLISH (Patient-balance review - the classifier and the "Patient Balances Remaining" page; no AMD calls)
# Decides: for every charge carrying a patient balance, whether the money is RETRIEVABLE by sending it to the right insurance,
#   or a WRITE-OFF, from the live chart read (patbal_scan.py) and William's standing rules:
#   - a dual / Medicaid-family patient is never balance-billed: the cost-sharing is WOCAID2ND (Medicare/MA paid) or WOMCAD;
#     a never-adjudicated line inside 12 months on a dual goes to Medicaid first (retrievable).
#   - a $0 denial that means WRONG PAYER (PR27/26/200/22/24/31/109/49/96/204, CO22/24/109) was auto-transferred to the patient:
#     move it back to insurance and re-route (retrievable inside 12 months of the DOS; WOLATE past it).
#   - any other posted denial with no payment: fix + resubmit inside 12 months, WOLATE past it.
#   - never adjudicated at all: a live plan on the chart at the DOS -> send it (inside 12 months), else WOLATE; no plan at all ->
#     Stedi discovery inside 12 months, else self-pay bad debt.
#   - adjudicated cost-sharing (a real payment, PR1/2/3): a secondary / supplement on the chart -> bill it (retrievable);
#     otherwise it is the patient's: statement, or WOSMBAL when the whole chart's cost-sharing is under $25.
#   - a deceased flag on the chart turns a statement into an estate write-off recommendation; a DOS after a death is a VOID.
# Never touches: AMD.
import json, collections, datetime, html, re, sys
STAMP = "1013"; TODAY = datetime.date(2026, 10, 13); SMALL = 25.0
MEDICAID = {"MCAD", "SUN01", "WEL04", "WEL07", "SIM01", "STA03", "FLO99", "FCC", "GEO05"}
MEDICARE = {"FLO02", "RET01"}
WRONG = {"PR27", "PR26", "PR200", "PR22", "PR24", "PR31", "PI109", "PR109", "PR49", "PR96", "PR204", "CO22", "CO24", "CO109", "CO31", "CO26", "CO27"}
COSTSHARE = {"PR1", "PR2", "PR3"}
scan = json.load(open("patbal_scan_%s.json" % STAMP))["charts"]
rows = json.load(open("mwo_pat_all_20261013.json"))
for x in json.load(open("[name]_[DOB].json"))["chargedetails"]:
    if x["chargedetailid"] not in {r["chargedetailid"] for r in rows}: rows.append(x)
names = {str(r["patientid"]): r.get("patientname", "") for r in rows}
def d8(s):
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", str(s or ""))
    if m: return datetime.date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(s or ""))
    return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None
def money(x): return round(float(x or 0) + 1e-9, 2)
def plan_active(p, dos):
    b, e = d8(p["begin"]), d8(p["end"])
    return (e is None or dos is None or e >= dos) and (b is None or dos is None or b <= dos + datetime.timedelta(days=366))
out = []; per_pid_cs = collections.defaultdict(float)
# first pass: per-patient adjudicated cost-sharing total (the WOSMBAL test is per chart)
for r in rows:
    pid = str(r["patientid"]); ch = scan.get(pid)
    if not ch: continue
    c = next((c for c in ch["charges"] if c["cid"] == "charge" + r["chargedetailid"] or c["cid"] == r["chargedetailid"]), None)
    if c and any(p["amount"] > 0 for p in c["pays"]): per_pid_cs[pid] += c["patbal"]
for r in rows:
    pid = str(r["patientid"]); ch = scan.get(pid)
    rec = {"pid": pid, "patient": names.get(pid, ""), "cid": r["chargedetailid"], "vid": r["visitid"], "dos": r["dateofservice"][:10], "cpt": r["chargecode"].strip(),
           "fee": money(r["totalchargeamount"]), "patbal_list": money(r["patbalance"]), "prov": r["providerprofilecode"].strip()}
    dos = d8(rec["dos"]); age = (TODAY - dos).days if dos else 9999; rec["age"] = age; old = age > 365
    if not ch:
        rec.update(bucket="UNREAD", action="chart not read tonight", retrievable=False, patbal=rec["patbal_list"]); out.append(rec); continue
    c = next((c for c in ch["charges"] if c["cid"] in ("charge" + r["chargedetailid"], r["chargedetailid"])), None)
    if c is None:
        rec.update(bucket="SETTLED", action="no live patient balance on the chart any more", retrievable=False, patbal=0.0); out.append(rec); continue
    rec["patbal"] = money(c["patbal"]); rec["insbal"] = money(c["insbal"]); rec["carrier"] = c["carrier"]; rec["billdate"] = c["billdate"]
    if rec["patbal"] <= 0.004:
        rec.update(bucket="SETTLED", action="patient balance already cleared", retrievable=False); out.append(rec); continue
    plans = ch["plans"]; active = [p for p in plans if plan_active(p, dos)]
    codes = {p["code"] for p in active}
    dual = bool(codes & MEDICAID)
    pos = [p for p in c["pays"] if p["amount"] > 0]; zero = [p for p in c["pays"] if p["amount"] == 0]
    reasons = {x[0] for p in c["pays"] for x in p["reasons"]}
    zero_reasons = {x[0] for p in zero for x in p["reasons"]}
    dec = str(ch.get("deceased", "")) in ("1", "true", "True")
    primary_code = active[0]["code"] if active else ""
    secondaries = [p["code"] for p in active[1:] if p["code"] not in MEDICAID] if active else []
    rec.update(plans=[p["code"] for p in active], dual=dual, deceased=dec, paid=money(sum(p["amount"] for p in pos)), pay_carriers=sorted({p["carrier"] for p in pos}), reasons=sorted(reasons))
    if dual:
        if not pos and not zero and not old and active:
            rec.update(bucket="DUAL-SEND", action="dual, never adjudicated, inside 12 months - send to %s (Medicare first if on the chart), never to the patient" % "/".join(sorted(codes)), retrievable=True)
        elif pos:
            rec.update(bucket="DUAL-WRITEOFF", action="dual: %s paid $%.2f - the cost-sharing is Medicaid's, never the patient's -> WOCAID2ND (after the crossover / $0 statement)" % ("/".join(rec["pay_carriers"]), rec["paid"]), retrievable=False, wocode="WOCAID2ND")
        else:
            rec.update(bucket="DUAL-WRITEOFF", action="dual, no payment on the charge%s - cannot balance-bill a Medicaid patient -> %s" % (" (past 12 months)" if old else "", "WOLATE" if old else "WOMCAD"), retrievable=False, wocode="WOLATE" if old else "WOMCAD")
    elif not pos and (zero_reasons & WRONG):
        rec.update(bucket="WRONG-PAYER" if not old else "WRONG-PAYER-UNTIMELY",
                   action=("wrong-payer denial (%s) auto-transferred to the patient - move back to insurance, Stedi cascade for the real payer, re-route" % "/".join(sorted(zero_reasons & WRONG))) if not old else ("wrong-payer denial (%s) and the DOS is over 12 months - past the real payer's window -> WOLATE" % "/".join(sorted(zero_reasons & WRONG))),
                   retrievable=not old, wocode=None if not old else "WOLATE")
    elif not pos and zero:
        rec.update(bucket="DENIED-FIX" if not old else "DENIED-UNTIMELY",
                   action=("$0 denial (%s) sits on the patient - move back to insurance, fix (dx / modifier / records) and resubmit as an original" % "/".join(sorted(zero_reasons))) if not old else ("$0 denial (%s), over 12 months - WOLATE" % "/".join(sorted(zero_reasons))),
                   retrievable=not old, wocode=None if not old else "WOLATE")
    elif not pos and not zero:
        if active and not old:
            rec.update(bucket="NEVER-SENT-LIVE-PLAN", action="never adjudicated, %s on the chart - move to insurance and send (freq 1)" % "/".join(sorted(codes)), retrievable=True)
        elif active:
            rec.update(bucket="NEVER-SENT-UNTIMELY", action="never adjudicated, over 12 months, %s on the chart - past the window -> WOLATE" % "/".join(sorted(codes)), retrievable=False, wocode="WOLATE")
        elif not old:
            rec.update(bucket="SELF-PAY-DISCOVERY", action="no plan on the chart at the DOS - Stedi insurance discovery ($1.50) before any statement; found -> add plan + send", retrievable=True)
        else:
            rec.update(bucket="SELF-PAY-BAD-DEBT", action="no plan on the chart, over 12 months - self-pay no-pay -> bad-debt write-off", retrievable=False, wocode="WOBADDEBT")
    else:
        cs = bool(reasons & COSTSHARE)
        if secondaries:
            rec.update(bucket="BILL-SECONDARY", action="%s paid; %s on the chart as secondary - bill the secondary / let the crossover run (timely from the primary's remit)" % ("/".join(rec["pay_carriers"]), "/".join(secondaries)), retrievable=True)
        elif dec:
            rec.update(bucket="DECEASED-STATEMENT", action="patient cost-sharing on a deceased chart - estate statement or write-off (William's call)", retrievable=False, wocode="WOBADDEBT")
        elif per_pid_cs[pid] < SMALL:
            rec.update(bucket="SMALL-BALANCE", action="patient cost-sharing, the whole chart's open cost-sharing is $%.2f (< $25) -> WOSMBAL" % per_pid_cs[pid], retrievable=False, wocode="WOSMBAL")
        elif primary_code in MEDICARE and not secondaries:
            rec.update(bucket="STATEMENT-MEDICARE", action="Medicare coinsurance/deductible, no supplement on the chart - run Stedi discovery for a Medigap once per patient; none -> patient statement", retrievable=False)
        else:
            rec.update(bucket="STATEMENT", action="%s copay/coinsurance%s - patient statement" % ("/".join(rec["pay_carriers"]) or "payer", "" if cs else " (no PR reason on the payment: check the posting)"), retrievable=False)
    out.append(rec)
B = collections.OrderedDict()
ORDER = ["WRONG-PAYER", "DENIED-FIX", "NEVER-SENT-LIVE-PLAN", "DUAL-SEND", "BILL-SECONDARY", "SELF-PAY-DISCOVERY",
         "DUAL-WRITEOFF", "WRONG-PAYER-UNTIMELY", "DENIED-UNTIMELY", "NEVER-SENT-UNTIMELY", "SELF-PAY-BAD-DEBT", "SMALL-BALANCE", "DECEASED-STATEMENT", "STATEMENT-MEDICARE", "STATEMENT", "SETTLED", "UNREAD"]
for k in ORDER: B[k] = {"charges": 0, "patients": set(), "patbal": 0.0, "carriers": collections.Counter()}
for r in out:
    b = B[r["bucket"]]; b["charges"] += 1; b["patients"].add(r["pid"]); b["patbal"] += r.get("patbal", 0); b["carriers"][r.get("carrier") or "-"] += 1
for k, b in B.items(): b["patients"] = len(b["patients"]); b["patbal"] = money(b["patbal"]); b["carriers"] = dict(b["carriers"].most_common(6))
json.dump({"stamp": STAMP, "built": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), "summary": B, "rows": out}, open("patbal_review_%s.json" % STAMP, "w"), indent=0)
tot = sum(r.get("patbal", 0) for r in out); ret = sum(r.get("patbal", 0) for r in out if r.get("retrievable")); wo = sum(r.get("patbal", 0) for r in out if r.get("wocode"))
print("charges %d  patient balance $%.2f  retrievable $%.2f  write-off $%.2f  statements $%.2f" % (len(out), tot, ret, wo, tot - ret - wo))
for k, b in B.items():
    if b["charges"]: print("  %-22s %5d charges %4d pts  $%10.2f  %s" % (k, b["charges"], b["patients"], b["patbal"], b["carriers"]))
