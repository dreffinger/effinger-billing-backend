# Rebuild registers/inflated_medicare_lines_2026-10-07T0510Z.json (the 0510Z run's register never reached main or Drive).
# READ-ONLY: per chart, a non-void payment carrying CO45/CO253 reasons, no non-void WOINS on the charge, insbal > 0.
import payreasons, txh, json, sys
SEC = {"A": "17471688", "B": "12232001", "C": "17471172", "D": "21564"}
out = []
for sec, pid in SEC.items():
    root = txh.fetch(pid); n = 0
    vids = sorted({payreasons.num(c.get("visit")) for c in root.iter("charge") if c.get("void") != "1"})
    for vid in vids:
        for ch in payreasons.visit_state(pid, vid, root):
            if ch["insbalance"] <= 0: continue
            if any(w["void"] != "1" and w["code"].strip() == "WOINS" for w in ch["wos"]): continue
            for p in ch["pays"]:
                if p["void"] == "1": continue
                co45 = round(sum(a for c, a in p["reasons"] if c.strip().upper() in ("CO45", "CO-45")), 2)
                co253 = round(sum(a for c, a in p["reasons"] if c.strip().upper() in ("CO253", "CO-253")), 2)
                if co45 + co253 <= 0: continue
                out.append({"sec": sec, "pid": pid, "vid": vid, "cid": ch["cid"], "dos": ch["dos"], "cpt": ch["cpt"], "fee": ch["fee"], "paid": ch["paid"],
                            "insbal": ch["insbalance"], "patbal": ch["patbalance"], "carrier": ch["carrier"], "checkno": p["checkno"], "paydate": p["date"],
                            "co45": co45, "co253": co253}); n += 1
    print("section %s pat%s: %d lines" % (sec, pid, n), flush=True)
json.dump(out, open("registers/inflated_medicare_lines_2026-10-07T0510Z.json", "w"), indent=1)
print("TOTAL", len(out), "lines; open", round(sum(l["insbal"] for l in out), 2), "; CO", round(sum(l["co45"] + l["co253"] for l in out), 2))
