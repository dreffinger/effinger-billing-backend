#!/usr/bin/env python3
# PLAIN ENGLISH (the ERA archive - William 11/27/2026: "run through all the era files to collect all the run reports and era files ... all the
#   data on that in the database for usefull questions ... like which payer hasnt paid since when"; "a look should be done for these large era
#   files uploaded to parse them and save them for usefull info for billing along with what denial codes are common or frequent enough to act
#   on and make a bigger fix for"; "check the era reports in the drive folders as well ... all of those and file away where they can be used for
#   practice management questions and info")
# Decides: nothing about a claim. It FILES what the remittances say. Every ERA file in the practice's Drive folders (Optum / Availity / Change
#   Healthcare 835 downloads, the ERA Center, paper and card remits once the OCR pipeline has read them) becomes rows in the practice database
#   (Neon, HIPAA): amd.era_files (one per Drive file: where it is, what it is, whether it was read), amd.era_payments (one per payment: payer,
#   method - ACH / CHK paper check / NON no money / VCC virtual card / BOP / FWT - amount, date, trace or check number, payee), amd.era_claims
#   (one per claim: AdvancedMD claim number and visit, status, charge, paid, patient share, the payer's claim number, dates of service) and
#   amd.era_adjustments (every CAS reason with its group and amount, claim, service-line and provider level). The views amd.payer_payment_methods
#   (how each payer pays) and amd.era_denial_patterns (the most frequent denial reasons by payer) answer the questions.
# Rules it uses: an 835 is read by its own separators (ISA); a file read before (same sha256) is not read twice; a payment is keyed by payer +
#   trace number + amount + date, so the same remittance downloaded twice (Optum's "(1)" copies) is one payment.
# Never touches: AdvancedMD, the files themselves (read-only in Drive), the public repository - nothing it reads is written to git.
# ---
"""Usage (NEON_DATABASE_URL, as for credentialing/cred_vault.py):
  python3 billing/era_input/era_archive.py inventory <drive-listing.json>... [--folder-name NAME]   Drive files -> amd.era_files
  python3 billing/era_input/era_archive.py pending [--kind x12|pdf|other]                            what is not read yet
  python3 -I billing/era_input/era_archive.py parse <file> --drive-id <id>                             one 835 -> the tables
  python3 -I billing/era_input/era_archive.py parse-dir <dir>      every <drive-id>.bin / .dat / .835 file in <dir> (named by Drive id)
  python3 -I billing/era_input/era_archive.py load-pdf-json <dir>  the remit-pdf-archive JSON files (one per PDF: payments + claims)
  python3 billing/era_input/era_archive.py selftest"""
import datetime, glob, hashlib, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
A = sys.argv[1:]
def opt(n, d=None): return A[A.index(n) + 1] if n in A and A.index(n) + 1 < len(A) else d

METHOD = {"ACH": "ACH (EFT)", "CHK": "paper check", "NON": "no payment", "BOP": "financial institution option", "FWT": "wire",
          "VCC": "virtual card", "CCP": "card"}


def num(x):
    try: return round(float(x), 2)
    except (TypeError, ValueError): return 0.0


def d8(s):
    s = (s or "").strip()
    return "%s-%s-%s" % (s[:4], s[4:6], s[6:8]) if re.match(r"^\d{8}$", s) else None


def kind_of(title, mime):
    t = (title or "").lower()
    if t.endswith((".dat", ".835", ".edi", ".x12", ".era")) or (mime or "") == "application/octet-stream" and not t.endswith((".exe", ".zip")): return "x12"
    if t.endswith(".pdf") or (mime or "").endswith("pdf"): return "pdf"
    if t.endswith((".csv", ".xlsx", ".xls")) or "spreadsheet" in (mime or ""): return "table"
    return "other"


