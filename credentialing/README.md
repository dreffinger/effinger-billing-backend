# Credentialing

Two tools and one place for every document:

- `cred_check.py`: the nightly check (NPPES changes, Medicare revalidation list, OIG exclusions, reminder windows).
- `cred_vault.py`: the document vault index in the practice's Neon database (list, get, add, store, folders, accounts,
  missing).
- `medicaid/`: the Medicaid playbook, the public status checker, and the kit for onboarding another practice.

## The vault: where every credentialing document lives

**This repository is public. It holds the method, never the documents.** Files live in the practice's Google Drive and
are indexed in the practice's Neon database (HIPAA-enabled). Nothing here stores an SSN, a date of birth, a card number,
a password or a signature.

### Drive layout (one per practice)

```
Credentialing Vault/
  00 Inbox - drop new documents here       anything new; Claude files it and indexes it
  1 <Practice name> (practice)/            Medicaid · Medicare · Payer contracts and enrollments ·
                                           NPI tax and business · Permits and insurance · Correspondence
  2 <Clinician> /                          License · DEA · Board certification and CAQH · Malpractice · Medicaid ·
                                           Medicare and payers · Background screening · Hospital privileges ·
                                           Identity documents (restricted) · signature (private)
  3 <APRN or PA> /                         the same, plus Collaboration agreements and
                                           Discipline history (restricted) when there is any
```

"Restricted" folders have inherited sharing turned off, so only the owner can open them. Identity documents (SS cards,
driver's licenses, passports), any page that shows an SSN, and discipline or monitoring records go there.

### Neon tables (schema `public`)

| Table / view | One row per | Notes |
|---|---|---|
| `cred_documents` | document | practice, entity (person or `group`), category, title, status, doc_date, expiration_date, sensitivity (`normal`/`restricted`), Drive file and folder ids, source, notes; optional copy of the bytes in `content` (never for restricted rows) |
| `cred_document_index` | document | the readable view: title, status, dates, sensitivity, Drive link, whether a copy is in Neon |
| `cred_folders` | Drive folder | practice, entity, category, folder id, restricted flag |
| `cred_accounts` | portal account | site, url, username, owner, help page; **no password column on purpose**: passwords live in the owner's password manager |
| `cred_providers`, `cred_enrollments`, `cred_tasks`, `cred_expiring_90d`, `cred_todo_ranked` | (earlier) | people, enrollments per payer, task list, expiry view |

### Intake rule (how a new document gets filed)

1. William uploads it in a chat, emails it to himself, drops it in **00 Inbox**, or scans it into the ScanSnap folder
   "aa claude folders / scansnap uploads / scanscnap credentialing files uploads" (sorted by `billing/era_input/scan_intake.py`,
   which reads each page, splits a multi-document scan and names the vault folder and document id; steps in
   `billing/era_input/README.md`, "Drive upload folders").
2. Claude reads it and decides **who** (practice or which clinician), **category**, **title**, **dates** (issue and
   expiry) and **sensitivity** (anything with an SSN, DOB with photo, card number, or discipline record = restricted).
3. Claude saves it into that Drive folder (restricted ones into the restricted folder), then indexes it:
   `cred_vault.py add --id <entity>-<what>-<yyyy> --entity <who> --category <cat> --title "..." --drive-id <id> --folder-id <id> [--expires ...] [--restricted]`.
4. Duplicates are not filed twice (compare sha256 with what is on file); an older version is kept with status
   `superseded by <id>`.
5. Claude never types an SSN, DOB, DEA or card number into a chat, board, digest, commit or column.

### Daily use

```bash
python3 credentialing/cred_vault.py list --entity garcia            # everything on file for one person, with Drive links
python3 credentialing/cred_vault.py list --expiring 90              # what expires in the next 90 days
python3 credentialing/cred_vault.py missing                         # what a complete file still lacks, per person
python3 credentialing/cred_vault.py get effinger-mpa-renewal-2026   # the copy in Neon, or the Drive link
python3 credentialing/cred_vault.py folders                         # where to file each kind of document
python3 credentialing/cred_vault.py accounts                        # portal usernames (no passwords)
```

The connection string comes from `NEON_DATABASE_URL` (the routines have it) or `secrets/neon_database_url`
(git-ignored). In a chat session without it, the same SQL runs through the Neon connector.

### A new practice

Add `practices/<code>/`, create the same Drive layout under that practice's own Drive, insert its folder ids into
`cred_folders` with `practice = '<code>'`, and send the practice the two lists in `medicaid/practice_kit.md`.
