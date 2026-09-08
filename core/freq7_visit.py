# PLAIN ENGLISH (Corrected-claim resend with the payer's original claim number)
# Decides: Nothing on its own. Re-sends one visit to one insurance sequence as a CORRECTED claim (frequency 7) carrying the payer's original claim number (ICN), which is what a payer needs to link the resend to the claim it already has.
# Rules it uses: Same extra-info echo as freq1_visit (keeps the admission date), but sets resubmissioncode=7 and origrefnum=<ICN>. Use only when the payer has already adjudicated the claim (Stedi claim status returned a payer claim number); otherwise use freq1_visit.
# Never touches: Balances, payments, other visits.
# ---
"""Usage: python3 freq7_visit.py <visitid> <chargeid> <seq> <payer claim number>"""
import amd, resave, sys, time
def run(vid, cid, seq, icn):
    vis, pat, allc = resave.visit_charges(cid); e = vis.find("extins"); base = dict(e.attrib) if e is not None else {}; base.pop("id", None)
    base.update({"resubmissioncode": "7", "origrefnum": icn})
    for k, val in {"patsignature": "1", "emergency": "0", "epsdt": "0", "payprov": "1", "employment": "0", "autoaccident": "0", "otheraccident": "0", "pregnant": "0", "outsidelab": "0"}.items(): base.setdefault(k, val)
    base = resave.clean_extins(base)
    for pc in sorted({c.get("proccode") for c in allc}):
        base["txtChargeCode"] = pc
        r = amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": str(vid), "nocookie": "1"}, "<extins %s/>" % " ".join('%s="%s"' % (k, val) for k, val in base.items())))
        if "Fault" in r: return "FAULT extins " + r[:200]
    time.sleep(0.5)
    code, _ = amd.rebill_charge(cid, int(seq)); return "freq7 icn %s + rebill seq %s -> %s" % (icn, seq, code)
if __name__ == "__main__":
    amd.login_cached(); print(run(*sys.argv[1:5]))
