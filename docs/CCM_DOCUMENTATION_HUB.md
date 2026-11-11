# CCM documentation hub (started 2026-11-11)

William 11/11/2026: "new artifact called ccm documentation hub, this will be a fax archive and additional practice notes for CCM
supporting the ccm charges"; "a note or folder for each ccm charge that will contain a minimum of a statement note that the time was
spent and at a maximum any unlimited number of supporting documents and orders"; "do patient level data on the neon database but also
have an artifact pull from that and have patient data on it which is ok".

## The record
There is one record per patient per calendar month - the unit chronic care management is billed in. A record holds:
- the month's CCM charge lines (date, code, AdvancedMD visit and charge numbers, facility, provider);
- William's late-entry statement for that month - the least a record holds;
- any number of supporting items of that same month - the most.

## The statement (his words; codes confirmed by him 11/11/2026)
- 99487 alone: "greater than 60 minutes spent during <month> performing chart review, reviewing medication lists, faxes, labs, orders,
  referrals, phone conversations with nurses, the ARNP, the treatment team and family if needed, and on developing treatment plans for
  this patient."
- 99487 with 99489: the same sentence with "greater than 90 minutes".
- Any other set of CCM codes (99489 without 99487, 99489 billed more than once - more than 120 minutes -, 99490, 99491, 99439, 99437,
  G0506) has no ready-made statement: the record is flagged and William writes that note's statement himself on the hub page.
- Also flagged for his own eyes (never part of a "sign all"): 99487 billed more than once in a month (a duplicate charge to check), and a
  month with a line billed under another clinician than WEFFI (e.g. GARCIA).

## The note
`scripts/helpers/ccm_notes.py` lays the note out like his sample encounter note: the practice's letterhead, the patient, the location,
the provider, the charge date and codes, a section headed LATE ENTRY, the month's supporting items, and his signed stamp down the side.
- The top of the note is the practice's name, North Florida Senior Care. The late entry reads "LATE ENTRY for the charge dated <date>,
  for the month of <month>" and then the day it was written (William 11/11/2026; he and his attorney approved the wording that day).
- It is a late entry: dated the day it is written, never dated an earlier day, and it cannot be signed before it was written.
- The helper never signs for him. The stamp appears only when a signing (who, when) was recorded for that note; until then the note says
  DRAFT - NOT SIGNED. Whether the statement is true of that patient and month is his to review before he signs.
- A signed note is final (the database refuses a change): a correction is a new late entry.
- A month with no supporting item says so on the note: the statement stands alone (the least a record holds, as he decided).

## What a signature covers
`note_fields()` is the whole content of a note as plain text. At signing the day it is written (the practice's day, Eastern time) is
added, and the SHA-256 of that text in one fixed form (`canon()`: keys sorted, no spaces, UTF-8) is recorded with who signed and when.
`verify_signature()` recomputes it from the draft stored in Neon: a note whose content changed after he saw it, a forged hash, or a
signing dated another day than it was made is refused - nothing is ever signed in his name. The hub page computes the same text and
hash in JavaScript; an end-to-end run (the page in a browser, signing invented notes, the Python check on every signing) agreed on all
of them (11/11/2026).

## Supporting items
Each item has a kind, a date inside the record's month, a source and one line of summary. Kinds: `fax_lab`, `fax_order`,
`fax_hhc_plan_of_care`, `fax_other`, `phone_call`, `call_transcript`, `referral`, `prescription`, `email`, `pcc_record`, `other`.
Where they come from: the practice's RingCentral account (faxes received, and calls and their transcripts on the main number),
referrals and prescriptions sent, home health plans of care signed, e-mail, and later PointClickCare. An item from another month is
refused: a month is supported by that month's own records.

## Where it lives
Neon is the primary store. The documents are in `raw.documents`, source `ccm` (collections `patients`, `months`, `signed`, `evidence`,
`faxes`), written only through `tools/db/neon_db.py load-docs`; `tools/db/ccm_schema.sql` builds the `ccm.*` views over them
(`ccm.patients`, `ccm.months`, `ccm.signed_notes`, `ccm.notes`, `ccm.evidence`, `ccm.faxes`) and the trigger `ccm_signed_is_final` that
skips any later change to, or removal of, a signed note or its month. Applied to the practice database on 11/11/2026 after a rehearsal
on a temporary branch (`ccm-rehearsal-1111`) that tried to change and delete a signed note and its month (both skipped) and to change an
unsigned month (applied); the routines' role `ehpa_routine` reads the views. The hub page (`tools/db/ccm_hub_page.html`) is filled from
Neon and shows patient data - it is William's private page: its database is readable by editors only and writable by him only. Nothing
of a patient is written into this repository.

## How the notes are built
1. Every CCM charge line ever billed is already in Neon: `amd.charges` (the AdvancedMD history pulled 11/10/2026, void lines left out)
   - 4,177 patient-months on 660 charts, January 2023 to October 2026 (11/11/2026). Insurance: `amd.chart_plans`, the plan in force that
   month with the lowest billing sequence.
2. `python3 scripts/helpers/ccm_build.py charts` lists those charts in the workspace (`ccm/ccm_charts.json`).
3. `python3 scripts/helpers/ccm_patients.py --live` reads ONLY each patient's name, birth date and sex from AdvancedMD (getdemographic,
   read-only, one login, outside the scheduled routines' windows, resumable) into the workspace (`ccm/ccm_patients.jsonl`).
4. `python3 scripts/helpers/ccm_build.py build --out <dir>` writes the database documents (`<dir>/neon`) and the hub page's documents
   (`<dir>/hub`); a signed month is never rebuilt.
5. `python3 tools/db/neon_db.py load-docs --src <dir>/neon --source ccm` loads them; the hub page's documents go into its own database
   with the ArtifactData tool (collections `config` and `notes`).

## How he signs, and how a signing is recorded
- On the hub page he opens any note, reads it, ticks that he reviewed it and signs it; a flagged month without a ready-made statement
  takes his own statement first. "Sign the ready notes in <month>" and "Sign all ready notes" show how many notes and which statements,
  and sign only after he ticks that he reviewed them; flagged notes and notes still waiting for a patient's name are never in them.
  Only the page's owner sees the sign buttons; the page never signs on its own.
- A signing is written to the page's `signatures/<YYYY-MM>` document (who, when, the day written, the hash, which kind of note).
- To record them: read the page's `signatures` collection with ArtifactData list (out_dir), then
  `python3 scripts/helpers/ccm_build.py signatures --page <out_dir> --out <dir> --via <page url>` verifies each against the draft in Neon
  and writes `<dir>/signed/<id>.json` for the good ones (the refused ones are listed with the reason), and
  `python3 tools/db/neon_db.py load-docs --src <dir> --source ccm` records them - final from then on. Then mark those signings
  recorded on the page (`rec: true` on each) and rebuild the page's documents so its counts move.

## Not built yet
- The RingCentral search (faxes, calls): it needs the practice's RingCentral app key - the account's Developer Console access is turned
  off as of 11/11/2026 (the owner turns on "Developer Portal Access" for his role, or RingCentral support enables it);
  `scripts/helpers/ringcentral_fax.py` is on the census-inputs pull request.
- Supporting items on the notes (faxes, calls, transcripts, referrals, prescriptions, plans of care, PointClickCare).
- A scheduled routine that records the page's signings and adds each new month's CCM charges.

Offline proofs (no AdvancedMD, no RingCentral, no Neon, no network): `python3 tools/selftest/test_ccm_notes.py`,
`python3 tools/selftest/test_ccm_patients.py`, `python3 tools/selftest/test_ccm_build.py`.
