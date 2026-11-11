#!/usr/bin/env python3
# PLAIN ENGLISH (CCM documentation hub - William 11/11/2026: "do all the notes and give me buttons to sign off on all of them"; "do patient
#   level data on the neon database but also have an artifact pull from that and have patient data on it which is ok").
# Decides: nothing about a charge. It builds every chronic-care-management note from what the practice's Neon database already holds:
#   every CCM charge line ever billed (amd.charges - the AdvancedMD history pulled 11/10/2026, void lines left out), the insurance plan in
#   force that month (amd.chart_plans), and the name and birth date ccm_patients.py read (workspace ccm/ccm_patients.jsonl). One record per
#   patient per calendar month, with the note's fields and flags from scripts/helpers/ccm_notes.py (the single place the statements, the
#   flags and the signing rules live).
# What it writes (files only - the database is written through its one door, tools/db/neon_db.py load-docs, and the hub page through the
#   ArtifactData tool):
#   <out>/neon/patients/<chart>.json, <out>/neon/months/<chart>_<YYYY-MM>.json  -> python3 tools/db/neon_db.py load-docs --src <out>/neon --source ccm
#   <out>/hub/config/practice.json, <out>/hub/notes/<YYYY-MM>-<n>.json         -> the hub page's own database (collections config and notes)
#   <out>/signed/signed/<chart>_<YYYY-MM>.json (command signatures)              -> python3 tools/db/neon_db.py load-docs --src <out>/signed --source ccm
# What it never does: write to Neon or to AdvancedMD itself (it sends SELECT statements only - anything else is refused before it leaves);
#   rebuild a month whose note is signed (a signed note is final - the database refuses the change too); record a signing it cannot verify
#   against the stored draft (the hash of the note he saw, the day written, who and when - ccm_notes.verify_signature); put patient data in
#   the repository (it refuses an output folder inside the checkout).
# Usage:
#   python3 scripts/helpers/ccm_build.py charts                         write ccm/ccm_charts.json (the charts with a CCM charge) for ccm_patients.py
#   python3 scripts/helpers/ccm_build.py plan                           counts only: patient-months, ready / flagged / no name yet
#   python3 scripts/helpers/ccm_build.py build --out <dir>              the documents above
#   python3 scripts/helpers/ccm_build.py signatures --page <dir> --out <dir> [--via <hub page url>]
#        <dir> = what ArtifactData list wrote with out_dir for the hub page's collection "signatures"; each signing is checked against the
#        draft in Neon; good ones become signed/<id>.json, the others are listed with the reason (nothing is signed in his name otherwise).
# Reads NEON_DATABASE_URL (Neon's HTTPS SQL route, as tools/db/neon_db.py does when port 5432 is closed); the workspace is BILLING_WORKSPACE
#   (default /home/claude/unbilled).
# Self-test: python3 tools/selftest/test_ccm_build.py
import os, sys, re, json, hashlib, datetime, collections, urllib.request, urllib.parse
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ccm_notes as N
REPO = os.path.dirname(os.path.dirname(HERE))
CODES = N.CCM_CODES
PROVIDERS = {N.SIGNER_CODE: N.SIGNER}      # AdvancedMD provider profile -> the name on the note (others keep their profile code)
PER_DOC = 150                               # notes per hub document (a page's database document holds at most 256 KiB)
LINES_SQL = ("select c.chart_id, c.charge_id, c.visit_id, c.dos::text, c.cpt, "
             "coalesce((select max(d.units) from amd.charge_details d where d.chart_id = c.chart_id and d.charge_id = c.charge_id), 1)::text, "
             "coalesce(c.provider, ''), coalesce(c.facility, '') from amd.charges c where not c.void and c.cpt in (%s) "
             "order by c.chart_id, c.dos, c.cpt, c.charge_id")
