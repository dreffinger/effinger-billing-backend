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
#   <out>/icd10cm/descriptions.json (command icd10)                                -> python3 tools/db/neon_db.py load-docs --src <out> --source ref
#   <out>/neon/addenda/<chart>_<YYYY-MM>_dx.json (command addenda)                 -> python3 tools/db/neon_db.py load-docs --src <out>/neon --source ccm
#   <out>/hub/config/addenda.json, <out>/hub/addenda/<YYYY-MM>-<n>.json           -> the hub page's own database (collections config and addenda)
#   <out>/addenda_signed/<chart>_<YYYY-MM>_dx.json (signatures --kind addenda)    -> python3 tools/db/neon_db.py load-docs --src <out> --source ccm
# Diagnoses (William 11/12/2026: "on all these signed notes add to them the diagnoses that were included with the charge in a diagnosis with
#   icd10 number as was shown in the original sample note"; "for new notes going forward always include the individual patient icd10 diagnosis
#   list"; "icd 10 diagnoses lists definitely need to be downloaded for each patient chart from advanced md and kept in each chart folder in
#   the database"): every charge's ICD-10 codes are already in the AdvancedMD history in Neon (raw.documents amd_history / chargedetail,
#   body.charges[].dx, with the dot, AdvancedMD's order; the typed amd.charge_details.diagnoses is empty and is not used). A note's charge
#   lines carry AdvancedMD's charge number without the "charge" prefix that chargedetail's charges[].id carries - checked 11/12/2026: all
#   7,055 CCM lines of the 4,177 signed notes match by chart and charge number, with the same code, date and visit. The descriptions are the
#   official CMS ICD-10-CM code files (newest fiscal year first; a code retired since keeps its last description) - one reference document,
#   source 'ref', collection 'icd10cm', doc_id 'descriptions', holding the codes that appear on any charge (command icd10).
#   - New notes carry the month's diagnoses in their fields (ccm_notes.note_fields); a signed note keeps the fields he signed (the stored
#     draft), so its hash still verifies.
#   - Every SIGNED note gets a dated ADDENDUM with the diagnoses on its CCM charge lines (command addenda; never for an addendum already
#     signed - a signed addendum keeps on the hub page the fields he signed, its recorded document, never rebuilt from today's charge
#     lines or descriptions), which he signs on the hub page later ("if needed i can sign the addendums later after they are added");
#     signatures --kind addenda checks each of those signings against the stored draft exactly as a note's signing is checked.
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
#   python3 scripts/helpers/ccm_build.py icd10 --cms <folder> --out <dir>   the CMS descriptions of every ICD-10 code on a charge (the CMS
#        icd10cm_codes_<year>.txt files anywhere under <folder>)
#   python3 scripts/helpers/ccm_build.py addenda --out <dir> [--descriptions <file>]   the diagnosis addendum of every signed note: the
#        drafts and the hub page's documents (the descriptions come from Neon's reference document, or from the file icd10 wrote)
#   python3 scripts/helpers/ccm_build.py signatures --kind addenda --page <dir> --out <dir> [--via <hub page url>]   the same check for the
#        hub page's collection "addendum_signatures"; good ones become addenda_signed/<id>.json
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
PER_DOC = 150                               # notes (or addenda) per hub document at most (a page's database document holds at most 256 KiB)
DOC_CAP = 180 * 1024                        # and at most this many bytes of them in one hub document
LINES_SQL = ("select c.chart_id, c.charge_id, c.visit_id, c.dos::text, c.cpt, "
             "coalesce((select max(d.units) from amd.charge_details d where d.chart_id = c.chart_id and d.charge_id = c.charge_id), 1)::text, "
             "coalesce(c.provider, ''), coalesce(c.facility, '') from amd.charges c where not c.void and c.cpt in (%s) "
             "order by c.chart_id, c.dos, c.cpt, c.charge_id")
PLANS_SQL = ("select p.chart_id, coalesce(p.carrier_name, ''), coalesce(p.begin_date::text, ''), coalesce(p.end_date::text, ''), coalesce(p.sequence, '') "
             "from amd.chart_plans p where p.chart_id in (select distinct chart_id from amd.charges where not void and cpt in (%s))")
