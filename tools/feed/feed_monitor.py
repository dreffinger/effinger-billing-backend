#!/usr/bin/env python3
# PLAIN ENGLISH (Claimocity feed monitoring data - William 10/29/2026: "make an artifact called claimocity feed monitoring and give a
#   summary of the claimocity feed encounters on the past week and month in categories").
# Reads the PHI-light feed registers the ingest writes (registers/feed_import_<stamp>.json, feed_verify_<stamp>.json,
#   feed_newcharts_<stamp>.json, claimocity_ingest.json) plus, when they exist in the workspace, the parsed feed files
#   (feed_parsed_<stamp>.json - names stay out; only diagnosis codes, the clinician and the file date are used) and the practice's
#   facilities.json / carriers_rich.json, and writes ONE aggregate file with no patient names, member ids or dates of birth:
#   reports/feed/feed_monitor.json - encounters, visits, charge lines and dollars by day, by service category (hospital / SNF /
#   CCM / ACP / home), by facility, by clinician, by lead payer, by AdvancedMD outcome (entered / already there / held / deceased /
#   failed), the open holds (chart ids only), the ingest runs and the files on hand - for three windows: the past 7 days, the past
#   30 days and everything on hand. The "Claimocity feed monitoring" page (https://claude.ai/artifact/<id>) draws this file from
#   GitHub main; the Billing Button's feed step and the daily feed task run this script after every ingest and commit the file.
# Writes nothing anywhere else. Usage: python3 feed_monitor.py [--ws /home/claude/unbilled] [--repo /home/claude/effinger-billing-backend]
#   [--out <repo>/reports/feed/feed_monitor.json] [--as-of YYYY-MM-DD]
import os, sys, json, glob, re, collections, datetime

def opt(name, default=None):
    a = sys.argv[1:]
    return a[a.index(name) + 1] if name in a else default

WS = opt("--ws", "/home/claude/unbilled")
REPO = opt("--repo", "/home/claude/effinger-billing-backend")
OUT = opt("--out", os.path.join(REPO, "reports", "feed", "feed_monitor.json"))
AS_OF = opt("--as-of", datetime.date.today().isoformat())
today = datetime.date.fromisoformat(AS_OF)

def load(p, default):
    try:
        return json.load(open(p))
    except Exception:
        return default

def mdy_to_date(s):
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", s or "")
    if m: return datetime.date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
    m = re.match(r"(\d{4})-?(\d{2})-?(\d{2})", s or "")
    if m: return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None

# ---- practice lookups -------------------------------------------------------------------------------------------------------------
FAC = load(os.path.join(REPO, "practices", "ehpa", "facilities.json"), {})
if not FAC: FAC = load(os.path.join(WS, "facilities.json"), {})
CAR = load(os.path.join(WS, "carriers_rich.json"), {}) or load(os.path.join(REPO, "practices", "ehpa", "carriers.json"), {})
CODE2NAME = {v[0]: v[1] for v in CAR.values() if isinstance(v, list) and len(v) > 1}

FAC_SHORTALL = {"fac29": "HCA Capital Hospital", "fac34": "Brynwood (Monticello)", "fac33": "Centre Pointe Health & Rehab", "fac58": "Westminster Bertrand",
             "fac32": "Aspire at Tallahassee", "fac1350": "Oakes Southwood"}
def fac_name(fid):
    if fid in FAC_SHORTALL: return FAC_SHORTALL[fid]
    n = FAC.get(fid) if isinstance(FAC, dict) else None
    if not n: return fid or "unknown facility"
    n = re.sub(r"\s*\((TALLAHASSEE|MONTICELLO|QUINCY|CRAWFORDVILLE)\)\s*$", "", n)
    words = n.split(); half = len(words) // 2
    if half and words[:half] == words[half:2 * half]: words = words[:half]          # AMD doubles some names: "X LLC X LLC"
    n = " ".join(w for w in words if w.upper() not in ("LLC", "INC", "LP"))
    n = n.title().replace("Alf", "ALF").replace("Snf", "SNF").replace("Hca", "HCA").replace("Tmh", "TMH").replace(" And ", " & ")
    return n[:40]

POS_NAME = {"21": "Inpatient hospital", "22": "Outpatient hospital", "23": "Emergency room", "31": "Skilled nursing facility", "32": "Nursing facility",
            "13": "Assisted living", "12": "Home", "11": "Office", "33": "Custodial care", "34": "Hospice", "14": "Group home", "19": "Off-campus outpatient",
            "61": "Inpatient rehab"}      # 11/25/2026 (William): the visits of the hospital's rehabilitation unit go out at 61

