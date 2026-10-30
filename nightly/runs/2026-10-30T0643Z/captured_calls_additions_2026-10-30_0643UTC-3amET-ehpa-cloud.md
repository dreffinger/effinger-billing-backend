# captured_calls additions - backend billing run 2026-10-30T0643Z (3 AM ET 10/30 slot, ehpa cloud)

No new call shapes. Calls used (all already in the registry): getclaimcenteroverview, getclaiminspectorbatches / getclaiminspectorcharges,
bypassclaimedits (insp_bypass_advisories.py, 11 visits, advisory 35790), getclaimunbillablecharges, getclaimrunstatus / getclaimexclusioncharges,
GET /api/era/checks (0 before / 0 after), posterapayments (nothing to post), POST /api/claim/massrebillsearch + Stedi 276/277
(claim_status_sweep --skip-answered, pass 171: 15 PENDING chart 17472874, 0 sent)
(engine pass tools/button/run_all.py --mode live --profile columns --stedi-proxy 06:44-06:53Z, then --steps sweep 07:00-07:01Z).
Behaviour seen: columns 0/11/4/1 -> 0/0/4/1 - the 11 inspector rows were the 0535Z cascade's re-sent visits (9 of chart 25558 + v19458938 + v19458953)
carrying only the 35790 add-on advisory; Unbilled = the four fac67 'Facility is missing NPI' visits ($871); Exclusions = AET12 chart 24750 run 1700294.
ERA Center empty before and after. No insurance entered, no rebill, no write-off. Pam Gmail: nothing beyond the 10/29 22:44Z readmit already handled.
