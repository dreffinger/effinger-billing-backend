# PLAIN ENGLISH (read-only verification, run 2026-10-16T0310Z): re-reads the two visits co45_settle_1016_0310.py wrote to
# and prints each charge's live insurance / patient balance and its non-void write-offs. Decides nothing, writes nothing.
import amd, payreasons, json
amd.login_cached()
out = []
for pid, vid in [(17472977, 19429034), (21577, 19389388)]:
    for ch in payreasons.visit_state(pid, vid):
        wos = [(w["code"], w["amount"]) for w in ch["wos"] if w["void"] == "0"]
        out.append({"pid": pid, "vid": vid, "cid": ch["cid"], "cpt": ch["cpt"], "dos": ch["dos"], "insbalance": ch["insbalance"], "patbalance": ch["patbalance"], "wos": wos})
        print(pid, vid, ch["cid"], ch["cpt"], ch["dos"], "insbal", ch["insbalance"], "patbal", ch["patbalance"], "live wos", wos)
json.dump(out, open("registers/co45_settle_2026-10-16T0310Z_verify.json", "w"), indent=1)