# ---------------------------------------------------------------- the 835 reader (pure; the selftest feeds it a synthetic file)
def segments(raw):
    """X12 text -> list of element lists, by the file's own separators (ISA: element sep at [3], sub-element at [104], terminator at [105])."""
    raw = raw.replace("\r", "").replace("\n", "") if "~" in raw else raw.replace("\r", "")
    i = raw.find("ISA")
    if i < 0: return []
    raw = raw[i:]
    el = raw[3]; term = raw[105] if len(raw) > 105 and raw[105] not in (el,) else "~"
    if term.isalnum(): term = "~"
    return [s.split(el) for s in (x.strip() for x in raw.split(term)) if s]


def g(seg, i, d=""):
    return seg[i] if len(seg) > i else d


def parse_835(raw):
    """-> list of payments, each {payer, method, amount, date, trace, payee..., claims: [{..., adjustments: [...]}], plb: [...]}."""
    segs = segments(raw); out = []; cur = None; claim = None; line = None; who = None; sub = ":"
    if segs and len(segs[0]) > 16: sub = segs[0][16][:1] or ":"
    for s in segs:
        tag = s[0]
        if tag == "ST":
            cur = {"payer_name": None, "payer_id": None, "payee_name": None, "payee_npi": None, "method": None, "amount": 0.0, "date": None,
                   "trace": None, "handling": None, "claims": [], "plb": []}; claim = None; line = None; who = None
        elif cur is None: continue
        elif tag == "BPR":
            cur.update(handling=g(s, 1), amount=num(g(s, 2)), method=g(s, 4) or None, date=d8(g(s, 16)))
        elif tag == "TRN": cur["trace"] = g(s, 2) or None; cur["payer_id"] = cur["payer_id"] or (g(s, 3) or None)
        elif tag == "N1":
            who = g(s, 1)
            if who == "PR": cur["payer_name"] = g(s, 2) or None
            elif who == "PE": cur["payee_name"] = g(s, 2) or None; cur["payee_npi"] = g(s, 4) or None if g(s, 3) == "XX" else cur["payee_npi"]
        elif tag == "REF" and who == "PR" and g(s, 1) == "2U" and not claim: cur["payer_id"] = g(s, 2) or cur["payer_id"]
        elif tag == "CLP":
            pc = g(s, 1); m = re.match(r"^(\d{7,9})([A-Z]{0,2})$", pc.strip())
            claim = {"patient_control": pc or None, "visit_id": int(m.group(1)) if m else None, "status": g(s, 2) or None, "charge": num(g(s, 3)),
                     "paid": num(g(s, 4)), "patient_resp": num(g(s, 5)), "filing": g(s, 6) or None, "payer_claim_no": g(s, 7) or None,
                     "dos_from": None, "dos_to": None, "patient": None, "rendering_npi": None, "adjustments": [], "lines": 0}
            cur["claims"].append(claim); line = None
        elif tag == "NM1" and claim is not None:
            if g(s, 1) == "QC": claim["patient"] = ("%s,%s" % (g(s, 3), g(s, 4))).strip(",") or None
            elif g(s, 1) == "82": claim["rendering_npi"] = g(s, 9) or None
        elif tag == "DTM" and claim is not None:
            q, v = g(s, 1), d8(g(s, 2))
            if q in ("232", "472") and not claim["dos_from"]: claim["dos_from"] = v
            if q in ("233", "472"): claim["dos_to"] = v or claim["dos_to"]
        elif tag == "SVC" and claim is not None:
            claim["lines"] += 1; comp = g(s, 1).split(sub)
            line = {"line_no": claim["lines"], "cpt": comp[1] if len(comp) > 1 else comp[0], "charge": num(g(s, 2)), "paid": num(g(s, 3))}
        elif tag == "CAS" and claim is not None:
            grp = g(s, 1)
            for k in range(2, len(s), 3):
                reason = g(s, k)
                if not reason: continue
                claim["adjustments"].append({"level": "line" if line else "claim", "line_no": line["line_no"] if line else 0,
                                             "cpt": line["cpt"] if line else None, "grp": grp, "carc": reason, "amount": num(g(s, k + 1))})
        elif tag == "PLB":
            for k in range(3, len(s), 2):
                if g(s, k): cur["plb"].append({"code": g(s, k).split(sub)[0], "ref": (g(s, k).split(sub) + [""])[1] or None, "amount": num(g(s, k + 1))})
        elif tag == "SE":
            out.append(cur); cur = None; claim = None; line = None
    return out


