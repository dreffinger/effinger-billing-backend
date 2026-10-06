# PLAIN ENGLISH (Frequency-1 reset + rebill)
# Decides: Nothing. Resets one visit to an original claim (frequency 1, no payer reference number), strips 1900 dates, rebills one plan sequence.
# Rules it uses: Every rebill goes out as frequency 1 unless a payer ICN is on file.
# Never touches: Balances, plans, codes. reroute() = the one correct re-route: visit order (no rebill) + ONE freq-1 rebill (10/6/2026).
# ---
"""Reset a single visit to an original claim (freq 1, no ref #), strip 1900 dates, and rebill one sequence.
Usage: freq1_visit.py <visitid> <chargeid> <seq>
       freq1_visit.py reroute <visitid> <chargeid> <order> [<seq>] [--dry]   (visit order, no rebill, then ONE freq-1 rebill; live unless --dry)"""
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
    code, txt = amd.rebill_charge(cid, int(seq), visitid=vid)
    return "freq1 + rebill seq %s -> %s%s" % (seq, code, " (SKIPPED - already rebilled in this run)" if str(txt).startswith("SKIPPED") else "")
def reroute(vid, cid, order, seq=None, dry=False):
    """THE re-route (William 10/6/2026 - one frequency-1 rebill per visit): set the visit insorder by a no-rebill full-visit
    echo (resave.set_insorder), then ONE frequency-1 reset + ONE chargerebill to `seq` (default = the first plan of the new
    order). Never move_to_ins.move(cid, seq) + run(): move rebills on its own, before the reset - two rebills for one visit."""
    seq = int(seq or str(order).split(",")[0])
    ok, msg = resave.set_insorder(cid, order, dry=dry)
    if not ok: return "NOT rebilled - visit order step failed: " + msg
    if dry: return "%s | DRY freq1 + rebill seq %s" % (msg, seq)
    time.sleep(0.5)
    return "%s | %s" % (msg, run(vid, cid, seq))
if __name__ == "__main__":
    amd.login_cached()
    if sys.argv[1] == "reroute":   # freq1_visit.py reroute <visitid> <chargeid> <order> [<seq>] [--dry]   (live unless --dry, like move_to_ins.py)
        rest = [a for a in sys.argv[2:] if not a.startswith("--")]
        print(reroute(rest[0], rest[1], rest[2], rest[3] if len(rest) > 3 else None, dry="--dry" in sys.argv))
    else:
        print(run(sys.argv[1], sys.argv[2], sys.argv[3]))
