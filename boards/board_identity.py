# PLAIN ENGLISH (Identity block for the Insurance Refresh Board - DOB, insurance ID, last facility)
# Decides: Nothing. For every board card with an AMD patient id, reads the chart (getdemographic) and the
#   transaction history (gettxhistory) and works out the four things William wants under the chart number:
#   the DOB, the insurance ID number of the plan that bills FIRST today (with its carrier), the last facility
#   the patient was seen at (with the last date of service), and the full facilities line (newest first, same
#   rule as board_facilities.py). Writes board_identity.json and ONE board_updates_<stamp>.json file (schema
#   irb-board-updates/1) that the board applies by itself the next time it is opened - the same no-approval
#   path the 2-hourly run uses.
# Rules it uses: primary plan = the plan whose sequence is the FIRST entry of the patient's insorder, if it is
#   still active (no end date, or an end date on/after today); otherwise the first active plan in insorder;
#   otherwise the most recently begun plan, flagged '(ended mm/dd/yyyy)'. Voided charges are ignored. Carrier
#   codes/names come from carriers.json. Only rows whose values actually changed go into the update file.
# Never touches: AMD (read-only), the board itself (the page applies the file), group numbers, plans.
# Usage: python3 board_identity.py <dir of board row JSON files> [--stamp 2026-09-14T0500Z] [--limit N]
# ---
import amd, txh, json, glob, re, collections, datetime, sys, os, time
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
def _load_json(name):
    for p in (os.path.join(HERE, name), os.path.join(HERE, "..", "practices", "ehpa", name), os.path.join("/home/claude/unbilled", name)):
        if os.path.exists(p): return json.load(open(p))
    return {}
CARRIERS = _load_json("carriers.json")          # "car6085": ["FLO02", "MEDICARE ..."]
SHORTALL = {"HCA FLORIDA CAPITAL HOSPITAL TALLAHASSEE MEDICAL C": "HCA Capital Hospital",
         "BRYNWOOD OPERATIONS LLC BRYNWOOD OPERATIONS LLC": "Brynwood (Monticello)",
         "CENTRE POINTE HEALTH AND REHAB CENTER CENTRE POINT": "Centre Pointe Health & Rehab"}
TODAY = datetime.date.today()

def short(n):
    n = SHORTALL.get(n) or n.title().replace(" Alf", " ALF").replace(" Llc", "").replace("Of ", "of ").replace("At ", "at ").replace("And ", "and ").strip()
    return re.sub(r"\s+", " ", n)
def carrier_label(car):
    code, name = (CARRIERS.get(car) or [car, ""])[:2]
    name = re.sub(r"\s+", " ", (name or "").title()).replace("Of ", "of ").strip()
    return code, (name[:30].rstrip() + ("…" if len(name) > 30 else ""))
def mdy(d):
    """mm/dd/yyyy -> date or None"""
    try: return datetime.datetime.strptime(d, "%m/%d/%Y").date()
    except Exception: return None
def active(p):
    e = mdy(p.get("enddate") or "")
    return e is None or e >= TODAY

def chart(pid):
    r = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "pat%s" % pid, "nocookie": "1"}), timeout=60)
    root = ET.fromstring(r)
    pat = next(root.iter("patient"), None)
    if pat is None: raise RuntimeError("no <patient> in getdemographic (%s)" % re.sub(r"\s+", " ", r[:160]))
    plans = [dict(i.attrib) for i in root.iter("insplan")]
    return dict(pat.attrib), plans

def primary(pat, plans):
    order = [s.strip() for s in (pat.get("insorder") or "").split(",") if s.strip()]
    by_seq = {p.get("sequence"): p for p in plans}
    for s in order:                                   # first ACTIVE plan in billing order
        p = by_seq.get(s)
        if p and active(p): return p, ""
    act = [p for p in plans if active(p)]
    if act: return sorted(act, key=lambda p: int(p.get("sequence") or 99))[0], ""
    if plans:                                          # nothing active: newest plan, flagged
        p = sorted(plans, key=lambda p: mdy(p.get("begindate") or "") or datetime.date(1900, 1, 1))[-1]
        return p, " (ended %s)" % (p.get("enddate") or "?")
    return None, ""

def plans_line(pat, plans):
    order = [s.strip() for s in (pat.get("insorder") or "").split(",") if s.strip()]
    by_seq = {p.get("sequence"): p for p in plans}
    parts, seen = [], set()
    rank = {0: "1st", 1: "2nd", 2: "3rd"}
    i = 0
    for s in order:
        p = by_seq.get(s)
        if not p or not active(p): continue
        code, name = carrier_label(p.get("carrier")); parts.append("%s %s %s %s" % (rank.get(i, "%dth" % (i + 1)), code, name, p.get("subscribernum") or "")); seen.add(p.get("id")); i += 1
    for p in sorted(plans, key=lambda p: int(p.get("sequence") or 99)):
        if p.get("id") in seen: continue
        code, name = carrier_label(p.get("carrier"))
        parts.append("%s %s %s%s" % (code, name, p.get("subscribernum") or "", "" if active(p) else " (ended %s)" % p.get("enddate")))
    return " · ".join(parts)