def payment_key(p):
    return "%s|%s|%.2f|%s" % (p.get("payer_id") or p.get("payer_name") or "?", p.get("trace") or "?", p.get("amount") or 0, p.get("date") or "?")


# ---------------------------------------------------------------- the database
DDL = [
    """create table if not exists amd.era_files (drive_file_id text primary key, folder_id text, folder text, title text, mime_type text,
         size_bytes bigint, created_in_drive timestamptz, kind text, status text default 'pending', sha256 text, payments int, claims int,
         parsed_at timestamptz, note text, first_seen timestamptz default now())""",
    """create table if not exists amd.era_payments (payment_key text primary key, drive_file_id text, payer_name text, payer_id text,
         payee_name text, payee_npi text, method text, handling text, amount numeric(12,2), payment_date date, trace_number text, claims int,
         provider_adjustments jsonb, source text default '835', loaded_at timestamptz default now())""",
    """create table if not exists amd.era_claims (claim_key text primary key, payment_key text, patient_control text, visit_id bigint,
         status_code text, charge numeric(12,2), paid numeric(12,2), patient_resp numeric(12,2), filing text, payer_claim_no text,
         dos_from date, dos_to date, patient_name text, rendering_npi text, lines int, loaded_at timestamptz default now())""",
    "create index if not exists era_claims_visit on amd.era_claims (visit_id)",
    """create table if not exists amd.era_adjustments (claim_key text, level text, line_no int, cpt text, grp text, carc text,
         amount numeric(12,2), primary key (claim_key, level, line_no, grp, carc))""",
    # how each payer pays: ERA files + the ERA Center's own check list (run_alerts.py fills amd.era_checks)
    """create or replace view amd.payer_payment_methods as
       select payer_name, method, count(*) payments, sum(amount) dollars, min(payment_date) first_payment, max(payment_date) last_payment,
              'era file' source from amd.era_payments group by payer_name, method
       union all
       select era_payer, payment_code, count(*), sum(amount), min(check_date), max(check_date), 'era center'
       from amd.era_checks group by era_payer, payment_code""",
    # the denial reasons that repeat: every non-contractual, non-cost-share adjustment on the ERA files, by payer and reason
    """create or replace view amd.era_denial_patterns as
       select p.payer_name, a.grp || '-' || a.carc reason, count(distinct a.claim_key) claims, sum(a.amount) dollars,
              min(p.payment_date) first_seen, max(p.payment_date) last_seen
       from amd.era_adjustments a join amd.era_claims c using (claim_key) join amd.era_payments p using (payment_key)
       where not (a.grp = 'CO' and a.carc in ('45', '253')) and a.grp <> 'PR' and a.carc not in ('23', '94', '246')
       group by 1, 2""",
]


def db():
    sys.path.insert(0, os.path.join(REPO, "credentialing"))
    saved = sys.argv[:]; sys.argv = sys.argv[:1]
    try:
        import cred_vault
    finally:
        sys.argv = saved
    return cred_vault.DB()


def ensure(d):
    for s in DDL: d.q(s)


