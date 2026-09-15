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

## Addendum 06:00 UTC — Baxley write-off (William instruction)
- No-coverage-at-DOS charges: transfer to patient responsibility then bad-debt no-pay = a single `manual_post.post(cid, carrier, pay=0, wo=balance, "WOBAD", note=...)` that zeros the insurance balance; WOINS fallback if WOBAD is refused (precedent: Alcorn 9/1 99308 on the 0310Z slot). Baxley 99239 chg 23342620 $163 + 99223 chg 23342783 $310 = $473, both -> $0, WOBAD accepted. Then `hideexclusions claimrunid hide="-1"` with both visit/claimid pairs to clear the dead exclusion rows. Register registers/wo_baxley_2026-09-15.json. Reverse + rebill if valid coverage is later found.

## Addendum 06:20 UTC — AET12 rebill #3 (William matched settings to AAR01)
- William changed the AET12 (car42009) carrier-master to match AAR01 (car6600, a working AARP payer). Per instruction, rebilled all 59 AET12 exclusion claims on run 1700192: freq-1 (`freq1_visit.run(vid,cid,seq)`) on AET12 **seq 2** (Medigap secondary), 15 patients, all `chargerebill -> 204`. Register registers/aet12_rebill_2026-09-15.json.
- Charge-id lookup that WORKS for exclusion visits: `gettxhistory` per patient, keep non-void charges whose `visit` is in the exclusion set (`getchargedetaildataicd10 visitid=` returns nothing for these). AET12 seq from getdemographic car42009.
- Watch: verdict on the NEXT nightly 21:07 ET run's CH report (rebill timing rule). If PREF0288/PREF0264 recurs, next lever per William = **suppress the provider loop** (another carrier-master setting) then rebill again.
- Log gotcha: a `--dry` run and the live run share aet12_rebill_0915.log; the "=== done: N ===" summary line is not authoritative — count `^REBILL ... -> 204` lines by distinct visit instead. Live run initially left 6 visits unsent (Thomson x2, Poppell x4); resent to 204.
