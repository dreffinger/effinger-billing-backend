# PLAIN ENGLISH (Pattern 4543 invalid-DOS triage, 11/09/2026)
# Decides: Nothing. For each of the 15 Claim Inspector visits held with Pattern 4543 (DOS 11/07/2026),
#          reads the chart's whole charge history and prints the DOS timeline around that date, so the
#          duplicate-of-11/01 visits can be told apart from the real 11/07 visits.
# Rules it uses: Read-only. Two tests William gave:
#          (a) is there already a charge of the SAME E/M family on 11/01/2026 on this chart?
#          (b) is 11/07 part of a daily run - i.e. is there a visit on 11/06 (the day prior)?
# Never touches: Anything - it writes nothing to AdvancedMD. Output file only.
import json, sys, datetime
import xml.etree.ElementTree as ET
import txh

HELD = [
    ("19459901", "23372510", "22858",    "FLO99", "99233"),
    ("19459902", "23372511", "17476458", "FLO02", "99233"),
    ("19459903", "23372512", "17478213", "SUN01", "99232"),
    ("19459904", "23372513", "47979",    "UHCMA", "99233"),
    ("19459905", "23372514", "17478223", "BCBS",  "99233"),
    ("19459906", "23372515", "17473197", "FLO02", "99233"),
    ("19459907", "23372516", "17473090", "FLO02", "99233"),
    ("19459908", "23372517", "17470950", "FLO02", "99233"),
    ("19459909", "23372518", "20379",    "FLO02", "99233"),
    ("19459910", "23372519", "17478262", "UNI20", "99232"),
    ("19459911", "23372520", "17478264", "FLO02", "99232"),
    ("19459912", "23372521", "17472922", "CAP07", "99232"),
    ("19459913", "23372522", "17478261", "BCBS",  "99233"),
    ("19459914", "23372523", "17474798", "SUN01", "99233"),
    ("19459915", "23372524", "17478031", "UHCMA", "99233"),
]

HOSP = {"99221","99222","99223","99231","99232","99233","99238","99239"}

def fam(code):
    if code in HOSP: return "hospital E/M"
    if code.startswith("994"): return "CCM/ACP"
    return code

def dparse(s):
    s = (s or "").strip().split(" ")[0]
    try: return datetime.date(*[int(x) for x in (s.split("/")[2], s.split("/")[0], s.split("/")[1])])
    except Exception: return None

out = {}
for vid, cid, pid, carrier, cpt in HELD:
    root = txh.fetch(pid)
    rows = []
    for c in root.iter("charge"):
        a = c.attrib
        d = dparse(a.get("dos") or a.get("dateofservice"))
        if d is None: continue
        rows.append({
            "chg": a.get("id"), "visit": a.get("visitid") or a.get("visit"),
            "dos": d.isoformat(), "cpt": a.get("proccode"),
            "amount": a.get("amount"), "void": a.get("void"),
            "billdate": a.get("billdate"), "carrier": a.get("carrier") or a.get("carriercode"),
            "insbal": a.get("insbal") or a.get("insbalance"), "paid": a.get("paid"),
            "fac": a.get("facname"),
        })
    rows.sort(key=lambda r: (r["dos"], r["cpt"] or ""))
    live = [r for r in rows if r["void"] != "1"]
    # window: 10/24 .. 11/09
    win = [r for r in live if "2026-10-24" <= r["dos"] <= "2026-11-09"]
    dates_hosp = sorted({r["dos"] for r in win if (r["cpt"] or "") in HOSP})
    same_1101 = [r for r in live if r["dos"] == "2026-11-01" and fam(r["cpt"] or "") == fam(cpt)]
    on_1106 = [r for r in win if r["dos"] == "2026-11-06" and (r["cpt"] or "") in HOSP]
    on_1108 = [r for r in win if r["dos"] == "2026-11-08" and (r["cpt"] or "") in HOSP]
    other_1107 = [r for r in live if r["dos"] == "2026-11-07" and r["chg"] != cid]
    out[vid] = {
        "chg": cid, "pid": pid, "carrier": carrier, "cpt": cpt,
        "hosp_em_dates_1024_1109": dates_hosp,
        "same_family_on_1101": same_1101,
        "hosp_em_on_1106": on_1106,
        "hosp_em_on_1108": on_1108,
        "other_charges_on_1107": other_1107,
        "window_rows": win,
    }
    print("=" * 84)
    print(f"vst{vid}  chg{cid}  pat{pid}  {carrier}  {cpt} 11/07")
    print("  hospital E/M dates 10/24-11/09:", ", ".join(d[5:] for d in dates_hosp) or "(none)")
    print("  day prior 11/06 hospital E/M :", "YES " + ", ".join(f"{r['cpt']}@{r['visit']}" for r in on_1106) if on_1106 else "no")
    print("  11/08 hospital E/M           :", "YES " + ", ".join(f"{r['cpt']}@{r['visit']}" for r in on_1108) if on_1108 else "no")
    if same_1101:
        for r in same_1101:
            print(f"  11/01 SAME FAMILY            : {r['cpt']} chg{r['chg']} vst{r['visit']} ${r['amount']} billed {r['billdate']} insbal {r['insbal']} paid {r['paid']}")
    else:
        print("  11/01 same family            : none")
    if other_1107:
        for r in other_1107:
            print(f"  other 11/07 charge           : {r['cpt']} chg{r['chg']} vst{r['visit']} ${r['amount']} billed {r['billdate']}")

json.dump(out, open("registers/dos_4543_check_20261109.json", "w"), indent=1)
print("\nsaved registers/dos_4543_check_20261109.json")
