# PLAIN ENGLISH (Claimocity feed reconciliation - William 11/1/2026: "this artifact should include all charges that show up in
#   claimocity feed and then show that all these have been entered into amd").
# For ONE ingest batch (stamp), pairs every message the feed carried (one message = one patient-day with its CPT lines) with what
#   AdvancedMD got: entered (visit + charge ids + fees), already in AMD (the dedupe found the visit on the chart), skipped (why:
#   date of death / diagnosis code not in AMD's list / unknown CPT), failed, or no chart (the patient could not be matched and no
#   chart was made - William's identity hold). Entered rows also carry the insurance cascade's verdict (RELEASE / HOLD + why).
# Writes registers/feed_recon_<stamp>.json - PHI-LIGHT: Claimocity patient id, AMD chart id, DOS, CPTs, dx codes, fees, visit and
#   charge ids, facility id, clinician key, file date. Never a name, DOB, member id or SSN (the parsed file that has them stays in
#   the workspace). The file is mirrored to main with the other registers and copied into the Claimocity Feed Monitoring page's
#   database (collection `batches`) by tools/feed/feed_db_payload.py.
# Inputs (workspace /home/claude/unbilled): feed_parsed_<stamp>.json (re-parsed from hl7/<stamp>/*.hl7 when missing),
#   feed_match_<stamp>.json (optional), registers/claimocity_patient_map.json, registers/feed_import_<stamp>.json,
#   registers/feed_verify_<stamp>.json, registers/feed_newcharts_<stamp>.json, registers/claimocity_ingest.json.
# Exit 0 written, 3 = no messages to reconcile (nothing parsed and no hl7 batch folder). Decides nothing; writes nothing in AMD.
# Usage: FEED_STAMP=<stamp> python3 claimocity_recon.py   |   python3 claimocity_recon.py <stamp> [--ws /home/claude/unbilled]
import os, sys, re, json, glob, subprocess, datetime, collections

a = sys.argv[1:]
def opt(name, default=None): return a[a.index(name) + 1] if name in a else default
WS = opt("--ws", "/home/claude/unbilled")
STAMP = next((x for x in a if re.match(r"^\d{8}T\d{4}Z(R?)$|^1028$|^dry\w+$", x)), None) or os.environ.get("FEED_STAMP")
if not STAMP: sys.exit("usage: claimocity_recon.py <stamp>  (or FEED_STAMP=<stamp>)")
os.chdir(WS)
HERE = os.path.dirname(os.path.abspath(__file__))

def load(p, default):
    try: return json.load(open(p))
    except Exception: return default
def iso(yyyymmdd):
    s = re.sub(r"\D", "", str(yyyymmdd or ""))[:8]
    return "%s-%s-%s" % (s[:4], s[4:6], s[6:8]) if len(s) == 8 else None
def mdy(yyyymmdd):
    s = re.sub(r"\D", "", str(yyyymmdd or ""))[:8]
    return "%s/%s/%s" % (s[4:6], s[6:8], s[:4]) if len(s) == 8 else None
def iso_from_mdy(s):
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", s or "")
    return "%s-%02d-%02d" % (m.group(3), int(m.group(1)), int(m.group(2))) if m else None
CLIN = {"EFFINGER WILLIAM": "Dr. Effinger (DO)", "GARCIA PAMELA": "Pamela G. (ARNP)", "GARLAND-G PAMELA": "Pamela G. (ARNP)"}
def clin(p):
    """clinician label without a surname the PHI gate could mistake for a patient's (the pseudonym map holds common surnames)"""
    if not p: return "Clinician on file"
    k = re.sub(r"[^A-Z ]", "", str(p).upper()).strip()
    if k in CLIN: return CLIN[k]
    parts = k.split(); return (parts[-1].title() + " " + parts[0][0] + ".") if len(parts) > 1 else parts[0].title()
def money(x):
    try: return round(float(str(x).replace("$", "").replace(",", "") or 0), 2)
    except Exception: return 0.0

