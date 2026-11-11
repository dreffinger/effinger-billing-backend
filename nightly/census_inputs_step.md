# CENSUS INPUTS — step `census` (v1, 2026-11-11)

William 11/11/2026: "daily census inputs can be the app, or section, and claimocity feed will be one of the sections in that category";
"the claimocity integration is the best electronic input for a practice to input a census, but not the only way a practice can send in
daily census reports with the relevant information date patient name location and code"; "this is for supporting information and if the
claimocity feed is not available, the claimocity feed takes the paramount importance with the other feeds as supporting information";
"this would give other practices that dont use claimocity the ability to get encounters into advancedmd for billing".

## The category and its sections
**Census inputs** is the category. Every section carries the same kind of information - the date, the patient's name, the location, the
code, and whatever else the page has:

| section (`source`) | what it is | what it usually carries |
|---|---|---|
| Claimocity feed | electronic, entered by the feed step (nightly/claimocity_feed_step.md) - **the record** | everything: date, name, birth date, building, clinician, codes, diagnoses |
| Claimocity app census list - `claimocity_app` | a screenshot of the app's census list | room, name, visit code, clinician's initials |
| Hospital or facility census list - `hospital_census` | a picture, a scan or a fax of the building's own list | room, name, birth date, record number, visit number, admit date, attending |
| Ortho report - `ortho_fax` | the report that arrives by fax | as the hospital's list |
| Daily census a practice sends in - `practice_census` | a fax, a scan or an upload from a practice that does not use Claimocity | who was seen, on what date, where, which code |

THE RULE OF WEIGHT: the feed is the record. Everything else supports it and stands in for it when it is not available. Where a census
and the feed differ, the feed stands and the difference is listed for a person.