def store(d, drive_id, raw, sha):
    pays = parse_835(raw)
    if not pays:
        d.q("update amd.era_files set status='not 835', sha256=%s, parsed_at=now() where drive_file_id=%s", [sha, drive_id]); return 0, 0
    nclaims = 0
    for p in pays:
        pk = payment_key(p)
        d.q("""insert into amd.era_payments (payment_key, drive_file_id, payer_name, payer_id, payee_name, payee_npi, method, handling, amount,
                 payment_date, trace_number, claims, provider_adjustments) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
               on conflict (payment_key) do nothing""",
            [pk, drive_id, p["payer_name"], p["payer_id"], p["payee_name"], p["payee_npi"], p["method"], p["handling"], p["amount"], p["date"],
             p["trace"], len(p["claims"]), json.dumps(p["plb"])])
        rows, adj = [], []
        for i, c in enumerate(p["claims"]):
            ck = "%s|%s|%s|%d" % (pk, c["patient_control"] or "?", c["payer_claim_no"] or "?", i)
            rows.append(dict(claim_key=ck, payment_key=pk, patient_control=c["patient_control"], visit_id=c["visit_id"], status_code=c["status"],
                             charge=c["charge"], paid=c["paid"], patient_resp=c["patient_resp"], filing=c["filing"], payer_claim_no=c["payer_claim_no"],
                             dos_from=c["dos_from"], dos_to=c["dos_to"], patient_name=c["patient"], rendering_npi=c["rendering_npi"], lines=c["lines"]))
            seen = {}
            for a in c["adjustments"]:
                k = (a["level"], a["line_no"], a["grp"], a["carc"])
                if k in seen: seen[k]["amount"] = round(seen[k]["amount"] + a["amount"], 2); continue
                seen[k] = dict(claim_key=ck, level=a["level"], line_no=a["line_no"], cpt=a["cpt"], grp=a["grp"], carc=a["carc"], amount=a["amount"])
            adj += list(seen.values())
        if rows:
            d.q("""insert into amd.era_claims select * , now() from jsonb_populate_recordset(null::amd.era_claims, %s::jsonb) x
                   on conflict (claim_key) do nothing""".replace("select * , now() from", "select claim_key, payment_key, patient_control, visit_id, status_code, charge, paid, patient_resp, filing, payer_claim_no, dos_from, dos_to, patient_name, rendering_npi, lines, now() from"),
                [json.dumps(rows)])
        if adj:
            d.q("""insert into amd.era_adjustments select claim_key, level, line_no, cpt, grp, carc, amount
                   from jsonb_populate_recordset(null::amd.era_adjustments, %s::jsonb) on conflict do nothing""", [json.dumps(adj)])
        nclaims += len(rows)
    d.q("update amd.era_files set status='read', sha256=%s, payments=%s, claims=%s, parsed_at=now() where drive_file_id=%s",
        [sha, len(pays), nclaims, drive_id])
    return len(pays), nclaims


def parse_file(d, path, drive_id):
    data = open(path, "rb").read(); sha = hashlib.sha256(data).hexdigest()
    if d.q("select 1 from amd.era_files where sha256=%s and status='read' and drive_file_id<>%s", [sha, drive_id]):
        d.q("update amd.era_files set status='duplicate', sha256=%s, parsed_at=now() where drive_file_id=%s", [sha, drive_id]); return "duplicate", 0, 0
    if not d.q("select 1 from amd.era_files where drive_file_id=%s", [drive_id]):
        d.q("insert into amd.era_files (drive_file_id, title, kind) values (%s,%s,'x12')", [drive_id, os.path.basename(path)])
    p, c = store(d, drive_id, data.decode("latin-1"), sha)
    return ("read" if p else "not 835"), p, c


METHOD_CODE = {"CHK": "CHK", "CHECK": "CHK", "PAPER CHECK": "CHK", "ACH": "ACH", "EFT": "ACH", "VCC": "VCC", "VIRTUAL CARD": "VCC", "CARD": "VCC",
               "NON": "NON", "NONE": "NON"}