SIGNED_SQL = "select doc_id from raw.documents where source = 'ccm' and collection = 'signed'"
DRAFTS_SQL = "select doc_id, body from raw.documents where source = 'ccm' and collection = 'months' and doc_id = any(string_to_array(%s, ','))"
# the fields of the signed months' drafts (what he signed, without the day written): a signed note keeps them on the hub page
STORED_SQL = ("select doc_id, body->'fields' from raw.documents where source = 'ccm' and collection = 'months' "
              "and doc_id in (select doc_id from raw.documents where source = 'ccm' and collection = 'signed')")
# every non-void CCM charge line's ICD-10 codes, from the AdvancedMD history (chargedetail; amd.charge_details.diagnoses is empty)
NOT_VOID = "lower(coalesce(e->>'void', '0')) not in ('1', 't', 'true', 'y', 'yes')"
LINES_OF = "jsonb_array_elements(case when jsonb_typeof(d.body->'charges') = 'array' then d.body->'charges' else '[]'::jsonb end) e"      # never fails on a document without a list
DX_SQL = ("select d.doc_id, e->>'id', e->'dx' from raw.documents d cross join lateral " + LINES_OF + " "
          "where d.source = 'amd_history' and d.collection = 'chargedetail' and e->>'cpt' in (%s) and " + NOT_VOID)
CODES_SQL = ("select distinct x.code from raw.documents d cross join lateral " + LINES_OF + " "
             "cross join lateral jsonb_array_elements_text(case when jsonb_typeof(e->'dx') = 'array' then e->'dx' else '[]'::jsonb end) x(code) "
             "where d.source = 'amd_history' and d.collection = 'chargedetail'")
CHART_DX_SQL = ("select d.doc_id, e->>'begindate', e->'dx' from raw.documents d cross join lateral " + LINES_OF + " "
                "where d.source = 'amd_history' and d.collection = 'chargedetail' and d.doc_id = any(string_to_array(%s, ',')) and " + NOT_VOID)
REF_SQL = "select body from raw.documents where source = 'ref' and collection = 'icd10cm' and doc_id = 'descriptions'"
NOTES_SIGNED_SQL = "select doc_id, body->'fields', body->>'sha' from raw.documents where source = 'ccm' and collection = 'signed'"
# the signed addenda with their recorded fields (what he signed, with the day written): a signed addendum keeps them on the hub page
ADD_SIGNED_SQL = "select doc_id, body->'fields' from raw.documents where source = 'ccm' and collection = 'addenda_signed'"
# the monthly add-on (11/25/2026): CCM visits read back from AdvancedMD after the history pull (scripts/helpers/ccm_month.py), the names the
# hub already has in Neon, and the fingerprint of every month draft already loaded (to tell which notes are new this run)
CCM_LINES_SQL = "select doc_id, body from raw.documents where source = 'ccm' and collection = 'lines'"
NEON_PATIENTS_SQL = "select doc_id, body from raw.documents where source = 'ccm' and collection = 'patients'"
MONTH_SHAS_SQL = "select doc_id, body->>'fields_sha' from raw.documents where collection = 'months' and source = 'ccm'"
ADD_DRAFTS_SQL = "select doc_id, body from raw.documents where source = 'ccm' and collection = 'addenda' and doc_id = any(string_to_array(%s, ','))"

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
def _json(x):
    """a JSON column as Neon's text route returns it (text), or as it is"""
    if isinstance(x, str):
        try: return json.loads(x)
        except ValueError: return None
    return x
