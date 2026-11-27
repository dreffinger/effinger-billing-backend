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
#   (how each payer pays), amd.era_denial_patterns (the most frequent denial reasons by payer) and amd.era_paid_not_posted (claims the payer's
#   own remit shows paid that AdvancedMD never posted - still open, or written off) answer the questions.
# Rules it uses: an 835 is read by its own separators (ISA); a file read before (same sha256) is not read twice; a payment is keyed by payer +
#   trace number + amount + date, so the same remittance downloaded twice (Optum's "(1)" copies) is one payment. A PDF payment is keyed by payer
#   + payment number + date (one payment however many printouts show it); a PDF of a payment an 835 already holds is not filed twice; a check
#   that is not from an insurer (a patient's bill-pay check) is kept but left out of "how each payer pays".
# Never touches: AdvancedMD, the files themselves (read-only in Drive), the public repository - nothing it reads is written to git.
# ---
"""Usage (NEON_DATABASE_URL, as for credentialing/cred_vault.py):
  python3 billing/era_input/era_archive.py inventory <drive-listing.json>... [--folder-name NAME]   Drive files -> amd.era_files
  python3 billing/era_input/era_archive.py pending [--kind x12|pdf|other]                            what is not read yet
  python3 -I billing/era_input/era_archive.py parse <file> --drive-id <id>                             one 835 -> the tables
  python3 -I billing/era_input/era_archive.py parse-dir <dir>      every <drive-id>.bin / .dat / .835 file in <dir> (named by Drive id)
  python3 -I billing/era_input/era_archive.py load-pdf-json <dir> [--reload]  the remit-pdf-archive JSON files (one per PDF: payments + claims);
                                                 --reload clears what earlier PDF loads filed (never the 835 rows) and files them again
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
    # the bank's ACH trace where a portal print shows it next to the payer's own payment number (Optum Pay), and payments that are not insurance
    "alter table amd.era_payments add column if not exists ach_trace text",
    "alter table amd.era_payments add column if not exists not_insurance boolean default false",
    """create table if not exists amd.era_adjustments (claim_key text, level text, line_no int, cpt text, grp text, carc text,
         amount numeric(12,2), primary key (claim_key, level, line_no, grp, carc))""",
    # how each payer pays: ERA files + the ERA Center's own check list (run_alerts.py fills amd.era_checks)
    """create or replace view amd.payer_payment_methods as
       select payer_name, method, count(*) payments, sum(amount) dollars, min(payment_date) first_payment, max(payment_date) last_payment,
              'era file' source from amd.era_payments where not coalesce(not_insurance, false) group by payer_name, method
       union all
       select era_payer, payment_code, count(*), sum(amount), min(check_date), max(check_date), 'era center'
       from amd.era_checks group by era_payer, payment_code""",
    # paid on the payer's own remit, never posted in AdvancedMD: every archived claim the payer paid, against AdvancedMD's payments (by check
    # number, then by the payer's carrier on that visit near the payment date, then by the same amount on the visit) and its balance today
    """create or replace view amd.era_paid_not_posted as
       with c as (
         select p.payer_name, p.method, p.trace_number, p.payment_date, p.source, c.visit_id, c.patient_control, c.paid, c.dos_from,
                (select m.carrier_code from amd.era_payer_map m where upper(m.era_payer) = upper(p.payer_name) limit 1) carrier
         from amd.era_claims c join amd.era_payments p using (payment_key)
         where c.paid > 0 and c.visit_id is not null and not coalesce(p.not_insurance, false)),
       m as (
         select c.*,
                exists (select 1 from amd.insurance_payments i where upper(i.check_number) = upper(c.trace_number)) by_check,
                (select sum(i.paid) from amd.insurance_payments i where i.visit_id = c.visit_id and i.carrier = c.carrier
                   and i.payment_date between c.payment_date - 10 and c.payment_date + 180) by_carrier,
                exists (select 1 from amd.insurance_payments i where i.visit_id = c.visit_id and abs(i.paid - c.paid) < 0.02) by_amount,
                (select sum(o.insurance_balance) from amd.charge_outcomes o where o.visit_id = c.visit_id::text) amd_ins_balance,
                (select sum(o.written_off) from amd.charge_outcomes o where o.visit_id = c.visit_id::text) amd_written_off,
                (select string_agg(distinct o.writeoff_codes, ' ') from amd.charge_outcomes o where o.visit_id = c.visit_id::text) amd_writeoff_codes,
                (select string_agg(distinct o.denial_codes, ' ') from amd.charge_outcomes o where o.visit_id = c.visit_id::text) amd_denials,
                (select string_agg(distinct o.current_carrier, ' ') from amd.charge_outcomes o where o.visit_id = c.visit_id::text) amd_carrier,
                (select string_agg(distinct o.paying_carriers, ' ') from amd.charge_outcomes o where o.visit_id = c.visit_id::text) amd_paying
         from c)
       select payer_name, carrier, method, trace_number, payment_date, source, visit_id, patient_control, dos_from, paid, amd_carrier, amd_ins_balance,
              amd_written_off, amd_writeoff_codes, amd_denials,
              case when by_check or coalesce(by_carrier, 0) >= paid - 0.02 or by_amount
                     or (carrier is not null and coalesce(amd_paying, '') like '%' || carrier || '%') then 'posted'
                   when amd_ins_balance is null then 'visit not in the AdvancedMD copy'
                   when amd_ins_balance > 0 then 'paid - balance still open in AdvancedMD'
                   when coalesce(amd_written_off, 0) > 0 then 'paid - written off in AdvancedMD'
                   else 'paid - not posted' end status
       from m""",
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


def payer_key(name):
    """FLORIDA BLUE / Florida Blue / "Health Options, Inc." -> one spelling for the payment key."""
    return re.sub(r"[^A-Z0-9]+", " ", str(name or "").upper()).strip() or "?"


def pdf_rows(j, did):
    """One extracted PDF (the remit-pdf-archive JSON: payments[] + claims[]) -> (payments, claims, adjustments) rows for the tables.
    A payment is keyed by payer + payment number + date when the number is printed, so the same payment read from a single-claim printout,
    a check summary and a portal list is ONE payment (the amount and method fill in from whichever copy prints them). A claim is keyed by its
    payment + claim number + paid amount, so the same claim on two printouts is one claim (a reversal pays the negative and stays apart)."""
    pays, keys = [], []
    not_ins = "not an insurance payer" in str(j.get("notes") or "").lower()
    for p in j.get("payments") or []:
        raw = str(p.get("method") or "").strip().upper()
        meth = METHOD_CODE.get(raw) or METHOD_CODE.get(raw.split(" ")[0]) or (
            "unknown" if ("CHECK" in raw and ("EFT" in raw or "ACH" in raw)) else      # Availity's "Check/EFT" label names no method
            "CHK" if "CHECK" in raw else "VCC" if "CARD" in raw else "ACH" if ("EFT" in raw or "ACH" in raw) else "NON" if "NO PAY" in raw else "unknown")
        amt = p.get("amount"); amt = num(amt) if amt is not None else None
        date = p.get("date") if re.match(r"^\d{4}-\d{2}-\d{2}$", str(p.get("date") or "")) else None
        num_ = str(p.get("number") or "").strip()
        pk = ("pdf|%s|%s|%s" % (payer_key(p.get("payer_name")), num_, date or "?") if num_ else
              "pdf|%s|%s|%s|%s" % (payer_key(p.get("payer_name")), did, "%.2f" % amt if amt is not None else "?", date or "?"))
        keys.append(pk)
        pays.append(dict(payment_key=pk, drive_file_id=did, payer_name=p.get("payer_name"), payer_id=p.get("payer_id"), payee_name=p.get("payee_name"),
                         payee_npi=p.get("payee_npi"), method=meth, amount=amt, payment_date=date, trace_number=num_ or None,
                         ach_trace=str(p.get("ach_trace") or "").strip() or None, not_insurance=not_ins))
    claims, adj = [], []
    for k, c in enumerate(j.get("claims") or []):
        i = c.get("payment_index")
        pk = keys[i] if isinstance(i, int) and 0 <= i < len(keys) else (keys[0] if len(keys) == 1 else "pdf|%s|no payment" % did)
        pc = str(c.get("patient_control") or "").strip(); m = re.match(r"^(\d{7,9})([A-Z]{0,2})$", pc)
        pcn = str(c.get("payer_claim_no") or "").strip()
        ck = ("%s|%s|%s|%.2f" % (pk, pc or "?", pcn, num(c.get("paid"))) if (pc and pcn) else "%s|%s|%s|%d" % (pk, pc or "?", pcn or "?", k))
        dt = lambda v: v if re.match(r"^\d{4}-\d{2}-\d{2}$", str(v or "")) else None
        claims.append(dict(claim_key=ck, payment_key=pk, patient_control=pc or None, visit_id=int(m.group(1)) if m else None, status_code=c.get("status"),
                           charge=num(c.get("charge")), paid=num(c.get("paid")), patient_resp=num(c.get("patient_resp")), filing=None,
                           payer_claim_no=pcn or None, dos_from=dt(c.get("dos_from")), dos_to=dt(c.get("dos_to")), patient_name=c.get("patient_name"),
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
    # a PDF of a payment the 835 files already hold (same payment number and amount): the 835 is the record, the PDF adds nothing
    twins = {r[0] for r in d.q("""select x.payment_key from jsonb_to_recordset(%s::jsonb) as x(payment_key text, trace_number text, amount numeric)
                                   join amd.era_payments e on e.source = '835' and e.trace_number = x.trace_number
                                    and (x.amount is null or e.amount = x.amount)""", [json.dumps(pays)])} if pays else set()
    keep = [p for p in pays if p["payment_key"] not in twins]
    claims = [c for c in claims if c["payment_key"] not in twins]
    keepc = {c["claim_key"] for c in claims}; adj = [a for a in adj if a["claim_key"] in keepc]
    if keep:
        d.q("""insert into amd.era_payments (payment_key, drive_file_id, payer_name, payer_id, payee_name, payee_npi, method, amount, payment_date,
                 trace_number, ach_trace, not_insurance, claims, source)
               select payment_key, drive_file_id, payer_name, payer_id, payee_name, payee_npi, method, amount, payment_date, trace_number, ach_trace,
                 not_insurance, 0, 'pdf' from jsonb_to_recordset(%s::jsonb) as x(payment_key text, drive_file_id text, payer_name text, payer_id text,
                 payee_name text, payee_npi text, method text, amount numeric, payment_date date, trace_number text, ach_trace text, not_insurance boolean)
               on conflict (payment_key) do update set
                 amount = coalesce(amd.era_payments.amount, excluded.amount),
                 method = case when amd.era_payments.method = 'unknown' then excluded.method else amd.era_payments.method end,
                 ach_trace = coalesce(amd.era_payments.ach_trace, excluded.ach_trace),
                 payer_id = coalesce(amd.era_payments.payer_id, excluded.payer_id),
                 payee_npi = coalesce(amd.era_payments.payee_npi, excluded.payee_npi)""", [json.dumps(keep)])
    if claims:
        d.q("""insert into amd.era_claims (claim_key, payment_key, patient_control, visit_id, status_code, charge, paid, patient_resp, filing, payer_claim_no,
                 dos_from, dos_to, patient_name, rendering_npi, lines) select claim_key, payment_key, patient_control, visit_id, status_code, charge, paid,
                 patient_resp, filing, payer_claim_no, dos_from, dos_to, patient_name, rendering_npi, lines
               from jsonb_populate_recordset(null::amd.era_claims, %s::jsonb) on conflict (claim_key) do nothing""", [json.dumps(claims)])
    if adj:
        d.q("""insert into amd.era_adjustments select claim_key, level, line_no, cpt, grp, carc, amount
               from jsonb_populate_recordset(null::amd.era_adjustments, %s::jsonb) on conflict do nothing""", [json.dumps(adj)])
    note = str(j.get("class") or "")[:40] + ("; %d payment(s) already in the 835 files" % len(twins) if twins else "")
    d.q("update amd.era_files set status='read', kind='pdf', payments=%s, claims=%s, parsed_at=now(), note=%s where drive_file_id=%s",
        [len(keep), len(claims), note, did])
    return len(keep), len(claims)


def recount(d):
    """Each payment's claim count, after every file is in (PDF copies of one payment add their claims to it)."""
    d.q("""update amd.era_payments p set claims = c.n from (select payment_key, count(*) n from amd.era_claims group by 1) c
           where c.payment_key = p.payment_key and p.source = 'pdf' and p.claims is distinct from c.n""")


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
        if "--reload" in A:
            d.q("""delete from amd.era_adjustments a using amd.era_claims c where c.claim_key = a.claim_key and c.payment_key like 'pdf|%%'""")
            d.q("delete from amd.era_claims where payment_key like 'pdf|%%'")
            d.q("delete from amd.era_payments where source = 'pdf'")
        tot = [0, 0, 0]
        for path in sorted(glob.glob(os.path.join(A[1], "*.json"))):
            p, c = load_pdf_json(d, path); tot[0] += 1; tot[1] += p; tot[2] += c
        recount(d)
        n = d.q("select count(*), (select count(*) from amd.era_claims where payment_key like 'pdf|%%') from amd.era_payments where source = 'pdf'")[0]
        print("%d PDF file(s) read: %d payment row(s), %d claim row(s); after merging copies: %d payment(s), %d claim(s)" % tuple(tot + [int(x) for x in n])); return
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
    assert pr[0]["method"] == "CHK" and pr[0]["payment_key"] == "pdf|SAMPLE PLAN|C1|2026-10-01" and cl[0]["visit_id"] == 19461428
    assert ad == [{"claim_key": cl[0]["claim_key"], "level": "claim", "line_no": 0, "cpt": None, "grp": "CO", "carc": "45", "amount": 25.0}]
    # the same payment on a single-claim printout (no total, other spelling) and on the check summary: one payment key, one claim key
    one = {"payments": [{"payer_name": "FLORIDA BLUE", "method": "ACH", "number": "423000001", "date": "2026-08-05", "amount": None}],
           "claims": [{"payment_index": 0, "patient_control": "19461430A", "payer_claim_no": "P9", "paid": 33.86}]}
    two = {"payments": [{"payer_name": "Florida Blue", "method": "Check/EFT", "number": "423000001", "date": "2026-08-05", "amount": 101.58}],
           "claims": [{"payment_index": 0, "patient_control": "19461431A", "payer_claim_no": "P8", "paid": 67.72},
                      {"payment_index": 0, "patient_control": "19461430A", "payer_claim_no": "P9", "paid": 33.86}]}
    a, ac, _ = pdf_rows(one, "F2"); b, bc, _ = pdf_rows(two, "F3")
    assert a[0]["payment_key"] == b[0]["payment_key"] and ac[0]["claim_key"] == bc[1]["claim_key"] and bc[0]["claim_key"] != bc[1]["claim_key"]
    assert a[0]["method"] == "ACH" and b[0]["method"] == "unknown" and a[0]["amount"] is None and b[0]["amount"] == 101.58  # the load merges them
    rev = {"payments": [{"payer_name": "X", "number": "N1", "date": "2026-08-05", "amount": 0}],
           "claims": [{"payment_index": 0, "patient_control": "19461432A", "payer_claim_no": "P7", "paid": 50},
                      {"payment_index": 0, "patient_control": "19461432A", "payer_claim_no": "P7", "paid": -50}]}
    assert len({c["claim_key"] for c in pdf_rows(rev, "F4")[1]}) == 2          # a reversal and its original stay two claims
    pt = {"notes": "Check image only. Not an insurance payer: a bill-pay check.", "payments": [{"payer_name": "Wealth Co", "method": "CHK", "number": "9", "amount": 4}]}
    assert pdf_rows(pt, "F5")[0][0]["not_insurance"] is True and pdf_rows(one, "F2")[0][0]["not_insurance"] is False
    for s_ in DDL: assert not re.search(r"\b(drop|delete|truncate)\b", s_, re.I)
    print("era_archive selftest: ok")


if __name__ == "__main__":
    main()
