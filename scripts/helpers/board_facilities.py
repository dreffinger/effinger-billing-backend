# PLAIN ENGLISH (Facilities line for the Insurance Refresh Board)
# Decides: Nothing. For every board card with an AMD patient id, reads the chart's transaction history and writes a one-line list of the facilities the patient was seen at (name + month range, newest first; '(Pam)' when only Pam saw them there) to board_facilities.json so the board cards can show it under the chart number.
# Rules it uses: txh.fetch per patient; voided charges ignored; facility names shortened (drops 'LLC', duplicates, city in parentheses).
# Never touches: AMD or the board itself (the batch writer does that).
# ---
import txh, json, glob, re, collections, datetime, sys, os
SRC = sys.argv[1]; out = {}
SHORT = {"HCA FLORIDA CAPITAL HOSPITAL TALLAHASSEE MEDICAL C": "HCA Capital Hospital", "BRYNWOOD OPERATIONS LLC BRYNWOOD OPERATIONS LLC": "Brynwood (Monticello)", "CENTRE POINTE HEALTH AND REHAB CENTER CENTRE POINT": "Centre Pointe Health & Rehab"}
def short(n):
    n = SHORT.get(n) or n.title().replace(" Alf", " ALF").replace(" Llc", "").replace("Of ", "of ").replace("At ", "at ").replace("And ", "and ").strip()
    return re.sub(r"\s+", " ", n)
def mmyy(d): return "%d/%s" % (int(d[:2]), d[8:10])
for f in sorted(glob.glob(os.path.join(SRC, "*.json"))):
    d = json.load(open(f)); pid = re.sub(r"\D", "", str(d.get("amdid") or ""))
    if not pid: continue
    try: root = txh.fetch(pid)
    except Exception as e: print("ERR", f, e); continue
    fac = collections.defaultdict(lambda: {"first": "9999", "last": "0000", "provs": set(), "n": 0})
    for c in root.iter("charge"):
        if c.get("void") == "1" or not c.get("dos"): continue
        k = c.get("facname") or c.get("faccode") or "?"; dos = c.get("dos"); iso = dos[6:] + dos[:2] + dos[3:5]
        x = fac[k]; x["first"] = min(x["first"], iso); x["last"] = max(x["last"], iso); x["provs"].add(c.get("provcode")); x["n"] += 1
    parts = []
    for k, x in sorted(fac.items(), key=lambda kv: -int(kv[1]["last"])):
        a = "%d/%s" % (int(x["first"][4:6]), x["first"][2:4]); b = "%d/%s" % (int(x["last"][4:6]), x["last"][2:4])
        rng = a if a == b else "%s–%s" % (a, b); who = "" if "WEFFI" in x["provs"] else " (Pam)"
        parts.append("%s %s%s" % (short(k), rng, who))
    out[os.path.basename(f)[:-5]] = " · ".join(parts)
    print(os.path.basename(f)[:-5], "->", out[os.path.basename(f)[:-5]][:120], flush=True)
json.dump(out, open("board_facilities.json", "w"), indent=1)
print("done", len(out))
