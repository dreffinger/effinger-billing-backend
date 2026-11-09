# PLAIN ENGLISH (Pattern 4543 timeline, 11/09/2026)
# Decides: Nothing. Prints every live charge 10/26-11/09 for the 15 charts whose 11/07 visit is held
#          with Pattern 4543, so a continuing stay can be told from one that had already ended.
# Rules it uses: Read-only. Flags discharge-day codes (99238/99239) and the 11/06 / 11/08 neighbours.
# Never touches: Anything - it writes nothing to AdvancedMD.
import json, datetime
import xml.etree.ElementTree as ET
import txh

HELD = {
    "22858":    ("19459901", "23372510", "FLO99", "99233"),
    "17476458": ("19459902", "23372511", "FLO02", "99233"),
    "17478213": ("19459903", "23372512", "SUN01", "99232"),
    "47979":    ("19459904", "23372513", "UHCMA", "99233"),
    "17478223": ("19459905", "23372514", "BCBS",  "99233"),
    "17473197": ("19459906", "23372515", "FLO02", "99233"),
    "17473090": ("19459907", "23372516", "FLO02", "99233"),
    "17470950": ("19459908", "23372517", "FLO02", "99233"),
    "20379":    ("19459909", "23372518", "FLO02", "99233"),
    "17478262": ("19459910", "23372519", "UNI20", "99232"),
    "17478264": ("19459911", "23372520", "FLO02", "99232"),
    "17472922": ("19459912", "23372521", "CAP07", "99232"),
    "17478261": ("19459913", "23372522", "BCBS",  "99233"),
    "17474798": ("19459914", "23372523", "SUN01", "99233"),
    "17478031": ("19459915", "23372524", "UHCMA", "99233"),
}
HOSP = {"99221","99222","99223","99231","99232","99233"}
DISCH = {"99238","99239"}

def dparse(s):
    s = (s or "").strip().split(" ")[0]
    p = s.split("/")
    try: return datetime.date(int(p[2]), int(p[0]), int(p[1]))
    except Exception: return None

out = {}
for pid, (vid, cid, carrier, cpt) in HELD.items():
    root = txh.fetch(pid)
    rows = []
    for c in root.iter("charge"):
        a = c.attrib
        d = dparse(a.get("dos") or a.get("dateofservice"))
        if d is None or a.get("void") == "1": continue
        if not (datetime.date(2026,10,26) <= d <= datetime.date(2026,11,9)): continue
        rows.append((d.isoformat(), a.get("proccode"), a.get("id"), a.get("visitid") or a.get("visit"),
                     a.get("billdate") or "", a.get("insbal") or "", a.get("paid") or ""))
    rows.sort()
    days = {}
    for r in rows: days.setdefault(r[0], []).append(r)
    hosp_days = sorted(d for d, rs in days.items() if any(r[1] in HOSP for r in rs))
    disch = [(d, r[1]) for d, rs in days.items() for r in rs if r[1] in DISCH]
    last_before = [d for d in hosp_days if d < "2026-11-07"]
    gap = None
    if last_before:
        gap = (datetime.date(2026,11,7) - dparse(last_before[-1].replace("-","/")[5:7] + "/" + last_before[-1][8:10] + "/2026")).days if False else \
              (datetime.date(2026,11,7) - datetime.date(int(last_before[-1][:4]), int(last_before[-1][5:7]), int(last_before[-1][8:10]))).days
    verdict = "BILL (stay running into 11/07)" if "2026-11-06" in hosp_days else "VOID (stay had ended; isolated 11/07)"
    out[pid] = {"visit": vid, "charge": cid, "carrier": carrier, "cpt": cpt,
                "hosp_days": hosp_days, "discharge_codes": disch,
                "last_hosp_day_before_1107": last_before[-1] if last_before else None,
                "gap_days": gap, "verdict": verdict,
                "rows": rows}
    print("=" * 92)
    print(f"pat{pid}  vst{vid}  chg{cid}  {carrier}  {cpt}  ->  {verdict}")
    print(f"   last hospital day before 11/07: {last_before[-1][5:] if last_before else '(none)'}   gap to 11/07: {gap} day(s)")
    if disch: print("   DISCHARGE CODE:", ", ".join(f"{d[5:]} {c}" for d, c in sorted(disch)))
    for d in sorted(days):
        tags = " ".join(f"{r[1]}" + ("[HELD]" if r[2] == cid else "") for r in days[d])
        bill = days[d][0][4]
        print(f"     {d[5:]}  {tags:<28} billed {bill or '-'}")

json.dump(out, open("registers/dos_4543_timeline_20261109.json", "w"), indent=1)
print("\nsaved registers/dos_4543_timeline_20261109.json")