def facilities(pid):
    root = txh.fetch(pid)
    fac = collections.defaultdict(lambda: {"first": "9999", "last": "0000", "provs": set(), "n": 0})
    last = ("0000", None)
    for c in root.iter("charge"):
        if c.get("void") == "1" or not c.get("dos"): continue
        k = c.get("facname") or c.get("faccode") or "?"; dos = c.get("dos"); iso = dos[6:] + dos[:2] + dos[3:5]
        x = fac[k]; x["first"] = min(x["first"], iso); x["last"] = max(x["last"], iso); x["provs"].add(c.get("provcode")); x["n"] += 1
        if iso > last[0]: last = (iso, k)
    parts = []
    for k, x in sorted(fac.items(), key=lambda kv: -int(kv[1]["last"])):
        a = "%d/%s" % (int(x["first"][4:6]), x["first"][2:4]); b = "%d/%s" % (int(x["last"][4:6]), x["last"][2:4])
        rng = a if a == b else "%s–%s" % (a, b); who = "" if "WEFFI" in x["provs"] else " (Pam)"
        parts.append("%s %s%s" % (short(k), rng, who))
    lastfac = short(last[1]) if last[1] else ""
    lastdos = "%s/%s/%s" % (last[0][4:6], last[0][6:8], last[0][:4]) if last[1] else ""
    return " · ".join(parts), lastfac, lastdos

def identity(pid):
    pat, plans = chart(pid)
    p, flag = primary(pat, plans)
    code, name = carrier_label(p.get("carrier")) if p else ("", "")
    facs, lastfac, lastdos = facilities(pid)
    return {"dob": pat.get("dob") or "", "insid": ((p.get("subscribernum") or "") + flag).strip() if p else "",
            "inscarrier": ("%s %s" % (code, name)).strip() if p else "", "insplans": plans_line(pat, plans),
            "lastfac": lastfac, "lastdos": lastdos, "facilities": facs, "chartname": pat.get("name") or ""}

if __name__ == "__main__":
    a = sys.argv[1:]; SRC = a[0]
    stamp = a[a.index("--stamp") + 1] if "--stamp" in a else datetime.datetime.utcnow().strftime("%Y-%m-%dT%H%MZ")
    limit = int(a[a.index("--limit") + 1]) if "--limit" in a else 0
    amd.login_cached()
    out, ops, diffs, errs = {}, [], [], []
    files = sorted(glob.glob(os.path.join(SRC, "*.json")))
    if limit: files = files[:limit]
    for f in files:
        d = json.load(open(f)); rid = os.path.basename(f)[:-5]
        pid = re.sub(r"\D", "", str(d.get("amdid") or d.get("pid") or ""))
        if not pid: continue
        try: ident = identity(pid)
        except Exception as e:
            errs.append((rid, str(e)[:120])); print("ERR", rid, str(e)[:120], flush=True); time.sleep(1); continue
        out[rid] = ident
        if ident["dob"] and d.get("dob") and ident["dob"] != d.get("dob"): diffs.append((rid, d.get("dob"), ident["dob"]))
        setf = {k: ident[k] for k in ("insid", "inscarrier", "insplans", "lastfac", "lastdos", "facilities") if (ident[k] or "") != (d.get(k) or "")}
        if ident["dob"] and ident["dob"] != (d.get("dob") or ""): setf["dob"] = ident["dob"]
        if not d.get("amdid") and d.get("pid"): setf["amdid"] = pid
        if setf:
            setf["identity_at"] = stamp
            ops.append({"op": "update", "collection": "items", "id": rid, "set": setf})
        print(rid, "->", ident["insid"], "|", ident["inscarrier"], "|", ident["lastfac"], ident["lastdos"], flush=True)
        time.sleep(0.3)
    json.dump(out, open("board_identity.json", "w"), indent=1)
    upd = {"schema": "irb-board-updates/1", "source": "board_identity.py %s (chat session)" % stamp,
           "created": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), "ops": ops}
    name = "board_updates_%s.json" % stamp
    json.dump(upd, open(name, "w"), indent=1)
    print("done: %d charts, %d rows changed -> %s; %d DOB differences; %d errors" % (len(out), len(ops), name, len(diffs), len(errs)))
    for x in diffs: print("DOB DIFF", x)
    for x in errs: print("ERROR", x)
