# PLAIN ENGLISH (Frequency-1 reset + rebill)
# Decides: Nothing. Resets one visit to an original claim (frequency 1, no payer reference number), strips 1900 dates, rebills one plan sequence.
# Rules it uses: Every rebill goes out as frequency 1 unless a payer ICN is on file.
# Never touches: Balances, plans, codes.
# ---
"""Reset a single visit to an original claim (freq 1, no ref #), strip 1900 dates, and rebill one sequence.
Usage: freq1_visit.py <visitid> <chargeid> <seq>"""
import amd, resave, sys, time
def run(vid, cid, seq):
    vis, pat, allc = resave.visit_charges(cid); e = vis.find("extins"); base = dict(e.attrib) if e is not None else {}; base.pop("id", None)
    base.update({"resubmissioncode": "1", "origrefnum": ""})
    for k, val in {"patsignature": "1", "emergency": "0", "epsdt": "0", "payprov": "1", "employment": "0", "autoaccident": "0", "otheraccident": "0", "pregnant": "0", "outsidelab": "0"}.items(): base.setdefault(k, val)
    base = resave.clean_extins(base)
    for pc in sorted({c.get("proccode") for c in allc}):
        base["txtChargeCode"] = pc
        r = amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": str(vid), "nocookie": "1"}, "<extins %s/>" % " ".join('%s="%s"' % (k, val) for k, val in base.items())))
        if "Fault" in r: return "FAULT extins " + r[:200]
    time.sleep(0.5)
    code, _ = amd.rebill_charge(cid, int(seq)); return "freq1 + rebill seq %s -> %s" % (seq, code)
if __name__ == "__main__":
    amd.login_cached(); print(run(sys.argv[1], sys.argv[2], sys.argv[3]))
