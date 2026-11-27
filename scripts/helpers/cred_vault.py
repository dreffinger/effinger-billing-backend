#!/usr/bin/env python3
# PLAIN ENGLISH (Credentialing vault - William 11/27/2026: "keep all these files ... using drive and the neon database so we can pull any
#   of these credentialing documents as needed", "start uploading things like licenses and ssn cards and these need to go in drive or neon")
# Decides: nothing about a payer. It keeps the INDEX of every credentialing document in the practice's Neon database
#   (public.cred_documents, one row per document: who, category, title, status, dates, sensitivity, the Google Drive file it lives in),
#   the Drive folder map (public.cred_folders) and the portal account inventory (public.cred_accounts: site, username, owner - never a
#   password). It can also keep a COPY of a non-restricted document's bytes in Neon, so a document can be pulled even without Drive.
# Rules it uses: The file itself lives in the practice's Drive "Credentialing Vault" (one folder per person and category; "restricted"
#   folders for identity documents, SSN-bearing pages and discipline history). Restricted documents are indexed but their bytes are NEVER
#   stored in Neon, and no SSN, DOB or card number is ever typed into any column. Passwords are never stored anywhere here.
#   Works for any practice: every row carries a practice code (default ehpa).
# Never touches: Drive itself (Claude files documents into Drive with the Drive connector, then registers them here), any payer or portal.
# ---
"""Usage (connection string from NEON_DATABASE_URL or <repo>/secrets/neon_database_url, git-ignored):
  python3 credentialing/cred_vault.py list [--practice ehpa] [--entity garland-g] [--category medicaid] [--q text] [--expiring 90]
  python3 credentialing/cred_vault.py get <doc-id> [--out file.pdf]          bytes from Neon if stored, else the Drive link
  python3 credentialing/cred_vault.py add --id <doc-id> --entity <who> --category <cat> --title "<title>" [--drive-id <id>]
          [--folder-id <id>] [--status "<s>"] [--doc-date YYYY-MM-DD] [--expires YYYY-MM-DD] [--restricted] [--source "<s>"]
          [--notes "<n>"] [--file <path>] [--replace]                        --file stores a copy in Neon (refused for restricted rows);
                                                                             an id already used for another Drive file is refused unless --replace
  python3 credentialing/cred_vault.py store <doc-id> <path>                   attach a local copy to an existing non-restricted row
  python3 credentialing/cred_vault.py folders [--practice ehpa]               the Drive folder for every person and category
  python3 credentialing/cred_vault.py accounts [--practice ehpa]              portal usernames and help pages (no passwords)
  python3 credentialing/cred_vault.py missing [--practice ehpa]               required documents not yet on file (see credentialing/README.md)
"""
import base64, hashlib, json, mimetypes, os, re, sys, urllib.parse, urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = sys.argv[1:]
def opt(name, default=None): return A[A.index(name) + 1] if name in A and A.index(name) + 1 < len(A) else default
def flag(name): return name in A

# What a complete file looks like, per kind of entity (credentialing/README.md explains each item).
REQUIRED = {
    "individual": ["license", "dea", "board-caqh", "malpractice", "screening", "medicaid", "medicare-payers", "identity"],
    "aprn-pa": ["license", "dea", "board-caqh", "malpractice", "screening", "medicaid", "medicare-payers", "identity", "collaboration"],
    "group": ["business", "medicaid", "medicare", "payers", "permits-insurance"],
}
ENTITY_KIND = {"group": "group", "garland-g": "aprn-pa", "effinger": "individual"}   # extend per practice


def database_url():
    for k in ("NEON_DATABASE_URL", "DATABASE_URL"):
        v = re.sub(r"\s+", "", os.environ.get(k) or "")
        if v.startswith("postgres"): return v
    p = os.path.join(REPO, "secrets", "neon_database_url")
    if os.path.isfile(p):
        v = re.sub(r"\s+", "", open(p, encoding="utf-8-sig").read())
        if v.startswith("postgres"): return v
    sys.exit("cred_vault: no connection string - set NEON_DATABASE_URL or write it to secrets/neon_database_url (git-ignored)")