def pdf_rows(j, did):
    """One extracted PDF (the remit-pdf-archive JSON: payments[] + claims[]) -> (payments, claims, adjustments) rows for the tables."""
    pays, keys = [], []
    for p in j.get("payments") or []:
        raw = str(p.get("method") or "").strip().upper()
        meth = METHOD_CODE.get(raw) or METHOD_CODE.get(raw.split(" ")[0]) or (
            "CHK" if "CHECK" in raw else "VCC" if "CARD" in raw else "ACH" if ("EFT" in raw or "ACH" in raw) else "NON" if "NO PAY" in raw else "unknown")
        amt = p.get("amount"); amt = num(amt) if amt is not None else None
        pk = "pdf|%s|%s|%s|%s" % (p.get("payer_id") or p.get("payer_name") or "?", p.get("number") or did, "%.2f" % amt if amt is not None else "?", p.get("date") or "?")
        keys.append(pk)
        pays.append(dict(payment_key=pk, drive_file_id=did, payer_name=p.get("payer_name"), payer_id=p.get("payer_id"), payee_name=p.get("payee_name"),
                         payee_npi=p.get("payee_npi"), method=meth, amount=amt, payment_date=p.get("date") if re.match(r"^\d{4}-\d{2}-\d{2}$", str(p.get("date") or "")) else None,
                         trace_number=p.get("number")))
    claims, adj = [], []
    for k, c in enumerate(j.get("claims") or []):
        i = c.get("payment_index")
        pk = keys[i] if isinstance(i, int) and 0 <= i < len(keys) else (keys[0] if len(keys) == 1 else "pdf|%s|no payment" % did)
        pc = str(c.get("patient_control") or "").strip(); m = re.match(r"^(\d{7,9})([A-Z]{0,2})$", pc)
        ck = "%s|%s|%s|%d" % (pk, pc or "?", c.get("payer_claim_no") or "?", k)
        dt = lambda v: v if re.match(r"^\d{4}-\d{2}-\d{2}$", str(v or "")) else None
        claims.append(dict(claim_key=ck, payment_key=pk, patient_control=pc or None, visit_id=int(m.group(1)) if m else None, status_code=c.get("status"),
                           charge=num(c.get("charge")), paid=num(c.get("paid")), patient_resp=num(c.get("patient_resp")), filing=None,
                           payer_claim_no=c.get("payer_claim_no"), dos_from=dt(c.get("dos_from")), dos_to=dt(c.get("dos_to")), patient_name=c.get("patient_name"),
                           rendering_npi=None, lines=None))
        seen = {}
        for a in c.get("adjustments") or []:
            if not a.get("carc"): continue
            key = ("claim", 0, str(a.get("grp") or "").upper()[:2], str(a.get("carc")).upper())
            if key in seen: seen[key]["amount"] = round(seen[key]["amount"] + num(a.get("amount")), 2); continue
            seen[key] = dict(claim_key=ck, level="claim", line_no=0, cpt=a.get("cpt"), grp=key[2], carc=key[3], amount=num(a.get("amount")))
        adj += list(seen.values())
    return pays, claims, adj


def load_pdf_json(d, path):
    j = json.load(open(path)); did = j.get("drive_file_id") or os.path.basename(path).split(".")[0]
    pays, claims, adj = pdf_rows(j, did)
    d.q("insert into amd.era_files (drive_file_id, kind) values (%s,'pdf') on conflict (drive_file_id) do nothing", [did])
    if pays:
        d.q("""insert into amd.era_payments (payment_key, drive_file_id, payer_name, payer_id, payee_name, payee_npi, method, amount, payment_date,
                 trace_number, claims, source) select payment_key, drive_file_id, payer_name, payer_id, payee_name, payee_npi, method, amount, payment_date,
                 trace_number, 0, 'pdf' from jsonb_to_recordset(%s::jsonb) as x(payment_key text, drive_file_id text, payer_name text, payer_id text,
                 payee_name text, payee_npi text, method text, amount numeric, payment_date date, trace_number text) on conflict (payment_key) do nothing""",
            [json.dumps(pays)])
    if claims:
        d.q("""insert into amd.era_claims (claim_key, payment_key, patient_control, visit_id, status_code, charge, paid, patient_resp, filing, payer_claim_no,
                 dos_from, dos_to, patient_name, rendering_npi, lines) select claim_key, payment_key, patient_control, visit_id, status_code, charge, paid,
                 patient_resp, filing, payer_claim_no, dos_from, dos_to, patient_name, rendering_npi, lines
               from jsonb_populate_recordset(null::amd.era_claims, %s::jsonb) on conflict (claim_key) do nothing""", [json.dumps(claims)])
    if adj:
        d.q("""insert into amd.era_adjustments select claim_key, level, line_no, cpt, grp, carc, amount
               from jsonb_populate_recordset(null::amd.era_adjustments, %s::jsonb) on conflict do nothing""", [json.dumps(adj)])
    d.q("update amd.era_files set status='read', kind='pdf', payments=%s, claims=%s, parsed_at=now(), note=%s where drive_file_id=%s",
        [len(pays), len(claims), str(j.get("class") or "")[:40], did])
    return len(pays), len(claims)