# ---- the messages --------------------------------------------------------------------------------------------------------------------
pf = "feed_parsed_%s.json" % STAMP
parsed = load(pf, None)
if parsed is None:
    batch = os.path.join("hl7", STAMP)
    if glob.glob(os.path.join(batch, "*.hl7")):
        c = subprocess.run([sys.executable, "-I", os.path.join(WS, "feed_parse_dft_1028.py"), os.path.abspath(batch), pf], capture_output=True, text=True)
        parsed = load(pf, None)
    if parsed is None:
        print("recon %s: no parsed messages (no %s and no hl7/%s/*.hl7) - nothing to reconcile" % (STAMP, pf, STAMP)); sys.exit(3)

match = load("feed_match_%s.json" % STAMP, {})
pmap = load("registers/claimocity_patient_map.json", {})
IMPF = "registers/feed_import_%s.json" % STAMP
imp = load(IMPF, {"created": [], "skipped": [], "failed": []})
HAVE_IMPORT = os.path.exists(IMPF)
# visits a later void helper removed (duplicates William approved voiding): their rows read 'voided', not 'entered'
voided = {}
for e in load("registers/feed_void_visits.json", []):
    if e.get("mode") == "live" or any(c.get("ok") for c in e.get("charges") or []): voided[e.get("vid")] = e.get("why") or "voided"
verify = load("registers/feed_verify_%s.json" % STAMP, {})
newcharts = {c.get("pid"): c.get("chart") for c in load("registers/feed_newcharts_%s.json" % STAMP, {}).get("created", [])}
reg = load("registers/claimocity_ingest.json", {"files": {}, "runs": []})

created_by_key = {}
for c in imp.get("created", []):
    created_by_key.setdefault((c.get("feed_id"), c.get("dos"), tuple(sorted(c.get("cpts") or []))), []).append(c)
skipped_by_fid = collections.defaultdict(list)
for s in imp.get("skipped", []): skipped_by_fid[s.get("feed_id")].append(s)
failed_by_fid = collections.defaultdict(list)
for f in imp.get("failed", []): failed_by_fid[f.get("feed_id")].append(f)
resolved = {}
for k, v in match.items():
    if v.get("resolved"):
        for fid in v.get("feed_ids", []): resolved[fid] = v["resolved"]

def skip_kind(why):
    w = (why or "").lower()
    if "death" in w or "deceased" in w: return "deceased"
    if "no usable dx" in w: return "dx"
    if "unknown cpt" in w: return "cpt"
    if "already" in w: return "already"
    return "skipped"

