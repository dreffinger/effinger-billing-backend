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

## Diagnoses on every note, and the addenda (11/12/2026)
William 11/12/2026: "on all these signed notes add to them the diagnoses that were included with the charge in a diagnosis with icd10
number as was shown in the original sample note"; "add this as an addendum to the note, if needed i can sign the addendums later after they
are added, for new notes going forward always include the individual patient icd10 diagnosis list, this is the first thing medicare looks
for [...] in the audit of ccm is that they have 2 or more qualifying chronic medical conditions, then that the time was spent and attested
to"; "icd 10 diagnoses lists definitely need to be downloaded for each patient chart from advanced md and kept in each chart folder in the
database".
- Where the diagnoses come from: the AdvancedMD history already in Neon holds every charge's ICD-10 codes (`raw.documents` source
  `amd_history`, collection `chargedetail`, `body.charges[].dx`, with the dot, in AdvancedMD's order - about 5.8 on a CCM line; all 7,055
  CCM lines have them). The typed `amd.charge_details.diagnoses` is empty and is not used. A note's charge lines carry AdvancedMD's charge
  number without the `charge` prefix that chargedetail's id carries: checked 11/12/2026, all 7,055 CCM lines of the 4,177 signed notes match
  by chart and charge number, with the same code, date and visit.
- The words: the official CMS ICD-10-CM code files (fiscal years 2023 to 2027), the newest year's description, and a code retired since keeps
  its last one. ONE reference document holds the codes that appear on any charge, each with its description and the fiscal year it comes
  from (`raw.documents` source `ref`, collection `icd10cm`, doc_id `descriptions`; view `ccm.icd10`).
- Every chart's diagnosis list: view `ccm.chart_diagnoses` (chart, code, description, first and last charge date, charge lines) over the
  chargedetail documents, the lines that are not void - every chart in the history (11,050), not only CCM.
- New notes from now on carry the month's ICD-10 diagnoses in their fields (`diagnoses`: code and description - the codes on that month's
  CCM charge lines, the 99487 line first, then 99489, each code once) and show them as a "Diagnoses (ICD-10)" table above the late entry. A
  month whose charge carries fewer than two is flagged: Medicare looks first for two or more qualifying chronic conditions - he checks the
  chart's diagnosis list. A signed note keeps the fields he signed (the hub page shows its stored draft), so every signing still verifies.
- Every signed note gets a dated ADDENDUM - a signed note is never edited. `ccm_notes.addendum_fields()` is its whole content: the note it
  adds to (its id, the day it was written, the hash he signed), that note's CCM charge lines and the diagnoses on them with their
  descriptions. It is signed exactly like a note (the hash of its fields with the day written), but it carries no statement (a signing that
  brings one is refused) and it is never dated before the note. On paper it is a sheet of its own under the note: "ADDENDUM - written
  <day>, to the late entry for the charge dated ..., for the month of ...", a "Diagnoses on the CCM charge (ICD-10)" table, the line "The
  late entry was written and signed <day> ... and is final: this addendum adds to it and changes nothing in it", and its own stamp down the
  side - signed, or ADDENDUM - NOT SIGNED. One with fewer than two diagnoses is flagged; the hub page shows that chart's whole diagnosis list
  beside it, and it is never part of "Sign all addenda".
- A signed addendum is final like a signed note: the trigger skips any change to, or removal of, an `addenda_signed` document and its
  `addenda` draft (views `ccm.addenda`, `ccm.signed_addenda`), and the hub page shows the fields he signed (its `addenda_signed`
  document): `addenda` never rebuilds a signed one from today's charge lines or descriptions. Rehearsed 11/12/2026 on a throwaway local
  PostgreSQL 16 with invented rows: edit, edit without a new fingerprint, rename, move, delete and an upsert of a signed addendum or its
  draft all skipped; an unsigned draft rebuilt and removed; a reload that only touches loaded_by applied; the signed-note rules unchanged.
- Next, his words: "after that we need to find all supporting documentation and add it later as a dated addendum at that time [...] once we
  get records dated back and access to those on ring central or from pcc" - the supporting documents become further dated addenda (a doc_id
  of their own beside `_dx`).
- Dry run 11/12/2026 (read-only, nothing loaded): 4,177 addenda - 4,128 ready to sign, 49 flagged (each with one diagnosis on its charge);
  1,258 distinct codes on them, every one with a CMS description; 2,909 distinct codes on any charge, 2,901 described (8 without a CMS
  description - codes CMS had already split before fiscal year 2023, none of them on a CCM charge); 41 hub documents, the largest 146 KB.