def service(cpt):
    c = (cpt or "").upper()
    if c in ("99221", "99222", "99223"): return "Hospital admission"
    if c in ("99231", "99232", "99233"): return "Hospital follow-up"
    if c in ("99238", "99239"): return "Hospital discharge"
    if c in ("99234", "99235", "99236"): return "Observation same-day"
    if c in ("99281", "99282", "99283", "99284", "99285"): return "Emergency visit"
    if c in ("99304", "99305", "99306"): return "SNF admission"
    if c in ("99307", "99308", "99309", "99310"): return "SNF follow-up"
    if c in ("99315", "99316"): return "SNF discharge"
    if c in ("99341", "99342", "99344", "99345", "99347", "99348", "99349", "99350"): return "Home / ALF visit"
    if c in ("99487", "99489", "99490", "99491", "99437", "99439", "G0506"): return "Chronic care management"
    if c in ("99497", "99498"): return "Advance care planning"
    if c in ("G0438", "G0439", "G0402"): return "Annual wellness"
    if c in ("99495", "99496"): return "Transitional care"
    if c in ("99358", "99359", "G2211", "G0136"): return "Prolonged / add-on"
    return "Other"

SERVICE_ORDER = ["Hospital admission", "Hospital follow-up", "Hospital discharge", "Observation same-day", "Emergency visit", "SNF admission",
                 "SNF follow-up", "SNF discharge", "Home / ALF visit", "Chronic care management", "Advance care planning", "Annual wellness",
                 "Transitional care", "Prolonged / add-on", "Other"]

MA_CODES = {"HUM01", "UNI20", "CAP07", "UHCMA", "WEL04", "AET12", "AET07", "CIG13", "DEV01", "CPL01", "FBM01"}
MEDICAID_CODES = {"FLO99", "FCC", "SUN01", "SIM01", "MCAD", "MOL01", "STA01", "HUMMD"}
def payer_cat(code):
    if not code: return "No active plan"
    c = code.upper(); n = (CODE2NAME.get(code) or "").upper()
    if c in MA_CODES or re.search(r"ADVANTAGE|DUAL COMPLETE|MEDICARE HMO|MEDICARE PPO|CAREPLUS|DEVOTED|WELLCARE", n): return "Medicare Advantage"
    if c in MEDICAID_CODES or re.search(r"MEDICAID|MCD|COMMUNITY CARE|SUNSHINE STATE|SIMPLY|MOLINA|STAYWELL|LTC", n): return "Medicaid / LTC"
    if c in ("MC", "FLO02", "MCR") or re.search(r"\bMEDICARE\b", n): return "Medicare"
    if c in ("VACCN", "TRI05", "TRI01") or re.search(r"\bVA\b|VETERAN|TRICARE|CCN", n): return "VA / TRICARE"
    return "Commercial / other"
PAYER_ORDER = ["Medicare", "Medicare Advantage", "Medicaid / LTC", "Commercial / other", "VA / TRICARE", "No active plan"]

# clinician labels carry no surname that the PHI gate could mistake for a patient's (the pseudonym map holds common surnames)
CLINICIAN = {"EFFINGER WILLIAM": "Dr. Effinger (DO)", "GARLAND-G PAMELA": "Pamela G. (ARNP)"}
def clinician_label(p):
    if not p: return "Clinician on file"
    k = re.sub(r"[^A-Z ]", "", p.upper()).strip()
    if k in CLINICIAN: return CLINICIAN[k]
    parts = k.split()
    return (parts[-1].title() + " " + parts[0][0] + ".") if len(parts) > 1 else parts[0].title()

def money(x):
    try: return round(float(str(x).replace("$", "").replace(",", "") or 0), 2)
    except Exception: return 0.0