## The ways in - one folder
The Drive folder **"aa census imports files"** (id `1FCZQpMV9hE5UHJ-VdV_n-sVgOMJMIGsa`, inside "aa claude folders" > "aa claude practice
optimization framework"; practices/ehpa/practice.json `drive.census_inbox`) is the one place a census arrives:
- **an upload**: William (or a practice) drops a screenshot, a photo or a PDF there;
- **a fax through RingCentral**: `python3 ringcentral_fax.py --fetch` copies every received fax out of RingCentral into the workspace's
  inbox/faxes/ (the API route William chose 11/11/2026). It needs the practice's own RingCentral app - a private REST API app with the
  "Read Messages" permission; its client id, client secret and JWT reach a run as RINGCENTRAL_CLIENT_ID, RINGCENTRAL_CLIENT_SECRET and
  RINGCENTRAL_JWT or as secrets/ringcentral.json in the workspace, never through the repository - and the hosts platform.ringcentral.com
  and media.ringcentral.com allowed for the environment. 'no RingCentral key here' (exit 4) = report that line and go on with the uploads;
  exit 5 (sign-in refused), 6 (RingCentral answered an error) and 3 (the network is closed) = report the line verbatim, never retry in
  the same run. RingCentral keeps only the newest 200 received faxes (30 days on an account with its HIPAA setting on), so the fetch runs
  every day. The first real run is `python3 ringcentral_fax.py --list` (it downloads nothing). Each new PDF in inbox/faxes/ is uploaded
  to the Drive folder by the run (the PHI-safe copy) and read like an upload;
- **a scan made with Adobe** (Adobe Scan on the phone, Acrobat on the desktop): saved or shared into the same Drive folder - a scheduled
  run carries Drive and Gmail, not Adobe; a chat session with the Adobe connector can also find a scan in Adobe's cloud storage;
- **mail**: an attachment William points at this step is saved into the folder first.

## What a run does (a chat session on William's word, or a routine once this step is switched on for it)
1. Helpers: `cd /home/claude/effinger-billing-backend/scripts/helpers && cp -p census_inputs.py ringcentral_fax.py /home/claude/unbilled/`.
2. Faxes: `cd /home/claude/unbilled && python3 ringcentral_fax.py --fetch` (see above).
3. What is new: list the Drive folder; `cd /home/claude/unbilled && python3 census_inputs.py status` prints one line per file already
   read with its Drive ids. Download every file whose id is not there (and every new PDF of inbox/faxes/) into inbox/census/.
4. Read each new file - the picture or the PDF itself, never a pasted text version of it (the columns come apart and icons are read as
   letters). Write what the page PRINTS as one JSON record per file:
   `{"schema": "census/1", "source": ..., "practice": "ehpa", "date": "YYYY-MM-DD", "place": ..., "facility": "<the building as printed>", "rows": [...]}`
   - `source`: `claimocity_app`, `hospital_census`, `ortho_fax` or `practice_census`; `place`: `hospital`, `nursing`, `home` or `office`;
     `date`: the day the list is for (the app's own date; on a faxed list the date the list was printed).
   - one row per patient: `n` (its place on the page, counted from 1), `name` (as printed, family name first), and whatever the page
     shows of `dob`, `room`, `mrn`, `visit_no`, `admit`, `attending`, `clinician`, `code`, `more_codes` (the "+1" beside a code). Dates
     are written YYYY-MM-DD.
   - `unread`: the cells of that row the page does not show clearly (handwriting over the print, a cut-off edge). A cell that cannot be
     read is listed there and left out - it is never guessed. A row whose name cannot be read says so with `unread: ["name"]`.
   - NOT kept: the reason for a visit, a diagnosis written as words, handwriting, notes. The helper refuses a record that carries them.
5. Save: `cd /home/claude/unbilled && python3 census_inputs.py save <record.json> --file <the picture or PDF> --drive-id <its Drive id>`.
   'census saved: ...' = done; 'census already saved' = the same file had been sent before (read once); 'NOT SAVED' = the record has a
   problem, named line by line - correct what was read and save again (`--replace` only to put a better reading in place of an earlier one).
6. Compare: `cd /home/claude/unbilled && python3 census_inputs.py compare --recent 7` - every census day of the last week against the
   Claimocity feed of that day and the same kind of place (the feed brings charges a day or two after the visit, so each day is checked
   again). One line per day and place for the report: `census check <day> <place>: census N patient(s) from K file(s) | feed M visit(s)
   | on both B (code differs C) | census only X | feed only Y`. 'names not on hand' = this machine has the feed's registers but not its
   parsed files: counts and codes only. 'nothing yet' = the feed has no visit for that day so far.
7. Report: the `census check` lines under the feed line; every line that starts `  - TOP OF THE REPORT - ` goes to the top word for word:
   - `CENSUS WITHOUT A FEED: <day> (<place>) ...` = three days on, the feed has brought no visit for that day: the census is the worklist.
   - `ON THE CENSUS, NOT IN THE FEED: N patient(s) ...` = the feed did bring that day's visits and N patients of a census have none:
     possible missed charges.
   The names behind both are in census/<day>/census_check_<day>.md in the workspace: that file goes to Drive "chat history" with the run
   digest, never into a commit. William says what happens; no routine enters a visit from a census.
8. Mirror: registers/census_inputs.json, registers/census_check_<day>.json and registers/ringcentral_faxes.json -> practices/ehpa/registers/
   on main with the other registers (counts, chart ids, file and row numbers - no name, birth date, room, telephone number or file name).
   The census records (census/<day>/*.json), the pictures and the PDFs stay in the workspace and Drive.

## What a routine never does
- Enter, change or void anything in AdvancedMD from a census: no routine enters a visit from a census. Entering encounters for a
  practice that has no Claimocity feed needs William's own rule first (which code and diagnosis a census row may stand for, that
  practice's AdvancedMD sign-in, and his approval of each batch) - it is not built.
- Guess: a name, a date or a code the page does not show clearly is `unread`, never guessed.
- Put a census picture, a scan, a fax or a name into the repository, a skill or a public page. `.gitignore` keeps pictures and PDFs out
  of the folders run files are copied into (the privacy gate reads text files only).
- Change anything in RingCentral: the fax helper only reads.

Offline proof: `python3 tools/selftest/test_census_inputs.py` (no AdvancedMD, no RingCentral, no network; nothing is started as a program).