PLANS_SQL = ("select p.chart_id, coalesce(p.carrier_name, ''), coalesce(p.begin_date::text, ''), coalesce(p.end_date::text, ''), coalesce(p.sequence, '') "
             "from amd.chart_plans p where p.chart_id in (select distinct chart_id from amd.charges where not void and cpt in (%s))")
SIGNED_SQL = "select doc_id from raw.documents where source = 'ccm' and collection = 'signed'"
DRAFTS_SQL = "select doc_id, body from raw.documents where source = 'ccm' and collection = 'months' and doc_id = any(string_to_array(%s, ','))"

def neon_select(sql, params=()):
    """one SELECT over Neon's HTTPS SQL route; rows as lists of text. Anything but a SELECT is refused here."""
    if not re.match(r"^\s*(select|with)\b", sql, re.I) or ";" in sql.rstrip().rstrip(";"): raise ValueError("ccm_build reads only: one SELECT statement")
    u = re.sub(r"\s+", "", os.environ.get("NEON_DATABASE_URL") or os.environ.get("DATABASE_URL") or "")
    if not u.startswith("postgres"): raise SystemExit("ccm_build: NEON_DATABASE_URL is not set")
    n = [0]
    def ph(m): n[0] += 1; return "$%d" % n[0]
    body = json.dumps({"query": re.sub(r"%s", ph, sql), "params": [None if p is None else str(p) for p in params]}).encode("utf-8")
    req = urllib.request.Request("https://%s/sql" % urllib.parse.urlparse(u).hostname, data=body, method="POST",
                                 headers={"Neon-Connection-String": u, "Content-Type": "application/json", "Neon-Array-Mode": "true", "Neon-Raw-Text-Output": "true"})
    with urllib.request.urlopen(req, timeout=180) as r: return json.loads(r.read().decode("utf-8")).get("rows") or []