# ---- gather every batch -----------------------------------------------------------------------------------------------------------
reg = load(os.path.join(WS, "registers", "claimocity_ingest.json"), {"files": {}, "runs": []})
stamps = sorted({re.sub(r"^feed_import_|\.json$", "", os.path.basename(p)) for p in glob.glob(os.path.join(WS, "registers", "feed_import_*.json"))})
visits = []      # one per created visit: {date, pid, visit, cpts, fees, fac, pos, stamp, provider, dx}
already = []     # skipped as already in AMD
other_skips = [] # skipped for another reason (unknown CPT, no chart)
deceased = []    # skipped for a date of death
failed = []
newcharts = 0
dx_by_feed, prov_by_feed, filedate_by_feed = {}, {}, {}
for st in stamps:
    for m in load(os.path.join(WS, "feed_parsed_%s.json" % st), []):   # workspace only; absent on a fresh container
        fid = m.get("pid")
        dx_by_feed.setdefault(fid, []).extend([l.get("dx") for l in m.get("FT1", []) if l.get("dx")] + list(m.get("DG1") or []))
        prov_by_feed[fid] = m.get("provider") or prov_by_feed.get(fid)
        filedate_by_feed[fid] = m.get("file")
    imp = load(os.path.join(WS, "registers", "feed_import_%s.json" % st), {})
    for c in imp.get("created", []):
        d = mdy_to_date(c.get("dos"))
        if not d: continue
        visits.append({"date": d, "pid": c.get("pid"), "visit": c.get("visit"), "cpts": c.get("cpts", []), "fees": [money(f) for f in c.get("fees", [])],
                       "fac": c.get("fac", ""), "pos": c.get("pos", ""), "stamp": st, "feed_id": c.get("feed_id"),
                       "provider": prov_by_feed.get(c.get("feed_id")), "dx": dx_by_feed.get(c.get("feed_id"), [])})
    for s in imp.get("skipped", []):
        why = (s.get("why") or "").lower()
        row = {"pid": s.get("pid"), "why": s.get("why"), "stamp": st, "feed_id": s.get("feed_id"), "date": mdy_to_date(s.get("dos"))}
        (deceased if "death" in why or "deceased" in why else (already if "already" in why else other_skips)).append(row)
    for f in imp.get("failed", []):
        failed.append({"pid": f.get("pid"), "why": (f.get("why") or f.get("err") or "")[:160], "stamp": st})
    nc = load(os.path.join(WS, "registers", "feed_newcharts_%s.json" % st), {})
    newcharts += len(nc.get("created", []))

verify = {}
for st in stamps:
    verify.update(load(os.path.join(WS, "registers", "feed_verify_%s.json" % st), {}) or {})
lead_by_pid = {pid: ((v.get("lead") or {}).get("code")) for pid, v in verify.items()}
holds = []
for pid, v in verify.items():
    for h in v.get("hold") or []:
        txt = h if isinstance(h, str) else json.dumps(h)
        txt = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[SSN]", txt)
        txt = re.sub(r"(date of death)\s+\d{4}-\d{2}-\d{2}", r"\1 [date]", txt)   # the date itself stays in the workspace registers
        holds.append({"pid": pid, "why": txt[:220], "dos": (v.get("dos") or [""])[-1], "kind": "deceased" if "death" in txt.lower() else ("payer" if "CMS reports" in txt or "primary" in txt.lower() else "facesheet")})
verif_status = collections.Counter()
for v in verify.values():
    sts = [c.get("status") for c in v.get("checks") or []]
    verif_status["active plan verified" if "ACTIVE" in sts else ("inactive only" if sts else "no plan to check")] += 1