rows = []
for m in parsed:
    fid = m.get("pid"); ft = m.get("FT1") or []
    if not ft: continue
    dos = ft[0].get("dos"); cpts = [l.get("cpt") for l in ft if l.get("cpt")]
    dx = sorted({x.strip() for l in ft for x in (l.get("dx") or "").split("^") if x.strip()})
    key = (fid, mdy(dos), tuple(sorted(cpts)))
    row = {"f": fid, "d": iso(dos), "c": cpts, "dx": dx, "file": str(m.get("file") or "")[:8], "prov": clin(m.get("provider")), "u": sum(int(l.get("units") or 1) for l in ft)}
    pid = resolved.get(fid) or pmap.get(fid)
    hit = created_by_key.get(key)
    if hit:
        c = hit.pop(0)
        row.update({"s": "entered", "p": c.get("pid"), "v": c.get("visit"), "ch": c.get("charges") or [], "fee": round(sum(money(x) for x in c.get("fees") or []), 2),
                    "fac": c.get("fac") or "", "pos": c.get("pos") or "", "admit": iso(c.get("admit")) if c.get("admit") else None})
        ver = verify.get(c.get("pid")) or {}
        if ver:
            lead = (ver.get("lead") or {}).get("code") if isinstance(ver.get("lead"), dict) else None
            row["lead"] = lead or ""
            row["verdict"] = ver.get("decision") or ""
            holds = ver.get("hold") or []
            if holds:
                txt = "; ".join(h if isinstance(h, str) else json.dumps(h) for h in holds)
                txt = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[SSN]", txt); txt = re.sub(r"(date of death)\s+\d{4}-\d{2}-\d{2}", r"\1 [date]", txt)
                row["hold"] = txt[:240]
        if c.get("pid") in newcharts: row["newchart"] = newcharts[c.get("pid")]
        if c.get("visit") in voided: row["s"] = "voided"; row["why"] = ("voided after entry: " + voided[c.get("visit")])[:200]
    elif not HAVE_IMPORT:
        row.update({"s": "unrecorded", "p": pid, "why": "this batch's import register is not on main - outcome not recorded (the September files the old integration had already posted)"})
    elif skipped_by_fid.get(fid):
        s = skipped_by_fid[fid].pop(0)
        why = s.get("why") or ""; why = re.sub(r"(date of death)\s+\d{4}-\d{2}-\d{2}", r"\1 [date]", why)
        row.update({"s": skip_kind(why), "p": s.get("pid") or pid, "why": why[:200]})
    elif failed_by_fid.get(fid):
        f = failed_by_fid[fid].pop(0)
        row.update({"s": "failed", "p": f.get("pid") or pid, "why": re.sub(r"\s+", " ", (f.get("err") or f.get("why") or ""))[:200]})
    elif pid:
        row.update({"s": "already", "p": pid, "why": "visit already on the chart (same CPT and date) - not entered twice"})
    else:
        res = next((v.get("resolution") for v in match.values() if fid in (v.get("feed_ids") or [])), None)
        row.update({"s": "nochart", "p": None, "why": ("no AdvancedMD chart matched: " + (res or "patient not found by name and date of birth"))[:200]})
    rows.append(row)

counts = collections.Counter(r["s"] for r in rows)
files = [{"name": k, "date": (re.match(r"\d{8}", k) or re.match(r"", k)).group(0), "messages": v.get("messages")} for k, v in reg.get("files", {}).items() if v.get("stamp") == STAMP]
if not files:
    files = [{"name": d, "date": d, "messages": n} for d, n in sorted(collections.Counter(r["file"] for r in rows).items())]
run = next((r for r in reversed(reg.get("runs", [])) if r.get("stamp") == STAMP and r.get("live")), None) or next((r for r in reversed(reg.get("runs", [])) if r.get("stamp") == STAMP), None) or {}
dates = sorted(r["d"] for r in rows if r.get("d"))
out = {"schema": "feed-recon/1", "stamp": STAMP, "built": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
       "at": run.get("at"), "live": run.get("live"), "files": files, "dmin": dates[0] if dates else None, "dmax": dates[-1] if dates else None,
       "counts": {"messages": len(rows), "entered": counts["entered"], "lines": sum(len(r["c"]) for r in rows if r["s"] == "entered"),
                  "dollars": round(sum(r.get("fee") or 0 for r in rows if r["s"] == "entered"), 2), "already": counts["already"], "deceased": counts["deceased"],
                  "dx": counts["dx"], "cpt": counts["cpt"], "skipped": counts["skipped"], "failed": counts["failed"], "nochart": counts["nochart"], "voided": counts["voided"], "unrecorded": counts["unrecorded"],
                  "new_charts": len(newcharts), "holds": sum(1 for r in rows if r.get("hold"))},
       "rows": rows}
os.makedirs("registers", exist_ok=True)
json.dump(out, open("registers/feed_recon_%s.json" % STAMP, "w"), indent=0, separators=(",", ":"))
c = out["counts"]
print("recon %s: %d messages -> %d entered ($%.2f, %d lines), %d already in AMD, %d not entered (deceased %d, dx %d, cpt %d, other %d, failed %d), %d no chart, %d insurance holds -> registers/feed_recon_%s.json" % (
    STAMP, c["messages"], c["entered"], c["dollars"], c["lines"], c["already"], c["deceased"] + c["dx"] + c["cpt"] + c["skipped"] + c["failed"], c["deceased"], c["dx"], c["cpt"], c["skipped"], c["failed"], c["nochart"], c["holds"], STAMP))
