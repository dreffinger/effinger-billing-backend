# captured_calls additions - 2026-09-19 1510 UTC (11 AM ET 9/19 backend billing run, ehpa cloud v7)

No new call shapes this run. Behaviours confirmed (registry-level notes, chart ids only):

- **Quiet slot.** getclaimcenteroverview at 15:17Z: Charge Review 0 / Claim Inspector 0 / Unbilled 14 ($3030.26) / Exclusions 1 ($204.00, list calls return 0 rows on every run - the overview count lags). getclaimrunstatus still lists 1700202 (9/16 22:16 AMD clock) as the newest claim run (78 runs): fifteenth consecutive worked slot with no nightly claim run - the Automation Center EOD close has not fired since 9/16.
- **Unbilled snapshot unchanged**: the same 14 rows as 1310Z (11 'Payment reason codes are missing or do not balance' on 2024 SUN01/BCBS/HUM01/TRI05 visits held per the 9/15 rule; pat17471007 v19375395 'Bill Insurance = No' MV line on William's turn; pat17477798 x2 'Insurance order is missing' - getdemographic at 15:17Z still returns no insplan, no facesheet in Drive, no Pam email, no drop).
- **AET12 (car42009) live re-read** (gettxhistory on the 15 charts of exclusion run 1700202): 68 charges, billdate 09/16/2026, insurance balance $2052.25 open, Medicare paid $9703.75, no AET12 payment, none at $0 - held on the carrier-master fix, not re-sent.
- **Post button on the held Medicare check, fourth slot in a row**: era_post --all-unposted re-offered 29 lines on 1051714 (postable=29 / skipped=103) and AMD refused every one (fault -2147217287, PaymentEntry=29) - the already-manual-posted lines; no double post.