## Supporting items
Each item has a kind, a date inside the record's month, a source and one line of summary. Kinds: `fax_lab`, `fax_order`,
`fax_hhc_plan_of_care`, `fax_other`, `phone_call`, `call_transcript`, `referral`, `prescription`, `email`, `pcc_record`, `other`.
Where they come from: the practice's RingCentral account (faxes received, and calls and their transcripts on the main number),
referrals and prescriptions sent, home health plans of care signed, e-mail, and later PointClickCare. An item from another month is
refused: a month is supported by that month's own records.

## Where it lives
Neon is the primary store. The documents are in `raw.documents`, source `ccm` (collections `patients`, `months`, `signed`, `evidence`,
`faxes`, and since 11/12/2026 `addenda`, `addenda_signed`), written only through `tools/db/neon_db.py load-docs`; `tools/db/ccm_schema.sql`
builds the `ccm.*` views over them (`ccm.patients`, `ccm.months`, `ccm.signed_notes`, `ccm.notes`, `ccm.evidence`, `ccm.faxes`,
`ccm.icd10`, `ccm.chart_diagnoses`, `ccm.addenda`, `ccm.signed_addenda`) and the trigger `ccm_signed_is_final` that skips any later change
to, or removal of, a signed note or its month (and, since 11/12/2026, a signed addendum or its draft). Applied to the practice database on 11/11/2026 after a rehearsal
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
   (`<dir>/hub`); a signed month is never rebuilt and keeps the fields he signed. It needs the ICD-10 descriptions (a new note lists its
   diagnoses with them): the reference document in Neon, or `--descriptions <file>`.
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

## The ICD-10 descriptions and the addenda, step by step
1. `python3 scripts/helpers/ccm_build.py icd10 --cms <folder of the CMS code files> --out <dir>` writes `<dir>/icd10cm/descriptions.json`
   (the codes on any charge, read from Neon); `python3 tools/db/neon_db.py load-docs --src <dir> --source ref` loads it.
2. `python3 scripts/helpers/ccm_build.py addenda --out <dir>` writes one draft per signed note (`<dir>/neon/addenda/<chart>_<YYYY-MM>_dx.json`
   - never for an addendum already signed) and the hub page's documents (`<dir>/hub/config/addenda.json`, `<dir>/hub/addenda/<YYYY-MM>-<n>.json`,
   each under 200 KB); `python3 tools/db/neon_db.py load-docs --src <dir>/neon --source ccm` loads the drafts, and the hub documents go into
   the page's own database with the ArtifactData tool (collections `config` and `addenda`).
3. On the hub page each signed note shows its addendum under it with "Sign this addendum" (owner only, after the review tick), and "Sign all
   addenda (N)" signs the ones that are not flagged after the same confirmation as the notes. A signing goes to the page's
   `addendum_signatures/<YYYY-MM>` document (never written over).
4. To record them: read the page's `addendum_signatures` collection with ArtifactData list (out_dir), then
   `python3 scripts/helpers/ccm_build.py signatures --kind addenda --page <out_dir> --out <dir> --via <page url>` checks each against the draft
   in Neon and writes `<dir>/addenda_signed/<id>.json` (refused ones listed with the reason), and
   `python3 tools/db/neon_db.py load-docs --src <dir> --source ccm` records them - final from then on. Then mark them recorded on the page
   (`rec: true`) and rebuild the page's addenda documents so its counts move.

## Running it (11/25/2026)
The daily Claimocity feed routine does it, as PHASE C of `nightly/live/feed_daily.txt`: `scripts/helpers/ccm_month.py plan` (one Neon read) decides whether anything is waiting; when new CCM charges came in, `ccm_month.py read --in-routine` reads them back from AdvancedMD (read only, the feed's own login - the feed misses later voids and AdvancedMD holds the diagnosis order) into the workspace, `ccm_build.py build --hub-new` drafts the new or changed notes, and William gets one email with counts and the hub link. Offline proof: `python3 tools/selftest/test_ccm_month.py`.

## Not built yet
- The RingCentral search (faxes, calls): it needs the practice's RingCentral app key - the account's Developer Console access is turned
  off as of 11/11/2026 (the owner turns on "Developer Portal Access" for his role, or RingCentral support enables it);
  `scripts/helpers/ringcentral_fax.py` is on the census-inputs pull request.
- Supporting items on the notes (faxes, calls, transcripts, referrals, prescriptions, plans of care, PointClickCare) - as dated addenda.

Offline proofs (no AdvancedMD, no RingCentral, no Neon, no network): `python3 tools/selftest/test_ccm_notes.py`,
`python3 tools/selftest/test_ccm_patients.py`, `python3 tools/selftest/test_ccm_build.py`.
