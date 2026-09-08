# PLAIN ENGLISH (Rebill a patient's last 12 months)
# Decides: Which of a patient's visits in the last N days are unpaid with a balance, and re-sends each under a given plan order.
# Rules it uses: Frequency-1 reset first; skips paid visits and zero balances. The order can depend on date of service (e.g. Humana before 12/1, Medicare after).
# Never touches: Visits older than the window.
# ---
"""Rebill every unpaid visit of a patient in the last 12 months under a corrected insurance order:
freq-1 extins (echo, keeps admission date) + move_to_ins (whole visit, sets insorder, rebills).
Usage: python3 rebill_patient_year.py <patientid> <insorder e.g. 4,3> [--days 365] [--dry]"""
import amd, resave, txh, move_to_ins, re, sys, time, datetime
def run(pid, order, days=365, dry=False):
    root = txh.fetch(pid); cutoff = datetime.date.today() - datetime.timedelta(days=days)
    byv = {}
    for c in root.iter("charge"):
        a = c.attrib
        if a.get("void") == "1" or (a.get("fee") or "").startswith("-") or not a.get("dos"): continue
        d = datetime.datetime.strptime(a["dos"], "%m/%d/%Y").date()
        if d < cutoff: continue
        paid = any(p.get("void") != "1" and float(p.get("amount") or 0) != 0 for p in c.iter("payment"))
        byv.setdefault(a.get("visit"), {"cid": a.get("id"), "dos": d, "paid": False})
        byv[a.get("visit")]["paid"] |= paid
    out = []
    for vid, v in sorted(byv.items(), key=lambda kv: kv[1]["dos"]):
        x = resave.detail(v["cid"]); m = re.search(r'<charge [^>]*>', x); bal = float(re.search(r'insbalance="([^"]*)"', m.group(0)).group(1)) + float(re.search(r'patbalance="([^"]*)"', m.group(0)).group(1))
        if bal <= 0 or v["paid"]:
            out.append("skip %s %s bal %.2f paid %s" % (vid, v["dos"], bal, v["paid"])); continue
        if dry: out.append("DRY %s %s bal %.2f" % (vid, v["dos"], bal)); continue
        vis, pat, allc = resave.visit_charges(v["cid"]); e = vis.find("extins"); base = dict(e.attrib) if e is not None else {}; base.pop("id", None)
        base.update({"resubmissioncode": "1", "origrefnum": ""})
        for k, val in {"patsignature": "1", "emergency": "0", "epsdt": "0", "payprov": "1", "employment": "0", "autoaccident": "0", "otheraccident": "0", "pregnant": "0", "outsidelab": "0"}.items(): base.setdefault(k, val)
        base = resave.clean_extins(base)
        base = resave.clean_extins(base)
        for pc in sorted({c.get("proccode") for c in allc}):
            base["txtChargeCode"] = pc; amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": str(vid), "nocookie": "1"}, "<extins %s/>" % " ".join('%s="%s"' % (k, val) for k, val in base.items())))
        o = order(v["dos"]) if callable(order) else order; out.append("%s %s bal %.2f -> %s" % (vid, v["dos"], bal, move_to_ins.move(v["cid"], o))); time.sleep(0.5)
    return out
if __name__ == "__main__":
    a = sys.argv; days = int(a[a.index("--days") + 1]) if "--days" in a else 365
    for line in run(a[1], a[2], days, "--dry" in a): print(line)
