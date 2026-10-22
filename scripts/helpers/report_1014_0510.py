# PLAIN ENGLISH (run report builder, 1 AM ET 10/14/2026 run 2026-10-14T0510Z)
# Decides: nothing. Reads the before/after scan summaries, this run's registers and the sweep answers and writes
#   "_run report 10-14 0510.csv" (per column: cleared / remaining with chart id, visit, DOS, carrier, error, action) plus
#   a printed before -> after breakdown. Chart ids and visit ids only (10/6 rule) - no names.
# Never touches: AdvancedMD.
import json, csv, collections, glob, os
S = "scan_2026-10-14T0510Z"
b = json.load(open(S + "/summary_before.json")); a = json.load(open(S + "/summary_after.json"))
def ov(s): return {k: s["overview"].get(k) for k in ("chargereviewcount", "claiminspectorcount", "claiminspectoramount", "unbillablecount", "unbillableamount", "exclusioncount", "exclusionamount")}
print("overview before", ov(b)); print("overview after ", ov(a))
def counts(s):
    return (len(s["chargereview"]), sum(len(v) for v in s["inspector"].values()), len(s["unbilled"]), sum(len(v) for v in s["exclusions"].values()))
print("list counts before (CR/CI/UB/EX):", counts(b)); print("list counts after  (CR/CI/UB/EX):", counts(a))
rows = []
def unb_err(r): return " | ".join(sorted(r["_errs"])) or "(no error text)"
bu = {r["id"]: r for r in b["unbilled"]}; au = {r["id"]: r for r in a["unbilled"]}
print("UNBILLED after by error:")
for k, v in collections.Counter(unb_err(r) for r in a["unbilled"]).most_common(): print("  ", v, k[:100])
for vid, r in bu.items():
    st = "remaining" if vid in au else "cleared"
    amt = sum(float(c["insportion"]) for c in r["_chgs"]); dos = r["_chgs"][0]["dos"].strip() if r["_chgs"] else ""
    err = unb_err(r)
    if "Bill Insurance" in err: act = "billins_1014_0510.py: billins=1 full-visit echo + released (66 visits, 4 charts)"
    elif "outside insurance coverage" in err or r["patientid"] == "48008": act = "approval card A-2026-10-14T0510Z-A/B/C/D/E (cov_1014_0510.py refused by the classifier)"
    elif "Payment reason codes" in err: act = "HELD - code-less MONEY payment (payreasons --list: no-era-line; ERA-linked re-post needs the 835 lines, Medicare 819814877 / UHC / TRICARE checks not in the cache)"
    elif "prior payor" in err: act = "released by AMD itself after the inspector bypass / claim run (rule b)" if st == "cleared" else "unbilled_repair saw 0 prior rows - re-listed next run"
    elif "Claim Inspector" in err: act = "inspector advisories bypassed (insp_bypass_advisories.py) -> row dropped" if st == "cleared" else "standing inspector hold (4852 / 20389 / 24078)"
    elif "Insurance order" in err: act = "chart 17478013 facesheet needed (board row)" if r["patientid"] == "17478013" else "approval card C (chart 48008)"
    else: act = ""
    rows.append(["Unbilled", st, r["patientid"], vid, dos, r.get("carriercode", ""), err[:120], "%.2f" % amt, act])
for vid, r in au.items():
    if vid not in bu:
        rows.append(["Unbilled", "new after", r["patientid"], vid, r["_chgs"][0]["dos"].strip() if r["_chgs"] else "", r.get("carriercode", ""), unb_err(r)[:120], "%.2f" % sum(float(c["insportion"]) for c in r["_chgs"]), "re-listed by AMD after this run's resaves/bypasses"])
bx = {(run, r["claimid"]): r for run, rr in b["exclusions"].items() for r in rr}; ax = {(run, r["claimid"]): r for run, rr in a["exclusions"].items() for r in rr}
print("EXCLUSIONS after by error:")
for k, v in collections.Counter((r["carriercodeshort"], " | ".join(sorted(e["name"][:45] for e in r["_errs"]))) for r in ax.values()).most_common(): print("  ", v, k)
cross = set()
for f in glob.glob("registers/excl_crossover_17002*_2026-10-14T05*Z.json"):
    try:
        d = json.load(open(f)); cross |= {str(x[0]) if isinstance(x, (list, tuple)) else str(x) for x in (d.get("completed") or d.get("hide") or d.get("rows") or [])}
    except Exception: pass
