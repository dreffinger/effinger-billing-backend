# PLAIN ENGLISH (Facility badge for the Insurance Refresh Board - the ACTUAL facility + ALF/SNF residence, top-left of every card)
# Decides: Nothing. For every board card with an AMD patient id, reads the chart's transaction history (gettxhistory via
#   board_identity.facilities) and works out the facility badge William asked for on 10/3/2026: the actual facility of the
#   NEWEST visit (name as AMD spells it, shortened), its kind (SNF / ALF / IL / ICF resident, hospital inpatient, inpatient rehab,
#   home visit, telehealth, office), the last date of service there, and - when the newest visit is a hospital/other place -
#   the newest SNF/ALF/IL facility on the chart as the place the patient LIVES ("resident at ..."). Writes board_facnow.json
#   (row id -> the facnow object + refreshed facilities/lastfac/lastdos) for the caller to put on the board rows (field `facnow`).
# Rules it uses: voided charges ignored; kind by facility NAME (every ALF in the AMD list carries 'ALF'; the nursing facilities are
#   named; HCA/TMH = hospital; HCA REHAB = inpatient rehab). Same classifier as the board page's kindOf() - keep them in step.
# Never touches: AMD (read-only) or the board itself (the chat session / run applies the file).
# Usage: python3 board_facnow.py <dir of board row JSON files> [--limit N] [--only id,id,...]
# ---
import amd, json, glob, re, datetime, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import board_identity as bi

KIND_LABEL = {"SNF": "SNF resident", "ALF": "ALF resident", "IL": "IL resident", "ICF": "ICF resident", "HOSP": "hospital inpatient",
              "IRF": "inpatient rehab", "HOME": "home visit", "TELE": "telehealth", "OFFICE": "office", "OTHER": ""}
RES_KINDS = ("SNF", "ALF", "IL", "ICF")

def kind_of(name):
    n = re.sub(r"\s+", " ", str(name or "").upper().replace("&", " AND "))
    if not n: return "OTHER"
    if re.search(r"\bALF\b|ASSISTED|MEMORY CARE|BROOKDALE|ALLEGRO|AZALEA|CANTERFIELD|CAPITAL SQUARE|GROVE AT CANOPY|HARBOR ?CHASE|PACIFICA|SODALIS|TAPESTRY|PARRY", n): return "ALF"
    # 11/12: SOUTHWOOD, not the facility's first word - the privacy gate took two facility names for patient names and rewrote them
    # here (the other is caught by HEALTH AND REHAB / REHABILITATION CENTER). Same words as the page and tools/db/board_chargefac.py.
    if re.search(r"BRYNWOOD|SOUTHWOOD|ASPIRE|AVIATA|CENTRE POINTE|CENTER POINTE|EDEN SPRINGS|LAKE PARK|SEVEN HILLS|BERTRAND|HEALTH AND REHAB|REHABILITATION CENTER|NURSING", n): return "SNF"
    if re.search(r"HCA REHAB|INPATIENT REHAB|\bIRF\b", n): return "IRF"
    if re.search(r"HOSPITAL|\bHCA\b|\bTMH\b|MEMORIAL|MEDICAL CENTER|\bER\b|EMERGENCY", n): return "HOSP"
    if re.search(r"INDEPENDENT LIVING|\bIL\b", n): return "IL"
    if re.search(r"DEVELOPMENTAL|\bICF\b", n): return "ICF"
    if re.search(r"TELEHEALTH", n): return "TELE"
    if re.search(r"INDIVIDUAL PATIENT HOMES|\bHOME\b", n): return "HOME"
    if re.search(r"NORTH FLORIDA SENIOR CARE|\bOFFICE\b", n): return "OFFICE"
    if re.search(r"\bSNF\b|\bNF\b|\bLTC\b|SKILLED|REHAB|HEALTH CENTER|WESTMINSTER", n): return "SNF"
    return "OTHER"

def facnow_from(facs_line, lastfac, lastdos):
    """facilities line 'Name m/yy–m/yy · Name m/yy (Pam)' (newest first) -> the badge object"""
    ents = []
    for part in [p.strip() for p in (facs_line or "").split(" · ") if p.strip()]:
        m = re.match(r"^(.*?)\s+(\d{1,2}/\d{2}(?:[–-]\d{1,2}/\d{2})?)(\s*\(Pam\))?$", part)
        ents.append({"name": m.group(1), "range": m.group(2), "pam": bool(m.group(3))} if m else {"name": part, "range": "", "pam": False})
    if not ents and not lastfac: return None
    top = ents[0]["name"] if ents else lastfac
    k = kind_of(top)
    res = None
    if k not in RES_KINDS:
        for e in ents[1:]:
            ek = kind_of(e["name"])
            if ek in RES_KINDS:
                res = {"name": e["name"], "kind": ek, "thru": e["range"].split("–")[-1].split("-")[-1]}; break
    return {"name": top, "kind": k, "label": KIND_LABEL.get(k, ""), "dos": lastdos or "", "res": res,
            "at": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}

if __name__ == "__main__":
    a = sys.argv[1:]; SRC = a[0]
    limit = int(a[a.index("--limit") + 1]) if "--limit" in a else 0
    only = set(a[a.index("--only") + 1].split(",")) if "--only" in a else None
    amd.login_cached()
    out, errs = {}, []
    files = sorted(glob.glob(os.path.join(SRC, "*.json")))
    if limit: files = files[:limit]
    for f in files:
        rid = os.path.basename(f)[:-5]
        if only and rid not in only: continue
        d = json.load(open(f))
        pid = re.sub(r"\D", "", str(d.get("amdid") or d.get("pid") or ""))
        if not pid: continue
        try: facs, lastfac, lastdos = bi.facilities(pid)
        except Exception as e:
            errs.append((rid, str(e)[:120])); print("ERR", rid, str(e)[:120], flush=True); time.sleep(1); continue
        fn = facnow_from(facs, lastfac, lastdos)
        row = {"facnow": fn}
        for k, v in (("facilities", facs), ("lastfac", lastfac), ("lastdos", lastdos)):
            if (v or "") != (d.get(k) or ""): row[k] = v
        out[rid] = row
        print(rid, "->", (fn or {}).get("name"), (fn or {}).get("kind"), (fn or {}).get("dos"), "| res", ((fn or {}).get("res") or {}).get("name"), flush=True)
        time.sleep(0.25)
    json.dump(out, open("board_facnow.json", "w"), indent=1)
    print("done: %d rows, %d errors" % (len(out), len(errs)))
    for x in errs: print("ERR", x)
