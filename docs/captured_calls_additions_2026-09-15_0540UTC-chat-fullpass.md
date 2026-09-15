# Captured-calls additions — 2026-09-15 05:40 UTC (chat full pass, William-requested)

## New observations (AMD)
- **`getclaimunbillablecharges` prior-payor rows decided from charge detail attrs**: `lastbilledcarrier` (sequence last billed), `datebilled`, and the payment list on `resave.detail(cid)`. Rows with only $0 postings (denial/info) or an empty `datebilled` (brand-new charge) = case (b) → `hideunbillablevisits hide="-1"`. Only a REAL (nonzero) primary payment older than the secondary window is a write-off candidate. 9/15: 128 charges / 103 visits, all release; Unbilled 114 → 11.
- **`hideunbillablevisits` success reply is `<Results success="1" /><Error />`** — the empty `<Error />` element is NOT a fault. Detect faults on `<Fault` / `success="0"`, never on the string "error".
- **`getclaimexclusionclaimruns`** returns ONLY runs that still carry live exclusions (with `claimcount`); it is the right list to iterate. `getclaimrunstatus` `totalexclusions` is the historical count at submit time and stays > 0 after rows are completed.
- **"Payment reason codes are missing or do not balance"** (Unbilled) = a payment on the charge posted with an empty `<reasonlist>`; residual sits in `insbalance`. Fix = re-post with CARCs from the remit. Never release.
- **The 9/14 04:20 UTC freq-1 rebill transmitted on the next NIGHTLY 21:07 ET run (1700192), not on the run created at rebill time.** A rebill's CH verdict is read on the run whose `date` is the first 21:07 after the rebill.
- **AET12/PREF0288 NOT fixed by the Standard Professional profile.** Run 1700192: 59/59 rejected PREF0288 INVALID PAYER ID/CPID 814723941 + PREF0264 MISS/INVD PAYER DOC CONTRL NUM. Carrier-master (UI) change required; do not rebill again.
- Stedi Centene 68069 answered a March DOS in September WITHOUT ERR 62 (returned Inactive with planEnd) — ERR 62 is not guaranteed on old DOS.
- FL Medicaid 77027 271 can return **Active with planCoverage "FP| Limited to family planning services"** — Active ≠ billable; read `planCoverage`.
- UHC rejection text "PROCESSED ACCORDING TO CONTRACT, PLAN PROVISIONS" on an unprocessable claim = already adjudicated (duplicate resubmission) → complete the exclusion, find the original remit (Clever 19394490B).

## Rolled in from chat b3fa6d0f (Availity, 9/14 23:30 ET)
- `availity_pdf.py` (Drive workspace mirror 1d7wjRNHpfID2Z6fgxKLPBKPOOgowh0Wy) parses Availity Remittance Viewer ClaimDetails/CheckDetails PDFs → ERA-style rows (trace #, check date/amount, FL Blue claim #, AMD visit + claim letter, per-line CPT/CAS/RARC). Companion `availity_paste.py` (1-yNQXJ9BStCulkAKo-EAWTQYPviOcYs5).
- Pull at CHECK level (≈150–200 check files/yr) not per claim. Order: 26YYMMDD zero-dollar remits (denial worklist) → checks AMD failed to auto-post (nightly email counts) → skip cleanly-posted checks.
- OA-18 exact duplicate on a claim letter E = 5th submission (Dean 19426625/19426661): freq-1 into an already-adjudicated claim; fix = locate original remit, never a 6th send.
- Status-22 reversal PR-22/N598 (Dayhoff 19446222) = FL Blue takeback, other policy primary → COB fix + post the takeback.
- ReceiveFiles may hold 835s that would replace PDF parsing (unverified).

## Workspace restore notes
- Cloud amd.py from repo core lacks `call()/rest_post()/check_eligibility*`: append `amd_shims_2026-09-10.py` in full (not just `call`).
- `.amd_cred.json` key is `psw`, not `password`.
- `precheck.py` needs `carriers.json` = `practices/ehpa/carriers.json` copied into the workspace.
