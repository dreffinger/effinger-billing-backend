# PLAIN ENGLISH (Deceased-patient guard - William 9/22/2026: "on any straight medicare claims we are never submitting bills on a
#          medicare deceased person"; check the MBI / Medicare record for a date of death before any claim goes out).
# Decides: whether a claim may be submitted. BLOCK when the date of service is AFTER the patient's date of death (any payer).
# Sources, in order: (1) the cache practices/ehpa/registers/deceased_cache.json (pid -> dod / checked date / source),
#          (2) AMD getdemographic 'deceased', (3) a fresh Stedi Medicare lookup (MBILUNOSSN: name + DOB + FL) whose 271
#          carries the date of death (DTP*442 / dateOfDeath). A fresh lookup runs when the claim goes to straight Medicare
#          (FLO02 / car6085) or is CCM and the cache is missing or older than 30 days. A lookup that fails does NOT block
#          (logged 'unverified' for the daily report) - only a positive date of death blocks.
# CCM in the month of death: the DOS must be on/before the date of death; a month-end CCM date after the death is blocked.
import os, re, json, time, datetime
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
CACHE = os.environ.get("DECEASED_CACHE", os.path.join(REPO, "practices/ehpa/registers/deceased_cache.json"))
KEYF = os.environ.get("STEDI_KEY_FILE", "/home/claude/unbilled/secrets/stedi_live.key")
STEDI = "https://healthcare.us.stedi.com/2024-04-01/change/medicalnetwork/eligibility/v3"
MEDICARE = {"FLO02", "car6085"}
CCM = {"99487", "99489", "99490", "99491", "99439", "99437", "G0556", "G0557", "G0558", "G2058",
       "pcode492674", "pcode492675", "pcode492676", "pcode492677"}
MAX_AGE_DAYS = 30
LOG = []
def _load():
    try: return json.load(open(CACHE))
    except Exception: return {}
def _save(c):
    os.makedirs(os.path.dirname(CACHE), exist_ok=True); json.dump(c, open(CACHE, "w"), indent=1, sort_keys=True)
def _iso(d):
    d = str(d or "").strip()
    if re.match(r"\d{8}$", d): return f"{d[:4]}-{d[4:6]}-{d[6:]}"
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", d)
    return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}" if m else d[:10]
def dod_from_271(j):
    s = json.dumps(j)
    hits = re.findall(r'"[A-Za-z]*[Dd]eath[A-Za-z]*"\s*:\s*"(\d{8})"', s) + re.findall(r"DTP\*442\*D8\*(\d{8})", s)
    return _iso(sorted(set(hits))[0]) if hits else None
def stedi_lookup(pid, dos_iso):
    """Medicare record for pid as of dos -> (dod or None, ok)."""
    import amd, requests
    t = amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"}), timeout=60)
    m = re.search(r'<patient [^>]*>', t); a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(0))) if m else {}
    if a.get("deceased") not in (None, "", "0"): return _iso(a.get("deceased")) if re.search(r"\d", a.get("deceased")) else dos_iso, True
    last, first = (a.get("name", "").split(",") + [""])[:2]; first = first.strip().split(" ")[0]
    mm = re.match(r"(\d\d)/(\d\d)/(\d{4})", a.get("dob", "")); dob8 = f"{mm.group(3)}{mm.group(1)}{mm.group(2)}" if mm else ""
    # 9/22/2026 (3pm ET run): the ehpa cloud environment carries the Stedi key as a proxy-attached credential (bootstrap net =
    # STEDI_CRED_OK, no key file) - a missing key file means send NO Authorization header and let the proxy add it (stedi.py does the same).
    try: key = open(KEYF).read().strip()
    except Exception: key = None
    body = {"tradingPartnerServiceId": "MBILUNOSSN", "provider": {"organizationName": "EFFINGER HEALTH PA", "npi": "1629515325"},
            "subscriber": {"firstName": first, "lastName": last.strip(), "dateOfBirth": dob8, "address": {"state": "FL"}},
            "encounter": {"dateOfService": dos_iso.replace("-", ""), "serviceTypeCodes": ["30"]}}
    try:
        hdr = {"Content-Type": "application/json"}
        if key: hdr["Authorization"] = key
        j = requests.post(STEDI, json=body, headers=hdr, timeout=60).json()
    except Exception: return None, False
    errs = [e.get("code") for e in j.get("errors", []) or []]
    return dod_from_271(j), (not errs or errs == ["72"])       # 72 = not a Medicare beneficiary: nothing to find, still a valid answer
def check(pid, dos, carrier=None, proc=None, allow_lookup=True):
    """-> (blocked: bool, reason: str). Blocks only on a known date of death earlier than the DOS."""
    pid = re.sub(r"\D", "", str(pid)); dos = _iso(dos); c = _load(); rec = c.get(pid)
    stale = rec is None or (datetime.date.today() - datetime.date.fromisoformat(rec.get("checked", "2000-01-01"))).days > MAX_AGE_DAYS
    needs = (carrier in MEDICARE) or ((proc or "") in CCM)
    if allow_lookup and needs and stale and not (rec and rec.get("dod")):
        dod, ok = stedi_lookup(pid, dos)
        if ok or dod:
            rec = {"dod": dod, "checked": datetime.date.today().isoformat(), "src": "stedi-medicare-271" if dod else "stedi: no death on record"}
            c[pid] = rec; _save(c)
        else: LOG.append(f"pat{pid} DOS {dos}: date of death UNVERIFIED (lookup failed)")
    dod = (rec or {}).get("dod")
    if dod and dos and dos > dod:
        return True, f"pat{pid} DOS {dos} is after date of death {dod} ({(rec or {}).get('src')}) - claim must not be submitted" + \
                     ("; CCM in the month of death needs a DOS on/before the death date, else void" if (proc or "") in CCM and dos[:7] == dod[:7] else "; void the charge")
    return False, ""
def check_charge(chargeid, sequencenumber=None, allow_lookup=True):
    """Reads the charge (patient, visit date, procedure, carrier at the billed sequence) and applies check()."""
    import resave
    import xml.etree.ElementTree as ET
    cid = re.sub(r"\D", "", str(chargeid)); d = ET.fromstring(resave.detail(cid))
    v = d.find(".//visit"); p = d.find(".//patient"); ch = [x for x in d.iter("charge") if x.get("id") == "charge" + cid]
    pid = re.sub(r"\D", "", p.get("id")) if p is not None else ""
    carrier = None
    if sequencenumber is not None:
        for ip in d.iter("insplan"):
            if str(ip.get("sequence")) == str(sequencenumber): carrier = ip.get("carrier")
    proc = ch[0].get("proccode") if ch else None
    return check(pid, v.get("date") if v is not None else "", carrier, proc, allow_lookup)
def record(pid, j, src="stedi-medicare-271"):
    """Store what a Medicare 271 says about death for pid (called by scripts/helpers/stedi.py on every Medicare lookup)."""
    pid = re.sub(r"\D", "", str(pid)); dod = dod_from_271(j); c = _load()
    errs = [e.get("code") for e in (j.get("errors") or [])]
    if dod or not errs or errs == ["72"]:
        c[pid] = {"dod": dod, "checked": datetime.date.today().isoformat(), "name": (c.get(pid) or {}).get("name"),
                  "src": src if dod else ("stedi: not a Medicare beneficiary" if errs == ["72"] else "stedi: no death on record")}
        _save(c)
    return dod
