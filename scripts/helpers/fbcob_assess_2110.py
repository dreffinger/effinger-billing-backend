# PLAIN ENGLISH (Florida Blue secondary COB assessment, 5pm ET 9/23/2026 run 2026-09-23T2110Z): the 1910Z run found Florida Blue 835s
#   2609231016 / 2609230762 answered CO-252 / MA04 'secondary needs the primary EOB' on 26 visits of 5 charts (Medigap secondaries sent
#   without Medicare's adjudication). This script READS each visit live (gettxhistory once per chart, payreasons.visit_state) and reports:
#   the charges' carrier / balances, every live payment with its check number and reason codes (code-less = the hand-post that broke the
#   secondary claim), so the repair (payreasons repost) and the secondary resend can be decided per visit.
# Never touches: AMD writes.
import txh, payreasons, json, time, sys
STAMP = "2026-09-23T2110Z"
G = {"17473086": ["19409354", "19420961", "19420894", "19417565"], "17476090": ["19438064"],
     "17472195": ["19433890", "19433413", "19430677", "19427221", "19421063", "19442312", "19420521"],
     "24937": ["19411042", "19409957", "19409908", "19409861", "19409816", "19409815"],
     "17469028": ["19408122", "19409414", "19422340", "19423587", "19427201", "19440438", "19442293"]}
out = {}
for pid, vids in G.items():
    root = txh.fetch(pid); time.sleep(0.3)
    for vid in vids:
        st = payreasons.visit_state(pid, vid, root)
        cl = payreasons.codeless(st)
        out.setdefault(pid, {})[vid] = {"charges": st, "codeless": [(c["cid"], p["id"], p["amount"], p["checkno"], p["carrier"]) for c, p in cl], "balanced": payreasons.balanced(st)}
        for c in st:
            print("pat%s v%s c%s %s %s fee %.2f paid %.2f insbal %.2f patbal %.2f carrier %s | pays %s | wos %s" % (
                pid, vid, c["cid"], c["cpt"], c["dos"], c["fee"], c["paid"], c["insbalance"], c["patbalance"], c["carrier"],
                [(p["carrier"], p["amount"], p["checkno"], p["date"], "VOID" if p["void"] == "1" else "", p["reasons"]) for p in c["pays"]],
                [(w["code"], w["amount"], "VOID" if w["void"] == "1" else "") for w in c["wos"]]))
        print("   codeless:", out[pid][vid]["codeless"], "balanced:", out[pid][vid]["balanced"])
json.dump(out, open("registers/fbcob_assess_%s.json" % STAMP, "w"), indent=1, default=str)