class DB:
    """Neon's HTTPS SQL endpoint (port 443), %s placeholders; the wire driver when psycopg is installed."""
    def __init__(self):
        self.url = database_url(); self.conn = None
        try:
            import psycopg
            self.conn = psycopg.connect(self.url, autocommit=True, connect_timeout=10)
        except Exception:
            self.conn = None
        self.host = urllib.parse.urlparse(self.url).hostname

    def q(self, sql, params=None):
        if self.conn is not None:
            cur = self.conn.cursor(); cur.execute(sql, params or None)
            return [list(r) for r in cur.fetchall()] if cur.description else []
        n = [0]
        def repl(m): n[0] += 1; return "$%d" % n[0]
        text = re.sub(r"%s", repl, sql) if params else sql
        body = json.dumps({"query": text, "params": [p if (p is None or isinstance(p, (int, float, bool))) else str(p) for p in (params or [])]}).encode()
        req = urllib.request.Request("https://%s/sql" % self.host, data=body, method="POST",
                                     headers={"Neon-Connection-String": self.url, "Content-Type": "application/json", "Neon-Array-Mode": "true"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r: j = json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")
            sys.exit("cred_vault: database refused the statement: " + msg.replace(self.url, "<connection string>")[:300])
        return j.get("rows") or []


def table(rows, cols):
    if not rows: print("(none)"); return
    w = [min(max(len(str(c)), *(len(str(r[i] if r[i] is not None else "")) for r in rows)), 60) for i, c in enumerate(cols)]
    print("  ".join(str(c).ljust(w[i]) for i, c in enumerate(cols)))
    for r in rows: print("  ".join(str(r[i] if r[i] is not None else "")[:60].ljust(w[i]) for i in range(len(cols))))


def store_bytes(db, doc_id, path):
    row = db.q("select sensitivity from public.cred_documents where id = %s", [doc_id])
    if not row: sys.exit("cred_vault: no document %s" % doc_id)
    if (row[0][0] or "normal") == "restricted":
        sys.exit("cred_vault: %s is restricted - its file stays in the restricted Drive folder only" % doc_id)
    data = open(path, "rb").read()
    if len(data) > 8 * 1024 * 1024: sys.exit("cred_vault: %s is over 8 MB - keep it in Drive only" % path)
    db.q("update public.cred_documents set content = decode(%s, 'base64'), sha256 = %s, size_bytes = %s, mime_type = %s, updated_at = now() where id = %s",
         [base64.b64encode(data).decode(), hashlib.sha256(data).hexdigest(), len(data), mimetypes.guess_type(path)[0] or "application/octet-stream", doc_id])
    print("stored %s (%d bytes) in Neon" % (doc_id, len(data)))


def main():
    cmd = A[0] if A else "list"
    practice = opt("--practice", "ehpa")
    db = DB()
    if cmd == "list":
        where, params = ["practice = %s"], [practice]
        if opt("--entity"): where.append("entity = %s"); params.append(opt("--entity"))
        if opt("--category"): where.append("category = %s"); params.append(opt("--category"))
        if opt("--q"): where.append("(title ilike %s or coalesce(notes,'') ilike %s)"); params += ["%" + opt("--q") + "%"] * 2
        if opt("--expiring"): where.append("expiration_date is not null and expiration_date <= current_date + (%s)::int"); params.append(int(opt("--expiring")))
        rows = db.q("select id, entity, category, title, status, expiration_date, sensitivity, copy_in_neon, link from public.cred_document_index where "
                    + " and ".join(where) + " order by entity, category, title", params)
        table(rows, ["id", "entity", "category", "title", "status", "expires", "sensitivity", "in_neon", "link"])
    elif cmd == "get":
        doc_id = A[1] if len(A) > 1 else sys.exit(__doc__)
        r = db.q("select coalesce(title, file_name), case when content is null then null else encode(content, 'base64') end, file_name, "
                 "coalesce('https://drive.google.com/file/d/' || drive_file_id || '/view', drive_url) from public.cred_documents where id = %s", [doc_id])
        if not r: sys.exit("cred_vault: no document %s" % doc_id)
        title, b64, fname, link = r[0]
        if b64:
            out = opt("--out", fname or (doc_id + ".bin"))
            open(out, "wb").write(base64.b64decode(b64)); print("wrote %s (%s)" % (out, title))
        else:
            print("%s: no copy in Neon - open it in Drive: %s" % (title, link or "(no link on file)"))
    elif cmd == "add":
        need = ["--id", "--entity", "--category", "--title"]
        if any(not opt(n) for n in need): sys.exit(__doc__)
        drive = opt("--drive-id")
        clash = db.q("select drive_file_id from public.cred_documents where id = %s", [opt("--id")])
        if clash and clash[0][0] and drive and clash[0][0] != drive and not flag("--replace"):
            sys.exit("cred_vault: %s already indexes another Drive file - pick a new --id (or pass --replace to supersede it)" % opt("--id"))
        db.q("insert into public.cred_documents (id, practice, provider, category, doc_type, title, file_name, status, doc_date, expiration_date, sensitivity, "
             "drive_file_id, drive_folder_id, source, notes, uploaded_at, updated_at) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now(),now()) "
             "on conflict (id) do update set provider=excluded.provider, category=excluded.category, doc_type=excluded.doc_type, title=excluded.title, status=excluded.status, "
             "doc_date=excluded.doc_date, expiration_date=excluded.expiration_date, sensitivity=excluded.sensitivity, drive_file_id=excluded.drive_file_id, "
             "drive_folder_id=excluded.drive_folder_id, source=excluded.source, notes=excluded.notes, updated_at=now()",
             [opt("--id"), practice, opt("--entity"), opt("--category"), opt("--type") or opt("--category"), opt("--title"),
              opt("--file-name") or (os.path.basename(opt("--file")) if opt("--file") else opt("--title")),
              opt("--status", "current"), opt("--doc-date"), opt("--expires"), "restricted" if flag("--restricted") else "normal", drive, opt("--folder-id"),
              opt("--source"), opt("--notes")])
        print("indexed %s" % opt("--id"))
        if opt("--file"): store_bytes(db, opt("--id"), opt("--file"))
    elif cmd == "store":
        if len(A) < 3: sys.exit(__doc__)
        store_bytes(db, A[1], A[2])
    elif cmd == "folders":
        table(db.q("select entity, coalesce(category,'(person folder)'), title, restricted, 'https://drive.google.com/drive/folders/' || drive_folder_id "
                   "from public.cred_folders where practice = %s order by entity, category nulls first", [practice]),
              ["entity", "category", "folder", "restricted", "link"])
    elif cmd == "accounts":
        table(db.q("select entity, site, username, owner, url, notes from public.cred_accounts where practice = %s order by entity, site", [practice]),
              ["entity", "site", "username", "owner", "url", "notes"])
    elif cmd == "missing":
        have = {}
        for ent, cat in db.q("select provider, category from public.cred_documents where practice = %s and category is not null "
                             "and coalesce(status,'') not ilike 'superseded%%' and coalesce(file_name,'') not in ('MISSING','pending upload')", [practice]):
            have.setdefault(ent, set()).add(cat)
        for ent, kind in ENTITY_KIND.items():
            gaps = [c for c in REQUIRED[kind] if c not in have.get(ent, set())]
            print("%-10s %-11s %s" % (ent, kind, ("missing: " + ", ".join(gaps)) if gaps else "complete"))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