ex14 = json.load(open("registers/excl_1014_0510.json")) if os.path.exists("registers/excl_1014_0510.json") else {"rows": []}
ex14r = {str(x["vid"]): x for x in ex14["rows"]}
for (run, cl), r in bx.items():
    st = "remaining" if (run, cl) in ax else "cleared"
    errs = " | ".join(e["name"][:60] for e in r["_errs"]); amt = sum(float(c["insportion"]) for c in r["_chgs"]); dos = r["_chgs"][0]["dos"].strip()
    vid = r["id"]
    if vid in ex14r: act = "excl_1014_0510.py: %s -> %s" % (ex14r[vid]["action"], ex14r[vid].get("result", "")[:60])
    elif r["carriercodeshort"] == "BCBS" and st == "cleared": act = "completed - Florida Blue Medigap crossover-wait (Medicare paid, balance = coinsurance)"
    elif r["carriercodeshort"] == "BCBS": act = "LEFT - balance is not the coinsurance (Medicare contractual never adjusted) - needs the CO-45 correction pass"
    elif r["carriercodeshort"] == "AAR01": act = "AARP member id AAA 72 on AMD's 271 - board row hic[member id] on William's turn (card)"
    elif r["carriercodeshort"] == "AET12": act = "AET12 carrier-master hold (TIN as payer id)"
    else: act = ""
    rows.append(["Exclusions", st, r["patientid"], vid + " " + cl, dos, r["carriercodeshort"], errs[:120], "%.2f" % amt, act + (" [run %s]" % run)])
for (run, cl), r in ax.items():
    if (run, cl) not in bx: rows.append(["Exclusions", "new after", r["patientid"], r["id"] + " " + cl, r["_chgs"][0]["dos"].strip(), r["carriercodeshort"], " | ".join(e["name"][:60] for e in r["_errs"])[:120], "%.2f" % sum(float(c["insportion"]) for c in r["_chgs"]), "new on run %s" % run])
bi = {v["vid"]: (bt, v) for bt, rr in b["inspector"].items() for v in rr}; ai = {v["vid"]: (bt, v) for bt, rr in a["inspector"].items() for v in rr}
for vid, (bt, v) in bi.items():
    st = "remaining" if vid in ai else "cleared"
    pats = ",".join((e[1] or "")[:25] for e in v["errs"])
    rows.append(["Claim Inspector", st, v["pid"], vid, "", "", pats[:120], "", "advisory bypassed (insp_bypass_advisories.py)" if st == "cleared" else "standing hard hold"])
for vid, (bt, v) in ai.items():
    if vid not in bi: rows.append(["Claim Inspector", "new after", v["pid"], vid, "", "", ",".join((e[1] or "")[:25] for e in v["errs"])[:120], "", "raised by this run's Bill-Insurance resaves: advisories bypassed 0611Z; admission-date / sequela / CCI holds -> insp_1014_0510.py / next run"])
rows.append(["ERA", "remaining", "", "check 1053116", "", "UNI20 W0020208", "takeback pair - held for William's decision", "71.00", "unposted before 1 / after 1; no new 835, no Availity file"])
try:
    cs = json.load(open("claimstatus_20261014.json"))
    for r in cs:
        rows.append(["UNI20/BCBS pre-5/1 sweep 89", "answer", r.get("patientid"), r.get("visitid"), r.get("dos"), r.get("carrier"), "; ".join("%s %s %s" % (s.get("cat"), s.get("code"), (s.get("codev") or "")[:40]) for s in r.get("status") or [])[:120], "%.2f" % float(r.get("balance") or 0), r.get("action", "")])
except Exception as e: print("sweep rows skipped", e)
with open("_run report 10-14 0510.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["column", "state", "chart", "visit", "dos", "carrier", "error", "amount", "action"]); w.writerows(rows)
print("csv rows", len(rows))