def _size(x): return len(json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")) + 1
def _parts(items, per=PER_DOC, cap=DOC_CAP):
    """items cut into hub documents: at most `per` of them and `cap` bytes in each (well under the page database's 256 KiB)"""
    parts, cur, n = [], [], 0
    for x in items:
        k = _size(x)
        if cur and (len(cur) >= per or n + k > cap): parts.append(cur); cur, n = [], 0
        cur.append(x); n += k
    return parts + ([cur] if cur else [])

def _charge_no(x):
    """AdvancedMD's charge number as a note carries it: chargedetail's id without its "charge" prefix"""
    x = str(x or ""); return x[6:] if x.startswith("charge") else x
def dx_by_charge(select):
    """chart -> {charge number -> [ICD-10 codes, AdvancedMD's order]} for every non-void CCM charge line in the AdvancedMD history"""
    out = collections.defaultdict(dict)
    for chart, cid, dx in select(DX_SQL % _codes()):
        v = _json(dx); out[chart][_charge_no(cid)] = [str(c) for c in v if c] if isinstance(v, list) else []
    return out
def charge_lines(select, dx=None):
    """every live CCM charge line, shaped for ccm_notes.months(); with dx (dx_by_charge) each line carries its ICD-10 codes ("dx")"""
    out = [{"chart": r[0], "charge": r[1] or "", "visit": r[2] or "", "dos": r[3], "code": r[4], "units": r[5] or "1",
            "provider_code": r[6], "provider": PROVIDERS.get(r[6], r[6]), "facility": r[7]} for r in select(LINES_SQL % _codes())]
    if dx is not None:
        for l in out: l["dx"] = list(dx.get(l["chart"], {}).get(_charge_no(l["charge"]), []))
    return out
def ccm_lines(select, have=()):
    """(lines, carriers): the live CCM lines of the visits ccm_month.py read back from AdvancedMD after the history pull, shaped like
    charge_lines() with their ICD-10 codes as AdvancedMD holds them - a charge already among `have` (charge numbers from the history) is
    left to the history; carriers = {(chart, YYYY-MM): the feed's lead carrier} for a chart the history has no plan for"""
    have = {_charge_no(x) for x in have}; out = []; car = {}
    for did, body in select(CCM_LINES_SQL):
        d = _json(body)
        if not isinstance(d, dict) or not d.get("chart"): continue
        for c in d.get("charges") or []:
            if c.get("void") or not c.get("dos") or c.get("code") not in CODES or _charge_no(c.get("charge")) in have: continue
            have.add(_charge_no(c.get("charge")))
            out.append({"chart": d["chart"], "charge": _charge_no(c.get("charge")), "visit": str(c.get("visit") or d.get("visit") or ""), "dos": c["dos"], "code": c["code"],
                        "units": str(c.get("units") or "1"), "provider_code": c.get("provider_code") or "", "provider": PROVIDERS.get(c.get("provider_code") or "", c.get("provider_code") or ""),
                        "facility": c.get("facility") or (d.get("feed") or {}).get("facility") or "", "dx": [str(x) for x in (c.get("dx") or []) if x]})
            fc = (d.get("feed") or {}).get("carrier") or ""
            if fc: car.setdefault((d["chart"], c["dos"][:7]), fc)
    return out, car
def read_descriptions(select, path=None):
    """code -> [CMS description, fiscal year]: the reference document the icd10 command writes - from that file when one is named, else
    the one loaded into Neon (source 'ref', collection 'icd10cm', doc_id 'descriptions'); {} when there is none"""
    if path:
        with open(path, encoding="utf-8") as f: body = json.load(f)
    else:
        rows = select(REF_SQL); body = _json(rows[0][0]) if rows else None
    codes = body.get("codes") if isinstance(body, dict) else None
    return codes if isinstance(codes, dict) else {}
def with_dot(code):
    """an ICD-10-CM code as a charge carries it: the CMS files write E119, AdvancedMD E11.9"""
    c = str(code or "").strip().upper().replace(".", ""); return c[:3] + "." + c[3:] if len(c) > 3 else c
def cms_descriptions(folder):
    """code (with the dot) -> (description, fiscal year) from every CMS icd10cm_codes_<year>.txt under folder: the newest year's words,
    and a code retired since keeps its last description. Returns (descriptions, the years read)."""
    files = []
    for root, _, fs in os.walk(folder):
        for fn in fs:
            m = re.match(r"^icd10cm_codes_(\d{4})\.txt$", fn)
            if m: files.append((int(m.group(1)), os.path.join(root, fn)))
    out = {}
    for year, path in sorted(files):      # oldest first: a newer year's description replaces an older one
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                parts = line.strip().split(None, 1)
                if len(parts) == 2 and re.match(r"^[A-Z][0-9][0-9A-Z]{1,5}$", parts[0]): out[with_dot(parts[0])] = (parts[1].strip(), year)
    return out, sorted({y for y, _ in files}, reverse=True)
def build_months(select, patients, descriptions=None):
    """(records, signed ids). A record: the months() record + insurance + diagnoses + patient + fields + fields_sha + status. A signed
    month keeps the fields he signed (its stored draft); every other month's note carries its diagnoses with their CMS descriptions."""
    plans = plans_by_chart(select); signed = {r[0] for r in select(SIGNED_SQL)}
    desc = read_descriptions(select) if descriptions is None else descriptions
    stored = {}
    if signed:
        for did, f in select(STORED_SQL):
            f = _json(f)
            if isinstance(f, dict): stored[did] = f
    recs = []
    hist = charge_lines(select, dx_by_charge(select))
    extra, carriers = ccm_lines(select, [l["charge"] for l in hist])
    for m in N.months(hist + extra, signer=N.SIGNER_CODE):
        m = dict(m, insurance=insurance_for(plans.get(m["chart"], []), m["month"]) or carriers.get((m["chart"], m["month"]), ""), diagnoses=N.diagnoses([(c["code"], c.get("dx")) for c in m["charges"]], desc))
        pt = patients.get(m["chart"]) or {}
        rid = "%s_%s" % (m["chart"], m["month"])
        f = stored[rid] if rid in signed and rid in stored else N.note_fields(m, pt, None, [])      # a signed note is final: what he signed
        status = "flagged" if m["flag"] else ("no name yet" if not (pt.get("name") and pt.get("dob")) else "ready to sign")
        recs.append(dict(m, id=rid, patient=pt, fields=f, fields_sha=hashlib.sha256(N.canon(f).encode("utf-8")).hexdigest(), status=status))
    return recs, signed
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
def neon_patients(select):
    """chart -> {name, dob, sex, read_at}: the names the hub already has in Neon (source 'ccm', collection 'patients') - a routine's fresh
    workspace starts with none, and a note must not wait for a name that was read before"""
    out = {}
    for did, body in select(NEON_PATIENTS_SQL):
        d = _json(body)
        if isinstance(d, dict) and d.get("name") and d.get("dob"): out[d.get("chart") or did] = d
    return out
def all_patients(select, ws):
    """Neon's names, then the workspace's on top (a read made this run wins)"""
    out = neon_patients(select); out.update(read_patients(ws)); return out
def read_patients(ws):
    p = os.path.join(ws, "ccm", "ccm_patients.jsonl"); out = {}
    if os.path.exists(p):
        for line in open(p, encoding="utf-8"):
            try: j = json.loads(line)
            except ValueError: continue
            if j.get("chart") and not j.get("error"): out[j["chart"]] = j
    return out
def month_doc(r, at):
    return {"chart": r["chart"], "month": r["month"], "codes": r["codes"], "counts": r["counts"], "minutes": r["minutes"], "statement": r["statement"],
            "flag": r["flag"], "insurance": r["insurance"], "fields": r["fields"], "fields_sha": r["fields_sha"], "_written": at,
            "charges": [{"charge": c["charge"], "visit": c["visit"], "dos": c["dos"], "code": c["code"], "units": str(c.get("units") or "1"),
                         "provider": c["provider_code"], "facility": c["facility"], "dx": list(c.get("dx") or [])} for c in r["charges"]]}
def hub_docs(recs, signed, at):
    """the hub page's documents: config/practice and notes/<YYYY-MM>-<n> (the statement is stored once per document)"""
    by = collections.OrderedDict()
    for r in sorted(recs, key=lambda r: (r["month"], r["fields"]["patient"] or "~", r["chart"])): by.setdefault(r["month"], []).append(r)
    docs = {}; months = []
    for ym, rs in sorted(by.items(), reverse=True):
        items = []
        for r in rs:
            key = str(r["minutes"] or ""); own = r["fields"].get("statement") or ""
            if own and own != (r.get("statement") or ""): key = r["id"]      # a signed note whose statement is not today's for its codes keeps its own
            items.append({"id": r["id"], "f": {k2: v for k2, v in r["fields"].items() if k2 != "statement"}, "m": key, "flag": r["flag"],
                          "status": "signed" if r["id"] in signed else r["status"]})
        stm = {r["id"]: r["fields"].get("statement") or "" for r in rs}
        parts = _parts(items)
        for k, notes in enumerate(parts, 1):
            st = {x["m"]: stm[x["id"]] for x in notes if x["m"]}
            docs["notes/%s-%d" % (ym, k)] = {"month": ym, "part": k, "parts": len(parts), "statements": st, "notes": notes, "built_at": at}
        c = collections.Counter(("signed" if r["id"] in signed else r["status"]) for r in rs)
        months.append({"month": ym, "name": N.month_name(ym), "parts": len(parts), "notes": len(rs), "ready": c["ready to sign"], "flagged": c["flagged"], "noname": c["no name yet"], "signed": c["signed"]})
    tot = collections.Counter(("signed" if r["id"] in signed else r["status"]) for r in recs)
    docs["config/practice"] = {"practice": N.PRACTICE_NAME, "letterhead": list(N.LETTERHEAD), "phone": N.PHONE, "fax": N.FAX, "signer": N.SIGNER, "signer_code": N.SIGNER_CODE,
                               "built_at": at, "months": months, "counts": {"notes": len(recs), "ready": tot["ready to sign"], "flagged": tot["flagged"], "noname": tot["no name yet"], "signed": tot["signed"]}}
    return docs

def chart_dx(select, charts):
    """chart -> its diagnosis list from every non-void charge line ([code, first charge date, last charge date, charge lines], most lines
    first) - what ccm.chart_diagnoses shows, for the charts whose addendum is flagged"""
    acc = collections.defaultdict(dict); charts = sorted(set(charts))
    for i in range(0, len(charts), 200):
        for chart, day, dx in select(CHART_DX_SQL, [",".join(charts[i:i + 200])]):
            d = N._day(day); v = _json(dx)
            for c in sorted({str(x) for x in v if x}) if isinstance(v, list) else []:
                a = acc[chart].setdefault(c, [None, None, 0]); a[2] += 1
                if d: a[0] = min(a[0] or d, d); a[1] = max(a[1] or d, d)
    return {ch: [[c, N.us(a[0]), N.us(a[1]), str(a[2])] for c, a in sorted(m.items(), key=lambda kv: (-kv[1][2], kv[0]))] for ch, m in acc.items()}
def addenda_records(select, descriptions):
    """(records, ids already signed): the diagnosis addendum of every signed note whose fields carry no diagnoses (a note signed with them
    needs none). A record: id (<chart>_<YYYY-MM>_dx), note, chart, month, fields (ccm_notes.addendum_fields), fields_sha, note_sha, flag,
    status ("ready to sign", "flagged" or "signed") and, for a flagged one, the chart's whole diagnosis list (chart_dx). A SIGNED addendum
    keeps the fields he signed (its recorded document, without the day written) - never rebuilt from today's charge lines or descriptions."""
    signed_f = {r[0]: (_json(r[1]) if len(r) > 1 else None) for r in select(ADD_SIGNED_SQL)}
    done = set(signed_f)
    dx = dx_by_charge(select); recs = []
    for did, fields, sha in select(NOTES_SIGNED_SQL):
        f = _json(fields)
        if not isinstance(f, dict) or "diagnoses" in f or not f.get("chart"): continue
        aid = did + "_dx"
        if aid in done and isinstance(signed_f[aid], dict):
            af = {k: v for k, v in signed_f[aid].items() if k != "written"}; flags = []      # a signed addendum is final: what he signed
        else:
            cd = dx.get(f["chart"], {})
            af = N.addendum_fields(f, sha or "", cd, descriptions)
            flags = [x for x in [N.dx_flag(af["diagnoses"])] if x]
            lost = [c[3] for c in af["charges"] if len(c) > 3 and c[3] not in cd]
            if lost: flags.append("charge %s not found in the AdvancedMD history - its diagnoses could not be read" % ", ".join(lost))
        recs.append({"id": aid, "note": did, "chart": af["chart"], "month": af["month"], "fields": af, "note_sha": sha or "",
                     "fields_sha": hashlib.sha256(N.canon(af).encode("utf-8")).hexdigest(), "flag": "; ".join(flags),
                     "status": "signed" if aid in done else ("flagged" if flags else "ready to sign")})
    flagged = [r for r in recs if r["flag"] and r["status"] != "signed"]
    if flagged:
        cdx = chart_dx(select, [r["chart"] for r in flagged])
        for r in flagged: r["chart_dx"] = [[c, N.describe(c, descriptions), a, b, n] for c, a, b, n in cdx.get(r["chart"], [])]
    return recs, done
def addendum_doc(r, at):
    return {"chart": r["chart"], "month": r["month"], "note": r["note"], "kind": r["fields"]["kind"], "note_sha": r["note_sha"], "flag": r["flag"],
            "fields": r["fields"], "fields_sha": r["fields_sha"], "_written": at}
def addenda_hub_docs(recs, at):
    """the hub page's documents for the addenda: config/addenda (the counts) and addenda/<YYYY-MM>-<n> (the addenda of a month, each
    document well under the page database's 256 KiB)"""
    by = collections.OrderedDict()
    for r in sorted(recs, key=lambda r: (r["month"], r["fields"]["patient"] or "~", r["chart"])): by.setdefault(r["month"], []).append(r)
    docs = {}; months = []
    for ym, rs in sorted(by.items(), reverse=True):
        items = [dict({"id": r["id"], "note": r["note"], "f": r["fields"], "flag": r["flag"], "status": r["status"]}, **({"chart_dx": r["chart_dx"]} if r.get("chart_dx") else {})) for r in rs]
        parts = _parts(items)
        for k, part in enumerate(parts, 1): docs["addenda/%s-%d" % (ym, k)] = {"month": ym, "part": k, "parts": len(parts), "addenda": part, "built_at": at}
        c = collections.Counter(r["status"] for r in rs)
        months.append({"month": ym, "name": N.month_name(ym), "parts": len(parts), "addenda": len(rs), "ready": c["ready to sign"], "flagged": c["flagged"], "signed": c["signed"]})
    tot = collections.Counter(r["status"] for r in recs)
    docs["config/addenda"] = {"kind": "diagnoses", "built_at": at, "months": months,
                              "counts": {"addenda": len(recs), "ready": tot["ready to sign"], "flagged": tot["flagged"], "signed": tot["signed"]}}
    return docs
def page_sigs(page):
    """every signing in what ArtifactData list wrote with out_dir for one of the hub page's signing collections: (key, month, signing)"""
    out = []
    for root, _, files in os.walk(page):
        for fn in sorted(files):
            if not fn.endswith(".json"): continue
            try: j = json.load(open(os.path.join(root, fn), encoding="utf-8"))
            except ValueError: continue
            if not isinstance(j, dict): continue
            body = j.get("data") if isinstance(j.get("data"), dict) and "sigs" not in j else j
            ym = body.get("month") or fn[:-5]
            for key, s in (body.get("sigs") or {}).items(): out.append((key, ym, s))
    return out

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
        desc = read_descriptions(select, opt("--descriptions"))
        if cmd == "build" and not desc:
            print("ccm_build: no ICD-10 descriptions - a new note lists its diagnoses with them: write them with `icd10`, load them "
                  "(neon_db.py load-docs --source ref) or pass --descriptions <file>"); return 2
        recs, signed = build_months(select, all_patients(select, ws), desc)
        c = collections.Counter(("signed" if r["id"] in signed else r["status"]) for r in recs)
        print("ccm_build: %d patient-months (%d charts, %s to %s): %d ready to sign, %d flagged, %d waiting for the patient's name, %d signed" % (
            len(recs), len({r["chart"] for r in recs}), min((r["month"] for r in recs), default="-"), max((r["month"] for r in recs), default="-"),
            c["ready to sign"], c["flagged"], c["no name yet"], c["signed"]))
        if cmd == "plan": return 0
        out = opt("--out")
        if not out: print("ccm_build: build needs --out <dir>"); return 2
        if _inside_repo(out): print("ccm_build: %s is inside the repository - patient data never goes there" % out); return 2
        at = _now(); pts = read_patients(ws); n = 0
        loaded = {r[0]: r[1] for r in select(MONTH_SHAS_SQL)}
        fresh = [r for r in recs if r["id"] not in signed and loaded.get(r["id"]) != r["fields_sha"]]      # new or changed since the last load
        for chart in sorted({r["chart"] for r in recs} & set(pts)):
            p = pts[chart]; _write(os.path.join(out, "neon", "patients", chart + ".json"), {"chart": chart, "name": p.get("name", ""), "dob": p.get("dob", ""), "sex": p.get("sex", ""), "read_at": p.get("read_at", ""), "_written": at})
        for r in recs:
            if r["id"] in signed: continue      # a signed month is final
            _write(os.path.join(out, "neon", "months", r["id"] + ".json"), month_doc(r, at)); n += 1
        hub = hub_docs(recs, signed, at)
        only = [m for m in (opt("--hub-months") or "").split(",") if m]      # the routine writes only the months that changed (and config/practice)
        if "--hub-new" in a: only = sorted(set(only) | {r["month"] for r in fresh})
        for k, v in hub.items():
            if only and k.startswith("notes/") and v.get("month") not in only: continue
            _write(os.path.join(out, "hub", k + ".json"), v)
        new = collections.Counter(r["status"] for r in fresh if r["id"] not in signed)
        _write(os.path.join(out, "summary.json"), {"_written": at, "new_or_changed": len(fresh), "new_ready": new["ready to sign"], "new_flagged": new["flagged"],
               "new_noname": new["no name yet"], "months": sorted({r["month"] for r in fresh}), "hub_months": only or "all",
               "unsigned": {"ready": c["ready to sign"], "flagged": c["flagged"], "noname": c["no name yet"]}})
        print("ccm_build: wrote %d month records (%d new or changed since the last load: %d ready, %d flagged, %d waiting for a name; months %s; "
              "%d signed months left as they are) and the hub documents (%s) under %s" % (n, len(fresh), new["ready to sign"], new["flagged"], new["no name yet"],
              ", ".join(sorted({r["month"] for r in fresh})) or "-", len(signed & {r["id"] for r in recs}), ("months " + ", ".join(only)) if only else "all months", out)); return 0
    if cmd == "signatures" and (opt("--kind") or "notes") == "addenda":
        page, out, via = opt("--page"), opt("--out"), opt("--via") or ""
        if not (page and out) or _inside_repo(out): print("ccm_build: signatures --kind addenda needs --page <dir> and --out <dir> outside the repository"); return 2
        sigs = []
        for key, ym, s in page_sigs(page):
            aid = key if re.match(r"^.+_\d{4}-\d{2}_dx$", key) else "%s_%s_dx" % (key, ym)
            sigs.append((aid, s))
        signed = {r[0] for r in select(ADD_SIGNED_SQL)}
        todo = [x for x in sigs if x[0] not in signed]
        drafts = {}
        for i in range(0, len(todo), 300):
            for did, body in select(ADD_DRAFTS_SQL, [",".join(x[0] for x in todo[i:i + 300])]): drafts[did] = _json(body) or {}
        good = 0; rejects = []
        for aid, s in todo:
            d = drafts.get(aid)
            if not d: rejects.append({"id": aid, "why": "no draft for this addendum in the database"}); continue
            final, why = N.verify_signature(d.get("fields") or {}, s, statement=False)
            if final is None: rejects.append({"id": aid, "why": why}); continue
            _write(os.path.join(out, "addenda_signed", aid + ".json"), {"chart": d.get("chart", ""), "month": d.get("month", ""), "note": d.get("note", ""), "kind": d.get("kind", ""),
                                                                         "written": final["written"], "by": s["by"], "by_id": s.get("by_id", ""), "at": s["at"], "sha": s["sha"], "fields": final, "via": via})
            good += 1
        if rejects: _write(os.path.join(out, "addendum_signature_rejects.json"), {"rejects": rejects, "_written": _now()})
        print("ccm_build: %d addendum signings found, %d already recorded, %d verified -> %s, %d refused%s" % (len(sigs), len(sigs) - len(todo), good, os.path.join(out, "addenda_signed"), len(rejects),
              (" (" + "; ".join("%s: %s" % (r["id"], r["why"]) for r in rejects[:3]) + ")") if rejects else "")); return 0
    if cmd == "signatures":
        if (opt("--kind") or "notes") != "notes": print("ccm_build: signatures --kind is notes (the default) or addenda"); return 2
        page, out, via = opt("--page"), opt("--out"), opt("--via") or ""
        if not (page and out) or _inside_repo(out): print("ccm_build: signatures needs --page <dir> and --out <dir> outside the repository"); return 2
        sigs = [("%s_%s" % (chart, ym), chart, ym, s) for chart, ym, s in page_sigs(page)]
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
    if cmd == "icd10":
        cms, out = opt("--cms"), opt("--out")
        if not (cms and out and os.path.isdir(cms)) or _inside_repo(out): print("ccm_build: icd10 needs --cms <folder of the CMS code files> and --out <dir> outside the repository"); return 2
        cmsd, years = cms_descriptions(cms)
        if not cmsd: print("ccm_build: no CMS icd10cm_codes_<year>.txt file under %s" % cms); return 2
        on = sorted({str(r[0]).strip() for r in select(CODES_SQL) if r and r[0]})
        codes = {c: [cmsd[c][0], cmsd[c][1]] for c in on if c in cmsd}; missing = [c for c in on if c not in cmsd]
        by_year = collections.Counter(v[1] for v in codes.values())
        _write(os.path.join(out, "icd10cm", "descriptions.json"), {"title": "ICD-10-CM descriptions (CMS code files) of every code on a charge in the AdvancedMD history",
               "years": years, "codes": codes, "missing": missing, "codes_on_charges": len(on), "_written": _now()})
        print("ccm_build: %d ICD-10 codes on the charges, %d described (%s), %d without a CMS description%s -> %s" % (len(on), len(codes),
              ", ".join("FY%d %d" % (y, by_year[y]) for y in years if by_year[y]), len(missing), (" (" + ", ".join(missing[:8]) + ")") if missing else "",
              os.path.join(out, "icd10cm", "descriptions.json"))); return 0
    if cmd == "addenda":
        out = opt("--out")
        if not out or _inside_repo(out): print("ccm_build: addenda needs --out <dir> outside the repository - patient data never goes there"); return 2
        desc = read_descriptions(select, opt("--descriptions"))
        if not desc: print("ccm_build: no ICD-10 descriptions - write them with `icd10` and load them (neon_db.py load-docs --source ref), or pass --descriptions <file>"); return 2
        recs, done = addenda_records(select, desc)
        at = _now(); n = 0
        for r in recs:
            if r["id"] in done: continue      # a signed addendum is final
            _write(os.path.join(out, "neon", "addenda", r["id"] + ".json"), addendum_doc(r, at)); n += 1
        hub = addenda_hub_docs(recs, at)
        for k, v in hub.items(): _write(os.path.join(out, "hub", k + ".json"), v)
        c = collections.Counter(r["status"] for r in recs)
        dxs = [x[0] for r in recs for x in r["fields"]["diagnoses"]]
        big = max(((_size(v), k) for k, v in hub.items()), default=(0, "-"))
        print("ccm_build: %d addenda (%d ready to sign, %d flagged, %d signed); %d drafts written, %d signed left as they are; %d distinct codes, %d without a CMS description; "
              "%d hub documents, the largest %s (%d KB) -> %s" % (len(recs), c["ready to sign"], c["flagged"], c["signed"], n, len(done & {r["id"] for r in recs}), len(set(dxs)),
              len({x for x in dxs if not N.describe(x, desc)}), len(hub), big[1], big[0] // 1024, out)); return 0
    print("usage: ccm_build.py charts | plan | build --out <dir> [--descriptions <file>] | signatures [--kind addenda] --page <dir> --out <dir> [--via <url>] | "
          "icd10 --cms <folder> --out <dir> | addenda --out <dir> [--descriptions <file>]"); return 2
if __name__ == "__main__":
    sys.exit(main())