# ---- aggregate --------------------------------------------------------------------------------------------------------------------
def agg(rows, deceased_rows, already_rows, lo, hi):
    def inwin(d): return d is not None and lo <= d <= hi
    rs = [r for r in rows if inwin(r["date"])]
    dec = [r for r in deceased_rows if r.get("date") is None or inwin(r["date"])] if rows else deceased_rows
    alr = [r for r in already_rows if r.get("date") is None or inwin(r["date"])] if rows else already_rows
    out = {"from": lo.isoformat(), "to": hi.isoformat(), "visits": len(rs), "lines": sum(len(r["cpts"]) for r in rs),
           "dollars": round(sum(sum(r["fees"]) for r in rs), 2), "patients": len({r["pid"] for r in rs}),
           "entered": len(rs), "already_in_amd": len(alr), "deceased_not_entered": len(dec), "failed": len(failed) if rows else 0,
           "skipped_other": len(other_skips) if rows else 0, "skipped_other_why": sorted({(r.get("why") or "")[:60] for r in other_skips})[:5]}
    def table(keyf, order=None, per="lines"):
        cnt, dol, vis = collections.Counter(), collections.Counter(), collections.Counter()
        for r in rs:
            seen = set()
            for cpt, fee in zip(r["cpts"], r["fees"] + [0.0] * (len(r["cpts"]) - len(r["fees"]))):
                k = keyf(r, cpt); cnt[k] += 1; dol[k] += fee
                if k not in seen: vis[k] += 1; seen.add(k)
        keys = sorted(cnt, key=lambda k: ((order.index(k) if order and k in order else 999), -cnt[k]))
        return [{"name": k, "lines": cnt[k], "visits": vis[k], "dollars": round(dol[k], 2)} for k in keys]
    out["service"] = table(lambda r, c: service(c), SERVICE_ORDER)
    out["cpt"] = table(lambda r, c: c)
    out["facility"] = table(lambda r, c: fac_name(r["fac"]))
    out["setting"] = table(lambda r, c: POS_NAME.get(r["pos"], "POS " + (r["pos"] or "?")))
    out["clinician"] = table(lambda r, c: clinician_label(r.get("provider")))
    out["payer"] = table(lambda r, c: payer_cat(lead_by_pid.get(r["pid"])), PAYER_ORDER)
    dxc = collections.Counter(d for r in rs for d in set(r.get("dx") or []))
    out["top_dx"] = [{"code": k, "patients": n} for k, n in dxc.most_common(12)]
    by_day = collections.defaultdict(lambda: {"visits": 0, "lines": 0, "dollars": 0.0, "patients": set()})
    for r in rs:
        d = by_day[r["date"].isoformat()]; d["visits"] += 1; d["lines"] += len(r["cpts"]); d["dollars"] += sum(r["fees"]); d["patients"].add(r["pid"])
    days = []
    d = lo
    while d <= hi:
        k = d.isoformat(); e = by_day.get(k)
        days.append({"date": k, "visits": e["visits"] if e else 0, "lines": e["lines"] if e else 0, "dollars": round(e["dollars"], 2) if e else 0.0, "patients": len(e["patients"]) if e else 0})
        d += datetime.timedelta(days=1)
    out["days"] = days
    return out

dates = [r["date"] for r in visits]
dos_min, dos_max = (min(dates), max(dates)) if dates else (today, today)
windows = {
    "week": agg(visits, deceased, already, today - datetime.timedelta(days=6), today),
    "month": agg(visits, deceased, already, today - datetime.timedelta(days=29), today),
    "all": agg(visits, deceased, already, dos_min, max(dos_max, today)),
}
files = sorted(({"name": k, "date": (re.match(r"\d{8}", k) or re.match(r"", k)).group(0), "stamp": v.get("stamp"), "messages": v.get("messages"), "at": v.get("at")}
                for k, v in reg.get("files", {}).items()), key=lambda f: f["name"])
coverage = {"files": files, "file_count": len(files), "first_file": files[0]["date"] if files else None, "last_file": files[-1]["date"] if files else None,
            "dos_min": dos_min.isoformat() if dates else None, "dos_max": dos_max.isoformat() if dates else None, "batches": stamps,
            "note": ("Feed files on hand start 10/16/2026: the old integration consumed the earlier files on the SFTP, so those encounters live in "
                     "AdvancedMD only. Days with no bar inside the window are days with no feed encounter on hand, not necessarily days without visits.")}
runs = [{"stamp": r.get("stamp"), "at": r.get("at"), "files": len(r.get("files") or []), "exit": r.get("exit"), "live": r.get("live")} for r in reg.get("runs", [])][-12:]
data = {"schema": "feed-monitor/1", "generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "as_of": AS_OF,
        "coverage": coverage, "windows": windows, "holds": sorted(holds, key=lambda h: (h["kind"], h["pid"])), "runs": runs,
        "totals": {"visits": len(visits), "lines": sum(len(r["cpts"]) for r in visits), "dollars": round(sum(sum(r["fees"]) for r in visits), 2),
                   "patients": len({r["pid"] for r in visits}), "new_charts": newcharts, "already_in_amd": len(already), "deceased_not_entered": len(deceased),
                   "failed": len(failed), "skipped_other": len(other_skips), "holds": len(holds), "verification": dict(verif_status)},
        "button": {"trigger": "trig_01S771Si8VJ8DvcwgHMHGYB5", "page": "https://claude.ai/artifact/5Eyw5K3ydS13uDHkR8JJyZ"}}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(data, open(OUT, "w"), indent=1)
w = windows["week"]; m = windows["month"]
print("feed monitor -> %s | week %d visits / $%.2f, month %d visits / $%.2f, all %d visits / $%.2f, %d holds, %d files on hand" % (
    OUT, w["visits"], w["dollars"], m["visits"], m["dollars"], len(visits), data["totals"]["dollars"], len(holds), len(files)))
