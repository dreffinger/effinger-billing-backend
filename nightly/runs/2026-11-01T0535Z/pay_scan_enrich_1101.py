# PLAIN ENGLISH (Add the two ledger fields the current pay_scan.py no longer writes, nightly cascade 2026-11-01)
# Decides: Nothing. build_money.py / money_template.html expect paid_dos12 (payments posted in the last 12 months whose
# date of service is also inside 12 months) and dos_year (paid by year of service) per carrier; the workspace pay_scan.py
# writes paid_12 / paid_24 / months only. This recomputes both from pay_scan_cache.json and rewrites payments_by_carrier.json.
# Never touches: AMD.
import json, datetime, collections
cache = json.load(open("pay_scan_cache.json")); out = json.load(open("payments_by_carrier.json"))
today = datetime.date.today(); d12 = today - datetime.timedelta(days=365)
def iso(s):
    try: return datetime.datetime.strptime(s[:10], "%m/%d/%Y").date()
    except Exception:
        try: return datetime.date.fromisoformat(s[:10])
        except Exception: return None
dos12 = collections.defaultdict(float); dosyr = collections.defaultdict(lambda: collections.defaultdict(float))
for pid, rec in cache.items():
    for p in rec.get("pays", []):
        date, car, amt, chk, dos = (p + [None] * 5)[:5]; d = iso(date or ""); s = iso(dos or "")
        car = car or "PAT"
        if s: dosyr[car][str(s.year)] += float(amt or 0)
        if d and s and d >= d12 and s >= d12: dos12[car] += float(amt or 0)
for k, v in out["carriers"].items():
    v.setdefault("paid_dos12", round(dos12.get(k, 0.0), 2)); v.setdefault("dos_year", {y: round(a, 2) for y, a in sorted(dosyr.get(k, {}).items())})
json.dump(out, open("payments_by_carrier.json", "w"), indent=1)
print("enriched %d carriers; paid_dos12 total $%.2f" % (len(out["carriers"]), sum(v["paid_dos12"] for v in out["carriers"].values())))