def _codes(): return ", ".join("'%s'" % c for c in CODES)
def _ws(): return os.path.abspath(os.environ.get("BILLING_WORKSPACE") or "/home/claude/unbilled")
def _inside_repo(p): p = os.path.abspath(p); return p == REPO or p.startswith(REPO + os.sep)
def _write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f: json.dump(obj, f, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
def _now(): return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def charge_lines(select):
    """every live CCM charge line, shaped for ccm_notes.months()"""
    return [{"chart": r[0], "charge": r[1] or "", "visit": r[2] or "", "dos": r[3], "code": r[4], "units": r[5] or "1",
             "provider_code": r[6], "provider": PROVIDERS.get(r[6], r[6]), "facility": r[7]} for r in select(LINES_SQL % _codes())]
def plans_by_chart(select):
    by = collections.defaultdict(list)
    for chart, name, begin, end, seq in select(PLANS_SQL % _codes()): by[chart].append((name, begin, end, seq))
    return by
def insurance_for(plans, ym):
    """the plan in force during the month with the lowest billing sequence; "" when none was"""
    first = datetime.date(int(ym[:4]), int(ym[5:7]), 1)
    last = (first.replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1)
    live = []
    for name, begin, end, seq in plans:
        b = N._day(begin) if begin else None; e = N._day(end) if end else None
        if (b is None or b <= last) and (e is None or e >= first) and name:
            live.append((int(seq) if str(seq).isdigit() else 99, name))
    return min(live)[1] if live else ""
def read_patients(ws):
    p = os.path.join(ws, "ccm", "ccm_patients.jsonl"); out = {}
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            try: j = json.loads(line)
            except ValueError: continue
            if j.get("chart") and not j.get("error"): out[j["chart"]] = j
    return out
def build_months(select, patients):
    """(records, signed ids). A record: the months() record + insurance + patient + fields + fields_sha + status."""
    plans = plans_by_chart(select); signed = {r[0] for r in select(SIGNED_SQL)}
    recs = []
    for m in N.months(charge_lines(select), signer=N.SIGNER_CODE):
        m = dict(m, insurance=insurance_for(plans.get(m["chart"], []), m["month"]))
        pt = patients.get(m["chart"]) or {}
        f = N.note_fields(m, pt, None, [])
        status = "flagged" if m["flag"] else ("no name yet" if not (pt.get("name") and pt.get("dob")) else "ready to sign")
        recs.append(dict(m, id="%s_%s" % (m["chart"], m["month"]), patient=pt, fields=f, fields_sha=hashlib.sha256(N.canon(f).encode("utf-8")).hexdigest(), status=status))
    return recs, signed
def month_doc(r, at):
    return {"chart": r["chart"], "month": r["month"], "codes": r["codes"], "counts": r["counts"], "minutes": r["minutes"], "statement": r["statement"],
            "flag": r["flag"], "insurance": r["insurance"], "fields": r["fields"], "fields_sha": r["fields_sha"], "_written": at,
            "charges": [{"charge": c["charge"], "visit": c["visit"], "dos": c["dos"], "code": c["code"], "units": str(c.get("units") or "1"),
                         "provider": c["provider_code"], "facility": c["facility"]} for c in r["charges"]]}
def hub_docs(recs, signed, at):
    """the hub page's documents: config/practice and notes/<YYYY-MM>-<n> (the statement is stored once per document)"""
    by = collections.OrderedDict()
    for r in sorted(recs, key=lambda r: (r["month"], r["fields"]["patient"] or "~", r["chart"])): by.setdefault(r["month"], []).append(r)
    docs = {}; months = []
    for ym, rs in sorted(by.items(), reverse=True):
        parts = [rs[i:i + PER_DOC] for i in range(0, len(rs), PER_DOC)]
        for k, part in enumerate(parts, 1):
            st = {}; notes = []
            for r in part:
                key = str(r["minutes"] or "")
                if key: st[key] = r["fields"]["statement"]
                notes.append({"id": r["id"], "f": {k2: v for k2, v in r["fields"].items() if k2 != "statement"}, "m": key, "flag": r["flag"],
                              "status": "signed" if r["id"] in signed else r["status"]})
            docs["notes/%s-%d" % (ym, k)] = {"month": ym, "part": k, "parts": len(parts), "statements": st, "notes": notes, "built_at": at}
        c = collections.Counter(("signed" if r["id"] in signed else r["status"]) for r in rs)
        months.append({"month": ym, "name": N.month_name(ym), "parts": len(parts), "notes": len(rs), "ready": c["ready to sign"], "flagged": c["flagged"], "noname": c["no name yet"], "signed": c["signed"]})
    tot = collections.Counter(("signed" if r["id"] in signed else r["status"]) for r in recs)
    docs["config/practice"] = {"practice": N.PRACTICE_NAME, "letterhead": list(N.LETTERHEAD), "phone": N.PHONE, "fax": N.FAX, "signer": N.SIGNER, "signer_code": N.SIGNER_CODE,
                               "built_at": at, "months": months, "counts": {"notes": len(recs), "ready": tot["ready to sign"], "flagged": tot["flagged"], "noname": tot["no name yet"], "signed": tot["signed"]}}
    return docs

def main(argv=None, select=None):
    a = list(sys.argv[1:] if argv is None else argv); select = select or neon_select
    cmd = a[0] if a else ""
    def opt(k): return a[a.index(k) + 1] if k in a and a.index(k) + 1 < len(a) else None
    ws = _ws()
    if cmd == "charts":
        if _inside_repo(ws): print("ccm_build: the workspace %s is inside the repository - set BILLING_WORKSPACE" % ws); return 2
        charts = [r[0] for r in select("select distinct chart_id from amd.charges where not void and cpt in (%s) order by 1" % _codes())]
        _write(os.path.join(ws, "ccm", "ccm_charts.json"), {"charts": charts, "_written": _now()})
        print("ccm_build: %d charts with a CCM charge -> %s" % (len(charts), os.path.join(ws, "ccm", "ccm_charts.json"))); return 0
    if cmd in ("plan", "build"):
        recs, signed = build_months(select, read_patients(ws))
        c = collections.Counter(("signed" if r["id"] in signed else r["status"]) for r in recs)
        print("ccm_build: %d patient-months (%d charts, %s to %s): %d ready to sign, %d flagged, %d waiting for the patient's name, %d signed" % (
            len(recs), len({r["chart"] for r in recs}), min((r["month"] for r in recs), default="-"), max((r["month"] for r in recs), default="-"),
            c["ready to sign"], c["flagged"], c["no name yet"], c["signed"]))
        if cmd == "plan": return 0
        out = opt("--out")
        if not out: print("ccm_build: build needs --out <dir>"); return 2
        if _inside_repo(out): print("ccm_build: %s is inside the repository - patient data never goes there" % out); return 2
        at = _now(); pts = read_patients(ws); n = 0
        for chart in sorted({r["chart"] for r in recs} & set(pts)):
            p = pts[chart]; _write(os.path.join(out, "neon", "patients", chart + ".json"), {"chart": chart, "name": p.get("name", ""), "dob": p.get("dob", ""), "sex": p.get("sex", ""), "read_at": p.get("read_at", ""), "_written": at})
        for r in recs:
            if r["id"] in signed: continue      # a signed month is final
            _write(os.path.join(out, "neon", "months", r["id"] + ".json"), month_doc(r, at)); n += 1
        hub = hub_docs(recs, signed, at)
        for k, v in hub.items(): _write(os.path.join(out, "hub", k + ".json"), v)
        print("ccm_build: wrote %d month records (%d signed months left as they are) and %d hub documents under %s" % (n, len(signed & {r["id"] for r in recs}), len(hub), out)); return 0
    if cmd == "signatures":
        page, out, via = opt("--page"), opt("--out"), opt("--via") or ""
        if not (page and out) or _inside_repo(out): print("ccm_build: signatures needs --page <dir> and --out <dir> outside the repository"); return 2
        sigs = []
        for root, _, files in os.walk(page):
            for fn in sorted(files):
                if not fn.endswith(".json"): continue
                try: j = json.load(open(os.path.join(root, fn), encoding="utf-8"))
                except ValueError: continue
                body = j.get("data") if isinstance(j.get("data"), dict) and "sigs" not in j else j
                ym = body.get("month") or fn[:-5]
                for chart, s in (body.get("sigs") or {}).items(): sigs.append(("%s_%s" % (chart, ym), chart, ym, s))
        signed = {r[0] for r in select(SIGNED_SQL)}
        todo = [s for s in sigs if s[0] not in signed]
        drafts = {}
        for i in range(0, len(todo), 300):
            for did, body in select(DRAFTS_SQL, [",".join(s[0] for s in todo[i:i + 300])]):
                drafts[did] = json.loads(body) if isinstance(body, str) else body
        good = 0; rejects = []
        for did, chart, ym, s in todo:
            d = drafts.get(did)
            if not d: rejects.append({"id": did, "why": "no draft for this month in the database"}); continue
            final, why = N.verify_signature(d.get("fields") or {}, s)
            if final is None: rejects.append({"id": did, "why": why}); continue
            _write(os.path.join(out, "signed", did + ".json"), {"chart": chart, "month": ym, "written": final["written"], "by": s["by"], "by_id": s.get("by_id", ""),
                                                             "at": s["at"], "sha": s["sha"], "fields": final, "via": via})
            good += 1
        if rejects: _write(os.path.join(out, "signature_rejects.json"), {"rejects": rejects, "_written": _now()})
        print("ccm_build: %d signings found, %d already recorded, %d verified -> %s, %d refused%s" % (len(sigs), len(sigs) - len(todo), good, os.path.join(out, "signed"), len(rejects),
              (" (" + "; ".join("%s: %s" % (r["id"], r["why"]) for r in rejects[:3]) + ")") if rejects else "")); return 0
    print("usage: ccm_build.py charts | plan | build --out <dir> | signatures --page <dir> --out <dir> [--via <url>]"); return 2
if __name__ == "__main__":
    sys.exit(main())
