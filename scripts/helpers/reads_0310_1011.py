# PLAIN ENGLISH (read-only chart reads, 11 PM ET 10/10 slot = 2026-10-11T0310Z backend billing run)
# Decides: nothing. Reads the charts named in William's three board notes of 02:41-03:16Z (charts 17474493, 12232248,
# 17471172, 21564 and the five 'repair them' charts) plus the ERA Center unposted list, and writes a register.
# Never touches: AMD writes. No patient names are printed or saved (chart / visit / charge ids only).
import json, sys, re, time
import xml.etree.ElementTree as ET
import amd, txh, payreasons, era_post
amd.login_cached()
STAMP = "2026-10-11T0310Z"
out = {"stamp": STAMP, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
def vs(pid, vid):
    return payreasons.visit_state(pid, vid, root=txh.fetch_visit(pid, vid))
def brief(ch):
    return {k: ch[k] for k in ("cid","cpt","dos","fee","paid","insbalance","patbalance","carrier")} | {
        "pays": [(p["carrier"], p["amount"], p["checkno"], p["date"], p["void"], len(p["reasons"])) for p in ch["pays"]],
        "wos": [(w["code"], w["amount"], w["date"], w["void"]) for w in ch["wos"]]}
# 1. chart 17474493 (card C 10/6, William 'go' 03:16Z)
out["c17474493"] = {v: [brief(c) for c in vs("17474493", v)] for v in ("19456837","19456905","19456976","19456833")}
print("17474493:", json.dumps(out["c17474493"]))
# 2. chart 12232248 (card B 10/6 + watch united-12232248-2025, William 'go to UHC' 02:42Z)
tfw = json.load(open("registers/tf_writeoff_watch.json"))
items = tfw.get("items", tfw) if isinstance(tfw, dict) else tfw
watch = [i for i in items if i.get("id") == "united-12232248-2025"][0]
out["c12232248"] = {}
for v in watch["visits"]:
    out["c12232248"][v["vid"]] = {"watch_outcome": v.get("outcome"), "dos": v.get("dos"), "live": [brief(c) for c in vs("12232248", v["vid"])]}
print("12232248:", json.dumps(out["c12232248"]))
# 3. chart 17471172: the 1/31/2024 99497 line + chart plans
root = txh.fetch("17471172")
th = []
for c in root.iter("charge"):
    if c.get("void") == "1": continue
    if c.get("proccode") == "99497" and c.get("dos","").startswith("01/31/2024"):
        th.append({k: c.get(k) for k in ("id","visit","proccode","dos","fee","paid","insbal","patbal","carrier","billdate","insorder") if c.get(k) is not None})
        th[-1]["attrs"] = sorted(c.keys())
out["thurlow_0131"] = th; print("thurlow 1/31/2024 99497:", json.dumps(th))
def plans(pid):
    r = amd.post(amd.msg("getdemographic", "demographics", {"patientid": str(pid), "nocookie": "1"}), timeout=120)
    rt = ET.fromstring(r.encode("latin-1", "ignore")) if isinstance(r, str) else ET.fromstring(r)
    res = []
    for p in rt.iter("insplan"):
        res.append({k: p.get(k) for k in p.keys() if not re.search(r"(?i)subscriber|name|ssn|dob|birth|address|phone", k)})
    pat = next(rt.iter("patient"), None)
    order = pat.get("insorder") if pat is not None else None
    return {"patient_insorder": order, "plans": res}
out["plans_17471172"] = plans("17471172"); print("plans 17471172:", json.dumps(out["plans_17471172"]))
# 4. chart 21564 (deceased [DOB]): any charge after death?
root = txh.fetch("21564")
late = [{k: c.get(k) for k in ("id","visit","proccode","dos","fee","insbal","patbal","carrier","billdate")} for c in root.iter("charge")
        if c.get("void") != "1" and c.get("dos") and time.strptime(c.get("dos")[:10], "%m/%d/%Y") > time.strptime("08/05/2026", "%m/%d/%Y")]
out["inchbold_after_death"] = late; print("21564 charges after 8/5/2026:", json.dumps(late))
# 5. 'repair them' scope: Medicare payments posted with no reason codes / no write-off and an open insurance balance
scope = {}
for pid in ("12232001","17471688","17471172","21564","17476855"):
    root = txh.fetch(pid); rows = []
    for c in root.iter("charge"):
        if c.get("void") == "1": continue
        chs = payreasons.visit_state(pid, c.get("visit"), root=root)
        ch = next((x for x in chs if x["cid"] == payreasons.num(c.get("id"))), None)
        if not ch: continue
        live_pays = [p for p in ch["pays"] if p["void"] != "1"]
        live_wos = [w for w in ch["wos"] if w["void"] != "1"]
        mcr = [p for p in live_pays if p["carrier"] in ("FLO02","") or "MEDICARE" in p["carrier"].upper()]
        if mcr and (ch["insbalance"] > 0 or ch["patbalance"] > 0) and (not live_wos or any(not p["reasons"] for p in live_pays)):
            rows.append(brief(ch) | {"vid": c.get("visit"), "billdate": c.get("billdate"), "codeless": [p["id"] for p in live_pays if not p["reasons"]]})
    scope[pid] = rows; print("repair scope", pid, len(rows), "lines", round(sum(r["insbalance"]+r["patbalance"] for r in rows),2))
out["repair_scope"] = scope
# 6. ERA Center unposted list
chk = era_post.checks()
out["era_checks"] = [{k: c.get(k) for k in c.keys() if not re.search(r"(?i)patient|name", k)} for c in chk]
print("ERA unposted:", len(chk), "checks", [(c.get("id"), c.get("eracarriername") or c.get("carriername"), c.get("checkamount") or c.get("amount"), c.get("checkdate") or c.get("date")) for c in chk])
json.dump(out, open("registers/reads_%s.json" % STAMP, "w"), indent=1)
print("saved registers/reads_%s.json" % STAMP)