def main():
    cmd = A[0] if A else "help"
    if cmd == "selftest": return selftest()
    if cmd not in ("inventory", "pending", "parse", "parse-dir", "load-pdf-json"): sys.exit(__doc__)
    d = db(); ensure(d)
    if cmd == "inventory":
        files = []
        for p in [x for x in A[1:] if not x.startswith("--") and os.path.exists(x)]:
            j = json.load(open(p)); files += j.get("files", j) if isinstance(j, dict) else j
        n = 0
        for f in files:
            if "size" in f and "fileSize" not in f:     # the remit-pdf-archive inventory shape
                f = dict(f, fileSize=f.get("size"), parentId=f.get("folder_id"), createdTime=f.get("created"), mimeType=f.get("mimeType") or "application/pdf")
            if f.get("mimeType") == "application/vnd.google-apps.folder" or f.get("trashed"): continue
            k = kind_of(f.get("title"), f.get("mimeType"))
            r = d.q("""insert into amd.era_files (drive_file_id, folder_id, folder, title, mime_type, size_bytes, created_in_drive, kind)
                       values (%s,%s,%s,%s,%s,%s,%s,%s) on conflict (drive_file_id) do nothing returning drive_file_id""",
                    [f["id"], f.get("parentId"), opt("--folder-name"), f.get("title"), f.get("mimeType"), f.get("fileSize"), f.get("createdTime"), k])
            n += 1 if r else 0
        print("%d new file(s) in the ERA archive" % n); return
    if cmd == "pending":
        rows = d.q("select drive_file_id, kind, size_bytes, title from amd.era_files where status='pending' and (%s::text is null or kind=%s) order by size_bytes",
                   [opt("--kind"), opt("--kind")])
        for r in rows: print("%-34s %-6s %10s  %s" % (r[0], r[1], r[2] or "?", (r[3] or "")[:60]))
        print("%d pending" % len(rows)); return
    if cmd == "parse":
        st, p, c = parse_file(d, A[1], opt("--drive-id") or sys.exit("--drive-id is required"))
        print("%s: %s - %d payment(s), %d claim(s)" % (opt("--drive-id"), st, p, c)); return
    if cmd == "load-pdf-json":
        tot = [0, 0, 0]
        for path in sorted(glob.glob(os.path.join(A[1], "*.json"))):
            p, c = load_pdf_json(d, path); tot[0] += 1; tot[1] += p; tot[2] += c
        print("%d PDF file(s) filed: %d payment(s), %d claim(s)" % tuple(tot)); return
    if cmd == "parse-dir":
        tot = [0, 0, 0]
        for path in sorted(glob.glob(os.path.join(A[1], "*"))):
            did = os.path.basename(path).split(".")[0]
            st, p, c = parse_file(d, path, did); tot[0] += 1; tot[1] += p; tot[2] += c
            print("%s %s %d/%d" % (did, st, p, c))
        print("%d file(s): %d payment(s), %d claim(s)" % tuple(tot)); return


