# PLAIN ENGLISH (Nightly credentialing check)
# Decides: Whether anything on the Credentialing Board changed at the source - the three NPPES records (address, taxonomy, license, group), the Medicare revalidation list (a due date appearing), and the OIG exclusion list (a match) - and which register rows are inside their reminder window.
# Rules it uses: Compares tonight's NPPES pull to the last snapshot (cred_nppes_snapshot.json) and reports only differences. Revalidation: any non-blank due date is news. LEIE: match on last name + first name, business name, or NPI. Reminder windows: 120-day items at 14/3 days, everything else at 90/30/7 days, computed from each board row's `due`.
# Never touches: NPPES, PECOS, or any payer. It writes cred_check_<date>.json for the cascade to post to the board; the board writes themselves are done by the cascade with read-merge-update.
# ---
"""Usage: python3 cred_check.py   -> cred_check_YYYYMMDD.json + printed summary"""
import requests, json, csv, io, datetime, os, sys
NPIS = {"1629515325": "Effinger Health PA (group)", "1225327380": "William Effinger DO", "1235128869": "Pamela Garcia ARNP"}
PEOPLE = [("EFFINGER", "WILLIAM"), ("GARCIA", "PAMELA")]; BUS = ["EFFINGER"]
today = datetime.date.today(); stamp = today.strftime("%Y%m%d"); out = {"date": today.isoformat(), "nppes": {}, "nppes_changes": [], "revalidation": {}, "leie": None, "reminders": []}
# 1. NPPES
for npi, who in NPIS.items():
    try:
        j = requests.get("https://npiregistry.cms.hhs.gov/api/", params={"version": "2.1", "number": npi}, timeout=30).json(); r = (j.get("results") or [{}])[0]; b = r.get("basic", {})
        loc = next((a for a in r.get("addresses", []) if a.get("address_purpose") == "LOCATION"), {})
        out["nppes"][npi] = {"who": who, "status": b.get("status"), "updated": b.get("last_updated"), "location": "%s, %s, %s %s" % (loc.get("address_1"), loc.get("city"), loc.get("state"), loc.get("postal_code")),
                             "taxonomies": [(t.get("code"), t.get("license"), t.get("primary")) for t in r.get("taxonomies", [])], "identifiers": [(i.get("desc"), i.get("identifier")) for i in r.get("identifiers", [])],
                             "practice_locations": [p.get("address_1") for p in r.get("practiceLocations", [])]}
    except Exception as e: out["nppes"][npi] = {"who": who, "error": str(e)[:120]}
snap = json.load(open("cred_nppes_snapshot.json")) if os.path.exists("cred_nppes_snapshot.json") else {}
for npi, cur in out["nppes"].items():
    old = snap.get(npi)
    if old and "error" not in cur and json.dumps(old, sort_keys=True) != json.dumps(cur, sort_keys=True):
        out["nppes_changes"].append({"npi": npi, "who": cur["who"], "before": old, "after": cur})
if all("error" not in v for v in out["nppes"].values()): json.dump(out["nppes"], open("cred_nppes_snapshot.json", "w"), indent=1)
# 2. Medicare revalidation
try:
    u = "https://data.cms.gov/data-api/v1/dataset/3746498e-874d-45d8-9c69-68603cafea60/data"
    for npi, who in NPIS.items():
        rows = requests.get(u, params={"filter[National Provider Identifier]": npi, "size": 20}, timeout=30).json()
        out["revalidation"][npi] = [{"enrollment": x.get("Enrollment ID"), "specialty": x.get("Enrollment Specialty"), "due": x.get("Revalidation Due Date") or "TBD", "adjusted": x.get("Adjusted Due Date") or ""} for x in rows]
except Exception as e: out["revalidation"] = {"error": str(e)[:120]}
# 3. OIG LEIE (monthly is enough, but it is cheap)
try:
    r = requests.get("https://oig.hhs.gov/exclusions/downloadables/UPDATED.csv", timeout=180); rows = list(csv.DictReader(io.StringIO(r.content.decode("latin-1"))))
    hits = [x for x in rows if (x.get("LASTNAME", "").upper(), x.get("FIRSTNAME", "").upper()[:3]) in [(l, f[:3]) for l, f in PEOPLE] or x.get("NPI") in NPIS or any(bn in x.get("BUSNAME", "").upper() for bn in BUS)]
    out["leie"] = {"rows": len(rows), "matches": [{k: h.get(k) for k in ("LASTNAME", "FIRSTNAME", "BUSNAME", "NPI", "STATE", "EXCLDATE")} for h in hits]}
except Exception as e: out["leie"] = {"error": str(e)[:120]}
# 4. Reminder windows from the board export, if the cascade dropped one (cred_board_rows.json = list of {id,name,due,cycle})
if os.path.exists("cred_board_rows.json"):
    for row in json.load(open("cred_board_rows.json")):
        if not row.get("due"): continue
        days = (datetime.date.fromisoformat(row["due"]) - today).days; lead = (14, 3) if "120" in (row.get("cycle") or "") else (90, 30, 7)
        if days < 0 or days in lead: out["reminders"].append({"id": row["id"], "name": row["name"], "due": row["due"], "days": days})
json.dump(out, open("cred_check_%s.json" % stamp, "w"), indent=1)
print("NPPES: %d records, %d changed" % (len(out["nppes"]), len(out["nppes_changes"])))
for npi, rv in (out["revalidation"] or {}).items():
    if isinstance(rv, list): print("  revalidation %s: %s" % (NPIS[npi], ", ".join("%s due %s" % (x["enrollment"], x["due"]) for x in rv) or "not on list"))
print("LEIE:", out["leie"] if not out["leie"] or "error" in out["leie"] else "%d rows, %d matches" % (out["leie"]["rows"], len(out["leie"]["matches"])))
print("Reminders due:", out["reminders"] or "none")
