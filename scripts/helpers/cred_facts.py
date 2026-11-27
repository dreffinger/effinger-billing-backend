#!/usr/bin/env python3
# PLAIN ENGLISH (Credentialing facts - William 11/27/2026: "go through my entire gmail and get all the credentialing documents ... for me to
#   have quick access to stuff like pam dob ... gathering relevant info so i have it in one place and will be actionable when i ask you
#   questions here", then "so you can use the correct info to auto fill forms and to do appeals")
# Decides: nothing about a payer. It keeps the practice's credentialing FACTS in Neon (public.cred_facts): one row per fact - who it is about,
#   the field (npi, license_no, dea_exp, dob, payer_provider_id:<payer>, facility_credentialed_on:<facility> ...), the value, the date the
#   source says it was true, the email it came from, and whether a second, stronger model re-read that source and confirmed it. Forms and
#   appeals use ONLY verified facts; anything unverified or in conflict is shown as such. Leads to documents worth filing go to
#   public.cred_doc_leads, open items to public.cred_open_items.
# Rules it uses: Social Security numbers, card and bank numbers and passwords are never stored (the table refuses such fields and any
#   SSN-shaped value); dates of birth, home addresses and personal phones are stored as sensitivity 'restricted' (the owner asked for them
#   for form filling) and live only in the practice's HIPAA-covered database - never in this public repository, a board or a digest.
# Never touches: Gmail, Drive, any payer or portal. It loads what a Claude session gathered and answers questions from it.
# ---
"""Usage (NEON_DATABASE_URL, as for cred_vault.py):
  python3 credentialing/cred_facts.py load <workflow-output.json> [--found-by TEXT]   facts + checks from a Gmail sweep run
  python3 credentialing/cred_facts.py get <entity> [--field TEXT] [--topic TEXT] [--all]   the facts on file (verified first)
  python3 credentialing/cred_facts.py profile <entity>                    one line per field: the best value and its source
  python3 credentialing/cred_facts.py open-items [--topic TEXT]           what the emails say is still to do
  python3 credentialing/cred_facts.py leads [--entity E] [--unfiled]      documents found in Gmail, filed in the vault or not
entity: effinger | garland-g | group | payer:<name> | facility:<name>"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
A = sys.argv[1:]
def opt(name, default=None): return A[A.index(name) + 1] if name in A and A.index(name) + 1 < len(A) else default
def flag(name): return name in A

SECRET_FIELD = re.compile(r"ssn|social_security|password|passcode|secret|pin_code|routing|bank_account|card_number", re.I)
SSN_VALUE = re.compile(r"\b\d{3}[- .]\d{2}[- .]\d{4}\b")
CARD_VALUE = re.compile(r"\b(?:\d{4}[ -]){3}\d{4}\b")
RESTRICTED = re.compile(r"^(dob|home_address|personal_phone|personal_email)\b")
GMAIL = "https://mail.google.com/mail/?authuser=dreffinger@gmail.com#all/%s"


def db():
    sys.path.insert(0, HERE)
    saved = sys.argv[:]; sys.argv = sys.argv[:1]
    try:
        import cred_vault
    finally:
        sys.argv = saved
    return cred_vault.DB()


def clean(s, n=None):
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    return s[:n] if n else s


def safe(f):
    """A fact that must never be stored: secret fields, SSN- or card-shaped numbers anywhere in it."""
    blob = " ".join(str(f.get(k) or "") for k in ("field", "value", "evidence", "source_note"))
    return not (SECRET_FIELD.search(str(f.get("field") or "")) or SSN_VALUE.search(blob) or CARD_VALUE.search(blob))


def load(path, found_by):
    raw = open(path).read()
    j = json.loads(raw[raw.index("{"):]) if not raw.lstrip().startswith("{") else json.loads(raw)
    j = j.get("result", j)
    results = j.get("results") or []
    d = db(); n_f = n_skip = n_v = n_l = n_o = 0
    for r in results:
        ex = r.get("extract") or {}
        checks = {c.get("index"): c for c in ((r.get("verify") or {}).get("checks") or [])}
        for i, f in enumerate(ex.get("facts") or []):
            if not safe(f): n_skip += 1; continue
            c = checks.get(i); verified, status, note, value = False, "current", "", clean(f.get("value"), 2000)
            if c:
                v = c.get("verdict")
                if v == "confirmed": verified = True
                elif v == "corrected" and c.get("value") and safe({"value": c["value"]}):
                    note = "corrected by the check (sweep had: %s)" % value; value = clean(c["value"], 2000); verified = True
                elif v == "conflict": status = "conflict"; note = "the source also shows: %s" % clean(c.get("value"), 300)
                elif v == "not_found": status = "unconfirmed"
                note = clean((note + " " + clean(c.get("note"), 300)).strip(), 600)
            field = clean(f.get("field"), 120).lower()
            sens = "restricted" if (RESTRICTED.match(field) or f.get("sensitivity") == "restricted") else "normal"
            as_of = clean(f.get("as_of"))
            as_of = as_of if re.match(r"^\d{4}-\d{2}-\d{2}$", as_of) else None
            tid = clean(f.get("source_thread_id"), 64)
            rows = d.q("insert into public.cred_facts (practice, entity, topic, field, value, as_of, source_kind, source_ref, source_link, source_note, "
                       "evidence, confidence, verified, verified_by, verified_at, sensitivity, status, found_by) values "
                       "('ehpa',%s,%s,%s,%s,%s,'gmail',%s,%s,%s,%s,%s,%s,%s,case when %s then now() else null end,%s,%s,%s) "
                       "on conflict do nothing returning id",
                       [clean(f.get("entity"), 80).lower(), clean(f.get("topic") or r.get("topic"), 40), field, value, as_of,
                        clean(f.get("source_message_id") or tid, 64), (GMAIL % tid) if tid else None,
                        clean(f.get("source_note"), 300), clean(f.get("evidence"), 200), clean(f.get("confidence"), 10),
                        verified, ("opus check: " + note) if c else None, verified, sens, status, found_by])
            if rows: n_f += 1; n_v += 1 if verified else 0
        for doc in ex.get("documents") or []:
            if SSN_VALUE.search(json.dumps(doc)): continue
            rows = d.q("insert into public.cred_doc_leads (practice, entity, doc_type, filename, thread_id, message_id, doc_date, note, topic, found_by) "
                       "values ('ehpa',%s,%s,%s,%s,%s,%s,%s,%s,%s) on conflict do nothing returning id",
                       [clean(doc.get("entity"), 80).lower(), clean(doc.get("doc_type"), 120), clean(doc.get("filename"), 300),
                        clean(doc.get("thread_id"), 64), clean(doc.get("message_id"), 64), clean(doc.get("date"), 40),
                        clean(doc.get("note"), 400), r.get("topic"), found_by])
            if rows: n_l += 1
        for it in ex.get("open_items") or []:
            if SSN_VALUE.search(json.dumps(it)): continue
            rows = d.q("insert into public.cred_open_items (practice, entity, topic, item, deadline, status, source_thread_id, found_by) "
                       "values ('ehpa',%s,%s,%s,%s,%s,%s,%s) on conflict do nothing returning id",
                       [clean(it.get("entity"), 80).lower(), clean(it.get("topic") or r.get("topic"), 40), clean(it.get("item"), 600),
                        clean(it.get("deadline"), 60), clean(it.get("status"), 200), clean(it.get("source_thread_id"), 64), found_by])
            if rows: n_o += 1
    print("loaded %d new facts (%d verified), %d document leads, %d open items; %d refused as secrets" % (n_f, n_v, n_l, n_o, n_skip))


def show(rows, cols):
    for r in rows:
        print(" | ".join(str(x) if x is not None else "" for x in r))
    if not rows: print("(none)")


def main():
    cmd = A[0] if A else "help"
    if cmd == "load": return load(A[1], opt("--found-by", "gmail sweep"))
    if cmd not in ("get", "profile", "open-items", "leads"): sys.exit(__doc__)
    d = db()
    if cmd == "get":
        ent = A[1].lower(); where, params = ["practice='ehpa'", "entity=%s"], [ent]
        if opt("--field"): where.append("field like %s"); params.append(opt("--field").lower() + "%")
        if opt("--topic"): where.append("topic=%s"); params.append(opt("--topic"))
        if not flag("--all"): where.append("status <> 'superseded'")
        show(d.q("select field, value, case when verified then 'VERIFIED' else status end, as_of, source_note, source_link from public.cred_facts where "
                 + " and ".join(where) + " order by field, verified desc, as_of desc nulls last", params), None)
    elif cmd == "profile":
        show(d.q("select distinct on (field) field, value, case when verified then 'VERIFIED' else status end, as_of, source_link "
                 "from public.cred_facts where practice='ehpa' and entity=%s and status <> 'superseded' "
                 "order by field, verified desc, as_of desc nulls last, id desc", [A[1].lower()]), None)
    elif cmd == "open-items":
        where, params = ["practice='ehpa'", "not done"], []
        if opt("--topic"): where.append("topic=%s"); params.append(opt("--topic"))
        show(d.q("select topic, entity, item, deadline, status from public.cred_open_items where " + " and ".join(where)
                 + " order by topic, deadline nulls last", params), None)
    elif cmd == "leads":
        where, params = ["practice='ehpa'"], []
        if opt("--entity"): where.append("entity=%s"); params.append(opt("--entity").lower())
        if flag("--unfiled"): where.append("not filed")
        show(d.q("select entity, doc_type, filename, doc_date, filed, thread_id from public.cred_doc_leads where " + " and ".join(where)
                 + " order by entity, doc_type, doc_date", params), None)


if __name__ == "__main__":
    main()