def selftest():
    s = ("ISA*00*          *00*          *ZZ*PAYERX         *ZZ*RECEIVER       *260101*1200*^*00501*000000001*0*P*:~GS*HP*A*B*20260101*1200*1*X*005010X221A1~"
         "ST*835*0001~BPR*I*150.25*C*ACH*CCP*01*999999999*DA*123*1000000000**01*999999999*DA*456*20261120~TRN*1*EFT123*1000000000~"
         "N1*PR*SAMPLE HEALTH PLAN~REF*2U*SHP01~N1*PE*SAMPLE CLINIC*XX*1000000003~LX*1~"
         "CLP*19461428A*1*300*150.25*20*12*PAYERCLM1~NM1*QC*1*DOE*JANE~NM1*82*1*ROE*JOHN****XX*1000000001~DTM*232*20261001~"
         "CAS*CO*45*129.75~SVC*HC:99223:25*300*150.25~DTM*472*20261001~CAS*PR*2*20~"
         "CLP*19461429A*4*120*0*0*12*PAYERCLM2~CAS*CO*170*120~SE*20*0001~"
         "ST*835*0002~BPR*H*0*C*NON************20261121~TRN*1*NOPAY77*1000000000~N1*PR*SAMPLE HEALTH PLAN~PLB*1000000003*20261231*L6:INT1*-1.5~SE*5*0002~"
         "GE*2*1~IEA*1*000000001~")
    pays = parse_835(s)
    assert len(pays) == 2, pays
    p = pays[0]
    assert p["payer_name"] == "SAMPLE HEALTH PLAN" and p["payer_id"] == "SHP01" and p["method"] == "ACH" and p["amount"] == 150.25
    assert p["date"] == "2026-11-20" and p["trace"] == "EFT123" and p["payee_npi"] == "1000000003" and len(p["claims"]) == 2
    c1, c2 = p["claims"]
    assert c1["visit_id"] == 19461428 and c1["status"] == "1" and c1["paid"] == 150.25 and c1["payer_claim_no"] == "PAYERCLM1"
    assert c1["rendering_npi"] == "1000000001" and c1["dos_from"] == "2026-10-01" and c1["lines"] == 1
    assert {(a["level"], a["grp"], a["carc"], a["amount"]) for a in c1["adjustments"]} == {("claim", "CO", "45", 129.75), ("line", "PR", "2", 20.0)}
    assert c2["status"] == "4" and c2["adjustments"][0]["carc"] == "170"
    q = pays[1]
    assert q["method"] == "NON" and q["amount"] == 0 and q["plb"] == [{"code": "L6", "ref": "INT1", "amount": -1.5}] and q["date"] == "2026-11-21"
    assert payment_key(p) == "SHP01|EFT123|150.25|2026-11-20"
    assert kind_of("3009416512.dat", "application/octet-stream") == "x12" and kind_of("a.pdf", "application/pdf") == "pdf"
    assert kind_of("x.csv", "text/csv") == "table" and kind_of("setup.exe", "application/x-msdos-program") == "other"
    pr, cl, ad = pdf_rows({"payments": [{"payer_name": "SAMPLE PLAN", "method": "paper check", "number": "C1", "date": "2026-10-01", "amount": 80}],
                           "claims": [{"payment_index": 0, "patient_control": "19461428A", "paid": 80, "status": "paid",
                                       "adjustments": [{"grp": "co", "carc": "45", "amount": 20}, {"grp": "CO", "carc": "45", "amount": 5}]}]}, "F1")
    assert pr[0]["method"] == "CHK" and pr[0]["payment_key"] == "pdf|SAMPLE PLAN|C1|80.00|2026-10-01" and cl[0]["visit_id"] == 19461428
    assert ad == [{"claim_key": cl[0]["claim_key"], "level": "claim", "line_no": 0, "cpt": None, "grp": "CO", "carc": "45", "amount": 25.0}]
    for s_ in DDL: assert not re.search(r"\b(drop|delete|truncate)\b", s_, re.I)
    print("era_archive selftest: ok")


if __name__ == "__main__":
    main()
