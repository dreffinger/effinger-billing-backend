# captured_calls additions - 2026-09-18T1910Z (3pm ET 9/18/2026 slot, ehpa cloud Code Routine)

No new AMD call shapes this run. Behaviours worth keeping:
- A Claimocity feed drop of 24 HCA hospital visits (batch 127737) all arrive in the Claim Inspector with 'Hospitalization From Date empty'; the insp_0917_1910.py recipe (admission = most recent 99223 within 45 days / own 99223 / the same stay's date already on an earlier visit, updextrainsinfo hospitalizationfrom per CPT, full-visit resave onhcfa=1, re-list + bypass advisories with fresh ids) cleared all 24 in one pass, 0 held.
- Z96.641 / Z96.651 (presence of a joint implant) as the only diagnosis on a 99232 fires dx_primary_fix.never_primary; the cascade lands on add-i10 (I10 dcode1034543883 in front) and freq-1 rebills the visit (204) before the admission-date write.
- getclaimrunstatus still lists 1700202 (AMD clock 2026-09-16 22:16) as the newest claim run at 19:25Z 9/18 (78 runs): fifth consecutive worked slot with no nightly claim run - nothing in the API starts one; the 24 inspector-cleared visits, the 2 dx-cascade rebills and the 59 AET12 claims all wait on the Automation Center EOD close.
