# PLAIN ENGLISH (supplement-residual write-offs, 9/12 7am ET run): William's board answers 09:16-09:18 UTC -
#   pemberly-norcott "+ write off the supplement residuals", whitfield-rowan "write off the supplement residuals",
#   penhale-rupert "write off as no secondary". For each of their excluded visits: WOINS the open insurance balance on the
#   dead supplement (UNI20 / HUM01) with a dated note, end-date that plan the day before the first denied DOS, complete the
#   exclusion rows. Register written to registers/Writeoff_register_2026-09-12_7amET.csv.
# Never touches: Medicare-side balances, other patients, paid lines.
import amd, txh, manual_post, ins_update, re, time, json, csv, collections
LOG = open("wo_1112_supplements.log", "a")
def L(m): print(m, flush=True); LOG.write(m + "\n"); LOG.flush()
PLAN = {"17473020": ("UNI20", "ins9512551", "03/10/2025", "UNI20 supplement residual - subscriber not found, patient deceased Nov 2025; William 9/12 board pemberly-norcott: write off"),
        "17473232": ("UNI20", "ins9512833", "04/27/2025", "UNI20 supplement residual - subscriber not found, patient deceased Jun 2026; William 9/12 board whitfield-rowan: write off"),
        "17471681": ("HUM01", "ins9511163", "12/03/2024", "HUM01 secondary inactive / entity not found - no secondary exists; William 9/12 board penhale-rupert: write off as no secondary")}
s = json.load(open("scan_0912/summary_before.json"))
rows = [(rid, r) for rid, rs in s["exclusions"].items() for r in rs if r["patientid"] in PLAN]
amd.login_cached(); reg = []; done = collections.defaultdict(list); total = 0.0
for pid, (car, insid, endd, note) in PLAN.items():
    root = txh.fetch(pid); myrows = [(rid, r) for rid, r in rows if r["patientid"] == pid]
    vids = {r["id"] for _, r in myrows}; L("== pat%s %s rows %d visits %s" % (pid, car, len(myrows), sorted(vids)))
    ok_v = set()
    for c in root.iter("charge"):
        a = c.attrib
        if a.get("void") == "1" or a.get("visit") not in vids: continue
        ib = float(a.get("insbal") or 0)
        if ib <= 0: ok_v.add(a.get("visit")); continue
        if a.get("carrier") != car: L("  SKIP c%s carrier %s != %s" % (a.get("id"), a.get("carrier"), car)); continue
        okp, msg = manual_post.post(a.get("id"), car, 0.0, ib, "WOINS", "", None, note)
        L("  c%s %s %s ins %.2f -> WOINS %s %s" % (a.get("id"), a.get("proccode"), a.get("dos"), ib, okp, str(msg)[:80]))
        if okp: reg.append(("2026-09-12", "pat" + pid, car, a.get("dos"), a.get("proccode"), "%.2f" % ib, "WOINS", note)); total += ib; ok_v.add(a.get("visit"))
        time.sleep(0.4)
    r2 = txh.fetch(pid); left = {v: 0.0 for v in vids}
    for c in r2.iter("charge"):
        if c.get("void") != "1" and c.get("visit") in vids: left[c.get("visit")] += float(c.get("insbal") or 0) + float(c.get("patbal") or 0)
    L("  balances after: %s" % left)
    for rid, r in myrows:
        if abs(left.get(r["id"], 1)) < 0.005: done[rid].append((r["id"], r["claimid"]))
    okE, m = ins_update.update(pid, insid, enddate=endd); L("  end-date %s %s -> %s %s" % (insid, endd, okE, m[:80]))
    time.sleep(0.4)
for rid, lst in done.items():
    x = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": rid, "hide": "-1", "nocookie": "1"}, "<visitlist>%s</visitlist>" % "".join('<visit id="%s" claimid="%s"/>' % (v, c) for v, c in lst)))
    L("hideexclusions %s x%d -> %s" % (rid, len(lst), "ok" if "Fault" not in x else re.sub(r"\s+", " ", x[:200]))); time.sleep(0.4)
import os; os.makedirs("registers", exist_ok=True)
with open("registers/Writeoff_register_2026-09-12_7amET.csv", "a", newline="") as f:
    w = csv.writer(f); w.writerow(["date", "patient", "carrier", "dos", "cpt", "amount", "code", "note"]); w.writerows(reg)
L("TOTAL written off %.2f on %d charges; exclusions completed %d" % (total, len(reg), sum(len(v) for v in done.values())))
json.dump({"total": total, "n": len(reg), "done": done}, open("wo_1112_results.json", "w"))
